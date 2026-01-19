"""
Workflow Test Design Node - 测试设计工作流节点

处理测试设计工作流的核心逻辑，包括需求澄清、策略制定、用例编写和文档交付。
"""

import logging
import re
from typing import Any, List, Dict, Optional, cast

from langchain_core.messages import SystemMessage, AIMessage, HumanMessage, BaseMessage
from langgraph.config import get_stream_writer

from ..state import LisaState, ArtifactKeys
from ..schemas import UpdateArtifact, WorkflowResponse
from ..prompts.workflows import build_workflow_prompt
from backend.agents.shared.artifact_summary import get_artifacts_summary
from ..prompts.artifacts import (
    ARTIFACT_CLARIFY_REQUIREMENTS,
    ARTIFACT_STRATEGY_BLUEPRINT,
    ARTIFACT_CASES_SET,
    ARTIFACT_DELIVERY_FINAL,
    ARTIFACT_REQ_REVIEW_RECORD
)
from backend.agents.shared.data_stream import (
    stream_text_delta,
    stream_data
)
from ..stream_utils import process_workflow_stream

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# 默认计划定义
# ═══════════════════════════════════════════════════════════════════════════════

DEFAULT_TEST_DESIGN_PLAN: List[Dict[str, str]] = [
    {"id": "clarify", "name": "需求澄清", "status": "pending"},
    {"id": "strategy", "name": "策略制定", "status": "pending"},
    {"id": "cases", "name": "用例设计", "status": "pending"},
    {"id": "delivery", "name": "文档交付", "status": "pending"},
]

DEFAULT_REQUIREMENT_REVIEW_PLAN: List[Dict[str, str]] = [
    {"id": "clarify", "name": "需求澄清", "status": "pending"},
    {"id": "analysis", "name": "需求分析", "status": "pending"},
    {"id": "risk", "name": "风险评估", "status": "pending"},
    {"id": "report", "name": "评审报告", "status": "pending"},
]

# 产出物模板元数据
ARTIFACT_TEMPLATES_TEST_DESIGN = [
    {"stage_id": "clarify", "artifact_key": "test_design_requirements", "name": "需求澄清报告"},
    {"stage_id": "strategy", "artifact_key": "test_design_strategy", "name": "测试策略蓝图"},
    {"stage_id": "cases", "artifact_key": "test_design_cases", "name": "测试用例集"},
    {"stage_id": "delivery", "artifact_key": "test_design_final", "name": "交付文档"},
]

ARTIFACT_TEMPLATES_REQUIREMENT_REVIEW = [
    {"stage_id": "clarify", "artifact_key": "req_review_record", "name": "需求评审记录"},
    {"stage_id": "analysis", "artifact_key": "req_review_record", "name": "需求评审记录"},
    {"stage_id": "risk", "artifact_key": "req_review_risk", "name": "风险评估报告"},
    {"stage_id": "report", "artifact_key": "req_review_report", "name": "评审报告"},
]

def get_artifact_templates(workflow_type: str) -> List[Dict[str, str]]:
    """获取工作流对应的产出物模板元数据"""
    if workflow_type == "requirement_review":
        return ARTIFACT_TEMPLATES_REQUIREMENT_REVIEW
    return ARTIFACT_TEMPLATES_TEST_DESIGN


# ═══════════════════════════════════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════════════════════════════════

def get_default_plan(workflow_type: str) -> List[Dict[str, str]]:
    """获取工作流的默认计划"""
    if workflow_type == "requirement_review":
        return [dict(s) for s in DEFAULT_REQUIREMENT_REVIEW_PLAN]
    return [dict(s) for s in DEFAULT_TEST_DESIGN_PLAN]


def get_stage_index(plan: List[Dict], stage_id: str) -> int:
    """获取阶段在计划中的索引"""
    for i, stage in enumerate(plan):
        if stage.get("id") == stage_id:
            return i
    return 0


def update_plan_status(plan: List[Dict], current_stage_id: str) -> None:
    """更新计划中各阶段的状态"""
    current_idx = get_stage_index(plan, current_stage_id)
    for i, stage in enumerate(plan):
        if i < current_idx:
            stage["status"] = "completed"
        elif i == current_idx:
            stage["status"] = "active"
        else:
            stage["status"] = "pending"

