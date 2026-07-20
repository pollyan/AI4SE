from __future__ import annotations

import os
import secrets
import signal
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from types import TracebackType
from urllib.error import URLError
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
    build_child_environments,
    build_secret_free_browser_environment,
    start_secret_free_playwright,
)
from .stream_observer import install_stream_observer


class LiveStackStartupError(RuntimeError):
    code = "STACK_STARTUP_FAILED"


STARTUP_LOG_TAIL_BYTES = 4096
PROXY_API_KEY_FILE_ENV_NAME = "NEW_AGENTS_PROXY_API_KEY_FILE"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _build_proxy_api_key() -> str:
    return secrets.token_urlsafe(32)


def _build_config_admin_api_key() -> str:
    return secrets.token_urlsafe(32)


def _write_proxy_api_key_file(path: Path, proxy_api_key: str) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(proxy_api_key)


def _wait_for_url(
    url: str,
    process: subprocess.Popen[bytes],
    *,
    label: str,
    timeout_seconds: float = 30,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error = ""
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(
                f"{label} exited before readiness with code {process.returncode}"
            )
        try:
            with urlopen(url, timeout=0.5) as response:
                if response.status < 500:
                    return
        except (OSError, URLError) as error:
            last_error = str(error)
        time.sleep(0.1)
    raise RuntimeError(f"{label} did not become ready at {url}: {last_error}")


def _stop_process(process: subprocess.Popen[bytes] | None) -> None:
    if process is None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    except OSError:
        if process.poll() is None:
            process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except OSError:
            process.kill()
        process.wait(timeout=5)


class LiveStack:
    def __init__(self, root: Path, llm_config: RealLlmConfig):
        self.root = root
        self.llm_config = llm_config
        self.backend_port = _free_port()
        self.frontend_port = _free_port()
        self.backend_url = f"http://127.0.0.1:{self.backend_port}"
        self.frontend_url = f"http://127.0.0.1:{self.frontend_port}/new-agents/"
        self._proxy_api_key = _build_proxy_api_key()
        self._config_admin_api_key = _build_config_admin_api_key()
        if (
            self._proxy_api_key == self._config_admin_api_key
            or self.llm_config.uses_api_key(self._proxy_api_key)
            or self.llm_config.uses_api_key(self._config_admin_api_key)
        ):
            raise ValueError(
                "provider, runtime, and config admin credentials must differ"
            )
        self._temporary_directory: tempfile.TemporaryDirectory[str] | None = None
        self._backend_process: subprocess.Popen[bytes] | None = None
        self._frontend_process: subprocess.Popen[bytes] | None = None
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._backend_log = None
        self._frontend_log = None
        self._backend_log_path: Path | None = None
        self._frontend_log_path: Path | None = None
        self.page: Page | None = None
        self.frontend_environment: dict[str, str] = {}

    def __enter__(self) -> "LiveStack":
        try:
            self._start()
            return self
        except (
            OSError,
            RuntimeError,
            ValueError,
            subprocess.SubprocessError,
            PlaywrightError,
        ) as error:
            diagnostic = self._startup_diagnostic(error)
            cleanup_errors = self._cleanup_resources()
            if cleanup_errors:
                diagnostic += "; cleanup=" + ", ".join(cleanup_errors)
            raise LiveStackStartupError(diagnostic) from None

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        cleanup_errors = self._cleanup_resources()
        if not cleanup_errors:
            return
        message = "live stack cleanup failed: " + ", ".join(cleanup_errors)
        if exc_value is not None:
            exc_value.add_note(message)
            return
        raise RuntimeError(message)

    def _start(self) -> None:
        self._temporary_directory = tempfile.TemporaryDirectory(
            prefix="ai4se-new-agents-real-"
        )
        temporary_path = Path(self._temporary_directory.name)
        self._backend_log_path = temporary_path / "backend.log"
        self._frontend_log_path = temporary_path / "frontend.log"
        self._backend_log = self._backend_log_path.open("ab")
        self._frontend_log = self._frontend_log_path.open("ab")
        backend_environment, frontend_environment = build_child_environments(
            self.llm_config,
            os.environ,
        )
        backend_environment.update(
            {
                "DATABASE_URL": f"sqlite:///{temporary_path / 'new-agents.db'}",
                "CORS_ORIGINS": f"http://127.0.0.1:{self.frontend_port}",
                "PYTHONPATH": os.pathsep.join(
                    [
                        str(self.root),
                        str(self.root / "tools/new-agents/backend"),
                        backend_environment.get("PYTHONPATH", ""),
                    ]
                ),
            }
        )
        backend_environment.pop("FLASK_TESTING", None)
        backend_environment.update(
            {
                "PROXY_API_KEY": self._proxy_api_key,
                "NEW_AGENTS_CONFIG_ADMIN_API_KEY": self._config_admin_api_key,
                "AI4SE_TRUST_GATEWAY_HEADER": "0",
            }
        )
        proxy_api_key_file = temporary_path / "new-agents-proxy-auth"
        _write_proxy_api_key_file(proxy_api_key_file, self._proxy_api_key)
        frontend_environment.update(
            {
                "NEW_AGENTS_BACKEND_URL": self.backend_url,
                PROXY_API_KEY_FILE_ENV_NAME: str(proxy_api_key_file),
                "DISABLE_HMR": "true",
            }
        )
        self.frontend_environment = {
            name: value
            for name, value in frontend_environment.items()
            if name != PROXY_API_KEY_FILE_ENV_NAME
        }

        python = Path(sys.executable)
        self._backend_process = subprocess.Popen(
            [
                str(python),
                "-m",
                "flask",
                "--app",
                "app",
                "run",
                "--host",
                "127.0.0.1",
                "--port",
                str(self.backend_port),
                "--no-reload",
                "--no-debugger",
            ],
            cwd=self.root / "tools/new-agents/backend",
            env=backend_environment,
            stdout=self._backend_log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        _wait_for_url(
            f"{self.backend_url}/api/health",
            self._backend_process,
            label="New Agents backend",
        )

        self._frontend_process = subprocess.Popen(
            [
                "npm",
                "run",
                "dev",
                "--",
                "--host",
                "127.0.0.1",
                "--port",
                str(self.frontend_port),
                "--strictPort",
            ],
            cwd=self.root / "tools/new-agents/frontend",
            env=frontend_environment,
            stdout=self._frontend_log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        _wait_for_url(
            self.frontend_url,
            self._frontend_process,
            label="New Agents frontend",
        )

        self._playwright = start_secret_free_playwright(sync_playwright, os.environ)
        self._browser = self._playwright.chromium.launch(
            headless=True,
            env=build_secret_free_browser_environment(frontend_environment),
        )
        self._context = self._browser.new_context(base_url=self.frontend_url)
        self.page = self._context.new_page()
        install_stream_observer(self.page)

    def _redact(self, value: str) -> str:
        redacted = value
        for secret in sorted(
            set(self.redaction_secrets()),
            key=len,
            reverse=True,
        ):
            if secret:
                redacted = redacted.replace(secret, "<redacted>")
        return redacted

    def redaction_secrets(self) -> tuple[str, ...]:
        proxy_api_key = getattr(self, "_proxy_api_key", "")
        config_admin_api_key = getattr(self, "_config_admin_api_key", "")
        return (
            *self.llm_config.redaction_secrets(),
            proxy_api_key,
            config_admin_api_key,
        )

    def _log_tail(self, path: Path | None, handle) -> str:
        if path is None or not path.exists():
            return ""
        if handle is not None:
            try:
                handle.flush()
            except (OSError, ValueError):
                pass
        max_secret_bytes = max(
            (
                len(secret.encode("utf-8"))
                for secret in self.redaction_secrets()
                if secret
            ),
            default=0,
        )
        overlap_bytes = max(0, max_secret_bytes - 1)
        data = path.read_bytes()[-(STARTUP_LOG_TAIL_BYTES + overlap_bytes) :]
        decoded = data.decode("utf-8", errors="replace")
        redacted = self._redact(decoded)
        return redacted[-STARTUP_LOG_TAIL_BYTES:].strip()

    def _startup_diagnostic(self, error: BaseException) -> str:
        parts = [
            self._redact(f"{type(error).__name__}: {error}"),
        ]
        backend_tail = self._log_tail(
            self._backend_log_path,
            self._backend_log,
        )
        frontend_tail = self._log_tail(
            self._frontend_log_path,
            self._frontend_log,
        )
        if backend_tail:
            parts.append(f"backendLog={backend_tail}")
        if frontend_tail:
            parts.append(f"frontendLog={frontend_tail}")
        return "; ".join(parts)

    def _cleanup_resources(self) -> list[str]:
        errors: list[str] = []
        self.page = None

        def attempt(label: str, action) -> None:
            try:
                action()
            except (
                OSError,
                RuntimeError,
                ValueError,
                subprocess.SubprocessError,
                PlaywrightError,
            ) as error:
                errors.append(self._redact(f"{label}: {type(error).__name__}: {error}"))

        if self._context is not None:
            attempt("browser context", self._context.close)
            self._context = None
        if self._browser is not None:
            attempt("browser", self._browser.close)
            self._browser = None
        if self._playwright is not None:
            attempt("playwright", self._playwright.stop)
            self._playwright = None
        if self._frontend_process is not None:
            attempt(
                "frontend process",
                lambda: _stop_process(self._frontend_process),
            )
            self._frontend_process = None
        if self._backend_process is not None:
            attempt(
                "backend process",
                lambda: _stop_process(self._backend_process),
            )
            self._backend_process = None
        if self._frontend_log is not None:
            attempt("frontend log", self._frontend_log.close)
            self._frontend_log = None
        if self._backend_log is not None:
            attempt("backend log", self._backend_log.close)
            self._backend_log = None
        if self._temporary_directory is not None:
            attempt(
                "temporary directory",
                self._temporary_directory.cleanup,
            )
            self._temporary_directory = None
        return errors

    def close(self) -> None:
        errors = self._cleanup_resources()
        if errors:
            raise RuntimeError("live stack cleanup failed: " + ", ".join(errors))
