from __future__ import annotations

import importlib
import json
import os
import re
import traceback
from pathlib import Path

import pytest

from . import assertions
from . import matrix


def _text_summary(
    digest: str,
    length: int,
    headings: tuple[str | dict, ...] = (),
    *,
    monotonic: bool = True,
    monotonic_reason: str = "ok",
    metadata: dict | None = None,
) -> dict:
    heading_summaries = [
        (
            heading
            if isinstance(heading, dict)
            else {
                "hash": assertions.text_digest(heading),
                "level": len(heading) - len(heading.lstrip("#")),
                "metadata": bool(
                    re.fullmatch(
                        r"#{1,3}\s+(?:\d+\.\s+)?(?:文档|评审|报告)信息",
                        heading,
                    )
                ),
            }
        )
        for heading in headings
    ]
    sections = [
        {
            "headingHash": heading["hash"],
            "headingLevel": heading["level"],
            "metadata": heading["metadata"],
            "hash": f"section-{index}-{heading['hash']}",
            "length": 20 + index,
        }
        for index, heading in enumerate(heading_summaries)
    ]
    if metadata is not None and "heading" in metadata:
        raw_heading = metadata.pop("heading")
        metadata.update(
            {
                "headingHash": assertions.text_digest(raw_heading),
                "headingLevel": len(raw_heading) - len(raw_heading.lstrip("#")),
            }
        )
    return {
        "hash": digest,
        "length": length,
        "headings": heading_summaries,
        "sections": sections,
        "monotonic": monotonic,
        "monotonicReason": monotonic_reason,
        "metadata": metadata,
    }


def _valid_trace() -> tuple[dict, dict]:
    chat = _text_summary("chat-final", 32)
    artifact_one = _text_summary(
        "artifact-1",
        80,
        ("# 需求分析文档", "## 1. 被测系统与边界"),
    )
    artifact_two = _text_summary(
        "artifact-2",
        160,
        ("# 需求分析文档", "## 1. 被测系统与边界"),
    )
    artifact_final = _text_summary(
        "artifact-final",
        240,
        (
            "# 需求分析文档",
            "## 1. 被测系统与边界",
            "## 文档信息",
        ),
        metadata={
            "heading": "## 文档信息",
            "index": 2,
            "isFinal": True,
            "compact": True,
            "hasTable": False,
        },
    )
    trace = {
        "request": {
            "workflowId": "TEST_DESIGN",
            "stageId": "CLARIFY",
            "requestId": "request-1",
            "runId": None,
        },
        "events": [
            {"type": "run_started", "runId": "run-1", "attempt": 0},
            {"type": "agent_delta", "attempt": 0, "chat": chat},
            {"type": "agent_delta", "attempt": 0, "artifact": artifact_one},
            {"type": "agent_delta", "attempt": 0, "artifact": artifact_two},
            {
                "type": "agent_turn",
                "attempt": 0,
                "chat": chat,
                "artifact": artifact_final,
                "requestsNextStage": True,
                "targetStageId": "STRATEGY",
            },
            {"type": "done", "attempt": 0},
        ],
    }
    dom = {
        "requestId": "request-1",
        "events": [
            {"kind": "chat", "attempt": 0, **chat},
            {"kind": "artifact", "attempt": 0, **artifact_one},
            {"kind": "artifact", "attempt": 0, **artifact_two},
            {"kind": "artifact", "attempt": 0, **artifact_final},
        ],
    }
    return trace, dom


def _load_reporting():
    try:
        return importlib.import_module("tests.e2e.new_agents_real.reporting")
    except ModuleNotFoundError:
        pytest.fail("real-agent reporting module is missing")


def test_report_recursively_redacts_secret_values_and_sensitive_keys(tmp_path):
    reporting = _load_reporting()
    secret = "sk-qg020-canary"
    report_path = tmp_path / "report.json"

    reporting.write_report(
        report_path,
        {
            "status": "FAIL",
            "apiKey": secret,
            "nested": {
                "authorization": f"Bearer {secret}",
                "message": f"provider rejected {secret}",
            },
            "items": [{"password": secret}, secret],
        },
        secrets=(secret,),
    )

    raw = report_path.read_text(encoding="utf-8")
    payload = json.loads(raw)
    assert secret not in raw
    assert payload["apiKey"] == "<redacted>"
    assert payload["nested"]["authorization"] == "<redacted>"
    assert payload["nested"]["message"] == "provider rejected <redacted>"
    assert payload["items"] == [{"password": "<redacted>"}, "<redacted>"]


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        ("LLM_ERROR", "provider"),
        ("SCHEMA_VALIDATION_FAILED", "schema"),
        ("CONTRACT_VALIDATION_FAILED", "renderer"),
        ("VISUAL_VALIDATION_FAILED", "renderer"),
        ("REQUEST_VALIDATION_FAILED", "schema"),
        ("SSE_TRUNCATED", "transport"),
        ("DOM_NOT_MONOTONIC", "frontend"),
        ("RUN_SNAPSHOT_MISSING", "persistence"),
        ("PERSISTENCE_FAILED", "persistence"),
        ("PERSISTENCE_CONFLICT", "persistence"),
        ("REQUEST_IN_PROGRESS", "persistence"),
        ("REQUEST_IDENTITY_CONFLICT", "persistence"),
        ("INVALID_STAGE_TRANSITION", "transition"),
        ("AGENT_RUNTIME_UNAVAILABLE", "infrastructure"),
    ],
)
def test_error_codes_have_stable_functional_categories(code, expected):
    reporting = _load_reporting()

    assert reporting.classify_error(code) == expected


def test_report_path_stays_under_real_agent_results_directory(tmp_path):
    reporting = _load_reporting()
    target = reporting.report_path(tmp_path, "pr", "TEST_DESIGN")

    assert target.parent == tmp_path / "test-results" / "new-agents-real"
    assert target.name == "pr-TEST_DESIGN.json"


