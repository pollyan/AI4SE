import pytest
from unittest.mock import AsyncMock, MagicMock
import json
from backend.agents.shared.data_stream_adapter import adapt_langgraph_stream

class MockService:
    def __init__(self, chunks):
        self.chunks = chunks

    async def stream_message(self, session_id, message):
        for chunk in self.chunks:
            yield chunk

@pytest.mark.asyncio
async def test_adapt_langgraph_stream():
    # Prepare mock data
    chunks = [
        "Hello",
        " world",
        {"type": "state", "progress": {"stage": 1}},
        "!"
    ]
    service = MockService(chunks)
    
    # Collect events
    events = []
    async for event in adapt_langgraph_stream(service, "sess_1", "hi"):
        events.append(event)
    
    # Verify
    # 3. 验证事件序列
    # 3. Data event (from progress dict)
    assert events[3].startswith("data: ")
    data_event = json.loads(events[3][6:].strip())
    assert data_event["type"] == "data"
    assert data_event["value"]["stage"] == 1

    # 4. Text event "!" (V2 uses text-delta)
    assert events[4].startswith("data: ")
    text_event = json.loads(events[4][6:].strip())
    assert text_event["type"] == "text-delta"
    assert text_event["delta"] == "!"
    assert "id" in text_event
    
    # 5. Text end event
    assert events[5].startswith("data: ")
    text_end_event = json.loads(events[5][6:].strip())
    assert text_end_event["type"] == "text-end"
    
    # 6. Finish event
    assert events[6].startswith("data: ")
    finish_event = json.loads(events[6][6:].strip())
    assert finish_event["type"] == "finish"
    assert finish_event["finishReason"] == "stop"
