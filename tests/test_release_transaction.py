import hashlib
import json
from email.message import Message
from pathlib import Path

import pytest

from scripts.ci.release_transaction import (
    GatewayReadiness,
    ReleaseFailure,
    ReleaseManifest,
    ReleasePaths,
    ReleaseState,
    ReleaseTransaction,
    SubprocessRunner,
    tree_digest,
)


class RecordingRunner:
    def __init__(self) -> None:
        self.commands: list[tuple[str, ...]] = []

    def run(self, command, *, cwd: Path):
        self.commands.append(tuple(command))
        raise AssertionError("untrusted previous must stop before a command runs")


class CommandResult:
    def __init__(self, stdout: str = "") -> None:
        self.returncode = 0
        self.stdout = stdout


class TransactionRunner:
    def __init__(self) -> None:
        self.commands: list[tuple[str, ...]] = []
        self.working_directories: list[Path] = []

    def run(self, command, *, cwd: Path):
        normalized = tuple(command)
        self.commands.append(normalized)
        self.working_directories.append(cwd)
        if normalized[:3] == ("docker", "image", "inspect"):
            release_id = normalized[-1].rsplit(":", 1)[-1]
            image_hex = "b" if release_id == "b" * 40 else "c"
            return CommandResult("sha256:" + image_hex * 64)
        return CommandResult()


class FailingTransactionRunner(TransactionRunner):
    def __init__(self, predicate) -> None:
        super().__init__()
        self.predicate = predicate

    def run(self, command, *, cwd: Path):
        normalized = tuple(command)
        self.commands.append(normalized)
        self.working_directories.append(cwd)
        if self.predicate(normalized):
            result = CommandResult()
            result.returncode = 1
            return result
        if normalized[:3] == ("docker", "image", "inspect"):
            release_id = normalized[-1].rsplit(":", 1)[-1]
            image_hex = "b" if release_id == "b" * 40 else "c"
            return CommandResult("sha256:" + image_hex * 64)
        return CommandResult()


class ScriptedReadiness:
    def __init__(self, outcomes: list[bool]) -> None:
        self.outcomes = list(outcomes)
        self.release_ids: list[str] = []

    def assert_ready(self, state, directory: Path) -> None:
        self.release_ids.append(state.release_id)
        if not self.outcomes.pop(0):
            raise ReleaseFailure("READINESS_FAILED")


class HttpResponse:
    def __init__(self, status: int, body: bytes, headers=None):
        self.status = status
        self._body = body
        self.headers = headers or {}

    def read(self, _size: int | None = None) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, _type, _value, _traceback) -> None:
        return None


class FakeHttp:
    def __init__(self, responses: dict[str, HttpResponse]) -> None:
        self.responses = responses
        self.urls: list[str] = []

    def __call__(self, url: str, *, timeout: float):
        self.urls.append(url)
        return self.responses[url]


def _write_manifest(upload: Path, release_id: str, source_digest: str) -> None:
    (upload / "release-manifest.json").write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "releaseId": release_id,
                "sourceDigest": source_digest,
            }
        ),
        encoding="utf-8",
    )


def _write_trusted_previous(root: Path, release_id: str = "b" * 40) -> Path:
    release_dir = root / "releases" / release_id
    release_dir.mkdir(parents=True)
    (release_dir / ".env").write_text(
        f"AI4SE_RELEASE_ID='{release_id}'\n" "INTENT_EXECUTION_ENABLED='false'\n",
        encoding="utf-8",
    )
    (release_dir / ".env").chmod(0o600)
    _write_manifest(release_dir, release_id, tree_digest(release_dir))
    (release_dir / "release-state.json").write_text(
        json.dumps(
            {
                "releaseId": release_id,
                "sourceDigest": tree_digest(release_dir),
                "composeDigest": "e" * 64,
                "envDigest": hashlib.sha256(
                    (release_dir / ".env").read_bytes()
                ).hexdigest(),
                "imageIds": {
                    "intent-tester": "sha256:" + "b" * 64,
                    "new-agents": "sha256:" + "b" * 64,
                    "new-agents-backend": "sha256:" + "b" * 64,
                },
                "phase": "active",
            }
        ),
        encoding="utf-8",
    )
    (root / "current").symlink_to(release_dir)
    return release_dir


