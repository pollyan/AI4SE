# New Agents Manual Decision Entry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a standalone decision entry form that persists a decision summary for the current run and stage.

**Architecture:** Reuse `agent_context_summaries` and the existing `artifact/decision` summary consumed by `context_builder.py`. Add a small POST API and a Header modal form that calls it.

**Tech Stack:** Flask, SQLAlchemy, pytest, React, Zustand, TypeScript, Vitest.

---

## File Structure

- Modify `tools/new-agents/backend/run_persistence.py`: add `upsert_manual_decision_summary()`.
- Modify `tools/new-agents/backend/routes.py`: add `POST /agent/runs/<run_id>/context-summaries/decisions`.
- Modify `tools/new-agents/backend/tests/test_run_persistence.py`: add repository tests.
- Modify `tools/new-agents/backend/tests/test_agent_endpoint.py`: add endpoint tests.
- Modify `tools/new-agents/frontend/src/core/types.ts`: add store action to upsert a context summary.
- Modify `tools/new-agents/frontend/src/store.ts`: implement upsert action.
- Modify `tools/new-agents/frontend/src/services/runSnapshotService.ts`: add `createRunDecisionSummary()`.
- Modify `tools/new-agents/frontend/src/services/__tests__/runSnapshotService.test.ts`: add service test.
- Modify `tools/new-agents/frontend/src/components/Header.tsx`: add decision form.
- Modify `tools/new-agents/frontend/src/components/__tests__/Header.test.tsx`: add Header test.
- Modify `docs/todos/new-agents-evolution.md`: record progress and remaining lock/permission gaps.

## Task 1: Backend Decision Upsert

- [ ] Write failing repository tests for creating/updating a decision summary and rejecting invalid stage/content.
- [ ] Run `cd tools/new-agents/backend && python3 -m pytest tests/test_run_persistence.py -q` and verify RED.
- [ ] Implement `upsert_manual_decision_summary()`.
- [ ] Re-run the same command and verify GREEN.

## Task 2: Backend Endpoint

- [ ] Write failing endpoint tests for POST success and invalid payload.
- [ ] Run `cd tools/new-agents/backend && python3 -m pytest tests/test_agent_endpoint.py -q` and verify RED.
- [ ] Wire route in `routes.py`.
- [ ] Re-run endpoint tests and verify GREEN.

## Task 3: Frontend Service And Store

- [ ] Write failing service test for `createRunDecisionSummary()`.
- [ ] Write failing store test for upserting a new context summary.
- [ ] Run `cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/runSnapshotService.test.ts src/__tests__/store.test.ts` and verify RED.
- [ ] Implement service and store action.
- [ ] Re-run tests and verify GREEN.

## Task 4: Header Decision Form

- [ ] Write failing Header test for saving a new key decision.
- [ ] Run `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/Header.test.tsx` and verify RED.
- [ ] Implement form, success update, and error state.
- [ ] Re-run Header test and verify GREEN.

## Task 5: Final Verification

- [ ] Run backend focused verification:

```bash
cd tools/new-agents/backend && python3 -m pytest tests/test_run_persistence.py tests/test_agent_endpoint.py tests/test_context_builder.py -q
```

- [ ] Run frontend focused verification:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/runSnapshotService.test.ts src/__tests__/store.test.ts src/components/__tests__/Header.test.tsx
cd tools/new-agents/frontend && npm run lint
git diff --check
```

## Self-Review

- Spec coverage: repository, API, service, store, Header and todo update are covered.
- Placeholder scan: no placeholder implementation instructions remain.
- Type consistency: API and frontend both return `AgentRunSnapshotContextSummary`.
