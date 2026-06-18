from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]


def read_module(module_name: str) -> str:
    return BACKEND_DIR.joinpath(module_name).read_text(encoding="utf-8")


def test_app_module_stays_application_factory_shell() -> None:
    source = read_module("app.py")

    assert "@app.route(" not in source
    assert "OpenAI" not in source
    assert "chat.completions.create" not in source
    assert "Response(" not in source
    assert "text/event-stream" not in source
    assert "LlmConfig.query" not in source


def test_routes_module_stays_http_orchestration_layer() -> None:
    source = read_module("routes.py")

    assert "OpenAI" not in source
    assert "chat.completions.create" not in source
    assert "build_pydantic_agent_runtime" not in source
    assert "ChatDeltaEvent" not in source
    assert "AgentTurnEvent" not in source
    assert "ErrorEvent" not in source
    assert "Response(" not in source
    assert "text/event-stream" not in source
    assert 'jsonify({"error":' not in source
    assert "except Exception" not in source
    assert "LlmConfig.query" not in source
    assert "get_active_default_llm_config" not in source


def test_stream_services_do_not_depend_on_flask_http_response_layer() -> None:
    source = read_module("stream_services.py")

    assert "from flask" not in source
    assert "jsonify" not in source
    assert "Response(" not in source
    assert "text/event-stream" not in source
    assert "except Exception" not in source


def test_stream_services_does_not_import_pydantic_ai_at_module_load() -> None:
    source = read_module("stream_services.py")

    assert "from pydantic_ai" not in source
    assert "import pydantic_ai" not in source


def test_low_level_helpers_do_not_depend_on_flask_request_context() -> None:
    for module_name in [
        "llm_client.py",
        "request_schemas.py",
        "config_service.py",
        "sse_encoder.py",
    ]:
        source = read_module(module_name)

        assert "from flask" not in source
        assert "current_app" not in source
        assert "request." not in source
        assert "except Exception" not in source
