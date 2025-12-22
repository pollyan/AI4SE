"""
LangGraph 图定义

定义智能体的工作流图：
- create_alex_graph: Alex 需求分析师的图（纯提示词驱动）
- create_lisa_graph: Lisa Song 测试分析师的图（向后兼容）
- create_lisa_v2_graph: Lisa v2 图（LangGraph 驱动，MVP）

Alex 使用最简单的流程：START → chat → END
Lisa v2 使用结构化工作流：意图识别 → 工作流子图
"""

import logging
from langgraph.graph import StateGraph, START, END

from .state import AssistantState
from .nodes import chat_node

# 导入 Lisa v2
from .lisa_v2.graph import create_lisa_v2_graph

logger = logging.getLogger(__name__)


def create_alex_graph(checkpointer=None):
    """
    创建 Alex 需求分析师的图
    
    第一阶段：纯提示词驱动
    图结构：START → chat → END
    
    所有需求分析逻辑（澄清、共识提取、文档生成）都在 
    Bundle 提示词中由 LLM 自动完成。
    
    Args:
        checkpointer: 可选的检查点保存器，用于状态持久化
        
    Returns:
        编译后的图
    """
    logger.info("创建 Alex 需求分析师图（纯提示词模式）")
    
    # 创建状态图
    builder = StateGraph(AssistantState)
    
    # 添加节点
    builder.add_node("chat", chat_node)
    
    # 添加边：START → chat → END
    builder.add_edge(START, "chat")
    builder.add_edge("chat", END)
    
    # 编译图
    graph = builder.compile(checkpointer=checkpointer)
    
    logger.info("Alex 图创建完成")
    return graph


def create_lisa_graph(checkpointer=None):
    """
    创建 Lisa Song 测试分析师的图
    
    第一阶段：纯提示词驱动
    图结构：START → chat → END
    
    所有测试分析逻辑（策略规划、用例设计、文档生成）都在
    Bundle 提示词中由 LLM 自动完成。
    
    Args:
        checkpointer: 可选的检查点保存器，用于状态持久化
        
    Returns:
        编译后的图
    """
    logger.info("创建 Lisa Song 测试分析师图（纯提示词模式）")
    
    # 创建状态图
    builder = StateGraph(AssistantState)
    
    # 添加节点
    builder.add_node("chat", chat_node)
    
    # 添加边：START → chat → END
    builder.add_edge(START, "chat")
    builder.add_edge("chat", END)
    
    # 编译图
    graph = builder.compile(checkpointer=checkpointer)
    
    logger.info("Lisa 图创建完成")
    return graph


def get_graph_for_assistant(assistant_type: str, checkpointer=None, use_v2: bool = True):
    """
    根据智能体类型获取对应的图
    
    Args:
        assistant_type: 智能体类型（alex 或 lisa）
        checkpointer: 可选的检查点保存器
        use_v2: 是否使用 Lisa v2（LangGraph 驱动版本），默认启用
        
    Returns:
        编译后的图
    """
    if assistant_type == "alex":
        return create_alex_graph(checkpointer)
    elif assistant_type in ("lisa", "song"):  # 兼容旧名称
        if use_v2:
            logger.info("使用 Lisa v2（LangGraph 驱动）")
            return create_lisa_v2_graph(checkpointer)
        else:
            logger.info("使用 Lisa v1（纯提示词驱动，向后兼容）")
            return create_lisa_graph(checkpointer)
    else:
        raise ValueError(f"未知的智能体类型: {assistant_type}")