def test_real_scope_environment_collects_only_planned_cases():
    root = Path(__file__).resolve().parents[3]
    manifest = json.loads(
        (root / "tools/new-agents/workflow_manifest.json").read_text(encoding="utf-8")
    )

    assert hasattr(matrix, "selection_from_environment")
    stage_selection = matrix.selection_from_environment(
        manifest,
        {
            "NEW_AGENTS_REAL_SCOPE": "stage",
            "NEW_AGENTS_REAL_WORKFLOW": "TEST_DESIGN",
            "NEW_AGENTS_REAL_STAGE": "CLARIFY",
        },
    )
    pr_selection = matrix.selection_from_environment(
        manifest,
        {"NEW_AGENTS_REAL_SCOPE": "pr"},
    )

    assert stage_selection.scope is matrix.FunctionalScope.STAGE
    assert [case.test_id for case in stage_selection.cases] == [
        "stage-TEST_DESIGN-CLARIFY"
    ]
    assert len(pr_selection.cases) == 2


def test_pr_selection_is_derived_from_scenario_markers():
    root = Path(__file__).resolve().parents[3]
    manifest = json.loads(
        (root / "tools/new-agents/workflow_manifest.json").read_text(encoding="utf-8")
    )
    scenarios = json.loads(
        (root / "tests/e2e/new_agents_real/real_llm_scenarios.json").read_text(
            encoding="utf-8"
        )
    )
    scenarios["TEST_DESIGN"]["prCritical"] = False
    scenarios["REQ_REVIEW"]["prCritical"] = True

    selection = matrix.select_cases(
        matrix.FunctionalScope.PR,
        manifest,
        scenarios=scenarios,
    )

    assert [case.workflow_id for case in selection] == [
        "REQ_REVIEW",
        "VALUE_DISCOVERY",
    ]


def test_workflow_run_id_assertion_rejects_changes_between_stages():
    with pytest.raises(
        assertions.FunctionalAssertionError,
        match="runId",
    ):
        assertions.assert_workflow_run_ids(("run-1", "run-2"))

    assertions.assert_workflow_run_ids(("run-1", "run-1", "run-1"))


@pytest.mark.parametrize(
    "mutation",
    [
        "turn-before-delta",
        "duplicate-artifact",
        "artifact-content-regression",
        "artifact-heading-reorder",
        "dom-content-regression",
        "dom-section-content-replacement",
        "dom-heading-reorder",
    ],
)
def test_stage_trace_rejects_false_positive_stream_mutations(mutation):
    trace, dom = _valid_trace()
    if mutation == "turn-before-delta":
        turn = trace["events"].pop(4)
        trace["events"].insert(2, turn)
    elif mutation == "duplicate-artifact":
        trace["events"][3]["artifact"] = dict(trace["events"][2]["artifact"])
    elif mutation == "artifact-content-regression":
        trace["events"][3]["artifact"]["monotonic"] = False
    elif mutation == "artifact-heading-reorder":
        trace["events"][3]["artifact"]["headings"].reverse()
    elif mutation == "dom-content-regression":
        dom["events"][2]["monotonic"] = False
    elif mutation == "dom-section-content-replacement":
        dom["events"][2]["sections"][0]["hash"] = "section-replaced"
    else:
        dom["events"][2]["headings"].reverse()

    with pytest.raises(assertions.FunctionalAssertionError):
        assertions.assert_stage_trace(
            trace,
            dom,
            expected_next_stage_id="STRATEGY",
        )


@pytest.mark.parametrize(
    ("surface", "expected_code"),
    [
        ("network", "CONTRACT_VALIDATION_FAILED"),
        ("dom", "DOM_NOT_MONOTONIC"),
    ],
)
def test_stage_trace_rejects_metadata_only_partial_artifacts(
    surface,
    expected_code,
):
    trace, dom = _valid_trace()
    metadata_only = [
        _text_summary(
            f"metadata-only-{index}",
            length,
            ("## 文档信息",),
            metadata={
                "heading": "## 文档信息",
                "index": 0,
                "isFinal": True,
                "compact": True,
                "hasTable": False,
            },
        )
        for index, length in enumerate((80, 160), start=1)
    ]
    if surface == "network":
        trace["events"][2]["artifact"] = metadata_only[0]
        trace["events"][3]["artifact"] = metadata_only[1]
    else:
        dom["events"][1] = {
            "kind": "artifact",
            "attempt": 0,
            **metadata_only[0],
        }
        dom["events"][2] = {
            "kind": "artifact",
            "attempt": 0,
            **metadata_only[1],
        }

    with pytest.raises(assertions.FunctionalAssertionError) as captured:
        assertions.assert_stage_trace(
            trace,
            dom,
            expected_next_stage_id="STRATEGY",
        )

    assert captured.value.code == expected_code


@pytest.mark.parametrize(
    ("surface", "expected_code"),
    [
        ("network", "CONTRACT_VALIDATION_FAILED"),
        ("dom", "DOM_NOT_MONOTONIC"),
    ],
)
def test_stage_trace_rejects_metadata_before_business_section(
    surface,
    expected_code,
):
    trace, dom = _valid_trace()
    metadata_first = _text_summary(
        "metadata-first",
        80,
        ("## 文档信息", "## 1. 被测系统与边界"),
        metadata={
            "heading": "## 文档信息",
            "index": 0,
            "isFinal": False,
            "compact": True,
            "hasTable": False,
        },
    )
    if surface == "network":
        trace["events"][2]["artifact"] = metadata_first
    else:
        dom["events"][1] = {
            "kind": "artifact",
            "attempt": 0,
            **metadata_first,
        }

    with pytest.raises(assertions.FunctionalAssertionError) as captured:
        assertions.assert_stage_trace(
            trace,
            dom,
            expected_next_stage_id="STRATEGY",
        )

    assert captured.value.code == expected_code


