"""
语义路由器测试 - TDD Red Phase

测试 LisaSemanticRouter 的意图识别能力。
由于语义路由依赖外部 Embedding API，测试使用 Mock 来隔离外部依赖。
"""

import pytest
from unittest.mock import MagicMock, patch
from dataclasses import dataclass


@dataclass
class MockRouteResult:
    """模拟 semantic-router 的路由结果"""
    name: str | None
    similarity: float


class TestLisaSemanticRouter:
    
    def test_routes_test_design_intent_high_confidence(self):
        from backend.agents.lisa.routing.semantic_router import LisaSemanticRouter
        
        router = LisaSemanticRouter(encoder=MagicMock())
        mock_layer = MagicMock()
        mock_layer.return_value = MockRouteResult(name="START_TEST_DESIGN", similarity=0.92)
        router._route_layer = mock_layer
        
        intent, confidence = router.route("帮我设计测试用例")
        
        assert intent == "START_TEST_DESIGN"
        assert confidence >= 0.7
    
    def test_routes_requirement_review_intent_high_confidence(self):
        from backend.agents.lisa.routing.semantic_router import LisaSemanticRouter
        
        router = LisaSemanticRouter(encoder=MagicMock())
        mock_layer = MagicMock()
        mock_layer.return_value = MockRouteResult(name="START_REQUIREMENT_REVIEW", similarity=0.88)
        router._route_layer = mock_layer
        
        intent, confidence = router.route("帮我评审这个需求")
        
        assert intent == "START_REQUIREMENT_REVIEW"
        assert confidence >= 0.7
    
    def test_returns_none_for_low_confidence(self):
        from backend.agents.lisa.routing.semantic_router import LisaSemanticRouter
        
        router = LisaSemanticRouter(encoder=MagicMock())
        mock_layer = MagicMock()
        mock_layer.return_value = MockRouteResult(name="START_TEST_DESIGN", similarity=0.45)
        router._route_layer = mock_layer
        
        intent, confidence = router.route("你好", threshold=0.7)
        
        assert intent is None
        assert confidence < 0.7
    
    def test_returns_none_for_no_match(self):
        from backend.agents.lisa.routing.semantic_router import LisaSemanticRouter
        
        router = LisaSemanticRouter(encoder=MagicMock())
        mock_layer = MagicMock()
        mock_layer.return_value = MockRouteResult(name=None, similarity=0.0)
        router._route_layer = mock_layer
        
        intent, confidence = router.route("今天天气怎么样")
        
        assert intent is None
        assert confidence == 0.0
    
    def test_custom_threshold(self):
        from backend.agents.lisa.routing.semantic_router import LisaSemanticRouter
        
        router = LisaSemanticRouter(encoder=MagicMock())
        mock_layer = MagicMock()
        mock_layer.return_value = MockRouteResult(name="START_TEST_DESIGN", similarity=0.75)
        router._route_layer = mock_layer
        
        intent1, _ = router.route("测试一下", threshold=0.7)
        assert intent1 == "START_TEST_DESIGN"
        
        intent2, _ = router.route("测试一下", threshold=0.8)
        assert intent2 is None


class TestSemanticRouterUtterances:
    """测试路由锚点定义"""
    
    def test_test_design_utterances_exist(self):
        """应定义测试设计意图的锚点"""
        from backend.agents.lisa.routing.semantic_router import TEST_DESIGN_UTTERANCES
        
        assert len(TEST_DESIGN_UTTERANCES) >= 5
        assert any("测试" in u for u in TEST_DESIGN_UTTERANCES)
    
    def test_requirement_review_utterances_exist(self):
        """应定义需求评审意图的锚点"""
        from backend.agents.lisa.routing.semantic_router import REQUIREMENT_REVIEW_UTTERANCES
        
        assert len(REQUIREMENT_REVIEW_UTTERANCES) >= 5
        assert any("需求" in u or "评审" in u for u in REQUIREMENT_REVIEW_UTTERANCES)
