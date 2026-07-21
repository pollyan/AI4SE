#!/usr/bin/env python3
"""Isolated, production-shaped Docker Compose harness for the pre-push gate."""

from __future__ import annotations

import json
import os
import secrets
import socket
import subprocess
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator, Mapping, Protocol
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from werkzeug.security import generate_password_hash

MINIMUM_COMPOSE_VERSION = (2, 24, 4)
POSTGRES_USER = "prepush"
POSTGRES_DATABASE = "ai4se"


class LlmConfiguration(Protocol):
    def backend_environment(self) -> dict[str, str]: ...


def _free_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _random_secret() -> str:
    return secrets.token_urlsafe(32)


def _write_private_environment(path: Path, values: Mapping[str, str]) -> None:
    if any("\n" in value or "\r" in value for value in values.values()):
        raise ValueError("pre-push deployment environment values must be single-line")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        for key, value in sorted(values.items()):
            escaped_value = value.replace("'", "\\'")
            handle.write(f"{key}='{escaped_value}'\n")


@dataclass(frozen=True)
class DeploymentConfig:
    root: Path
    output_dir: Path
    project_name: str
    gateway_port: int
    env_path: Path
    environment: Mapping[str, str] = field(repr=False, compare=False)

    @property
    def evidence_dir(self) -> Path:
        return self.output_dir / "real-e2e"

    @property
    def control_path(self) -> Path:
        return self.evidence_dir / "deployment-control.json"

    @property
    def frontend_url(self) -> str:
        return f"http://127.0.0.1:{self.gateway_port}/new-agents/"

    @property
    def compose_files(self) -> tuple[Path, Path]:
        return (
            self.root / "docker-compose.prod.yml",
            self.root / "docker-compose.pre-push.yml",
        )

    @classmethod
    def create(
        cls,
        *,
        root: Path,
        output_dir: Path,
        llm_config: LlmConfiguration,
        common_frontend_dist: Path | None = None,
    ) -> "DeploymentConfig":
        project_name = f"ai4se-pre-push-{secrets.token_hex(6)}"
        gateway_port = _free_loopback_port()
        env_path = output_dir / "real-e2e" / "deployment.env"
        provider_environment = llm_config.backend_environment()
        proxy_api_key = _random_secret()
        config_admin_api_key = _random_secret()
        if proxy_api_key == config_admin_api_key:
            raise RuntimeError("generated independent deployment credentials collided")
        frontend_dist = common_frontend_dist or output_dir / "common-frontend-dist"
        environment = {
            "PRE_PUSH_PROJECT_NAME": project_name,
            "PRE_PUSH_GATEWAY_PORT": str(gateway_port),
            "PRE_PUSH_COMMON_FRONTEND_DIST": str(frontend_dist),
            "DB_USER": POSTGRES_USER,
            "DB_PASSWORD": _random_secret(),
            "SECRET_KEY": _random_secret(),
            "INTENT_ACCESS_MODE": "restricted",
            "INTENT_EXECUTION_ENABLED": "false",
            "INTENT_PUBLIC_ORIGIN": "https://pre-push.invalid",
            "INTENT_TESTER_ADMIN_PASSWORD_HASH": generate_password_hash(
                _random_secret(), method="pbkdf2:sha256:1000000"
            ),
            "INTENT_PROXY_TOKEN": _random_secret(),
            "OPENAI_API_KEY": "",
            "OPENAI_BASE_URL": "",
            "MIDSCENE_MODEL_NAME": "",
            "NEW_AGENTS_CONFIG_ADMIN_API_KEY": config_admin_api_key,
            "PROXY_API_KEY": proxy_api_key,
            **provider_environment,
        }
        _write_private_environment(env_path, environment)
        config = cls(
            root=root,
            output_dir=output_dir,
            project_name=project_name,
            gateway_port=gateway_port,
            env_path=env_path,
            environment=environment,
        )
        descriptor = {
            "projectName": config.project_name,
            "targetUrl": config.frontend_url,
            "envFile": str(config.env_path),
        }
        descriptor_path = config.control_path
        descriptor_path.write_text(
            json.dumps(descriptor, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.chmod(descriptor_path, 0o600)
        return config


def render_pre_push_compose(config: DeploymentConfig) -> dict[str, Any]:
    """Expose the one dynamic overlay value for deterministic contract tests."""
    return {
        "services": {
            "nginx": {
                "ports": [f"127.0.0.1:{config.gateway_port}:80"],
            }
        }
    }


class ProductionHarness:
    """Run the production Compose topology under isolated names and loopback port."""

    def __init__(self, config: DeploymentConfig):
        self.config = config
        self.checked_paths: list[str] = []
        self._started = False

    def _compose_command(self, *arguments: str) -> tuple[str, ...]:
        compose_files = tuple(
            option for path in self.config.compose_files for option in ("-f", str(path))
        )
        return (
            "docker",
            "compose",
            "-p",
            self.config.project_name,
            *compose_files,
            "--env-file",
            str(self.config.env_path),
            *arguments,
        )

    @staticmethod
    def _parse_version(value: str) -> tuple[int, int, int] | None:
        parts = value.strip().removeprefix("v").split(".")
        if len(parts) < 2:
            return None
        numbers: list[int] = []
        for part in parts[:3]:
            digits = "".join(character for character in part if character.isdigit())
            if not digits:
                return None
            numbers.append(int(digits))
        while len(numbers) < 3:
            numbers.append(0)
        return tuple(numbers)

    def _require_compose_version(self) -> None:
        result = subprocess.run(
            ("docker", "compose", "version", "--short"),
            text=True,
            capture_output=True,
            check=False,
        )
        version = self._parse_version(result.stdout) if result.returncode == 0 else None
        if version is None or version < MINIMUM_COMPOSE_VERSION:
            raise RuntimeError("Docker Compose v2.24.4 or newer is required")

    def _run_compose(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            self._compose_command(*arguments),
            cwd=self.config.root,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"isolated production Compose {arguments[0]} command failed"
            )
        return result

    def _run_project_cleanup(self) -> None:
        """Remove only resources carrying this isolated Compose project label."""
        result = subprocess.run(
            (
                "docker",
                "compose",
                "-p",
                self.config.project_name,
                "down",
                "--volumes",
                "--remove-orphans",
            ),
            cwd=self.config.root,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError("isolated project cleanup command failed")

    @contextmanager
    def request(self, request: str | Request, *, timeout: float) -> Iterator[Any]:
        with urlopen(request, timeout=timeout) as response:
            yield response

    def _wait_for_http(self, path: str, *, expect_json: bool = False) -> None:
        deadline = time.monotonic() + 45
        last_error: BaseException | None = None
        url = f"http://127.0.0.1:{self.config.gateway_port}{path}"
        while time.monotonic() < deadline:
            self.checked_paths.append(url)
            try:
                with self.request(url, timeout=1) as response:
                    if response.status != 200:
                        raise RuntimeError("unexpected readiness status")
                    body = response.read()
                    if expect_json:
                        payload = json.loads(body)
                        if payload.get("status") != "ok":
                            raise RuntimeError("backend readiness did not report ok")
                    return
            except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as error:
                last_error = error
                time.sleep(0.2)
        raise RuntimeError(
            "isolated production readiness did not complete"
        ) from last_error

    def _assert_config_admin_is_protected(self) -> None:
        url = f"http://127.0.0.1:{self.config.gateway_port}/new-agents/api/config"
        request = Request(
            url,
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with self.request(request, timeout=5) as response:
                status = response.status
        except HTTPError as error:
            status = error.code
        if status != 401:
            raise RuntimeError("production config administration is not protected")

    def _assert_database_read_write(self) -> None:
        self._run_compose(
            "exec",
            "-T",
            "postgres",
            "psql",
            "-U",
            POSTGRES_USER,
            "-d",
            POSTGRES_DATABASE,
            "-v",
            "ON_ERROR_STOP=1",
            "-c",
            "CREATE TEMPORARY TABLE pre_push_probe (id integer); "
            "INSERT INTO pre_push_probe VALUES (1); "
            "SELECT count(*) FROM pre_push_probe;",
        )

    def _assert_nginx_sse_configuration(self) -> None:
        result = self._run_compose("exec", "-T", "nginx", "nginx", "-T")
        nginx_configuration = f"{result.stdout}\n{result.stderr}"
        if (
            "location /new-agents/api/" not in nginx_configuration
            or "proxy_buffering off;" not in nginx_configuration
            or "X-AI4SE-Gateway" not in nginx_configuration
        ):
            raise RuntimeError("production Nginx SSE configuration is unavailable")

    def assert_ready(self) -> None:
        self._wait_for_http("/new-agents/")
        self._wait_for_http("/new-agents/api/health", expect_json=True)
        self._assert_config_admin_is_protected()
        self._run_compose(
            "exec",
            "-T",
            "postgres",
            "pg_isready",
            "-U",
            POSTGRES_USER,
            "-d",
            POSTGRES_DATABASE,
        )
        self._assert_database_read_write()
        self._assert_nginx_sse_configuration()

    def start(self) -> None:
        try:
            self._require_compose_version()
            self._run_compose("config", "--quiet")
            self._run_compose("build")
            self._started = True
            self._run_compose("up", "--wait", "--remove-orphans")
            self.assert_ready()
        except (OSError, RuntimeError, ValueError):
            self.close()
            raise

    def restart_backend(self) -> None:
        if not self._started:
            raise RuntimeError("isolated production stack is not running")
        self._run_compose("restart", "new-agents-backend")
        self.assert_ready()

    def close(self) -> None:
        cleanup_error: OSError | RuntimeError | None = None
        try:
            if self._started:
                try:
                    self._run_compose("down", "--volumes", "--remove-orphans")
                except RuntimeError:
                    self._run_project_cleanup()
        finally:
            self._started = False
            try:
                self.config.env_path.unlink(missing_ok=True)
            except OSError as error:
                cleanup_error = error
        if cleanup_error is not None:
            raise RuntimeError(
                "isolated deployment credential cleanup failed"
            ) from cleanup_error

    def __enter__(self) -> "ProductionHarness":
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()
