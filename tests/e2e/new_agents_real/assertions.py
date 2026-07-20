from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any, NoReturn

DIGEST_PATTERN = re.compile(r"sha256-[0-9a-f]{64}")


class FunctionalAssertionError(AssertionError):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ):
        self.code = code
        self.details = details or {}
        super().__init__(f"{code}: {message}")


@dataclass(frozen=True)
class StageTraceResult:
    run_id: str
    request_id: str
    event_types: tuple[str, ...]
    artifact_delta_count: int
    artifact_hash: str
    first_heading: str
    retry_count: int


@dataclass(frozen=True)
class SnapshotResult:
    version_number: int
    message_count: int
    artifact_stage_ids: tuple[str, ...]
    context_summary_count: int


def text_digest(value: str) -> str:
    """Match the browser observer's SHA-256 digest over UTF-8 text."""
    normalized = value.encode("utf-16", errors="surrogatepass").decode(
        "utf-16", errors="replace"
    )
    return f"sha256-{hashlib.sha256(normalized.encode('utf-8')).hexdigest()}"


def _trace_details(
    trace: dict[str, Any],
    *,
    event_index: int | None = None,
) -> dict[str, Any]:
    events = trace.get("events", [])
    run_started = next(
        (event for event in events if event.get("type") == "run_started"),
        {},
    )
    final_artifact = next(
        (
            event.get("artifact")
            for event in reversed(events)
            if isinstance(event.get("artifact"), dict)
        ),
        {},
    )
    error_diagnostic = next(
        (
            event.get("diagnostic")
            for event in reversed(events)
            if event.get("type") == "error"
            and isinstance(event.get("diagnostic"), dict)
        ),
        None,
    )
    return {
        "workflowId": trace.get("request", {}).get("workflowId"),
        "stageId": trace.get("request", {}).get("stageId"),
        "runId": run_started.get("runId"),
        "requestId": trace.get("request", {}).get("requestId"),
        "eventIndex": event_index,
        "eventTypes": [event.get("type") for event in events],
        "retryCount": sum(1 for event in events if event.get("type") == "agent_retry"),
        "artifactHash": final_artifact.get("hash"),
        "diagnostic": error_diagnostic,
    }


def _fail(
    code: str,
    message: str,
    *,
    trace: dict[str, Any] | None = None,
    event_index: int | None = None,
    details: dict[str, Any] | None = None,
) -> NoReturn:
    diagnostic = dict(details or {})
    if trace is not None:
        diagnostic = {**_trace_details(trace, event_index=event_index), **diagnostic}
    raise FunctionalAssertionError(code, message, details=diagnostic)


def _summary(event: dict[str, Any], field: str) -> dict[str, Any] | None:
    value = event.get(field)
    return value if isinstance(value, dict) else None


def _is_ordered_subsequence(
    expected: list[Any],
    actual: list[Any],
    *,
    key,
) -> bool:
    actual_index = 0
    for item in expected:
        expected_key = key(item)
        while actual_index < len(actual) and key(actual[actual_index]) != expected_key:
            actual_index += 1
        if actual_index >= len(actual):
            return False
        actual_index += 1
    return True


