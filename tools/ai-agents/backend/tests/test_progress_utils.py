"""
测试 shared/progress_utils.py 模块

覆盖场景：
- XML 解析正确
- 无 XML 指令
- 文本清理
- 动态 Plan 解析（全量快照模式）
- JSON 结构化输出解析（新格式）
"""

import pytest
from backend.agents.shared.progress_utils import (
    parse_plan,
    clean_response_text,
    clean_response_streaming,
    get_current_stage_id,
    parse_structured_json,
    extract_plan_from_structured,
    extract_artifacts_from_structured,
)


class TestCleanResponseText:
    """测试响应文本清理"""
    
    def test_clean_plan_tag(self):
        """清理 plan 标签"""
        text = '<plan>[{"id": "a", "status": "active"}]</plan>开始工作'
        result = clean_response_text(text)
        assert result == "开始工作"
    
    def test_clean_no_tags(self):
        """无标签时保持原样"""
        text = "这是一段普通文本"
        result = clean_response_text(text)
        assert result == "这是一段普通文本"
    
    def test_clean_preserves_content(self):
        """清理后保留其他内容"""
        text = '<plan>[...]</plan>\n\n## 需求分析\n\n详细内容...'
        result = clean_response_text(text)
        assert "## 需求分析" in result
        assert "详细内容..." in result
        assert "plan" not in result


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


class TestParsePlan:
    """测试动态 Plan 解析（全量快照模式）"""
    
    def test_parse_valid_plan_with_status(self):
        """正确解析包含 status 的 plan（全量快照模式）"""
        text = '<plan>[{"id": "clarify", "name": "需求澄清", "status": "completed"}, {"id": "strategy", "name": "策略制定", "status": "active"}]</plan>其他内容'
        result = parse_plan(text)
        
        assert result is not None
        assert len(result) == 2
        assert result[0]["id"] == "clarify"
        assert result[0]["status"] == "completed"
        assert result[1]["id"] == "strategy"
        assert result[1]["status"] == "active"
    
    def test_parse_plan_without_status_uses_default(self):
        """解析不含 status 的 plan 时使用默认值 pending"""
        text = '<plan>[{"id": "clarify", "name": "需求澄清"}, {"id": "strategy", "name": "策略制定"}]</plan>'
        result = parse_plan(text)
        
        assert result is not None
        assert result[0]["status"] == "pending"
        assert result[1]["status"] == "pending"
    
    def test_parse_no_plan_tag(self):
        """无 plan 标签时返回 None"""
        text = "这是一段普通的回复，没有 plan 标签。"
        result = parse_plan(text)
        assert result is None
    
    def test_parse_invalid_json(self):
        """JSON 格式错误时返回 None"""
        text = '<plan>这不是有效的 JSON</plan>'
        result = parse_plan(text)
        assert result is None
    
    def test_parse_plan_normalizes_stages(self):
        """解析时自动标准化阶段"""
        text = '<plan>[{"id": "step1"}, {"name": "步骤2"}]</plan>'
        result = parse_plan(text)
        
        assert result is not None
        assert result[0]["id"] == "step1"
        assert "stage_" in result[1]["id"]
        assert result[1]["name"] == "步骤2"


class TestCleanResponseStreaming:
    """测试流式响应清理"""
    
    def test_clean_complete_tags(self):
        """测试移除完整的标签"""
        text = "开始<plan>[...]</plan>结束"
        result = clean_response_streaming(text)
        assert result == "开始结束"
        
    def test_truncate_partial_plan_start(self):
        """测试截断未完成的 plan 开始标签"""
        text = "前面内容<pla"
        result = clean_response_streaming(text)
        assert result == "前面内容"
        
    def test_truncate_known_start(self):
        text = "text <plan"
        assert clean_response_streaming(text) == "text "

    def test_no_truncate_other_tags(self):
        """不截断其他标签"""
        text = "text <br"
        assert clean_response_streaming(text) == "text <br"


class TestParseStructuredJson:

    def test_parse_valid_json_block(self):
        response = '''对话内容...

```json
{
  "plan": [{"id": "clarify", "name": "需求澄清", "status": "active"}],
  "current_stage_id": "clarify",
  "artifacts": [],
  "message": "让我们开始需求澄清"
}
```'''
        data, message = parse_structured_json(response)

        assert data is not None
        assert message == "让我们开始需求澄清"
        assert len(data["plan"]) == 1
        assert data["current_stage_id"] == "clarify"

    def test_parse_json_with_artifacts(self):
        response = '''```json
{
  "plan": [{"id": "clarify", "name": "需求澄清", "status": "completed"}],
  "current_stage_id": "clarify",
  "artifacts": [
    {"stage_id": "clarify", "key": "requirements", "name": "需求文档", "content": "# 需求内容"}
  ],
  "message": "已完成需求分析"
}
```'''
        data, message = parse_structured_json(response)

        assert data is not None
        assert len(data["artifacts"]) == 1
        assert data["artifacts"][0]["content"] == "# 需求内容"

    def test_parse_no_json_block(self):
        response = "这是普通文本，没有 JSON 块"
        data, message = parse_structured_json(response)

        assert data is None
        assert message is None

    def test_parse_invalid_json(self):
        response = '''```json
{ invalid json }
```'''
        data, message = parse_structured_json(response)

        assert data is None
        assert message is None

    def test_parse_missing_required_field(self):
        # 缺少 plan 或 current_stage_id 应该失败
        response = '''```json
{"plan": []}
```'''
        data, message = parse_structured_json(response)

        assert data is None

    def test_parse_success_without_message(self):
        # 缺少 message 应该成功 (混合模式)
        response = '''```json
{"plan": [], "current_stage_id": "test"}
```'''
        data, message = parse_structured_json(response)

        assert data is not None
        assert data["current_stage_id"] == "test"
        assert message == ""

    def test_parse_uses_last_json_block(self):
        response = '''First block:
```json
{"plan": [], "current_stage_id": "first", "message": "first", "artifacts": []}
```

Second block:
```json
{"plan": [], "current_stage_id": "second", "message": "second", "artifacts": []}
```'''
        data, message = parse_structured_json(response)

        assert data is not None
        assert data["current_stage_id"] == "second"
        assert message == "second"


class TestExtractPlanFromStructured:

    def test_extract_plan_normalizes_stages(self):
        data = {
            "plan": [
                {"id": "step1", "name": "步骤1", "status": "active"},
                {"name": "步骤2"},
            ]
        }
        plan = extract_plan_from_structured(data)

        assert plan is not None
        assert len(plan) == 2
        assert plan[0]["id"] == "step1"
        assert plan[0]["status"] == "active"
        assert "stage_" in plan[1]["id"]
        assert plan[1]["status"] == "pending"

    def test_extract_empty_plan(self):
        data = {"plan": []}
        plan = extract_plan_from_structured(data)

        assert plan == []


class TestExtractArtifactsFromStructured:

    def test_extract_templates_and_content(self):
        data = {
            "artifacts": [
                {"stage_id": "clarify", "key": "req", "name": "需求", "content": "# 内容"},
                {"stage_id": "strategy", "key": "strat", "name": "策略", "content": None},
            ]
        }
        templates, artifacts = extract_artifacts_from_structured(data)

        assert len(templates) == 2
        assert templates[0]["artifact_key"] == "req"
        assert len(artifacts) == 1
        assert artifacts["req"] == "# 内容"

    def test_extract_empty_artifacts(self):
        data = {"artifacts": []}
        templates, artifacts = extract_artifacts_from_structured(data)

        assert templates == []
        assert artifacts == {}
