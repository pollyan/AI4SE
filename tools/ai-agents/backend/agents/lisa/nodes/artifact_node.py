import logging
import json
from typing import Any, Dict, List
from langchain_core.messages import SystemMessage, AIMessage

from langgraph.config import get_stream_writer

from ..state import LisaState
from ..tools import update_artifact

logger = logging.getLogger(__name__)

def artifact_node(state: LisaState, llm: Any) -> LisaState:
    """
    产出物更新节点 (Artifact Node)
    
    负责：
    1. 强制调用 update_artifact 工具
    2. 执行工具调用并更新 State 中的 artifacts
    3. 推送 tool-call 和 progress 事件
    """
    logger.info("Entering ArtifactNode...")
    
    current_stage = state.get("current_stage_id", "clarify")
    artifacts = state.get("artifacts", {})
    plan = state.get("plan", [])
    
    writer = get_stream_writer()
    
    # 1. 绑定工具并强制调用
    llm_with_tools = llm.model.bind_tools(
        [update_artifact],
        tool_choice={"type": "function", "function": {"name": "update_artifact.name"}} # .name might not work if tool not compiled? checking...
        # Safer to use literal name
    )
    # Re-bind with literal name to be safe
    llm_with_tools = llm.model.bind_tools(
        [update_artifact],
        tool_choice={"type": "function", "function": {"name": "update_artifact"}}
    )

    # 2. 构建 Artifact 专用 Prompt
    # 简单起见，提示模型使用工具更新当前阶段的产出物
    artifact_prompt = f"""
    Internal System Instruction:
    You are in the Artifact Update Phase.
    You MUST call the `update_artifact` tool to save the latest content for stage '{current_stage}'.
    
    Use the context from previous messages to generate the full markdown content.
    """
    
    # 使用 state 中的 messages + 指令
    messages = state["messages"] + [SystemMessage(content=artifact_prompt)]
    
    # 3. 调用 LLM
    try:
        response = llm_with_tools.invoke(messages)
    except Exception as e:
        logger.error(f"Artifact LLM call failed: {e}", exc_info=True)
        return state

    # 4. 处理工具调用
    tool_calls = response.tool_calls
    if not tool_calls:
        logger.warning("ArtifactNode: No tool calls generated!")
        return state
        
    new_artifacts = dict(artifacts)
    
    for tool_call in tool_calls:
        # 验证工具名称
        if tool_call["name"] != "update_artifact":
            continue
            
        args = tool_call["args"]
        key = args.get("key")
        content = args.get("markdown_body")
        
        if key and content:
            # 更新本地状态
            new_artifacts[key] = content
            logger.info(f"ArtifactNode: Updated artifact {key}")
            
            # 推送 tool-call 事件 (用于前端展示 "正在更新...")
            writer({
                "type": "tool-call",
                "toolCallId": tool_call.get("id", "call_unknown"),
                "toolName": "update_artifact",
                "args": {"key": key} # 仅发送 key，不发送全文以免冗余
            })
            
            # 推送进度更新 (前端根据此更新右侧面板)
            # 计算 stage_index
            stage_index = next((i for i, s in enumerate(plan) if s["id"] == current_stage), 0)
            
            writer({
                "type": "progress",
                "progress": {
                    "stages": plan,
                    "currentStageIndex": stage_index,
                    "currentTask": f"已更新产出物: {key}",
                    "artifacts": new_artifacts
                }
            })
            
    return {**state, "artifacts": new_artifacts}
