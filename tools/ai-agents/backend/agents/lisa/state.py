"""
Lisa State - LangGraph 状态定义

定义 Lisa 智能体的核心状态结构，用于在图节点间传递和更新状态。
继承自 BaseAgentState 共享基础字段。
"""

from typing import Literal, Dict, Union, Any

from ..shared.state import BaseAgentState
from .artifact_models import RequirementDoc, DesignDoc, CaseDoc, DeliveryDoc


# 工作流阶段定义
WorkflowStage = Literal["clarify", "strategy", "cases", "delivery"]

# 工作流类型定义 (目前仅支持测试设计)
WorkflowType = Literal["test_design"]


class LisaState(BaseAgentState):
    """
    Lisa 智能体核心状态

    继承自 BaseAgentState，包含所有智能体共用字段：
    - messages: 消息历史 (LangGraph Reducer)
    - current_workflow: 当前工作流
    - workflow_stage: 工作流阶段
    - plan: 动态进度计划
    - current_stage_id: 当前阶段 ID
    - artifacts: 产出物存储 (Markdown)
    - artifact_templates: 产出物模板列表
    - pending_clarifications: 待澄清问题
    - clarification: 当前意图澄清消息
    - consensus_items: 已达成共识项

    Lisa 特有字段可在此扩展。
    """

    # 覆盖 artifacts 类型，使其支持结构化对象
    artifacts: Dict[str, Union[RequirementDoc, DesignDoc, CaseDoc, DeliveryDoc, Any]]


def get_initial_state() -> LisaState:
    """
    获取 LisaState 的初始状态

    用于创建新会话时初始化状态。
    Plan 由 LLM 在首次响应时动态生成。

    Returns:
        LisaState: 初始化后的状态字典
    """
    # 使用共享模块的基础初始状态
    from ..shared.state import get_base_initial_state

    # 注意: get_base_initial_state 返回的是 Dict[str, Any]，需要转型
    # 且确保包含 LisaState 特有的字段
    base_state = get_base_initial_state()
    return base_state  # type: ignore


def clear_workflow_state(state: LisaState) -> LisaState:
    """
    清空工作流相关状态

    当用户切换工作流时调用，保留消息历史但清空产出物。

    Args:
        state: 当前状态

    Returns:
        LisaState: 清空工作流状态后的新状态
    """
    # 使用共享模块的清空函数
    from ..shared.state import clear_workflow_state as base_clear

    return base_clear(state)  # type: ignore


# Artifact 命名常量
class ArtifactKeys:
    """产出物 Key 常量定义"""

    # 测试设计工作流
    TEST_DESIGN_REQUIREMENTS = "test_design_requirements"
    TEST_DESIGN_STRATEGY = "test_design_strategy"
    TEST_DESIGN_CASES = "test_design_cases"
    TEST_DESIGN_FINAL = "test_design_final"

    # 需求评审工作流
    REQ_REVIEW_RECORD = "req_review_record"  # 需求评审记录
    REQ_REVIEW_RISK = "req_review_risk"  # 风险评估
    REQ_REVIEW_REPORT = "req_review_report"  # 最终报告
