import pytest
from typing import Any, Dict, cast
from unittest.mock import MagicMock, patch
from langchain_core.messages import AIMessage
from backend.agents.lisa.state import LisaState
from backend.agents.lisa.nodes.artifact_node import artifact_node


@pytest.fixture
def mock_llm():
    llm = MagicMock()
    # Mock bind_tools to return the mock itself (fluent interface)
    llm.model.bind_tools.return_value = llm
    return llm


@pytest.fixture
def mock_stream_writer():
    with patch("backend.agents.lisa.nodes.artifact_node.get_robust_stream_writer") as mock:
        writer = MagicMock()
        mock.return_value = writer
        yield writer


@pytest.mark.integration
def test_e2e_incremental_update_flow(mock_llm, mock_stream_writer):
    # 1. Initialize State
    state = LisaState(
        messages=[],
        current_workflow="test_design",
        workflow_stage="clarify",
        plan=[],
        current_stage_id="clarify",
        artifacts={
            "requirement": ""  # Should be string in new design
        },
        structured_artifacts={
            "requirement": {}  # Storage for structured data
        },
        artifact_templates=[
            {"stage": "clarify", "key": "requirement", "outline": "template"}
        ],
        pending_clarifications=[],
        clarification=None,
        consensus_items=[],
        latest_artifact_hint=None,
    )

    # 2. Simulate Interaction 1: Create initial artifact (Q1, Q2)
    # Mock LLM response with tool call
    initial_content = {
        "scope": ["Login"],
        "flow_mermaid": "graph TD; A-->B;",
        "rules": [],
        "assumptions": [
            {"id": "Q1", "question": "2FA?", "status": "pending", "priority": "P1"},
            {
                "id": "Q2",
                "question": "Timeout?",
                "status": "confirmed",
                "priority": "P2",
            },
        ],
    }

    msg_1 = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "UpdateStructuredArtifact",
                "args": {
                    "key": "requirement",
                    "artifact_type": "requirement",
                    "content": initial_content,
                },
                "id": "call_1",
            }
        ],
    )

    mock_llm.invoke.return_value = msg_1

    # Run Node
    state_after_1 = cast(Dict[str, Any], {**state, **artifact_node(state, None, mock_llm)})

    # Verify State 1: Check STRUCTURED data
    # state['artifacts'] now holds markdown string
    # state['structured_artifacts'] holds the dict
    structured_1 = state_after_1.get("structured_artifacts", {}).get("requirement")
    markdown_1 = state_after_1.get("artifacts", {}).get("requirement")

    assert structured_1 is not None, "Structured artifact not found"
    assert isinstance(structured_1, dict)
    
    # Verify content conversion
    assert len(structured_1["assumptions"]) == 2
    assert structured_1["assumptions"][0]["id"] == "Q1"
    assert structured_1["assumptions"][0]["status"] == "pending"

    # Verify Markdown generation happened
    assert isinstance(markdown_1, str)
    assert "2FA?" in markdown_1  # Basic check that content is reflected

    # 3. Simulate Interaction 2: Incremental Update (Update Q1, Add Q3)
    # Only sending changed/new items
    patch_content = {
        "assumptions": [
            {"id": "Q1", "status": "confirmed", "note": "Yes, SMS"},  # Update
            {
                "id": "Q3",
                "question": "New Q?",
                "status": "pending",
                "priority": "P1",
            },  # Add
        ]
    }

    msg_2 = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "UpdateStructuredArtifact",
                "args": {
                    "key": "requirement",
                    "artifact_type": "requirement",
                    "content": patch_content,
                },
                "id": "call_2",
            }
        ],
    )

    mock_llm.invoke.return_value = msg_2

    # Run Node again with updated state
    state_after_2 = cast(Dict[str, Any], {**state_after_1, **artifact_node(cast(LisaState, state_after_1), None, mock_llm)})

    # Verify State 2
    structured_2 = cast(
        Dict[str, Any],
        state_after_2.get("structured_artifacts", {}).get("requirement")
    )
    assumptions = structured_2["assumptions"]

    assert len(assumptions) == 3  # Q1, Q2, Q3

    # Verify Q1 Updated
    q1 = next(a for a in assumptions if a["id"] == "Q1")
    assert q1["status"] == "confirmed"
    assert q1["note"] == "Yes, SMS"
    assert q1["question"] == "2FA?"  # Preserved from initial

    # Verify Q2 Unchanged (was not in patch)
    q2 = next(a for a in assumptions if a["id"] == "Q2")
    assert q2["status"] == "confirmed"

    # Verify Q3 Added
    q3 = next(a for a in assumptions if a["id"] == "Q3")
    assert q3["question"] == "New Q?"
