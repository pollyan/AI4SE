"""
共享 RetryPolicy 模块单元测试

测试 shared/retry_policy.py 中的重试策略配置。
"""

import pytest
from langgraph.types import RetryPolicy


class TestLLMRetryConfig:
    """测试 LLM_RETRY_CONFIG 配置"""
    
    def test_config_has_required_keys(self):
        """配置应包含所有必需的键"""
        from backend.agents.shared.retry_policy import LLM_RETRY_CONFIG
        
        assert "max_attempts" in LLM_RETRY_CONFIG
        assert "initial_interval" in LLM_RETRY_CONFIG
        assert "backoff_factor" in LLM_RETRY_CONFIG
        assert "max_interval" in LLM_RETRY_CONFIG
    
    def test_max_attempts_is_three(self):
        """最大重试次数应为 3"""
        from backend.agents.shared.retry_policy import LLM_RETRY_CONFIG
        
        assert LLM_RETRY_CONFIG["max_attempts"] == 3
    
    def test_backoff_factor_is_two(self):
        """退避系数应为 2.0（1s -> 2s -> 4s）"""
        from backend.agents.shared.retry_policy import LLM_RETRY_CONFIG
        
        assert LLM_RETRY_CONFIG["backoff_factor"] == 2.0


class TestRetryableExceptions:
    """测试 RETRYABLE_EXCEPTIONS 配置"""
    
    def test_includes_network_errors(self):
        """应包含网络相关的临时性错误"""
        from backend.agents.shared.retry_policy import RETRYABLE_EXCEPTIONS
        
        assert TimeoutError in RETRYABLE_EXCEPTIONS
        assert ConnectionError in RETRYABLE_EXCEPTIONS
        assert ConnectionResetError in RETRYABLE_EXCEPTIONS
        assert ConnectionRefusedError in RETRYABLE_EXCEPTIONS
    
    def test_does_not_include_rate_limit_or_auth_errors(self):
        """不应包含 RateLimitError 等账户问题（这些应直接抛出）"""
        from backend.agents.shared.retry_policy import RETRYABLE_EXCEPTIONS
        
        exception_names = [exc.__name__ for exc in RETRYABLE_EXCEPTIONS]
        
        assert "RateLimitError" not in exception_names
        assert "AuthenticationError" not in exception_names
        assert "InvalidRequestError" not in exception_names


class TestGetLLMRetryPolicy:
    """测试 get_llm_retry_policy 函数"""
    
    def test_returns_retry_policy_instance(self):
        """应返回 RetryPolicy 实例"""
        from backend.agents.shared.retry_policy import get_llm_retry_policy
        
        policy = get_llm_retry_policy()
        
        assert isinstance(policy, RetryPolicy)
    
    def test_policy_has_correct_max_attempts(self):
        """RetryPolicy 应有正确的 max_attempts"""
        from backend.agents.shared.retry_policy import get_llm_retry_policy, LLM_RETRY_CONFIG
        
        policy = get_llm_retry_policy()
        
        assert policy.max_attempts == LLM_RETRY_CONFIG["max_attempts"]
    
    def test_policy_has_correct_retry_on(self):
        """RetryPolicy 应配置正确的可重试异常"""
        from backend.agents.shared.retry_policy import get_llm_retry_policy, RETRYABLE_EXCEPTIONS
        
        policy = get_llm_retry_policy()
        
        assert policy.retry_on == RETRYABLE_EXCEPTIONS
    
    def test_each_call_returns_new_instance(self):
        """每次调用应返回新实例（非单例）"""
        from backend.agents.shared.retry_policy import get_llm_retry_policy
        
        policy1 = get_llm_retry_policy()
        policy2 = get_llm_retry_policy()
        
        assert policy1 is not policy2


class TestGetConservativeRetryPolicy:
    """测试 get_conservative_retry_policy 函数"""
    
    def test_returns_retry_policy_instance(self):
        """应返回 RetryPolicy 实例"""
        from backend.agents.shared.retry_policy import get_conservative_retry_policy
        
        policy = get_conservative_retry_policy()
        
        assert isinstance(policy, RetryPolicy)
    
    def test_policy_has_fewer_attempts_than_llm_policy(self):
        """保守策略应比 LLM 策略重试次数少"""
        from backend.agents.shared.retry_policy import (
            get_llm_retry_policy, 
            get_conservative_retry_policy
        )
        
        llm_policy = get_llm_retry_policy()
        conservative_policy = get_conservative_retry_policy()
        
        assert conservative_policy.max_attempts < llm_policy.max_attempts
    
    def test_policy_has_same_retry_on_as_llm_policy(self):
        """保守策略应使用相同的可重试异常"""
        from backend.agents.shared.retry_policy import (
            get_llm_retry_policy, 
            get_conservative_retry_policy
        )
        
        llm_policy = get_llm_retry_policy()
        conservative_policy = get_conservative_retry_policy()
        
        assert conservative_policy.retry_on == llm_policy.retry_on


class TestRetryPolicyExport:
    """测试 shared/__init__.py 的导出"""
    
    def test_get_llm_retry_policy_exported(self):
        """get_llm_retry_policy 应从 shared 模块导出"""
        from backend.agents.shared import get_llm_retry_policy
        
        assert callable(get_llm_retry_policy)
    
    def test_get_conservative_retry_policy_exported(self):
        """get_conservative_retry_policy 应从 shared 模块导出"""
        from backend.agents.shared import get_conservative_retry_policy
        
        assert callable(get_conservative_retry_policy)
