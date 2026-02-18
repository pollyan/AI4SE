import pytest
import sys
import os

# Ensure backend can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from backend.agents.lisa.prompts.artifacts import build_artifact_update_prompt
from backend.agents.lisa.schemas import ReasoningResponse


def test_prompt_instructs_incremental_update():
    existing_artifact = {
        "scope": ["Login"],
        "assumptions": [{"id": "Q1", "question": "Existing?", "status": "pending"}],
    }

    prompt = build_artifact_update_prompt(
        artifact_key="test_key",
        current_stage="clarify",
        template_outline="Outline...",
        existing_artifact=existing_artifact,
    )

    assert "INCREMENTAL UPDATE" in prompt
    assert "Q1" in prompt  # Context should be included
    assert "Existing?" in prompt
    assert "Only output changed items" in prompt


# ─────────────────────────────────────────────────────────────────────────────
# Context-Aware Artifact Sync: build_artifact_update_prompt reasoning_hint 注入
# ─────────────────────────────────────────────────────────────────────────────

class TestReasoningHintInjection:
    """验证 reasoning_hint 参数正确注入到 Artifact Update Prompt 中"""

    def test_hint_is_injected_when_provided(self):
        """当传入 reasoning_hint 时，Prompt 中应包含 hint 内容和上下文标题"""
        hint = "用户确认库存并发使用数据库乐观锁。风险提示: 高并发下失败率上升。"

        prompt = build_artifact_update_prompt(
            artifact_key="test_design_requirements",
            current_stage="clarify",
            template_outline="Outline...",
            reasoning_hint=hint,
        )

        assert "CONTEXT FROM REASONING AGENT" in prompt
        assert hint in prompt
        assert "请务必根据上述上下文更新文档" in prompt

    def test_no_hint_section_when_hint_is_none(self):
        """当 reasoning_hint 为 None 时，Prompt 中不应出现 hint 上下文块"""
        prompt = build_artifact_update_prompt(
            artifact_key="test_design_requirements",
            current_stage="clarify",
            template_outline="Outline...",
            reasoning_hint=None,
        )

        assert "CONTEXT FROM REASONING AGENT" not in prompt
        assert "请务必根据上述上下文更新文档" not in prompt

    def test_hint_and_incremental_context_coexist(self):
        """reasoning_hint 与 incremental update context 可以同时存在于 Prompt 中"""
        existing_artifact = {
            "scope": ["Login"],
            "assumptions": [{"id": "Q1", "question": "Timeout?", "status": "pending"}],
        }
        hint = "用户确认超时时间为 30 秒。"

        prompt = build_artifact_update_prompt(
            artifact_key="test_design_requirements",
            current_stage="clarify",
            template_outline="Outline...",
            existing_artifact=existing_artifact,
            reasoning_hint=hint,
        )

        # 两个上下文块都应存在
        assert "CONTEXT FROM REASONING AGENT" in prompt
        assert hint in prompt
        assert "INCREMENTAL UPDATE" in prompt
        assert "Q1" in prompt

    def test_hint_position_before_incremental_context(self):
        """reasoning_hint 应出现在 incremental context 之前（优先级更高）"""
        existing_artifact = {"scope": ["Checkout"]}
        hint = "用户确认支付方式仅支持微信支付。"

        prompt = build_artifact_update_prompt(
            artifact_key="test_design_requirements",
            current_stage="clarify",
            template_outline="Outline...",
            existing_artifact=existing_artifact,
            reasoning_hint=hint,
        )

        hint_pos = prompt.find("CONTEXT FROM REASONING AGENT")
        incremental_pos = prompt.find("INCREMENTAL UPDATE")
        assert hint_pos < incremental_pos, "reasoning_hint 上下文块应出现在 incremental context 之前"


# ─────────────────────────────────────────────────────────────────────────────
# Context-Aware Artifact Sync: ReasoningResponse.artifact_update_hint 字段验证
# ─────────────────────────────────────────────────────────────────────────────

class TestReasoningResponseArtifactUpdateHint:
    """验证 ReasoningResponse Schema 中 artifact_update_hint 字段的行为"""

    def test_field_is_optional_and_defaults_to_none(self):
        """artifact_update_hint 字段应为可选，默认值为 None"""
        response = ReasoningResponse(
            thought="您好，我已收到需求文档。",
            should_update_artifact=False,
        )

        assert response.artifact_update_hint is None

    def test_field_accepts_valid_hint_string(self):
        """artifact_update_hint 字段应接受有效的字符串值"""
        hint = "用户确认库存并发使用数据库乐观锁。行动项: 更新需求规则章节。"

        response = ReasoningResponse(
            thought="好的，我已记录您的确认。",
            should_update_artifact=True,
            artifact_update_hint=hint,
        )

        assert response.artifact_update_hint == hint

    def test_field_accepts_none_explicitly(self):
        """artifact_update_hint 字段应接受显式传入的 None"""
        response = ReasoningResponse(
            thought="只是闲聊，无需更新。",
            should_update_artifact=False,
            artifact_update_hint=None,
        )

        assert response.artifact_update_hint is None

    def test_other_required_fields_still_work(self):
        """新增 artifact_update_hint 字段不应破坏 ReasoningResponse 的其他字段"""
        response = ReasoningResponse(
            thought="正在分析需求。",
            progress_step="需求分析中",
            should_update_artifact=True,
            request_transition_to="strategy",
            artifact_update_hint="用户确认了所有 P0 问题。",
        )

        assert response.thought == "正在分析需求。"
        assert response.progress_step == "需求分析中"
        assert response.should_update_artifact is True
        assert response.request_transition_to == "strategy"
        assert "P0" in response.artifact_update_hint
