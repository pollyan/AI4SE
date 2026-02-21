"""意图解析器测试"""
from unittest.mock import Mock
from backend.agents.lisa.intent_parser import parse_user_intent, ClarifyContext
from backend.agents.lisa.schemas import UserIntentInClarify


class TestParseUserIntent:
    """parse_user_intent 函数测试"""

    def test_parse_returns_user_intent_schema(self):
        """解析结果应返回 UserIntentInClarify 类型"""
        mock_llm = Mock()
        mock_structured = Mock()
        mock_structured.invoke.return_value = UserIntentInClarify(
            intent="confirm_proceed",
            confidence=0.9,
            answered_question_ids=[],
            extracted_info=None
        )
        mock_llm.model.with_structured_output.return_value = mock_structured
        
        context = ClarifyContext(
            blocking_questions=["Q1: 登录重试机制?"],
            optional_questions=[]
        )
        
        result = parse_user_intent("好的，继续吧", context, mock_llm)
        
        assert isinstance(result, UserIntentInClarify)
        assert result.intent == "confirm_proceed"

    def test_fallback_on_error(self):
        """解析失败时返回降级意图"""
        mock_llm = Mock()
        mock_llm.model.with_structured_output.return_value.invoke.side_effect = Exception("LLM Error")
        
        context = ClarifyContext(blocking_questions=[], optional_questions=[])
        result = parse_user_intent("测试消息", context, mock_llm)
        
        assert result.intent == "need_more_clarify"
        assert result.confidence == 0.5

    def test_context_passed_to_llm(self):
        """上下文应传递给 LLM"""
        mock_llm = Mock()
        mock_structured = Mock()
        mock_structured.invoke.return_value = UserIntentInClarify(
            intent="answer_question",
            confidence=0.85,
        )
        mock_llm.model.with_structured_output.return_value = mock_structured
        
        context = ClarifyContext(
            blocking_questions=["Q1: 阻塞问题"],
            optional_questions=["Q2: 可选问题"]
        )
        
        parse_user_intent("重试机制是3次", context, mock_llm)
        
        mock_structured.invoke.assert_called_once()
        call_args = mock_structured.invoke.call_args[0][0]
        assert len(call_args) == 1


class TestClarifyContext:
    """ClarifyContext 数据类测试"""
    
    def test_context_creation(self):
        """测试上下文创建"""
        context = ClarifyContext(
            blocking_questions=["Q1"],
            optional_questions=["Q2", "Q3"]
        )
        assert context.blocking_questions == ["Q1"]
        assert context.optional_questions == ["Q2", "Q3"]
