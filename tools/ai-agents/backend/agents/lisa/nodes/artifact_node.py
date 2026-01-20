import logging
import json
from typing import Any, Dict, List
from langchain_core.messages import SystemMessage, AIMessage

from langgraph.config import get_stream_writer

from ..state import LisaState
from ..tools import update_artifact
from ..prompts.artifacts import ARTIFACT_UPDATE_PROMPT
from ...shared.progress import get_progress_info

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
    
    # [新增] 初始化模版注入逻辑 (Deterministic Initialization)
    # 如果是初始化阶段，直接构造工具调用而不经过 LLM，确保 100% 成功率
    templates = state.get("artifact_templates", [])
    current_template = next((t for t in templates if t.get("stage") == current_stage), None)
    
    mock_tool_calls_for_init = []
    
    if current_template:
        key = current_template["key"]
        if key not in artifacts:
            outline = current_template.get("outline", "")
            logger.info(f"ArtifactNode: DETECTED MISSING ARTIFACT {key}. Using deterministic initialization.")
            
            # 手动构造一个"虚拟"的 tool calls 列表
            mock_tool_calls_for_init = [{
                "name": "update_artifact",
                "args": {
                    "key": key,
                    "markdown_body": outline
                },
                "id": f"call_init_{current_stage}"
            }]

    # 3. 执行逻辑分叉
    tool_calls = []
    
    if mock_tool_calls_for_init:
        # A. 确定性初始化路径
        tool_calls = mock_tool_calls_for_init
    else:
        # B. 正常的 LLM 生成路径
        # 绑定工具并强制调用
        llm_with_tools = llm.model.bind_tools(
            [update_artifact],
            tool_choice={"type": "function", "function": {"name": "update_artifact"}}
        )

        # 获取当前阶段对应的 artifact key
        current_template = next((t for t in templates if t.get("stage") == current_stage), None)
        artifact_key = current_template["key"] if current_template else f"{current_stage}_output"

        # 构建 Prompt
        artifact_prompt_text = ARTIFACT_UPDATE_PROMPT.format(
            current_stage=current_stage,
            artifact_key=artifact_key
        )
        
        # 使用 state 中的 messages + 指令
        messages = state["messages"] + [SystemMessage(content=artifact_prompt_text)]
        
        try:
            response = llm_with_tools.invoke(messages)
            tool_calls = response.tool_calls
        except Exception as e:
            logger.error(f"Artifact LLM call failed: {e}", exc_info=True)
            return state

    # 4. 处理工具调用
    # tool_calls 已经在上面被正确赋值了 (无论来自 mock 还是 response)
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
            # 使用 get_progress_info 确保格式统一 (包含 artifactProgress)
            temp_state = {
                **state,
                "artifacts": new_artifacts
            }
            progress_info = get_progress_info(temp_state)
            
            if progress_info:
                # DEBUG: Log progress info details
                logger.info(f"ArtifactNode: Generated progress info. Completed keys: {progress_info.get('artifactProgress', {}).get('completed')}")
                # 覆盖当前任务描述，显示具体更新动作
                progress_info["currentTask"] = f"已更新产出物: {key}"
                
                writer({
                    "type": "progress",
                    "progress": progress_info
                })
                logger.info("ArtifactNode: Sent progress event via writer")
            
    return {**state, "artifacts": new_artifacts}