def _deployment_environment(release_id: str) -> dict[str, str]:
    return {
        "AI4SE_RELEASE_ID": release_id,
        "DB_PASSWORD": "test-db-password",
        "SECRET_KEY": "test-secret-key",
        "INTENT_ACCESS_MODE": "restricted",
        "INTENT_TESTER_ADMIN_PASSWORD_HASH": "test-admin-hash",
        "INTENT_PUBLIC_ORIGIN": "https://release.test",
        "INTENT_EXECUTION_ENABLED": "false",
        "NEW_AGENTS_DEFAULT_LLM_API_KEY": "test-model-key",
        "NEW_AGENTS_DEFAULT_LLM_BASE_URL": "https://model.test",
        "NEW_AGENTS_DEFAULT_LLM_MODEL": "test-model",
        "NEW_AGENTS_CONFIG_ADMIN_API_KEY": "test-config-key",
        "PROXY_API_KEY": "test-proxy-key",
    }


def _candidate_transaction(tmp_path, readiness: list[bool]):
    release_id = "a" * 40
    upload = tmp_path / "uploads" / release_id
    upload.mkdir(parents=True)
    (upload / "app.txt").write_text("candidate", encoding="utf-8")
    _write_manifest(upload, release_id, tree_digest(upload))
    previous_dir = _write_trusted_previous(tmp_path)
    runner = TransactionRunner()
    readiness_probe = ScriptedReadiness(readiness)
    transaction = ReleaseTransaction(
        paths=ReleasePaths.from_root(tmp_path, release_id, upload),
        runner=runner,
        environment=_deployment_environment(release_id),
        readiness=readiness_probe,
    )
    return transaction, runner, readiness_probe, previous_dir


def _release_state() -> ReleaseState:
    return ReleaseState(
        release_id="a" * 40,
        source_digest="d" * 64,
        compose_digest="e" * 64,
        env_digest="f" * 64,
        image_ids={"new-agents": "sha256:" + "a" * 64},
        phase="prepared",
    )


def test_manifest_rejects_sha_or_content_digest_mismatch(tmp_path):
    release_id = "a" * 40
    upload = tmp_path / "upload"
    upload.mkdir()
    (upload / "app.txt").write_text("candidate", encoding="utf-8")
    _write_manifest(upload, release_id, "0" * 64)

    with pytest.raises(ReleaseFailure, match="INVALID_MANIFEST"):
        ReleaseManifest.load_and_verify(upload, release_id)

    _write_manifest(upload, "b" * 40, tree_digest(upload))
    with pytest.raises(ReleaseFailure, match="INVALID_MANIFEST"):
        ReleaseManifest.load_and_verify(upload, release_id)


def test_manifest_accepts_matching_immutable_release_identity(tmp_path):
    release_id = "a" * 40
    upload = tmp_path / "upload"
    upload.mkdir()
    (upload / "app.txt").write_text("candidate", encoding="utf-8")
    _write_manifest(upload, release_id, tree_digest(upload))

    manifest = ReleaseManifest.load_and_verify(upload, release_id)

    assert manifest.release_id == release_id
    assert manifest.source_digest == tree_digest(upload)


def test_manifest_rejects_any_symlink_in_the_release_tree(tmp_path):
    upload = tmp_path / "upload"
    upload.mkdir()
    (upload / "app.txt").write_text("candidate", encoding="utf-8")
    (upload / "linked-directory").symlink_to(tmp_path, target_is_directory=True)
    _write_manifest(upload, "a" * 40, "0" * 64)

    with pytest.raises(ReleaseFailure, match="INVALID_MANIFEST"):
        ReleaseManifest.load_and_verify(upload, "a" * 40)


def test_release_upload_must_be_under_the_transaction_uploads_directory(tmp_path):
    with pytest.raises(ReleaseFailure, match="PREPARE_FAILED"):
        ReleasePaths.from_root(tmp_path, "a" * 40, tmp_path / "outside-upload")


