from unittest.mock import patch

from app import create_app
from models import LlmConfig
from route_guards import require_default_llm_config


def test_require_default_llm_config_returns_active_config() -> None:
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
    })
    config = LlmConfig(
        config_key="default",
        api_key="sk-test",
        base_url="https://api.test/v1",
        model="test-model",
    )

    with app.app_context():
        with patch("route_guards.get_active_default_llm_config", return_value=config):
            result, error_response = require_default_llm_config(
                request_id="req-1",
                context="chat stream",
            )

    assert result is config
    assert error_response is None


def test_require_default_llm_config_returns_503_error_response_when_missing() -> None:
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
    })

    with app.app_context():
        with patch("route_guards.get_active_default_llm_config", return_value=None):
            result, error_response = require_default_llm_config(
                request_id="req-2",
                context="agent runtime",
            )

    assert result is None
    assert error_response is not None
    response, status_code = error_response
    assert status_code == 503
    assert response.get_json() == {
        "error": "系统未配置默认 LLM，请维护后端默认 LLM 配置后重试"
    }
