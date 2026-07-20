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
        "message": "模型连接检测失败",
    }


@patch("config_service.stream_chat_completion_content")
def test_check_default_llm_config_never_reflects_provider_secret_canary(
    mock_stream,
) -> None:
    secret = "provider-authorization-secret-canary"
    mock_stream.side_effect = LlmClientError(
        f"upstream rejected Authorization: Bearer {secret}"
    )
    config = LlmConfig(
        config_key="default",
        api_key=secret,
        base_url="https://api.test.com/v1",
        model="test-model",
    )

    result = check_default_llm_config(config)

    assert result["message"] == "模型连接检测失败"
    assert secret not in str(result)
