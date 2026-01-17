"""
测试路由模块的可观测性功能
"""
import logging
import pytest
from unittest.mock import Mock, patch
from backend.agents.lisa.routing.observability import measure_latency, log_routing_decision
from backend.agents.lisa.routing.hybrid_router import RoutingDecision

class TestRouterObservability:
    """测试路由可观测性工具"""

    def test_measure_latency_decorator(self):
        """测试延迟测量装饰器"""
        mock_logger = Mock()
        
        @measure_latency(logger=mock_logger)
        def dummy_function():
            return "result"
            
        result = dummy_function()
        
        assert result == "result"
        assert mock_logger.info.call_count == 1
        # 验证日志包含耗时信息
        log_args = mock_logger.info.call_args[0][0]
        assert "耗时" in log_args or "latency" in log_args

    def test_log_routing_decision_structure(self):
        """测试路由决策日志结构"""
        mock_logger = Mock()
        
        decision = RoutingDecision(
            intent="TEST_INTENT",
            confidence=0.95,
            source="semantic",
            latency_ms=10.5,
            reason="similarity match"
        )
        
        log_routing_decision(decision, logger=mock_logger)
        
        assert mock_logger.info.call_count == 1
        log_msg = mock_logger.info.call_args[0][0]
        
        # 验证关键字段都在日志中
        assert "TEST_INTENT" in log_msg
        assert "0.95" in log_msg
        assert "semantic" in log_msg
        assert "10.5ms" in log_msg
