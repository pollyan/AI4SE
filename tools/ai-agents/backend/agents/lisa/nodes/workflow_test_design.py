"""
Workflow Test Design Node - 测试设计工作流节点

处理测试设计工作流的核心逻辑，包括需求澄清、策略制定、用例编写和文档交付。
"""

import logging
from typing import Any, List, Dict

from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
from langgraph.config import get_stream_writer

from ..state import LisaState, ArtifactKeys
from ..prompts.workflows import build_workflow_prompt
from backend.agents.shared.artifact_summary import get_artifacts_summary
from ..prompts.artifacts import (
    ARTIFACT_CLARIFY_REQUIREMENTS,
    ARTIFACT_STRATEGY_BLUEPRINT,
    ARTIFACT_CASES_SET,
    ARTIFACT_DELIVERY_FINAL,
    ARTIFACT_REQ_REVIEW_RECORD
)

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


def get_artifact_template(key: str) -> str:
    """根据 Artifact Key 获取对应的 Markdown 模板"""
    if key == ArtifactKeys.TEST_DESIGN_REQUIREMENTS: return ARTIFACT_CLARIFY_REQUIREMENTS
    if key == ArtifactKeys.TEST_DESIGN_STRATEGY: return ARTIFACT_STRATEGY_BLUEPRINT
    if key == ArtifactKeys.TEST_DESIGN_CASES: return ARTIFACT_CASES_SET
    if key == ArtifactKeys.TEST_DESIGN_FINAL: return ARTIFACT_DELIVERY_FINAL
    if key == ArtifactKeys.REQ_REVIEW_RECORD: return ARTIFACT_REQ_REVIEW_RECORD
    return ""

def get_artifact_key_for_stage(stage: str, workflow_type: str) -> str | None:
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

def extract_artifact_from_response(response: str, stage: str, workflow_type: str) -> tuple[str, str]:
    """
    从 LLM 响应中提取产出物
    """
    artifact_key = get_artifact_key_for_stage(stage, workflow_type)
    if not artifact_key:
        return None, None
    
    # 简单的产出物提取逻辑：查找 Markdown 代码块
    # 增强产出物提取逻辑
    import re
    
    # 策略 1: 查找 markdown 代码块 (最优先)
    # pattern: ```(markdown)? ...content... ```
    matches = list(re.finditer(r'```(?:markdown)?\s*\n(.*?)```', response, re.DOTALL))
    
    if matches:
        # 遍历所有代码块，寻找最像产出物的一个
        # 优先特征：内容包含 "产出物" 或 "Artifact" 或 "Key"
        target_match = None
        for match in reversed(matches):
            content = match.group(1).strip()
            if content.startswith("#") and ("产出物" in content or "Artifact" in content or "Key" in content):
                target_match = match
                break
        
        # 如果没找到特定特征的，还是取最后一个
        if not target_match:
            target_match = matches[-1]
            
        content = target_match.group(1).strip()
        
        if content.startswith("#"):
            return artifact_key, content
            
    # 策略 2: 降级策略 - 直接查找以 # 开头的产出物标题 (如果 LLM 忘记打标签)
    # 假设产出物都在回答的最后部分
    # 我们查找最后一个 "# " 及其后的所有内容
    
    # 定义可能的标题特征，例如 "# 需求评审记录" 或 "# 测试策略蓝图"
    # 或者简单地查找最后一个一级标题 (支持 # 到 ######)
    header_matches = list(re.finditer(r'(^|\n)#{1,6}\s+(.*?)\n', response))
    if header_matches:
        last_header = header_matches[-1]
        start_index = last_header.start()
        # 如果是换行符开头，+1
        if response[start_index] == '\n':
            start_index += 1
            
        params_content = response[start_index:].strip()
        
        # 简单校验长度，避免提取到无关的小标题
        if len(params_content) > 50: 
            return artifact_key, params_content

    return None, None


def strip_artifact_block(response: str) -> str:
    """
    移除响应中的产出物代码块（用于显示）
    """
    import re
    
    # 策略 1: 移除 Markdown 块
    matches = list(re.finditer(r'```(?:markdown)?\s*\n(.*?)```', response, re.DOTALL))
    if matches:
        last_match = matches[-1]
        content = last_match.group(1).strip()
        if content.startswith("#"):
            start, end = last_match.span()
            return (response[:start] + response[end:]).strip()
            
    # 策略 2: 移除降级策略找到的内容
    header_matches = list(re.finditer(r'(^|\n)#{1,6}\s+(.*?)\n', response))
    if header_matches:
        last_header = header_matches[-1]
        start_index = last_header.start()
        if response[start_index] == '\n':
            start_index += 1
            
        # 确认这段内容看起来像产出物 (长度检查)
        candidate = response[start_index:].strip()
        if len(candidate) > 50:
            return response[:start_index].strip()
            
    return response

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
            "currentTask": f"正在处理 {current_stage} 阶段..."
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
    messages = [SystemMessage(content=system_prompt)]
    for msg in state.get("messages", []):
        messages.append(msg)
    
    # 调用 LLM
    try:
        response = llm.model.invoke(messages)
        response_content = response.content
        
        # DEBUG LOGGING - 使用 warning 级别确保可见
        logger.warning(f"LLM Response Content Length: {len(response_content)}")
        if len(response_content) > 500:
            logger.warning(f"LLM Response tail (500 chars): {response_content[-500:]}")
        else:
            logger.warning(f"LLM Response full: {response_content}")
            
        # 尝试提取产出物
        new_artifacts = dict(artifacts)
        artifact_key, artifact_content = extract_artifact_from_response(response_content, current_stage, workflow_type)
        
        logger.warning(f"Extraction Result - Key: {artifact_key}, Content Found: {bool(artifact_content)}")
        
        # 决定显示给用户的内容 (移除产出物代码块)
        display_content = response_content
        if artifact_key and artifact_content:
            new_artifacts[artifact_key] = artifact_content
            logger.info(f"提取产出物: {artifact_key} ({len(artifact_content)} 字符)")
            display_content = strip_artifact_block(response_content)
            
            # ════════════════════════════════════════════════════════════
            # 📍 推送产出物更新
            # ════════════════════════════════════════════════════════════
            writer({
                "type": "progress",
                "progress": {
                    "stages": plan,
                    "currentStageIndex": get_stage_index(plan, current_stage),
                    "currentTask": f"正在处理 {current_stage} 阶段...",
                    "artifacts": new_artifacts
                }
            })
            logger.info(f"StreamWriter 推送产出物: {artifact_key}")
            
        ai_message = AIMessage(content=display_content)
        
        # 更新消息历史
        new_messages = list(state.get("messages", []))
        new_messages.append(ai_message)
        
        # 返回更新后的状态 (包含 plan)
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

