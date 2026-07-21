from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest
from werkzeug.security import check_password_hash

ROOT = Path(__file__).resolve().parents[1]
DEPLOYMENT_PATH = ROOT / "scripts" / "test" / "pre_push_deployment.py"


def _load_deployment_module():
    if not DEPLOYMENT_PATH.exists():
        pytest.fail(f"pre-push deployment harness is missing: {DEPLOYMENT_PATH}")
    spec = importlib.util.spec_from_file_location(
        "pre_push_deployment", DEPLOYMENT_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _llm_config():
    from tests.e2e.new_agents_real.config import RealLlmConfig

    return RealLlmConfig(
        api_key="provider-api-key-canary",
        base_url="https://api.deepseek.example",
        model="deepseek-v4-flash",
    )


def test_deployment_config_never_reuses_production_names_or_public_ports(tmp_path):
    deployment = _load_deployment_module().DeploymentConfig.create(
        root=tmp_path,
        output_dir=tmp_path / "test-results",
        llm_config=_llm_config(),
    )

    assert deployment.project_name.startswith("ai4se-pre-push-")
    assert deployment.gateway_port != 80
    assert deployment.frontend_url.startswith("http://127.0.0.1:")
    assert deployment.env_path.parent == deployment.output_dir / "real-e2e"
    assert oct(deployment.env_path.stat().st_mode & 0o777) == "0o600"
    assert "provider-api-key-canary" not in repr(deployment)


def test_deployment_config_uses_valid_production_only_intent_security_values(tmp_path):
    deployment = _load_deployment_module().DeploymentConfig.create(
        root=tmp_path,
        output_dir=tmp_path / "test-results",
        llm_config=_llm_config(),
    )

    assert deployment.environment["INTENT_PUBLIC_ORIGIN"].startswith("https://")
    assert (
        check_password_hash(
            deployment.environment["INTENT_TESTER_ADMIN_PASSWORD_HASH"],
            "not-the-password",
        )
        is False
    )
    environment_source = deployment.env_path.read_text(encoding="utf-8")
    assert (
        "INTENT_TESTER_ADMIN_PASSWORD_HASH="
        f"'{deployment.environment['INTENT_TESTER_ADMIN_PASSWORD_HASH']}'"
    ) in environment_source


def test_readiness_requires_new_agents_page_backend_and_database_not_static_gateway(
    monkeypatch,
    tmp_path,
):
    module = _load_deployment_module()
    deployment = module.DeploymentConfig.create(
        root=tmp_path,
        output_dir=tmp_path / "test-results",
        llm_config=_llm_config(),
    )
    harness = module.ProductionHarness(deployment)
    checked_paths: list[str] = []

    class Response:
        status = 200

        def __init__(self, target):
            self.target = target
            self.headers = {}

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            if self.target.endswith("/readiness/stream"):
                self.headers = {"Content-Type": "text/event-stream"}
                return (
                    b'data: {"type": "run_started", "runId": "readiness"}\n\n'
                    b"data: [DONE]\n\n"
                )
            if self.target.endswith("/readiness"):
                return b'{"status":"ok","service":"new-agents-backend","database":"ok"}'
            return b'{"status":"ok","service":"new-agents-backend"}'

    def request(target, **_kwargs):
        if isinstance(target, module.Request):
            raise module.HTTPError(target.full_url, 401, "Unauthorized", {}, None)
        checked_paths.append(target)
        return Response(target)

    commands: list[tuple[str, ...]] = []

    class Result:
        returncode = 0
        stdout = (
            "location /new-agents/api/ { proxy_buffering off; "
            "proxy_set_header X-AI4SE-Gateway marker; }"
        )
        stderr = ""

    monkeypatch.setattr(harness, "request", request)
    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda command, **_kwargs: commands.append(tuple(command)) or Result(),
    )

    harness.assert_ready()

    assert f"http://127.0.0.1:{deployment.gateway_port}/new-agents/" in checked_paths
    assert (
        f"http://127.0.0.1:{deployment.gateway_port}/new-agents/api/health"
        in checked_paths
    )
    assert (
        f"http://127.0.0.1:{deployment.gateway_port}/new-agents/api/readiness"
        in checked_paths
    )
    assert (
        f"http://127.0.0.1:{deployment.gateway_port}/new-agents/api/readiness/stream"
        in checked_paths
    )
    assert f"http://127.0.0.1:{deployment.gateway_port}/health" not in checked_paths
    assert any(
        command[-3:] == ("postgres", "pg_isready", "-U") or "pg_isready" in command
        for command in commands
    )
    assert any("psql" in command for command in commands)
    assert any(command[-2:] == ("nginx", "-T") for command in commands)


