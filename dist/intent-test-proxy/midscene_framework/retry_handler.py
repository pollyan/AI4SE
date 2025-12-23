#!/usr/bin/env python3
"""
重试和错误恢复机制
提供指数退避重试和错误处理功能
"""

import asyncio
import random
import logging
from typing import Callable, Any, Union
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """重试配置"""

    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0

    def __post_init__(self):
        """参数验证"""
        if self.max_attempts < 1:
            raise ValueError("max_attempts必须大于0")
        if self.base_delay <= 0:
            raise ValueError("base_delay必须大于0")
        if self.max_delay <= 0:
            raise ValueError("max_delay必须大于0")
        if self.exponential_base <= 1:
            raise ValueError("exponential_base必须大于1")


class RetryHandler:
    """重试处理器"""

    # 可重试的异常类型
    RETRYABLE_EXCEPTIONS = (
        ConnectionError,
        TimeoutError,
        # 可以根据需要添加更多异常类型
    )

    # 限流相关的错误关键字
    RATE_LIMIT_KEYWORDS = [
        "rate limit",
        "rate_limit",
        "too many requests",
        "429",
        "quota exceeded",
        "limit exceeded",
    ]

    @staticmethod
    async def retry_with_backoff(
        func: Callable, config: RetryConfig, *args, **kwargs
    ) -> Any:
        """
        指数退避重试机制

        Args:
            func: 要重试的函数
            config: 重试配置
            *args: 函数参数
            **kwargs: 函数关键字参数

        Returns:
            函数执行结果

        Raises:
            最后一次执行的异常
        """
        last_exception = None

        for attempt in range(config.max_attempts):
            try:
                # 如果是异步函数
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)

                if attempt > 0:
                    logger.info(f"重试成功，第 {attempt + 1} 次尝试")

                return result

            except Exception as e:
                last_exception = e

                # 检查是否为最后一次尝试
                if attempt == config.max_attempts - 1:
                    logger.error(f"重试失败，已达到最大尝试次数 {config.max_attempts}")
                    break

                # 检查是否应该重试
                if not RetryHandler._should_retry(e):
                    logger.warning(f"异常不适合重试: {type(e).__name__}: {str(e)}")
                    break

                # 计算延迟时间
                delay = RetryHandler._calculate_delay(attempt, config, e)

                logger.warning(
                    f"尝试 {attempt + 1} 失败: {type(e).__name__}: {str(e)}, "
                    f"{delay:.2f}秒后重试"
                )

                await asyncio.sleep(delay)

        # 抛出最后一次的异常
        raise last_exception

    @staticmethod
    def _should_retry(exception: Exception) -> bool:
        """
        判断异常是否应该重试

        Args:
            exception: 异常实例

        Returns:
            是否应该重试
        """
        # 检查异常类型
        if isinstance(exception, RetryHandler.RETRYABLE_EXCEPTIONS):
            return True

        # 检查异常消息中的关键字
        error_message = str(exception).lower()

        # 网络相关错误
        network_keywords = [
            "connection",
            "timeout",
            "network",
            "unreachable",
            "refused",
            "reset",
        ]

        for keyword in network_keywords:
            if keyword in error_message:
                return True

        # 限流错误
        for keyword in RetryHandler.RATE_LIMIT_KEYWORDS:
            if keyword in error_message:
                return True

        # 服务器错误 (5xx)
        if any(code in error_message for code in ["500", "502", "503", "504"]):
            return True

        return False

    @staticmethod
    def _calculate_delay(
        attempt: int, config: RetryConfig, exception: Exception
    ) -> float:
        """
        计算延迟时间

        Args:
            attempt: 当前尝试次数（从0开始）
            config: 重试配置
            exception: 异常实例

        Returns:
            延迟时间（秒）
        """
        # 基础指数退避
        delay = config.base_delay * (config.exponential_base**attempt)

        # 限制最大延迟
        delay = min(delay, config.max_delay)

        # 检查是否是限流错误，如果是则使用更长的延迟
        error_message = str(exception).lower()
        if any(
            keyword in error_message for keyword in RetryHandler.RATE_LIMIT_KEYWORDS
        ):
            delay = max(delay, 10.0)  # 限流错误至少等待10秒

        # 添加随机抖动（避免惊群效应）
        jitter = random.uniform(0.1, 0.3) * delay
        delay += jitter

        return delay

    @staticmethod
    async def retry_with_circuit_breaker(
        func: Callable,
        config: RetryConfig,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        *args,
        **kwargs,
    ) -> Any:
        """
        带熔断器的重试机制

        Args:
            func: 要重试的函数
            config: 重试配置
            failure_threshold: 熔断阈值
            recovery_timeout: 恢复超时时间
            *args: 函数参数
            **kwargs: 函数关键字参数

        Returns:
            函数执行结果
        """
        # 简单的熔断器实现（可以扩展为更完整的实现）
        circuit_breaker_key = f"{func.__name__}"

        # 这里可以实现更复杂的熔断器逻辑
        # 目前直接使用基本重试
        return await RetryHandler.retry_with_backoff(func, config, *args, **kwargs)

    @staticmethod
    def create_retry_config(
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
    ) -> RetryConfig:
        """
        创建重试配置的便捷方法

        Args:
            max_attempts: 最大尝试次数
            base_delay: 基础延迟时间
            max_delay: 最大延迟时间
            exponential_base: 指数基数

        Returns:
            重试配置
        """
        return RetryConfig(
            max_attempts=max_attempts,
            base_delay=base_delay,
            max_delay=max_delay,
            exponential_base=exponential_base,
        )


class RetryStats:
    """重试统计"""

    def __init__(self):
        self.total_attempts = 0
        self.total_successes = 0
        self.total_failures = 0
        self.retry_counts = {}

    def record_attempt(self, function_name: str, attempt_count: int, success: bool):
        """记录重试尝试"""
        self.total_attempts += 1

        if success:
            self.total_successes += 1
        else:
            self.total_failures += 1

        if function_name not in self.retry_counts:
            self.retry_counts[function_name] = []

        self.retry_counts[function_name].append(attempt_count)

    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            "total_attempts": self.total_attempts,
            "total_successes": self.total_successes,
            "total_failures": self.total_failures,
            "success_rate": self.total_successes / max(self.total_attempts, 1),
            "retry_counts": self.retry_counts,
        }
