# Run History Reuse Center Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade New Agents history from a restore-only list into a reuse center with filtering, preview, continue, and clone-as-new-run.

**Architecture:** Extend existing run persistence and route surfaces. Keep shared run/artifact/message/context summary models, existing snapshot restore, Header modal, and `runSnapshotService`. Clone creates a new active run by copying messages, current artifacts, and context summaries; it does not copy collaboration/audit/runtime metric records.

**Tech Stack:** Python 3.11, Flask, SQLAlchemy, pytest, React, TypeScript, Vitest.

---

## File Structure

- Modify: `tools/new-agents/backend/run_persistence.py`
- Modify: `tools/new-agents/backend/routes.py`
- Modify: `tools/new-agents/backend/tests/test_run_persistence.py`
- Modify: `tools/new-agents/backend/tests/test_agent_endpoint.py`
- Modify: `tools/new-agents/frontend/src/core/types.ts`
- Modify: `tools/new-agents/frontend/src/services/runSnapshotService.ts`
- Modify: `tools/new-agents/frontend/src/services/__tests__/runSnapshotService.test.ts`
- Modify: `tools/new-agents/frontend/src/components/Header.tsx`
- Modify: `tools/new-agents/frontend/src/components/__tests__/Header.test.tsx`
- Modify: `docs/todos/refactor/README.md`
- Modify: `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md`
- Modify: `docs/strategy/goal-mode-playbook.md`

## Task 1: Backend RED

- [x] Add persistence tests for `clone_agent_run` that expect a new active run with copied messages, current artifacts, and context summaries while leaving the source run unchanged.
- [x] Add list tests for `reuseStatus=ready|needs_artifact|failed` filtering.
- [x] Add endpoint tests for `POST /api/agent/runs/<run_id>/clone` and invalid `reuseStatus`.
- [x] Run focused backend tests and confirm failures are due to missing clone/filter behavior.

## Task 2: Backend GREEN

- [x] Implement `RUN_REUSE_STATUSES`, `_run_reuse_status`, `reuse_status` filtering, and `reuseStatus` in run list items.
- [x] Implement `clone_agent_run(source_run_id)` using existing models and `record_artifact_version` / `_upsert_context_summary` patterns.
- [x] Add `POST /api/agent/runs/<run_id>/clone` route returning `get_run_snapshot(new_run.id)`.
- [x] Run focused backend tests until green.

## Task 3: Frontend Service RED/GREEN

- [x] Extend `AgentRunListItem` with `reuseStatus`.
- [x] Add `RunReuseStatus` type.
- [x] Update `fetchRunList` to accept `reuseStatus`.
- [x] Add `cloneRun` service calling `POST /new-agents/api/agent/runs/<run_id>/clone`.
- [x] Update service tests for valid parsing, malformed `reuseStatus`, query param, and clone API.

## Task 4: Header Reuse Center RED/GREEN

- [x] Update Header tests to require reuse status filter buttons, selected run preview, continue action, clone action, and clone failure feedback.
- [x] Add state for selected run, preview snapshot, preview loading/error, cloning id/error, and reuse status filter.
- [x] Render run list items as selectable cards instead of direct navigation buttons.
- [x] Add detail preview panel with artifact excerpt and actions.
- [x] Reuse existing `restoreRunSnapshot` when clone returns a snapshot, then navigate to the new run URL.
- [x] Run Header tests until green.

## Task 5: Docs And Final Verification

- [x] Update active todo docs to mark E06 consumed.
- [x] Run focused backend tests.
- [x] Run focused frontend service/Header tests.
- [x] Run `npm run lint`, `npm run build`, and `git diff --check`.
- [x] Commit the verified milestone.
