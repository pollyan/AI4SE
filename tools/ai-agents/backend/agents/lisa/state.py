"""
Lisa State - LangGraph 状态定义

定义 Lisa 智能体的核心状态结构，用于在图节点间传递和更新状态。
"""

from typing import TypedDict, Optional, Literal, Annotated
from langgraph.graph import add_messages
from langchain_core.messages import BaseMessage


# 工作流阶段定义
WorkflowStage = Literal["clarify", "strategy", "cases", "delivery"]

# 工作流类型定义 (目前仅支持测试设计)
WorkflowType = Literal["test_design"]


class LisaState(TypedDict):
    """
    Lisa 智能体核心状态
    
    用于在 LangGraph 图节点间传递状态，包含：
    - 消息历史
    - 工作流控制
    - 产出物存储
    - 交互追踪
    """
    
    # ═══════════════════════════════════════════════════════════
    # 消息历史 (LangGraph Reducer - 自动合并消息)
    # ═══════════════════════════════════════════════════════════
    messages: Annotated[list[BaseMessage], add_messages]
    
    # ═══════════════════════════════════════════════════════════
    # 工作流控制
    # ═══════════════════════════════════════════════════════════
    current_workflow: Optional[WorkflowType]
    workflow_stage: Optional[WorkflowStage]
    
    # ═══════════════════════════════════════════════════════════
    # 产出物存储 (Markdown 格式，支持 Mermaid)
    # ═══════════════════════════════════════════════════════════
    # 命名规范:
    #   - test_design_requirements: 需求分析文档
    #   - test_design_strategy: 测试策略蓝图
    #   - test_design_cases: 测试用例集
    #   - test_design_final: 最终测试设计文档
    artifacts: dict[str, str]
    
    # ═══════════════════════════════════════════════════════════
    # 交互追踪
    # ═══════════════════════════════════════════════════════════
    pending_clarifications: list[str]  # 待澄清问题列表
    consensus_items: list[dict]        # [{"question": "...", "answer": "..."}]


def get_initial_state() -> LisaState:
    """
    获取 LisaState 的初始状态
    
    用于创建新会话时初始化状态。
    
    Returns:
        LisaState: 初始化后的状态字典
    """
    return {
        "messages": [],
        "current_workflow": None,
        "workflow_stage": None,
        "artifacts": {},
        "pending_clarifications": [],
        "consensus_items": [],
    }


def clear_workflow_state(state: LisaState) -> LisaState:
    """
    清空工作流相关状态
    
    当用户切换工作流时调用，保留消息历史但清空产出物。
    
    Args:
        state: 当前状态
        
    Returns:
        LisaState: 清空工作流状态后的新状态
    """
    return {
        **state,
        "current_workflow": None,
        "workflow_stage": None,
        "artifacts": {},
        "pending_clarifications": [],
        "consensus_items": [],
    }


# Artifact 命名常量
class ArtifactKeys:
    """产出物 Key 常量定义"""
    
    # 测试设计工作流
    TEST_DESIGN_REQUIREMENTS = "test_design_requirements"
    TEST_DESIGN_STRATEGY = "test_design_strategy"
    TEST_DESIGN_CASES = "test_design_cases"
    TEST_DESIGN_FINAL = "test_design_final"
