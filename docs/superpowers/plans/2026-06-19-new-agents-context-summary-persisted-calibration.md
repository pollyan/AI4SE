# New Agents Context Summary Persisted Calibration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist frontend context summary calibration back to `agent_context_summaries` so the server context builder uses corrected summaries.

**Architecture:** Add a tuple-based PATCH API on persisted runs, backed by `AgentContextSummary`'s existing unique key. The frontend calls the API from the existing Header modal and updates Zustand only after the server returns the saved summary.

**Tech Stack:** Flask, SQLAlchemy, pytest, React, Zustand, TypeScript, Vitest.

---

## File Structure

- Modify `tools/new-agents/backend/run_persistence.py`: add strict payload validation and `update_context_summary()`.
- Modify `tools/new-agents/backend/routes.py`: add `PATCH /api/agent/runs/<run_id>/context-summaries`.
- Modify `tools/new-agents/backend/tests/test_run_persistence.py`: repository RED/GREEN tests.
- Modify `tools/new-agents/backend/tests/test_agent_endpoint.py`: endpoint RED/GREEN tests.
- Modify `tools/new-agents/frontend/src/services/runSnapshotService.ts`: add `updateRunContextSummary()`.
- Modify `tools/new-agents/frontend/src/services/__tests__/runSnapshotService.test.ts`: service RED/GREEN tests.
- Modify `tools/new-agents/frontend/src/components/Header.tsx`: persist summary saves.
- Modify `tools/new-agents/frontend/src/components/__tests__/Header.test.tsx`: Header RED/GREEN tests.
- Modify `docs/todos/new-agents-evolution.md`: record the completed slice and remaining permission/decision-form gaps.

## Task 1: Backend Repository

- [ ] Step 1: Write failing tests for updating an existing summary and rejecting a missing summary.
- [ ] Step 2: Run `cd tools/new-agents/backend && python3 -m pytest tests/test_run_persistence.py -q` and verify RED.
- [ ] Step 3: Implement `update_context_summary(run_id, patch)` with strict keys, string validation, nonblank content, existing-run check, existing-summary check, and commit.
- [ ] Step 4: Re-run the same pytest command and verify GREEN.

## Task 2: Backend Endpoint

- [ ] Step 1: Write failing endpoint tests for successful PATCH, invalid payload, and missing summary.
- [ ] Step 2: Run `cd tools/new-agents/backend && python3 -m pytest tests/test_agent_endpoint.py -q` and verify RED.
- [ ] Step 3: Wire the route in `routes.py`, mapping validation errors to 400 and missing run/summary to 404.
- [ ] Step 4: Re-run endpoint tests and verify GREEN.

## Task 3: Frontend Service And Header

- [ ] Step 1: Write failing service test for PATCH URL/body/response parsing.
- [ ] Step 2: Write failing Header test asserting save calls the service and updates store from the server response.
- [ ] Step 3: Run `cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/runSnapshotService.test.ts src/components/__tests__/Header.test.tsx` and verify RED.
- [ ] Step 4: Implement `updateRunContextSummary()` and update Header save flow with error display.
- [ ] Step 5: Re-run frontend tests and verify GREEN.

## Task 4: Verification And Todo Record

- [ ] Step 1: Run focused backend verification:

```bash
cd tools/new-agents/backend && python3 -m pytest tests/test_run_persistence.py tests/test_agent_endpoint.py tests/test_context_builder.py -q
```

- [ ] Step 2: Run focused frontend verification:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/runSnapshotService.test.ts src/components/__tests__/Header.test.tsx src/__tests__/store.test.ts
cd tools/new-agents/frontend && npm run lint
git diff --check
```

- [ ] Step 3: Update `docs/todos/new-agents-evolution.md` with completed evidence and remaining gaps.

## Self-Review

- Spec coverage: tasks cover repository, API, frontend service, Header integration, verification and todo record.
- Placeholder scan: no placeholder implementation steps remain.
- Type consistency: frontend service uses `AgentRunSnapshotContextSummary` tuple fields and returns the same summary shape parsed from snapshots.
