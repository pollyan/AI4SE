import pytest
import sys
import os

# Ensure backend can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from backend.agents.lisa.prompts.artifacts import build_artifact_update_prompt


def test_prompt_instructs_incremental_update():
    existing_artifact = {
        "scope": ["Login"],
        "assumptions": [{"id": "Q1", "question": "Existing?", "status": "pending"}],
    }

    prompt = build_artifact_update_prompt(
        artifact_key="test_key",
        current_stage="clarify",
        template_outline="Outline...",
        existing_artifact=existing_artifact,
    )

    assert "INCREMENTAL UPDATE" in prompt
    assert "Q1" in prompt  # Context should be included
    assert "Existing?" in prompt
    assert "Only output changed items" in prompt
