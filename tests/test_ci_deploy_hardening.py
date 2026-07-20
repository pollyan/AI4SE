from pathlib import Path
import subprocess

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "deploy.yml"
DEPLOY_SCRIPT = ROOT / "scripts" / "ci" / "deploy.sh"
PRODUCTION_COMPOSE = ROOT / "docker-compose.prod.yml"
NGINX_CONFIG = ROOT / "nginx" / "nginx.conf"
DEVELOPMENT_COMPOSES = (
    ROOT / "docker-compose.dev.yml",
    ROOT / "docker-compose.dev-cn.yml",
)


def test_new_agents_frontend_ci_runs_typecheck_before_tests():
    workflow = WORKFLOW.read_text(encoding="utf-8")
    section = workflow.split("new-agents-frontend-test:", 1)[1].split(
        "code-quality:", 1
    )[0]

    assert "npm run lint" in section
    assert section.index("npm run lint") < section.index("npm run test")


def test_critical_flake8_is_not_soft_failed():
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert (
        "flake8 tools/intent-tester/backend --count "
        "--select=E9,F63,F7,F82 --show-source --statistics || true"
    ) not in workflow


def test_production_env_sync_avoids_sed_secret_rewrite_and_locks_permissions():
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "sed -i" not in workflow
    assert "chmod 600 .env" in workflow
    assert "is_managed_env_key()" in workflow
    assert "rm -f .env.managed" in workflow
    assert "mv .env.managed .env" in workflow


def test_new_agents_production_config_admin_auth_is_fail_closed():
    workflow = WORKFLOW.read_text(encoding="utf-8")
    compose = PRODUCTION_COMPOSE.read_text(encoding="utf-8")
    nginx = NGINX_CONFIG.read_text(encoding="utf-8")

    for secret_name in (
        "NEW_AGENTS_CONFIG_ADMIN_API_KEY",
        "PROXY_API_KEY",
    ):
        assert f"secrets.{secret_name}" in workflow
        assert f'require_secret {secret_name} "${secret_name}"' in workflow
        assert f'write_env_var {secret_name} "${secret_name}"' in workflow
        assert f"${{{secret_name}:?" in compose
        assert secret_name in DEPLOY_SCRIPT.read_text(encoding="utf-8")
    compose_payload = yaml.safe_load(compose)
    backend_environment = compose_payload["services"]["new-agents-backend"][
        "environment"
    ]
    assert backend_environment["AI4SE_ENV"] == "production"
    assert "NEW_AGENTS_CONFIG_ADMIN_API_KEY" in backend_environment
    assert "PROXY_API_KEY" in backend_environment
    assert '[ "$NEW_AGENTS_CONFIG_ADMIN_API_KEY" = "$PROXY_API_KEY" ]' in workflow
    assert (
        '[ "$NEW_AGENTS_CONFIG_ADMIN_API_KEY" = "$NEW_AGENTS_DEFAULT_LLM_API_KEY" ]'
        in workflow
    )
    assert '[ "$PROXY_API_KEY" = "$NEW_AGENTS_DEFAULT_LLM_API_KEY" ]' in workflow
    assert "umask 077" in workflow
    deploy_script = DEPLOY_SCRIPT.read_text(encoding="utf-8")
    assert (
        '[ "$NEW_AGENTS_CONFIG_ADMIN_API_KEY_VALUE" = "$PROXY_API_KEY_VALUE" ]'
        in deploy_script
    )
    assert (
        '[ "$NEW_AGENTS_CONFIG_ADMIN_API_KEY_VALUE" = "$NEW_AGENTS_DEFAULT_LLM_API_KEY_VALUE" ]'
        in deploy_script
    )
    assert (
        '[ "$PROXY_API_KEY_VALUE" = "$NEW_AGENTS_DEFAULT_LLM_API_KEY_VALUE" ]'
        in deploy_script
    )
    assert "map $request_uri $new_agents_gateway_marker" in nginx
    assert "proxy_set_header X-AI4SE-Gateway $new_agents_gateway_marker;" in nginx
    assert '~^/new-agents/api/config(?:/check)?(?:\\?|$) "";' in nginx


def test_new_agents_development_config_admin_is_opt_in_and_loopback_only():
    for compose_path in DEVELOPMENT_COMPOSES:
        compose_payload = yaml.safe_load(compose_path.read_text(encoding="utf-8"))
        backend_environment = compose_payload["services"]["new-agents-backend"][
            "environment"
        ]
        assert backend_environment["AI4SE_ENV"] == "development"
        assert backend_environment[
            "NEW_AGENTS_CONFIG_ADMIN_ALLOW_UNAUTHENTICATED"
        ].endswith(":-false}")
        gateway_ports = compose_payload["services"]["nginx"]["ports"]
        assert gateway_ports == ["127.0.0.1:80:80", "127.0.0.1:443:443"]


def test_local_deploy_uses_existing_dev_compose_file():
    script = DEPLOY_SCRIPT.read_text(encoding="utf-8")
    local_case = script.split("local|dev|development)", 1)[1].split(
        "prod|production|remote)", 1
    )[0]

    assert 'COMPOSE_FILE="docker-compose.dev.yml"' in local_case
    assert (ROOT / "docker-compose.dev.yml").exists()


def test_typescript_incremental_build_metadata_is_not_tracked():
    result = subprocess.run(
        ["git", "ls-files", "*.tsbuildinfo"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )

    assert result.stdout.strip() == ""