def test_subprocess_runner_does_not_leak_release_environment_into_compose(
    monkeypatch, tmp_path
):
    captured = {}

    def run(_command, **kwargs):
        captured.update(kwargs)
        return CommandResult()

    monkeypatch.setattr("scripts.ci.release_transaction.subprocess.run", run)
    runner = SubprocessRunner(
        {
            "PATH": "/usr/bin",
            "DB_PASSWORD": "candidate-secret",
            "NEW_AGENTS_DEFAULT_LLM_API_KEY": "provider-secret",
            "AI4SE_RELEASE_ID": "a" * 40,
            "COMPOSE_FILE": "untrusted-compose.yml",
        }
    )

    runner.run(("docker", "compose", "config"), cwd=tmp_path)

    assert captured["env"] == {"PATH": "/usr/bin"}


def test_untrusted_previous_stops_before_any_compose_command(tmp_path):
    release_id = "a" * 40
    upload = tmp_path / "uploads" / release_id
    upload.mkdir(parents=True)
    (upload / "app.txt").write_text("candidate", encoding="utf-8")
    _write_manifest(upload, release_id, tree_digest(upload))
    runner = RecordingRunner()
    paths = ReleasePaths.from_root(tmp_path, release_id, upload)
    transaction = ReleaseTransaction(
        paths=paths,
        runner=runner,
        environment={"AI4SE_RELEASE_ID": release_id},
    )

    with pytest.raises(ReleaseFailure, match="UNTRUSTED_PREVIOUS"):
        transaction.run()

    assert runner.commands == []


def test_build_and_config_complete_before_current_pointer_changes(tmp_path):
    transaction, runner, readiness, _previous_dir = _candidate_transaction(
        tmp_path, [True]
    )

    active = transaction.run()

    build_index = next(
        index
        for index, event in enumerate(transaction.events)
        if event[0] == "command" and event[1].endswith(" build")
    )
    current_switch_index = transaction.events.index(
        ("current", str(transaction.paths.release_dir))
    )
    assert active.release_id == "a" * 40
    assert build_index < current_switch_index
    assert not any("down" in command for command in runner.commands)
    assert readiness.release_ids == ["a" * 40]


def test_readiness_failure_restores_previous_pointer_and_reverifies_it(tmp_path):
    transaction, runner, readiness, previous_dir = _candidate_transaction(
        tmp_path, [False, True]
    )

    with pytest.raises(ReleaseFailure, match="READINESS_FAILED"):
        transaction.run()

    assert transaction.current_release_id() == "b" * 40
    assert runner.working_directories[-1] == previous_dir
    assert str(previous_dir) in runner.commands[-1]
    assert readiness.release_ids == ["a" * 40, "b" * 40]


def test_execution_profile_builds_and_records_the_proxy_image(tmp_path):
    transaction, runner, _readiness, _previous_dir = _candidate_transaction(
        tmp_path, [True]
    )
    transaction.environment.update(
        {
            "INTENT_EXECUTION_ENABLED": "true",
            "INTENT_PROXY_TOKEN": "test-intent-proxy-token",
            "OPENAI_API_KEY": "test-provider-key",
            "OPENAI_BASE_URL": "https://provider.test",
            "MIDSCENE_MODEL_NAME": "test-provider-model",
        }
    )

    active = transaction.run()

    assert "intent-execution-proxy" in active.image_ids
    assert any(
        "--profile" in command and "execution" in command for command in runner.commands
    )


def test_rollback_uses_the_previous_release_execution_profile(tmp_path):
    transaction, runner, _readiness, previous_dir = _candidate_transaction(
        tmp_path, [False, True]
    )
    previous_environment = previous_dir / ".env"
    previous_environment.write_text(
        previous_environment.read_text(encoding="utf-8").replace(
            "INTENT_EXECUTION_ENABLED='false'", "INTENT_EXECUTION_ENABLED='true'"
        ),
        encoding="utf-8",
    )
    state = ReleaseState.load(previous_dir / "release-state.json")
    ReleaseState(
        release_id=state.release_id,
        source_digest=state.source_digest,
        compose_digest=state.compose_digest,
        env_digest=hashlib.sha256(previous_environment.read_bytes()).hexdigest(),
        image_ids={
            **state.image_ids,
            "intent-execution-proxy": "sha256:" + "b" * 64,
        },
        phase=state.phase,
    ).write(previous_dir / "release-state.json")

    with pytest.raises(ReleaseFailure, match="READINESS_FAILED"):
        transaction.run()

    rollback_up = next(
        command
        for command in reversed(runner.commands)
        if "up" in command and str(previous_dir) in command
    )
    assert "--profile" in rollback_up
    assert "execution" in rollback_up


