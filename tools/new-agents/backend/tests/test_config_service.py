from unittest.mock import patch

from config_service import check_default_llm_config
from llm_client import LlmClientError
from models import LlmConfig


@patch("config_service.stream_chat_completion_content")
def test_check_default_llm_config_calls_configured_model(mock_stream) -> None:
    mock_stream.return_value = ["ok"]
    config = LlmConfig(
        config_key="default",
        api_key="secret-api-key",
        base_url="https://api.test.com/v1",
        model="test-model",
    )

    result = check_default_llm_config(config)

    assert result == {
        "ok": True,
        "baseUrl": "https://api.test.com/v1",
        "model": "test-model",
        "message": "模型配置可用",
    }
    call = mock_stream.call_args.kwargs
    assert call["api_key"] == "secret-api-key"
    assert call["base_url"] == "https://api.test.com/v1"
    assert call["model"] == "test-model"
    assert call["temperature"] == 0
    assert call["messages"][0]["role"] == "system"
    assert call["messages"][1]["role"] == "user"


@patch("config_service.stream_chat_completion_content")
def test_check_default_llm_config_returns_unavailable_on_client_error(
    mock_stream,
) -> None:
    mock_stream.side_effect = LlmClientError("provider unavailable")
    config = LlmConfig(
        config_key="default",
        api_key="secret-api-key",
        base_url="https://api.test.com/v1",
        model="test-model",
    )

    result = check_default_llm_config(config)

    assert result == {
        "ok": False,
        "baseUrl": "https://api.test.com/v1",
        "model": "test-model",
        "message": "provider unavailable",
    }
