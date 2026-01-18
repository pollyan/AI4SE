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
    
    # Simulate Tool Call Chunks
    # Chunk 1: Start
    chunk1 = AIMessageChunk(content="", tool_call_chunks=[
        {"name": "UpdateArtifact", "args": "", "id": "call_123", "index": 0}
    ])
    # Chunk 2: Args delta
    chunk2 = AIMessageChunk(content="", tool_call_chunks=[
        {"name": "UpdateArtifact", "args": '{"key": "test"', "id": "call_123", "index": 0}
    ])
    # Chunk 3: Args delta
    chunk3 = AIMessageChunk(content="", tool_call_chunks=[
        {"name": "UpdateArtifact", "args": '}', "id": "call_123", "index": 0}
    ])
    
    mock_bound_llm.stream.return_value = [chunk1, chunk2, chunk3]
    
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
    
    # Check for start event (Protocol 'b')
    # b:{"toolCallId": "call_123", "toolName": "UpdateArtifact"}
    start_events = [e for e in data_events if e["event"].startswith("b:")]
    assert len(start_events) == 1
    assert "call_123" in start_events[0]["event"]
    
    # Check for delta events (Protocol 'c')
    # c:{"toolCallId": "call_123", "argsTextDelta": "..."}
    delta_events = [e for e in data_events if e["event"].startswith("c:")]
    assert len(delta_events) >= 2
    
    # Parse Protocol to verify content
    # Format: c:{"toolCallId":..., "argsTextDelta":...}
    evt1_json = delta_events[0]["event"][2:].strip()
    evt1 = json.loads(evt1_json)
    assert '{"key": "test"' in evt1["argsTextDelta"]
    
    evt2_json = delta_events[1]["event"][2:].strip()
    evt2 = json.loads(evt2_json)
    assert '}' in evt2["argsTextDelta"]
