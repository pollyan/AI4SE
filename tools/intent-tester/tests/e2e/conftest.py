from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import socket
import threading
import time

import pytest
import requests
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright
from werkzeug.security import generate_password_hash
from werkzeug.serving import make_server

from backend.app import create_app


def _free_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


@dataclass
class LiveIntentServer:
    app: object
    base_url: str
    server: object
    thread: threading.Thread

    def close(self) -> None:
        self.server.shutdown()
        self.thread.join(timeout=5)
        self.server.server_close()
        assert not self.thread.is_alive(), "Intent E2E server did not stop"


def _start_server(tmp_path: Path, access_mode: str) -> LiveIntentServer:
    port = _free_port()
    origin = f"http://127.0.0.1:{port}"
    app = create_app(
        {
            "TESTING": True,
            "AI4SE_ENV": "test",
            "INTENT_ACCESS_MODE": access_mode,
            "INTENT_EXECUTION_ENABLED": True,
            "INTENT_PUBLIC_ORIGIN": origin,
            "INTENT_PROXY_TOPOLOGY": "local-host",
            "INTENT_PROXY_TOKEN": "e2e-proxy-token-with-at-least-32-bytes",
            "SECRET_KEY": "e2e-secret-key-with-at-least-32-bytes",
            "INTENT_TESTER_ADMIN_PASSWORD_HASH": generate_password_hash(
                "e2e-admin-password"
            ),
            "OPENAI_API_KEY": "e2e-provider-key",
            "OPENAI_BASE_URL": "http://127.0.0.1:9999/v1",
            "MIDSCENE_MODEL_NAME": "e2e-offline-model",
            "MIDSCENE_SERVER_URL": "http://127.0.0.1:59999",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        }
    )
    server = make_server("127.0.0.1", port, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    live = LiveIntentServer(app=app, base_url=origin, server=server, thread=thread)
    thread.start()

    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        try:
            if requests.get(f"{origin}/health", timeout=0.5).ok:
                return live
        except requests.RequestException:
            pass
        time.sleep(0.05)
    live.close()
    raise AssertionError("Intent E2E server did not become healthy")


@pytest.fixture
def restricted_server(tmp_path: Path):
    server = _start_server(tmp_path, "restricted")
    try:
        yield server
    finally:
        server.close()


@pytest.fixture
def public_readonly_server(tmp_path: Path):
    server = _start_server(tmp_path, "public-readonly")
    try:
        yield server
    finally:
        server.close()


@pytest.fixture(scope="module")
def chromium_browser():
    with sync_playwright() as playwright:
        executable = Path(playwright.chromium.executable_path)
        if not executable.exists():
            pytest.fail(
                "BLOCKED: Playwright Chromium is missing; run "
                "`python -m playwright install chromium`"
            )
        try:
            browser = playwright.chromium.launch(headless=True)
        except PlaywrightError as error:
            pytest.fail(
                "BLOCKED: real Chromium could not launch; run "
                "`python -m playwright install chromium` and verify OS browser "
                f"permissions. Original error: {error}"
            )
        try:
            yield browser
        finally:
            browser.close()
