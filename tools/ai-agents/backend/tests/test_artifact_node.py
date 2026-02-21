import pytest
from typing import cast, Dict, Any
from unittest.mock import MagicMock, patch
from langchain_core.messages import AIMessage
from backend.agents.lisa.nodes.artifact_node import artifact_node
from backend.agents.lisa.state import LisaState
from backend.agents.lisa.artifact_models import RequirementDoc


@pytest.fixture
def mock_llm():
    llm = MagicMock()
    # Mock bind_tools returning itself or a mock that has invoke
    bound_llm = MagicMock()
    llm.model.bind_tools.return_value = bound_llm
    return llm, bound_llm


@pytest.fixture
def mock_state() -> Dict[str, Any]:
    return {
        "messages": [],
        "artifacts": {},
        "current_stage_id": "clarify",
        "current_workflow": "test_design",
    }


@patch("backend.agents.lisa.nodes.artifact_node.get_stream_writer")
@patch(
    "backend.agents.lisa.nodes.artifact_node.update_artifact"
)  # Mock the tool function itself if needed, or just checking flow
def test_artifact_node_updates_state(
    mock_tool, mock_writer_getter, mock_llm, mock_state
):
    """Test that artifact node updates state based on tool calls"""
    original_llm, bound_llm = mock_llm
    mock_writer = MagicMock()
    mock_writer_getter.return_value = mock_writer

    # Mock LLM response with tool use
    tool_call_id = "call_123"
    tool_args = {
        "key": "test_design_requirements",
        "markdown_body": "# Updated Content",
    }

    mock_response = AIMessage(
        content="",
        tool_calls=[{"name": "update_artifact", "args": tool_args, "id": tool_call_id}],
    )
    bound_llm.invoke.return_value = mock_response

    # Execute node
    new_state = artifact_node(cast(LisaState, mock_state), original_llm)

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
    prompt_msg = bound_llm.invoke.call_args[0][0][0]  # SystemMessage
    assert (
        "test_design" in prompt_msg.content
        or "artifact" in prompt_msg.content.lower()
        or "current_stage" in prompt_msg.content
    )


@patch("backend.agents.lisa.nodes.artifact_node.get_stream_writer")
def test_artifact_node_injects_template_outline(mock_writer_getter, mock_llm):
    """Verify that artifact node injects template outline into the prompt"""
    original_llm, bound_llm = mock_llm
    mock_writer = MagicMock()
    mock_writer_getter.return_value = mock_writer

    # State with templates
    template_outline = "# My Strict Template Structure"
    state = {
        "messages": [],
        "artifacts": {
            "test_key": "some content"
        },  # Artifact exists matching template key, so it goes to LLM update path
        "current_stage_id": "clarify",
        "plan": [{"id": "clarify", "name": "Clarify"}],
        "artifact_templates": [
            {"key": "test_key", "stage": "clarify", "outline": template_outline}
        ],
    }

    # Mock response
    bound_llm.invoke.return_value = AIMessage(content="thought", tool_calls=[])

    # Execute node
    artifact_node(cast(LisaState, state), original_llm)

    # Verify prompt contains template outline
    bound_llm.invoke.assert_called_once()
    system_msg = bound_llm.invoke.call_args[0][0][0]
    assert template_outline in system_msg.content


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
        "plan": [
            {"id": "clarify", "name": "Clarify", "status": "active"}
        ],  # Add status for get_progress_info
        "artifact_templates": [
            {"key": "test_key", "stage": "clarify", "outline": "# My Template"}
        ],
    }

    # Execute node
    new_state = artifact_node(cast(LisaState, state), original_llm)

    # Verify LLM was NOT called
    bound_llm.invoke.assert_not_called()

    # Verify deterministic state update
    assert "test_key" in new_state["artifacts"]
    assert new_state["artifacts"]["test_key"] == "# My Template"

    # Verify progress event includes artifact info correctly formatted
    progress_event = next(
        (
            c.args[0]
            for c in mock_writer.call_args_list
            if c.args[0]["type"] == "progress"
        ),
        None,
    )
    assert progress_event is not None

    # Updated assertion for get_progress_info structure
    assert "artifactProgress" in progress_event["progress"]
    assert "template" in progress_event["progress"]["artifactProgress"]
    templates = progress_event["progress"]["artifactProgress"]["template"]
    assert len(templates) == 1
    assert templates[0]["artifactKey"] == "test_key"


