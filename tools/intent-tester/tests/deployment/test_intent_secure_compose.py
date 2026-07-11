from __future__ import annotations

from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[4]
PRODUCTION_COMPOSE = REPO_ROOT / "docker-compose.prod.yml"
DEV_COMPOSES = (
    (REPO_ROOT / "docker-compose.dev.yml", "intent-tester"),
    (REPO_ROOT / "docker-compose.dev-cn.yml", "intent-tester"),
    (
        REPO_ROOT / "tools/intent-tester/docker/docker-compose.yml",
        "web-app",
    ),
)
WORKFLOW = REPO_ROOT / ".github/workflows/deploy.yml"
DEPLOY_SCRIPT = REPO_ROOT / "scripts/ci/deploy.sh"
NGINX_CONFIG = REPO_ROOT / "nginx/nginx.conf"
HEALTH_SCRIPT = REPO_ROOT / "scripts/health/health_check.sh"


def _load_compose(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _environment(service: dict) -> dict[str, str]:
    environment = service.get("environment", {})
    if isinstance(environment, dict):
        return {str(key): str(value) for key, value in environment.items()}
    parsed = {}
    for item in environment:
        key, separator, value = str(item).partition("=")
        assert separator, f"invalid environment item: {item}"
        parsed[key] = value
    return parsed


def test_production_managed_execution_is_internal_and_fail_closed() -> None:
    text = PRODUCTION_COMPOSE.read_text(encoding="utf-8")
    compose = _load_compose(PRODUCTION_COMPOSE)
    services = compose["services"]

    assert "change_me_in_production" not in text
    assert "host.docker.internal" not in text
    assert {name for name, service in services.items() if service.get("ports")} == {
        "nginx"
    }

    for service_name in ("postgres", "intent-tester", "intent-execution-proxy"):
        assert service_name in services
        assert "ports" not in services[service_name]

    postgres_env = _environment(services["postgres"])
    assert ":?" in postgres_env["POSTGRES_USER"]
    assert ":?" in postgres_env["POSTGRES_PASSWORD"]

    flask_env = _environment(services["intent-tester"])
    assert flask_env["AI4SE_ENV"] == "production"
    assert flask_env["INTENT_PROXY_TOPOLOGY"] == "managed"
    assert flask_env["MIDSCENE_SERVER_URL"] == "http://intent-execution-proxy:3001"
    for key in (
        "DATABASE_URL",
        "SECRET_KEY",
        "INTENT_ACCESS_MODE",
        "INTENT_TESTER_ADMIN_PASSWORD_HASH",
        "INTENT_EXECUTION_ENABLED",
        "INTENT_PUBLIC_ORIGIN",
    ):
        assert ":?" in flask_env[key], key

    proxy = services["intent-execution-proxy"]
    assert proxy["profiles"] == ["execution"]
    assert proxy["build"]["target"] == "proxy"
    proxy_env = _environment(proxy)
    assert proxy_env["INTENT_PROXY_TOPOLOGY"] == "managed"
    assert proxy_env["MAIN_APP_URL"] == (
        "http://intent-tester:5001/intent-tester/api"
    )
    assert ":?" in proxy_env["INTENT_PUBLIC_ORIGIN"]
    for key in (
        "INTENT_PROXY_TOKEN",
        "OPENAI_API_KEY",
        "OPENAI_BASE_URL",
        "MIDSCENE_MODEL_NAME",
    ):
        assert proxy_env[key] == f"${{{key}:-}}", key


def test_production_workflow_validates_complete_environment_before_replacement() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    deploy = DEPLOY_SCRIPT.read_text(encoding="utf-8")
    always_required = (
        "DB_PASSWORD",
        "SECRET_KEY",
        "INTENT_ACCESS_MODE",
        "INTENT_TESTER_ADMIN_PASSWORD_HASH",
        "INTENT_PUBLIC_ORIGIN",
        "INTENT_EXECUTION_ENABLED",
    )
    execution_required = (
        "INTENT_PROXY_TOKEN",
        "OPENAI_API_KEY",
        "OPENAI_BASE_URL",
        "MIDSCENE_MODEL_NAME",
    )

    envs_line = next(line for line in workflow.splitlines() if "envs:" in line)
    for key in (*always_required, *execution_required):
        assert f"{key}: ${{{{ secrets.{key} }}}}" in workflow
        assert key in envs_line
        assert f"write_env_var {key} " in workflow
        assert f"{key}|" in workflow or f"|{key})" in workflow

    validation_end = workflow.index("mv .env.managed .env")
    for key in always_required:
        assert workflow.index(f"require_secret {key} ") < validation_end
    assert 'case "$INTENT_EXECUTION_ENABLED" in' in workflow
    assert 'if [ "$INTENT_EXECUTION_ENABLED" = "true" ]; then' in workflow
    for key in execution_required:
        assert workflow.index(f"require_secret {key} ") < validation_end

    assert "validate_deploy_environment" in deploy
    assert 'COMPOSE_PROFILE_ARGS="--profile execution"' in deploy
    assert deploy.index("validate_deploy_environment") < deploy.index(
        'log_info "停止现有服务..."'
    )


def test_development_compose_closes_managed_loop_without_host_bridge() -> None:
    for compose_path, flask_service_name in DEV_COMPOSES:
        text = compose_path.read_text(encoding="utf-8")
        services = _load_compose(compose_path)["services"]
        flask = services[flask_service_name]
        flask_env = _environment(flask)

        assert "host.docker.internal" not in text, compose_path
        assert "ports" not in services["postgres"], compose_path
        assert flask["ports"] == ["127.0.0.1:5001:5001"], compose_path
        assert flask_env["AI4SE_ENV"] == "development"
        assert flask_env["INTENT_ACCESS_MODE"] == "local-dev"
        assert flask_env["INTENT_PUBLIC_ORIGIN"] == "http://127.0.0.1:5001"
        assert flask_env["INTENT_PROXY_TOPOLOGY"] == "managed"
        assert flask_env["MIDSCENE_SERVER_URL"] == (
            "http://intent-execution-proxy:3001"
        )

        proxy = services["intent-execution-proxy"]
        assert "ports" not in proxy, compose_path
        assert proxy["build"]["target"] == "proxy"
        proxy_env = _environment(proxy)
        assert proxy_env["INTENT_PROXY_TOPOLOGY"] == "managed"
        assert proxy_env["MAIN_APP_URL"] == (
            f"http://{flask_service_name}:5001/intent-tester/api"
        )


def test_gateway_preserves_intent_static_namespace_to_flask() -> None:
    nginx = NGINX_CONFIG.read_text(encoding="utf-8")

    intent_static = nginx.split("location /intent-tester/static/ {", 1)[1].split(
        "}", 1
    )[0]
    assert "proxy_pass http://intent_tester;" in intent_static
    assert "proxy_pass http://intent_tester/static" not in intent_static


def test_production_health_uses_gateway_and_declared_access_outcomes() -> None:
    deploy = DEPLOY_SCRIPT.read_text(encoding="utf-8")
    health = HEALTH_SCRIPT.read_text(encoding="utf-8")

    assert "localhost:5001" not in deploy
    assert "localhost:5001" not in health
    assert 'http://localhost/intent-tester/health' in deploy
    assert '"ai4se-db-prod"' in health
    assert '"ai4se-intent-tester-prod"' in health
    assert '"ai4se-gateway-prod"' in health
    assert "200|401" in health
    assert "200|302|403" in health
