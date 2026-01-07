"""
Intent Router Node - 意图路由节点

使用 LLM 进行语义意图识别，将用户请求路由到对应工作流。
"""

import json
import logging
from typing import Any

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from ..state import LisaState
from ..prompts import INTENT_ROUTING_PROMPT

logger = logging.getLogger(__name__)



def format_messages_for_context(messages: list, max_messages: int = 10) -> str:
    """格式化消息列表供上下文使用"""
    recent = messages[-max_messages:] if len(messages) > max_messages else messages
    
    formatted = []
    for msg in recent:
        role = "用户" if isinstance(msg, HumanMessage) else "Lisa"
        content = msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
        formatted.append(f"[{role}]: {content}")
    
    return "\n".join(formatted) if formatted else "(无历史消息)"


def summarize_artifacts(artifacts: dict) -> str:
    """生成产出物摘要"""
    if not artifacts:
        return "(无产出物)"
    
    summaries = []
    for key, value in artifacts.items():
        length = len(value) if value else 0
        summaries.append(f"- {key}: {length} 字符")
    
    return "\n".join(summaries)


def intent_router_node(state: LisaState, llm: Any) -> LisaState:
    """
    意图路由节点
    
    使用 LLM 分析用户意图，更新 state 中的工作流控制字段。
    
    Args:
        state: 当前状态
        llm: LLM 实例
        
    Returns:
        LisaState: 更新后的状态
    """
    logger.info("执行意图路由...")
    
    # 获取用户最新消息
    messages = state.get("messages", [])
    if not messages:
        logger.warning("无用户消息，跳过路由")
        return state
    
    # 获取最新的用户消息
    last_user_message = None
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            last_user_message = msg.content
            break
    
    if not last_user_message:
        logger.warning("未找到用户消息，跳过路由")
        return state
    
    # 构建上下文
    recent_messages = format_messages_for_context(messages)
    artifacts_summary = summarize_artifacts(state.get("artifacts", {}))
    
    # 构建系统 Prompt
    system_prompt = INTENT_ROUTING_PROMPT.format(
        current_workflow=state.get("current_workflow", "未开始"),
        workflow_stage=state.get("workflow_stage", "无"),
        artifacts_summary=artifacts_summary,
        recent_messages=recent_messages,
    )
    
    # 调用 LLM - 使用 SystemMessage + HumanMessage 格式确保兼容性
    try:
        response = llm.model.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"请分析上述对话中用户的意图，用户的最新消息是：\n\n{last_user_message}")
        ])
        response_text = response.content
        
        # 解析 JSON
        # 尝试提取 JSON 块
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            json_text = response_text[json_start:json_end].strip()
        elif "{" in response_text:
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            json_text = response_text[json_start:json_end]
        else:
            json_text = response_text
        
        result = json.loads(json_text)
        intent = result.get("intent", "UNCLEAR")
        confidence = result.get("confidence", 0.0)
        
        logger.info(f"意图识别结果: {intent} (置信度: {confidence})")
        
        # 根据意图更新状态
        if intent in ["START_TEST_DESIGN", "CONTINUE", "SUPPLEMENT"]:
            return {
                **state,
                "current_workflow": "test_design",
            }
        else:
            # UNCLEAR - 保持当前状态
            return state
            
    except Exception as e:
        logger.error(f"意图路由失败: {e}")
        # 失败时默认继续当前工作流或进入澄清
        if state.get("current_workflow"):
            return state
        return state
