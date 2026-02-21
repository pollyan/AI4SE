import pytest
import json
from unittest.mock import MagicMock
from backend.agents.shared.data_stream_adapter import adapt_langgraph_stream

@pytest.mark.asyncio
async def test_adapt_langgraph_stream_tool_protocol_v2():
    """
    Test that adapt_langgraph_stream emits Vercel AI SDK V2/V3 compatible tool events.
    Expected: tool-input-available (and optionally tool-output-available)
    """
    # Mock service
    service = MagicMock()
    
    # Simulate a tool-call chunk from service (as emitted by ArtifactNode via StreamWriter)
    tool_call_payload = {
        "type": "tool-call",
        "toolCallId": "call_123",
        "toolName": "update_artifact",
        "args": {"key": "test_artifact"},
        "result": "Artifact updated successfully"
    }
    
    # Setup async generator
    async def mock_stream(*args, **kwargs):
        yield tool_call_payload
        
    service.stream_message = mock_stream

    # Run adapter
    events = []
    async for event in adapt_langgraph_stream(service, "session_1", "msg_1"):
        events.append(event)
        
    # Helper to parse SSE data
    def parse_event(event_str):
        if not event_str.startswith("data: "):
            return None
        json_str = event_str[6:].strip()
        try:
            return json.loads(json_str)
        except:
            return None

    parsed_events = [parse_event(e) for e in events if e.strip()]
    parsed_events = [e for e in parsed_events if e] # filter Nones
    
    print(f"Captured events: {parsed_events}")

    # Check for tool-input-available
    # "type": "tool-input-available", "toolCallId": "...", "toolName": "...", "input": {...}
    tool_input_events = [e for e in parsed_events if e.get("type") == "tool-input-available"]
    
    assert len(tool_input_events) == 1, f"Expected 1 tool-input-available event, found {len(tool_input_events)}"
    
    event = tool_input_events[0]
    assert event["toolCallId"] == "call_123"
    assert event["toolName"] == "update_artifact"
    assert event["input"] == {"key": "test_artifact"}

    # Check for tool-output-available (Since we treat the call as completed)
    # "type": "tool-output-available", "toolCallId": "...", "output": {...}
    tool_output_events = [e for e in parsed_events if e.get("type") == "tool-output-available"]
    
    assert len(tool_output_events) == 1, f"Expected 1 tool-output-available event, found {len(tool_output_events)}"
    assert tool_output_events[0]["toolCallId"] == "call_123"
