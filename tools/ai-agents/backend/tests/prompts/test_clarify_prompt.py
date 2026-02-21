"""测试 clarify 阶段 Prompt 内容完整性"""
from backend.agents.lisa.prompts.workflows.test_design import STAGE_CLARIFY_PROMPT


class TestClarifyPrompt:
    """clarify 阶段 Prompt 测试"""

    def test_contains_stage_goal(self):
        """Prompt 应包含阶段目标定义"""
        assert "Testing Foundation" in STAGE_CLARIFY_PROMPT or "测试基础信息" in STAGE_CLARIFY_PROMPT

    def test_contains_hard_requirements(self):
        """Prompt 应包含必须完成的事项"""
        required_items = ["SUT", "Scope", "Main Flow", "阻塞性"]
        for item in required_items:
            assert item in STAGE_CLARIFY_PROMPT, f"Missing required item: {item}"

    def test_contains_dor_criteria(self):
        """Prompt 应包含 DoR 准出标准"""
        assert "DoR" in STAGE_CLARIFY_PROMPT or "Definition of Ready" in STAGE_CLARIFY_PROMPT

    def test_contains_question_levels(self):
        """Prompt 应包含问题分级机制"""
        levels = ["阻塞性", "建议澄清", "可选"]
        found = sum(1 for level in levels if level in STAGE_CLARIFY_PROMPT)
        assert found >= 2, "Should contain at least 2 question levels"
