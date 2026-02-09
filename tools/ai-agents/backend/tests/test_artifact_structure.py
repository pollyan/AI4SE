import pytest
from backend.agents.lisa.state import LisaState
from backend.agents.lisa.artifact_models import RequirementDoc


def test_state_stores_structured_artifact():
    state = LisaState(
        messages=[],
        current_workflow=None,
        workflow_stage=None,
        plan=[],
        current_stage_id=None,
        artifacts={},
        artifact_templates=[],
        pending_clarifications=[],
        clarification=None,
        consensus_items=[],
    )

    # verify artifacts is Dict[str, Dict] or Pydantic model, not str
    state["artifacts"] = {
        "requirement": RequirementDoc(
            scope=["login"], rules=[], flow_mermaid="graph TD; A-->B;"
        )
    }

    assert isinstance(state["artifacts"]["requirement"], RequirementDoc)
    assert state["artifacts"]["requirement"].scope == ["login"]


def test_patch_update_list_item_by_id():
    from backend.agents.lisa.artifact_patch import merge_artifacts

    original = {"items": [{"id": "1", "val": "a"}, {"id": "2", "val": "b"}]}
    patch = {"items": [{"id": "1", "val": "updated"}]}
    result = merge_artifacts(original, patch)
    assert result["items"][0]["val"] == "updated"
    assert len(result["items"]) == 2
    assert result["items"][1]["val"] == "b"


def test_patch_append_new_item():
    from backend.agents.lisa.artifact_patch import merge_artifacts

    original = {"items": [{"id": "1", "val": "a"}]}
    patch = {"items": [{"id": "2", "val": "new"}]}
    result = merge_artifacts(original, patch)
    assert len(result["items"]) == 2
    assert result["items"][1]["id"] == "2"
    assert result["items"][1]["val"] == "new"


def test_patch_invalid_json_returns_original():
    from backend.agents.lisa.artifact_patch import merge_artifacts
    from typing import Dict, Any, cast

    original = {"items": [{"id": "1", "val": "a"}]}
    invalid_patch = cast(Dict[str, Any], "not a json")
    result = merge_artifacts(original, invalid_patch)
    assert result == original
