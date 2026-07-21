from __future__ import annotations

import json
import os
import re
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

SENSITIVE_KEY = re.compile(
    r"api[_-]?key|authorization|secret|token|password",
    re.IGNORECASE,
)
SAFE_FILE_PART = re.compile(r"[^A-Za-z0-9_.-]+")
SAFE_TOKEN = re.compile(r"[A-Za-z0-9_.:-]{1,256}")
SAFE_ERROR_CODE = re.compile(r"[A-Z][A-Z0-9_]{0,63}")
SAFE_HASH = re.compile(r"sha256-[0-9a-f]{64}")
SENSITIVE_VALUE = re.compile(
    r"api.?key|authorization|bearer|password|secret|token|sk[-_]",
    re.IGNORECASE,
)
SAFE_EVENT_TYPES = {
    "run_started",
    "agent_retry",
    "agent_delta",
    "agent_turn",
    "error",
    "done",
}
SAFE_OBSERVER_ERRORS = {"sse_incomplete_frame", "sse_observer_failed"}
SAFE_MONOTONIC_REASONS = {
    "active_tail_rewrite",
    "duplicate_heading",
    "heading_order",
    "network_order_rewind",
    "source_length_rewind",
    "source_prefix_rewrite",
    "stable_section_rewrite",
}
SAFE_ASSERTION_STEPS = {
    "dom_observer_finalize",
    "next_stage_confirmation_click",
    "next_stage_confirmation_visible",
    "restore_artifact_hash",
    "restore_artifact_length",
    "restore_assistant_messages",
    "run_snapshot_fetch",
    "stream_terminal_wait",
    "terminal_artifact_dom_sync",
}

ERROR_CATEGORIES = {
    "LLM_ERROR": "provider",
    "DEFAULT_LLM_CONFIG_MISSING": "provider",
    "SCHEMA_VALIDATION_FAILED": "schema",
    "REQUEST_VALIDATION_FAILED": "schema",
    "CONTRACT_VALIDATION_FAILED": "renderer",
    "VISUAL_VALIDATION_FAILED": "renderer",
    "SSE_TRUNCATED": "transport",
    "SSE_INVALID": "transport",
    "DOM_NOT_MONOTONIC": "frontend",
    "BROWSER_ASSERTION_FAILED": "frontend",
    "REPORT_WRITE_FAILED": "infrastructure",
    "RUN_SNAPSHOT_MISSING": "persistence",
    "PERSISTENCE_FAILED": "persistence",
    "PERSISTENCE_CONFLICT": "persistence",
    "REQUEST_IN_PROGRESS": "persistence",
    "REQUEST_IDENTITY_CONFLICT": "persistence",
    "INVALID_STAGE_TRANSITION": "transition",
    "TIMEOUT": "timeout",
    "STACK_STARTUP_FAILED": "infrastructure",
    "AGENT_RUNTIME_UNAVAILABLE": "infrastructure",
}


def classify_error(code: str) -> str:
    return ERROR_CATEGORIES.get(code, "unknown")


def _safe_token(value: Any) -> str | None:
    if not isinstance(value, str) or SAFE_TOKEN.fullmatch(value) is None:
        return None
    if SENSITIVE_VALUE.search(value):
        return None
    return value


def _safe_diagnostic(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, Mapping):
        return None
    diagnostic: dict[str, Any] = {}
    for key in ("phase", "fieldPath", "validator"):
        token = _safe_token(value.get(key))
        if token is not None:
            diagnostic[key] = token
    if isinstance(value.get("retryable"), bool):
        diagnostic["retryable"] = value["retryable"]
    return diagnostic or None


