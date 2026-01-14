"""
Workflow Test Design Node - 测试设计工作流节点

处理测试设计工作流的核心逻辑，包括需求澄清、策略制定、用例编写和文档交付。
"""

import logging
from typing import Any

from langchain_core.messages import SystemMessage, AIMessage, HumanMessage

from ..state import LisaState, ArtifactKeys
from ..prompts.workflows import build_workflow_prompt
from backend.agents.shared.artifact_summary import get_artifacts_summary

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════════════════════════════════

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
            # 默认 starting point
            # 注意: 如果有 plan，通常 current_stage_id 会被设置，
            # 这个函数作为 fallback
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


def extract_artifact_from_response(response: str, stage: str, workflow_type: str) -> tuple[str, str]:
    """
    从 LLM 响应中提取产出物
    """
    # 阶段对应的产出物 Key 映射
    if workflow_type == "requirement_review":
        stage_to_artifact = {
            "clarify": None, # 澄清阶段通常无正式产出物，或者更新需求文档（暂不支持回写）
            "analysis": ArtifactKeys.REQ_REVIEW_RECORD,
            "risk": ArtifactKeys.REQ_REVIEW_RISK,
            "report": ArtifactKeys.REQ_REVIEW_REPORT,
        }
    else:
        # test_design
        stage_to_artifact = {
            "clarify": ArtifactKeys.TEST_DESIGN_REQUIREMENTS,
            "strategy": ArtifactKeys.TEST_DESIGN_STRATEGY,
            "cases": ArtifactKeys.TEST_DESIGN_CASES,
            "delivery": ArtifactKeys.TEST_DESIGN_FINAL,
        }
    
    artifact_key = stage_to_artifact.get(stage)
    if not artifact_key:
        return None, None
    
    # 简单的产出物提取逻辑：查找 Markdown 代码块
    if "```markdown" in response:
        start = response.find("```markdown") + 11
        end = response.find("```", start)
        if end > start:
            return artifact_key, response[start:end].strip()
    
    return None, None


# ═══════════════════════════════════════════════════════════════════════════════
# 主节点
# ═══════════════════════════════════════════════════════════════════════════════

def workflow_execution_node(state: LisaState, llm: Any) -> LisaState:
    """
    通用工作流执行节点 (原名 workflow_test_design_node)
    
    能够处理 test_design 和 requirement_review 两种工作流。
    """
    # 获取当前工作流类型，默认为 test_design
    workflow_type = state.get("current_workflow") or "test_design"
    logger.info(f"执行工作流: {workflow_type}")
    
    # 确定当前阶段 (优先使用 current_stage_id)
    current_stage = state.get("current_stage_id") or state.get("workflow_stage")
    if not current_stage:
        current_stage = determine_stage(state, workflow_type)
    
    logger.info(f"当前阶段: {current_stage}")
    
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
    messages = [SystemMessage(content=system_prompt)]
    for msg in state.get("messages", []):
        messages.append(msg)
    
    # 调用 LLM
    try:
        response = llm.model.invoke(messages)
        response_content = response.content
        ai_message = AIMessage(content=response_content)
        
        # 更新消息历史
        new_messages = list(state.get("messages", []))
        new_messages.append(ai_message)
        
        # 尝试提取产出物
        new_artifacts = dict(artifacts)
        artifact_key, artifact_content = extract_artifact_from_response(response_content, current_stage, workflow_type)
        if artifact_key and artifact_content:
            new_artifacts[artifact_key] = artifact_content
            logger.info(f"提取产出物: {artifact_key} ({len(artifact_content)} 字符)")
        
        # 返回更新后的状态
        return {
            **state,
            "messages": new_messages,
            "artifacts": new_artifacts,
            "workflow_stage": current_stage,
            "current_workflow": workflow_type, # 保持当前 workflow type
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

