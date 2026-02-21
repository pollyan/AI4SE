"""
测试产出物更新 Prompt 的 hint 注入机制
"""
import pytest
from backend.agents.lisa.prompts.artifacts import (
    build_artifact_update_prompt,
)


class TestArtifactHintSync:
    """验证 artifact_update_hint 在 Prompt 中的注入行为"""

    def test_prompt_includes_hint_when_provided(self):
        """有 hint 时，Prompt 中应包含 hint 内容和状态变更指令"""
        hint = "用户确认密码不需要特殊字符。**状态变更**: Q-003 → confirmed (note: 无需特殊字符)"
        
        prompt = build_artifact_update_prompt(
            artifact_key="test_design_requirements",
            current_stage="clarify",
            template_outline="# 模板",
            existing_artifact=None,
            reasoning_hint=hint,
        )
        
        assert "Q-003 → confirmed" in prompt
        assert "状态变更" in prompt
        assert "status" in prompt.lower() or "confirmed" in prompt

    def test_prompt_includes_fallback_when_no_hint(self):
        """无 hint 时，Prompt 中应包含通用兜底规则"""
        prompt = build_artifact_update_prompt(
            artifact_key="test_design_requirements",
            current_stage="clarify",
            template_outline="# 模板",
            existing_artifact=None,
            reasoning_hint=None,
        )
        
        assert "通用规则" in prompt or "FALLBACK RULE" in prompt
        assert "confirmed" in prompt

    def test_prompt_includes_hint_but_not_fallback(self):
        """有 hint 时，不应出现兜底规则"""
        hint = "**状态变更**: Q-001 → confirmed"
        
        prompt = build_artifact_update_prompt(
            artifact_key="test_design_requirements",
            current_stage="clarify",
            template_outline="# 模板",
            existing_artifact=None,
            reasoning_hint=hint,
        )
        
        assert "FALLBACK RULE" not in prompt
        assert "通用规则" not in prompt
