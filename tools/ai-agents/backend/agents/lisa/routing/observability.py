import time
import functools
import logging
from typing import Callable, Any, Generator
from contextlib import contextmanager
from .hybrid_router import RoutingDecision
from .exceptions import RoutingError

def measure_latency(logger: logging.Logger):
    """测量函数执行延迟的装饰器"""
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                latency = (time.perf_counter() - start) * 1000
                logger.info(f"Function {func.__name__} 耗时: {latency:.2f}ms")
        return wrapper
    return decorator

def log_routing_decision(decision: RoutingDecision, logger: logging.Logger):
    """记录结构化路由决策日志"""
    logger.info(
        f"Routing Decision: intent={decision.intent}, "
        f"confidence={decision.confidence:.2f}, "
        f"source={decision.source}, "
        f"latency={decision.latency_ms:.1f}ms, "
        f"reason={decision.reason}"
    )

@contextmanager
def safe_routing_context(error_message: str = "Routing failed") -> Generator[None, None, None]:
    """安全路由上下文管理器，捕获并包装异常"""
    try:
        yield
    except RoutingError:
        raise
    except Exception as e:
        raise RoutingError(error_message) from e
