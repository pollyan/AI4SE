from __future__ import annotations

import importlib
import json
import os
import traceback

import pytest
from playwright.sync_api import sync_playwright

from .config import (
    RealLlmConfig,
    build_secret_free_browser_environment,
    secret_free_sync_playwright,
)
from .assertions import text_digest
from .stream_observer import (
    STREAM_OBSERVER_SCRIPT,
    finish_dom_observer,
    start_dom_observer,
)

pytestmark = pytest.mark.e2e


def _module(name: str):
    try:
        return importlib.import_module(f"tests.e2e.new_agents_real.{name}")
    except ModuleNotFoundError:
        pytest.fail(f"real-agent {name} module is missing")


def test_live_stack_startup_failure_suppresses_raw_exception_traceback(
    monkeypatch,
    tmp_path,
):
    live_stack = _module("live_stack")
    api_key_canary = "STARTUP-TRACEBACK-API-KEY-CANARY"
    ports = iter((19001, 19002))
    monkeypatch.setattr(live_stack, "_free_port", lambda: next(ports))
    stack = live_stack.LiveStack(
        tmp_path,
        RealLlmConfig(
            api_key_canary,
            "https://api.deepseek.example/v1",
            "deepseek-v4-flash",
        ),
    )

    def fail_start() -> None:
        raise RuntimeError(f"provider startup included {api_key_canary}")

    monkeypatch.setattr(stack, "_start", fail_start)
    monkeypatch.setattr(stack, "_cleanup_resources", lambda: [])

    with pytest.raises(live_stack.LiveStackStartupError) as captured:
        stack.__enter__()

    formatted = "".join(traceback.format_exception(captured.value))
    assert api_key_canary not in str(captured.value)
    assert api_key_canary not in formatted
    assert captured.value.__cause__ is None
    assert captured.value.__suppress_context__ is True


def test_live_stack_startup_log_redaction_covers_tail_boundary(
    monkeypatch,
    tmp_path,
):
    live_stack = _module("live_stack")
    api_key_canary = "sk-" + ("TAIL-BOUNDARY-CANARY-" * 4)
    omitted_prefix_length = 7
    log_tail_bytes = 4096
    retained_suffix_length = len(api_key_canary) - omitted_prefix_length
    trailing_text = "z" * (log_tail_bytes - retained_suffix_length)
    log_path = tmp_path / "backend.log"
    log_path.write_text(
        ("p" * 100) + api_key_canary + trailing_text,
        encoding="utf-8",
    )
    ports = iter((19001, 19002))
    monkeypatch.setattr(live_stack, "_free_port", lambda: next(ports))
    stack = live_stack.LiveStack(
        tmp_path,
        RealLlmConfig(
            api_key_canary,
            "https://api.deepseek.example/v1",
            "deepseek-v4-flash",
        ),
    )
    stack._backend_log_path = log_path
    stack._frontend_log_path = None
    stack._backend_log = None
    stack._frontend_log = None

    def fail_start() -> None:
        raise RuntimeError("safe startup failure")

    stack._start = fail_start
    stack._cleanup_resources = lambda: []

    with pytest.raises(live_stack.LiveStackStartupError) as captured:
        stack.__enter__()

    diagnostic = str(captured.value)
    formatted = "".join(traceback.format_exception(captured.value))
    leaked_suffix = api_key_canary[omitted_prefix_length:]
    assert leaked_suffix not in diagnostic
    assert leaked_suffix not in formatted
    assert api_key_canary not in diagnostic
    assert api_key_canary not in formatted
    assert "<redacted>" in diagnostic
    assert len(diagnostic) < 5000