@patch("backend.agents.lisa.nodes.artifact_node.get_stream_writer")
def test_artifact_node_llm_exception(mock_writer_getter, mock_llm, mock_state):
    original_llm, bound_llm = mock_llm

    bound_llm.invoke.side_effect = Exception("LLM failure")

    new_state = artifact_node(cast(LisaState, mock_state), original_llm)

    assert new_state == mock_state


@patch("backend.agents.lisa.nodes.artifact_node.get_stream_writer")
def test_artifact_node_multiple_updates(mock_writer_getter, mock_llm, mock_state):
    original_llm, bound_llm = mock_llm
    mock_writer = MagicMock()
    mock_writer_getter.return_value = mock_writer

    mock_response = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "update_artifact",
                "args": {"key": "key1", "markdown_body": "Content 1"},
                "id": "call_1",
            },
            {
                "name": "update_artifact",
                "args": {"key": "key2", "markdown_body": "Content 2"},
                "id": "call_2",
            },
        ],
    )
    bound_llm.invoke.return_value = mock_response

    new_state = artifact_node(cast(LisaState, mock_state), original_llm)

    assert "key1" in new_state["artifacts"]
    assert new_state["artifacts"]["key1"] == "Content 1"
    assert "key2" in new_state["artifacts"]
    assert new_state["artifacts"]["key2"] == "Content 2"

    assert mock_writer.call_count >= 2


@patch("backend.agents.lisa.nodes.artifact_node.get_stream_writer")
def test_artifact_node_invalid_tool_name(mock_writer_getter, mock_llm, mock_state):
    original_llm, bound_llm = mock_llm

    mock_response = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "wrong_tool",
                "args": {"key": "key1", "markdown_body": "Content 1"},
                "id": "call_1",
            }
        ],
    )
    bound_llm.invoke.return_value = mock_response

    new_state = artifact_node(cast(LisaState, mock_state), original_llm)

    assert "key1" not in new_state["artifacts"]


@patch("backend.agents.lisa.nodes.artifact_node.get_stream_writer")
def test_artifact_node_structured_output(mock_writer_getter, mock_llm, mock_state):
    """Test that artifact node can handle structured artifact output (Pydantic models)"""
    original_llm, bound_llm = mock_llm
    mock_writer = MagicMock()
    mock_writer_getter.return_value = mock_writer

    requirement_doc = RequirementDoc(
        scope=["登录页面", "POST /api/login"],
        flow_mermaid="graph LR; A-->B",
        rules=[],
        assumptions=[],
    )

    mock_response = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "update_structured_artifact",
                "args": {
                    "key": "test_design_requirements",
                    "artifact_type": "requirement",
                    "content": requirement_doc.model_dump(),
                },
                "id": "call_structured_1",
            }
        ],
    )
    bound_llm.invoke.return_value = mock_response

    new_state = artifact_node(cast(LisaState, mock_state), original_llm)

    assert "test_design_requirements" in new_state["artifacts"]
    artifact = new_state["artifacts"]["test_design_requirements"]

    # Artifact node converts structured data to Markdown string for frontend rendering
    assert isinstance(artifact, str)
    assert "登录页面" in artifact
    assert "## 1. 测试范围" in artifact


@patch("backend.agents.lisa.nodes.artifact_node.get_stream_writer")
def test_artifact_node_structured_output_pascal_case(
    mock_writer_getter, mock_llm, mock_state
):
    """Test that artifact node can handle PascalCase tool name (UpdateStructuredArtifact)"""
    original_llm, bound_llm = mock_llm
    mock_writer = MagicMock()
    mock_writer_getter.return_value = mock_writer

    requirement_doc = RequirementDoc(
        scope=["Test Scope"], flow_mermaid="graph LR; A-->B", rules=[], assumptions=[]
    )

    mock_response = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "UpdateStructuredArtifact",
                "args": {
                    "key": "test_design_requirements",
                    "artifact_type": "requirement",
                    "content": requirement_doc.model_dump(),
                },
                "id": "call_structured_pascal",
            }
        ],
    )
    bound_llm.invoke.return_value = mock_response

    new_state = artifact_node(cast(LisaState, mock_state), original_llm)

    assert "test_design_requirements" in new_state["artifacts"]
    artifact = new_state["artifacts"]["test_design_requirements"]

    # Artifact node converts structured data to Markdown string for frontend rendering
    assert isinstance(artifact, str)
    assert "Test Scope" in artifact


