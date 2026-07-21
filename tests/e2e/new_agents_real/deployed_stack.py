from __future__ import annotations

import json
import os
import re
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Mapping
from urllib.parse import urlsplit
from urllib.request import urlopen

from playwright.sync_api import (
    Browser,
    BrowserContext,
    Error as PlaywrightError,
    Page,
    Playwright,
    sync_playwright,
)

from .config import (
    RealLlmConfig,
    build_secret_free_browser_environment,
    start_secret_free_playwright,
)
from .stream_observer import install_stream_observer

PROJECT_NAME = re.compile(r"ai4se-pre-push-[0-9a-f]{12}")
RESTART_READINESS_TIMEOUT_SECONDS = 45
RESTART_READINESS_POLL_SECONDS = 0.2


class DeploymentTargetError(ValueError):
    pass


def _is_loopback(hostname: str | None) -> bool:
    return hostname in {"127.0.0.1", "::1", "localhost"}


@dataclass(frozen=True)
class DeploymentTarget:
    url: str

    @classmethod
    def parse(cls, value: str) -> "DeploymentTarget":
        try:
            parsed = urlsplit(value)
            port = parsed.port
        except ValueError as error:
            raise DeploymentTargetError("deployment target URL is invalid") from error
        if (
            parsed.scheme not in {"http", "https"}
            or not _is_loopback(parsed.hostname)
            or port is None
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path != "/new-agents/"
            or parsed.query
            or parsed.fragment
        ):
            raise DeploymentTargetError(
                "deployment target must be a loopback /new-agents/ URL"
            )
        return cls(value)

    @property
    def origin(self) -> str:
        parsed = urlsplit(self.url)
        return f"{parsed.scheme}://{parsed.netloc}"


