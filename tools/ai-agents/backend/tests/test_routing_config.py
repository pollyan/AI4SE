"""
测试路由配置
"""
from backend.agents.lisa.routing.config import get_intent_workflow_map, RoutingConfig

class TestRoutingConfig:
    def test_default_intent_mapping(self):
        """测试默认意图映射"""
        mapping = get_intent_workflow_map()
        assert mapping["START_TEST_DESIGN"] == "test_design"
        assert mapping["START_REQUIREMENT_REVIEW"] == "requirement_review"

    def test_routing_config_constants(self):
        """测试配置常量"""
        assert RoutingConfig.SEMANTIC_HIGH_THRESHOLD == 0.85
        assert RoutingConfig.SEMANTIC_LOW_THRESHOLD == 0.5
