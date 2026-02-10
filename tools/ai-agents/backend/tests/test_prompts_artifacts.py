import pytest
from backend.agents.lisa.prompts.artifacts import (
    generate_requirement_template,
    get_artifact_json_schemas,
    ARTIFACT_UPDATE_PROMPT,
)


class TestGenerateRequirementTemplate:
    def test_returns_string(self):
        result = generate_requirement_template()
        assert isinstance(result, str)

    def test_contains_all_7_sections(self):
        result = generate_requirement_template()
        assert "## 1. 测试范围" in result
        assert "## 2. 功能详细规格" in result
        assert "## 3. 核心业务规则" in result
        assert "## 4. 业务流程图" in result
        assert "## 5. 非功能需求" in result
        assert "## 6. 待澄清问题" in result
        assert "## 7. 已确认信息" in result

    def test_schema_sync_with_model(self):
        schemas = get_artifact_json_schemas()
        req_schema = schemas["requirement"]
        props = req_schema.get("properties", {})
        assert "out_of_scope" in props
        assert "features" in props


class TestArtifactUpdatePrompt:
    def test_is_chinese_and_strict(self):
        assert "系统内部指令" in ARTIFACT_UPDATE_PROMPT
        assert "严禁" in ARTIFACT_UPDATE_PROMPT or "严重警告" in ARTIFACT_UPDATE_PROMPT
        assert "{template_outline}" in ARTIFACT_UPDATE_PROMPT
        assert "UpdateStructuredArtifact" in ARTIFACT_UPDATE_PROMPT
