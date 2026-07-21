from __future__ import annotations

import os
from dataclasses import dataclass, replace
from typing import Any, Callable
from urllib.parse import urlencode, urljoin

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import expect

from .assertions import (
    FunctionalAssertionError,
    assert_observability,
    assert_restored_assistant_messages,
    assert_restored_artifact,
    assert_snapshot,
    assert_stage_trace,
    assert_workflow_run_ids,
    text_digest,
)
from .live_stack import LiveStack
from .matrix import FunctionalCase
from .stream_observer import (
    finish_dom_observer,
    start_dom_observer,
    wait_for_stream_trace,
)


@dataclass(frozen=True)
class StageEvidence:
    level: int
    workflow_id: str
    stage_id: str
    run_id: str
    request_id: str
    stream_order: tuple[str, ...]
    artifact_delta_count: int
    artifact_hash: str
    retry_count: int
    snapshot_artifact_versions: int
    snapshot_message_count: int
    snapshot_artifact_stage_ids: tuple[str, ...]
    snapshot_context_summary_count: int
    metric_status: str
    restored_from_server: bool
    event_types: tuple[str, ...]


@dataclass(frozen=True)
class WorkflowEvidence:
    level: int
    workflow_id: str
    run_id: str
    stages: tuple[StageEvidence, ...]
    transition_count: int
    restored_from_server: bool


def _browser_step(assertion_step: str, action: Callable[[], Any]) -> Any:
    """Keep browser failure evidence actionable without writing DOM or model text."""
    try:
        return action()
    except (AssertionError, PlaywrightError) as error:
        raise FunctionalAssertionError(
            "BROWSER_ASSERTION_FAILED",
            "browser functional assertion failed",
            details={"assertionStep": assertion_step},
        ) from error


