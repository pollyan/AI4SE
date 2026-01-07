"""
Lisa Prompts 模块

提供 Lisa 智能体的 Prompt 组件，支持模块化组合。
"""

from .shared import (
    LISA_IDENTITY,
    LISA_STYLE,
    LISA_PRINCIPLES,
    LISA_SKILLS,
    PROTOCOL_PANORAMA_FOCUS,
    PROTOCOL_TECH_SELECTION,
    RESPONSE_TEMPLATE,
)

from .intent_router import INTENT_ROUTING_PROMPT

__all__ = [
    # 共享组件
    "LISA_IDENTITY",
    "LISA_STYLE",
    "LISA_PRINCIPLES",
    "LISA_SKILLS",
    "PROTOCOL_PANORAMA_FOCUS",
    "PROTOCOL_TECH_SELECTION",
    "RESPONSE_TEMPLATE",
    # 意图路由
    "INTENT_ROUTING_PROMPT",
]
