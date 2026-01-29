import pytest
from backend.agents.lisa.utils.markdown_generator import convert_to_markdown

def test_convert_requirement_doc():
    content = {
        "scope": ["模块A", "模块B"],
        "flow_mermaid": "graph TD\nA-->B",
        "rules": ["规则1"],
        "assumptions": ["假设1"],
        "nfr_markdown": {
            "性能": "很快",
            "安全": "很安全"
        }
    }
    
    md = convert_to_markdown(content, "requirement")
    
    assert "## 1. 需求全景图" in md
    assert "- 模块A" in md
    assert "## 3. 业务流程图" in md
    assert "```mermaid" in md
    assert "graph TD" in md
    assert "## 2. 功能详细规格" in md
    assert "## 4. 非功能需求 (NFR)" in md
    assert "### 性能" not in md # 之前是 ###, 现在是 - **性能**: ...
    assert "**性能**" in md
    assert "很快" in md

def test_convert_fallback():
    content = {"key": "value"}
    md = convert_to_markdown(content, "unknown")
    assert "## key" in md
    assert "value" in md