@dataclass(frozen=True)
class DeploymentControl:
    root: Path
    evidence_root: Path
    project_name: str
    target: DeploymentTarget
    env_path: Path

    @classmethod
    def from_environment(
        cls,
        root: Path,
        environ: Mapping[str, str],
    ) -> "DeploymentControl":
        evidence_value = str(environ.get("NEW_AGENTS_REAL_EVIDENCE_DIR", "")).strip()
        descriptor_value = str(
            environ.get("NEW_AGENTS_REAL_DEPLOYMENT_CONTROL_FILE", "")
        ).strip()
        target_value = str(environ.get("NEW_AGENTS_REAL_TARGET_URL", "")).strip()
        if not evidence_value or not descriptor_value or not target_value:
            raise DeploymentTargetError(
                "deployed E2E requires all control environment values"
            )
        evidence_root = Path(evidence_value).resolve()
        allowed_root = (root / "test-results" / "pre-push").resolve()
        if not evidence_root.is_absolute() or not evidence_root.is_relative_to(
            allowed_root
        ):
            raise DeploymentTargetError(
                "deployment evidence root is outside pre-push output"
            )
        descriptor = Path(descriptor_value).resolve()
        if not descriptor.is_relative_to(evidence_root) or not descriptor.is_file():
            raise DeploymentTargetError(
                "deployment control descriptor is outside evidence root"
            )
        try:
            payload = json.loads(descriptor.read_text(encoding="utf-8"))
            project_name = payload["projectName"]
            descriptor_target = payload["targetUrl"]
            env_path = Path(payload["envFile"]).resolve()
        except (OSError, TypeError, ValueError, KeyError) as error:
            raise DeploymentTargetError(
                "deployment control descriptor is invalid"
            ) from error
        target = DeploymentTarget.parse(target_value)
        if descriptor_target != target.url:
            raise DeploymentTargetError(
                "deployment target does not match its control descriptor"
            )
        if (
            not isinstance(project_name, str)
            or PROJECT_NAME.fullmatch(project_name) is None
        ):
            raise DeploymentTargetError(
                "deployment project name is not a pre-push project"
            )
        if not env_path.is_relative_to(evidence_root) or not env_path.is_file():
            raise DeploymentTargetError(
                "deployment environment file is outside evidence root"
            )
        if env_path.stat().st_mode & 0o077:
            raise DeploymentTargetError("deployment environment file must be private")
        return cls(root, evidence_root, project_name, target, env_path)

    def restart_backend(self) -> None:
        import subprocess

        command = (
            "docker",
            "compose",
            "-p",
            self.project_name,
            "-f",
            str(self.root / "docker-compose.prod.yml"),
            "-f",
            str(self.root / "docker-compose.pre-push.yml"),
            "--env-file",
            str(self.env_path),
            "restart",
            "new-agents-backend",
        )
        result = subprocess.run(
            command,
            cwd=self.root,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError("controlled deployed backend restart failed")


class DeployedStack:
    """Browser facade for a local production-shaped target started by pre-push."""

    def __init__(
        self,
        root: Path,
        llm_config: RealLlmConfig,
        target: DeploymentTarget,
        control: DeploymentControl,
    ):
        self.root = root
        self.llm_config = llm_config
        self.target = target
        self.control = control
        self.frontend_url = target.url
        self.page: Page | None = None
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None

    @contextmanager
    def _request(self, url: str) -> Iterator[Any]:
        with urlopen(url, timeout=10) as response:
            yield response

    def _assert_ready(self) -> None:
        with self._request(self.frontend_url) as response:
            if response.status != 200:
                raise RuntimeError("deployed New Agents frontend is not ready")
        with self._request(f"{self.target.origin}/new-agents/api/health") as response:
            if response.status != 200:
                raise RuntimeError("deployed New Agents backend is not ready")
            payload = json.loads(response.read())
            if payload.get("status") != "ok":
                raise RuntimeError("deployed New Agents backend health is invalid")
        with self._request(
            f"{self.target.origin}/new-agents/api/readiness"
        ) as response:
            if response.status != 200:
                raise RuntimeError("deployed New Agents database readiness is unavailable")
            payload = json.loads(response.read())
            if payload != {
                "status": "ok",
                "service": "new-agents-backend",
                "database": "ok",
            }:
                raise RuntimeError("deployed New Agents database readiness is invalid")
        with self._request(
            f"{self.target.origin}/new-agents/api/readiness/stream"
        ) as response:
            if response.status != 200:
                raise RuntimeError("deployed New Agents readiness stream is unavailable")
            content_type = response.headers.get("Content-Type", "")
            body = response.read()
            if (
                not content_type.startswith("text/event-stream")
                or b'"type": "run_started"' not in body
                or b"data: [DONE]" not in body
            ):
                raise RuntimeError("deployed New Agents readiness stream is invalid")

    def __enter__(self) -> "DeployedStack":
        self._assert_ready()
        self._playwright = start_secret_free_playwright(sync_playwright, os.environ)
        self._browser = self._playwright.chromium.launch(
            headless=True,
            env=build_secret_free_browser_environment(os.environ),
        )
        self._context = self._browser.new_context(base_url=self.frontend_url)
        self.page = self._context.new_page()
        install_stream_observer(self.page)
        return self

    def restart_backend(self) -> None:
        self.control.restart_backend()
        deadline = time.monotonic() + RESTART_READINESS_TIMEOUT_SECONDS
        last_error: BaseException | None = None
        while time.monotonic() < deadline:
            try:
                self._assert_ready()
                return
            except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as error:
                last_error = error
                time.sleep(RESTART_READINESS_POLL_SECONDS)
        raise RuntimeError(
            "deployed backend did not become ready after restart"
        ) from last_error

    def redaction_secrets(self) -> tuple[str, ...]:
        return self.llm_config.redaction_secrets()

    def close(self) -> None:
        errors: list[Exception] = []
        for resource in (self._context, self._browser, self._playwright):
            if resource is None:
                continue
            try:
                resource.close() if hasattr(resource, "close") else resource.stop()
            except (OSError, RuntimeError, ValueError, PlaywrightError) as error:
                errors.append(error)
        self.page = None
        self._context = None
        self._browser = None
        self._playwright = None
        if errors:
            raise RuntimeError("deployed browser cleanup failed") from errors[0]

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()
