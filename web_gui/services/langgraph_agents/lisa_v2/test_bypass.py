"""
最小化测试 - 绕过图直接返回响应
"""

from typing import AsyncIterator, Optional
from langchain_core.messages import HumanMessage, AIMessage

async def test_stream_response(user_message: str) -> AsyncIterator[str]:
    """
    最小化测试：不经过图，直接流式返回
    """
    response = f"[测试] 我收到了您的消息：{user_message}"
    
    # 模拟打字效果
    for char in response:
        yield char
        import asyncio
        await asyncio.sleep(0.01)
