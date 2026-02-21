from backend.agents.lisa.schemas import ReasoningResponse, WorkflowResponse, UpdateArtifact

def test_reasoning_response_structure():
    """Test the structure of the new ReasoningResponse"""
    # Valid data
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

def test_workflow_response_legacy_update():
    """
    Test that WorkflowResponse no longer has update_artifact 
    or behaves as expected if we keep it for backward compatibility 
    but we plan to remove update_artifact from it.
    """
    # If we removed update_artifact, passing it should either be ignored or cause error 
    # if using extra='forbid'. Let's assume standard Pydantic behavior (ignore extra).
    # But strictly, the class shouldn't have the field.
    
    data = {
        "thought": "Thinking..."
    }
    resp = WorkflowResponse(**data)
    assert not hasattr(resp, "update_artifact")

def test_update_artifact_schema_check():
    """
    UpdateArtifact schema is still needed for the tool definition type hinting,
    even if not nested in WorkflowResponse.
    """
    data = {
        "key": "test_design_requirements",
        "markdown_body": "# Content"
    }
    artifact = UpdateArtifact(**data)
    assert artifact.key == "test_design_requirements"
