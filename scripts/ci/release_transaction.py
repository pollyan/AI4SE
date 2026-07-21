#!/usr/bin/env python3
"""Fail-closed identity boundary for production release transactions."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import subprocess
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol
from urllib.request import urlopen

RELEASE_ID_PATTERN = re.compile(r"[0-9a-f]{40}\Z")
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}\Z")
IMAGE_ID_PATTERN = re.compile(r"sha256:[0-9a-f]{64}\Z")
IGNORED_DIGEST_FILES = frozenset(
    {"release-manifest.json", "release-state.json", ".env"}
)
MANAGED_ENVIRONMENT_KEYS = (
    "DB_PASSWORD",
    "SECRET_KEY",
    "INTENT_ACCESS_MODE",
    "INTENT_TESTER_ADMIN_PASSWORD_HASH",
    "INTENT_PUBLIC_ORIGIN",
    "INTENT_EXECUTION_ENABLED",
    "INTENT_PROXY_TOKEN",
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "MIDSCENE_MODEL_NAME",
    "NEW_AGENTS_DEFAULT_LLM_API_KEY",
    "NEW_AGENTS_DEFAULT_LLM_BASE_URL",
    "NEW_AGENTS_DEFAULT_LLM_MODEL",
    "NEW_AGENTS_DEFAULT_LLM_DESCRIPTION",
    "NEW_AGENTS_CONFIG_ADMIN_API_KEY",
    "PROXY_API_KEY",
)
ALWAYS_REQUIRED_ENVIRONMENT_KEYS = (
    "DB_PASSWORD",
    "SECRET_KEY",
    "INTENT_ACCESS_MODE",
    "INTENT_TESTER_ADMIN_PASSWORD_HASH",
    "INTENT_PUBLIC_ORIGIN",
    "INTENT_EXECUTION_ENABLED",
    "NEW_AGENTS_DEFAULT_LLM_API_KEY",
    "NEW_AGENTS_DEFAULT_LLM_BASE_URL",
    "NEW_AGENTS_DEFAULT_LLM_MODEL",
    "NEW_AGENTS_CONFIG_ADMIN_API_KEY",
    "PROXY_API_KEY",
)
PRESERVED_UNMANAGED_ENVIRONMENT_KEYS: tuple[str, ...] = ()
COMPOSE_INTERPOLATION_ENVIRONMENT_KEYS = frozenset(
    (*MANAGED_ENVIRONMENT_KEYS, "AI4SE_RELEASE_ID", "DB_USER", "FLASK_ENV", "AI4SE_ENV")
)


class ReleaseFailure(RuntimeError):
    """A release failure safe to expose through CI logs."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


class CommandRunner(Protocol):
    def run(self, command: Sequence[str], *, cwd: Path) -> Any: ...


class ReadinessProbe(Protocol):
    def assert_ready(self, state: "ReleaseState", directory: Path) -> None: ...


class SubprocessRunner:
    """Production command adapter that retains no child output in release state."""

    def __init__(self, environment: Mapping[str, str]) -> None:
        self.environment = {
            key: value
            for key, value in environment.items()
            if key not in COMPOSE_INTERPOLATION_ENVIRONMENT_KEYS
            and not key.startswith("COMPOSE_")
        }

    def run(
        self, command: Sequence[str], *, cwd: Path
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            command,
            cwd=cwd,
            text=True,
            capture_output=True,
            check=False,
            env=self.environment,
        )


@dataclass(frozen=True)
class ReleaseManifest:
    release_id: str
    source_digest: str

    @classmethod
    def load_and_verify(cls, root: Path, release_id: str) -> "ReleaseManifest":
        if RELEASE_ID_PATTERN.fullmatch(release_id) is None:
            raise ReleaseFailure("INVALID_MANIFEST")
        manifest_path = root / "release-manifest.json"
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            raise ReleaseFailure("INVALID_MANIFEST") from None
        if not isinstance(payload, Mapping):
            raise ReleaseFailure("INVALID_MANIFEST")
        manifest_release_id = payload.get("releaseId")
        source_digest = payload.get("sourceDigest")
        if (
            payload.get("schemaVersion") != 1
            or manifest_release_id != release_id
            or not isinstance(source_digest, str)
            or SHA256_PATTERN.fullmatch(source_digest) is None
            or source_digest != tree_digest(root)
        ):
            raise ReleaseFailure("INVALID_MANIFEST")
        return cls(release_id=manifest_release_id, source_digest=source_digest)