def _assert_monotonic_summaries(
    summaries: list[dict[str, Any]],
    *,
    label: str,
    code: str,
    trace: dict[str, Any],
    enforce_length: bool = True,
    enforce_section_hashes: bool = False,
    require_business_section: bool = False,
) -> None:
    for index, summary in enumerate(summaries):
        if summary.get("monotonic") is not True:
            previous = summaries[index - 1] if index > 0 else {}
            _fail(
                code,
                f"{label} content is not monotonic",
                trace=trace,
                event_index=index,
                details={
                    "previousLength": previous.get("length", 0),
                    "currentLength": summary.get("length", 0),
                    "previousHash": previous.get("hash"),
                    "currentHash": summary.get("hash"),
                    "currentPrefixHash": summary.get("currentPrefixHash"),
                    "monotonicReason": summary.get("monotonicReason"),
                },
            )
        if not isinstance(summary.get("length"), int) or summary["length"] <= 0:
            _fail(code, f"{label} summary has invalid length", trace=trace)
        if not isinstance(summary.get("hash"), str) or not summary["hash"]:
            _fail(code, f"{label} summary has invalid hash", trace=trace)
        business_heading_keys: list[tuple[str, int]] = []
        for heading in summary.get("headings", []):
            if (
                not isinstance(heading, dict)
                or DIGEST_PATTERN.fullmatch(str(heading.get("hash") or "")) is None
                or not isinstance(heading.get("level"), int)
                or not 1 <= heading["level"] <= 6
                or not isinstance(heading.get("metadata"), bool)
            ):
                _fail(code, f"{label} heading summary is invalid", trace=trace)
            if not heading["metadata"]:
                business_heading_keys.append((heading["hash"], heading["level"]))
        if len(set(business_heading_keys)) != len(business_heading_keys):
            _fail(code, f"{label} has duplicate business headings", trace=trace)

        business_section_keys: list[tuple[str, int]] = []
        for section in summary.get("sections", []):
            if not isinstance(section, dict) or not isinstance(
                section.get("metadata"), bool
            ):
                _fail(code, f"{label} section summary is invalid", trace=trace)
            if not section["metadata"]:
                key = (
                    str(section.get("headingHash") or ""),
                    int(section.get("headingLevel") or 0),
                )
                if DIGEST_PATTERN.fullmatch(key[0]) is None or not 1 <= key[1] <= 6:
                    _fail(code, f"{label} section identity is invalid", trace=trace)
                business_section_keys.append(key)
        if len(set(business_section_keys)) != len(business_section_keys):
            _fail(code, f"{label} has duplicate business sections", trace=trace)
        if require_business_section and not any(
            heading_level > 1 for _, heading_level in business_section_keys
        ):
            _fail(
                code,
                f"{label} requires a business section below the document title",
                trace=trace,
                event_index=index,
            )
        if require_business_section:
            _assert_metadata_footer(
                summary,
                label=label,
                code=code,
                trace=trace,
                event_index=index,
            )

    for previous, current in zip(summaries, summaries[1:]):
        if enforce_length and current["length"] < previous["length"]:
            _fail(code, f"{label} content length regressed", trace=trace)
        previous_headings = [
            heading
            for heading in previous.get("headings", [])
            if not heading.get("metadata")
        ]
        current_headings = [
            heading
            for heading in current.get("headings", [])
            if not heading.get("metadata")
        ]
        if not _is_ordered_subsequence(
            previous_headings,
            current_headings,
            key=lambda heading: (heading.get("hash"), heading.get("level")),
        ):
            _fail(code, f"{label} heading order regressed", trace=trace)
        if enforce_section_hashes:
            previous_business_sections = [
                section
                for section in previous.get("sections", [])
                if isinstance(section, dict) and not section.get("metadata")
            ]
            previous_sections = previous_business_sections[:-1]
            current_sections = [
                section
                for section in current.get("sections", [])
                if isinstance(section, dict) and not section.get("metadata")
            ]
            if not _is_ordered_subsequence(
                previous_sections,
                current_sections,
                key=lambda section: (
                    section.get("headingHash"),
                    section.get("headingLevel"),
                    section.get("hash"),
                ),
            ):
                _fail(
                    code,
                    f"{label} completed section content regressed",
                    trace=trace,
                )
            previous_tail = (
                previous_business_sections[-1] if previous_business_sections else None
            )
            current_tail = (
                next(
                    (
                        section
                        for section in current_sections
                        if (
                            section.get("headingHash")
                            == previous_tail.get("headingHash")
                            and section.get("headingLevel")
                            == previous_tail.get("headingLevel")
                        )
                    ),
                    None,
                )
                if previous_tail is not None
                else None
            )
            if (
                current_tail is not None
                and "previousPrefixHash" in current_tail
                and current_tail.get("previousPrefixHash") != previous_tail.get("hash")
            ):
                _fail(
                    code,
                    f"{label} active section content regressed",
                    trace=trace,
                )


