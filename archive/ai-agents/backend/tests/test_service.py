import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from backend.agents.service import LangchainAssistantService
from langchain_core.messages import HumanMessage, AIMessage

@pytest.fixture
def mock_config():
    return {"model_name": "gpt-4", "base_url": "http://test", "api_key": "sk-test"}

@pytest.mark.asyncio
@patch("backend.agents.lisa.create_lisa_graph")
@patch("backend.models.RequirementsAIConfig.get_default_config")
async def test_service_initialization_real(mock_get_config, mock_create_graph, mock_config):
    mock_db_config = MagicMock()
    mock_db_config.get_config_for_ai_service.return_value = mock_config
    mock_get_config.return_value = mock_db_config
    
    service = LangchainAssistantService("lisa")
    await service.initialize()
    
    mock_create_graph.assert_called_once_with(mock_config)
    assert service.agent is not None

def test_session_history():
    service = LangchainAssistantService("lisa")
    session_id = "test_session"
    
    service._add_to_history(session_id, "user", "Hello")
    service._add_to_history(session_id, "assistant", "Hi")
    
    history = service._get_session_history(session_id)
    assert len(history) == 2
    assert history[0] == {"role": "user", "content": "Hello"}
    assert history[1] == {"role": "assistant", "content": "Hi"}

def test_build_messages():
    service = LangchainAssistantService("lisa")
    session_id = "test_session"
    service._add_to_history(session_id, "user", "Prev User")
    service._add_to_history(session_id, "assistant", "Prev AI")
    
    messages = service._build_messages(session_id, "New User")
    
    assert len(messages) == 3
    assert isinstance(messages[0], HumanMessage)
    assert messages[0].content == "Prev User"
    assert isinstance(messages[1], AIMessage)
    assert messages[1].content == "Prev AI"
    assert isinstance(messages[2], HumanMessage)
    assert messages[2].content == "New User"

@pytest.mark.asyncio
async def test_test_connection_success():
    service = LangchainAssistantService("lisa")
    service.agent = AsyncMock()
    service.config = {"model_name": "test"}
    
    mock_response = {"messages": [AIMessage(content="Hello World")]}
    service.agent.ainvoke.return_value = mock_response
    
    result = await service.test_connection([{"role": "user", "content": "Hi"}])
    
    assert result == "Hello World"

@pytest.mark.asyncio
async def test_test_connection_failure():
    service = LangchainAssistantService("lisa")
    service.agent = AsyncMock()
    service.config = {"model_name": "test"}
    
    service.agent.ainvoke.return_value = {"messages": []}
    
    with pytest.raises(Exception, match="LLM 返回了空响应"):
        await service.test_connection([{"role": "user", "content": "Hi"}])