def test_stage_trace_counts_retry_and_resets_attempt_monotonicity():
    trace, dom = _valid_trace()
    trace["events"].insert(
        1,
        {
            "type": "agent_delta",
            "attempt": 0,
            "artifact": _text_summary("failed-attempt", 120),
        },
    )
    trace["events"].insert(
        2,
        {"type": "agent_retry", "attempt": 1, "reason": "schema"},
    )
    for event in trace["events"][3:]:
        event["attempt"] = 1
    for event in dom["events"]:
        event["attempt"] = 1
    dom["events"].insert(
        0,
        {
            "kind": "artifact",
            "attempt": 0,
            **_text_summary("failed-dom-attempt", 120, ("# 失败草稿",)),
        },
    )

    result = assertions.assert_stage_trace(
        trace,
        dom,
        expected_next_stage_id="STRATEGY",
    )

    assert result.retry_count == 1
    assert result.request_id == "request-1"
    assert result.artifact_hash == "artifact-final"


def test_stage_trace_allows_active_tail_section_to_grow():
    trace, dom = _valid_trace()
    trace["events"][3]["artifact"]["sections"][-1]["hash"] = "active-tail-v1"
    trace["events"][4]["artifact"]["sections"][-2]["hash"] = "active-tail-v2"
    dom["events"][2]["sections"][-1]["hash"] = "active-tail-v1"
    dom["events"][3]["sections"][-2]["hash"] = "active-tail-v2"

    result = assertions.assert_stage_trace(
        trace,
        dom,
        expected_next_stage_id="STRATEGY",
    )

    assert result.artifact_hash == "artifact-final"


def test_stage_trace_rejects_duplicate_heading_active_tail_bypass():
    trace, dom = _valid_trace()
    final_artifact = trace["events"][-2]["artifact"]
    duplicate_section = {
        **final_artifact["sections"][-2],
        "hash": "rewritten-duplicate-tail",
        "previousPrefixHash": "rewritten-prefix",
    }
    final_artifact["headings"].insert(-1, final_artifact["headings"][-2])
    final_artifact["sections"].insert(-1, duplicate_section)
    final_artifact["metadata"]["index"] += 1
    dom["events"][-1] = {
        "kind": "artifact",
        "attempt": 0,
        **final_artifact,
    }

    with pytest.raises(
        assertions.FunctionalAssertionError,
        match="duplicate",
    ):
        assertions.assert_stage_trace(
            trace,
            dom,
            expected_next_stage_id="STRATEGY",
        )


def test_stage_trace_rejects_terminal_chat_rewrite_after_valid_deltas():
    trace, dom = _valid_trace()
    trace["events"][-2]["chat"] = _text_summary(
        "rewritten-final-chat",
        64,
        monotonic=False,
    )

    with pytest.raises(
        assertions.FunctionalAssertionError,
        match="final chat content is not monotonic",
    ):
        assertions.assert_stage_trace(
            trace,
            dom,
            expected_next_stage_id="STRATEGY",
        )


def test_stage_trace_allows_new_section_to_insert_before_existing_footer():
    trace, dom = _valid_trace()
    artifact_one = _text_summary(
        "artifact-1",
        120,
        (
            "# 需求分析文档",
            "## 2. 后到字段对应的已显示章节",
            "## 文档信息",
        ),
        metadata={
            "heading": "## 文档信息",
            "index": 2,
            "isFinal": True,
            "compact": True,
            "hasTable": False,
        },
    )
    artifact_two = _text_summary(
        "artifact-2",
        200,
        (
            "# 需求分析文档",
            "## 1. 规范顺序中更早的新增章节",
            "## 2. 后到字段对应的已显示章节",
            "## 文档信息",
        ),
        metadata={
            "heading": "## 文档信息",
            "index": 3,
            "isFinal": True,
            "compact": True,
            "hasTable": False,
        },
    )
    artifact_final = _text_summary(
        "artifact-final",
        260,
        tuple(artifact_two["headings"]),
        metadata=artifact_two["metadata"],
    )
    for summary in (artifact_one, artifact_two, artifact_final):
        for section in summary["sections"]:
            if section["headingHash"] == assertions.text_digest("# 需求分析文档"):
                section["hash"] = "stable-title"
            elif section["headingHash"] == assertions.text_digest(
                "## 2. 后到字段对应的已显示章节"
            ):
                section["hash"] = "stable-existing-section"
            elif section["headingHash"] == assertions.text_digest(
                "## 1. 规范顺序中更早的新增章节"
            ):
                section["hash"] = "stable-inserted-section"
    trace["events"][2]["artifact"] = artifact_one
    trace["events"][3]["artifact"] = artifact_two
    trace["events"][4]["artifact"] = artifact_final
    dom["events"][1] = {"kind": "artifact", "attempt": 0, **artifact_one}
    dom["events"][2] = {"kind": "artifact", "attempt": 0, **artifact_two}
    dom["events"][3] = {"kind": "artifact", "attempt": 0, **artifact_final}

    result = assertions.assert_stage_trace(
        trace,
        dom,
        expected_next_stage_id="STRATEGY",
    )

    assert result.artifact_hash == "artifact-final"


def test_stage_trace_rejects_numbered_or_tabular_metadata_footer():
    trace, dom = _valid_trace()
    metadata = trace["events"][-2]["artifact"]["metadata"]
    metadata.update(
        {
            "headingHash": assertions.text_digest("## 1. 文档信息"),
            "headingLevel": 2,
            "index": 1,
            "isFinal": False,
            "compact": False,
            "hasTable": True,
        }
    )

    with pytest.raises(
        assertions.FunctionalAssertionError,
        match="metadata",
    ):
        assertions.assert_stage_trace(
            trace,
            dom,
            expected_next_stage_id="STRATEGY",
        )


