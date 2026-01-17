from typing import Dict

class RoutingConfig:
    """路由配置常量"""
    SEMANTIC_HIGH_THRESHOLD = 0.85
    SEMANTIC_LOW_THRESHOLD = 0.5

def get_intent_workflow_map() -> Dict[str, str]:
    """获取意图到工作流的映射"""
    return {
        "START_TEST_DESIGN": "test_design",
        "START_REQUIREMENT_REVIEW": "requirement_review",
    }
