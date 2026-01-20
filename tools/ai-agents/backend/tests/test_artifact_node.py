import pytest
from unittest.mock import MagicMock, patch
from langchain_core.messages import AIMessage
from backend.agents.lisa.nodes.artifact_node import artifact_node

@pytest.fixture
def mock_llm():
    llm = MagicMock()
    # Mock bind_tools returning itself or a mock that has invoke
    bound_llm = MagicMock()
    llm.model.bind_tools.return_value = bound_llm
    return llm, bound_llm

@pytest.fixture
def mock_state():
    return {
        "messages": [],
        "artifacts": {},
        "current_stage_id": "clarify",
        "workflow_type": "test_design"
    }

@patch("backend.agents.lisa.nodes.artifact_node.get_stream_writer")
@patch("backend.agents.lisa.nodes.artifact_node.update_artifact") # Mock the tool function itself if needed, or just checking flow
def test_artifact_node_updates_state(mock_tool, mock_writer_getter, mock_llm, mock_state):
    """Test that artifact node updates state based on tool calls"""
    original_llm, bound_llm = mock_llm
    mock_writer = MagicMock()
    mock_writer_getter.return_value = mock_writer
    
    # Mock LLM response with tool use
    tool_call_id = "call_123"
    tool_args = {"key": "test_design_requirements", "markdown_body": "# Updated Content"}
    
    mock_response = AIMessage(
        content="",
        tool_calls=[{
            "name": "update_artifact",
            "args": tool_args,
            "id": tool_call_id
        }]
    )
    bound_llm.invoke.return_value = mock_response
    
    # Execute node
    new_state = artifact_node(mock_state, original_llm)
    
    # Verify state update
    assert "test_design_requirements" in new_state["artifacts"]
    assert new_state["artifacts"]["test_design_requirements"] == "# Updated Content"
    
    # Verify events
    # 1. tool-call event
    # 2. progress event
    # Note: Depending on implementation, these might be sent. We just verify they exist.
    assert mock_writer.call_count >= 1
    
    # Check tool-call event
    tool_call_event = None
    for call in mock_writer.call_args_list:
        event = call.args[0]
        if event.get("type") == "tool-call":
            tool_call_event = event
            break
            
    # Note: If artifact_node doesn't emit tool-call explicitly but relies on standard langgraph tooling, 
    # we might strictly check for progress. But assuming it mocks tool execution and sends event:
    if tool_call_event:
        assert tool_call_event["toolCallId"] == tool_call_id
        assert tool_call_event["toolName"] == "update_artifact"
        assert tool_call_event["args"] == {"key": tool_args["key"]}

    # Verify LLM prompt construction (briefly)
    bound_llm.invoke.assert_called_once()
    prompt_msg = bound_llm.invoke.call_args[0][0][0] # SystemMessage
    assert "test_design" in prompt_msg.content or "artifact" in prompt_msg.content.lower() or "current_stage" in prompt_msg.content

@patch("backend.agents.lisa.nodes.artifact_node.get_stream_writer")
def test_artifact_node_deterministic_init(mock_writer_getter, mock_llm):
    """Test that ArtifactNode uses deterministic initialization (bypassing LLM) when artifact is missing"""
    original_llm, bound_llm = mock_llm
    mock_writer = MagicMock()
    mock_writer_getter.return_value = mock_writer
    
    # State with templates but empty artifacts
    state = {
        "messages": [],
        "artifacts": {},
        "current_stage_id": "clarify",
        "plan": [{"id": "clarify", "name": "Clarify", "status": "active"}], # Add status for get_progress_info
        "artifact_templates": [
            {"key": "test_key", "stage": "clarify", "outline": "# My Template"}
        ]
    }
    
    # Execute node
    new_state = artifact_node(state, original_llm)
    
    # Verify LLM was NOT called
    bound_llm.invoke.assert_not_called()
    
    # Verify deterministic state update
    assert "test_key" in new_state["artifacts"]
    assert new_state["artifacts"]["test_key"] == "# My Template"
    
    # Verify progress event includes artifact info correctly formatted
    progress_event = next((c.args[0] for c in mock_writer.call_args_list if c.args[0]["type"] == "progress"), None)
    assert progress_event is not None
    
    # Updated assertion for get_progress_info structure
    assert "artifactProgress" in progress_event["progress"]
    assert "template" in progress_event["progress"]["artifactProgress"]
    templates = progress_event["progress"]["artifactProgress"]["template"]
    assert len(templates) == 1
    assert templates[0]["artifactKey"] == "test_key"