def test_snapshot_requires_cumulative_messages_artifacts_and_context_summaries():
    snapshot = {
        "run": {
            "id": "run-1",
            "workflowId": "TEST_DESIGN",
            "currentStageId": "STRATEGY",
        },
        "messages": [
            {"role": "user", "sequenceIndex": 1},
            {"role": "assistant", "sequenceIndex": 2},
            {"role": "user", "sequenceIndex": 3},
            {"role": "assistant", "sequenceIndex": 4},
        ],
        "artifacts": [
            {
                "stageId": "CLARIFY",
                "content": "clarify",
                "artifactData": {"ok": True},
                "versionNumber": 1,
            },
            {
                "stageId": "STRATEGY",
                "content": "strategy",
                "artifactData": {"ok": True},
                "versionNumber": 1,
            },
        ],
        "contextSummaries": [
            {"sourceStageId": "CLARIFY", "content": "clarify summary"},
            {"sourceStageId": "STRATEGY", "content": "strategy summary"},
        ],
    }
    final_hash = assertions.text_digest("strategy")

    result = assertions.assert_snapshot(
        snapshot,
        run_id="run-1",
        workflow_id="TEST_DESIGN",
        current_stage_id="STRATEGY",
        expected_stage_ids=("CLARIFY", "STRATEGY"),
        expected_turn_count=2,
        final_artifact_hash=final_hash,
    )
    assert result.message_count == 4
    assert result.artifact_stage_ids == ("CLARIFY", "STRATEGY")

    snapshot["contextSummaries"] = [snapshot["contextSummaries"][1]]
    with pytest.raises(assertions.FunctionalAssertionError):
        assertions.assert_snapshot(
            snapshot,
            run_id="run-1",
            workflow_id="TEST_DESIGN",
            current_stage_id="STRATEGY",
            expected_stage_ids=("CLARIFY", "STRATEGY"),
            expected_turn_count=2,
            final_artifact_hash=final_hash,
        )


def test_stream_observer_exports_only_summaries_and_seeds_current_assistant():
    source = Path(__file__).with_name("stream_observer.py").read_text(encoding="utf-8")

    assert "hashText" in source
    assert "summarizeText" in source
    assert "text: assistant" not in source
    assert "text: artifactText" not in source
    assert "...JSON.parse(data)" not in source
    assert "lastChat: currentAssistant" in source
    assert "streamIndex" in source
    assert "workflowId: trace.request?.workflowId" in source
    assert "stageId: trace.request?.stageId" in source
    assert "projected.targetStageId = safeDiagnosticToken" in source
    assert "'AGENT_RUNTIME_UNAVAILABLE'" in source
    assert "'REQUEST_IDENTITY_CONFLICT'" in source
    assert "'RUNTIME_DEPENDENCY_MISSING'" not in source


@pytest.mark.parametrize("field", ["hash", "length"])
def test_stage_trace_requires_terminal_network_artifact_to_match_final_dom(field):
    trace, dom = _valid_trace()
    dom["events"][-1][field] = (
        "different-artifact" if field == "hash" else dom["events"][-1][field] + 1
    )

    with pytest.raises(
        assertions.FunctionalAssertionError,
        match="terminal artifact",
    ):
        assertions.assert_stage_trace(
            trace,
            dom,
            expected_next_stage_id="STRATEGY",
        )


@pytest.mark.parametrize(
    "dom_summary",
    [
        {"hash": "different-artifact", "length": len("persisted markdown")},
        {
            "hash": assertions.text_digest("persisted markdown"),
            "length": len("persisted markdown") + 1,
        },
    ],
)
def test_restored_artifact_requires_dom_source_to_match_snapshot_content(dom_summary):
    with pytest.raises(
        assertions.FunctionalAssertionError,
        match="restored DOM artifact",
    ):
        assertions.assert_restored_artifact(
            dom_summary,
            snapshot_content="persisted markdown",
            run_id="run-1",
        )


def test_restored_artifact_accepts_dom_source_matching_snapshot_content():
    content = "persisted markdown"

    assertions.assert_restored_artifact(
        {"hash": assertions.text_digest(content), "length": len(content)},
        snapshot_content=content,
        run_id="run-1",
    )


def test_restored_assistant_messages_require_snapshot_content_and_order():
    snapshot_messages = [
        {"role": "user", "content": "第一轮输入"},
        {"role": "assistant", "content": "第一轮回复"},
        {"role": "user", "content": "内部阶段续写提示"},
        {"role": "assistant", "content": "第二轮回复"},
    ]
    reversed_dom = [
        {
            "hash": assertions.text_digest("第二轮回复"),
            "length": len("第二轮回复"),
        },
        {
            "hash": assertions.text_digest("第一轮回复"),
            "length": len("第一轮回复"),
        },
    ]

    with pytest.raises(
        assertions.FunctionalAssertionError,
        match="restored assistant message history",
    ):
        assertions.assert_restored_assistant_messages(
            reversed_dom,
            snapshot_messages=snapshot_messages,
            run_id="run-1",
        )


def test_restored_assistant_messages_accept_snapshot_content_in_order():
    snapshot_messages = [
        {"role": "user", "content": "第一轮输入"},
        {"role": "assistant", "content": "第一轮回复"},
        {"role": "user", "content": "内部阶段续写提示"},
        {"role": "assistant", "content": "第二轮回复"},
    ]

    assertions.assert_restored_assistant_messages(
        [
            {
                "hash": assertions.text_digest("第一轮回复"),
                "length": len("第一轮回复"),
            },
            {
                "hash": assertions.text_digest("第二轮回复"),
                "length": len("第二轮回复"),
            },
        ],
        snapshot_messages=snapshot_messages,
        run_id="run-1",
    )


def test_typed_assertion_details_include_actual_workflow_stage_coordinates():
    trace, dom = _valid_trace()
    trace["events"][-2]["requestsNextStage"] = False

    with pytest.raises(assertions.FunctionalAssertionError) as captured:
        assertions.assert_stage_trace(
            trace,
            dom,
            expected_next_stage_id="STRATEGY",
        )

    assert captured.value.details["workflowId"] == "TEST_DESIGN"
    assert captured.value.details["stageId"] == "CLARIFY"


def test_stage_trace_rejects_wrong_next_stage_target():
    trace, dom = _valid_trace()
    trace["events"][-2]["targetStageId"] = "REPORT"

    with pytest.raises(
        assertions.FunctionalAssertionError,
        match="immediate next stage STRATEGY",
    ):
        assertions.assert_stage_trace(
            trace,
            dom,
            expected_next_stage_id="STRATEGY",
        )


