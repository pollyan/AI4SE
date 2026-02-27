"""
Clarify Intent Node - 意图澄清节点

当用户意图不明确时，请求用户提供更多信息。
"""

import logging
from typing import Any

from langchain_core.messages import AIMessage

from ..state import LisaState
from ..prompts import CLARIFY_INTENT_MESSAGE

logger = logging.getLogger(__name__)


def clarify_intent_node(state: LisaState, llm: Any) -> LisaState:
    """
    意图澄清节点
    
    当意图不明确时，生成澄清请求。
    
    Args:
        state: 当前状态
        llm: LLM 实例
        
    Returns:
        LisaState: 更新后的状态，包含澄清请求消息
    """
    logger.info("执行意图澄清...")
    
    # 优先使用动态识别到的澄清问题
    dynamic_question = state.get("clarification")
    content = dynamic_question if dynamic_question else CLARIFY_INTENT_MESSAGE
    
    clarify_message = AIMessage(content=content)
    
    # 添加澄清消息到历史
    new_messages = list(state.get("messages", []))
    new_messages.append(clarify_message)
    
    return {
        **state,
        "messages": new_messages,
    }