def _safe_coordinates(value: Mapping[str, Any] | None) -> dict[str, Any]:
    if value is None:
        return {}
    coordinates: dict[str, Any] = {}
    for key in ("workflowId", "stageId", "runId", "requestId"):
        token = _safe_token(value.get(key))
        if token is not None:
            coordinates[key] = token
    for key in (
        "eventIndex",
        "retryCount",
        "previousLength",
        "currentLength",
    ):
        number = value.get(key)
        if isinstance(number, int) and not isinstance(number, bool) and number >= 0:
            coordinates[key] = number
    event_types = value.get("eventTypes")
    if isinstance(event_types, (list, tuple)):
        safe_event_types = [
            event_type
            for event_type in event_types
            if isinstance(event_type, str) and event_type in SAFE_EVENT_TYPES
        ]
        if safe_event_types:
            coordinates["eventTypes"] = safe_event_types
    for key in (
        "artifactHash",
        "previousHash",
        "currentHash",
        "currentPrefixHash",
    ):
        digest = value.get(key)
        if isinstance(digest, str) and SAFE_HASH.fullmatch(digest):
            coordinates[key] = digest
    observer_error = value.get("observerError")
    if observer_error in SAFE_OBSERVER_ERRORS:
        coordinates["observerError"] = observer_error
    monotonic_reason = value.get("monotonicReason")
    if monotonic_reason in SAFE_MONOTONIC_REASONS:
        coordinates["monotonicReason"] = monotonic_reason
    assertion_step = value.get("assertionStep")
    if assertion_step in SAFE_ASSERTION_STEPS:
        coordinates["assertionStep"] = assertion_step
    diagnostic = _safe_diagnostic(value.get("diagnostic"))
    if diagnostic is not None:
        coordinates["diagnostic"] = diagnostic
    return coordinates


def build_failure_evidence(
    error: BaseException,
    *,
    scope: str,
    workflow_id: str | None,
    stage_id: str | None,
    trace_summary: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    code = getattr(error, "code", None)
    if not isinstance(code, str) or SAFE_ERROR_CODE.fullmatch(code) is None:
        code = "TIMEOUT" if type(error).__name__ == "TimeoutError" else "UNKNOWN"
    details = getattr(error, "details", {})
    if not isinstance(details, Mapping):
        details = {}
    coordinates = {
        **_safe_coordinates(trace_summary),
        **_safe_coordinates(details),
    }
    return {
        "scope": scope,
        "workflowId": _safe_token(workflow_id),
        "stageId": _safe_token(stage_id),
        "status": "FAIL",
        "errorCode": code,
        "errorCategory": classify_error(code),
        "reason": f"{code}: functional gate failed",
        **coordinates,
    }


def _redact_string(value: str, secrets: tuple[str, ...]) -> str:
    redacted = value
    for secret in sorted(set(secrets), key=len, reverse=True):
        if secret:
            redacted = redacted.replace(secret, "<redacted>")
    return redacted


def redact(value: Any, *, secrets: Iterable[str] = ()) -> Any:
    normalized_secrets = tuple(secret for secret in secrets if secret)
    if isinstance(value, Mapping):
        return {
            str(key): (
                "<redacted>"
                if SENSITIVE_KEY.search(str(key))
                else redact(item, secrets=normalized_secrets)
            )
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact(item, secrets=normalized_secrets) for item in value]
    if isinstance(value, str):
        return _redact_string(value, normalized_secrets)
    return value


def write_report(
    path: Path,
    evidence: Mapping[str, Any],
    *,
    secrets: Iterable[str] = (),
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = redact(dict(evidence), secrets=secrets)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def report_path(
    root: Path,
    scope: str,
    identifier: str,
) -> Path:
    safe_scope = SAFE_FILE_PART.sub("-", scope).strip("-")
    safe_identifier = SAFE_FILE_PART.sub("-", identifier).strip("-")
    evidence_value = os.environ.get("NEW_AGENTS_REAL_EVIDENCE_DIR", "").strip()
    if not evidence_value:
        return (
            root
            / "test-results"
            / "new-agents-real"
            / f"{safe_scope}-{safe_identifier}.json"
        )
    evidence_root = Path(evidence_value).resolve()
    allowed_root = (root / "test-results" / "pre-push").resolve()
    if (
        not evidence_root.is_absolute()
        or not evidence_root.is_relative_to(allowed_root)
        or evidence_root.name != "real-e2e"
    ):
        raise ValueError(
            "real-model evidence directory is outside controlled pre-push output"
        )
    return evidence_root / f"{safe_scope}-{safe_identifier}.json"
