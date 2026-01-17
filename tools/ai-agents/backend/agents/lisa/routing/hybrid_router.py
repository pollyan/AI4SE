"""混合路由器 - 结合语义路由和 LLM 路由"""

from typing import Optional, Any, Callable, Dict
from dataclasses import dataclass, field
import time
import logging

from .semantic_router import LisaSemanticRouter
from .config import RoutingConfig

logger = logging.getLogger(__name__)


@dataclass
class RoutingDecision:
    intent: Optional[str]
    confidence: float
    source: str  # "semantic" | "llm"
    latency_ms: float
    reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)


class HybridRouter:
    
    def __init__(self, semantic_router: Optional[LisaSemanticRouter] = None):
        self._semantic_router = semantic_router
    
    @property
    def semantic_router(self) -> LisaSemanticRouter:
        if self._semantic_router is None:
            self._semantic_router = LisaSemanticRouter()
        return self._semantic_router
    
    def route(
        self, 
        user_input: str, 
        llm_router_fn: Optional[Callable] = None,
        context: Optional[dict] = None
    ) -> RoutingDecision:
        start_time = time.perf_counter()
        
        intent, semantic_confidence = self.semantic_router.route(user_input)
        semantic_latency = (time.perf_counter() - start_time) * 1000
        
        logger.info(f"语义路由: intent={intent}, confidence={semantic_confidence:.3f}, latency={semantic_latency:.1f}ms")
        
        if intent and semantic_confidence >= RoutingConfig.SEMANTIC_HIGH_THRESHOLD:
            return RoutingDecision(
                intent=intent,
                confidence=semantic_confidence,
                source="semantic",
                latency_ms=semantic_latency,
                reason=f"语义匹配置信度 {semantic_confidence:.2f}"
            )
        
        if llm_router_fn is None:
            return RoutingDecision(
                intent=intent if semantic_confidence >= RoutingConfig.SEMANTIC_LOW_THRESHOLD else None,
                confidence=semantic_confidence,
                source="semantic",
                latency_ms=semantic_latency,
                reason="无 LLM fallback"
            )
        
        llm_start = time.perf_counter()
        llm_result = llm_router_fn(user_input, context)
        llm_latency = (time.perf_counter() - llm_start) * 1000
        total_latency = (time.perf_counter() - start_time) * 1000
        
        logger.info(f"LLM路由: intent={llm_result.intent}, confidence={llm_result.confidence:.3f}, latency={llm_latency:.1f}ms")
        
        metadata = {}
        if hasattr(llm_result, 'clarification') and llm_result.clarification:
            metadata["clarification"] = llm_result.clarification
        if hasattr(llm_result, 'entities') and llm_result.entities:
            metadata["entities"] = llm_result.entities
        
        return RoutingDecision(
            intent=llm_result.intent,
            confidence=llm_result.confidence,
            source="llm",
            latency_ms=total_latency,
            reason=llm_result.reason,
            metadata=metadata
        )
