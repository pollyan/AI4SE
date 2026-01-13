"""
共享 Checkpointer 模块

提供 LangGraph 状态持久化的 Checkpointer 实例。
Lisa 和 Alex 智能体共用此模块。

使用 InMemorySaver 实现内存级持久化：
- 服务运行期间保持会话状态
- 服务重启后状态丢失（适用于 Demo 场景）
- 如需持久化到数据库，可替换为 PostgresSaver
"""

from langgraph.checkpoint.memory import MemorySaver

# 单例模式，整个应用共享一个 checkpointer
_checkpointer = None


def get_checkpointer() -> MemorySaver:
    """
    获取共享的 Checkpointer 实例
    
    使用单例模式确保所有智能体共享同一个 checkpointer，
    这样可以统一管理所有会话的状态。
    
    Returns:
        MemorySaver: 内存级 checkpointer 实例
    """
    global _checkpointer
    if _checkpointer is None:
        _checkpointer = MemorySaver()
    return _checkpointer


def reset_checkpointer() -> None:
    """
    重置 Checkpointer（仅用于测试）
    
    清除所有会话状态，创建新的 checkpointer 实例。
    """
    global _checkpointer
    _checkpointer = None