def determine_stage(state: LisaState, workflow_type: str) -> str:
    """
    根据产出物确定当前阶段
    
    Args:
        state: 当前状态
        workflow_type: 工作流类型
    """
    artifacts = state.get("artifacts", {})
    
    if workflow_type == "requirement_review":
        # 需求评审流程: clarify -> analysis -> risk -> report
        if ArtifactKeys.REQ_REVIEW_REPORT in artifacts:
            return "report"  # 已完成，停留在最后阶段或进入结束
        elif ArtifactKeys.REQ_REVIEW_RISK in artifacts:
            return "report"
        elif ArtifactKeys.REQ_REVIEW_RECORD in artifacts:
            return "risk"
        else:
            return "clarify"
            
    else:  # 默认为 test_design
        # 测试设计流程: clarify -> strategy -> cases -> delivery
        if ArtifactKeys.TEST_DESIGN_FINAL in artifacts:
            return "delivery"
        elif ArtifactKeys.TEST_DESIGN_CASES in artifacts:
            return "delivery"
        elif ArtifactKeys.TEST_DESIGN_STRATEGY in artifacts:
            return "cases"
        elif ArtifactKeys.TEST_DESIGN_REQUIREMENTS in artifacts:
            return "strategy"
        else:
            return "clarify"


def get_artifact_template(key: str) -> str:
    """根据 Artifact Key 获取对应的 Markdown 模板"""
    if key == ArtifactKeys.TEST_DESIGN_REQUIREMENTS: return ARTIFACT_CLARIFY_REQUIREMENTS
    if key == ArtifactKeys.TEST_DESIGN_STRATEGY: return ARTIFACT_STRATEGY_BLUEPRINT
    if key == ArtifactKeys.TEST_DESIGN_CASES: return ARTIFACT_CASES_SET
    if key == ArtifactKeys.TEST_DESIGN_FINAL: return ARTIFACT_DELIVERY_FINAL
    if key == ArtifactKeys.REQ_REVIEW_RECORD: return ARTIFACT_REQ_REVIEW_RECORD
    return ""

def get_artifact_key_for_stage(stage: str, workflow_type: str) -> Optional[str]:
    """获取阶段对应的产出物 Key"""
    if workflow_type == "requirement_review":
        stage_to_artifact = {
            "clarify": ArtifactKeys.REQ_REVIEW_RECORD,
            "analysis": ArtifactKeys.REQ_REVIEW_RECORD,
            "risk": ArtifactKeys.REQ_REVIEW_RISK,
            "report": ArtifactKeys.REQ_REVIEW_REPORT,
        }
    else:
        stage_to_artifact = {
            "clarify": ArtifactKeys.TEST_DESIGN_REQUIREMENTS,
            "strategy": ArtifactKeys.TEST_DESIGN_STRATEGY,
            "cases": ArtifactKeys.TEST_DESIGN_CASES,
            "delivery": ArtifactKeys.TEST_DESIGN_FINAL,
        }
    return stage_to_artifact.get(stage)


# ═══════════════════════════════════════════════════════════════════════════════
# 主节点
# ═══════════════════════════════════════════════════════════════════════════════

