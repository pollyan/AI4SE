"""
Workflow Product Design Node - 产品设计工作流节点

处理产品设计工作流的核心逻辑，包括电梯演讲、用户画像、用户旅程和 BRD 生成。
"""

import logging
from typing import Any

from langchain_core.messages import SystemMessage, AIMessage

from ..state import AlexState, ArtifactKeys
from ..prompts.workflows.product_design import build_product_design_prompt
from backend.agents.shared.progress_utils import (
    parse_structured_json,
    extract_plan_from_structured,
    extract_artifacts_from_structured,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════════════════════════════════

def get_artifacts_summary(artifacts: dict) -> str:
    """生成产出物摘要"""
    if not artifacts:
        return "(无)"
    
    summaries = []
    key_names = {
        ArtifactKeys.PRODUCT_ELEVATOR: "电梯演讲 (价值定位)",
        ArtifactKeys.PRODUCT_PERSONA: "用户画像分析",
        ArtifactKeys.PRODUCT_JOURNEY: "用户旅程地图",
        ArtifactKeys.PRODUCT_BRD: "业务需求文档 (BRD)",
    }
    
    for key, value in artifacts.items():
        name = key_names.get(key, key)
        length = len(value) if value else 0
        summaries.append(f"- {name}: {length} 字符")
    
    return "\n".join(summaries) if summaries else "(无)"


def determine_stage(state: AlexState) -> str:
    """
    根据产出物确定当前阶段
    
    阶段转换逻辑：
    - 无产出物 → elevator
    - 有 elevator → persona
    - 有 persona → journey
    - 有 journey → brd
    - 有 brd → brd (完成)
    """
    artifacts = state.get("artifacts", {})
    
    # 逆序检查完成状态
    if ArtifactKeys.PRODUCT_BRD in artifacts:
        return "brd"
    elif ArtifactKeys.PRODUCT_JOURNEY in artifacts:
        return "brd"  # journey 完成后进入 brd
    elif ArtifactKeys.PRODUCT_PERSONA in artifacts:
        return "journey"
    elif ArtifactKeys.PRODUCT_ELEVATOR in artifacts:
        return "persona"
    else:
        return "elevator"


def extract_artifact_from_response(response: str, stage: str) -> tuple[str, str]:
    """
    从 LLM 响应中提取产出物
    """
    # 阶段对应的产出物 Key
    stage_to_artifact = {
        "elevator": ArtifactKeys.PRODUCT_ELEVATOR,
        "persona": ArtifactKeys.PRODUCT_PERSONA,
        "journey": ArtifactKeys.PRODUCT_JOURNEY,
        "brd": ArtifactKeys.PRODUCT_BRD,
    }
    
    artifact_key = stage_to_artifact.get(stage)
    if not artifact_key:
        return None, None
    
    # 产出物提取逻辑：查找 Markdown 代码块
    if "```markdown" in response:
        start = response.find("```markdown") + 11
        end = response.find("```", start)
        if end > start:
            return artifact_key, response[start:end].strip()
            
    return None, None


# ═══════════════════════════════════════════════════════════════════════════════
# 主节点
# ═══════════════════════════════════════════════════════════════════════════════

def workflow_product_design_node(state: AlexState, llm: Any) -> AlexState:
    """
    产品设计工作流节点
    """
    logger.info("执行 Alex 产品设计工作流...")
    
    workflow_type = "product_design"
    
    # 确定当前阶段
    current_stage = state.get("current_stage_id") or state.get("workflow_stage")
    if not current_stage:
        current_stage = determine_stage(state)
    
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
    
    # 构建 Prompt
    system_prompt = build_product_design_prompt(
        stage=current_stage,
        artifacts_summary=artifacts_summary,
        pending_clarifications=", ".join(pending) if pending else "(无)",
        consensus_count=len(consensus),
        plan_context=plan_context,
    )
    
    # 构建消息列表
    messages = [SystemMessage(content=system_prompt)]
    # 添加历史消息
    messages.extend(state.get("messages", []))
    
    # 调用 LLM
    try:
        response = llm.model.invoke(messages)
        response_content = response.content
        ai_message = AIMessage(content=response_content)
        
        # 更新消息历史
        new_messages = list(state.get("messages", []))
        new_messages.append(ai_message)
        
        # --- 解析结构化输出 ---
        new_artifacts = dict(artifacts)
        new_plan = state.get("plan", [])
        new_stage = current_stage
        
        # 1. 尝试 JSON 解析
        structured_data, _ = parse_structured_json(response_content)
        
        if structured_data:
            # 提取 Plan
            parsed_plan = extract_plan_from_structured(structured_data)
            if parsed_plan:
                new_plan = parsed_plan
                new_stage = structured_data.get("current_stage_id") or new_stage
                logger.info(f"JSON Plan 解析成功, Stage: {new_stage}")
            
            # 提取 Artifacts
            _, artifacts_dict = extract_artifacts_from_structured(structured_data)
            if artifacts_dict:
                new_artifacts.update(artifacts_dict)
                logger.info(f"JSON Artifacts 解析成功: {list(artifacts_dict.keys())}")
                
        else:
            # 2. Fallback: 尝试旧的提取逻辑 (兼容 Markdown 代码块)
            artifact_key, artifact_content = extract_artifact_from_response(response_content, current_stage)
            if artifact_key and artifact_content:
                new_artifacts[artifact_key] = artifact_content
                logger.info(f"Markdown Artifact 提取成功: {artifact_key}")
        
        # 返回更新后的状态
        return {
            **state,
            "messages": new_messages,
            "artifacts": new_artifacts,
            "plan": new_plan,
            "workflow_stage": new_stage,
            "current_stage_id": new_stage,
            "current_workflow": workflow_type,
        }
        
    except Exception as e:
        logger.error(f"产品设计工作流执行失败: {e}")
        error_message = AIMessage(content=f"抱歉，遇到了一些问题：{str(e)}")
        new_messages = list(state.get("messages", []))
        new_messages.append(error_message)
        
        return {
            **state,
            "messages": new_messages,
        }