def test_candidate_environment_cannot_inherit_unmanaged_compose_controls(tmp_path):
    transaction, _runner, _readiness, previous_dir = _candidate_transaction(
        tmp_path, [True]
    )
    with (previous_dir / ".env").open("a", encoding="utf-8") as handle:
        handle.write("COMPOSE_FILE=untrusted-compose.yml\n")
    state = ReleaseState.load(previous_dir / "release-state.json")
    state = ReleaseState(
        release_id=state.release_id,
        source_digest=state.source_digest,
        compose_digest=state.compose_digest,
        env_digest=hashlib.sha256((previous_dir / ".env").read_bytes()).hexdigest(),
        image_ids=state.image_ids,
        phase=state.phase,
    )
    state.write(previous_dir / "release-state.json")

    transaction.run()

    candidate_environment = (transaction.paths.release_dir / ".env").read_text(
        encoding="utf-8"
    )
    assert "COMPOSE_FILE" not in candidate_environment


def test_tampered_previous_release_is_rejected_before_candidate_commands(tmp_path):
    transaction, runner, _readiness, previous_dir = _candidate_transaction(
        tmp_path, [True]
    )
    (previous_dir / "app.txt").write_text("tampered", encoding="utf-8")

    with pytest.raises(ReleaseFailure, match="UNTRUSTED_PREVIOUS"):
        transaction.run()

    assert runner.commands == []


@pytest.mark.parametrize(
    ("operation", "expected_code"),
    [
        ("config", "PREPARE_FAILED"),
        ("build", "PREPARE_FAILED"),
    ],
)
def test_prepare_failure_leaves_the_trusted_current_release_untouched(
    tmp_path, operation, expected_code
):
    transaction, _runner, readiness, previous_dir = _candidate_transaction(
        tmp_path, [True]
    )
    failing_runner = FailingTransactionRunner(lambda command: command[-1] == operation)
    transaction.runner = failing_runner

    with pytest.raises(ReleaseFailure, match=expected_code):
        transaction.run()

    assert transaction.current_release_id() == "b" * 40
    assert transaction.paths.current_link.resolve() == previous_dir
    assert readiness.release_ids == []
    assert not any("down" in command for command in failing_runner.commands)


def test_image_identity_drift_rolls_back_to_the_recorded_previous_release(tmp_path):
    transaction, _runner, readiness, previous_dir = _candidate_transaction(
        tmp_path, [True]
    )

    class DriftingImageRunner(TransactionRunner):
        def __init__(self):
            super().__init__()
            self.candidate_inspections = 0

        def run(self, command, *, cwd: Path):
            normalized = tuple(command)
            self.commands.append(normalized)
            self.working_directories.append(cwd)
            if normalized[:3] == ("docker", "image", "inspect"):
                release_id = normalized[-1].rsplit(":", 1)[-1]
                if release_id == "a" * 40:
                    self.candidate_inspections += 1
                    image_hex = "c" if self.candidate_inspections == 1 else "d"
                else:
                    image_hex = "b"
                return CommandResult("sha256:" + image_hex * 64)
            return CommandResult()

    runner = DriftingImageRunner()
    transaction.runner = runner

    with pytest.raises(ReleaseFailure, match="IDENTITY_MISMATCH"):
        transaction.run()

    assert transaction.paths.current_link.resolve() == previous_dir
    assert readiness.release_ids == ["b" * 40]


def test_rollback_readiness_failure_never_reports_a_candidate_failure_as_success(
    tmp_path,
):
    transaction, _runner, readiness, previous_dir = _candidate_transaction(
        tmp_path, [False, False]
    )

    with pytest.raises(ReleaseFailure, match="ROLLBACK_FAILED"):
        transaction.run()

    assert transaction.paths.current_link.resolve() == previous_dir
    assert readiness.release_ids == ["a" * 40, "b" * 40]


def test_lock_collision_stops_before_any_command(tmp_path):
    transaction, runner, _readiness, _previous_dir = _candidate_transaction(
        tmp_path, [True]
    )

    with transaction.lock(), pytest.raises(ReleaseFailure, match="LOCKED"):
        transaction.run()

    assert runner.commands == []


