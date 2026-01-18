import pytest
from unittest.mock import MagicMock, patch
from langchain_core.messages import AIMessageChunk
from backend.agents.lisa.nodes.workflow_test_design import workflow_execution_node
import json

@pytest.fixture
def mock_get_stream_writer():
    with patch("backend.agents.lisa.nodes.workflow_test_design.get_stream_writer") as mock:
        writer = MagicMock()
        mock.return_value = writer
        yield writer

def test_workflow_execution_node_streaming(mock_get_stream_writer):
    # 1. Setup Mock LLM Stream
    mock_llm = MagicMock()
    mock_bound_llm = MagicMock()
    mock_llm.model.bind_tools.return_value = mock_bound_llm
    
    # Simulate Tool Call
    # Use AIMessageChunk with BOTH tool_call_chunks (for loop safety) and tool_calls (for final logic)
    final_chunk = AIMessageChunk(
        content="",
        tool_call_chunks=[
             {"name": "UpdateArtifact", "args": '{"key": "test", "markdown_body": "content"}', "id": "call_123", "index": 0}
        ],
        tool_calls=[{
            "name": "UpdateArtifact",
            "args": {"key": "test", "markdown_body": "content"},
            "id": "call_123"
        }]
    )
    
    # stream returns an iterator
    mock_bound_llm.stream.return_value = iter([final_chunk])
    
    # 2. Setup State
    state = {
        "messages": [],
        "artifacts": {},
        "current_workflow": "test_design"
    }
    
    # 3. Run Node
    workflow_execution_node(state, mock_llm)
    
    # 4. Verify Writer Calls
    # Filter calls to find data_stream_event
    calls = mock_get_stream_writer.call_args_list
    data_events = [c[0][0] for c in calls if c[0][0].get("type") == "data_stream_event"]
    
    assert len(data_events) > 0, "No data_stream_event emitted"
    
    # Check for tool result event (V2 Protocol)
    result_events = []
    for event_container in data_events:
        event_str = event_container["event"]
        if event_str.startswith("data: "):
            json_str = event_str[6:].strip()
            try:
                payload = json.loads(json_str)
                if payload.get("type") == "tool-result":
                    result_events.append(payload)
            except:
                pass

    assert len(result_events) == 1
    res = result_events[0]
    assert res["toolCallId"] == "call_123"
    assert res["toolName"] == "UpdateArtifact"
    assert res["result"]["key"] == "test"
    assert res["result"]["status"] == "completed"
