from __future__ import annotations

import json
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

from tests.e2e.new_agents_real.config import (
    build_secret_free_browser_environment,
    secret_free_sync_playwright,
)

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
            raise RuntimeError("Vite dev server exited before becoming ready")
        try:
            with urlopen(url, timeout=0.5) as response:
                if response.status < 500:
                    return
        except (OSError, URLError) as exc:
            last_error = str(exc)
        time.sleep(0.25)
    raise RuntimeError(f"Vite dev server did not start at {url}: {last_error}")


def _open_new_agents_home(page: Page, base_url: str) -> None:
    page.goto(base_url, wait_until="domcontentloaded", timeout=60_000)
    page.get_by_role("heading", name="选择你的 AI 助手").wait_for(timeout=30_000)


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
    env = {
        **build_secret_free_browser_environment(os.environ),
        "DISABLE_HMR": "true",
    }
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
        with secret_free_sync_playwright(sync_playwright, os.environ) as playwright:
            browser = playwright.chromium.launch(
                headless=True,
                env=build_secret_free_browser_environment(os.environ),
            )
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
    story_handoff_packets: list[dict] = []

    def run_id_from_url(url: str) -> str:
        marker = "/agent/runs/"
        if marker not in url:
            return ""
        return url.split(marker, 1)[1].split("/", 1)[0].split("?", 1)[0]

    def handoff_id_from_url(url: str) -> str:
        marker = "/handoffs/"
        if marker not in url:
            return ""
        return url.split(marker, 1)[1].split("/start", 1)[0]

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

    def route_run_handoffs(route: Route) -> None:
        has_value_blueprint = (
            route_agent_stream.call_counts.get(("VALUE_DISCOVERY", "BLUEPRINT"), 0) > 0
        )
        handoffs = []
        if has_value_blueprint:
            handoffs = [
                {
                    "id": "value-blueprint-to-test-design",
                    "label": "交给 Lisa 做测试设计",
                    "sourceRunId": "mock-run-value_discovery",
                    "sourceWorkflowId": "VALUE_DISCOVERY",
                    "sourceStageId": "BLUEPRINT",
                    "sourceArtifactVersion": 1,
                    "sourceArtifactDigest": "sha256:mock-value-blueprint",
                    "sourceSummary": "AI 测试设计助手需求蓝图，包含产品概述、风险评估和 Lisa 输入。",
                    "unconfirmedItems": [],
                    "targetInputChecklist": [
                        "复核来源版本 VALUE_DISCOVERY/BLUEPRINT v1",
                        "基于蓝图风险和验收标准继续做测试设计",
                    ],
                    "targetWorkflowId": "TEST_DESIGN",
                    "targetStageId": "CLARIFY",
                    "targetAgentId": "lisa",
                    "prompt": (
                        "请基于 Alex 的价值蓝图继续做 Lisa 测试设计。\n\n"
                        "# AI 测试设计助手需求蓝图\n\n"
                        "## 1. 产品概述\n"
                        "AI 测试设计助手帮助测试负责人从需求生成测试策略和测试用例。\n\n"
                        "## 7. 风险评估\n"
                        "重点关注输出质量、权限隔离、需求追溯和 LLM judge 质量门。"
                    ),
                },
                {
                    "id": "value-blueprint-to-req-review",
                    "label": "交给 Lisa 做需求评审",
                    "sourceRunId": "mock-run-value_discovery",
                    "sourceWorkflowId": "VALUE_DISCOVERY",
                    "sourceStageId": "BLUEPRINT",
                    "sourceArtifactVersion": 1,
                    "sourceArtifactDigest": "sha256:mock-value-blueprint",
                    "sourceSummary": "AI 测试设计助手需求蓝图，适合作为 PRD 评审输入。",
                    "unconfirmedItems": [],
                    "targetInputChecklist": [
                        "复核来源版本 VALUE_DISCOVERY/BLUEPRINT v1",
                        "评审核心需求、验收标准和风险项",
                    ],
                    "targetWorkflowId": "REQ_REVIEW",
                    "targetStageId": "REVIEW",
                    "targetAgentId": "lisa",
                    "prompt": "请基于 Alex 的价值蓝图继续做 Lisa 需求评审。",
                },
                {
                    "id": "value-discovery-blueprint-to-story-breakdown",
                    "label": "从需求蓝图继续拆用户故事",
                    "sourceRunId": "mock-run-value_discovery",
                    "sourceWorkflowId": "VALUE_DISCOVERY",
                    "sourceStageId": "BLUEPRINT",
                    "sourceArtifactVersion": 1,
                    "sourceArtifactDigest": "sha256:mock-value-blueprint",
                    "sourceSummary": "AI 测试设计助手需求蓝图，包含 P0 需求、MVP 范围和风险评估。",
                    "unconfirmedItems": [],
                    "targetInputChecklist": [
                        "继承 VALUE_DISCOVERY/BLUEPRINT v1",
                        "按业务价值拆成可交给 AI Coding 的用户故事",
                    ],
                    "targetWorkflowId": "STORY_BREAKDOWN",
                    "targetStageId": "INPUT_ANALYSIS",
                    "targetAgentId": "alex",
                    "prompt": (
                        "请基于 Alex 的需求蓝图继续拆用户故事。\n\n"
                        "# AI 测试设计助手需求蓝图\n\n"
                        "## 1. 产品概述\n"
                        "AI 测试设计助手帮助测试负责人从需求生成测试策略和测试用例。\n\n"
                        "## 7. 风险评估\n"
                        "重点关注输出质量、权限隔离、需求追溯和 LLM judge 质量门。"
                    ),
                },
            ]

        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "runId": "mock-run-value_discovery",
                    "sourceWorkflowId": "VALUE_DISCOVERY",
                    "handoffs": handoffs,
                },
                ensure_ascii=False,
            ),
        )

    def route_start_handoff(route: Route) -> None:
        handoff_id = handoff_id_from_url(route.request.url)
        if handoff_id == "value-discovery-blueprint-to-story-breakdown":
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(
                    {
                        "id": "value-discovery-blueprint-to-story-breakdown",
                        "label": "从需求蓝图继续拆用户故事",
                        "sourceRunId": "mock-run-value_discovery",
                        "sourceWorkflowId": "VALUE_DISCOVERY",
                        "sourceStageId": "BLUEPRINT",
                        "sourceArtifactVersion": 1,
                        "sourceArtifactDigest": "sha256:mock-value-blueprint",
                        "sourceSummary": "AI 测试设计助手需求蓝图，包含 P0 需求、MVP 范围和风险评估。",
                        "unconfirmedItems": [],
                        "targetInputChecklist": [
                            "继承 VALUE_DISCOVERY/BLUEPRINT v1",
                            "按业务价值拆成可交给 AI Coding 的用户故事",
                        ],
                        "targetRunId": "mock-run-user_story_breakdown-handoff",
                        "targetWorkflowId": "STORY_BREAKDOWN",
                        "targetStageId": "INPUT_ANALYSIS",
                        "targetAgentId": "alex",
                        "prompt": (
                            "请基于 Alex 的需求蓝图继续拆用户故事。\n\n"
                            "# AI 测试设计助手需求蓝图\n\n"
                            "## 1. 产品概述\n"
                            "AI 测试设计助手帮助测试负责人从需求生成测试策略和测试用例。\n\n"
                            "## 7. 风险评估\n"
                            "重点关注输出质量、权限隔离、需求追溯和 LLM judge 质量门。"
                        ),
                    },
                    ensure_ascii=False,
                ),
            )
            return

        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "id": "value-blueprint-to-test-design",
                    "label": "交给 Lisa 做测试设计",
                    "sourceRunId": "mock-run-value_discovery",
                    "sourceWorkflowId": "VALUE_DISCOVERY",
                    "sourceStageId": "BLUEPRINT",
                    "sourceArtifactVersion": 1,
                    "sourceArtifactDigest": "sha256:mock-value-blueprint",
                    "sourceSummary": "AI 测试设计助手需求蓝图，包含产品概述、风险评估和 Lisa 输入。",
                    "unconfirmedItems": [],
                    "targetInputChecklist": [
                        "复核来源版本 VALUE_DISCOVERY/BLUEPRINT v1",
                        "基于蓝图风险和验收标准继续做测试设计",
                    ],
                    "targetRunId": "mock-run-test_design-handoff",
                    "targetWorkflowId": "TEST_DESIGN",
                    "targetStageId": "CLARIFY",
                    "targetAgentId": "lisa",
                    "prompt": (
                        "请基于 Alex 的价值蓝图继续做 Lisa 测试设计。\n\n"
                        "# AI 测试设计助手需求蓝图\n\n"
                        "## 1. 产品概述\n"
                        "AI 测试设计助手帮助测试负责人从需求生成测试策略和测试用例。\n\n"
                        "## 7. 风险评估\n"
                        "重点关注输出质量、权限隔离、需求追溯和 LLM judge 质量门。"
                    ),
                },
                ensure_ascii=False,
            ),
        )

    def route_run_snapshot(route: Route) -> None:
        run_id = run_id_from_url(route.request.url)
        if run_id == "mock-run-user_story_breakdown-handoff":
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(
                    {
                        "run": {
                            "id": "mock-run-user_story_breakdown-handoff",
                            "workflowId": "STORY_BREAKDOWN",
                            "agentId": "alex",
                            "currentStageId": "INPUT_ANALYSIS",
                            "status": "active",
                            "model": "mock",
                        },
                        "messages": [
                            {
                                "role": "user",
                                "content": (
                                    "请基于 Alex 的需求蓝图继续拆用户故事。\n\n"
                                    "# AI 测试设计助手需求蓝图\n\n"
                                    "## 1. 产品概述\n"
                                    "AI 测试设计助手帮助测试负责人从需求生成测试策略和测试用例。\n\n"
                                    "## 7. 风险评估\n"
                                    "重点关注输出质量、权限隔离、需求追溯和 LLM judge 质量门。"
                                ),
                                "sequenceIndex": 1,
                            }
                        ],
                        "artifacts": [],
                        "contextSummaries": [],
                    },
                    ensure_ascii=False,
                ),
            )
            return

        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "run": {
                        "id": "mock-run-test_design-handoff",
                        "workflowId": "TEST_DESIGN",
                        "agentId": "lisa",
                        "currentStageId": "CLARIFY",
                        "status": "active",
                        "model": "mock",
                    },
                    "messages": [
                        {
                            "role": "user",
                            "content": (
                                "请基于 Alex 的价值蓝图继续做 Lisa 测试设计。\n\n"
                                "# AI 测试设计助手需求蓝图\n\n"
                                "## 1. 产品概述\n"
                                "AI 测试设计助手帮助测试负责人从需求生成测试策略和测试用例。\n\n"
                                "## 7. 风险评估\n"
                                "重点关注输出质量、权限隔离、需求追溯和 LLM judge 质量门。"
                            ),
                            "sequenceIndex": 1,
                        }
                    ],
                    "artifacts": [],
                    "contextSummaries": [],
                },
                ensure_ascii=False,
            ),
        )

    def route_story_handoff_candidates(route: Route) -> None:
        run_id = run_id_from_url(route.request.url) or "mock-run-user_story_breakdown"
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "runId": run_id,
                    "workflowId": "STORY_BREAKDOWN",
                    "stageId": "SPRINT_PLAN",
                    "sourceArtifactVersion": 1,
                    "sourceArtifactDigest": "sha256:mock-user-story-handoff",
                    "candidates": [
                        {
                            "storyId": "US-001",
                            "title": "生成澄清问题",
                            "requirementIds": ["REQ-001"],
                            "userValue": "测试负责人能在设计前发现缺失业务规则",
                            "readyReason": "验收标准和业务规则已明确",
                        }
                    ],
                },
                ensure_ascii=False,
            ),
        )

    def route_story_handoff_packets(route: Route) -> None:
        run_id = run_id_from_url(route.request.url) or "mock-run-user_story_breakdown"
        if route.request.method == "POST":
            body = route.request.post_data_json
            packet = {
                "sourceRunId": run_id,
                "sourceWorkflowId": "STORY_BREAKDOWN",
                "sourceStageId": body.get("stageId", "SPRINT_PLAN"),
                "sourceArtifactVersion": 1,
                "sourceArtifactDigest": "sha256:mock-user-story-handoff",
                "createdAt": 1710000000000,
                "storyId": body["storyId"],
                "requirementIds": ["REQ-001"],
                "userStory": (
                    "作为测试负责人，我想要输入需求后看到待澄清问题和隐式风险，"
                    "以便在测试设计前补齐缺失业务规则"
                ),
                "acceptanceCriteria": [
                    "输出需求事实清单",
                    "输出阻断性待澄清问题",
                    "输出 P0 风险线索",
                ],
                "businessRules": ["问题必须标注阻断性、责任方和状态"],
                "nonFunctionalNotes": ["输出内容需要可追溯、可评审"],
                "outOfScope": ["不直接生成用例"],
                "dependencies": ["用户提供需求文本"],
                "openQuestions": ["问题分类口径可在试点中继续校准"],
            }
            story_handoff_packets.clear()
            story_handoff_packets.append(
                {
                    "id": "mock-packet-us-001",
                    "storyId": "US-001",
                    "createdAt": 1710000000000,
                    "isStale": False,
                    "currentSourceArtifactVersion": 1,
                    "currentSourceArtifactDigest": "sha256:mock-user-story-handoff",
                    "packet": packet,
                }
            )
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(packet, ensure_ascii=False),
            )
            return

        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "runId": run_id,
                    "workflowId": "STORY_BREAKDOWN",
                    "stageId": "SPRINT_PLAN",
                    "sourceArtifactVersion": 1,
                    "sourceArtifactDigest": "sha256:mock-user-story-handoff",
                    "packets": story_handoff_packets,
                },
                ensure_ascii=False,
            ),
        )

    page.route("**/new-agents/api/config", route_config)
    page.route("**/new-agents/api/agent/runs/stream", route_agent_stream)
    page.route(
        "**/new-agents/api/agent/runs/*/story-handoff-candidates**",
        route_story_handoff_candidates,
    )
    page.route(
        "**/new-agents/api/agent/runs/*/story-handoff-packets**",
        route_story_handoff_packets,
    )
    page.route(
        "**/new-agents/api/agent/runs/*/handoffs/*/start",
        route_start_handoff,
    )
    page.route("**/new-agents/api/agent/runs/*/handoffs", route_run_handoffs)
    page.route(
        "**/new-agents/api/agent/runs/mock-run-test_design-handoff",
        route_run_snapshot,
    )
    page.route(
        "**/new-agents/api/agent/runs/mock-run-user_story_breakdown-handoff",
        route_run_snapshot,
    )
    _open_new_agents_home(page, new_agents_base_url)
    page.evaluate("localStorage.clear()")
    page.reload(wait_until="domcontentloaded", timeout=60_000)
    page.get_by_role("heading", name="选择你的 AI 助手").wait_for(timeout=30_000)

    yield page

    context.close()
    assert console_errors == []
