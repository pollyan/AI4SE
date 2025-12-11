"""
智能体状态模型定义

使用 TypedDict 定义 LangGraph 状态模式，支持:
- 消息历史管理（自动追加）
- 会话元信息
- 分析上下文
- 控制流标志
"""

from typing import TypedDict, Annotated, Sequence, Literal, Optional, Dict, Any
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AssistantState(TypedDict):
    """
    智能体共用状态模型
    
    用于 Alex（需求分析师）和 Lisa（测试分析师）智能体的图状态管理。
    通过 add_messages reducer，新消息会自动追加到历史中。
    """
    
    # ===== 消息历史 =====
    # 使用 add_messages reducer，新消息自动追加，支持流式处理
    messages: Annotated[Sequence[BaseMessage], add_messages]
    
    # ===== 会话元信息 =====
    session_id: str                                    # 会话唯一标识
    assistant_type: Literal["alex", "lisa"]            # 智能体类型
    current_stage: str                                 # 当前分析阶段
    project_name: Optional[str]                        # 项目名称
    
    # ===== 分析上下文 =====
    # 共识内容：从对话中提取的已确认需求要点
    consensus_content: Dict[str, Any]
    # AI分析上下文：智能体内部使用的分析状态
    analysis_context: Dict[str, Any]
    
    # ===== 控制流标志 =====
    # 是否需要提取共识（Alex 专用）
    should_extract_consensus: bool
    # 是否需要生成文档
    should_generate_document: bool
    # 当前回合是否完成
    is_turn_complete: bool
    
    # ===== 错误处理 =====
    error_message: Optional[str]


def create_initial_state(
    session_id: str,
    assistant_type: Literal["alex", "lisa"],
    project_name: Optional[str] = None
) -> AssistantState:
    """
    创建初始状态
    
    Args:
        session_id: 会话 ID
        assistant_type: 智能体类型（alex 或 lisa）
        project_name: 可选的项目名称
        
    Returns:
        初始化的状态字典
    """
    return AssistantState(
        messages=[],
        session_id=session_id,
        assistant_type=assistant_type,
        current_stage="initial",
        project_name=project_name,
        consensus_content={},
        analysis_context={},
        should_extract_consensus=False,
        should_generate_document=False,
        is_turn_complete=False,
        error_message=None,
    )


# Alex 分析阶段定义
ALEX_STAGES = {
    "initial": "初始阶段 - 了解用户需求",
    "clarification": "澄清阶段 - 深入挖掘需求细节",
    "consensus": "共识阶段 - 确认需求理解",
    "documentation": "文档阶段 - 生成需求文档",
}

# Lisa 分析阶段定义
LISA_STAGES = {
    "initial": "初始阶段 - 了解测试目标",
    "analysis": "分析阶段 - 评估测试策略",
    "design": "设计阶段 - 设计测试用例",
    "documentation": "文档阶段 - 生成测试文档",
}
