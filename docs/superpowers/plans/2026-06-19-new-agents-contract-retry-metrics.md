# New Agents Contract Retry Metrics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Record real exhausted structured output retry counts in Agent Runtime turn metrics.

**Architecture:** Add retry-count parsing in `stream_services.py` and pass the parsed count into the existing metric recorder for schema validation failure paths. Keep persistence and API schemas unchanged.

**Tech Stack:** Python 3.11, pytest, Flask backend service tests, Markdown docs.

---

### Task 1: Stream Metric Retry Count

**Files:**
- Modify: `tools/new-agents/backend/stream_services.py`
- Modify: `tools/new-agents/backend/tests/test_stream_services.py`

- [x] **Step 1: Write the failing test**

Add `test_stream_agent_run_events_records_schema_retry_count_from_runtime_error`. Mock `runtime.stream_turn` to raise `AgentRuntimeSchemaError("Exceeded maximum output retries (3)")`, run `stream_agent_run_events`, assert the emitted error code is `SCHEMA_VALIDATION_FAILED`, and assert the recorded metric has `contract_retry_count == 3`.

- [x] **Step 2: Run test to verify RED**

Run: `cd tools/new-agents/backend && python3 -m pytest tests/test_stream_services.py::test_stream_agent_run_events_records_schema_retry_count_from_runtime_error -q`

Expected: FAIL because the metric currently records `contract_retry_count == 0`.

- [x] **Step 3: Implement retry count parsing**

Add a helper that parses `Exceeded maximum output retries (N)` from exception text and returns `N`, otherwise `0`. Extend `record_metric` to accept `contract_retry_count` and pass it into `_record_turn_metric`.

- [x] **Step 4: Run focused stream service tests**

Run: `cd tools/new-agents/backend && python3 -m pytest tests/test_stream_services.py::test_stream_agent_run_events_records_schema_retry_count_from_runtime_error tests/test_stream_services.py::test_stream_agent_run_events_records_turn_through_persistence_adapter tests/test_stream_services.py::test_stream_agent_run_events_records_error_turn_metric -q`

Expected: all selected stream service metric tests pass.

### Task 2: Todo Record And Verification

**Files:**
- Modify: `docs/todos/new-agents-evolution.md`
- Modify: `docs/superpowers/plans/2026-06-19-new-agents-contract-retry-metrics.md`

- [x] **Step 1: Update progress**

Record that schema/contract retry exhaustion now records the parsed retry count into `agent_run_turn_metrics.contract_retry_count`.

- [x] **Step 2: Run verification**

Run: `cd tools/new-agents/backend && python3 -m pytest tests/test_stream_services.py tests/test_agent_endpoint.py::test_agent_observability_endpoint_returns_runtime_turn_summary -q`

Expected: stream service behavior and observability endpoint summary tests pass.

- [x] **Step 3: Run whitespace check**

Run: `git diff --check`

Expected: no whitespace errors.
