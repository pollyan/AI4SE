import pytest
from unittest.mock import MagicMock, patch
from langchain_core.messages import AIMessage
from backend.agents.lisa.state import LisaState
from backend.agents.lisa.nodes.artifact_node import artifact_node
from backend.agents.lisa.artifact_models import RequirementDoc


@pytest.fixture
def mock_llm():
    llm = MagicMock()
    # Mock bind_tools to return the mock itself (fluent interface)
    llm.model.bind_tools.return_value = llm
    return llm


@pytest.fixture
def mock_stream_writer():
    with patch("backend.agents.lisa.nodes.artifact_node.get_stream_writer") as mock:
        writer = MagicMock()
        mock.return_value = writer
        yield writer


def test_e2e_incremental_update_flow(mock_llm, mock_stream_writer):
    # 1. Initialize State
    state = LisaState(
        messages=[],
        current_workflow="test_design",
        workflow_stage="clarify",
        plan=[],
        current_stage_id="clarify",
        artifacts={
            "requirement": {}
        },  # Pre-populate to bypass deterministic initialization
        artifact_templates=[
            {"stage": "clarify", "key": "requirement", "outline": "template"}
        ],
        pending_clarifications=[],
        clarification=None,
        consensus_items=[],
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
    state_after_1 = artifact_node(state, mock_llm)

    # Verify State 1
    req_1 = state_after_1["artifacts"]["requirement"]
    # It might be dict or model depending on implementation details of merge
    # Our merge_artifacts returns dict.
    # State definition says Union[RequirementDoc, ...].
    # But artifact_node currently stores result of merge_artifacts (dict).
    # Ideally we should cast it back to Model if we want strict typing,
    # but for now dict is what is stored.

    assert isinstance(req_1, dict)
    assert len(req_1["assumptions"]) == 2
    assert req_1["assumptions"][0]["id"] == "Q1"
    assert req_1["assumptions"][0]["status"] == "pending"

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
    state_after_2 = artifact_node(state_after_1, mock_llm)

    # Verify State 2
    req_2 = state_after_2["artifacts"]["requirement"]
    assumptions = req_2["assumptions"]

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
