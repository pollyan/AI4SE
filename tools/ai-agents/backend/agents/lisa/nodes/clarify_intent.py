"""
Clarify Intent Node - 意图澄清节点

当用户意图不明确时，请求用户提供更多信息。
"""

import logging
from typing import Any

from langchain_core.messages import AIMessage

from ..state import LisaState

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
    
    clarify_message = AIMessage(content="""
您好！我是 **Lisa Song**，您的首席测试领域专家。

请问您本次的任务更接近以下哪一种？

- **A. 新需求/功能测试设计**: 为一个全新的功能或需求设计完整的测试方案。
- **B. 需求评审与可测试性分析**: 审查需求文档，寻找逻辑漏洞、模糊点和不可测试之处。
- **C. 生产缺陷分析与回归策略**: 针对一个已发现的线上问题，进行根因分析并设计回归测试。
- **D. 专项测试策略规划**: 聚焦于非功能性领域，如性能、安全或自动化，进行策略规划。
- **E. 产品测试现状评估**: 对现有的测试现状进行分析、审查和优化建议。
- **F. 其他测试任务**: 上述场景都不完全匹配，需要进行更开放的探讨或咨询。

请告诉我您的需求，我会为您提供专业的测试指导。
""".strip())
    
    # 添加澄清消息到历史
    new_messages = list(state.get("messages", []))
    new_messages.append(clarify_message)
    
    return {
        **state,
        "messages": new_messages,
    }