@dataclass(frozen=True)
class ReleaseState:
    release_id: str
    source_digest: str
    compose_digest: str
    env_digest: str
    image_ids: Mapping[str, str]
    phase: str

    @classmethod
    def load(cls, path: Path) -> "ReleaseState":
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            raise ReleaseFailure("UNTRUSTED_PREVIOUS") from None
        if not isinstance(payload, Mapping):
            raise ReleaseFailure("UNTRUSTED_PREVIOUS")
        image_ids = payload.get("imageIds")
        if (
            not isinstance(payload.get("releaseId"), str)
            or RELEASE_ID_PATTERN.fullmatch(payload["releaseId"]) is None
            or not isinstance(payload.get("sourceDigest"), str)
            or SHA256_PATTERN.fullmatch(payload["sourceDigest"]) is None
            or not isinstance(payload.get("composeDigest"), str)
            or SHA256_PATTERN.fullmatch(payload["composeDigest"]) is None
            or not isinstance(payload.get("envDigest"), str)
            or SHA256_PATTERN.fullmatch(payload["envDigest"]) is None
            or not isinstance(image_ids, Mapping)
            or not image_ids
            or not all(
                isinstance(name, str)
                and isinstance(image_id, str)
                and IMAGE_ID_PATTERN.fullmatch(image_id) is not None
                for name, image_id in image_ids.items()
            )
            or payload.get("phase") not in {"prepared", "active"}
        ):
            raise ReleaseFailure("UNTRUSTED_PREVIOUS")
        return cls(
            release_id=payload["releaseId"],
            source_digest=payload["sourceDigest"],
            compose_digest=payload["composeDigest"],
            env_digest=payload["envDigest"],
            image_ids=dict(image_ids),
            phase=payload["phase"],
        )

    def write(self, path: Path) -> None:
        payload = {
            "releaseId": self.release_id,
            "sourceDigest": self.source_digest,
            "composeDigest": self.compose_digest,
            "envDigest": self.env_digest,
            "imageIds": dict(self.image_ids),
            "phase": self.phase,
        }
        path.write_text(
            json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )


class GatewayReadiness:
    """Probe only fixed gateway facts; never serialize response bodies or secrets."""

    def __init__(
        self,
        *,
        runner: CommandRunner,
        request: Callable[..., Any],
        gateway_url: str,
        compose_command: Callable[..., Sequence[str]],
    ) -> None:
        self.runner = runner
        self.request = request
        self.gateway_url = gateway_url.rstrip("/")
        self.compose_command = compose_command

    def _get(self, path: str) -> tuple[Any, bytes]:
        try:
            with self.request(f"{self.gateway_url}{path}", timeout=10) as response:
                status = getattr(response, "status", None)
                headers = getattr(response, "headers", {})
                body = response.read(65536)
        except (OSError, ValueError):
            raise ReleaseFailure("READINESS_FAILED") from None
        if (
            status != 200
            or not callable(getattr(headers, "get", None))
            or not isinstance(body, bytes)
        ):
            raise ReleaseFailure("READINESS_FAILED")
        return headers, body

    def _require_json(self, path: str, expected: Mapping[str, str]) -> None:
        _headers, body = self._get(path)
        try:
            payload = json.loads(body)
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ReleaseFailure("READINESS_FAILED") from None
        if not isinstance(payload, Mapping) or any(
            payload.get(key) != value for key, value in expected.items()
        ):
            raise ReleaseFailure("READINESS_FAILED")

    def _require_database_write(self, state: ReleaseState, directory: Path) -> None:
        command = self.compose_command(
            directory,
            "exec",
            "-T",
            "postgres",
            "psql",
            "-v",
            "ON_ERROR_STOP=1",
            "-c",
            "CREATE TEMPORARY TABLE release_probe (id integer); "
            "INSERT INTO release_probe VALUES (1); SELECT count(*) FROM release_probe;",
        )
        result = self.runner.run(command, cwd=directory)
        if getattr(result, "returncode", 0) != 0:
            raise ReleaseFailure("READINESS_FAILED")

    def assert_ready(self, state: ReleaseState, directory: Path) -> None:
        _headers, page = self._get("/new-agents/")
        if b'id="root"' not in page:
            raise ReleaseFailure("READINESS_FAILED")
        self._require_json(
            "/new-agents/api/health",
            {"status": "ok", "service": "new-agents-backend"},
        )
        self._require_json(
            "/new-agents/api/readiness",
            {
                "status": "ok",
                "service": "new-agents-backend",
                "database": "ok",
            },
        )
        headers, stream = self._get("/new-agents/api/readiness/stream")
        content_type = headers.get("Content-Type", "")
        if (
            not isinstance(content_type, str)
            or not content_type.startswith("text/event-stream")
            or b'"type": "run_started"' not in stream
            or b"data: [DONE]" not in stream
        ):
            raise ReleaseFailure("READINESS_FAILED")
        self._require_database_write(state, directory)


