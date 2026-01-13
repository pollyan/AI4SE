"""
产出物解析工具单元测试 (TDD Red Phase)

测试 shared/artifact_utils.py 中的产出物解析函数。
"""

import pytest


class TestParseArtifact:
    """测试 parse_artifact 函数"""
    
    def test_parses_simple_artifact_tag(self):
        """应能解析简单的 artifact 标签"""
        from backend.agents.shared.artifact_utils import parse_artifact
        
        text = '<artifact key="test_design_requirements">这是产出物内容</artifact>'
        result = parse_artifact(text)
        
        assert result is not None
        assert result["key"] == "test_design_requirements"
        assert result["content"] == "这是产出物内容"
    
    def test_parses_artifact_with_markdown_content(self):
        """应能解析包含 Markdown 内容的 artifact"""
        from backend.agents.shared.artifact_utils import parse_artifact
        
        text = '''<artifact key="product_brd">
# BRD 文档

## 产品概述
产品名称：测试产品
</artifact>'''
        result = parse_artifact(text)
        
        assert result is not None
        assert result["key"] == "product_brd"
        assert "# BRD 文档" in result["content"]
        assert "产品名称" in result["content"]
    
    def test_parses_artifact_mixed_with_other_content(self):
        """应能从混合内容中提取 artifact"""
        from backend.agents.shared.artifact_utils import parse_artifact
        
        text = '''好的，我来生成文档：
<artifact key="test_cases">
用例1: 登录测试
用例2: 注册测试
</artifact>
以上是测试用例。'''
        result = parse_artifact(text)
        
        assert result is not None
        assert result["key"] == "test_cases"
        assert "用例1" in result["content"]
    
    def test_returns_none_when_no_artifact(self):
        """无 artifact 标签时返回 None"""
        from backend.agents.shared.artifact_utils import parse_artifact
        
        text = "这是普通文本，没有产出物标签。"
        result = parse_artifact(text)
        
        assert result is None
    
    def test_parses_artifact_with_single_quotes(self):
        """应支持单引号的 key 属性"""
        from backend.agents.shared.artifact_utils import parse_artifact
        
        text = "<artifact key='strategy'>策略内容</artifact>"
        result = parse_artifact(text)
        
        assert result is not None
        assert result["key"] == "strategy"
    
    def test_artifact_content_is_stripped(self):
        """artifact 内容应去除首尾空白"""
        from backend.agents.shared.artifact_utils import parse_artifact
        
        text = "<artifact key='test'>  \n内容\n  </artifact>"
        result = parse_artifact(text)
        
        assert result["content"] == "内容"


class TestExtractMarkdownBlock:
    """测试 extract_markdown_block 函数（向后兼容）"""
    
    def test_extracts_markdown_code_block(self):
        """应能提取 ```markdown 代码块"""
        from backend.agents.shared.artifact_utils import extract_markdown_block
        
        text = '''这是一些文本
```markdown
# 标题
内容
```
更多文本'''
        result = extract_markdown_block(text)
        
        assert result is not None
        assert "# 标题" in result
        assert "内容" in result
    
    def test_returns_none_when_no_markdown_block(self):
        """无 markdown 代码块时返回 None"""
        from backend.agents.shared.artifact_utils import extract_markdown_block
        
        text = "普通文本，没有代码块"
        result = extract_markdown_block(text)
        
        assert result is None
    
    def test_extracts_first_markdown_block_only(self):
        """只提取第一个 markdown 代码块"""
        from backend.agents.shared.artifact_utils import extract_markdown_block
        
        text = '''
```markdown
第一个
```
```markdown
第二个
```
'''
        result = extract_markdown_block(text)
        
        assert result == "第一个"


class TestParseAllArtifacts:
    """测试 parse_all_artifacts 函数（多个产出物）"""
    
    def test_parses_multiple_artifacts(self):
        """应能解析多个 artifact 标签"""
        from backend.agents.shared.artifact_utils import parse_all_artifacts
        
        text = '''
<artifact key="requirements">需求文档</artifact>
一些文字
<artifact key="strategy">策略文档</artifact>
'''
        results = parse_all_artifacts(text)
        
        assert len(results) == 2
        assert results[0]["key"] == "requirements"
        assert results[1]["key"] == "strategy"
    
    def test_returns_empty_list_when_no_artifacts(self):
        """无 artifact 时返回空列表"""
        from backend.agents.shared.artifact_utils import parse_all_artifacts
        
        text = "没有任何产出物"
        results = parse_all_artifacts(text)
        
        assert results == []
