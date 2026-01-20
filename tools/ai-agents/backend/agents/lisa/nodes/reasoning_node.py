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
    {"key": ArtifactKeys.TEST_DESIGN_REQUIREMENTS, "name": "需求分析文档", "outline": ARTIFACT_CLARIFY_REQUIREMENTS},
    {"key": ArtifactKeys.TEST_DESIGN_STRATEGY, "name": "测试策略蓝图", "outline": ARTIFACT_STRATEGY_BLUEPRINT},
    {"key": ArtifactKeys.TEST_DESIGN_CASES, "name": "测试用例集", "outline": ARTIFACT_CASES_SET},
    {"key": ArtifactKeys.TEST_DESIGN_FINAL, "name": "测试设计文档", "outline": ARTIFACT_DELIVERY_FINAL},
]

REQ_REVIEW_TEMPLATES = [
    {"key": ArtifactKeys.REQ_REVIEW_RECORD, "name": "需求评审记录", "outline": ARTIFACT_REQ_REVIEW_RECORD},
    {"key": "req_review_risk", "name": "风险评估与测试重点", "outline": ARTIFACT_STRATEGY_BLUEPRINT}, # Reuse blueprint style for risk
    {"key": ArtifactKeys.REQ_REVIEW_REPORT, "name": "敏捷需求评审报告", "outline": ARTIFACT_REQ_REVIEW_RECORD}, # Reuse record style for report
]

def ensure_workflow_initialized(state: LisaState) -> Dict[str, Any]:
    """确保工作流状态已初始化 (Plan & Templates)"""
    updates = {}
    workflow_type = state.get("workflow_type", "test_design")
    
    # 1. 初始化 Plan
    if not state.get("plan"):
        if workflow_type == "requirement_review":
            updates["plan"] = DEFAULT_REQUIREMENT_REVIEW_STAGES
            updates["current_stage_id"] = "clarify"
        else: # default to test_design
            updates["plan"] = DEFAULT_TEST_DESIGN_STAGES
            updates["current_stage_id"] = "clarify"
            
    # 2. 初始化 Artifact Templates
    if not state.get("artifact_templates"):
        if workflow_type == "requirement_review":
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
    workflow_type = state.get("workflow_type", "test_design")
    messages = state["messages"]
    artifacts = state.get("artifacts", {})
    plan = state.get("plan", [])
    
    writer = get_stream_writer()
    
    # 立即发送初始化进度 (修复 UI 空白问题)
    if init_updates and writer:
        writer({
            "type": "progress",
            "progress": {
                "stages": plan,
                "currentStageIndex": 0, # Default to 0 for init
                "currentTask": "正在初始化工作流...",
                "artifact_templates": state.get("artifact_templates", []),
                "artifacts": artifacts
            }
        })
    
    # 1. 构建 Prompt
    if workflow_type == "requirement_review":
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
        final_response = process_reasoning_stream(
            stream_iterator=structured_llm.stream(messages_with_prompt),
            writer=writer,
            plan=plan,
            current_stage=current_stage,
            base_artifacts=artifacts
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
    
    # 5. 路由决策
    if final_response.should_update_artifact:
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
