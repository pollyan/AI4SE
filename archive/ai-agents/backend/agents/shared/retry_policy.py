"""
共享 RetryPolicy 配置模块

Lisa 和 Alex 智能体共用此模块中的重试策略配置。
修改此处配置会影响所有智能体的重试行为。
"""

import logging
from langgraph.types import RetryPolicy

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# 统一配置（修改这里会影响所有智能体）
# ═══════════════════════════════════════════════════════════════════════════════

LLM_RETRY_CONFIG = {
    "max_attempts": 3,           # 最大重试次数
    "initial_interval": 1.0,     # 首次重试等待时间（秒）
    "backoff_factor": 2.0,       # 退避系数（1s → 2s → 4s）
    "max_interval": 10.0,        # 最大等待时间（秒）
}


# ═══════════════════════════════════════════════════════════════════════════════
# 可重试的异常类型
# ═══════════════════════════════════════════════════════════════════════════════

# 网络相关的临时性错误，值得重试
RETRYABLE_EXCEPTIONS = (
    TimeoutError,
    ConnectionError,
    ConnectionResetError,
    ConnectionRefusedError,
)

# 注意：以下错误不应重试，应直接抛出给前端显示
# - RateLimitError: API 配额用尽或欠费
# - AuthenticationError: API Key 无效
# - InvalidRequestError: 请求格式错误


# ═══════════════════════════════════════════════════════════════════════════════
# 重试策略工厂函数
# ═══════════════════════════════════════════════════════════════════════════════

def get_llm_retry_policy() -> RetryPolicy:
    """
    获取 LLM 调用节点的重试策略
    
    针对网络超时、连接错误等临时性错误进行重试。
    RateLimitError 等账户问题不会重试，会直接抛出。
    
    重试策略：
    - 最多重试 3 次
    - 退避时间：1s → 2s → 4s
    
    Returns:
        RetryPolicy: 配置好的重试策略
    """
    return RetryPolicy(
        max_attempts=LLM_RETRY_CONFIG["max_attempts"],
        initial_interval=LLM_RETRY_CONFIG["initial_interval"],
        backoff_factor=LLM_RETRY_CONFIG["backoff_factor"],
        max_interval=LLM_RETRY_CONFIG["max_interval"],
        retry_on=RETRYABLE_EXCEPTIONS,
    )


def get_conservative_retry_policy() -> RetryPolicy:
    """
    获取保守的重试策略（用于非关键节点）
    
    只重试 2 次，适用于非 LLM 调用的辅助节点。
    
    Returns:
        RetryPolicy: 配置好的重试策略
    """
    return RetryPolicy(
        max_attempts=2,
        retry_on=RETRYABLE_EXCEPTIONS,
    )
