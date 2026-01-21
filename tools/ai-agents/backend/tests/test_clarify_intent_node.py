import pytest
from unittest.mock import MagicMock
from langchain_core.messages import AIMessage, HumanMessage
from backend.agents.lisa.nodes.clarify_intent import clarify_intent_node
from backend.agents.lisa.prompts import CLARIFY_INTENT_MESSAGE
from backend.agents.lisa.state import LisaState
from typing import cast

@pytest.fixture
def mock_llm():
    return MagicMock()

def test_clarify_intent_node_dynamic_question(mock_llm):
    dynamic_question = "Could you please clarify X?"
    state = {
        "messages": [HumanMessage(content="Help me")],
        "clarification": dynamic_question,
        "current_workflow": "test_design",
        "current_stage_id": "clarify",
        "plan": [],
        "artifacts": {}
    }
    
    new_state = clarify_intent_node(cast(LisaState, state), mock_llm)
    
    assert len(new_state["messages"]) == 2
    last_message = new_state["messages"][-1]
    assert isinstance(last_message, AIMessage)
    assert last_message.content == dynamic_question

def test_clarify_intent_node_default_message(mock_llm):
    state = {
        "messages": [HumanMessage(content="Help me")],
        "clarification": None,
        "current_workflow": "test_design",
        "current_stage_id": "clarify",
        "plan": [],
        "artifacts": {}
    }
    
    new_state = clarify_intent_node(cast(LisaState, state), mock_llm)
    
    assert len(new_state["messages"]) == 2
    last_message = new_state["messages"][-1]
    assert isinstance(last_message, AIMessage)
    assert last_message.content == CLARIFY_INTENT_MESSAGE

def test_clarify_intent_node_appends_to_history(mock_llm):
    existing_messages = [
        HumanMessage(content="Hello"),
        AIMessage(content="Hi"),
        HumanMessage(content="I want X")
    ]
    state = {
        "messages": existing_messages,
        "clarification": "Query?",
        "current_workflow": "test_design",
        "current_stage_id": "clarify",
        "plan": [],
        "artifacts": {}
    }
    
    new_state = clarify_intent_node(cast(LisaState, state), mock_llm)
    
    assert len(new_state["messages"]) == len(existing_messages) + 1
    assert new_state["messages"][:-1] == existing_messages
    assert new_state["messages"][-1].content == "Query?"
