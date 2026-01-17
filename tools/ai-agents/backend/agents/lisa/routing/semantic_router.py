"""语义路由器 - 基于 Embedding 的快速意图识别"""

from typing import Tuple, Optional, Any
import logging

try:
    from semantic_router import Route, RouteLayer
    from semantic_router.encoders import BaseEncoder
    SEMANTIC_ROUTER_AVAILABLE = True
except ImportError:
    SEMANTIC_ROUTER_AVAILABLE = False
    Route = None
    RouteLayer = None
    BaseEncoder = None

logger = logging.getLogger(__name__)

TEST_DESIGN_UTTERANCES = [
    "帮我设计测试用例",
    "我需要测试方案",
    "做一下测试设计",
    "给我写测试case",
    "测试这个功能",
    "需要测试计划",
    "帮我写测试",
    "做测试分析",
    "设计一套测试",
    "写一下测试用例",
]

REQUIREMENT_REVIEW_UTTERANCES = [
    "帮我评审需求",
    "分析这个需求的可测试性",
    "需求有什么问题",
    "评审一下这个PRD",
    "检查需求质量",
    "需求分析",
    "看看这个需求",
    "审查需求文档",
    "需求评审",
    "检查这个需求",
]


class LisaSemanticRouter:
    
    def __init__(self, encoder: Optional[Any] = None):
        if not SEMANTIC_ROUTER_AVAILABLE:
            logger.warning("semantic-router 库未安装，语义路由将不可用")
            self._route_layer = None
            return
        
        if encoder is None:
            try:
                from semantic_router.encoders import OpenAIEncoder
                encoder = OpenAIEncoder()
                logger.info("使用默认 OpenAI encoder 初始化语义路由")
            except Exception as e:
                logger.warning(f"无法创建默认 encoder: {e}，语义路由将不可用")
                self._route_layer = None
                return
        
        self._encoder = encoder
        self._route_layer = None
        self._init_routes()
    
    def _init_routes(self):
        if not SEMANTIC_ROUTER_AVAILABLE or self._encoder is None:
            return
            
        test_design_route = Route(
            name="START_TEST_DESIGN",
            utterances=TEST_DESIGN_UTTERANCES,
        )
        requirement_review_route = Route(
            name="START_REQUIREMENT_REVIEW",
            utterances=REQUIREMENT_REVIEW_UTTERANCES,
        )
        
        self._route_layer = RouteLayer(
            encoder=self._encoder,
            routes=[test_design_route, requirement_review_route]
        )
    
    def route(self, user_input: str, threshold: float = 0.7) -> Tuple[Optional[str], float]:
        if self._route_layer is None:
            return None, 0.0
        
        result = self._route_layer(user_input)
        
        if result is None:
            return None, 0.0
        
        name = getattr(result, 'name', None)
        similarity = getattr(result, 'similarity', 0.0) or 0.0
        
        if name and similarity >= threshold:
            return name, similarity
        
        return None, similarity