def _assert_metadata_footer(
    artifact: dict[str, Any],
    *,
    label: str,
    code: str,
    trace: dict[str, Any],
    event_index: int | None = None,
) -> None:
    metadata = artifact.get("metadata")
    headings = artifact.get("headings", [])
    sections = artifact.get("sections", [])
    metadata_heading_indexes = [
        index
        for index, heading in enumerate(headings)
        if isinstance(heading, dict) and heading.get("metadata") is True
    ]
    metadata_section_indexes = [
        index
        for index, section in enumerate(sections)
        if isinstance(section, dict) and section.get("metadata") is True
    ]
    if (
        metadata is None
        and not metadata_heading_indexes
        and not metadata_section_indexes
    ):
        return
    if (
        not isinstance(metadata, dict)
        or len(metadata_heading_indexes) != 1
        or len(metadata_section_indexes) != 1
    ):
        _fail(
            code,
            f"{label} metadata summary is inconsistent",
            trace=trace,
            event_index=event_index,
        )
    heading_index = metadata_heading_indexes[0]
    section_index = metadata_section_indexes[0]
    heading = headings[heading_index]
    section = sections[section_index]
    heading_hash = metadata.get("headingHash")
    if (
        not isinstance(heading_hash, str)
        or DIGEST_PATTERN.fullmatch(heading_hash) is None
        or metadata.get("headingLevel") not in (1, 2, 3)
        or heading.get("hash") != heading_hash
        or heading.get("level") != metadata.get("headingLevel")
        or section.get("headingHash") != heading_hash
        or section.get("headingLevel") != metadata.get("headingLevel")
    ):
        _fail(
            code,
            f"{label} metadata heading is invalid",
            trace=trace,
            event_index=event_index,
        )
    if (
        metadata.get("isFinal") is not True
        or metadata.get("index") != heading_index
        or heading_index != len(headings) - 1
        or section_index != len(sections) - 1
    ):
        _fail(
            code,
            f"{label} metadata must follow business content as the final section",
            trace=trace,
            event_index=event_index,
        )
    if metadata.get("compact") is not True or metadata.get("hasTable") is True:
        _fail(
            code,
            f"{label} metadata must use the compact non-table footer",
            trace=trace,
            event_index=event_index,
        )