def workflow_execution_node(state: LisaState, llm: Any) -> LisaState:
    """
    通用工作流执行节点
    
    能够处理 test_design 和 requirement_review 两种工作流。
    使用 get_stream_writer() 实时推送进度和产出物更新。
    """
    # 获取 StreamWriter 用于实时推送进度
    writer = get_stream_writer()
    
    # 获取当前工作流类型，默认为 test_design
    workflow_type = state.get("current_workflow") or "test_design"
    logger.info(f"执行工作流: {workflow_type}")
    
    # 确定当前阶段 (优先使用 current_stage_id)
    current_stage = state.get("current_stage_id") or state.get("workflow_stage")
    if not current_stage:
        current_stage = determine_stage(state, workflow_type)
    
    logger.info(f"当前阶段: {current_stage}")
    
    # 获取或初始化计划
    plan = state.get("plan") or get_default_plan(workflow_type)
    update_plan_status(plan, current_stage)
    
    # ════════════════════════════════════════════════════════════
    # 📍 推送进度更新
    # ════════════════════════════════════════════════════════════
    writer({
        "type": "progress",
        "progress": {
            "stages": plan,
            "currentStageIndex": get_stage_index(plan, current_stage),
            "currentTask": f"正在处理 {current_stage} 阶段...",
            "artifact_templates": get_artifact_templates(workflow_type)
        }
    })
    logger.info(f"StreamWriter 推送进度: stage={current_stage}")
    
    # ════════════════════════════════════════════════════════════
    # 📍 自动初始化产出物模板
    # ════════════════════════════════════════════════════════════
    target_artifact_key = get_artifact_key_for_stage(current_stage, workflow_type)
    
    if target_artifact_key:
        current_artifacts = state.get("artifacts", {})
        if target_artifact_key not in current_artifacts:
            # 1. 获取模板
            template = get_artifact_template(target_artifact_key)
            if template:
                # 2. 推送初始化事件 (作为 Progress 事件)
                # 构造临时 artifacts 字典用于前端展示
                display_artifacts = current_artifacts.copy()
                display_artifacts[target_artifact_key] = template
                
                writer({
                    "type": "progress",
                    "progress": {
                        "stages": plan,
                        "currentStageIndex": get_stage_index(plan, current_stage),
                        "currentTask": f"正在处理 {current_stage} 阶段...",
                        "artifact_templates": get_artifact_templates(workflow_type),
                        "artifacts": display_artifacts
                    }
                })
                logger.info(f"StreamWriter 初始化模板: {target_artifact_key}")
    
    # 构建上下文
    artifacts = state.get("artifacts", {})
    artifacts_summary = get_artifacts_summary(artifacts)
    pending = state.get("pending_clarifications", [])
    consensus = state.get("consensus_items", [])
    
    # 构建进度计划上下文
    plan = state.get("plan", [])
    plan_context_lines = []
    for step in plan:
        step_id = step.get("id", "")
        step_name = step.get("name", "")
        marker = "→ " if step_id == current_stage else "  "
        plan_context_lines.append(f"{marker}{step_id}: {step_name}")
    plan_context = "\n".join(plan_context_lines) if plan_context_lines else "(无进度计划)"
    
    # 使用统一的 Prompt 构建函数
    system_prompt = build_workflow_prompt(
        workflow_type=workflow_type,
        stage=current_stage,
        artifacts_summary=artifacts_summary,
        pending_clarifications=", ".join(pending) if pending else "(无)",
        consensus_count=len(consensus),
        plan_context=plan_context,
    )
    
    # 构建消息列表
    messages: List[BaseMessage] = [SystemMessage(content=system_prompt)]
    # 这里需要确保 messages 里的对象类型正确，LangChain 可能会把 dict 混进来
    # 如果是 dict，需要转换 (StateGraph 应该已经处理了，但为了安全)
    for msg in state.get("messages", []):
        messages.append(msg)
    
    # ════════════════════════════════════════════════════════════
    # 使用 Structured Output + Streaming (Phase 1 核心升级)
    # ════════════════════════════════════════════════════════════
    structured_llm = llm.model.with_structured_output(
        WorkflowResponse,
        method="function_calling"
    )
    
    # 最终汇总
    final_thought = ""
    
    new_artifacts = dict(artifacts)
    
    logger.info("开始 Structured Output 流式调用...")
    
    try:
        # 使用工具函数处理流
        final_response = process_workflow_stream(
            stream_iterator=structured_llm.stream(messages),
            writer=writer,
            plan=plan,
            current_stage=current_stage,
            base_artifacts=artifacts
        )
        
        final_thought = final_response.thought
        final_update_artifact = final_response.update_artifact

        # 循环结束，处理最终状态
        logger.info(f"流式调用结束. Thought: {len(final_thought)} chars")
        
        if final_update_artifact:
            key = final_update_artifact.key
            content = final_update_artifact.markdown_body
            if key and content:
                new_artifacts[key] = content
                logger.info(f"Structured Output 更新产出物: {key}")
                
                # process_workflow_stream 已经处理了实时推送，此处不再重复推送以免覆盖 currentTask
                pass

        ai_message = AIMessage(content=final_thought)
        
        # 更新消息历史
        new_messages = list(state.get("messages", []))
        new_messages.append(ai_message)
        
        # 返回更新后的状态
        return {
            **state,
            "messages": new_messages,
            "artifacts": new_artifacts,
            "workflow_stage": current_stage,
            "current_workflow": workflow_type,
        }
        
    except Exception as e:
        logger.error(f"测试设计工作流执行失败: {e}")
        error_message = AIMessage(content=f"抱歉，处理您的请求时遇到了问题：{str(e)}")
        new_messages = list(state.get("messages", []))
        new_messages.append(error_message)
        
        return {
            **state,
            "messages": new_messages,
        }
