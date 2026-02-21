from unittest.mock import MagicMock
from backend.agents.lisa.stream_utils import process_reasoning_stream
from backend.agents.lisa.schemas import ReasoningResponse

def test_process_reasoning_stream_thought_delta():
    mock_writer = MagicMock()
    plan = [{"id": "stage1"}]
    current_stage = "stage1"
    
    chunks = [
        ReasoningResponse(thought="Hello", progress_step=None),
        ReasoningResponse(thought="Hello World", progress_step=None)
    ]
    
    result = process_reasoning_stream(iter(chunks), mock_writer, plan, current_stage)
    
    assert result.thought == "Hello World"
    
    calls = mock_writer.call_args_list
    deltas = [c.args[0]["delta"] for c in calls if c.args[0]["type"] == "text_delta_chunk"]
    assert deltas == ["Hello", " World"]

def test_process_reasoning_stream_progress():
    mock_writer = MagicMock()
    plan = [{"id": "stage1"}]
    current_stage = "stage1"
    
    chunks = [
        ReasoningResponse(thought="A", progress_step="Step 1"),
        ReasoningResponse(thought="A", progress_step="Step 2")
    ]
    
    process_reasoning_stream(iter(chunks), mock_writer, plan, current_stage)
    
    calls = mock_writer.call_args_list
    progress_updates = [c.args[0]["progress"]["currentTask"] for c in calls if c.args[0]["type"] == "progress"]
    
    assert "Step 1" in progress_updates
    assert "Step 2" in progress_updates

def test_process_reasoning_stream_should_update_artifact():
    mock_writer = MagicMock()
    plan = [{"id": "stage1"}]
    current_stage = "stage1"
    
    chunks = [
        ReasoningResponse(thought="A", should_update_artifact=False),
        ReasoningResponse(thought="A", should_update_artifact=True)
    ]
    
    result = process_reasoning_stream(iter(chunks), mock_writer, plan, current_stage)
    
    assert result.should_update_artifact is True

def test_process_reasoning_stream_empty_chunks():
    mock_writer = MagicMock()
    plan = [{"id": "stage1"}]
    current_stage = "stage1"
    
    chunks = []
    
    result = process_reasoning_stream(iter(chunks), mock_writer, plan, current_stage)
    
    assert result.thought == ""
    assert result.progress_step is None
    assert result.should_update_artifact is False
