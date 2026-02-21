"""混合路由器测试 - TDD"""

from unittest.mock import MagicMock
from dataclasses import dataclass


@dataclass
class MockIntentResult:
    intent: str | None
    confidence: float
    reason: str


class TestHybridRouter:
    
    def test_uses_semantic_for_high_confidence(self):
        from backend.agents.lisa.routing.hybrid_router import HybridRouter
        from backend.agents.lisa.routing.semantic_router import LisaSemanticRouter
        
        mock_semantic = MagicMock(spec=LisaSemanticRouter)
        mock_semantic.route.return_value = ("START_TEST_DESIGN", 0.92)
        
        mock_llm_fn = MagicMock()
        
        router = HybridRouter(semantic_router=mock_semantic)
        decision = router.route("帮我设计测试用例", llm_router_fn=mock_llm_fn)
        
        assert decision.intent == "START_TEST_DESIGN"
        assert decision.source == "semantic"
        assert decision.confidence >= 0.85
        mock_llm_fn.assert_not_called()
    
    def test_falls_back_to_llm_for_low_confidence(self):
        from backend.agents.lisa.routing.hybrid_router import HybridRouter
        from backend.agents.lisa.routing.semantic_router import LisaSemanticRouter
        
        mock_semantic = MagicMock(spec=LisaSemanticRouter)
        mock_semantic.route.return_value = (None, 0.3)
        
        mock_llm_fn = MagicMock(return_value=MockIntentResult(
            intent="START_TEST_DESIGN",
            confidence=0.9,
            reason="LLM 判断"
        ))
        
        router = HybridRouter(semantic_router=mock_semantic)
        decision = router.route("模糊请求", llm_router_fn=mock_llm_fn)
        
        assert decision.intent == "START_TEST_DESIGN"
        assert decision.source == "llm"
        mock_llm_fn.assert_called_once()
    
    def test_returns_semantic_result_when_no_llm_fallback(self):
        from backend.agents.lisa.routing.hybrid_router import HybridRouter
        from backend.agents.lisa.routing.semantic_router import LisaSemanticRouter
        
        mock_semantic = MagicMock(spec=LisaSemanticRouter)
        mock_semantic.route.return_value = ("START_TEST_DESIGN", 0.6)
        
        router = HybridRouter(semantic_router=mock_semantic)
        decision = router.route("测试相关请求", llm_router_fn=None)
        
        assert decision.intent == "START_TEST_DESIGN"
        assert decision.source == "semantic"
    
    def test_returns_none_when_semantic_low_and_no_llm(self):
        from backend.agents.lisa.routing.hybrid_router import HybridRouter
        from backend.agents.lisa.routing.semantic_router import LisaSemanticRouter
        
        mock_semantic = MagicMock(spec=LisaSemanticRouter)
        mock_semantic.route.return_value = (None, 0.2)
        
        router = HybridRouter(semantic_router=mock_semantic)
        decision = router.route("无关请求", llm_router_fn=None)
        
        assert decision.intent is None
        assert decision.source == "semantic"
    
    def test_routing_decision_includes_latency(self):
        from backend.agents.lisa.routing.hybrid_router import HybridRouter
        from backend.agents.lisa.routing.semantic_router import LisaSemanticRouter
        
        mock_semantic = MagicMock(spec=LisaSemanticRouter)
        mock_semantic.route.return_value = ("START_TEST_DESIGN", 0.95)
        
        router = HybridRouter(semantic_router=mock_semantic)
        decision = router.route("测试请求")
        
        assert decision.latency_ms >= 0
        assert isinstance(decision.latency_ms, float)
    
    def test_medium_confidence_triggers_llm_verification(self):
        from backend.agents.lisa.routing.hybrid_router import HybridRouter
        from backend.agents.lisa.routing.semantic_router import LisaSemanticRouter
        
        mock_semantic = MagicMock(spec=LisaSemanticRouter)
        mock_semantic.route.return_value = ("START_TEST_DESIGN", 0.75)
        
        mock_llm_fn = MagicMock(return_value=MockIntentResult(
            intent="START_REQUIREMENT_REVIEW",
            confidence=0.95,
            reason="LLM 修正"
        ))
        
        router = HybridRouter(semantic_router=mock_semantic)
        decision = router.route("看看这个需求", llm_router_fn=mock_llm_fn)
        
        assert decision.intent == "START_REQUIREMENT_REVIEW"
        assert decision.source == "llm"
        mock_llm_fn.assert_called_once()


class TestRoutingDecision:
    
    def test_dataclass_fields(self):
        from backend.agents.lisa.routing.hybrid_router import RoutingDecision
        
        decision = RoutingDecision(
            intent="START_TEST_DESIGN",
            confidence=0.95,
            source="semantic",
            latency_ms=15.5,
            reason="高置信度匹配"
        )
        
        assert decision.intent == "START_TEST_DESIGN"
        assert decision.confidence == 0.95
        assert decision.source == "semantic"
        assert decision.latency_ms == 15.5
        assert decision.reason == "高置信度匹配"
