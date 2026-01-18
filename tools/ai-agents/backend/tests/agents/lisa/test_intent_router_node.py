
import pytest
from unittest.mock import MagicMock, patch
from langchain_core.messages import HumanMessage
from langgraph.types import Command

from backend.agents.lisa.nodes.intent_router import intent_router_node
from backend.agents.lisa.routing.hybrid_router import RoutingDecision

@pytest.mark.unit
def test_intent_router_sticky_workflow_on_unknown_intent():
    """
    [TDD] 测试：当在工作流中遇到不明意图时，应默认继续当前工作流（粘性）
    
    场景：
    1. 当前在 test_design 工作流中
    2. 用户输入 "好的"
    3. Router 无法识别明确意图 (intent=None)
    
    期望：goto="workflow_test_design"
    现状（Bug）：goto="clarify_intent"
    """
    # 1. Setup state
    state = {
        "messages": [HumanMessage(content="好的")],
        "current_workflow": "test_design",
        "artifacts": {}
    }
    
    mock_llm = MagicMock()
    
    # 2. Mock HybridRouter to return None intent
    with patch("backend.agents.lisa.nodes.intent_router.get_hybrid_router") as mock_get_router:
        mock_router = MagicMock()
        mock_get_router.return_value = mock_router
        
        # 模拟 Router 返回不明意图
        mock_router.route.return_value = RoutingDecision(
            intent=None,
            confidence=0.0,
            source="llm",
            latency_ms=100,
            reason="Unclear"
        )
        
        # 3. Execute node
        command = intent_router_node(state, mock_llm)
        
        # 4. Assert
        # 我们期望它保持粘性，继续工作流
        assert command.goto == "workflow_test_design", f"应保持在工作流中，实际跳转到: {command.goto}"
