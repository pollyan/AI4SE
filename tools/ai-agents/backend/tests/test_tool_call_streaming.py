import pytest
from unittest.mock import MagicMock, patch
from backend.agents.lisa.nodes.workflow_test_design import workflow_execution_node
from backend.agents.lisa.schemas import WorkflowResponse, UpdateArtifact

@pytest.fixture
def mock_get_stream_writer():
    with patch("backend.agents.lisa.nodes.workflow_test_design.get_stream_writer") as mock:
        writer = MagicMock()
        mock.return_value = writer
        yield writer

def test_workflow_execution_node_streaming(mock_get_stream_writer):
    # 1. Setup Mock LLM
    mock_llm = MagicMock()
    mock_model = MagicMock()
    mock_llm.model = mock_model
    
    mock_structured_llm = MagicMock()
    mock_model.with_structured_output.return_value = mock_structured_llm
    
    # 2. Simulate WorkflowResponse Stream
    # Chunk 1: Thought
    chunk1 = WorkflowResponse(thought="Thinking...", progress_step=None, update_artifact=None)
    # Chunk 2: Artifact Update
    chunk2 = WorkflowResponse(
        thought="Thinking...", 
        progress_step="Designing...", 
        update_artifact=UpdateArtifact(key="test_design_requirements", markdown_body="## Content")
    )
    
    mock_structured_llm.stream.return_value = iter([chunk1, chunk2])
    
    # 3. Setup State
    state = {
        "messages": [],
        "artifacts": {},
        "current_workflow": "test_design"
    }
    
    # 4. Run Node
    workflow_execution_node(state, mock_llm)
    
    # 5. Verify calls
    calls = mock_get_stream_writer.call_args_list
    
    # Verify text_delta_chunk (from thought)
    text_deltas = [c[0][0] for c in calls if c[0][0].get("type") == "text_delta_chunk"]
    assert len(text_deltas) > 0
    assert text_deltas[0]["delta"] == "Thinking..."
    
    # Verify progress (from artifact update)
    progress_events = [c[0][0] for c in calls if c[0][0].get("type") == "progress"]
    assert len(progress_events) > 0
    
    last_progress = progress_events[-1]["progress"]
    assert last_progress["currentTask"] == "Designing..."
    assert last_progress["artifacts"]["test_design_requirements"] == "## Content"
