"""UserIntentInClarify Schema 测试"""
import pytest
from pydantic import ValidationError
from backend.agents.lisa.schemas import UserIntentInClarify


class TestUserIntentInClarify:
    """UserIntentInClarify Schema 测试"""

    def test_valid_intent_confirm_proceed(self):
        """测试有效的 confirm_proceed 意图"""
        intent = UserIntentInClarify(
            intent="confirm_proceed",
            confidence=0.95,
        )
        assert intent.intent == "confirm_proceed"

    def test_all_intent_types(self):
        """测试所有 7 种意图类型都有效"""
        intent_types = [
            "provide_material", "answer_question", "confirm_proceed",
            "need_more_clarify", "accept_risk", "change_scope", "off_topic"
        ]
        for intent_type in intent_types:
            intent = UserIntentInClarify(intent=intent_type, confidence=0.8)
            assert intent.intent == intent_type

    def test_invalid_intent_raises_error(self):
        """测试无效意图值抛出错误"""
        with pytest.raises(ValidationError):
            UserIntentInClarify(intent="invalid", confidence=0.5)

    def test_confidence_bounds(self):
        """测试置信度边界值"""
        UserIntentInClarify(intent="confirm_proceed", confidence=0.0)
        UserIntentInClarify(intent="confirm_proceed", confidence=1.0)
        
        with pytest.raises(ValidationError):
            UserIntentInClarify(intent="confirm_proceed", confidence=-0.1)
        with pytest.raises(ValidationError):
            UserIntentInClarify(intent="confirm_proceed", confidence=1.1)

    def test_optional_fields_defaults(self):
        """测试可选字段默认值"""
        intent = UserIntentInClarify(intent="answer_question", confidence=0.9)
        assert intent.answered_question_ids == []
        assert intent.extracted_info is None