def test_typed_assertion_details_include_safe_error_diagnostic_coordinates():
    trace, dom = _valid_trace()
    trace["events"] = [
        trace["events"][0],
        {
            "type": "error",
            "attempt": 0,
            "code": "SCHEMA_VALIDATION_FAILED",
            "diagnostic": {
                "phase": "structured_output",
                "fieldPath": "artifact_data.test_cases.0.expected_results",
                "validator": "list_type",
                "retryable": False,
            },
        },
        trace["events"][-1],
    ]

    with pytest.raises(assertions.FunctionalAssertionError) as captured:
        assertions.assert_stage_trace(
            trace,
            dom,
            expected_next_stage_id="STRATEGY",
        )

    assert captured.value.details["diagnostic"] == {
        "phase": "structured_output",
        "fieldPath": "artifact_data.test_cases.0.expected_results",
        "validator": "list_type",
        "retryable": False,
    }


def test_live_stack_cleanup_attempts_every_resource_after_one_close_failure(
    monkeypatch,
):
    live_stack = importlib.import_module("tests.e2e.new_agents_real.live_stack")
    calls: list[str] = []

    class BrokenContext:
        def close(self):
            calls.append("context")
            raise ValueError("context close failed")

    class Resource:
        def __init__(self, label: str, method: str):
            self.label = label
            setattr(self, method, self.record)

        def record(self):
            calls.append(self.label)

    stack = object.__new__(live_stack.LiveStack)
    stack._context = BrokenContext()
    stack._browser = Resource("browser", "close")
    stack._playwright = Resource("playwright", "stop")
    stack._frontend_process = object()
    stack._backend_process = object()
    stack._frontend_log = Resource("frontend-log", "close")
    stack._backend_log = Resource("backend-log", "close")
    stack._temporary_directory = Resource("temporary-directory", "cleanup")
    stack.page = object()
    stack.llm_config = type(
        "Config",
        (),
        {"redaction_secrets": lambda self: ()},
    )()

    def stop_process(process):
        calls.append(
            "frontend-process"
            if process is stack._frontend_process
            else "backend-process"
        )

    monkeypatch.setattr(live_stack, "_stop_process", stop_process)

    with pytest.raises(RuntimeError, match="cleanup"):
        stack.close()

    assert calls == [
        "context",
        "browser",
        "playwright",
        "frontend-process",
        "backend-process",
        "frontend-log",
        "backend-log",
        "temporary-directory",
    ]
    assert stack.page is None


def test_failure_evidence_uses_typed_code_and_trace_coordinates():
    reporting = _load_reporting()
    error = assertions.FunctionalAssertionError(
        "DOM_NOT_MONOTONIC",
        "artifact regressed",
        details={
            "runId": "run-1",
            "eventIndex": 4,
            "monotonicReason": "active_tail_rewrite",
        },
    )

    payload = reporting.build_failure_evidence(
        error,
        scope="pr",
        workflow_id="TEST_DESIGN",
        stage_id="CLARIFY",
        trace_summary={
            "requestId": "request-1",
            "retryCount": 1,
            "artifactHash": "sha256-" + "d" * 64,
        },
    )

    assert payload["status"] == "FAIL"
    assert payload["errorCode"] == "DOM_NOT_MONOTONIC"
    assert payload["errorCategory"] == "frontend"
    assert payload["runId"] == "run-1"
    assert payload["requestId"] == "request-1"
    assert payload["eventIndex"] == 4
    assert payload["retryCount"] == 1
    assert payload["monotonicReason"] == "active_tail_rewrite"


def test_failure_evidence_drops_raw_exception_and_unapproved_coordinates():
    reporting = _load_reporting()
    secret = "sk-qg020-failure-canary"
    error = assertions.FunctionalAssertionError(
        "DOM_NOT_MONOTONIC",
        f"raw browser output {secret}",
        details={
            "runId": "run-1",
            "rawProviderOutput": secret,
            "monotonicReason": secret,
            "diagnostic": {
                "phase": "structured_output",
                "fieldPath": "artifact_data.test_cases",
                "validator": "list_type",
                "retryable": False,
                "publicReason": secret,
            },
        },
    )

    payload = reporting.build_failure_evidence(
        error,
        scope="pr",
        workflow_id="TEST_DESIGN",
        stage_id="CASES",
        trace_summary={
            "requestId": "request-1",
            "observerError": secret,
            "unknownCoordinate": secret,
        },
    )

    serialized = json.dumps(payload)
    assert secret not in serialized
    assert payload["reason"] == "DOM_NOT_MONOTONIC: functional gate failed"
    assert "rawProviderOutput" not in payload
    assert "unknownCoordinate" not in payload
    assert "observerError" not in payload
    assert payload["diagnostic"] == {
        "phase": "structured_output",
        "fieldPath": "artifact_data.test_cases",
        "validator": "list_type",
        "retryable": False,
    }


@pytest.mark.parametrize("error_kind", ["playwright", "assertion"])
@pytest.mark.parametrize("report_fails", [False, True])
def test_real_agent_boundary_rethrows_browser_failure_without_raw_model_text(
    monkeypatch,
    tmp_path,
    error_kind,
    report_fails,
):
    real_tests = importlib.import_module(
        "tests.e2e.new_agents_real.test_real_agent_workflows"
    )
    canary = "RAW-MODEL-ARTIFACT-CANARY"
    report_canary = "RAW-REPORT-WRITE-CANARY"
    report = tmp_path / "failure.json"
    case = matrix.FunctionalCase(
        kind="workflow",
        workflow_id="TEST_DESIGN",
        stage_id=None,
        agent_id="lisa",
        slug="test-design",
    )

    class Config:
        @staticmethod
        def redaction_secrets():
            return ()

    class Stack:
        llm_config = Config()
        page = None

        @staticmethod
        def redaction_secrets():
            return ()

    def raise_browser_failure(*_args, **_kwargs):
        if error_kind == "playwright":
            raise real_tests.PlaywrightError(canary)
        raise AssertionError(canary)

    monkeypatch.setattr(
        real_tests,
        "_scenarios",
        lambda: {"TEST_DESIGN": {"prompt": "safe prompt"}},
    )
    monkeypatch.setattr(real_tests, "_scope", lambda: "release")
    monkeypatch.setattr(real_tests, "report_path", lambda *_args: report)
    monkeypatch.setattr(real_tests, "latest_trace_summary", lambda _page: {})
    monkeypatch.setattr(
        real_tests,
        "run_workflow_journey",
        raise_browser_failure,
    )
    if report_fails:

        def fail_report_write(*_args, **_kwargs):
            raise OSError(report_canary)

        monkeypatch.setattr(real_tests, "write_report", fail_report_write)

    with pytest.raises(real_tests.FunctionalAssertionError) as captured:
        real_tests.test_real_agent_functional_scope(Stack(), case)

    expected_code = (
        "REPORT_WRITE_FAILED" if report_fails else "BROWSER_ASSERTION_FAILED"
    )
    expected_message = (
        "functional evidence report could not be written"
        if report_fails
        else "browser functional assertion failed"
    )
    assert captured.value.code == expected_code
    assert str(captured.value) == f"{expected_code}: {expected_message}"
    assert captured.value.__suppress_context__ is True
    formatted = "".join(traceback.format_exception(captured.value))
    assert canary not in formatted
    assert report_canary not in formatted
    if not report_fails:
        assert canary not in report.read_text(encoding="utf-8")
        report_payload = json.loads(report.read_text(encoding="utf-8"))
        assert report_payload["errorCode"] == "BROWSER_ASSERTION_FAILED"
        assert report_payload["errorCategory"] == "frontend"