def test_dom_observer_keeps_first_final_attempt_update_after_retry():
    final_chat = "最终尝试只有这一个有意义的对话增量，必须被观察器记录。"
    failed_artifact = "# 失败草稿\n\n不完整内容"
    final_artifact = "# 最终产出\n\n最终尝试的唯一产出增量"
    with secret_free_sync_playwright(sync_playwright, os.environ) as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            env=build_secret_free_browser_environment(os.environ),
        )
        page = browser.new_page()
        page.set_content("""
            <main data-testid="chat-pane">
              <div data-testid="assistant-message-content"></div>
            </main>
            <article data-testid="artifact-content"></article>
            """)
        page.evaluate("""
            () => {
              window.__ai4seRealStreamTraces = [{
                attempt: 0,
                request: { requestId: 'request-retry' },
                events: [],
              }];
            }
            """)
        start_dom_observer(page, 0)
        page.evaluate("window.__ai4seRealDomObserver.disconnect()")
        page.evaluate(
            """
            ({
              finalChat,
              finalChatHash,
              failedArtifact,
              failedArtifactHash,
              finalArtifact,
              finalArtifactHash,
            }) => {
              const trace = window.__ai4seRealStreamTraces[0];
              const chat = document.querySelector(
                '[data-testid="assistant-message-content"]'
              );
              const artifact = document.querySelector(
                '[data-testid="artifact-content"]'
              );
              trace.events.push({
                type: 'agent_delta',
                attempt: 0,
                artifact: {
                  hash: failedArtifactHash,
                  length: failedArtifact.length,
                  metadata: null,
                },
              });
              artifact.innerHTML = '<h1>失败草稿</h1><p>不完整内容</p>';
              artifact.setAttribute('data-artifact-source-hash', failedArtifactHash);
              artifact.setAttribute('data-artifact-source-length', String(failedArtifact.length));
              window.__ai4seRealDomSample();

              trace.attempt = 1;
              trace.events.push(
                { type: 'agent_retry', attempt: 1 },
                {
                  type: 'agent_delta',
                  attempt: 1,
                  chat: { hash: finalChatHash, length: finalChat.length },
                },
                {
                  type: 'agent_delta',
                  attempt: 1,
                  artifact: {
                    hash: finalArtifactHash,
                    length: finalArtifact.length,
                    metadata: null,
                  },
                },
              );
              chat.textContent = finalChat;
              artifact.innerHTML = '<h1>最终产出</h1><p>最终尝试的唯一产出增量</p>';
              artifact.setAttribute('data-artifact-source-hash', finalArtifactHash);
              artifact.setAttribute('data-artifact-source-length', String(finalArtifact.length));
              window.__ai4seRealDomSample();
            }
            """,
            {
                "finalChat": final_chat,
                "finalChatHash": text_digest(final_chat),
                "failedArtifact": failed_artifact,
                "failedArtifactHash": text_digest(failed_artifact),
                "finalArtifact": final_artifact,
                "finalArtifactHash": text_digest(final_artifact),
            },
        )
        dom_trace = finish_dom_observer(page)
        browser.close()

    final_events = [event for event in dom_trace["events"] if event["attempt"] == 1]
    assert [event["kind"] for event in final_events] == ["chat", "artifact"]


def test_dom_observer_projects_metadata_index_from_rendered_heading_tree():
    source = """# 评审报告

## 1. 业务结论

业务正文与结构化可视化。

## 文档信息

文档元信息：阶段 REPORT
"""
    metadata_heading_hash = text_digest("# 评审报告\n## 文档信息")

    with secret_free_sync_playwright(sync_playwright, os.environ) as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            env=build_secret_free_browser_environment(os.environ),
        )
        page = browser.new_page()
        page.set_content("""
            <main data-testid="chat-pane">
              <div data-testid="assistant-message-content"></div>
            </main>
            <article data-testid="artifact-content"></article>
            """)
        page.evaluate("""
            () => {
              window.__ai4seRealStreamTraces = [{
                attempt: 0,
                request: { requestId: 'request-dom-metadata' },
                events: [],
              }];
            }
            """)
        start_dom_observer(page, 0)
        page.evaluate("window.__ai4seRealDomObserver.disconnect()")
        page.evaluate(
            """
            ({ source, sourceHash, metadataHeadingHash }) => {
              const trace = window.__ai4seRealStreamTraces[0];
              const artifact = document.querySelector(
                '[data-testid="artifact-content"]'
              );
              trace.events.push({
                type: 'agent_delta',
                attempt: 0,
                artifact: {
                  hash: sourceHash,
                  length: source.length,
                  metadata: {
                    headingHash: metadataHeadingHash,
                    headingLevel: 2,
                    index: 2,
                    isFinal: true,
                    compact: true,
                    hasTable: false,
                  },
                },
              });
              artifact.innerHTML = [
                '<h1>评审报告</h1>',
                '<h2>1. 业务结论</h2>',
                '<div class="structured-visual"><h3>可视化内部标题</h3></div>',
                '<p>业务正文与结构化可视化。</p>',
                '<h2>文档信息</h2>',
                '<p>文档元信息：阶段 REPORT</p>',
              ].join('');
              artifact.setAttribute('data-artifact-source-hash', sourceHash);
              artifact.setAttribute('data-artifact-source-length', String(source.length));
              window.__ai4seRealDomSample();
            }
            """,
            {
                "source": source,
                "sourceHash": text_digest(source),
                "metadataHeadingHash": metadata_heading_hash,
            },
        )
        dom_trace = finish_dom_observer(page)
        browser.close()

    artifact_event = next(
        event for event in dom_trace["events"] if event["kind"] == "artifact"
    )
    assert artifact_event["metadata"]["index"] == 3
    assert artifact_event["metadata"]["isFinal"] is True
    assert artifact_event["metadata"]["headingHash"] == metadata_heading_hash


