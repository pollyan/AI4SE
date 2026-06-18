from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "deploy.yml"
DEPLOY_SCRIPT = ROOT / "scripts" / "ci" / "deploy.sh"


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
