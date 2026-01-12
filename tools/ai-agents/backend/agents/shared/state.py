"""
共享 State 模块

定义所有智能体共用的基础状态结构。
Lisa 和 Alex 智能体共用此模块中的基础定义。
"""

from typing import TypedDict, Annotated, Optional, List, Dict, Any
from langgraph.graph import add_messages
from langchain_core.messages import BaseMessage


class BaseAgentState(TypedDict):
    """
    智能体基础状态
    
    所有智能体（Lisa, Alex 等）共用的状态字段。
    各智能体可以继承此 TypedDict 并扩展特定字段。
    
    字段说明:
    - messages: 消息历史 (LangGraph Reducer - 自动合并消息)
    - current_workflow: 当前工作流 ID (如 "test_design", "product_design")
    - workflow_stage: 当前阶段 (如 "clarify", "elevator")
    - plan: 动态进度计划列表
    - current_stage_id: 当前活跃阶段 ID
    - artifacts: 产出物存储 (Markdown 格式)
    - artifact_templates: 产出物模板列表 (阶段与产出物的映射)
    - pending_clarifications: 待澄清问题列表
    - consensus_items: 已达成共识项
    """
    
    # 消息历史 (LangGraph Reducer - 自动合并消息)
    messages: Annotated[list[BaseMessage], add_messages]
    
    # 工作流控制
    current_workflow: Optional[str]
    workflow_stage: Optional[str]
    
    # 动态进度计划
    # 列表中的每个 item 结构:
    # {
    #     "id": "stage_id",
    #     "name": "阶段名称",
    #     "status": "pending" | "active" | "completed",
    #     "description": "阶段描述 (可选)"
    # }
    plan: List[Dict]
    current_stage_id: Optional[str]
    
    # 产出物存储 (Markdown 格式，支持 Mermaid)
    artifacts: Dict[str, str]
    
    # 产出物模板列表
    # 列表中的每个 item 结构:
    # {
    #     "stage_id": "阶段ID",
    #     "artifact_key": "产出物存储key",
    #     "name": "产出物显示名称"
    # }
    artifact_templates: List[Dict[str, str]]
    
    # 交互追踪
    pending_clarifications: List[str]
    consensus_items: List[Any]


def get_base_initial_state() -> Dict[str, Any]:
    """
    获取基础状态的初始值
    
    用于创建新会话时初始化状态。
    Plan 由 LLM 在首次响应时动态生成。
    
    Returns:
        dict: 初始化后的状态字典
    """
    return {
        "messages": [],
        "current_workflow": None,
        "workflow_stage": None,
        "plan": [],
        "current_stage_id": None,
        "artifacts": {},
        "artifact_templates": [],
        "pending_clarifications": [],
        "consensus_items": [],
    }


def clear_workflow_state(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    清空工作流相关状态
    
    当用户切换工作流时调用，保留消息历史但清空产出物。
    
    Args:
        state: 当前状态
        
    Returns:
        dict: 清空工作流状态后的新状态（不修改原对象）
    """
    return {
        **state,
        "current_workflow": None,
        "workflow_stage": None,
        "plan": [],
        "current_stage_id": None,
        "artifacts": {},
        "artifact_templates": [],
        "pending_clarifications": [],
        "consensus_items": [],
    }