def test_dom_observer_uses_source_summary_across_markdown_projection_changes():
    first_source = "这里是**测"
    final_source = "这里是**测试**"

    with secret_free_sync_playwright(sync_playwright, os.environ) as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            env=build_secret_free_browser_environment(os.environ),
        )
        page = browser.new_page()
        page.set_content("""
            <main data-testid="chat-pane">
              <div data-testid="assistant-message-content"></div>
            </main>
            <article data-testid="artifact-content"></article>
            """)
        page.evaluate("""
            () => {
              window.__ai4seRealStreamTraces = [{
                attempt: 0,
                request: { requestId: 'request-markdown-projection' },
                events: [],
              }];
            }
            """)
        start_dom_observer(page, 0)
        page.evaluate("window.__ai4seRealDomObserver.disconnect()")
        page.evaluate(
            """
            ({ firstSource, firstHash, finalSource, finalHash }) => {
              const trace = window.__ai4seRealStreamTraces[0];
              const chat = document.querySelector(
                '[data-testid="assistant-message-content"]'
              );
              trace.events.push({
                type: 'agent_delta',
                attempt: 0,
                chat: { hash: firstHash, length: firstSource.length },
              });
              chat.textContent = '这里是**测';
              chat.setAttribute('data-chat-source-hash', firstHash);
              chat.setAttribute('data-chat-source-length', String(firstSource.length));
              window.__ai4seRealDomSample();

              trace.events.push({
                type: 'agent_delta',
                attempt: 0,
                chat: { hash: finalHash, length: finalSource.length },
              });
              chat.textContent = '这里是测试';
              chat.setAttribute('data-chat-source-hash', finalHash);
              chat.setAttribute('data-chat-source-length', String(finalSource.length));
              window.__ai4seRealDomSample();
            }
            """,
            {
                "firstSource": first_source,
                "firstHash": text_digest(first_source),
                "finalSource": final_source,
                "finalHash": text_digest(final_source),
            },
        )
        dom_trace = finish_dom_observer(page)
        browser.close()

    chats = [event for event in dom_trace["events"] if event["kind"] == "chat"]
    assert [event["hash"] for event in chats] == [
        text_digest(first_source),
        text_digest(final_source),
    ]
    assert chats[-1]["monotonic"] is True


