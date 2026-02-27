"""
测试 shared/progress_utils.py 模块

覆盖场景：
- 文本清理
- JSON 结构化输出解析（新格式）
"""

from backend.agents.shared.progress_utils import (
    clean_response_text,
    get_current_stage_id,
)


class TestCleanResponseText:
    
    def test_clean_json_block(self):
        text = '''```json
{"plan": [], "current_stage_id": "test", "artifacts": [], "message": "msg"}
```
开始工作'''
        result = clean_response_text(text)
        assert result == "开始工作"
    
    def test_clean_no_json(self):
        text = "这是一段普通文本"
        result = clean_response_text(text)
        assert result == "这是一段普通文本"
    
    def test_clean_preserves_mermaid_blocks(self):
        text = '''```json
{"plan": []}
```
Here is a diagram:
```mermaid
graph TD;
    A-->B;
```
Description.'''
        result = clean_response_text(text)
        assert "```mermaid" in result
        assert "graph TD;" in result
        assert "```json" not in result
        text = '''```json
{"plan": [], "current_stage_id": "test", "artifacts": [], "message": "内容"}
```

## 需求分析

详细内容...'''
        result = clean_response_text(text)
        assert "## 需求分析" in result
        assert "详细内容..." in result
        assert "```json" not in result


class TestGetCurrentStageId:
    """测试获取当前活跃阶段"""
    
    def test_get_active_stage(self):
        """获取活跃阶段 ID"""
        plan = [
            {"id": "clarify", "status": "completed"},
            {"id": "strategy", "status": "active"},
            {"id": "cases", "status": "pending"},
        ]
        result = get_current_stage_id(plan)
        assert result == "strategy"
    
    def test_no_active_stage(self):
        """无活跃阶段返回 None"""
        plan = [
            {"id": "clarify", "status": "completed"},
            {"id": "strategy", "status": "pending"},
        ]
        result = get_current_stage_id(plan)
        assert result is None