@dataclass(frozen=True)
class ReleasePaths:
    root: Path
    release_id: str
    upload_dir: Path

    @classmethod
    def from_root(
        cls,
        root: Path,
        release_id: str,
        upload_dir: Path,
    ) -> "ReleasePaths":
        resolved_root = root.resolve()
        resolved_upload = upload_dir.resolve()
        if not resolved_upload.is_relative_to(resolved_root / "uploads"):
            raise ReleaseFailure("PREPARE_FAILED")
        return cls(
            root=resolved_root,
            release_id=release_id,
            upload_dir=resolved_upload,
        )

    @property
    def uploads_dir(self) -> Path:
        return self.root / "uploads"

    @property
    def releases_dir(self) -> Path:
        return self.root / "releases"

    @property
    def release_dir(self) -> Path:
        return self.releases_dir / self.release_id

    @property
    def current_link(self) -> Path:
        return self.root / "current"

    @property
    def lock_path(self) -> Path:
        return self.root / ".release.lock"


def tree_digest(root: Path) -> str:
    """Return a deterministic digest for ordinary release source files only."""
    digest = hashlib.sha256()
    try:
        paths = sorted(root.rglob("*"))
    except OSError:
        raise ReleaseFailure("INVALID_MANIFEST") from None
    for path in paths:
        if path.is_symlink():
            raise ReleaseFailure("INVALID_MANIFEST")
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if relative.name in IGNORED_DIGEST_FILES:
            continue
        try:
            content_digest = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            raise ReleaseFailure("INVALID_MANIFEST") from None
        digest.update(relative.as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(content_digest.encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


class ReleaseTransaction:
    """Own the release lock and reject activation without a trusted previous state."""

    def __init__(
        self,
        *,
        paths: ReleasePaths,
        runner: CommandRunner,
        environment: Mapping[str, str],
        readiness: ReadinessProbe | None = None,
    ) -> None:
        self.paths = paths
        self.runner = runner
        self.environment = dict(environment)
        self.readiness = readiness
        self.events: list[tuple[str, str]] = []

    @contextmanager
    def lock(self) -> Iterator[None]:
        self.paths.root.mkdir(parents=True, exist_ok=True)
        with self.paths.lock_path.open("a+", encoding="utf-8") as handle:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise ReleaseFailure("LOCKED") from None
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def require_trusted_previous(self) -> ReleaseState:
        current = self.paths.current_link
        if not current.is_symlink():
            raise ReleaseFailure("UNTRUSTED_PREVIOUS")
        try:
            previous_dir = current.resolve(strict=True)
        except OSError:
            raise ReleaseFailure("UNTRUSTED_PREVIOUS") from None
        if not previous_dir.is_relative_to(self.paths.releases_dir):
            raise ReleaseFailure("UNTRUSTED_PREVIOUS")
        state_path = previous_dir / "release-state.json"
        env_path = previous_dir / ".env"
        if not state_path.is_file() or not env_path.is_file():
            raise ReleaseFailure("UNTRUSTED_PREVIOUS")
        state = ReleaseState.load(state_path)
        try:
            manifest = ReleaseManifest.load_and_verify(previous_dir, state.release_id)
        except ReleaseFailure:
            raise ReleaseFailure("UNTRUSTED_PREVIOUS") from None
        try:
            env_mode = env_path.stat().st_mode & 0o777
        except OSError:
            raise ReleaseFailure("UNTRUSTED_PREVIOUS") from None
        try:
            profile_arguments = self._execution_profile_arguments(previous_dir)
        except ReleaseFailure:
            raise ReleaseFailure("UNTRUSTED_PREVIOUS") from None
        expected_services = {"intent-tester", "new-agents", "new-agents-backend"}
        if profile_arguments:
            expected_services.add("intent-execution-proxy")
        if (
            state.release_id != previous_dir.name
            or state.phase != "active"
            or env_mode != 0o600
            or set(state.image_ids) != expected_services
            or state.source_digest != manifest.source_digest
            or state.source_digest != tree_digest(previous_dir)
            or state.env_digest != self._digest_bytes(env_path.read_bytes())
        ):
            raise ReleaseFailure("UNTRUSTED_PREVIOUS")
        return state

    @staticmethod
    def _digest_bytes(value: bytes) -> str:
        return hashlib.sha256(value).hexdigest()

    @staticmethod
    def _result_stdout(result: Any) -> str:
        value = getattr(result, "stdout", "")
        return value if isinstance(value, str) else ""

    @staticmethod
    def _result_succeeded(result: Any) -> bool:
        return getattr(result, "returncode", 0) == 0

    def _run(self, command: Sequence[str], *, cwd: Path, code: str) -> Any:
        self.events.append(("command", " ".join(command)))
        result = self.runner.run(command, cwd=cwd)
        if not self._result_succeeded(result):
            raise ReleaseFailure(code)
        return result

    def _managed_environment(self, previous_dir: Path) -> dict[str, str]:
        values = {
            "DB_USER": "intent_user",
            "FLASK_ENV": "production",
            "AI4SE_ENV": "production",
            "INTENT_PROXY_TOPOLOGY": "managed",
            "AI4SE_RELEASE_ID": self.paths.release_id,
        }
        for key in MANAGED_ENVIRONMENT_KEYS:
            value = self.environment.get(key, "")
            if "\n" in value or "\r" in value:
                raise ReleaseFailure("PREPARE_FAILED")
            values[key] = value
        if any(not values[key].strip() for key in ALWAYS_REQUIRED_ENVIRONMENT_KEYS):
            raise ReleaseFailure("PREPARE_FAILED")
        if values["INTENT_ACCESS_MODE"] not in {"restricted", "public-readonly"}:
            raise ReleaseFailure("PREPARE_FAILED")
        if values["INTENT_EXECUTION_ENABLED"] not in {"true", "false"}:
            raise ReleaseFailure("PREPARE_FAILED")
        if values["INTENT_EXECUTION_ENABLED"] == "true" and any(
            not values[key].strip()
            for key in (
                "INTENT_PROXY_TOKEN",
                "OPENAI_API_KEY",
                "OPENAI_BASE_URL",
                "MIDSCENE_MODEL_NAME",
            )
        ):
            raise ReleaseFailure("PREPARE_FAILED")
        protected_keys = (
            "NEW_AGENTS_CONFIG_ADMIN_API_KEY",
            "PROXY_API_KEY",
            "NEW_AGENTS_DEFAULT_LLM_API_KEY",
        )
        if len({values[key] for key in protected_keys}) != len(protected_keys):
            raise ReleaseFailure("PREPARE_FAILED")
        if not values["NEW_AGENTS_DEFAULT_LLM_DESCRIPTION"].strip():
            values["NEW_AGENTS_DEFAULT_LLM_DESCRIPTION"] = (
                "AI4SE managed default LLM configuration"
            )
        previous_env = previous_dir / ".env"
        try:
            lines = previous_env.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            raise ReleaseFailure("PREPARE_FAILED") from None
        for line in lines:
            key = line.split("=", 1)[0]
            if "=" in line and key in PRESERVED_UNMANAGED_ENVIRONMENT_KEYS:
                values[key] = line.split("=", 1)[1]
        return values

    def _write_candidate_environment(
        self, release_dir: Path, previous_dir: Path
    ) -> Path:
        values = self._managed_environment(previous_dir)
        if values.get("AI4SE_RELEASE_ID") != self.paths.release_id:
            raise ReleaseFailure("PREPARE_FAILED")
        env_path = release_dir / ".env"
        descriptor = os.open(env_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            for key, value in sorted(values.items()):
                escaped_value = value.replace("'", "\\'")
                handle.write(f"{key}='{escaped_value}'\n")
        return env_path

    @staticmethod
    def _execution_profile_arguments(directory: Path) -> tuple[str, ...]:
        environment_path = directory / ".env"
        try:
            lines = environment_path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            raise ReleaseFailure("PREPARE_FAILED") from None
        for line in lines:
            key, separator, value = line.partition("=")
            if key != "INTENT_EXECUTION_ENABLED" or not separator:
                continue
            if value == "'true'":
                return ("--profile", "execution")
            if value == "'false'":
                return ()
            break
        raise ReleaseFailure("PREPARE_FAILED")

    def _compose_command(self, directory: Path, *arguments: str) -> tuple[str, ...]:
        profile_arguments = self._execution_profile_arguments(directory)
        return (
            "docker",
            "compose",
            "--project-directory",
            str(directory),
            "--env-file",
            str(directory / ".env"),
            "-p",
            "ai4se",
            *profile_arguments,
            "-f",
            str(directory / "docker-compose.prod.yml"),
            *arguments,
        )

    def _image_tag(self, service: str, release_id: str) -> str:
        return f"ai4se/{service}:{release_id}"

    def _record_image_ids(self, directory: Path, release_id: str) -> dict[str, str]:
        image_ids: dict[str, str] = {}
        services = ["intent-tester", "new-agents", "new-agents-backend"]
        if self.environment.get("INTENT_EXECUTION_ENABLED") == "true":
            services.append("intent-execution-proxy")
        for service in services:
            result = self._run(
                (
                    "docker",
                    "image",
                    "inspect",
                    "--format",
                    "{{.Id}}",
                    self._image_tag(service, release_id),
                ),
                cwd=directory,
                code="PREPARE_FAILED",
            )
            image_id = self._result_stdout(result).strip()
            if IMAGE_ID_PATTERN.fullmatch(image_id) is None:
                raise ReleaseFailure("PREPARE_FAILED")
            image_ids[service] = image_id
        return image_ids

    def prepare(self, previous_dir: Path) -> ReleaseState:
        manifest = ReleaseManifest.load_and_verify(
            self.paths.upload_dir, self.paths.release_id
        )
        if self.paths.release_dir.exists() or self.paths.release_dir.is_symlink():
            raise ReleaseFailure("PREPARE_FAILED")
        self.paths.releases_dir.mkdir(parents=True, exist_ok=True)
        try:
            os.replace(self.paths.upload_dir, self.paths.release_dir)
            env_path = self._write_candidate_environment(
                self.paths.release_dir, previous_dir
            )
        except (OSError, ValueError):
            raise ReleaseFailure("PREPARE_FAILED") from None
        config_result = self._run(
            self._compose_command(self.paths.release_dir, "config"),
            cwd=self.paths.release_dir,
            code="PREPARE_FAILED",
        )
        self._run(
            self._compose_command(self.paths.release_dir, "build"),
            cwd=self.paths.release_dir,
            code="PREPARE_FAILED",
        )
        state = ReleaseState(
            release_id=manifest.release_id,
            source_digest=manifest.source_digest,
            compose_digest=self._digest_bytes(
                self._result_stdout(config_result).encode("utf-8")
            ),
            env_digest=self._digest_bytes(env_path.read_bytes()),
            image_ids=self._record_image_ids(
                self.paths.release_dir, manifest.release_id
            ),
            phase="prepared",
        )
        state.write(self.paths.release_dir / "release-state.json")
        return state

    def point_current(self, directory: Path) -> None:
        temporary_link = self.paths.root / f".current-{directory.name}"
        try:
            temporary_link.symlink_to(directory)
            os.replace(temporary_link, self.paths.current_link)
        except OSError:
            raise ReleaseFailure("ACTIVATION_FAILED") from None
        self.events.append(("current", str(directory)))

    def current_release_id(self) -> str | None:
        if not self.paths.current_link.is_symlink():
            return None
        try:
            return self.paths.current_link.resolve(strict=True).name
        except OSError:
            return None

    def assert_identity(self, state: ReleaseState, directory: Path) -> None:
        for service, expected_image_id in state.image_ids.items():
            result = self._run(
                (
                    "docker",
                    "image",
                    "inspect",
                    "--format",
                    "{{.Id}}",
                    self._image_tag(service, state.release_id),
                ),
                cwd=directory,
                code="IDENTITY_MISMATCH",
            )
            if self._result_stdout(result).strip() != expected_image_id:
                raise ReleaseFailure("IDENTITY_MISMATCH")

    def compose_up(self, directory: Path) -> None:
        self._run(
            self._compose_command(
                directory,
                "up",
                "--no-build",
                "--wait",
                "--force-recreate",
                "--remove-orphans",
            ),
            cwd=directory,
            code="ACTIVATION_FAILED",
        )

    def _assert_ready(self, state: ReleaseState, directory: Path) -> None:
        if self.readiness is None:
            raise ReleaseFailure("READINESS_FAILED")
        self.readiness.assert_ready(state, directory)

    def rollback(self, previous: ReleaseState) -> None:
        previous_dir = self.paths.releases_dir / previous.release_id
        try:
            self.point_current(previous_dir)
            self.assert_identity(previous, previous_dir)
            self.compose_up(previous_dir)
            self._assert_ready(previous, previous_dir)
        except ReleaseFailure:
            raise ReleaseFailure("ROLLBACK_FAILED") from None

    def run(self) -> ReleaseState:
        with self.lock():
            previous = self.require_trusted_previous()
            previous_dir = self.paths.releases_dir / previous.release_id
            candidate = self.prepare(previous_dir)
            try:
                self.point_current(self.paths.release_dir)
                self.compose_up(self.paths.release_dir)
                self.assert_identity(candidate, self.paths.release_dir)
                self._assert_ready(candidate, self.paths.release_dir)
            except ReleaseFailure as error:
                self.rollback(previous)
                raise error from None
            active = ReleaseState(
                release_id=candidate.release_id,
                source_digest=candidate.source_digest,
                compose_digest=candidate.compose_digest,
                env_digest=candidate.env_digest,
                image_ids=candidate.image_ids,
                phase="active",
            )
            active.write(self.paths.release_dir / "release-state.json")
            return active


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--release-id", required=True)
    parser.add_argument("--upload-dir", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _build_parser().parse_args(argv)
    try:
        paths = ReleasePaths.from_root(
            arguments.root, arguments.release_id, arguments.upload_dir
        )
    except ReleaseFailure as failure:
        print(
            json.dumps(
                {
                    "releaseId": arguments.release_id,
                    "status": "FAIL",
                    "code": failure.code,
                }
            )
        )
        return 1
    runner = SubprocessRunner(os.environ)
    transaction = ReleaseTransaction(
        paths=paths,
        runner=runner,
        environment=os.environ,
    )
    transaction.readiness = GatewayReadiness(
        runner=runner,
        request=urlopen,
        gateway_url="http://127.0.0.1",
        compose_command=transaction._compose_command,
    )
    try:
        state = transaction.run()
    except ReleaseFailure as failure:
        print(
            json.dumps(
                {
                    "releaseId": arguments.release_id,
                    "status": "FAIL",
                    "code": failure.code,
                }
            )
        )
        return 1
    print(
        json.dumps(
            {"releaseId": state.release_id, "status": "PASS", "phase": state.phase}
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