def test_dom_observer_does_not_advance_network_watermark_for_read_ahead_synthetic_prefix():
    synthetic_prefix = "正在整"
    first_network_chat = "正在整理需求清单，并核对关键业务边界。"
    final_network_chat = first_network_chat + "随后我会给出完整评审结论。"

    with secret_free_sync_playwright(sync_playwright, os.environ) as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            env=build_secret_free_browser_environment(os.environ),
        )
        page = browser.new_page()
        page.set_content("""
            <main data-testid="chat-pane">
              <div data-testid="assistant-message-content"></div>
            </main>
            <article data-testid="artifact-content"></article>
            """)
        page.evaluate(
            """
            ({ firstChat, firstHash, finalChat, finalHash }) => {
              const trace = {
                attempt: 0,
                request: { requestId: 'request-read-ahead-prefix' },
                events: [
                  {
                    type: 'agent_delta',
                    attempt: 0,
                    chat: { hash: firstHash, length: firstChat.length },
                  },
                  {
                    type: 'agent_delta',
                    attempt: 0,
                    chat: { hash: finalHash, length: finalChat.length },
                  },
                ],
              };
              Object.defineProperty(trace, 'transient', {
                value: { lastChat: finalChat, lastArtifact: '' },
                enumerable: false,
                configurable: true,
              });
              window.__ai4seRealStreamTraces = [trace];
            }
            """,
            {
                "firstChat": first_network_chat,
                "firstHash": text_digest(first_network_chat),
                "finalChat": final_network_chat,
                "finalHash": text_digest(final_network_chat),
            },
        )
        start_dom_observer(page, 0)
        page.evaluate("window.__ai4seRealDomObserver.disconnect()")
        for source in (
            synthetic_prefix,
            first_network_chat,
            final_network_chat,
        ):
            page.evaluate(
                """
                ({ source, digest }) => {
                  const chat = document.querySelector(
                    '[data-testid="assistant-message-content"]'
                  );
                  chat.textContent = source;
                  chat.setAttribute('data-chat-source-hash', digest);
                  chat.setAttribute('data-chat-source-length', String(source.length));
                  window.__ai4seRealDomSample();
                }
                """,
                {"source": source, "digest": text_digest(source)},
            )
        dom_trace = finish_dom_observer(page)
        browser.close()

    chats = [event for event in dom_trace["events"] if event["kind"] == "chat"]
    assert [event["networkIndex"] for event in chats] == [-1, 0, 1]
    assert all(event["monotonic"] is True for event in chats)


def test_dom_observer_rejects_source_rewind_even_when_final_source_recovers():
    first_source = "第一段自然对话已经稳定显示。"
    second_source = first_source + "\n\n第二段继续补充。"
    final_source = second_source + "\n\n最终说明。"

    with secret_free_sync_playwright(sync_playwright, os.environ) as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            env=build_secret_free_browser_environment(os.environ),
        )
        page = browser.new_page()
        page.set_content("""
            <main data-testid="chat-pane">
              <div data-testid="assistant-message-content"></div>
            </main>
            <article data-testid="artifact-content"></article>
            """)
        page.evaluate("""
            () => {
              window.__ai4seRealStreamTraces = [{
                attempt: 0,
                request: { requestId: 'request-source-rewind' },
                events: [],
              }];
            }
            """)
        start_dom_observer(page, 0)
        page.evaluate("window.__ai4seRealDomObserver.disconnect()")
        for source in (first_source, second_source):
            page.evaluate(
                """
                ({ source, digest }) => {
                  const trace = window.__ai4seRealStreamTraces[0];
                  const chat = document.querySelector(
                    '[data-testid="assistant-message-content"]'
                  );
                  trace.events.push({
                    type: 'agent_delta',
                    attempt: 0,
                    chat: { hash: digest, length: source.length },
                  });
                  chat.textContent = source;
                  chat.setAttribute('data-chat-source-hash', digest);
                  chat.setAttribute('data-chat-source-length', String(source.length));
                  window.__ai4seRealDomSample();
                }
                """,
                {"source": source, "digest": text_digest(source)},
            )
        page.evaluate(
            """
            ({ source, digest }) => {
              const chat = document.querySelector(
                '[data-testid="assistant-message-content"]'
              );
              chat.textContent = source;
              chat.setAttribute('data-chat-source-hash', digest);
              chat.setAttribute('data-chat-source-length', String(source.length));
              window.__ai4seRealDomSample();
            }
            """,
            {"source": first_source, "digest": text_digest(first_source)},
        )
        page.evaluate(
            """
            ({ source, digest }) => {
              const trace = window.__ai4seRealStreamTraces[0];
              const chat = document.querySelector(
                '[data-testid="assistant-message-content"]'
              );
              trace.events.push({
                type: 'agent_turn',
                attempt: 0,
                chat: { hash: digest, length: source.length },
              });
              chat.textContent = source;
              chat.setAttribute('data-chat-source-hash', digest);
              chat.setAttribute('data-chat-source-length', String(source.length));
              window.__ai4seRealDomSample();
            }
            """,
            {"source": final_source, "digest": text_digest(final_source)},
        )
        dom_trace = finish_dom_observer(page)
        browser.close()

    chats = [event for event in dom_trace["events"] if event["kind"] == "chat"]
    assert any(event["monotonic"] is False for event in chats)


