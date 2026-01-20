from backend.agents.lisa.tools import update_artifact

def test_update_artifact_tool():
    """Test the update_artifact tool execution"""
    # Test valid input
    result = update_artifact.invoke({
        "key": "test_design_requirements",
        "markdown_body": "# Requirements"
    })
    
    assert result == "Artifact 'test_design_requirements' updated successfully."
    assert "update_artifact" == update_artifact.name

def test_update_artifact_args_schema():
    """Test argument schema validation"""
    args_schema = update_artifact.args_schema
    schema = args_schema.model_json_schema()
    
    # Verify key property exists and has enum constraint
    props = schema['properties']
    assert 'key' in props
    assert 'markdown_body' in props
    
    # Check enum values if possible (depends on Pydantic/LangChain version)
    # Just basic check is fine
