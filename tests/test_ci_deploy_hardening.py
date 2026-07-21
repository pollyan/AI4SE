from pathlib import Path
import subprocess

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "deploy.yml"
DEPLOY_SCRIPT = ROOT / "scripts" / "ci" / "deploy.sh"
HEALTH_SCRIPT = ROOT / "scripts" / "health" / "health_check.sh"
RELEASE_TRANSACTION = ROOT / "scripts" / "ci" / "release_transaction.py"
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
    transaction = RELEASE_TRANSACTION.read_text(encoding="utf-8")

    assert "sed -i" not in workflow
    assert "MANAGED_ENVIRONMENT_KEYS" in transaction
    assert "os.O_EXCL, 0o600" in transaction
    assert "previous_env.read_text" in transaction
    assert "escaped_value = value.replace" in transaction


def test_new_agents_production_config_admin_auth_is_fail_closed():
    workflow = WORKFLOW.read_text(encoding="utf-8")
    transaction = RELEASE_TRANSACTION.read_text(encoding="utf-8")
    compose = PRODUCTION_COMPOSE.read_text(encoding="utf-8")
    nginx = NGINX_CONFIG.read_text(encoding="utf-8")

    for secret_name in (
        "NEW_AGENTS_CONFIG_ADMIN_API_KEY",
        "PROXY_API_KEY",
    ):
        assert f"secrets.{secret_name}" in workflow
        assert f'"{secret_name}"' in transaction
        assert f"${{{secret_name}:?" in compose
    compose_payload = yaml.safe_load(compose)
    backend_environment = compose_payload["services"]["new-agents-backend"][
        "environment"
    ]
    assert backend_environment["AI4SE_ENV"] == "production"
    assert "NEW_AGENTS_CONFIG_ADMIN_API_KEY" in backend_environment
    assert "PROXY_API_KEY" in backend_environment
    assert "protected_keys" in transaction
    assert "len({values[key] for key in protected_keys})" in transaction
    assert "umask 077" in workflow
    assert "release_transaction.py" in DEPLOY_SCRIPT.read_text(encoding="utf-8")
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

    assert 'compose_file="docker-compose.dev.yml"' in local_case
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


def test_docker_build_context_excludes_nested_node_modules():
    dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8")

    assert "**/node_modules/" in dockerignore


def test_repository_documents_and_ci_reference_the_fixed_pre_push_contract():
    for path in (
        ROOT / "AGENTS.md",
        ROOT / "docs/TESTING.md",
        ROOT / "docs/deployment-guide.md",
    ):
        assert "scripts/test/pre-push.sh" in path.read_text(encoding="utf-8")
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "tests/test_pre_push_gate.py" in workflow
    assert "tests/test_pre_push_deployment.py" in workflow


def test_production_deploy_uses_unique_staging_manifest_and_serial_concurrency():
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "group: production-release" in workflow
    assert "cancel-in-progress: false" in workflow
    assert "release-manifest.json" in workflow
    assert "github.run_id" in workflow
    assert "github.run_attempt" in workflow
    assert "/opt/intent-test-framework-upload-tmp" not in workflow
    assert "release_transaction.py" in workflow


def test_deployment_guide_requires_the_trusted_release_transaction_path():
    guide = (ROOT / "docs" / "deployment-guide.md").read_text(encoding="utf-8")

    assert "scripts/ci/release_transaction.py" in guide
    assert "releases/<sha>" in guide
    assert "可信基线" in guide
    assert "scripts/test/pre-push.sh" in guide


def test_production_compose_builds_release_tagged_images():
    compose = yaml.safe_load(PRODUCTION_COMPOSE.read_text(encoding="utf-8"))

    for service_name in ("intent-tester", "new-agents", "new-agents-backend"):
        image = compose["services"][service_name].get("image")
        assert image is not None
        assert "AI4SE_RELEASE_ID" in image


def test_legacy_production_deploy_cannot_stop_or_globally_clean_resources():
    script = DEPLOY_SCRIPT.read_text(encoding="utf-8")
    production = script.split("prod|production|remote)", 1)[1]

    assert "release_transaction.py" in production
    assert "docker ps -a | grep" not in production
    assert "docker network ls | grep" not in production
    assert " down" not in production


def test_legacy_production_health_check_cannot_be_a_release_verdict():
    health = HEALTH_SCRIPT.read_text(encoding="utf-8")
    production = health.split("prod|production|remote)", 1)[1].split(";;", 1)[0]

    assert "release_transaction.py" in production
    assert "exit 2" in production


def test_production_readiness_contract_uses_new_agents_gateway_and_sse_boundary():
    nginx = NGINX_CONFIG.read_text(encoding="utf-8")
    routes = (ROOT / "tools/new-agents/backend/routes.py").read_text(
        encoding="utf-8"
    )
    transaction = RELEASE_TRANSACTION.read_text(encoding="utf-8")

    assert "location /new-agents/api/" in nginx
    assert "proxy_buffering off;" in nginx
    assert '@api_bp.route("/readiness", methods=["GET"])' in routes
    assert '@api_bp.route("/readiness/stream", methods=["GET"])' in routes
    assert 'RunStartedEvent(run_id="readiness")' in routes
    assert 'gateway_url="http://127.0.0.1"' in transaction
    assert "_execution_profile_arguments" in transaction
    assert 'str(directory / "docker-compose.prod.yml")' in transaction
    assert "--gateway-url" not in transaction
