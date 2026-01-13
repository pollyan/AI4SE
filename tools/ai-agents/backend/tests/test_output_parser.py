"""
JSON 输出解析器测试

TDD Red Phase: 验证 PydanticOutputParser 集成和 JSON 提取逻辑
"""

import pytest
from backend.agents.shared.schemas import LisaStructuredOutput, WorkflowStage, Artifact
from backend.agents.shared.output_parser import (
    create_lisa_parser,
    parse_structured_output,
    extract_json_from_response,
)


class TestCreateLisaParser:
    
    def test_create_parser_returns_parser(self):
        parser = create_lisa_parser()
        assert parser is not None
    
    def test_parser_has_format_instructions(self):
        parser = create_lisa_parser()
        instructions = parser.get_format_instructions()
        assert "plan" in instructions
        # message 字段已移除
        # assert "message" in instructions


class TestExtractJsonFromResponse:

    def test_extract_json_block(self):
        response = """我已完成需求分析。

```json
{
  "plan": [{"id": "clarify", "name": "需求澄清", "status": "completed"}],
  "current_stage_id": "clarify",
  "artifacts": []
}
```"""
        json_str = extract_json_from_response(response)
        assert json_str is not None
        assert '"plan"' in json_str

    def test_extract_json_without_markdown_block(self):
        response = """{
  "plan": [{"id": "clarify", "name": "需求澄清", "status": "active"}],
  "current_stage_id": "clarify",
  "artifacts": []
}"""
        json_str = extract_json_from_response(response)
        assert json_str is not None
        assert '"plan"' in json_str

    def test_extract_json_with_text_before(self):
        response = """这是一些前置文本。

```json
{"plan": [], "current_stage_id": "test", "artifacts": []}
```

这是一些后置文本。"""
        json_str = extract_json_from_response(response)
        assert json_str is not None

    def test_extract_returns_none_for_invalid(self):
        response = "这是一段没有 JSON 的普通文本"
        json_str = extract_json_from_response(response)
        assert json_str is None


class TestParseStructuredOutput:

    def test_parse_valid_json(self):
        json_str = """{
  "plan": [
    {"id": "clarify", "name": "需求澄清", "status": "completed"},
    {"id": "strategy", "name": "策略制定", "status": "active"}
  ],
  "current_stage_id": "strategy",
  "artifacts": [
    {"stage_id": "clarify", "key": "requirements", "name": "需求文档", "content": "# 需求"}
  ]
}"""
        result = parse_structured_output(json_str, LisaStructuredOutput)
        
        assert isinstance(result, LisaStructuredOutput)
        assert len(result.plan) == 2
        assert result.current_stage_id == "strategy"
        assert len(result.artifacts) == 1
        # message 字段已移除

    def test_parse_minimal_json(self):
        json_str = """{
  "plan": [{"id": "test", "name": "测试", "status": "active"}],
  "current_stage_id": "test"
}"""
        result = parse_structured_output(json_str, LisaStructuredOutput)
        
        assert result.artifacts == []

    def test_parse_invalid_json_returns_none(self):
        json_str = "{ invalid json }"
        result = parse_structured_output(json_str, LisaStructuredOutput)
        
        assert result is None

    def test_parse_missing_required_field_returns_none(self):
        json_str = '{"plan": []}' # 缺少 current_stage_id
        result = parse_structured_output(json_str, LisaStructuredOutput)
        
        assert result is None


class TestEndToEndParsing:

    def test_full_llm_response_parsing(self):
        llm_response = """好的，我已经理解了您的需求。让我们开始测试设计工作。

首先，我需要澄清几个关键问题：

1. 系统的主要用户群体是谁？
2. 预期的并发用户数量是多少？
3. 是否有特殊的安全要求？

```json
{
  "plan": [
    {"id": "clarify", "name": "需求澄清", "status": "active"},
    {"id": "strategy", "name": "策略制定", "status": "pending"},
    {"id": "cases", "name": "用例设计", "status": "pending"},
    {"id": "delivery", "name": "交付确认", "status": "pending"}
  ],
  "current_stage_id": "clarify",
  "artifacts": [
    {"stage_id": "clarify", "key": "requirements", "name": "需求分析文档", "content": null},
    {"stage_id": "strategy", "key": "test_strategy", "name": "测试策略", "content": null}
  ]
}
```"""
        json_str = extract_json_from_response(llm_response)
        assert json_str is not None
        
        result = parse_structured_output(json_str, LisaStructuredOutput)
        assert result is not None
        assert len(result.plan) == 4
        assert result.current_stage_id == "clarify"
        assert len(result.artifacts) == 2
        assert result.artifacts[0].content is None
        # message 不再在 JSON 中
