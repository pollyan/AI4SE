# New Agents Run Snapshot API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose a read-only HTTP snapshot for persisted New Agents runs.

**Architecture:** Add a route in `routes.py` that delegates to `run_persistence.get_run_snapshot`. Keep all persistence reads in the repository, and return JSON errors through the existing response helper.

**Tech Stack:** Flask, Flask-SQLAlchemy, pytest.

---

## File Structure

- Modify: `tools/new-agents/backend/routes.py`
  - Add `GET /api/agent/runs/<run_id>`.
- Modify: `tools/new-agents/backend/tests/test_agent_endpoint.py`
  - Add snapshot success and not-found tests.
- Modify docs:
  - `docs/api-contracts.md`
  - `docs/todos/new-agents-evolution.md`
  - `docs/TESTING.md`

## Task 1: Snapshot Endpoint Tests

- [ ] **Step 1: Add failing endpoint tests**

Create a stream run, fetch `GET /api/agent/runs/<runId>`, and assert run/messages/artifacts shape. Add a 404 test for an unknown run ID.

- [ ] **Step 2: Run endpoint tests**

Run: `cd tools/new-agents/backend && python3 -m pytest tests/test_agent_endpoint.py -q`
Expected: FAIL because the route does not exist yet.

## Task 2: Route Implementation

- [ ] **Step 1: Add route**

Implement `agent_run_snapshot(run_id)` in `routes.py`, returning `jsonify(get_run_snapshot(run_id))`.

- [ ] **Step 2: Map unknown run ID**

Catch `ValueError` from the repository and return `json_error_response(str(e), 404)`.

- [ ] **Step 3: Run endpoint tests**

Run: `cd tools/new-agents/backend && python3 -m pytest tests/test_agent_endpoint.py -q`
Expected: PASS.

## Task 3: Verification And Docs

- [ ] **Step 1: Run backend focused tests**

Run: `cd tools/new-agents/backend && python3 -m pytest tests/test_agent_endpoint.py tests/test_run_persistence.py -q`
Expected: PASS.

- [ ] **Step 2: Run backend full tests**

Run: `cd tools/new-agents/backend && python3 -m pytest -q`
Expected: PASS.

- [ ] **Step 3: Run diff whitespace check**

Run: `git diff --check`
Expected: no output and exit code 0.

- [ ] **Step 4: Update docs and todo**

Record the new snapshot API and remaining non-goals.
