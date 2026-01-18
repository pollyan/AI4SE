"""
产出物解析工具单元测试 (Updated)

测试 shared/artifact_utils.py 中的产出物解析函数。
"""

import pytest

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