def test_workflow_failure_evidence_uses_actual_trace_stage_coordinates():
    reporting = _load_reporting()
    error = assertions.FunctionalAssertionError(
        "INVALID_STAGE_TRANSITION",
        "journey failed in the second stage",
    )

    payload = reporting.build_failure_evidence(
        error,
        scope="release",
        workflow_id="TEST_DESIGN",
        stage_id=None,
        trace_summary={
            "workflowId": "TEST_DESIGN",
            "stageId": "STRATEGY",
            "runId": "run-1",
            "requestId": "request-2",
        },
    )

    assert payload["workflowId"] == "TEST_DESIGN"
    assert payload["stageId"] == "STRATEGY"
    assert payload["runId"] == "run-1"
    assert payload["requestId"] == "request-2"


def test_real_fixture_records_sanitized_startup_failure():
    source = Path(__file__).with_name("conftest.py").read_text(encoding="utf-8")

    assert "LiveStackStartupError" in source
    assert "build_failure_evidence" in source
    assert "write_report" in source
    assert 'report_path(ROOT, scope, "startup")' in source


def test_startup_diagnostic_redacts_secret_and_bounds_process_logs(tmp_path):
    live_stack = importlib.import_module("tests.e2e.new_agents_real.live_stack")
    config_module = importlib.import_module("tests.e2e.new_agents_real.config")
    secret = "sk-qg020-startup-canary"
    proxy_key = "qg020-proxy-key-canary"
    config_admin_key = "qg020-config-admin-key-canary"
    log_path = tmp_path / "backend.log"
    log_path.write_text(
        "prefix\n"
        + secret
        + "\n"
        + proxy_key
        + "\n"
        + config_admin_key
        + "\n"
        + ("x" * 6000),
        encoding="utf-8",
    )
    stack = object.__new__(live_stack.LiveStack)
    stack.llm_config = config_module.RealLlmConfig(
        secret,
        "https://api.deepseek.example/v1",
        "deepseek-v4-flash",
    )
    stack._proxy_api_key = proxy_key
    stack._config_admin_api_key = config_admin_key
    stack._backend_log_path = log_path
    stack._frontend_log_path = None
    stack._backend_log = None
    stack._frontend_log = None

    diagnostic = stack._startup_diagnostic(
        RuntimeError(f"provider {secret}; proxy {proxy_key}; admin {config_admin_key}")
    )

    assert secret not in diagnostic
    assert proxy_key not in diagnostic
    assert config_admin_key not in diagnostic
    assert "<redacted>" in diagnostic
    assert len(diagnostic) < 5000


