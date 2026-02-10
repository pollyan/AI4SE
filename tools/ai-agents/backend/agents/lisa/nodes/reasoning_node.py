import logging
from typing import Literal, Any, Dict, List
from langgraph.types import Command
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage
from ..intent_parser import parse_user_intent, ClarifyContext
from ...shared.artifact_summary import get_artifacts_summary

from ..state import LisaState, ArtifactKeys
from ..schemas import ReasoningResponse
from langgraph.config import get_stream_writer
from ..stream_utils import process_reasoning_stream
from ..prompts.workflows.test_design import (
    build_test_design_prompt,
    DEFAULT_TEST_DESIGN_STAGES,
)
from ..prompts.workflows.requirement_review import (
    build_requirement_review_prompt,
    DEFAULT_REQUIREMENT_REVIEW_STAGES,
)
from ..prompts.artifacts import (
    generate_requirement_template,
    ARTIFACT_STRATEGY_BLUEPRINT,
    ARTIFACT_CASES_SET,
    ARTIFACT_DELIVERY_FINAL,
    ARTIFACT_REQ_REVIEW_RECORD,
    ARTIFACT_STRATEGY_BLUEPRINT as ARTIFACT_REQ_REVIEW_RISK,
    ARTIFACT_REQ_REVIEW_RECORD as ARTIFACT_REQ_REVIEW_REPORT,  # Placeholder mapping for now
)

logger = logging.getLogger(__name__)

# Clarify 阶段问题提取正则
import re


def extract_blocking_questions(artifacts: Dict[str, Any]) -> List[str]:
    """从产出物中提取 [P0] 阻塞性问题

    解析 Markdown 文档中 '[P0] 阻塞性问题' 部分下的问题列表
    支持新旧两种格式: [P0] 和 🔴
    """
    questions = []

    for key, content in artifacts.items():
        if not isinstance(content, str):
            continue

        # 支持两种格式: [P0] 和 🔴
        pattern = r"###\s*(?:\[P0\]|🔴)\s*阻塞性问题[^\n]*\n(.*?)(?=###|\Z)"
        matches = re.findall(pattern, content, re.DOTALL)

        for match in matches:
            # 提取列表项 (1. xxx 或 - xxx)
            items = re.findall(r"^\s*(?:\d+\.\s*|\-\s*)(.+)$", match, re.MULTILINE)
            questions.extend(items)

    return questions


def extract_optional_questions(artifacts: Dict[str, Any]) -> List[str]:
    """从产出物中提取 [P1] 建议澄清问题

    解析 Markdown 文档中 '[P1] 建议澄清' 部分下的问题列表
    支持新旧两种格式: [P1] 和 🟡
    """
    questions = []

    for key, content in artifacts.items():
        if not isinstance(content, str):
            continue

        # 支持两种格式: [P1] 和 🟡
        pattern = r"###\s*(?:\[P1\]|🟡)\s*建议澄清[^\n]*\n(.*?)(?=###|\Z)"
        matches = re.findall(pattern, content, re.DOTALL)

        for match in matches:
            # 提取列表项
            items = re.findall(r"^\s*(?:\d+\.\s*|\-\s*)(.+)$", match, re.MULTILINE)
            questions.extend(items)

    return questions


# 定义产出物模板映射
TEST_DESIGN_TEMPLATES = [
    {
        "key": ArtifactKeys.TEST_DESIGN_REQUIREMENTS,
        "name": "需求分析文档",
        "stage": "clarify",
        "outline": generate_requirement_template(),
    },
    {
        "key": ArtifactKeys.TEST_DESIGN_STRATEGY,
        "name": "测试策略蓝图",
        "stage": "strategy",
        "outline": ARTIFACT_STRATEGY_BLUEPRINT,
    },
    {
        "key": ArtifactKeys.TEST_DESIGN_CASES,
        "name": "测试用例集",
        "stage": "cases",
        "outline": ARTIFACT_CASES_SET,
    },
    {
        "key": ArtifactKeys.TEST_DESIGN_FINAL,
        "name": "测试设计文档",
        "stage": "delivery",
        "outline": ARTIFACT_DELIVERY_FINAL,
    },
]

