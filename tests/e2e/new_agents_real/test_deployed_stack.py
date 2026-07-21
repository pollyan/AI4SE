from __future__ import annotations

import importlib
import json
import os
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

from .config import RealLlmConfig
from .conftest import build_real_stack
from .deployed_stack import (
    DeployedStack,
    DeploymentControl,
    DeploymentTarget,
    DeploymentTargetError,
)
from .workflow_runner import restart_and_restore, should_verify_restart
from . import reporting

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize(
    "value",
    (
        "https://remote.example/new-agents/",
        "http://127.0.0.1:8080/other/",
        "http://user:secret@127.0.0.1:8080/new-agents/",
        "http://127.0.0.1:8080/new-agents/?unsafe=true",
    ),
)
def test_deployment_target_rejects_non_loopback_or_non_workspace_urls(value):
    with pytest.raises(DeploymentTargetError):
        DeploymentTarget.parse(value)


def _control_environment(tmp_path: Path) -> dict[str, str]:
    evidence_root = tmp_path / "test-results" / "pre-push" / ("a" * 40) / "real-e2e"
    evidence_root.mkdir(parents=True)
    environment = evidence_root / "deployment.env"
    environment.write_text("PRE_PUSH_PROJECT_NAME=ai4se-pre-push-123456abcdef\n")
    os.chmod(environment, 0o600)
    descriptor = evidence_root / "deployment-control.json"
    descriptor.write_text(
        json.dumps(
            {
                "projectName": "ai4se-pre-push-123456abcdef",
                "targetUrl": "http://127.0.0.1:18080/new-agents/",
                "envFile": str(environment),
            }
        ),
        encoding="utf-8",
    )
    return {
        "NEW_AGENTS_REAL_TARGET_URL": "http://127.0.0.1:18080/new-agents/",
        "NEW_AGENTS_REAL_EVIDENCE_DIR": str(evidence_root),
        "NEW_AGENTS_REAL_DEPLOYMENT_CONTROL_FILE": str(descriptor),
    }


def test_real_fixture_selects_deployed_stack_without_starting_live_processes(tmp_path):
    environment = _control_environment(tmp_path)
    stack = build_real_stack(
        tmp_path,
        RealLlmConfig(
            "provider-api-key-canary",
            "https://api.deepseek.example",
            "deepseek-v4-flash",
        ),
        environ=environment,
    )

    assert isinstance(stack, DeployedStack)
    assert stack.frontend_url.endswith("/new-agents/")
    assert isinstance(stack.control, DeploymentControl)


def test_workflow_restore_runs_after_deployed_backend_restart(monkeypatch):
    events: list[str] = []

    class Stack:
        def restart_backend(self) -> None:
            events.append("restart")

    runner_module = importlib.import_module(restart_and_restore.__module__)
    monkeypatch.setattr(
        runner_module,
        "_restore_from_server",
        lambda *_args, **_kwargs: events.append("restore"),
    )

    restart_and_restore(Stack(), object(), object(), {}, (), 1)

    assert events == ["restart", "restore"]


def test_deployed_restart_waits_for_backend_readiness(monkeypatch, tmp_path):
    deployed_stack_module = importlib.import_module(DeployedStack.__module__)
    environment = _control_environment(tmp_path)
    events: list[str] = []
    control = SimpleNamespace(restart_backend=lambda: events.append("restart"))
    stack = DeployedStack(
        tmp_path,
        RealLlmConfig(
            "provider-api-key-canary",
            "https://api.deepseek.example",
            "deepseek-v4-flash",
        ),
        DeploymentTarget.parse(environment["NEW_AGENTS_REAL_TARGET_URL"]),
        control,
    )
    attempts = iter(
        (RuntimeError("still restarting"), RuntimeError("still restarting"), None)
    )

    def readiness_probe() -> None:
        events.append("ready")
        result = next(attempts)
        if result is not None:
            raise result

    monkeypatch.setattr(stack, "_assert_ready", readiness_probe)
    monkeypatch.setattr(deployed_stack_module.time, "sleep", lambda _seconds: None)

    stack.restart_backend()

    assert events == ["restart", "ready", "ready", "ready"]


def test_deployed_readiness_requires_database_json_and_typed_sse(monkeypatch, tmp_path):
    environment = _control_environment(tmp_path)
    stack = DeployedStack(
        tmp_path,
        RealLlmConfig(
            "provider-api-key-canary",
            "https://api.deepseek.example",
            "deepseek-v4-flash",
        ),
        DeploymentTarget.parse(environment["NEW_AGENTS_REAL_TARGET_URL"]),
        SimpleNamespace(),
    )
    requested: list[str] = []

    class Response:
        status = 200

        def __init__(self, url: str):
            self.url = url
            self.headers = {"Content-Type": "text/event-stream"}

        def read(self):
            if self.url.endswith("/readiness/stream"):
                return (
                    b'data: {"type": "run_started", "runId": "readiness"}\n\n'
                    b"data: [DONE]\n\n"
                )
            if self.url.endswith("/readiness"):
                return (
                    b'{"status":"ok","service":"new-agents-backend",'
                    b'"database":"ok"}'
                )
            return b'{"status":"ok","service":"new-agents-backend"}'

    @contextmanager
    def request(url: str):
        requested.append(url)
        yield Response(url)

    monkeypatch.setattr(stack, "_request", request)

    stack._assert_ready()

    assert requested[-2:] == [
        "http://127.0.0.1:18080/new-agents/api/readiness",
        "http://127.0.0.1:18080/new-agents/api/readiness/stream",
    ]


def test_restart_verification_requires_an_explicit_deployment_flag(monkeypatch):
    class Stack:
        def restart_backend(self) -> None:
            return None

    monkeypatch.setenv("NEW_AGENTS_REAL_VERIFY_RESTART", "1")

    assert should_verify_restart(Stack()) is True


def test_deployed_evidence_path_stays_inside_the_controlled_evidence_root(
    tmp_path,
    monkeypatch,
):
    environment = _control_environment(tmp_path)
    monkeypatch.setenv(
        "NEW_AGENTS_REAL_TARGET_URL", environment["NEW_AGENTS_REAL_TARGET_URL"]
    )
    monkeypatch.setenv(
        "NEW_AGENTS_REAL_EVIDENCE_DIR", environment["NEW_AGENTS_REAL_EVIDENCE_DIR"]
    )

    path = reporting.report_path(tmp_path, "release", "workflow-TEST_DESIGN")

    assert path.parent == Path(environment["NEW_AGENTS_REAL_EVIDENCE_DIR"])
