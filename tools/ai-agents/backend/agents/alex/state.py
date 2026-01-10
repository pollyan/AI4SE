"""
Alex State - LangGraph 状态定义

定义 Alex 智能体的核心状态结构。
"""

from typing import TypedDict, Annotated, Optional, List, Dict
from langgraph.graph import add_messages
from langchain_core.messages import BaseMessage


class ArtifactKeys:
    """Alex 产出物 Key 定义"""
    # 产品设计工作流
    PRODUCT_ELEVATOR = "product_elevator"      # 电梯演讲
    PRODUCT_PERSONA = "product_persona"        # 用户画像
    PRODUCT_JOURNEY = "product_journey"        # 用户旅程
    PRODUCT_BRD = "product_brd"                # BRD文档


class AlexState(TypedDict):
    """
    Alex 智能体核心状态
    """
    
    # 消息历史 (LangGraph Reducer)
    messages: Annotated[list[BaseMessage], add_messages]
    
    # 工作流控制
    current_workflow: Optional[str]  # 当前工作流 ID (如 "product_design")
    workflow_stage: Optional[str]    # 当前阶段 (如 "elevator")
    plan: List[Dict]                 # 动态进度计划
    current_stage_id: Optional[str]  # 当前活跃阶段 ID
    
    # 产出物与上下文
    artifacts: dict[str, str]        # 产出物内容
    pending_clarifications: List[str]# 待澄清问题
    consensus_items: List[str]       # 已达成共识项


def get_initial_state() -> AlexState:
    """
    获取 AlexState 的初始状态
    """
    return {
        "messages": [],
        "current_workflow": None,
        "workflow_stage": None,
        "plan": [],
        "current_stage_id": None,
        "artifacts": {},
        "pending_clarifications": [],
        "consensus_items": [],
    }