REQ_REVIEW_TEMPLATES = [
    {
        "key": ArtifactKeys.REQ_REVIEW_RECORD,
        "name": "需求评审记录",
        "stage": "clarify",
        "outline": ARTIFACT_REQ_REVIEW_RECORD,
    },
    {
        "key": "req_review_risk",
        "name": "风险评估与测试重点",
        "stage": "risk",
        "outline": ARTIFACT_STRATEGY_BLUEPRINT,
    },  # Reuse blueprint style for risk
    {
        "key": ArtifactKeys.REQ_REVIEW_REPORT,
        "name": "敏捷需求评审报告",
        "stage": "report",
        "outline": ARTIFACT_REQ_REVIEW_RECORD,
    },  # Reuse record style for report
]


def ensure_workflow_initialized(state: LisaState) -> Dict[str, Any]:
    """确保工作流状态已初始化 (Plan & Templates)"""
    updates = {}
    current_workflow = state.get("current_workflow", "test_design")

    # 1. 初始化 Plan
    if not state.get("plan"):
        if current_workflow == "requirement_review":
            updates["plan"] = DEFAULT_REQUIREMENT_REVIEW_STAGES
            updates["current_stage_id"] = "clarify"
        else:  # default to test_design
            updates["plan"] = DEFAULT_TEST_DESIGN_STAGES
            updates["current_stage_id"] = "clarify"

    # 2. 初始化 Artifact Templates
    if not state.get("artifact_templates"):
        if current_workflow == "requirement_review":
            updates["artifact_templates"] = REQ_REVIEW_TEMPLATES
        else:
            updates["artifact_templates"] = TEST_DESIGN_TEMPLATES

    return updates