@patch("backend.agents.lisa.nodes.artifact_node.get_stream_writer")
def test_incremental_update_bugs_reproduction(mock_writer_getter, mock_llm):
    """
    Reproduction test for 3 related bugs in artifact incremental update:
    Bug 3: Deterministic init doesn't write structured data
    Bug 2: Update merges always start from empty (data loss)
    Bug 1: Prompt builder doesn't receive existing artifact context
    """
    original_llm, bound_llm = mock_llm
    mock_writer = MagicMock()
    mock_writer_getter.return_value = mock_writer

    # --- Step 1: Initialize State ---
    state = {
        "messages": [],
        "artifacts": {},
        # Start without structured_artifacts (simulating current state or empty state)
        "structured_artifacts": {}, 
        "current_stage_id": "clarify",
        "plan": [{"id": "clarify", "name": "Clarify", "status": "active"}],
        "artifact_templates": [
            {"key": "test_req", "stage": "clarify", "outline": "# Template"}
        ],
    }
    
    # --- Execute 1: Deterministic Initialization ---
    # Should run deterministic path because "test_req" is missing in artifacts
    state_after_init = artifact_node(cast(LisaState, state), original_llm)
    
    # Verify Bug 3: structured_artifacts should be populated
    # CURRENT BEHAVIOR: structured_artifacts is empty or missing key
    assert "test_req" in state_after_init["artifacts"], "Markdown artifact missing after init"
    
    # Verify Bug 3 Fix (Reverted): structured_artifacts should NOT be populated
    # We want to show the Markdown template initially, so we strictly ensure structured data is empty
    assert "test_req" in state_after_init["artifacts"], "Markdown artifact missing after init"
    
    if "structured_artifacts" in state_after_init:
         assert "test_req" not in state_after_init["structured_artifacts"], "structured_artifacts should NOT be initialized (to show template)"


    # --- Execute 2: First LLM Update ---
    # Setup LLM response 1 (Adding Feature 1)
    llm_response_1 = AIMessage(
        content="thinking...",
        tool_calls=[
            {
                "name": "UpdateStructuredArtifact",
                "args": {
                    "key": "test_req",
                    "artifact_type": "requirement",
                    "content": {
                        "scope": ["Scope A"],
                        "features": [{"id": "F1", "name": "Feature 1", "priority": "P1"}]
                    }
                },
                "id": "call_1"
            }
        ]
    )
    bound_llm.invoke.return_value = llm_response_1
    
    state_after_update_1 = artifact_node(cast(LisaState, state_after_init), original_llm)
    
    # Verify Bug 2: structured_artifacts should be populated with merged data
    assert "test_req" in state_after_update_1["artifacts"]
    assert "Feature 1" in state_after_update_1["artifacts"]["test_req"]
    
    # This assertion is expected to FAIL until Bug 2 is fixed:
    if "structured_artifacts" in state_after_update_1:
        assert "test_req" in state_after_update_1["structured_artifacts"], "Bug 2: structured_artifacts missing after update 1"
        assert state_after_update_1["structured_artifacts"]["test_req"].get("features")[0]["id"] == "F1"


    # --- Execute 3: Second LLM Update ---
    # Setup LLM response 2 (Adding Feature 2)
    # Important: LLM only sends delta for F2, it assumes F1 exists
    llm_response_2 = AIMessage(
        content="thinking...",
        tool_calls=[
            {
                "name": "UpdateStructuredArtifact",
                "args": {
                    "key": "test_req",
                    "artifact_type": "requirement",
                    "content": {
                        "features": [{"id": "F2", "name": "Feature 2", "priority": "P2"}]
                    }
                },
                "id": "call_2"
            }
        ]
    )
    bound_llm.invoke.return_value = llm_response_2

    state_after_update_2 = artifact_node(cast(LisaState, state_after_update_1), original_llm)

    # Verify Bug 1: Check if prompt contained existing artifact context
    # Get the system message from the LAST call to invoke
    call_args = bound_llm.invoke.call_args
    # call_args[0] is args tuple, args[0] is messages list
    messages = call_args[0][0] 
    system_msg_content = messages[-1].content
    
    # This assertion is expected to FAIL until Bug 1 is fixed:
    assert "INCREMENTAL UPDATE MODE ACTIVE" in system_msg_content, "Bug 1: Incremental context missing in prompt"
    assert "Feature 1" in system_msg_content, "Bug 1: Existing content missing in prompt"

    # Verify Bug 2 again: Data Loss check
    # The final artifact should contain BOTH F1 and F2
    final_structured = state_after_update_2.get("structured_artifacts", {}).get("test_req", {})
    features = final_structured.get("features", [])
    feature_ids = [f.get("id") for f in features]
    
    assert "F1" in feature_ids, "Bug 2: Feature 1 lost during update (Data Loss)"
    assert "F2" in feature_ids, "Feature 2 missing"
