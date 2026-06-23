# Workflow Handoff Context Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn workflow handoff from a one-click transfer button into a reviewable cross-workflow context handoff.

**Architecture:** Extend the existing shared handoff service contract with deterministic review context derived from persisted source artifacts. Keep the existing manifest-driven handoff configuration, run persistence, frontend service parser, ChatPane action, and store transition.

**Tech Stack:** Python 3.11, Flask, pytest, React, TypeScript, Vitest.

---

## File Structure

- Modify: `tools/new-agents/backend/workflow_handoffs.py`
- Modify: `tools/new-agents/backend/tests/test_workflow_handoffs.py`
- Modify: `tools/new-agents/backend/tests/test_agent_endpoint.py`
- Modify: `tools/new-agents/frontend/src/core/types.ts`
- Modify: `tools/new-agents/frontend/src/services/workflowHandoffService.ts`
- Modify: `tools/new-agents/frontend/src/services/__tests__/workflowHandoffService.test.ts`
- Modify: `tools/new-agents/frontend/src/components/ChatPane.tsx`
- Modify: `tools/new-agents/frontend/src/components/__tests__/ChatPane.test.tsx`
- Modify: `tools/new-agents/frontend/src/__tests__/store.test.ts`
- Modify: `docs/todos/refactor/README.md`
- Modify: `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md`

## Task 1: Backend Contract RED

- [ ] Add a focused backend test that records a source artifact with an explicit unconfirmed item and expects exported handoffs to include `sourceSummary`, `unconfirmedItems`, `targetInputChecklist`, and an enriched prompt.
- [ ] Add endpoint assertions for the same fields in `/api/agent/runs/<run_id>/handoffs`.
- [ ] Run the focused backend tests and confirm failure because the fields do not exist yet.

## Task 2: Backend Contract GREEN

- [ ] Add deterministic helpers in `workflow_handoffs.py` for source summary, unconfirmed item extraction, checklist generation, and prompt formatting.
- [ ] Include the new fields in `_build_handoff`.
- [ ] Update the handoff prompt template output to include source version, summary, unconfirmed items, target input checklist, and bounded source artifact.
- [ ] Run the focused backend tests until they pass.

## Task 3: Frontend Parser RED/GREEN

- [ ] Extend `WorkflowHandoff` with the three new review fields.
- [ ] Update `workflowHandoffService` to require `sourceSummary: string`, `unconfirmedItems: string[]`, and `targetInputChecklist: string[]`.
- [ ] Update service tests to prove valid payloads parse and malformed list fields fail explicitly.
- [ ] Run the service tests until they pass.

## Task 4: ChatPane Review Card RED/GREEN

- [ ] Update ChatPane tests so handoff actions must display source version, summary, unconfirmed items, and target checklist before the click.
- [ ] Render each handoff as a compact review card with a clear start action.
- [ ] Keep `startWorkflowHandoff` and `applyWorkflowHandoff` behavior unchanged after the click.
- [ ] Run ChatPane tests until they pass.

## Task 5: Store Fixtures And Docs

- [ ] Update store handoff fixtures with the new required fields.
- [ ] Update active todo docs to mark E07 completed and keep E06/E08/E09 as next candidates.
- [ ] Run store tests and focused frontend tests.

## Task 6: Final Verification

- [ ] Run focused backend tests for handoff service and endpoint.
- [ ] Run focused frontend tests for service, ChatPane, and store.
- [ ] Run `git diff --check`.
- [ ] Commit the verified milestone.
