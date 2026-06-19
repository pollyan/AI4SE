# Lisa Test Assets Export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a read-only backend export for structured Lisa test assets derived from persisted `TEST_DESIGN/CASES` artifacts.

**Architecture:** Implement a focused Markdown table parser in `test_assets.py`, backed by `get_run_snapshot`. Expose it through `GET /api/agent/runs/{runId}/test-assets` without changing the typed SSE runtime or frontend state.

**Tech Stack:** Python 3.11, Flask, pytest.

---

## File Structure

- Create: `tools/new-agents/backend/test_assets.py`
  - Parse CASES artifact Markdown into test cases and coverage trace.
- Create: `tools/new-agents/backend/tests/test_test_assets.py`
  - Service-level tests for parsing and explicit failures.
- Modify: `tools/new-agents/backend/routes.py`
  - Add read-only export endpoint.
- Modify: `tools/new-agents/backend/tests/test_agent_endpoint.py`
  - Endpoint tests.
- Modify docs:
  - `docs/api-contracts.md`
  - `docs/ARCHITECTURE.md`
  - `docs/todos/new-agents-evolution.md`

## Task 1: RED Service Tests

- [ ] Write tests for successful CASES artifact parsing, missing CASES artifact, and non-TEST_DESIGN rejection.
- [ ] Run `cd tools/new-agents/backend && python3 -m pytest tests/test_test_assets.py -q`.
- [ ] Expected: FAIL because `test_assets.py` does not exist.

## Task 2: GREEN Service Implementation

- [ ] Implement `export_lisa_test_assets(run_id)`.
- [ ] Parse Markdown pipe tables with exact header mapping.
- [ ] Raise `ValueError` with clear messages for unsupported runs or missing assets.
- [ ] Run `cd tools/new-agents/backend && python3 -m pytest tests/test_test_assets.py -q`.
- [ ] Expected: PASS.

## Task 3: Endpoint

- [ ] Add `GET /api/agent/runs/<run_id>/test-assets`.
- [ ] Add endpoint tests for success and missing CASES artifact.
- [ ] Run `cd tools/new-agents/backend && python3 -m pytest tests/test_agent_endpoint.py tests/test_test_assets.py -q`.
- [ ] Expected: PASS.

## Task 4: Verification And Docs

- [ ] Run backend focused tests: `cd tools/new-agents/backend && python3 -m pytest tests/test_test_assets.py tests/test_agent_endpoint.py tests/test_run_persistence.py -q`.
- [ ] Run backend full tests: `cd tools/new-agents/backend && python3 -m pytest -q`.
- [ ] Update architecture/API/todo docs.
- [ ] Run `git diff --check`.