def test_dom_observer_rejects_synthetic_chat_rewind_with_single_network_chat():
    first_source = "第一段自然对话已经稳定显示。"
    second_source = first_source + "\n\n第二段继续补充。"
    final_source = second_source + "\n\n最终说明。"

    with secret_free_sync_playwright(sync_playwright, os.environ) as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            env=build_secret_free_browser_environment(os.environ),
        )
        page = browser.new_page()
        page.set_content("""
            <main data-testid="chat-pane">
              <div data-testid="assistant-message-content"></div>
            </main>
            <article data-testid="artifact-content"></article>
            """)
        page.evaluate(
            """
            ({ finalSource, finalHash }) => {
              const trace = {
                attempt: 0,
                request: { requestId: 'request-synthetic-source-rewind' },
                events: [{
                  type: 'agent_delta',
                  attempt: 0,
                  chat: { hash: finalHash, length: finalSource.length },
                }],
              };
              Object.defineProperty(trace, 'transient', {
                value: { lastChat: finalSource, lastArtifact: '' },
                enumerable: false,
                configurable: true,
              });
              window.__ai4seRealStreamTraces = [trace];
            }
            """,
            {"finalSource": final_source, "finalHash": text_digest(final_source)},
        )
        start_dom_observer(page, 0)
        page.evaluate("window.__ai4seRealDomObserver.disconnect()")
        for source in (first_source, second_source, first_source, final_source):
            page.evaluate(
                """
                ({ source, digest }) => {
                  const chat = document.querySelector(
                    '[data-testid="assistant-message-content"]'
                  );
                  chat.textContent = source;
                  chat.setAttribute('data-chat-source-hash', digest);
                  chat.setAttribute('data-chat-source-length', String(source.length));
                  window.__ai4seRealDomSample();
                }
                """,
                {"source": source, "digest": text_digest(source)},
            )
        dom_trace = finish_dom_observer(page)
        browser.close()

    chats = [event for event in dom_trace["events"] if event["kind"] == "chat"]
    assert [event["length"] for event in chats] == [
        len(first_source),
        len(second_source),
        len(first_source),
        len(final_source),
    ]
    assert chats[2]["monotonic"] is False
    assert chats[2]["monotonicReason"] == "source_length_rewind"


def test_stream_observer_projects_model_controlled_fields_to_safe_summaries():
    heading_canary = "SECRET_HEADING_CANARY"
    target_canary = "SECRET_TARGET_CANARY"
    run_canary = "AuthorizationBearerCanary"
    error_canary = "SECRET_CANARY_CODE"
    frames = [
        {
            "type": "run_started",
            "runId": run_canary,
        },
        {
            "type": "agent_turn",
            "output": {
                "chat": "已生成安全摘要。",
                "artifact_update": {
                    "type": "replace",
                    "markdown": f"# {heading_canary}\n\n正文",
                },
                "stage_action": {
                    "type": "request_next_stage",
                    "target_stage_id": target_canary,
                },
            },
        },
        {
            "type": "error",
            "code": error_canary,
            "message": "fixed public message",
        },
    ]
    stream_body = (
        "".join(
            f"data: {json.dumps(frame, ensure_ascii=False)}\n\n" for frame in frames
        )
        + "data: [DONE]\n\n"
    )

    with secret_free_sync_playwright(sync_playwright, os.environ) as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            env=build_secret_free_browser_environment(os.environ),
        )
        page = browser.new_page()
        page.set_content("<main></main>")
        page.evaluate(
            """
            (body) => {
              window.fetch = async () => new Response(body, {
                status: 200,
                headers: { 'Content-Type': 'text/event-stream' },
              });
            }
            """,
            stream_body,
        )
        page.evaluate(STREAM_OBSERVER_SCRIPT)
        page.evaluate("""
            () => window.fetch('/api/agent/runs/stream', {
              method: 'POST',
              body: JSON.stringify({
                workflowId: 'TEST_DESIGN',
                stageId: 'CLARIFY',
                requestId: 'request-safe-projection',
              }),
            })
        """)
        page.wait_for_function(
            "() => window.__ai4seRealStreamTraces?.[0]?.done === true"
        )
        trace = page.evaluate("window.__ai4seRealStreamTraces[0]")
        browser.close()

    serialized = json.dumps(trace, ensure_ascii=False)
    for canary in (heading_canary, target_canary, run_canary, error_canary):
        assert canary not in serialized
    turn = next(event for event in trace["events"] if event["type"] == "agent_turn")
    assert turn["requestsNextStage"] is True
    assert turn["artifact"]["headings"][0]["hash"].startswith("sha256-")
    error = next(event for event in trace["events"] if event["type"] == "error")
    assert error["code"] == "LLM_ERROR"