def _manifest_workflow(stack: LiveStack, workflow_id: str) -> dict[str, Any]:
    import json

    manifest = json.loads(
        (stack.root / "tools/new-agents/workflow_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    return manifest["workflows"][workflow_id]


def _stream_order(dom_trace: dict[str, Any]) -> tuple[str, ...]:
    order: list[str] = []
    events = dom_trace.get("events", [])
    final_attempt = max(
        (
            event.get("attempt", 0)
            for event in events
            if isinstance(event.get("attempt", 0), int)
        ),
        default=0,
    )
    for event in events:
        if event.get("attempt", 0) != final_attempt:
            continue
        kind = event.get("kind")
        if kind not in {"chat", "artifact"} or kind in order:
            continue
        if kind == "chat" and event.get("length", 0) < 12:
            continue
        order.append(kind)
    return tuple(order)


def _open_clean_workspace(stack: LiveStack, case: FunctionalCase) -> None:
    if stack.page is None:
        raise ValueError("live stack is not started")
    page = stack.page
    page.goto(stack.frontend_url, wait_until="domcontentloaded", timeout=60_000)
    page.evaluate("localStorage.clear()")
    page.goto(
        urljoin(
            stack.frontend_url,
            f"workspace/{case.agent_id}/{case.slug}",
        ),
        wait_until="domcontentloaded",
        timeout=60_000,
    )
    page.locator("textarea").wait_for(timeout=30_000)
    page.get_by_test_id("artifact-content").wait_for(timeout=30_000)


def _next_stage_id(workflow: dict[str, Any], stage_index: int) -> str | None:
    next_index = stage_index + 1
    if next_index >= len(workflow["stages"]):
        return None
    return str(workflow["stages"][next_index]["id"])


def stage_probe_prompt(
    prompt: str,
    *,
    expected_next_stage_id: str | None,
) -> str:
    directives = [
        "【真实模型阶段探针】请直接完整完成当前阶段；对于输入中未明确的非阻断细节，"
        "允许采用合理假设，但必须明确标注。"
    ]
    if expected_next_stage_id is not None:
        directives.append(
            "当前阶段不是末阶段；完成后必须请求进入紧邻的下一阶段，不得跳过阶段；"
            f'stage_action.target_stage_id 必须填写内部 ID "{expected_next_stage_id}"。'
        )
    else:
        directives.append("当前阶段是末阶段；完成后不得请求进入下一阶段。")
    return f"{prompt}\n\n{' '.join(directives)}"


def workflow_journey_prompt(
    prompt: str,
    *,
    expected_next_stage_id: str | None,
) -> str:
    directives = [
        "【真实模型工作流旅程】请直接完整完成当前阶段；对于输入中未明确的非阻断细节，"
        "允许采用合理假设，但必须明确标注。"
    ]
    if expected_next_stage_id is not None:
        directives.append(
            "阶段推进必须遵循当前阶段的系统契约；后续阶段不得沿用本轮的阶段身份或跳转目标。"
        )
    else:
        directives.append("当前阶段是末阶段；完成后不得请求进入下一阶段。")
    return f"{prompt}\n\n{' '.join(directives)}"


def _snapshot(stack: LiveStack, run_id: str) -> dict[str, Any]:
    assert stack.page is not None
    response = _browser_step(
        "run_snapshot_fetch",
        lambda: stack.page.request.get(
            urljoin(stack.frontend_url, f"api/agent/runs/{run_id}")
        ),
    )
    if not response.ok:
        raise FunctionalAssertionError(
            "RUN_SNAPSHOT_MISSING",
            f"run snapshot request failed with {response.status}",
            details={"runId": run_id},
        )
    return response.json()


def _observability(
    stack: LiveStack,
    workflow_id: str,
    stage_id: str,
) -> dict[str, Any]:
    assert stack.page is not None
    query = urlencode({"workflowId": workflow_id, "stageId": stage_id, "limit": "20"})
    response = stack.page.request.get(
        urljoin(stack.frontend_url, f"api/agent/observability?{query}")
    )
    if not response.ok:
        raise FunctionalAssertionError(
            "RUN_SNAPSHOT_MISSING",
            f"observability request failed with {response.status}",
        )
    return response.json()


def _current_artifact(snapshot: dict[str, Any], stage_id: str) -> dict[str, Any]:
    return next(
        artifact
        for artifact in snapshot["artifacts"]
        if artifact.get("stageId") == stage_id
    )


def _restore_from_server(
    stack: LiveStack,
    case: FunctionalCase,
    evidence: StageEvidence,
    snapshot: dict[str, Any],
    *,
    expected_stage_ids: tuple[str, ...],
    expected_turn_count: int,
) -> None:
    assert stack.page is not None
    page = stack.page
    workspace_url = urljoin(
        stack.frontend_url,
        f"workspace/{case.agent_id}/{case.slug}",
    )
    current_artifact = _current_artifact(snapshot, evidence.stage_id)
    markdown = str(current_artifact["content"])
    page.evaluate("localStorage.clear()")
    page.goto(
        f"{workspace_url}?runId={evidence.run_id}",
        wait_until="domcontentloaded",
        timeout=60_000,
    )
    artifact_content = page.get_by_test_id("artifact-content")
    _browser_step(
        "restore_assistant_messages",
        lambda: expect(page.get_by_test_id("assistant-message")).to_have_count(
            expected_turn_count,
            timeout=30_000,
        ),
    )
    expected_artifact_hash = text_digest(markdown)
    _browser_step(
        "restore_artifact_hash",
        lambda: expect(artifact_content).to_have_attribute(
            "data-artifact-source-hash",
            expected_artifact_hash,
            timeout=30_000,
        ),
    )
    _browser_step(
        "restore_artifact_length",
        lambda: expect(artifact_content).to_have_attribute(
            "data-artifact-source-length",
            str(len(markdown)),
            timeout=30_000,
        ),
    )
    restored_dom_summary = artifact_content.evaluate("""
        node => ({
          hash: node.getAttribute('data-artifact-source-hash'),
          length: Number(node.getAttribute('data-artifact-source-length')),
        })
        """)
    assert_restored_artifact(
        restored_dom_summary,
        snapshot_content=markdown,
        run_id=evidence.run_id,
    )
    restored_assistant_summaries = page.get_by_test_id(
        "assistant-message-content"
    ).evaluate_all(
        """
        nodes => nodes.map(node => ({
          hash: node.getAttribute('data-chat-source-hash'),
          length: Number(node.getAttribute('data-chat-source-length')),
        }))
        """
    )
    assert_restored_assistant_messages(
        restored_assistant_summaries,
        snapshot_messages=snapshot["messages"],
        run_id=evidence.run_id,
    )
    restored = _snapshot(stack, evidence.run_id)
    assert_snapshot(
        restored,
        run_id=evidence.run_id,
        workflow_id=case.workflow_id,
        current_stage_id=evidence.stage_id,
        expected_stage_ids=expected_stage_ids,
        expected_turn_count=expected_turn_count,
        final_artifact_hash=evidence.artifact_hash,
    )


def restart_and_restore(
    stack: LiveStack,
    case: FunctionalCase,
    evidence: StageEvidence,
    snapshot: dict[str, Any],
    expected_stage_ids: tuple[str, ...],
    expected_turn_count: int,
) -> None:
    restart = getattr(stack, "restart_backend", None)
    if not callable(restart):
        raise ValueError("restart verification requires a deployment-controlled stack")
    restart()
    _restore_from_server(
        stack,
        case,
        evidence,
        snapshot,
        expected_stage_ids=expected_stage_ids,
        expected_turn_count=expected_turn_count,
    )


def should_verify_restart(stack: LiveStack) -> bool:
    return os.environ.get(
        "NEW_AGENTS_REAL_VERIFY_RESTART", ""
    ).strip() == "1" and callable(getattr(stack, "restart_backend", None))


def _stage_evidence_from_current_turn(
    stack: LiveStack,
    case: FunctionalCase,
    *,
    stream_index: int,
    expected_next_stage_id: str | None,
    evidence_level: int,
    expected_stage_ids: tuple[str, ...],
    expected_turn_count: int,
) -> tuple[StageEvidence, dict[str, Any]]:
    assert stack.page is not None and case.stage_id is not None
    page = stack.page
    trace = _browser_step(
        "stream_terminal_wait",
        lambda: wait_for_stream_trace(page, stream_index, timeout_ms=180_000),
    )
    terminal_artifact = next(
        (
            event.get("artifact")
            for event in reversed(trace.get("events", []))
            if event.get("type") == "agent_turn"
            and isinstance(event.get("artifact"), dict)
        ),
        None,
    )
    if terminal_artifact is not None:
        artifact_content = page.get_by_test_id("artifact-content")
        _browser_step(
            "terminal_artifact_dom_sync",
            lambda: (
                expect(artifact_content).to_have_attribute(
                    "data-artifact-source-hash",
                    str(terminal_artifact.get("hash")),
                    timeout=30_000,
                ),
                expect(artifact_content).to_have_attribute(
                    "data-artifact-source-length",
                    str(terminal_artifact.get("length")),
                    timeout=30_000,
                ),
            ),
        )
    dom_trace = _browser_step(
        "dom_observer_finalize",
        lambda: finish_dom_observer(page),
    )
    trace_result = assert_stage_trace(
        trace,
        dom_trace,
        expected_next_stage_id=expected_next_stage_id,
    )
    snapshot = _snapshot(stack, trace_result.run_id)
    snapshot_result = assert_snapshot(
        snapshot,
        run_id=trace_result.run_id,
        workflow_id=case.workflow_id,
        current_stage_id=case.stage_id,
        expected_stage_ids=expected_stage_ids,
        expected_turn_count=expected_turn_count,
        final_artifact_hash=trace_result.artifact_hash,
    )
    metric_status = assert_observability(
        _observability(stack, case.workflow_id, case.stage_id),
        run_id=trace_result.run_id,
        workflow_id=case.workflow_id,
        stage_id=case.stage_id,
        expected_retry_count=trace_result.retry_count,
    )
    return (
        StageEvidence(
            level=evidence_level,
            workflow_id=case.workflow_id,
            stage_id=case.stage_id,
            run_id=trace_result.run_id,
            request_id=trace_result.request_id,
            stream_order=_stream_order(dom_trace),
            artifact_delta_count=trace_result.artifact_delta_count,
            artifact_hash=trace_result.artifact_hash,
            retry_count=trace_result.retry_count,
            snapshot_artifact_versions=snapshot_result.version_number,
            snapshot_message_count=snapshot_result.message_count,
            snapshot_artifact_stage_ids=snapshot_result.artifact_stage_ids,
            snapshot_context_summary_count=(snapshot_result.context_summary_count),
            metric_status=metric_status,
            restored_from_server=False,
            event_types=trace_result.event_types,
        ),
        snapshot,
    )


def run_stage_probe(
    stack: LiveStack,
    case: FunctionalCase,
    prompt: str,
    *,
    evidence_level: int = 4,
) -> StageEvidence:
    if stack.page is None or case.stage_id is None:
        raise ValueError("stage probe requires a started stack and a stage case")
    page = stack.page
    workflow = _manifest_workflow(stack, case.workflow_id)
    _open_clean_workspace(stack, case)
    target_stage = next(
        stage for stage in workflow["stages"] if stage["id"] == case.stage_id
    )
    if workflow["stages"][0]["id"] != case.stage_id:
        page.get_by_text(target_stage["name"], exact=True).click()
    start_dom_observer(page, 0)

    stage_index = next(
        index
        for index, stage in enumerate(workflow["stages"])
        if stage["id"] == case.stage_id
    )
    expected_next_stage_id = _next_stage_id(workflow, stage_index)
    page.locator("textarea").fill(
        stage_probe_prompt(
            prompt,
            expected_next_stage_id=expected_next_stage_id,
        )
    )
    page.locator("#send-button").click()
    expected_stage_ids = (case.stage_id,)
    evidence, snapshot = _stage_evidence_from_current_turn(
        stack,
        case,
        stream_index=0,
        expected_next_stage_id=expected_next_stage_id,
        evidence_level=evidence_level,
        expected_stage_ids=expected_stage_ids,
        expected_turn_count=1,
    )
    if should_verify_restart(stack):
        restart_and_restore(
            stack,
            case,
            evidence,
            snapshot,
            expected_stage_ids,
            1,
        )
    else:
        _restore_from_server(
            stack,
            case,
            evidence,
            snapshot,
            expected_stage_ids=expected_stage_ids,
            expected_turn_count=1,
        )
    return replace(evidence, restored_from_server=True)


def run_workflow_journey(
    stack: LiveStack,
    case: FunctionalCase,
    prompt: str,
    *,
    evidence_level: int = 4,
    max_stages: int | None = None,
) -> WorkflowEvidence:
    if stack.page is None or case.kind != "workflow":
        raise ValueError("workflow journey requires a started stack and workflow case")
    page = stack.page
    workflow = _manifest_workflow(stack, case.workflow_id)
    _open_clean_workspace(stack, case)
    stages = workflow["stages"]
    if max_stages is not None:
        if max_stages < 1 or max_stages > len(stages):
            raise ValueError("max_stages must select a non-empty workflow prefix")
        stages = stages[:max_stages]

    evidence_items: list[StageEvidence] = []
    snapshots: list[dict[str, Any]] = []
    run_ids: list[str] = []
    page_stream_index = 0
    for stage_index, stage in enumerate(stages):
        stage_case = FunctionalCase(
            kind="stage",
            workflow_id=case.workflow_id,
            stage_id=str(stage["id"]),
            agent_id=case.agent_id,
            slug=case.slug,
        )
        start_dom_observer(page, page_stream_index)
        if stage_index == 0:
            page.locator("textarea").fill(
                workflow_journey_prompt(
                    prompt,
                    expected_next_stage_id=_next_stage_id(workflow, stage_index),
                )
            )
            page.locator("#send-button").click()
        else:
            _browser_step(
                "next_stage_confirmation_click",
                lambda: page.get_by_role(
                    "button",
                    name=f"确认进入 {stage['name']}",
                ).click(),
            )
        expected_stage_ids = tuple(
            str(completed_stage["id"]) for completed_stage in stages[: stage_index + 1]
        )
        evidence, snapshot = _stage_evidence_from_current_turn(
            stack,
            stage_case,
            stream_index=page_stream_index,
            expected_next_stage_id=_next_stage_id(workflow, stage_index),
            evidence_level=evidence_level,
            expected_stage_ids=expected_stage_ids,
            expected_turn_count=stage_index + 1,
        )
        evidence_items.append(evidence)
        snapshots.append(snapshot)
        run_ids.append(evidence.run_id)
        if stage_index == 0 and should_verify_restart(stack):
            restart_and_restore(
                stack,
                stage_case,
                evidence,
                snapshot,
                expected_stage_ids,
                stage_index + 1,
            )
            page_stream_index = 0
        else:
            page_stream_index += 1
        next_stage_id = _next_stage_id(workflow, stage_index)
        if next_stage_id is not None:
            next_stage = workflow["stages"][stage_index + 1]
            _browser_step(
                "next_stage_confirmation_visible",
                lambda: expect(
                    page.get_by_role(
                        "button",
                        name=f"确认进入 {next_stage['name']}",
                    )
                ).to_be_visible(timeout=30_000),
            )

    run_id = assert_workflow_run_ids(tuple(run_ids))
    final_evidence = evidence_items[-1]
    final_stage_ids = tuple(str(stage["id"]) for stage in stages)
    _restore_from_server(
        stack,
        case,
        final_evidence,
        snapshots[-1],
        expected_stage_ids=final_stage_ids,
        expected_turn_count=len(stages),
    )
    evidence_items[-1] = replace(final_evidence, restored_from_server=True)
    return WorkflowEvidence(
        level=evidence_level,
        workflow_id=case.workflow_id,
        run_id=run_id,
        stages=tuple(evidence_items),
        transition_count=max(0, len(evidence_items) - 1),
        restored_from_server=True,
    )