def assert_stage_trace(
    trace: dict[str, Any],
    dom_trace: dict[str, Any],
    *,
    expected_next_stage_id: str | None,
) -> StageTraceResult:
    if trace.get("observerError"):
        _fail(
            "SSE_TRUNCATED",
            f"transport observer failed: {trace['observerError']}",
            trace=trace,
        )
    events = trace.get("events", [])
    event_types = tuple(str(event.get("type")) for event in events)
    if not event_types or event_types[0] != "run_started":
        _fail("SSE_INVALID", "stream must start with run_started", trace=trace)
    if event_types[-1:] != ("done",):
        _fail("SSE_TRUNCATED", "stream must terminate with done", trace=trace)
    if event_types.count("run_started") != 1:
        _fail("SSE_INVALID", "stream must contain one run_started", trace=trace)
    if "error" in event_types:
        index = event_types.index("error")
        error = events[index]
        _fail(
            str(error.get("code") or "LLM_ERROR"),
            "stream returned a terminal error",
            trace=trace,
            event_index=index,
        )
    turn_indexes = [
        index
        for index, event_type in enumerate(event_types)
        if event_type == "agent_turn"
    ]
    if turn_indexes != [len(events) - 2]:
        _fail(
            "SSE_INVALID",
            "stream must contain one agent_turn after every delta and before done",
            trace=trace,
        )

    attempts = [event.get("attempt") for event in events]
    if any(not isinstance(attempt, int) or attempt < 0 for attempt in attempts):
        _fail("SSE_INVALID", "every event must identify its retry attempt", trace=trace)
    if attempts != sorted(attempts):
        _fail("SSE_INVALID", "retry attempt numbers must be monotonic", trace=trace)
    retry_count = event_types.count("agent_retry")
    final_attempt = attempts[-1]
    if final_attempt != retry_count:
        _fail("SSE_INVALID", "retry attempt count is inconsistent", trace=trace)

    indexed_deltas = [
        (index, event)
        for index, event in enumerate(events)
        if event.get("type") == "agent_delta" and event.get("attempt") == final_attempt
    ]
    chat_deltas = [
        (index, summary)
        for index, event in indexed_deltas
        if (summary := _summary(event, "chat")) is not None
    ]
    artifact_deltas = [
        (index, summary)
        for index, event in indexed_deltas
        if (summary := _summary(event, "artifact")) is not None
    ]
    if not chat_deltas or chat_deltas[0][1].get("length", 0) < 12:
        _fail(
            "CONTRACT_VALIDATION_FAILED",
            "stream requires a meaningful natural chat delta",
            trace=trace,
        )
    if (
        len(artifact_deltas) < 2
        or len({summary["hash"] for _, summary in artifact_deltas}) < 2
    ):
        _fail(
            "CONTRACT_VALIDATION_FAILED",
            "stream requires multiple distinct partial artifact deltas",
            trace=trace,
        )
    if chat_deltas[0][0] >= artifact_deltas[0][0]:
        _fail(
            "DOM_NOT_MONOTONIC",
            "stream requires chat before artifact",
            trace=trace,
        )
    _assert_monotonic_summaries(
        [summary for _, summary in chat_deltas],
        label="chat",
        code="CONTRACT_VALIDATION_FAILED",
        trace=trace,
    )
    _assert_monotonic_summaries(
        [summary for _, summary in artifact_deltas],
        label="artifact",
        code="CONTRACT_VALIDATION_FAILED",
        trace=trace,
        enforce_section_hashes=True,
        require_business_section=True,
    )

    final_event = events[turn_indexes[0]]
    final_artifact = _summary(final_event, "artifact")
    final_chat = _summary(final_event, "chat")
    if final_artifact is None or final_chat is None:
        _fail(
            "CONTRACT_VALIDATION_FAILED",
            "agent_turn must contain chat and final artifact summaries",
            trace=trace,
        )
    _assert_monotonic_summaries(
        [chat_deltas[-1][1], final_chat],
        label="final chat",
        code="CONTRACT_VALIDATION_FAILED",
        trace=trace,
    )
    _assert_monotonic_summaries(
        [artifact_deltas[-1][1], final_artifact],
        label="final artifact",
        code="CONTRACT_VALIDATION_FAILED",
        trace=trace,
        enforce_section_hashes=True,
        require_business_section=True,
    )
    requests_next_stage = final_event.get("requestsNextStage")
    target_stage_id = final_event.get("targetStageId")
    if expected_next_stage_id is None:
        if requests_next_stage is not False or target_stage_id is not None:
            _fail(
                "INVALID_STAGE_TRANSITION",
                "final stage must not request a transition",
                trace=trace,
            )
    elif requests_next_stage is not True or target_stage_id != expected_next_stage_id:
        _fail(
            "INVALID_STAGE_TRANSITION",
            f"agent_turn must request immediate next stage {expected_next_stage_id}",
            trace=trace,
        )

    request_id = str(trace.get("request", {}).get("requestId") or "")
    if not request_id or dom_trace.get("requestId") != request_id:
        _fail(
            "DOM_NOT_MONOTONIC",
            "network and DOM evidence must share requestId",
            trace=trace,
        )
    dom_events = dom_trace.get("events", [])
    if any(
        not isinstance(event.get("attempt"), int) or event["attempt"] < 0
        for event in dom_events
    ):
        _fail(
            "DOM_NOT_MONOTONIC",
            "every DOM observation must identify its retry attempt",
            trace=trace,
        )
    dom_events = [
        event for event in dom_events if event.get("attempt") == final_attempt
    ]
    first_chat_index = next(
        (
            index
            for index, event in enumerate(dom_events)
            if event.get("kind") == "chat" and event.get("length", 0) >= 12
        ),
        None,
    )
    first_artifact_index = next(
        (
            index
            for index, event in enumerate(dom_events)
            if event.get("kind") == "artifact"
        ),
        None,
    )
    if first_chat_index is None or first_artifact_index is None:
        _fail(
            "DOM_NOT_MONOTONIC",
            "browser did not observe chat and artifact DOM states",
            trace=trace,
        )
    if first_chat_index >= first_artifact_index:
        _fail(
            "DOM_NOT_MONOTONIC",
            "browser must commit new chat before artifact",
            trace=trace,
        )
    dom_artifacts = [event for event in dom_events if event.get("kind") == "artifact"]
    if len({event.get("hash") for event in dom_artifacts}) < 2:
        _fail(
            "DOM_NOT_MONOTONIC",
            "browser requires multiple distinct artifact DOM states",
            trace=trace,
        )
    dom_chats = [event for event in dom_events if event.get("kind") == "chat"]
    _assert_monotonic_summaries(
        dom_chats,
        label="DOM chat",
        code="DOM_NOT_MONOTONIC",
        trace=trace,
        enforce_length=False,
    )
    if (
        not dom_chats
        or dom_chats[-1].get("hash") != final_chat.get("hash")
        or dom_chats[-1].get("length") != final_chat.get("length")
    ):
        _fail(
            "DOM_NOT_MONOTONIC",
            "final DOM chat source summary does not match the terminal chat",
            trace=trace,
        )
    _assert_monotonic_summaries(
        dom_artifacts,
        label="DOM artifact",
        code="DOM_NOT_MONOTONIC",
        trace=trace,
        enforce_length=False,
        enforce_section_hashes=True,
        require_business_section=True,
    )
    if (
        not dom_artifacts
        or dom_artifacts[-1].get("hash") != final_artifact.get("hash")
        or dom_artifacts[-1].get("length") != final_artifact.get("length")
    ):
        _fail(
            "DOM_NOT_MONOTONIC",
            "final DOM artifact source summary does not match the terminal artifact",
            trace=trace,
        )

    run_id = events[0].get("runId")
    first_heading = next(iter(final_artifact.get("headings", [])), {})
    first_heading_hash = (
        first_heading.get("hash") if isinstance(first_heading, dict) else None
    )
    if (
        not isinstance(run_id, str)
        or not run_id
        or not isinstance(first_heading_hash, str)
        or DIGEST_PATTERN.fullmatch(first_heading_hash) is None
    ):
        _fail(
            "SSE_INVALID",
            "run_started and final artifact identity are incomplete",
            trace=trace,
        )
    return StageTraceResult(
        run_id=run_id,
        request_id=request_id,
        event_types=event_types,
        artifact_delta_count=len(artifact_deltas),
        artifact_hash=str(final_artifact["hash"]),
        first_heading=first_heading_hash,
        retry_count=retry_count,
    )