def test_stream_observer_preserves_supported_runtime_errors_only():
    supported_codes = [
        "VISUAL_VALIDATION_FAILED",
        "PERSISTENCE_FAILED",
        "PERSISTENCE_CONFLICT",
        "REQUEST_IN_PROGRESS",
        "REQUEST_IDENTITY_CONFLICT",
        "AGENT_RUNTIME_UNAVAILABLE",
        "REQUEST_VALIDATION_FAILED",
    ]
    frames = [
        {"type": "error", "code": code}
        for code in [*supported_codes, "RUNTIME_DEPENDENCY_MISSING"]
    ]
    stream_body = (
        "".join(f"data: {json.dumps(frame)}\n\n" for frame in frames)
        + "data: [DONE]\n\n"
    )

    with secret_free_sync_playwright(sync_playwright, os.environ) as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            env=build_secret_free_browser_environment(os.environ),
        )
        page = browser.new_page()
        page.set_content("<main></main>")
        page.evaluate(
            """
            (body) => {
              window.fetch = async () => new Response(body, {
                status: 200,
                headers: { 'Content-Type': 'text/event-stream' },
              });
            }
            """,
            stream_body,
        )
        page.evaluate(STREAM_OBSERVER_SCRIPT)
        page.evaluate("""
            () => window.fetch('/api/agent/runs/stream', {
              method: 'POST',
              body: JSON.stringify({ requestId: 'request-error-allowlist' }),
            })
            """)
        page.wait_for_function(
            "() => window.__ai4seRealStreamTraces?.[0]?.done === true"
        )
        trace = page.evaluate("window.__ai4seRealStreamTraces[0]")
        browser.close()

    observed_codes = [
        event["code"] for event in trace["events"] if event["type"] == "error"
    ]
    assert observed_codes[:-1] == supported_codes
    assert observed_codes[-1] == "LLM_ERROR"


def test_stream_observer_does_not_retain_provider_retry_reason():
    secret = "sk-qg020-retry-canary"
    retry_frame = json.dumps(
        {
            "type": "agent_retry",
            "reason": f"Authorization: Bearer {secret}",
        }
    )
    stream_body = f"data: {retry_frame}\n\ndata: [DONE]\n\n"

    with secret_free_sync_playwright(sync_playwright, os.environ) as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            env=build_secret_free_browser_environment(os.environ),
        )
        page = browser.new_page()
        page.set_content("<main></main>")
        page.evaluate(
            """
            (body) => {
              window.fetch = async () => new Response(body, {
                status: 200,
                headers: { 'Content-Type': 'text/event-stream' },
              });
            }
            """,
            stream_body,
        )
        page.evaluate(STREAM_OBSERVER_SCRIPT)
        page.evaluate("""
            () => window.fetch('/api/agent/runs/stream', {
              method: 'POST',
              body: JSON.stringify({
                workflowId: 'TEST_DESIGN',
                stageId: 'CLARIFY',
                requestId: 'request-retry-redaction',
              }),
            })
            """)
        page.wait_for_function(
            "() => window.__ai4seRealStreamTraces?.[0]?.done === true"
        )
        trace = page.evaluate("window.__ai4seRealStreamTraces[0]")
        browser.close()

    serialized = json.dumps(trace)
    assert secret not in serialized
    retry = next(event for event in trace["events"] if event["type"] == "agent_retry")
    assert retry["reason"] == "contract_retry"


