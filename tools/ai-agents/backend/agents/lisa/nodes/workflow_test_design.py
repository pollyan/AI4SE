"""
Workflow Test Design Node - 测试设计工作流节点

处理测试设计工作流的核心逻辑，包括需求澄清、策略制定、用例编写和文档交付。
"""

import logging
from typing import Any

from langchain_core.messages import SystemMessage, AIMessage, HumanMessage

from ..state import LisaState, ArtifactKeys
from ..prompts.workflows import build_workflow_prompt

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
        ArtifactKeys.TEST_DESIGN_REQUIREMENTS: "需求分析文档",
        ArtifactKeys.TEST_DESIGN_STRATEGY: "测试策略蓝图",
        ArtifactKeys.TEST_DESIGN_CASES: "测试用例集",
        ArtifactKeys.TEST_DESIGN_FINAL: "最终测试设计文档",
    }
    
    for key, value in artifacts.items():
        name = key_names.get(key, key)
        length = len(value) if value else 0
        summaries.append(f"- {name}: {length} 字符")
    
    return "\n".join(summaries) if summaries else "(无)"


def determine_stage(state: LisaState) -> str:
    """
    根据产出物确定当前阶段
    
    阶段转换逻辑：
    - 无产出物 → clarify
    - 有 requirements → strategy
    - 有 strategy → cases
    - 有 cases → delivery
    - 有 final → delivery (完成)
    """
    artifacts = state.get("artifacts", {})
    
    if ArtifactKeys.TEST_DESIGN_FINAL in artifacts:
        return "delivery"
    elif ArtifactKeys.TEST_DESIGN_CASES in artifacts:
        return "delivery"  # cases 完成后进入 delivery
    elif ArtifactKeys.TEST_DESIGN_STRATEGY in artifacts:
        return "cases"
    elif ArtifactKeys.TEST_DESIGN_REQUIREMENTS in artifacts:
        return "strategy"
    else:
        return "clarify"


def extract_artifact_from_response(response: str, stage: str) -> tuple[str, str]:
    """
    从 LLM 响应中提取产出物
    
    Args:
        response: LLM 响应内容
        stage: 当前阶段
        
    Returns:
        (artifact_key, artifact_content) 或 (None, None)
    """
    # 阶段对应的产出物 Key
    stage_to_artifact = {
        "clarify": ArtifactKeys.TEST_DESIGN_REQUIREMENTS,
        "strategy": ArtifactKeys.TEST_DESIGN_STRATEGY,
        "cases": ArtifactKeys.TEST_DESIGN_CASES,
        "delivery": ArtifactKeys.TEST_DESIGN_FINAL,
    }
    
    artifact_key = stage_to_artifact.get(stage)
    if not artifact_key:
        return None, None
    
    # 简单的产出物提取逻辑：
    # 查找 Markdown 代码块或特定标题
    # 这里暂时返回完整响应作为产出物（后续可以优化提取逻辑）
    if "```markdown" in response:
        start = response.find("```markdown") + 11
        end = response.find("```", start)
        if end > start:
            return artifact_key, response[start:end].strip()
    
    # 如果响应中包含产出物相关的标题，可以考虑提取
    # 暂时不自动提取，由 LLM 自己管理
    return None, None


# ═══════════════════════════════════════════════════════════════════════════════
# 主节点
# ═══════════════════════════════════════════════════════════════════════════════

def workflow_test_design_node(state: LisaState, llm: Any) -> LisaState:
    """
    测试设计工作流节点
    
    处理测试设计的完整流程，包括需求澄清、策略制定、用例编写和文档交付。
    通过 Prompt 驱动，LLM 自主管理阶段转换和产出物生成。
    
    Args:
        state: 当前状态
        llm: LLM 实例
        
    Returns:
        LisaState: 更新后的状态
    """
    logger.info("执行测试设计工作流...")
    
    # 确定当前阶段
    current_stage = state.get("workflow_stage")
    if not current_stage:
        current_stage = determine_stage(state)
    
    logger.info(f"当前阶段: {current_stage}")
    
    # 构建上下文
    artifacts = state.get("artifacts", {})
    artifacts_summary = get_artifacts_summary(artifacts)
    pending = state.get("pending_clarifications", [])
    consensus = state.get("consensus_items", [])
    
    # 使用新的 Prompt 构建函数
    system_prompt = build_workflow_prompt(
        stage=current_stage,
        artifacts_summary=artifacts_summary,
        pending_clarifications=", ".join(pending) if pending else "(无)",
        consensus_count=len(consensus),
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
        
        # 尝试提取产出物（可选）
        new_artifacts = dict(artifacts)
        artifact_key, artifact_content = extract_artifact_from_response(response_content, current_stage)
        if artifact_key and artifact_content:
            new_artifacts[artifact_key] = artifact_content
            logger.info(f"提取产出物: {artifact_key} ({len(artifact_content)} 字符)")
        
        # 返回更新后的状态
        return {
            **state,
            "messages": new_messages,
            "artifacts": new_artifacts,
            "workflow_stage": current_stage,
            "current_workflow": "test_design",
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

