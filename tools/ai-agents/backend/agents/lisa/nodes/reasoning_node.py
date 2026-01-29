import logging
from typing import Literal, Any, Dict, List
from langgraph.types import Command
from langchain_core.messages import AIMessage, SystemMessage

from ..state import LisaState, ArtifactKeys
from ..schemas import ReasoningResponse
from langgraph.config import get_stream_writer
from ..stream_utils import process_reasoning_stream
from ..prompts.workflows.test_design import build_test_design_prompt, DEFAULT_TEST_DESIGN_STAGES
from ..prompts.workflows.requirement_review import build_requirement_review_prompt, DEFAULT_REQUIREMENT_REVIEW_STAGES
from ..prompts.artifacts import (
    ARTIFACT_CLARIFY_REQUIREMENTS, ARTIFACT_STRATEGY_BLUEPRINT, ARTIFACT_CASES_SET, ARTIFACT_DELIVERY_FINAL,
    ARTIFACT_REQ_REVIEW_RECORD, ARTIFACT_STRATEGY_BLUEPRINT as ARTIFACT_REQ_REVIEW_RISK, ARTIFACT_REQ_REVIEW_RECORD as ARTIFACT_REQ_REVIEW_REPORT # Placeholder mapping for now
)

logger = logging.getLogger(__name__)

# 定义产出物模板映射
TEST_DESIGN_TEMPLATES = [
    {"key": ArtifactKeys.TEST_DESIGN_REQUIREMENTS, "name": "需求分析文档", "stage": "clarify", "outline": ARTIFACT_CLARIFY_REQUIREMENTS},
    {"key": ArtifactKeys.TEST_DESIGN_STRATEGY, "name": "测试策略蓝图", "stage": "strategy", "outline": ARTIFACT_STRATEGY_BLUEPRINT},
    {"key": ArtifactKeys.TEST_DESIGN_CASES, "name": "测试用例集", "stage": "cases", "outline": ARTIFACT_CASES_SET},
    {"key": ArtifactKeys.TEST_DESIGN_FINAL, "name": "测试设计文档", "stage": "delivery", "outline": ARTIFACT_DELIVERY_FINAL},
]

REQ_REVIEW_TEMPLATES = [
    {"key": ArtifactKeys.REQ_REVIEW_RECORD, "name": "需求评审记录", "stage": "clarify", "outline": ARTIFACT_REQ_REVIEW_RECORD},
    {"key": "req_review_risk", "name": "风险评估与测试重点", "stage": "risk", "outline": ARTIFACT_STRATEGY_BLUEPRINT}, # Reuse blueprint style for risk
    {"key": ArtifactKeys.REQ_REVIEW_REPORT, "name": "敏捷需求评审报告", "stage": "report", "outline": ARTIFACT_REQ_REVIEW_RECORD}, # Reuse record style for report
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
        else: # default to test_design
            updates["plan"] = DEFAULT_TEST_DESIGN_STAGES
            updates["current_stage_id"] = "clarify"
            
    # 2. 初始化 Artifact Templates
    if not state.get("artifact_templates"):
        if current_workflow == "requirement_review":
            updates["artifact_templates"] = REQ_REVIEW_TEMPLATES
        else:
            updates["artifact_templates"] = TEST_DESIGN_TEMPLATES
            
    return updates

def reasoning_node(state: LisaState, llm: Any) -> Command[Literal["artifact_node", "__end__"]]:
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
    
    # 确保使用最新的 plan (包含初始化更新)
    plan = init_updates.get("plan") if init_updates and "plan" in init_updates else state.get("plan", [])
    
    writer = get_stream_writer()
    
    # 立即发送初始化进度 (修复 UI 空白问题)
    if init_updates and writer:
        writer({
            "type": "progress",
            "progress": {
                "stages": plan,
                "currentStageIndex": 0, # Default to 0 for init
                "currentTask": "正在初始化工作流...",
                "artifact_templates": init_updates.get("artifact_templates") or state.get("artifact_templates", []),
                "artifacts": artifacts
            }
        })
    
    # 1. 构建 Prompt
    if current_workflow == "requirement_review":
        system_prompt = build_requirement_review_prompt(
            stage=current_stage,
            artifacts_summary=str(list(artifacts.keys())),
            pending_clarifications="", 
            consensus_count=0
        )
    else:
        system_prompt = build_test_design_prompt(
            stage=current_stage,
            artifacts_summary=str(list(artifacts.keys())),
            pending_clarifications="",
            consensus_count=0,
            plan_context=str([p["name"] for p in plan])
        )
        
    messages_with_prompt = [SystemMessage(content=system_prompt)] + messages

    # 2. Structured Output 配置
    structured_llm = llm.model.with_structured_output(
        ReasoningResponse,
        method="function_calling"
    )
    
    # 3. 流式处理
    try:
        # 确保使用最新的 artifact_templates (包含初始化更新)
        current_templates = init_updates.get("artifact_templates") if init_updates else state.get("artifact_templates", [])

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
            base_artifacts={**artifacts, "artifact_templates": current_templates}
        )
    except Exception as e:
        logger.error(f"Reasoning stream failed: {e}", exc_info=True)
        return Command(
             update={"messages": [AIMessage(content="系统处理异常，请稍后重试。")]},
             goto="__end__"
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
        logger.info(f"ReasoningNode: Transition requested from {current_stage} to {next_stage}")
        state_updates["current_stage_id"] = next_stage
        state_updates["current_workflow"] = current_workflow  # Maintain workflow type
    
    # 5. 路由决策 (含自动初始化 Artifact 检测)
    should_update = final_response.should_update_artifact
    
    # 检查当前阶段是否缺少产出物
    templates = state.get("artifact_templates", [])
    if not templates and init_updates: # 如果刚刚初始化，使用新模板
        templates = init_updates.get("artifact_templates", [])
        
    current_template = next((t for t in templates if t.get("stage") == current_stage), None)
    
    if current_template:
        key = current_template["key"]
        # 如果当前 key 对应的产出物为空，强制触发更新以生成初始模板
        if key not in artifacts:
            logger.info(f"Artifact {key} missing for stage {current_stage}. Forcing routing to ArtifactNode for initialization.")
            should_update = True
    
    if should_update:
        logger.info("ReasoningNode decided to UPDATE ARTIFACT. Routing to artifact_node.")
        return Command(
            update=state_updates, # 包含初始化状态
            goto="artifact_node"
        )
    
    logger.info("ReasoningNode completed. Ending flow.")
    return Command(
        update=state_updates, # 包含初始化状态
        goto="__end__"
    )
