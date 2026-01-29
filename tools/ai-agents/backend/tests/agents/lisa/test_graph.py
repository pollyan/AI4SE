import pytest
from unittest.mock import MagicMock, patch
from langgraph.checkpoint.memory import MemorySaver
from backend.agents.lisa.graph import create_lisa_graph, get_graph_initial_state

@pytest.fixture
def mock_config():
    return {"model_name": "gpt-4", "base_url": "http://test", "api_key": "sk-test"}

@patch("backend.agents.lisa.graph.create_llm_from_config")
@patch("backend.agents.lisa.graph.get_checkpointer")
def test_create_lisa_graph_structure(mock_get_checkpointer, mock_create_llm, mock_config):
    # LangGraph validates checkpointer type, must use real MemorySaver
    test_checkpointer = MemorySaver()
    mock_get_checkpointer.return_value = test_checkpointer
    
    compiled_graph = create_lisa_graph(mock_config)
    
    assert compiled_graph.checkpointer is test_checkpointer
    
    nodes = compiled_graph.nodes
    assert "intent_router" in nodes
    assert "clarify_intent" in nodes
    assert "reasoning_node" in nodes
    assert "artifact_node" in nodes
    
    mock_create_llm.assert_called_once_with(mock_config)

def test_get_graph_initial_state():
    state = get_graph_initial_state()
    assert "messages" in state
    assert "artifacts" in state