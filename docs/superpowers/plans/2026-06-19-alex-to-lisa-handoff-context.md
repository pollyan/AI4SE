# Alex To Lisa Handoff Context Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add configuration-driven Alex-to-Lisa handoff context export.

**Architecture:** Store handoff metadata in the shared workflow manifest. Add backend helpers to load and validate handoffs, plus a `workflow_handoffs.py` service that uses `get_run_snapshot`. Expose `GET /api/agent/runs/{runId}/handoffs` as a read-only endpoint.

**Tech Stack:** Python 3.11, Flask, pytest.

---

## File Structure

- Modify: `tools/new-agents/workflow_manifest.json`
- Modify: `tools/new-agents/backend/workflow_manifest.py`
- Modify: `tools/new-agents/backend/tests/test_workflow_contract_sync.py`
- Create: `tools/new-agents/backend/workflow_handoffs.py`
- Create: `tools/new-agents/backend/tests/test_workflow_handoffs.py`
- Modify: `tools/new-agents/backend/routes.py`
- Modify: `tools/new-agents/backend/tests/test_agent_endpoint.py`
- Modify docs:
  - `docs/api-contracts.md`
  - `docs/ARCHITECTURE.md`
  - `docs/todos/new-agents-evolution.md`

## Task 1: RED Manifest And Service Tests

- [ ] Add manifest sync tests that expect handoff config and validate source/target workflow stages.
- [ ] Add service tests for `export_run_handoffs`.
- [ ] Run focused tests and confirm failure because handoffs are not configured and service does not exist.

## Task 2: GREEN Manifest And Service

- [ ] Add top-level `handoffs` to `workflow_manifest.json`.
- [ ] Add `get_workflow_handoffs()` to backend manifest loader.
- [ ] Implement `workflow_handoffs.py`.
- [ ] Run service and manifest tests.

## Task 3: Endpoint

- [ ] Add `GET /api/agent/runs/<run_id>/handoffs`.
- [ ] Add endpoint tests.
- [ ] Run endpoint and handoff tests.

## Task 4: Verification And Docs

- [ ] Update architecture/API/todo docs.
- [ ] Run backend full tests.
- [ ] Run `git diff --check`.
