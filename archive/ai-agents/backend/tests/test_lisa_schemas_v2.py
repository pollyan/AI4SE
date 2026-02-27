from backend.agents.lisa.schemas import ReasoningResponse, WorkflowResponse, UpdateStructuredArtifact

def test_reasoning_response_structure():
    """Test the structure of the new ReasoningResponse"""
    data = {
        "thought": "Analysis completed.",
        "progress_step": "Analyzing requirements",
        "should_update_artifact": True
    }
    resp = ReasoningResponse(**data)
    assert resp.thought == "Analysis completed."
    assert resp.progress_step == "Analyzing requirements"
    assert resp.should_update_artifact is True

def test_reasoning_response_defaults():
    """Test default values for ReasoningResponse"""
    data = {
        "thought": "Thinking..."
    }
    resp = ReasoningResponse(**data)
    assert resp.thought == "Thinking..."
    assert resp.progress_step is None
    assert resp.should_update_artifact is False

def test_workflow_response_legacy():
    """Test that WorkflowResponse still works as legacy schema"""
    data = {
        "thought": "Thinking..."
    }
    resp = WorkflowResponse(**data)
    assert resp.thought == "Thinking..."
    # WorkflowResponse should not have update_artifact field
    assert not hasattr(resp, "update_artifact")

def test_update_structured_artifact_schema():
    """
    UpdateStructuredArtifact is the ONLY artifact update schema.
    Verify its structure.
    """
    data = {
        "key": "test_design_requirements",
        "artifact_type": "requirement",
        "content": {"scope": ["Login"]}
    }
    artifact = UpdateStructuredArtifact(**data)
    assert artifact.key == "test_design_requirements"
    assert artifact.artifact_type == "requirement"
    assert artifact.content == {"scope": ["Login"]}