def test_stream_observer_projects_only_safe_error_diagnostic_coordinates():
    secret = "sk-qg020-error-canary"
    error_frame = json.dumps(
        {
            "type": "error",
            "code": "SCHEMA_VALIDATION_FAILED",
            "message": f"provider output included {secret}",
            "diagnostic": {
                "phase": "structured_output",
                "workflowId": "TEST_DESIGN",
                "stageId": "CASES",
                "fieldPath": "artifact_data.test_cases.0.expected_results",
                "validator": "list_type",
                "retryable": False,
                "publicReason": f"do not persist {secret}",
                "providerPayload": secret,
            },
        }
    )
    stream_body = f"data: {error_frame}\n\ndata: [DONE]\n\n"

    with secret_free_sync_playwright(sync_playwright, os.environ) as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            env=build_secret_free_browser_environment(os.environ),
        )
        page = browser.new_page()
        page.set_content("<main></main>")
        page.evaluate(
            """
            (body) => {
              window.fetch = async () => new Response(body, {
                status: 200,
                headers: { 'Content-Type': 'text/event-stream' },
              });
            }
            """,
            stream_body,
        )
        page.evaluate(STREAM_OBSERVER_SCRIPT)
        page.evaluate("""
            () => window.fetch('/api/agent/runs/stream', {
              method: 'POST',
              body: JSON.stringify({
                workflowId: 'TEST_DESIGN',
                stageId: 'CASES',
                requestId: 'request-error-diagnostic',
              }),
            })
            """)
        page.wait_for_function(
            "() => window.__ai4seRealStreamTraces?.[0]?.done === true"
        )
        trace = page.evaluate("window.__ai4seRealStreamTraces[0]")
        browser.close()

    serialized = json.dumps(trace)
    assert secret not in serialized
    error = next(event for event in trace["events"] if event["type"] == "error")
    assert error["diagnostic"] == {
        "phase": "structured_output",
        "fieldPath": "artifact_data.test_cases.0.expected_results",
        "validator": "list_type",
        "retryable": False,
    }


def test_stream_observer_allows_canonical_section_insertion_before_footer():
    before = """# 测试用例

## 2. 已先完成的章节

稳定内容

## 文档信息

文档元信息：阶段 CASES
"""
    after = """# 测试用例

## 1. 后闭合但规范顺序更早的章节

新增内容

## 2. 已先完成的章节

稳定内容

## 文档信息

文档元信息：阶段 CASES
"""
    frames = [
        {
            "type": "agent_delta",
            "output": {"artifact_update": {"type": "replace", "markdown": before}},
        },
        {
            "type": "agent_delta",
            "output": {"artifact_update": {"type": "replace", "markdown": after}},
        },
    ]
    stream_body = (
        "".join(f"data: {json.dumps(frame)}\n\n" for frame in frames)
        + "data: [DONE]\n\n"
    )

    with secret_free_sync_playwright(sync_playwright, os.environ) as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            env=build_secret_free_browser_environment(os.environ),
        )
        page = browser.new_page()
        page.set_content("<main></main>")
        page.evaluate(
            """
            (body) => {
              window.fetch = async () => new Response(body, {
                status: 200,
                headers: { 'Content-Type': 'text/event-stream' },
              });
            }
            """,
            stream_body,
        )
        page.evaluate(STREAM_OBSERVER_SCRIPT)
        page.evaluate("""
            () => window.fetch('/api/agent/runs/stream', {
              method: 'POST',
              body: JSON.stringify({
                workflowId: 'TEST_DESIGN',
                stageId: 'CASES',
                requestId: 'request-section-insertion',
              }),
            })
            """)
        page.wait_for_function(
            "() => window.__ai4seRealStreamTraces?.[0]?.done === true"
        )
        trace = page.evaluate("window.__ai4seRealStreamTraces[0]")
        browser.close()

    artifacts = [event["artifact"] for event in trace["events"] if "artifact" in event]
    assert len(artifacts) == 2
    assert artifacts[1]["monotonic"] is True
    assert artifacts[1]["monotonicReason"] == "ok"


