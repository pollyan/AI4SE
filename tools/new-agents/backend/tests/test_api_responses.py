from app import create_app
from api_responses import (
    default_llm_config_missing_response,
    json_error_response,
)


def test_json_error_response_uses_consistent_error_shape() -> None:
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
    })

    with app.app_context():
        response, status_code = json_error_response("请求体为空", 400)

    assert status_code == 400
    assert response.get_json() == {"error": "请求体为空"}


def test_default_llm_config_missing_response_keeps_existing_contract() -> None:
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
    })

    with app.app_context():
        response, status_code = default_llm_config_missing_response()

    assert status_code == 503
    assert response.get_json() == {
        "error": "系统未配置默认 LLM，请维护后端默认 LLM 配置后重试"
    }
