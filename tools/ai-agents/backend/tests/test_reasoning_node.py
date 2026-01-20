import pytest
from unittest.mock import MagicMock, patch
from langgraph.types import Command
from langchain_core.messages import AIMessage
from backend.agents.lisa.nodes.reasoning_node import reasoning_node
from backend.agents.lisa.schemas import ReasoningResponse

@pytest.fixture
def mock_llm():
    llm = MagicMock()
    # Mock with_structured_output
    structured_llm = MagicMock()
    llm.model.with_structured_output.return_value = structured_llm
    return llm

@pytest.fixture
def mock_state():
    return {
        "messages": [],
        "artifacts": {"test_design_requirements": "existing content"},
        "current_stage_id": "clarify",
        "plan": [{"id": "clarify", "name": "Clarify"}]
    }

@patch("backend.agents.lisa.nodes.reasoning_node.get_stream_writer")
@patch("backend.agents.lisa.nodes.reasoning_node.process_reasoning_stream")
@patch("backend.agents.lisa.nodes.reasoning_node.build_test_design_prompt")
def test_reasoning_node_routing_artifact(mock_prompt, mock_process, mock_writer, mock_llm, mock_state):
    """Test routing to artifact_node when update is needed"""
    
    # Mock LLM response via process_reasoning_stream return value
    mock_process.return_value = ReasoningResponse(
        thought="I need to update the artifact.",
        progress_step="Updating...",
        should_update_artifact=True
    )
    
    command = reasoning_node(mock_state, mock_llm)
    
    assert isinstance(command, Command)
    assert command.goto == "artifact_node"
    # Ensure messages are updated
    assert len(command.update["messages"]) > 0
    assert command.update["messages"][-1].content == "I need to update the artifact."

@patch("backend.agents.lisa.nodes.reasoning_node.get_stream_writer")
@patch("backend.agents.lisa.nodes.reasoning_node.process_reasoning_stream")
@patch("backend.agents.lisa.nodes.reasoning_node.build_test_design_prompt")
def test_reasoning_node_routing_end(mock_prompt, mock_process, mock_writer, mock_llm, mock_state):
    """Test routing to end when no update is needed"""
    
    # Mock LLM response
    mock_process.return_value = ReasoningResponse(
        thought="Just thinking.",
        should_update_artifact=False
    )
    
    command = reasoning_node(mock_state, mock_llm)
    
    assert isinstance(command, Command)
    assert command.goto == "__end__"

@patch("backend.agents.lisa.nodes.reasoning_node.get_stream_writer")
@patch("backend.agents.lisa.nodes.reasoning_node.process_reasoning_stream")
@patch("backend.agents.lisa.nodes.reasoning_node.build_test_design_prompt")
def test_reasoning_node_initializaton_force_routing(mock_prompt, mock_process, mock_writer, mock_llm):
    """Test that ReasoningNode forces routing to ArtifactNode when initializing empty artifact"""
    
    # Empty state triggering initialization
    state = {
        "messages": [],
        "artifacts": {}, # Empty artifacts
        # plan and templates missing, ensuring ensure_workflow_initialized runs
    }
    
    # Mock LLM saying NO update needed (we expect the logic to override this)
    mock_process.return_value = ReasoningResponse(
        thought="Welcome.",
        should_update_artifact=False
    )
    
    command = reasoning_node(state, mock_llm)
    
    assert isinstance(command, Command)
    assert command.goto == "artifact_node"
    # State should have been updated with initialization data
    assert "plan" in command.update
    assert "artifact_templates" in command.update
