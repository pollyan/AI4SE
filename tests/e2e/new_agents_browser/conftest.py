from __future__ import annotations

import os
import socket
import subprocess
import time
from collections.abc import Generator
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import pytest
from playwright.sync_api import Browser, Page, Route, sync_playwright

from .sse_mock import build_agent_sse_response


ROOT = Path(__file__).resolve().parents[3]
FRONTEND_DIR = ROOT / "tools" / "new-agents" / "frontend"
CODEX_NODE = (
    Path.home()
    / ".cache"
    / "codex-runtimes"
    / "codex-primary-runtime"
    / "dependencies"
    / "node"
    / "bin"
    / "node"
)

if "PLAYWRIGHT_NODEJS_PATH" not in os.environ and CODEX_NODE.exists():
    os.environ["PLAYWRIGHT_NODEJS_PATH"] = str(CODEX_NODE)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_server(url: str, process: subprocess.Popen[str]) -> None:
    deadline = time.time() + 30
    last_error = ""
    while time.time() < deadline:
        if process.poll() is not None:
            raise RuntimeError(
                "Vite dev server exited before becoming ready"
            )
        try:
            with urlopen(url, timeout=0.5) as response:
                if response.status < 500:
                    return
        except (OSError, URLError) as exc:
            last_error = str(exc)
        time.sleep(0.25)
    raise RuntimeError(f"Vite dev server did not start at {url}: {last_error}")


@pytest.fixture(scope="session")
def new_agents_base_url() -> Generator[str, None, None]:
    port = int(os.environ.get("NEW_AGENTS_E2E_PORT", "0")) or _free_port()
    base_url = f"http://127.0.0.1:{port}/new-agents/"
    command = [
        "npm",
        "run",
        "dev",
        "--",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--strictPort",
    ]
    env = {**os.environ, "DISABLE_HMR": "true"}
    process = subprocess.Popen(
        command,
        cwd=FRONTEND_DIR,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        _wait_for_server(base_url, process)
        yield base_url
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


@pytest.fixture(scope="session")
def browser() -> Generator[Browser, None, None]:
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                yield browser
            finally:
                browser.close()
    except Exception as exc:
        message = str(exc)
        if "Executable doesn't exist" in message or "playwright install" in message:
            pytest.fail(
                "Python Playwright browser binaries are not installed. "
                "Run `python3 -m playwright install chromium` and retry."
            )
        raise


@pytest.fixture()
def new_agents_page(
    browser: Browser,
    new_agents_base_url: str,
) -> Generator[Page, None, None]:
    context = browser.new_context(base_url=new_agents_base_url)
    page = context.new_page()
    console_errors: list[str] = []

    def capture_console_error(message) -> None:
        text = message.text
        if message.type == "error" and "Failed to load resource" not in text:
            console_errors.append(text)

    page.on("console", capture_console_error)

    def route_config(route: Route) -> None:
        route.fulfill(
            status=200,
            content_type="application/json",
            body='{"hasDefault": true, "baseUrl": "mock", "model": "mock"}',
        )

    def route_agent_stream(route: Route) -> None:
        body = route.request.post_data_json
        key = (body["workflowId"], body["stageId"])
        route_agent_stream.call_counts[key] = (
            route_agent_stream.call_counts.get(key, 0) + 1
        )
        turn_index = route_agent_stream.call_counts[key] - 1
        route.fulfill(
            status=200,
            content_type="text/event-stream",
            body=build_agent_sse_response(body, turn_index=turn_index),
        )

    route_agent_stream.call_counts = {}

    page.route("**/new-agents/api/config", route_config)
    page.route("**/new-agents/api/agent/runs/stream", route_agent_stream)
    page.goto(new_agents_base_url)
    page.evaluate("localStorage.clear()")
    page.reload()

    yield page

    context.close()
    assert console_errors == []
