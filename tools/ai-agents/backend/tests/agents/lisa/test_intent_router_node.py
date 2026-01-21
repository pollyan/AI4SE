import pytest
from unittest.mock import MagicMock, patch
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.types import Command
from backend.agents.lisa.nodes.intent_router import intent_router_node
from backend.agents.lisa.routing.hybrid_router import RoutingDecision
from backend.agents.lisa.state import LisaState
from typing import cast

@pytest.fixture
def mock_llm():
    return MagicMock()

@pytest.fixture
def mock_router():
    with patch("backend.agents.lisa.nodes.intent_router.get_hybrid_router") as mock_get_router:
        router = MagicMock()
        mock_get_router.return_value = router
        yield router

def test_intent_router_sticky_workflow_on_unknown_intent(mock_llm, mock_router):
    state = {
        "messages": [HumanMessage(content="好的")],
        "current_workflow": "test_design",
        "artifacts": {}
    }
    
    mock_router.route.return_value = RoutingDecision(
        intent=None,
        confidence=0.0,
        source="llm",
        latency_ms=100,
        reason="Unclear"
    )
    
    command = intent_router_node(cast(LisaState, state), mock_llm)
    
    assert command.goto == "reasoning_node"

def test_intent_router_unknown_intent_no_workflow(mock_llm, mock_router):
    state = {
        "messages": [HumanMessage(content="Hello")],
        "current_workflow": None,
        "artifacts": {}
    }
    
    mock_router.route.return_value = RoutingDecision(
        intent=None,
        confidence=0.0,
        source="llm",
        latency_ms=100,
        reason="Unclear"
    )
    
    command = intent_router_node(cast(LisaState, state), mock_llm)
    
    assert command.goto == "clarify_intent"

def test_intent_router_start_test_design(mock_llm, mock_router):
    state = {
        "messages": [HumanMessage(content="Start testing")],
        "current_workflow": None,
        "artifacts": {}
    }
    
    mock_router.route.return_value = RoutingDecision(
        intent="START_TEST_DESIGN",
        confidence=0.9,
        source="keyword",
        latency_ms=50
    )
    
    command = intent_router_node(cast(LisaState, state), mock_llm)
    
    assert command.goto == "reasoning_node"
    assert command.update is not None
    assert command.update["current_workflow"] == "test_design"

def test_intent_router_start_req_review(mock_llm, mock_router):
    state = {
        "messages": [HumanMessage(content="Review requirements")],
        "current_workflow": None,
        "artifacts": {}
    }
    
    mock_router.route.return_value = RoutingDecision(
        intent="START_REQUIREMENT_REVIEW",
        confidence=0.9,
        source="keyword",
        latency_ms=50
    )
    
    command = intent_router_node(cast(LisaState, state), mock_llm)
    
    assert command.goto == "reasoning_node"
    assert command.update is not None
    assert command.update["current_workflow"] == "requirement_review"

def test_intent_router_no_messages(mock_llm):
    state = {
        "messages": [],
        "current_workflow": None,
        "artifacts": {}
    }
    
    command = intent_router_node(cast(LisaState, state), mock_llm)
    
    assert command.goto == "clarify_intent"

def test_intent_router_only_ai_messages(mock_llm):
    state = {
        "messages": [AIMessage(content="Hello")],
        "current_workflow": None,
        "artifacts": {}
    }
    
    command = intent_router_node(cast(LisaState, state), mock_llm)
    
    assert command.goto == "clarify_intent"

def test_intent_router_exception_handling(mock_llm, mock_router):
    state = {
        "messages": [HumanMessage(content="Crash me")],
        "current_workflow": None,
        "artifacts": {}
    }
    
    mock_router.route.side_effect = Exception("Router crash")
    
    command = intent_router_node(cast(LisaState, state), mock_llm)
    
    assert command.goto == "clarify_intent"
