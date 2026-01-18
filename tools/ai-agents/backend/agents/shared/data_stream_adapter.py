"""
将 LangGraph astream 事件转换为 Data Stream Protocol (V2 - w/ text-delta) 格式
"""
from .data_stream import (
    stream_start,
    stream_text_delta,
    stream_text_end,
    stream_data,
    stream_finish,
    stream_done,
    stream_error
)
import uuid
import logging

logger = logging.getLogger(__name__)

async def adapt_langgraph_stream(service, session_id: str, message: str, db_message_id: str = None):
    """适配 LangGraph 流式输出到 Data Stream Protocol (text-delta variant)"""
    
    # Client expects discriminated union: for text, it's text-start, text-delta...
    # We need a stable ID for the message being streamed.
    stream_id = str(uuid.uuid4())
    
    try:
        # 1. Send Text Stream Start
        yield stream_start(stream_id)
        
        async for chunk in service.stream_message(session_id, message):
            if isinstance(chunk, str):
                # 文本增量 (type: "text-delta", delta: "...")
                yield stream_text_delta(chunk, stream_id)
            elif isinstance(chunk, dict):
                chunk_type = chunk.get("type")
                
                if chunk_type == "state":
                    # 进度更新 -> 作为 data 事件发送
                    # value IS the progress object
                    yield stream_data(chunk.get("progress", {}))
                
                elif chunk_type == "data_stream_event":
                    # 透传预格式化的事件
                    yield chunk.get("event")
                    
        # 2. Send Text Stream End
        yield stream_text_end(stream_id)

    except Exception as e:
        logger.error(f"流式适配器错误: {e}")
        yield stream_error(str(e))
    
    # 结束事件
    yield stream_finish("stop")
    yield stream_done()
