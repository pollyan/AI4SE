from __future__ import annotations

import ast
import json
import threading
import time
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import TracebackType
from typing import Any


def _literal_assignment(path: Path, name: str) -> Any:
    module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for statement in module.body:
        if not isinstance(statement, ast.Assign):
            continue
        if any(
            isinstance(target, ast.Name) and target.id == name
            for target in statement.targets
        ):
            return ast.literal_eval(statement.value)
    raise ValueError(f"assignment {name!r} not found in {path}")


def _clarify_response(root: Path) -> dict[str, Any]:
    fixture_path = (
        root / "tools/new-agents/backend/tests/test_artifact_data_renderers.py"
    )
    artifact_data = deepcopy(
        _literal_assignment(fixture_path, "VALID_CLARIFY_ARTIFACT_DATA")
    )
    return {
        "chat": (
            "我已经完成登录需求的事实、边界和风险分析，并把可追溯的详细内容"
            "更新到右侧产出物。当前阶段材料已完整，请确认后继续进入策略制定。"
        ),
        "artifact_data": artifact_data,
        "stage_action": {
            "type": "request_next_stage",
            "target_stage_id": "STRATEGY",
        },
        "warnings": [],
    }


def _strategy_response(root: Path) -> dict[str, Any]:
    fixture_path = (
        root / "tools/new-agents/backend/tests/test_artifact_data_renderers.py"
    )
    artifact_data = deepcopy(
        _literal_assignment(fixture_path, "VALID_STRATEGY_ARTIFACT_DATA")
    )
    return {
        "chat": (
            "我已经基于上一阶段的需求边界完成风险分层、测试层级和执行策略，"
            "右侧策略蓝图正在按章节形成。请确认后继续进入用例编写。"
        ),
        "artifact_data": artifact_data,
        "stage_action": {
            "type": "request_next_stage",
            "target_stage_id": "CASES",
        },
        "warnings": [],
    }


class FakeOpenAIProvider:
    def __init__(self, response_payloads: list[dict[str, Any]]):
        self._response_texts = [
            json.dumps(
                response_payload,
                ensure_ascii=False,
                separators=(",", ":"),
            )
            for response_payload in response_payloads
        ]
        self._response_index = 0
        self._response_lock = threading.Lock()
        provider = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def do_POST(self) -> None:
                if not self.path.endswith("/chat/completions"):
                    self.send_error(404)
                    return
                content_length = int(self.headers.get("Content-Length", "0"))
                if content_length:
                    self.rfile.read(content_length)
                with provider._response_lock:
                    if provider._response_index >= len(provider._response_texts):
                        self.send_error(500, "deterministic response queue exhausted")
                        return
                    response_text = provider._response_texts[provider._response_index]
                    provider._response_index += 1
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "close")
                self.end_headers()
                for offset in range(0, len(response_text), 24):
                    content = response_text[offset : offset + 24]
                    chunk = {
                        "id": "fake-qg020",
                        "object": "chat.completion.chunk",
                        "created": 1,
                        "model": "deepseek-v4-flash",
                        "choices": [
                            {
                                "index": 0,
                                "delta": {"content": content},
                                "finish_reason": None,
                            }
                        ],
                    }
                    body = (
                        "data: " + json.dumps(chunk, ensure_ascii=False) + "\n\n"
                    ).encode("utf-8")
                    self.wfile.write(body)
                    self.wfile.flush()
                    time.sleep(0.002)

                terminal = {
                    "id": "fake-qg020",
                    "object": "chat.completion.chunk",
                    "created": 1,
                    "model": "deepseek-v4-flash",
                    "choices": [
                        {
                            "index": 0,
                            "delta": {},
                            "finish_reason": "stop",
                        }
                    ],
                }
                self.wfile.write(
                    (
                        "data: " + json.dumps(terminal, ensure_ascii=False) + "\n\n"
                    ).encode("utf-8")
                )
                self.wfile.flush()

                usage = {
                    "id": "fake-qg020",
                    "object": "chat.completion.chunk",
                    "created": 1,
                    "model": "deepseek-v4-flash",
                    "choices": [],
                    "usage": {
                        "prompt_tokens": 100,
                        "completion_tokens": 200,
                        "total_tokens": 300,
                    },
                }
                self.wfile.write(
                    (
                        "data: "
                        + json.dumps(usage, ensure_ascii=False)
                        + "\n\ndata: [DONE]\n\n"
                    ).encode("utf-8")
                )
                self.wfile.flush()

            def log_message(self, format: str, *args: object) -> None:
                return

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            name="qg020-fake-provider",
            daemon=True,
        )

    @classmethod
    def for_clarify(cls, root: Path) -> "FakeOpenAIProvider":
        return cls([_clarify_response(root)])

    @classmethod
    def for_test_design_prefix(cls, root: Path) -> "FakeOpenAIProvider":
        return cls([_clarify_response(root), _strategy_response(root)])

    @property
    def base_url(self) -> str:
        host, port = self._server.server_address
        return f"http://{host}:{port}/v1"

    def __enter__(self) -> "FakeOpenAIProvider":
        self._thread.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=5)
