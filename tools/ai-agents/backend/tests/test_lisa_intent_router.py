"""Intent Router Node 单元测试 - Command 模式 & Hybrid Routing"""

import pytest
from unittest.mock import MagicMock, patch
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.types import Command

from backend.agents.lisa.nodes.intent_router import (
    intent_router_node,
    fallback_intent_routing,
    format_messages_for_context,
    summarize_artifacts,
)
from backend.agents.lisa.state import get_initial_state
from backend.agents.lisa.schemas import IntentResult
from backend.agents.lisa.routing.hybrid_router import RoutingDecision


class TestFallbackLLMRouting:
    """测试 LLM 降级路由逻辑 (fallback_intent_routing)"""
    
    @pytest.fixture
    def mock_llm(self):
        llm = MagicMock()
        llm.model = MagicMock()
        return llm
    
    @pytest.fixture
    def base_state(self):
        state = get_initial_state()
        state["messages"] = [HumanMessage(content="测试消息")]
        return state
    
    def test_uses_with_structured_output(self, mock_llm, base_state):
        structured_llm = MagicMock()
        structured_llm.invoke.return_value = IntentResult(
            intent="START_TEST_DESIGN",
            confidence=0.95,
            entities=["登录页面"],
            reason="明确要求设计测试用例"
        )
        mock_llm.model.with_structured_output.return_value = structured_llm
        
        result = fallback_intent_routing(base_state, mock_llm)
        
        assert isinstance(result, IntentResult)
        assert result.intent == "START_TEST_DESIGN"
        
        mock_llm.model.with_structured_output.assert_called_once()
        call_args = mock_llm.model.with_structured_output.call_args
        assert call_args[0][0] == IntentResult


class TestIntentRouterIntegration:
    """测试意图路由节点集成 HybridRouter"""
    
    @pytest.fixture(autouse=True)
    def clear_router_cache(self):
        from backend.agents.lisa.nodes.intent_router import get_hybrid_router
        get_hybrid_router.cache_clear()
        yield
    
    @pytest.fixture
    def mock_llm(self):
        return MagicMock()

    @pytest.fixture
    def base_state(self):
        state = get_initial_state()
        state["messages"] = [HumanMessage(content="测试消息")]
        return state

    @patch("backend.agents.lisa.nodes.intent_router.HybridRouter")
    def test_uses_hybrid_router_and_returns_command(self, MockHybridRouter, base_state, mock_llm):
        """测试使用 HybridRouter 并返回 Command"""
        mock_router = MockHybridRouter.return_value
        mock_router.route.return_value = RoutingDecision(
            intent="START_TEST_DESIGN",
            confidence=0.9,
            source="semantic",
            latency_ms=10.0
        )
        
        result = intent_router_node(base_state, mock_llm)
        
        # 验证返回了 Command
        assert isinstance(result, Command)
        assert result.goto == "workflow_test_design"
        assert result.update["current_workflow"] == "test_design"
        
        # 验证调用了 route
        mock_router.route.assert_called_once()
    
    @patch("backend.agents.lisa.nodes.intent_router.HybridRouter")
    def test_handles_low_confidence_clarify(self, MockHybridRouter, base_state, mock_llm):
        """测试低置信度时返回 Clarify"""
        mock_router = MockHybridRouter.return_value
        mock_router.route.return_value = RoutingDecision(
            intent=None,
            confidence=0.3,
            source="llm",
            latency_ms=500.0,
            reason="不明确"
        )
        
        result = intent_router_node(base_state, mock_llm)
        
        assert isinstance(result, Command)
        assert result.goto == "clarify_intent"


class TestFormatMessagesForContext:
    
    def test_format_empty_messages(self):
        result = format_messages_for_context([])
        assert result == "(无历史消息)"
    
    def test_format_truncates_long_content(self):
        long_content = "a" * 300
        messages = [HumanMessage(content=long_content)]
        
        result = format_messages_for_context(messages)
        
        assert len(result) < len(long_content) + 50
        assert "..." in result


class TestSummarizeArtifacts:
    
    def test_empty_artifacts(self):
        result = summarize_artifacts({})
        assert result == "(无产出物)"
    
    def test_summarize_with_content(self):
        artifacts = {"test_key": "some content here"}
        
        result = summarize_artifacts(artifacts)
        
        assert "test_key" in result