def test_live_stack_launches_browser_with_secret_free_os_environment(
    monkeypatch,
    tmp_path,
):
    live_stack = importlib.import_module("tests.e2e.new_agents_real.live_stack")
    config_module = importlib.import_module("tests.e2e.new_agents_real.config")
    api_key = "BROWSER-INHERITANCE-API-KEY-CANARY"
    token = "BROWSER-INHERITANCE-TOKEN-CANARY"
    password = "BROWSER-INHERITANCE-PASSWORD-CANARY"
    proxy_key = "LIVE-STACK-PROXY-KEY-CANARY"
    config_admin_key = "LIVE-STACK-CONFIG-ADMIN-KEY-CANARY"
    required_environment = {
        "PATH": "/safe/browser/bin",
        "HOME": str(tmp_path / "home"),
        "TMPDIR": str(tmp_path / "tmp"),
    }
    for name, value in required_environment.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("NEW_AGENTS_SMOKE_API_KEY", api_key)
    monkeypatch.setenv("OTHER_TOKEN", token)
    monkeypatch.setenv("SERVICE_PASSWORD", password)
    captured_launch: dict = {}
    captured_process_environments: list[dict[str, str]] = []
    captured_proxy_file: dict[str, object] = {}

    class FakeProcess:
        pass

    class FakePage:
        pass

    class FakeContext:
        def new_page(self):
            return FakePage()

        def close(self):
            return None

    class FakeBrowser:
        def new_context(self, *, base_url):
            captured_launch["base_url"] = base_url
            return FakeContext()

        def close(self):
            return None

    class FakeChromium:
        def launch(self, **kwargs):
            captured_launch["kwargs"] = kwargs
            return FakeBrowser()

    class FakePlaywright:
        chromium = FakeChromium()

        def stop(self):
            return None

    class FakePlaywrightManager:
        @staticmethod
        def start():
            captured_launch["driver_environment"] = dict(os.environ)
            return FakePlaywright()

    ports = iter((19001, 19002))
    monkeypatch.setattr(live_stack, "_free_port", lambda: next(ports))
    monkeypatch.setattr(live_stack, "_build_proxy_api_key", lambda: proxy_key)
    monkeypatch.setattr(
        live_stack,
        "_build_config_admin_api_key",
        lambda: config_admin_key,
    )

    def capture_popen(*_args, **kwargs):
        process_environment = dict(kwargs["env"])
        captured_process_environments.append(process_environment)
        proxy_file_value = process_environment.get("NEW_AGENTS_PROXY_API_KEY_FILE")
        if proxy_file_value:
            proxy_file = Path(proxy_file_value)
            captured_proxy_file.update(
                {
                    "content": proxy_file.read_text(encoding="utf-8"),
                    "mode": proxy_file.stat().st_mode & 0o777,
                }
            )
        return FakeProcess()

    monkeypatch.setattr(live_stack.subprocess, "Popen", capture_popen)
    monkeypatch.setattr(live_stack, "_wait_for_url", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(live_stack, "_stop_process", lambda _process: None)
    monkeypatch.setattr(
        live_stack,
        "sync_playwright",
        lambda: FakePlaywrightManager(),
    )
    monkeypatch.setattr(
        live_stack,
        "install_stream_observer",
        lambda _page: None,
    )
    config = config_module.RealLlmConfig(
        api_key,
        "https://api.deepseek.example/v1",
        "deepseek-v4-flash",
    )

    with live_stack.LiveStack(tmp_path, config) as stack:
        assert "NEW_AGENTS_PROXY_API_KEY" not in stack.frontend_environment
        assert "NEW_AGENTS_PROXY_API_KEY_FILE" not in stack.frontend_environment
        assert proxy_key in stack.redaction_secrets()
        assert config_admin_key in stack.redaction_secrets()

    browser_environment = captured_launch["kwargs"].get("env")
    assert isinstance(browser_environment, dict)
    assert required_environment.items() <= browser_environment.items()
    assert "NEW_AGENTS_SMOKE_API_KEY" not in browser_environment
    assert "OTHER_TOKEN" not in browser_environment
    assert "SERVICE_PASSWORD" not in browser_environment
    assert api_key not in browser_environment.values()
    assert token not in browser_environment.values()
    assert password not in browser_environment.values()
    assert proxy_key not in browser_environment.values()
    assert config_admin_key not in browser_environment.values()

    driver_environment = captured_launch["driver_environment"]
    assert required_environment.items() <= driver_environment.items()
    assert "NEW_AGENTS_SMOKE_API_KEY" not in driver_environment
    assert "OTHER_TOKEN" not in driver_environment
    assert "SERVICE_PASSWORD" not in driver_environment
    assert api_key not in driver_environment.values()
    assert token not in driver_environment.values()
    assert password not in driver_environment.values()
    assert proxy_key not in driver_environment.values()
    assert config_admin_key not in driver_environment.values()

    assert len(captured_process_environments) == 2
    backend_environment, frontend_environment = captured_process_environments
    assert backend_environment["NEW_AGENTS_DEFAULT_LLM_API_KEY"] == api_key
    assert backend_environment["PROXY_API_KEY"] == proxy_key
    assert backend_environment["NEW_AGENTS_CONFIG_ADMIN_API_KEY"] == config_admin_key
    assert (
        backend_environment["NEW_AGENTS_CONFIG_ADMIN_API_KEY"]
        != backend_environment["PROXY_API_KEY"]
    )
    assert backend_environment["NEW_AGENTS_CONFIG_ADMIN_API_KEY"] != api_key
    assert backend_environment["PROXY_API_KEY"] != api_key
    assert backend_environment["AI4SE_TRUST_GATEWAY_HEADER"] == "0"
    assert "NEW_AGENTS_SMOKE_API_KEY" not in backend_environment
    assert "OTHER_TOKEN" not in backend_environment
    assert "SERVICE_PASSWORD" not in backend_environment
    assert required_environment.items() <= frontend_environment.items()
    assert "NEW_AGENTS_PROXY_API_KEY" not in frontend_environment
    assert proxy_key not in frontend_environment.values()
    assert config_admin_key not in frontend_environment.values()
    assert "NEW_AGENTS_PROXY_API_KEY_FILE" in frontend_environment
    assert captured_proxy_file == {"content": proxy_key, "mode": 0o600}
    assert "NEW_AGENTS_SMOKE_API_KEY" not in frontend_environment
    assert "OTHER_TOKEN" not in frontend_environment
    assert "SERVICE_PASSWORD" not in frontend_environment

    assert os.environ["NEW_AGENTS_SMOKE_API_KEY"] == api_key
    assert os.environ["OTHER_TOKEN"] == token
    assert os.environ["SERVICE_PASSWORD"] == password


def test_live_stack_restores_parent_environment_when_playwright_start_fails(
    monkeypatch,
    tmp_path,
):
    live_stack = importlib.import_module("tests.e2e.new_agents_real.live_stack")
    config_module = importlib.import_module("tests.e2e.new_agents_real.config")
    api_key = "FAILED-DRIVER-API-KEY-CANARY"
    token = "FAILED-DRIVER-TOKEN-CANARY"
    password = "FAILED-DRIVER-PASSWORD-CANARY"
    monkeypatch.setenv("PATH", "/safe/browser/bin")
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("TMPDIR", str(tmp_path / "tmp"))
    monkeypatch.setenv("NEW_AGENTS_SMOKE_API_KEY", api_key)
    monkeypatch.setenv("OTHER_TOKEN", token)
    monkeypatch.setenv("SERVICE_PASSWORD", password)
    captured_driver_environment: dict[str, str] = {}

    class FakeProcess:
        pass

    class FailingPlaywrightManager:
        @staticmethod
        def start():
            captured_driver_environment.update(os.environ)
            raise RuntimeError("safe driver startup failure")

    ports = iter((19001, 19002))
    monkeypatch.setattr(live_stack, "_free_port", lambda: next(ports))
    monkeypatch.setattr(
        live_stack.subprocess,
        "Popen",
        lambda *_args, **_kwargs: FakeProcess(),
    )
    monkeypatch.setattr(live_stack, "_wait_for_url", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(live_stack, "_stop_process", lambda _process: None)
    monkeypatch.setattr(
        live_stack,
        "sync_playwright",
        lambda: FailingPlaywrightManager(),
    )
    config = config_module.RealLlmConfig(
        api_key,
        "https://api.deepseek.example/v1",
        "deepseek-v4-flash",
    )

    with pytest.raises(live_stack.LiveStackStartupError):
        with live_stack.LiveStack(tmp_path, config):
            pass

    assert captured_driver_environment["PATH"] == "/safe/browser/bin"
    assert captured_driver_environment["HOME"] == str(tmp_path / "home")
    assert captured_driver_environment["TMPDIR"] == str(tmp_path / "tmp")
    assert "NEW_AGENTS_SMOKE_API_KEY" not in captured_driver_environment
    assert "OTHER_TOKEN" not in captured_driver_environment
    assert "SERVICE_PASSWORD" not in captured_driver_environment
    assert api_key not in captured_driver_environment.values()
    assert token not in captured_driver_environment.values()
    assert password not in captured_driver_environment.values()

    assert os.environ["NEW_AGENTS_SMOKE_API_KEY"] == api_key
    assert os.environ["OTHER_TOKEN"] == token
    assert os.environ["SERVICE_PASSWORD"] == password


def test_live_stack_services_own_process_groups_for_recursive_cleanup():
    source = Path(__file__).with_name("live_stack.py").read_text(encoding="utf-8")

    assert source.count("start_new_session=True") == 2
    assert "os.killpg(process.pid, signal.SIGTERM)" in source
    assert "os.killpg(process.pid, signal.SIGKILL)" in source


def test_real_workflow_runner_exposes_stage_probe_and_workflow_journey():
    workflow_runner = importlib.import_module(
        "tests.e2e.new_agents_real.workflow_runner"
    )

    assert callable(workflow_runner.run_stage_probe)
    assert callable(workflow_runner.run_workflow_journey)


def test_stage_probe_prompt_authorizes_completion_and_requests_immediate_next_stage():
    workflow_runner = importlib.import_module(
        "tests.e2e.new_agents_real.workflow_runner"
    )

    prompt = workflow_runner.stage_probe_prompt(
        "原始场景输入。",
        expected_next_stage_id="ROOT_CAUSE",
    )

    assert prompt.startswith("原始场景输入。\n\n")
    assert "请直接完整完成当前阶段" in prompt
    assert "允许采用合理假设" in prompt
    assert "必须明确标注" in prompt
    assert "必须请求进入紧邻的下一阶段" in prompt
    assert 'stage_action.target_stage_id 必须填写内部 ID "ROOT_CAUSE"' in prompt
    assert "不得跳过阶段" in prompt


def test_terminal_stage_probe_prompt_forbids_requesting_a_next_stage():
    workflow_runner = importlib.import_module(
        "tests.e2e.new_agents_real.workflow_runner"
    )

    prompt = workflow_runner.stage_probe_prompt(
        "原始场景输入。",
        expected_next_stage_id=None,
    )

    assert "请直接完整完成当前阶段" in prompt
    assert "当前阶段是末阶段；完成后不得请求进入下一阶段" in prompt
    assert "必须请求进入紧邻的下一阶段" not in prompt


def test_workflow_journey_prompt_does_not_persist_first_stage_transition_identity():
    workflow_runner = importlib.import_module(
        "tests.e2e.new_agents_real.workflow_runner"
    )

    prompt = workflow_runner.workflow_journey_prompt(
        "完整工作流场景输入。",
        expected_next_stage_id="ROOT_CAUSE",
    )

    assert prompt.startswith("完整工作流场景输入。\n\n")
    assert "请直接完整完成当前阶段" in prompt
    assert "允许采用合理假设" in prompt
    assert "必须明确标注" in prompt
    assert "阶段推进必须遵循当前阶段的系统契约" in prompt
    assert "stage_action.target_stage_id" not in prompt
    assert "ROOT_CAUSE" not in prompt


def test_single_stage_workflow_journey_prompt_forbids_requesting_next_stage():
    workflow_runner = importlib.import_module(
        "tests.e2e.new_agents_real.workflow_runner"
    )

    prompt = workflow_runner.workflow_journey_prompt(
        "单阶段工作流场景输入。",
        expected_next_stage_id=None,
    )

    assert "请直接完整完成当前阶段" in prompt
    assert "当前阶段是末阶段；完成后不得请求进入下一阶段" in prompt
    assert "stage_action.target_stage_id 必须填写内部 ID" not in prompt


def test_scenario_catalog_matches_manifest_and_pr_selection():
    root = Path(__file__).resolve().parents[3]
    manifest = json.loads(
        (root / "tools/new-agents/workflow_manifest.json").read_text(encoding="utf-8")
    )
    scenarios = json.loads(
        (root / "tests/e2e/new_agents_real/real_llm_scenarios.json").read_text(
            encoding="utf-8"
        )
    )

    assert set(scenarios) == set(manifest["workflows"])
    assert {
        workflow_id
        for workflow_id, scenario in scenarios.items()
        if scenario["prCritical"]
    } == {"TEST_DESIGN", "VALUE_DISCOVERY"}
    assert all(len(scenario["prompt"].strip()) >= 80 for scenario in scenarios.values())


def test_test_design_scenario_supplies_blocking_clarify_decisions():
    root = Path(__file__).resolve().parents[3]
    scenarios = json.loads(
        (root / "tests/e2e/new_agents_real/real_llm_scenarios.json").read_text(
            encoding="utf-8"
        )
    )
    prompt = scenarios["TEST_DESIGN"]["prompt"]

    for decision in (
        "连续 5 次失败",
        "锁定 30 分钟",
        "验证码 60 秒",
        "24 小时",
        "管理员、操作员、审计员",
        "保留 180 天",
        "OIDC 授权码 + PKCE",
        "IdP subject",
        "未映射组默认无权限",
        "IdP 不可用时新登录失败关闭",
        "除此之外没有未决 P0/P1",
    ):
        assert decision in prompt
    assert "未明确的非阻断细节" in prompt
