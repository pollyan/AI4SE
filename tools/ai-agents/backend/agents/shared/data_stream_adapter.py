"""
将 LangGraph astream 事件转换为 Data Stream Protocol 格式
"""
from .data_stream import (
    stream_start,
    stream_text_delta,
    stream_tool_result,
    stream_finish,
    stream_done,
    stream_data
)
import uuid
import logging

logger = logging.getLogger(__name__)

async def adapt_langgraph_stream(service, session_id: str, message: str, db_message_id: str = None):
    """适配 LangGraph 流式输出到 Data Stream Protocol"""
    message_id = str(db_message_id) if db_message_id else f"msg_{uuid.uuid4().hex[:8]}"
    yield stream_start(message_id)
    
    try:
        async for chunk in service.stream_message(session_id, message):
            if isinstance(chunk, str):
                # 文本增量
                yield stream_text_delta(chunk)
            elif isinstance(chunk, dict):
                chunk_type = chunk.get("type")
                
                if chunk_type == "state":
                    # 进度更新 -> 作为 data 事件发送
                    yield stream_data(chunk.get("progress", {}))
                
                elif chunk_type == "data_stream_event":
                    # 直接透传已经格式化好的 Data Stream Event (来自 Phase 2 的 Tool Call)
                    yield chunk.get("event")
                    
    except Exception as e:
        logger.error(f"流式适配器错误: {e}")
        from .data_stream import stream_error
        yield stream_error(str(e))
    
    yield stream_finish("stop")
    yield stream_done()