def assert_restored_artifact(
    dom_summary: dict[str, Any],
    *,
    snapshot_content: str,
    run_id: str,
) -> None:
    expected_hash = text_digest(snapshot_content)
    expected_length = len(snapshot_content)
    if (
        dom_summary.get("hash") != expected_hash
        or dom_summary.get("length") != expected_length
    ):
        _fail(
            "RUN_SNAPSHOT_MISSING",
            "restored DOM artifact does not match persisted snapshot content",
            details={
                "runId": run_id,
                "artifactHash": dom_summary.get("hash"),
                "currentHash": expected_hash,
                "currentLength": dom_summary.get("length"),
            },
        )


def assert_restored_assistant_messages(
    dom_summaries: list[dict[str, Any]],
    *,
    snapshot_messages: list[dict[str, Any]],
    run_id: str,
) -> None:
    expected = [
        {"hash": text_digest(content), "length": len(content)}
        for message in snapshot_messages
        if message.get("role") == "assistant"
        and isinstance((content := message.get("content")), str)
        and content
    ]
    actual = [
        {"hash": summary.get("hash"), "length": summary.get("length")}
        for summary in dom_summaries
        if isinstance(summary, dict)
    ]
    if len(actual) != len(dom_summaries) or actual != expected:
        _fail(
            "RUN_SNAPSHOT_MISSING",
            "restored assistant message history does not match persisted snapshot",
            details={
                "runId": run_id,
                "expectedAssistantCount": len(expected),
                "restoredAssistantCount": len(actual),
            },
        )


def assert_workflow_run_ids(run_ids: tuple[str, ...]) -> str:
    if not run_ids:
        _fail("RUN_SNAPSHOT_MISSING", "workflow did not produce a runId")
    if len(set(run_ids)) != 1:
        _fail(
            "RUN_SNAPSHOT_MISSING",
            f"workflow must reuse one runId across stages, got {run_ids}",
        )
    return run_ids[0]


