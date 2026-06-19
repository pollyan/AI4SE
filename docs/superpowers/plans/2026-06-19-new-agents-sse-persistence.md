# New Agents SSE Persistence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist `/api/agent/runs/stream` turns into the generic run/message/artifact version repository while keeping the typed SSE path shared and backward compatible.

**Architecture:** Add optional `runId` to request parsing, optional `runId` to `run_started`, and a persistence adapter injected by the route into `stream_agent_run_events`. The service remains testable without Flask/SQLAlchemy because persistence is passed through a small protocol-shaped object.

**Tech Stack:** Python 3.11, Flask, Flask-SQLAlchemy, Pydantic, pytest.

---

## File Structure

- Modify: `tools/new-agents/backend/request_schemas.py`
  - Add optional `runId` parsing and blank rejection.
- Modify: `tools/new-agents/backend/sse_schemas.py`
  - Add optional `runId` to `RunStartedEvent`.
- Modify: `tools/new-agents/backend/sse_encoder.py`
  - Emit Pydantic aliases so `runId` is serialized as camelCase.
- Create: `tools/new-agents/backend/workflow_manifest.py`
  - Load workflow agent ownership from `tools/new-agents/workflow_manifest.json`.
- Modify: `tools/new-agents/backend/run_persistence.py`
  - Add helper for creating or reusing a run from stream request metadata.
- Modify: `tools/new-agents/backend/stream_services.py`
  - Accept optional persistence adapter and record turn side effects.
- Modify: `tools/new-agents/backend/routes.py`
  - Pass the real persistence adapter to the stream service.
- Modify tests:
  - `tools/new-agents/backend/tests/test_request_schemas.py`
  - `tools/new-agents/backend/tests/test_sse_encoder.py`
  - `tools/new-agents/backend/tests/test_stream_services.py`
  - `tools/new-agents/backend/tests/test_agent_endpoint.py`

## Task 1: Request And SSE Contract Tests

- [ ] **Step 1: Add failing request schema tests**

Add tests that `runId` is accepted and normalized, and blank `runId` raises `RequestValidationError("runId 不能为空")`.

- [ ] **Step 2: Add failing SSE schema/encoder test**

Add a test that `encode_sse_event(RunStartedEvent(run_id="run-123"))` emits `{"type":"run_started","runId":"run-123"}`.

- [ ] **Step 3: Run tests to verify failure**

Run: `cd tools/new-agents/backend && python3 -m pytest tests/test_request_schemas.py tests/test_sse_encoder.py -q`
Expected: FAIL because request and SSE schemas do not yet expose `runId`.

## Task 2: Stream Service Persistence Adapter Tests

- [ ] **Step 1: Add failing stream service adapter test**

Add a fake adapter test proving `stream_agent_run_events` calls `ensure_run`, `append_user_message`, `append_assistant_message`, and `record_artifact_version`, and emits `RunStartedEvent(run_id=...)`.

- [ ] **Step 2: Run test to verify failure**

Run: `cd tools/new-agents/backend && python3 -m pytest tests/test_stream_services.py -q`
Expected: FAIL because `stream_agent_run_events` does not accept a persistence adapter yet.

## Task 3: Endpoint Persistence Tests

- [ ] **Step 1: Add failing endpoint database side-effect test**

Add a route test that posts to `/api/agent/runs/stream`, reads `runId` from `run_started`, then checks database snapshot contains the user prompt, final assistant chat, and current artifact version.

- [ ] **Step 2: Run test to verify failure**

Run: `cd tools/new-agents/backend && python3 -m pytest tests/test_agent_endpoint.py -q`
Expected: FAIL because the endpoint does not create a persisted run.

## Task 4: Implementation

- [ ] **Step 1: Implement optional `runId` in request schema**

Normalize nonblank `runId` and store it as `run_id`.

- [ ] **Step 2: Implement `RunStartedEvent.runId` serialization**

Use a field alias and `model_dump(..., by_alias=True)` in the SSE encoder.

- [ ] **Step 3: Implement workflow manifest reader**

Expose `get_workflow_agent_id(workflow_id)` and raise a clear `ValueError` for unknown workflows.

- [ ] **Step 4: Implement persistence helper**

Create or reuse runs using request workflow/stage metadata and manifest `agentId`.

- [ ] **Step 5: Inject adapter into stream service from route**

Keep `persistence=None` as the default so existing pure service tests remain lightweight.

## Task 5: Verification And Docs

- [ ] **Step 1: Run focused backend tests**

Run: `cd tools/new-agents/backend && python3 -m pytest tests/test_request_schemas.py tests/test_sse_encoder.py tests/test_stream_services.py tests/test_agent_endpoint.py tests/test_run_persistence.py -q`
Expected: PASS.

- [ ] **Step 2: Run full backend tests**

Run: `cd tools/new-agents/backend && python3 -m pytest -q`
Expected: PASS, with existing external pytest-asyncio Python 3.14 warnings acceptable.

- [ ] **Step 3: Run diff whitespace check**

Run: `git diff --check`
Expected: no output and exit code 0.

- [ ] **Step 4: Update docs and todo**

Record the SSE persistence slice in `docs/todos/new-agents-evolution.md`, `docs/api-contracts.md`, `docs/ARCHITECTURE.md`, and `docs/TESTING.md`.