def reasoning_node(
    state: LisaState, llm: Any
) -> Command[Literal["artifact_node", "__end__"]]:
    """
    对话 + 进度节点 (Reasoning Node)
    """
    logger.info("Entering ReasoningNode...")

    # 0. 状态初始化检查
    init_updates = ensure_workflow_initialized(state)
    if init_updates:
        logger.info(f"Initializing workflow state: {list(init_updates.keys())}")
        state.update(init_updates)

    # 获取最新状态
    current_stage = state.get("current_stage_id", "clarify")
    current_workflow = state.get("current_workflow", "test_design")
    messages = state["messages"]
    artifacts = state.get("artifacts", {})

    # === Clarify 阶段意图解析 ===
    user_intent_result = None
    if current_stage == "clarify" and messages:
        last_message = messages[-1]
        if isinstance(last_message, HumanMessage):
            blocking_qs = extract_blocking_questions(artifacts)
            optional_qs = extract_optional_questions(artifacts)

            context = ClarifyContext(
                blocking_questions=blocking_qs, optional_questions=optional_qs
            )

            user_intent_result = parse_user_intent(
                user_message=str(last_message.content), context=context, llm=llm
            )

            if user_intent_result.intent == "confirm_proceed" and blocking_qs:
                warning_msg = (
                    f"⚠️ 检测到您希望继续，但仍有 {len(blocking_qs)} 个阻塞性问题未解决：\n\n"
                    + "\n".join(f"- {q}" for q in blocking_qs[:3])
                    + ("\n..." if len(blocking_qs) > 3 else "")
                    + "\n\n请先回答这些问题，或明确表示接受风险继续。"
                )
                logger.info(
                    f"Clarify stage: confirm_proceed with {len(blocking_qs)} blockers, returning warning"
                )
                writer = get_stream_writer()
                return Command(
                    update={"messages": [AIMessage(content=warning_msg)]},
                    goto="__end__",
                )

    # 确保使用最新的 plan (包含初始化更新)
    plan = (
        init_updates.get("plan")
        if init_updates and "plan" in init_updates
        else state.get("plan", [])
    )

    writer = get_stream_writer()

    # 立即发送初始化进度 (修复 UI 空白问题)
    if init_updates and writer:
        writer(
            {
                "type": "progress",
                "progress": {
                    "stages": plan,
                    "currentStageIndex": 0,  # Default to 0 for init
                    "currentTask": "正在初始化工作流...",
                    "artifact_templates": init_updates.get("artifact_templates")
                    or state.get("artifact_templates", []),
                    "artifacts": artifacts,
                },
            }
        )

    # 1. 构建 Prompt
    artifacts_summary = get_artifacts_summary(artifacts)

    # 注入意图上下文
    intent_context = ""
    if user_intent_result:
        intent_context = (
            f"\n\n**USER INTENT DETECTED**: {user_intent_result.intent} (Confidence: {user_intent_result.confidence})\n"
            f"Info: {user_intent_result.extracted_info or 'N/A'}\n"
            "If intent is 'provide_material' or 'answer_question', you MUST update artifacts."
        )

    if current_workflow == "requirement_review":
        system_prompt = (
            build_requirement_review_prompt(
                stage=current_stage,
                artifacts_summary=artifacts_summary,
                pending_clarifications="",
                consensus_count=0,
            )
            + intent_context
        )
    else:
        system_prompt = (
            build_test_design_prompt(
                stage=current_stage,
                artifacts_summary=artifacts_summary,
                pending_clarifications="",
                consensus_count=0,
                plan_context=str([p["name"] for p in plan]),
            )
            + intent_context
        )

    messages_with_prompt = [SystemMessage(content=system_prompt)] + messages

    # 2. Structured Output 配置
    structured_llm = llm.model.with_structured_output(
        ReasoningResponse, method="function_calling"
    )

    # 3. 流式处理
    try:
        # 确保使用最新的 artifact_templates (包含初始化更新)
        current_templates = (
            init_updates.get("artifact_templates")
            if init_updates and "artifact_templates" in init_updates
            else state.get("artifact_templates", [])
        )

        final_response = process_reasoning_stream(
            stream_iterator=structured_llm.stream(messages_with_prompt),
            writer=writer,
            plan=plan,
            current_stage=current_stage,
            # 将 templates 混入 base_artifacts 传递给 stream_utils (临时方案，避免修改函数签名)
            # 或者修改 stream_utils 接收更多参数。这里选择利用已有的 base_artifacts 参数
            # 但 base_artifacts 本意是 dict[str, str]。
            # 更稳妥的方式是修改 stream_utils.py 的签名，或者确认 base_artifacts 是否能携带额外信息。
            # 查看 stream_utils.py:117 current_artifacts = dict(base_artifacts or {})
            # 所以如果在 base_artifacts 中放入 'artifact_templates' key，它会被复制到 current_artifacts
            # 并在 progress event 中发送。
            base_artifacts={**artifacts, "artifact_templates": current_templates},
        )
    except Exception as e:
        logger.error(f"Reasoning stream failed: {e}", exc_info=True)
        return Command(
            update={"messages": [AIMessage(content="系统处理异常，请稍后重试。")]},
            goto="__end__",
        )

    # 4. 更新 State
    final_thought = final_response.thought
    new_messages = [AIMessage(content=final_thought)]

    # 构造完整 update 字典 (包含初始化更新)
    state_updates = {"messages": new_messages}
    if init_updates:
        state_updates.update(init_updates)

    # 处理阶段流转请求
    if final_response.request_transition_to:
        next_stage = final_response.request_transition_to
        logger.info(
            f"ReasoningNode: Transition requested from {current_stage} to {next_stage}"
        )
        state_updates["current_stage_id"] = next_stage
        state_updates["current_workflow"] = current_workflow  # Maintain workflow type

    # 5. 路由决策 (强制路由到 ArtifactNode)
    # 用户要求：90% 以上的情况都需要更新生成产出物，所以固定每次对话结束的时候都生成产出物
    # 在生成的逻辑里再看具体要更新什么 (ArtifactNode 内部逻辑)

    logger.info("ReasoningNode completed. Always routing to artifact_node.")
    return Command(
        update=state_updates,  # 包含初始化状态
        goto="artifact_node",
    )
