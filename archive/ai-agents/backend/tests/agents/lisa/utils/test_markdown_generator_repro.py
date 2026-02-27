from backend.agents.lisa.utils.markdown_generator import convert_to_markdown

def test_convert_requirement_doc_scope_mermaid_is_dict():
    """Verify fix: scope_mermaid dict should be converted to string, not crash"""
    content = {
        "scope_mermaid": {"code": "graph TD; A-->B"},
        "scope": ["Scope 1"]
    }
    
    # Should NOT raise TypeError
    md = convert_to_markdown(content, "requirement")
    
    # It should convert dict to string
    assert "{'code': 'graph TD; A-->B'}" in md or '{"code": "graph TD; A-->B"}' in md

def test_convert_requirement_doc_flow_mermaid_is_dict():
    """Verify fix: flow_mermaid dict should be converted to string, not crash"""
    content = {
        "flow_mermaid": {"code": "graph TD; A-->B"},
    }
    
    # Should NOT raise TypeError
    md = convert_to_markdown(content, "requirement")
    
    assert "{'code': 'graph TD; A-->B'}" in md or '{"code": "graph TD; A-->B"}' in md
