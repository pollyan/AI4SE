from pathlib import Path

from flask import Blueprint

from app import create_app
from routes import api_bp


def test_routes_module_exposes_api_blueprint() -> None:
    assert isinstance(api_bp, Blueprint)
    assert api_bp.name == "new_agents_api"
    assert api_bp.url_prefix == "/api"


def test_create_app_registers_api_blueprint() -> None:
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
    })

    rules = {rule.rule for rule in app.url_map.iter_rules()}
    assert "/api/health" in rules
    assert "/api/config" in rules
    assert "/api/agent/runs/stream" in rules
    assert "/api/utils/mermaid/repair" in rules
    assert "/api/chat/stream" not in rules


def test_app_module_does_not_define_concrete_api_routes() -> None:
    app_source = Path(__file__).resolve().parents[1].joinpath("app.py")

    assert "@app.route(" not in app_source.read_text(encoding="utf-8")


def test_routes_module_delegates_sse_response_wrapping() -> None:
    routes_source = Path(__file__).resolve().parents[1].joinpath("routes.py")
    source = routes_source.read_text(encoding="utf-8")

    assert "Response(" not in source
    assert "text/event-stream" not in source


def test_routes_module_delegates_error_response_and_config_guards() -> None:
    routes_source = Path(__file__).resolve().parents[1].joinpath("routes.py")
    source = routes_source.read_text(encoding="utf-8")

    assert 'jsonify({"error":' not in source
    assert "系统未配置默认 LLM" not in source
    assert "require_default_llm_config(" in source


def test_routes_module_delegates_test_asset_routes() -> None:
    routes_source = Path(__file__).resolve().parents[1].joinpath("routes.py")
    source = routes_source.read_text(encoding="utf-8")

    assert "register_test_asset_routes(api_bp)" in source
    assert "def agent_run_test_assets(" not in source
