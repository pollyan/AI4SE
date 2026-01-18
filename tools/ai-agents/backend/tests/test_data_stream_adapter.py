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
    
    # Verify events
    # 1. Start event (mapped to data event '8' with messageId)
    # Output: 8:[{"messageId": "..."}]\n
    assert events[0].startswith("8:")
    assert "messageId" in events[0]
    
    # 2. Text events
    # Output: 0:"Hello"\n
    assert events[1] == '0:"Hello"\n'
    
    # Output: 0:" world"\n
    assert events[2] == '0:" world"\n'
    
    # 3. Data event (Progress)
    # Output: 8:[{"stage": 1}]\n
    # Note: data_stream.stream_data wraps value in list if not already
    assert events[3].startswith("8:")
    json_str = events[3][2:].strip()
    data = json.loads(json_str)
    assert isinstance(data, list)
    assert data[0]["stage"] == 1
    
    # 4. Text event
    assert events[4] == '0:"!"\n'
    
    # 5. Finish event
    assert events[5].startswith("d:")
    
    # 6. Done event (empty string in new protocol)
    assert events[6] == ""
