"""
Alex State - LangGraph 状态定义

定义 Alex 智能体的核心状态结构。
"""

from typing import TypedDict, Annotated, Optional
from langgraph.graph import add_messages
from langchain_core.messages import BaseMessage


class AlexState(TypedDict):
    """
    Alex 智能体核心状态
    
    使用 LangGraph 管理：
    - 消息历史
    - 产出物存储 (虽然目前 Alex 主要是聊天，但保留此扩展性)
    """
    
    # 消息历史 (LangGraph Reducer - 自动合并消息)
    messages: Annotated[list[BaseMessage], add_messages]
    
    # 产出物存储 (可选)
    artifacts: dict[str, str]


def get_initial_state() -> AlexState:
    """
    获取 AlexState 的初始状态
    """
    return {
        "messages": [],
        "artifacts": {},
    }