def test_gateway_readiness_requires_new_agents_page_json_sse_and_database_probe(
    tmp_path,
):
    runner = TransactionRunner()
    http = FakeHttp(
        {
            "http://127.0.0.1/new-agents/": HttpResponse(200, b'<div id="root"></div>'),
            "http://127.0.0.1/new-agents/api/health": HttpResponse(
                200, b'{"status":"ok","service":"new-agents-backend"}'
            ),
            "http://127.0.0.1/new-agents/api/readiness": HttpResponse(
                200,
                b'{"status":"ok","service":"new-agents-backend","database":"ok"}',
            ),
            "http://127.0.0.1/new-agents/api/readiness/stream": HttpResponse(
                200,
                b'data: {"type": "run_started", "runId": "readiness"}\n\ndata: [DONE]\n\n',
                {"Content-Type": "text/event-stream"},
            ),
        }
    )
    readiness = GatewayReadiness(
        runner=runner,
        request=http,
        gateway_url="http://127.0.0.1",
        compose_command=lambda directory, *arguments: (
            "docker",
            "compose",
            "--project-directory",
            str(directory),
            *arguments,
        ),
    )

    readiness.assert_ready(_release_state(), tmp_path)

    assert http.urls == [
        "http://127.0.0.1/new-agents/",
        "http://127.0.0.1/new-agents/api/health",
        "http://127.0.0.1/new-agents/api/readiness",
        "http://127.0.0.1/new-agents/api/readiness/stream",
    ]
    assert any(
        any("CREATE TEMPORARY TABLE release_probe" in argument for argument in command)
        for command in runner.commands
    )


def test_gateway_readiness_accepts_urllib_http_message_headers(tmp_path):
    headers = Message()
    headers["Content-Type"] = "text/event-stream"
    responses = {
        "http://127.0.0.1/new-agents/": HttpResponse(200, b'<div id="root"></div>'),
        "http://127.0.0.1/new-agents/api/health": HttpResponse(
            200, b'{"status":"ok","service":"new-agents-backend"}'
        ),
        "http://127.0.0.1/new-agents/api/readiness": HttpResponse(
            200,
            b'{"status":"ok","service":"new-agents-backend","database":"ok"}',
        ),
        "http://127.0.0.1/new-agents/api/readiness/stream": HttpResponse(
            200,
            b'data: {"type": "run_started", "runId": "readiness"}\n\n'
            b"data: [DONE]\n\n",
            headers,
        ),
    }
    readiness = GatewayReadiness(
        runner=TransactionRunner(),
        request=FakeHttp(responses),
        gateway_url="http://127.0.0.1",
        compose_command=lambda directory, *arguments: (
            "docker",
            "compose",
            "--project-directory",
            str(directory),
            *arguments,
        ),
    )

    readiness.assert_ready(_release_state(), tmp_path)


@pytest.mark.parametrize(
    "broken_path",
    [
        "/new-agents/",
        "/new-agents/api/readiness",
        "/new-agents/api/readiness/stream",
    ],
)
def test_any_gateway_readiness_mutation_fails_closed(tmp_path, broken_path):
    responses = {
        "http://127.0.0.1/new-agents/": HttpResponse(200, b'<div id="root"></div>'),
        "http://127.0.0.1/new-agents/api/health": HttpResponse(
            200, b'{"status":"ok","service":"new-agents-backend"}'
        ),
        "http://127.0.0.1/new-agents/api/readiness": HttpResponse(
            200,
            b'{"status":"ok","service":"new-agents-backend","database":"ok"}',
        ),
        "http://127.0.0.1/new-agents/api/readiness/stream": HttpResponse(
            200,
            b'data: {"type": "run_started", "runId": "readiness"}\n\ndata: [DONE]\n\n',
            {"Content-Type": "text/event-stream"},
        ),
    }
    url = f"http://127.0.0.1{broken_path}"
    responses[url] = HttpResponse(503, b"unavailable")
    readiness = GatewayReadiness(
        runner=TransactionRunner(),
        request=FakeHttp(responses),
        gateway_url="http://127.0.0.1",
        compose_command=lambda directory, *arguments: (
            "docker",
            "compose",
            "--project-directory",
            str(directory),
            *arguments,
        ),
    )

    with pytest.raises(ReleaseFailure, match="READINESS_FAILED"):
        readiness.assert_ready(_release_state(), tmp_path)