def assert_snapshot(
    snapshot: dict[str, Any],
    *,
    run_id: str,
    workflow_id: str,
    current_stage_id: str,
    expected_stage_ids: tuple[str, ...],
    expected_turn_count: int,
    final_artifact_hash: str,
) -> SnapshotResult:
    run = snapshot.get("run", {})
    if (
        run.get("id") != run_id
        or run.get("workflowId") != workflow_id
        or run.get("currentStageId") != current_stage_id
    ):
        _fail(
            "RUN_SNAPSHOT_MISSING",
            "persisted run identity does not match the completed turn",
            details={"runId": run_id},
        )

    messages = snapshot.get("messages", [])
    expected_roles = ["user", "assistant"] * expected_turn_count
    if [message.get("role") for message in messages] != expected_roles:
        _fail(
            "RUN_SNAPSHOT_MISSING",
            "persisted workflow message history is incomplete",
            details={"runId": run_id},
        )
    if [message.get("sequenceIndex") for message in messages] != list(
        range(1, len(messages) + 1)
    ):
        _fail(
            "RUN_SNAPSHOT_MISSING",
            "persisted message sequenceIndex values are not contiguous",
            details={"runId": run_id},
        )

    artifacts = snapshot.get("artifacts", [])
    artifact_by_stage = {
        artifact.get("stageId"): artifact
        for artifact in artifacts
        if isinstance(artifact, dict)
    }
    if set(artifact_by_stage) != set(expected_stage_ids):
        _fail(
            "RUN_SNAPSHOT_MISSING",
            "persisted workflow artifacts do not match completed stages",
            details={"runId": run_id},
        )
    for stage_id in expected_stage_ids:
        artifact = artifact_by_stage[stage_id]
        if not isinstance(artifact.get("artifactData"), dict):
            _fail(
                "RUN_SNAPSHOT_MISSING",
                f"persisted artifactData is missing for {stage_id}",
                details={"runId": run_id},
            )
        version_number = artifact.get("versionNumber")
        if not isinstance(version_number, int) or version_number < 1:
            _fail(
                "RUN_SNAPSHOT_MISSING",
                f"persisted artifact version is invalid for {stage_id}",
                details={"runId": run_id},
            )
    current_artifact = artifact_by_stage[current_stage_id]
    current_content = current_artifact.get("content")
    if (
        not isinstance(current_content, str)
        or text_digest(current_content) != final_artifact_hash
    ):
        _fail(
            "RUN_SNAPSHOT_MISSING",
            "persisted current artifact does not match agent_turn",
            details={"runId": run_id},
        )

    context_summaries = snapshot.get("contextSummaries", [])
    summarized_stages = {
        summary.get("sourceStageId")
        for summary in context_summaries
        if isinstance(summary, dict) and summary.get("content")
    }
    if not set(expected_stage_ids) <= summarized_stages:
        _fail(
            "RUN_SNAPSHOT_MISSING",
            "persisted context summaries do not cover completed stages",
            details={"runId": run_id},
        )
    return SnapshotResult(
        version_number=int(current_artifact["versionNumber"]),
        message_count=len(messages),
        artifact_stage_ids=expected_stage_ids,
        context_summary_count=len(context_summaries),
    )


def assert_observability(
    payload: dict[str, Any],
    *,
    run_id: str,
    workflow_id: str,
    stage_id: str,
    expected_retry_count: int,
) -> str:
    totals = payload.get("totals", {})
    if totals.get("turns", 0) < 1 or totals.get("failedTurns") != 0:
        _fail(
            "RUN_SNAPSHOT_MISSING",
            "runtime observability does not contain a successful turn metric",
            details={"runId": run_id},
        )
    metric = next(
        (
            item
            for item in payload.get("recentTurns", [])
            if item.get("runId") == run_id
            and item.get("workflowId") == workflow_id
            and item.get("stageId") == stage_id
        ),
        None,
    )
    if metric is None or metric.get("status") != "success":
        _fail(
            "RUN_SNAPSHOT_MISSING",
            "successful turn metric is missing for the completed stage",
            details={"runId": run_id},
        )
    if metric.get("contractRetryCount") != expected_retry_count:
        _fail(
            "RUN_SNAPSHOT_MISSING",
            "turn metric retry count does not match SSE evidence",
            details={"runId": run_id},
        )
    return str(metric["status"])
