"""
测试路由模块的错误处理
"""
import pytest
from unittest.mock import Mock, patch
from backend.agents.lisa.routing.exceptions import RoutingError, SemanticRouterError, LLMRouterError

class TestRouterExceptions:
    """测试路由异常类"""
    
    def test_routing_error_base(self):
        """测试基础路由异常"""
        error = RoutingError("Base error")
        assert str(error) == "Base error"
        assert isinstance(error, Exception)

    def test_semantic_router_error(self):
        """测试语义路由异常"""
        error = SemanticRouterError("Model not loaded", original_error=ValueError("Model missing"))
        assert "Model not loaded" in str(error)
        assert isinstance(error.original_error, ValueError)

class TestErrorHandlingLogic:
    """测试错误处理逻辑"""
    
    def test_safe_routing_context_manager(self):
        """测试安全路由上下文管理器"""
        from backend.agents.lisa.routing.observability import safe_routing_context
        
        # 正常执行
        with safe_routing_context() as ctx:
            result = "success"
        assert result == "success"
        
        # 异常捕获与转换
        with pytest.raises(RoutingError) as excinfo:
            with safe_routing_context(error_message="Routing failed"):
                raise ValueError("Unexpected error")
        
        assert "Routing failed" in str(excinfo.value)
        # 确认原始异常被保留（如果是 Python 3，链式异常自动处理，这里主要测试抛出了 RoutingError）