def test_stream_observer_allows_repeated_nested_headings_under_distinct_parents():
    before = """# 用户画像分析

## 主要用户画像

### 画像 1

#### 基础特征

第一类用户的稳定内容
"""
    after = before + """

### 画像 2

#### 基础特征

第二类用户的新增内容
"""
    frames = [
        {
            "type": "agent_delta",
            "output": {"artifact_update": {"type": "replace", "markdown": before}},
        },
        {
            "type": "agent_delta",
            "output": {"artifact_update": {"type": "replace", "markdown": after}},
        },
    ]
    stream_body = (
        "".join(f"data: {json.dumps(frame)}\n\n" for frame in frames)
        + "data: [DONE]\n\n"
    )

    with secret_free_sync_playwright(sync_playwright, os.environ) as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            env=build_secret_free_browser_environment(os.environ),
        )
        page = browser.new_page()
        page.set_content("<main></main>")
        page.evaluate(
            """
            (body) => {
              window.fetch = async () => new Response(body, {
                status: 200,
                headers: { 'Content-Type': 'text/event-stream' },
              });
            }
            """,
            stream_body,
        )
        page.evaluate(STREAM_OBSERVER_SCRIPT)
        page.evaluate("""
            () => window.fetch('/api/agent/runs/stream', {
              method: 'POST',
              body: JSON.stringify({
                workflowId: 'VALUE_DISCOVERY',
                stageId: 'PERSONA',
                requestId: 'request-nested-heading',
              }),
            })
            """)
        page.wait_for_function(
            "() => window.__ai4seRealStreamTraces?.[0]?.done === true"
        )
        trace = page.evaluate("window.__ai4seRealStreamTraces[0]")
        browser.close()

    artifacts = [event["artifact"] for event in trace["events"] if "artifact" in event]
    assert len(artifacts) == 2
    assert artifacts[1]["monotonic"] is True
    assert artifacts[1]["monotonicReason"] == "ok"


def test_stream_observer_rejects_active_tail_rewrite():
    before = """# 测试用例

## 1. 活动章节

原始稳定内容
"""
    after = """# 测试用例

## 1. 活动章节

完全改写但更长的内容不应被接受
"""
    frames = [
        {
            "type": "agent_delta",
            "output": {"artifact_update": {"type": "replace", "markdown": before}},
        },
        {
            "type": "agent_delta",
            "output": {"artifact_update": {"type": "replace", "markdown": after}},
        },
    ]
    stream_body = (
        "".join(f"data: {json.dumps(frame)}\n\n" for frame in frames)
        + "data: [DONE]\n\n"
    )

    with secret_free_sync_playwright(sync_playwright, os.environ) as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            env=build_secret_free_browser_environment(os.environ),
        )
        page = browser.new_page()
        page.set_content("<main></main>")
        page.evaluate(
            """
            (body) => {
              window.fetch = async () => new Response(body, {
                status: 200,
                headers: { 'Content-Type': 'text/event-stream' },
              });
            }
            """,
            stream_body,
        )
        page.evaluate(STREAM_OBSERVER_SCRIPT)
        page.evaluate("""
            () => window.fetch('/api/agent/runs/stream', {
              method: 'POST',
              body: JSON.stringify({
                workflowId: 'TEST_DESIGN',
                stageId: 'CASES',
                requestId: 'request-tail-rewrite',
              }),
            })
            """)
        page.wait_for_function(
            "() => window.__ai4seRealStreamTraces?.[0]?.done === true"
        )
        trace = page.evaluate("window.__ai4seRealStreamTraces[0]")
        browser.close()

    artifacts = [event["artifact"] for event in trace["events"] if "artifact" in event]
    assert artifacts[1]["monotonic"] is False
    assert artifacts[1]["monotonicReason"] == "active_tail_rewrite"


def test_stream_observer_does_not_retain_malformed_sse_parse_error():
    secret = "sk-qg020-malformed-sse-canary"
    stream_body = f"data: {{{secret}}}\n\ndata: [DONE]\n\n"

    with secret_free_sync_playwright(sync_playwright, os.environ) as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            env=build_secret_free_browser_environment(os.environ),
        )
        page = browser.new_page()
        page.set_content("<main></main>")
        page.evaluate(
            """
            (body) => {
              window.fetch = async () => new Response(body, {
                status: 200,
                headers: { 'Content-Type': 'text/event-stream' },
              });
            }
            """,
            stream_body,
        )
        page.evaluate(STREAM_OBSERVER_SCRIPT)
        page.evaluate("""
            () => window.fetch('/api/agent/runs/stream', {
              method: 'POST',
              body: JSON.stringify({
                workflowId: 'TEST_DESIGN',
                stageId: 'CASES',
                requestId: 'request-malformed-sse',
              }),
            })
            """)
        page.wait_for_function(
            "() => window.__ai4seRealStreamTraces?.[0]?.done === true"
        )
        trace = page.evaluate("window.__ai4seRealStreamTraces[0]")
        browser.close()

    serialized = json.dumps(trace)
    assert secret not in serialized
    assert trace["observerError"] == "sse_observer_failed"