def test_rendered_overlay_has_exactly_one_loopback_gateway_port(tmp_path):
    module = _load_deployment_module()
    deployment = module.DeploymentConfig.create(
        root=tmp_path,
        output_dir=tmp_path / "test-results",
        llm_config=_llm_config(),
    )

    rendered = module.render_pre_push_compose(deployment)

    assert rendered["services"]["nginx"]["ports"] == [
        f"127.0.0.1:{deployment.gateway_port}:80"
    ]
    source = (ROOT / "docker-compose.pre-push.yml").read_text(encoding="utf-8")
    assert "ports: !override" in source
    assert "volumes: !override" in source
    assert "./nginx/nginx.conf:/etc/nginx/nginx.conf:ro" in source
    assert "./nginx/ssl:/etc/nginx/ssl:ro" in source


def test_compose_command_passes_each_compose_file_with_its_own_flag(tmp_path):
    module = _load_deployment_module()
    deployment = module.DeploymentConfig.create(
        root=tmp_path,
        output_dir=tmp_path / "test-results",
        llm_config=_llm_config(),
    )

    command = module.ProductionHarness(deployment)._compose_command("config", "--quiet")

    first_file, second_file = map(str, deployment.compose_files)
    assert command[command.index(first_file) - 1] == "-f"
    assert command[command.index(second_file) - 1] == "-f"


def test_compose_subprocess_cannot_inherit_parent_release_or_compose_controls(
    monkeypatch, tmp_path
):
    module = _load_deployment_module()
    deployment = module.DeploymentConfig.create(
        root=tmp_path,
        output_dir=tmp_path / "test-results",
        llm_config=_llm_config(),
    )
    harness = module.ProductionHarness(deployment)
    captured = {}

    class Result:
        returncode = 0
        stdout = ""
        stderr = ""

    monkeypatch.setenv("AI4SE_RELEASE_ID", "parent-release")
    monkeypatch.setenv("COMPOSE_FILE", "parent-compose.yml")
    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda _command, **kwargs: captured.update(kwargs) or Result(),
    )

    harness._run_compose("config", "--quiet")

    assert "AI4SE_RELEASE_ID" not in captured["env"]
    assert "COMPOSE_FILE" not in captured["env"]


def test_close_removes_private_environment_even_when_stack_never_started(tmp_path):
    module = _load_deployment_module()
    deployment = module.DeploymentConfig.create(
        root=tmp_path,
        output_dir=tmp_path / "test-results",
        llm_config=_llm_config(),
    )

    module.ProductionHarness(deployment).close()

    assert not deployment.env_path.exists()


def test_start_failure_cleans_isolated_compose_resources_and_private_environment(
    monkeypatch,
    tmp_path,
):
    module = _load_deployment_module()
    deployment = module.DeploymentConfig.create(
        root=tmp_path,
        output_dir=tmp_path / "test-results",
        llm_config=_llm_config(),
    )
    harness = module.ProductionHarness(deployment)
    commands: list[tuple[str, ...]] = []

    monkeypatch.setattr(harness, "_require_compose_version", lambda: None)

    def fail_start(*arguments):
        commands.append(arguments)
        if arguments[0] == "up":
            raise RuntimeError("up failed")

    monkeypatch.setattr(harness, "_run_compose", fail_start)

    with pytest.raises(RuntimeError, match="up failed"):
        harness.start()

    assert ("down", "--volumes", "--remove-orphans") in commands
    assert not deployment.env_path.exists()


def test_cleanup_falls_back_to_the_isolated_project_when_compose_config_cleanup_fails(
    monkeypatch,
    tmp_path,
):
    module = _load_deployment_module()
    deployment = module.DeploymentConfig.create(
        root=tmp_path,
        output_dir=tmp_path / "test-results",
        llm_config=_llm_config(),
    )
    harness = module.ProductionHarness(deployment)
    harness._started = True

    monkeypatch.setattr(
        harness,
        "_run_compose",
        lambda *_arguments: (_ for _ in ()).throw(RuntimeError("down failed")),
    )
    commands: list[tuple[str, ...]] = []

    class Result:
        returncode = 0

    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda command, **_kwargs: commands.append(tuple(command)) or Result(),
    )

    harness.close()

    assert commands == [
        (
            "docker",
            "compose",
            "-p",
            deployment.project_name,
            "down",
            "--volumes",
            "--remove-orphans",
        )
    ]
    assert not deployment.env_path.exists()


def test_compose_failure_identifies_the_safe_operation_name(monkeypatch, tmp_path):
    module = _load_deployment_module()
    deployment = module.DeploymentConfig.create(
        root=tmp_path,
        output_dir=tmp_path / "test-results",
        llm_config=_llm_config(),
    )
    harness = module.ProductionHarness(deployment)

    class Result:
        returncode = 1
        stdout = "provider-api-key-canary"
        stderr = ""

    monkeypatch.setattr(module.subprocess, "run", lambda *_args, **_kwargs: Result())

    with pytest.raises(RuntimeError, match="Compose build command failed"):
        harness._run_compose("build")
