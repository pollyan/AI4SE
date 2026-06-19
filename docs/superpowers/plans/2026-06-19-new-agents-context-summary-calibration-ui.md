# New Agents Context Summary Calibration UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose persisted run context summaries in the frontend workspace and allow local calibration in a Header modal.

**Architecture:** Reuse the existing snapshot service and Zustand store. Store `contextSummaries` in workspace state, reset them on workspace boundary changes, and render/edit them through a lightweight Header modal without adding a backend write API.

**Tech Stack:** React, Zustand, TypeScript, Vitest, React Testing Library.

---

## File Structure

- Modify `tools/new-agents/frontend/src/core/types.ts`: add `contextSummaries` and an action for local summary updates to `ChatState`.
- Modify `tools/new-agents/frontend/src/store.ts`: hydrate summaries from snapshot, keep local edits out of persisted localStorage state, reset on workflow boundaries, and update a single summary by stable tuple.
- Modify `tools/new-agents/frontend/src/__tests__/store.test.ts`: add RED/GREEN coverage for snapshot hydration, summary editing, and reset.
- Modify `tools/new-agents/frontend/src/components/Header.tsx`: add the Header button and modal for summary viewing/editing.
- Modify `tools/new-agents/frontend/src/components/__tests__/Header.test.tsx`: add RED/GREEN coverage for modal rendering and local calibration.
- Modify `docs/todos/new-agents-evolution.md`: record the new P1 #6 progress and remaining server-side writeback gap.

## Task 1: Store Context Summaries

- [ ] Step 1: Write the failing store test.

Add tests that call `restoreRunSnapshot()` with one `contextSummaries` item, assert it appears in `useStore.getState().contextSummaries`, call the new local update action, and assert the content changes. Add a reset assertion for `clearHistory()`.

- [ ] Step 2: Run the store test to verify RED.

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/__tests__/store.test.ts
```

Expected: fails because `contextSummaries` and the update action do not exist.

- [ ] Step 3: Implement the minimal store support.

Update `ChatState`, initial state, `restoreRunSnapshot()`, `setWorkflow()`, `clearHistory()` and `applyWorkflowHandoff()` to carry or reset summaries. Keep `contextSummaries` out of the persisted `partialize()` state because this slice is local calibration only. Add `updateContextSummaryContent(summary, content)` that matches by `sourceType`, `sourceStageId`, and `summaryType`.

- [ ] Step 4: Run the store test to verify GREEN.

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/__tests__/store.test.ts
```

Expected: all store tests pass.

## Task 2: Header Summary Modal

- [ ] Step 1: Write the failing Header test.

Render Header with `contextSummaries` in store, click “上下文摘要”, assert the modal shows summary type/stage/content, edit the textarea, click “保存摘要”, and assert `useStore.getState().contextSummaries[0].content` has the edited text.

- [ ] Step 2: Run the Header test to verify RED.

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/Header.test.tsx
```

Expected: fails because the Header button and modal do not exist.

- [ ] Step 3: Implement the minimal modal.

Add a `FileText` icon button, local editing state, a label map for `user_supplement` / `stage_conclusion` / `decision` / `current_artifact`, textarea editing, and local save through `updateContextSummaryContent()`. Show an empty state when there are no summaries.

- [ ] Step 4: Run the Header test to verify GREEN.

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/Header.test.tsx
```

Expected: all Header tests pass.

## Task 3: Verification And Todo Record

- [ ] Step 1: Run focused frontend verification.

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/__tests__/store.test.ts src/components/__tests__/Header.test.tsx
cd tools/new-agents/frontend && npm run lint
git diff --check
```

Expected: all commands pass.

- [ ] Step 2: Update `docs/todos/new-agents-evolution.md`.

Add a P1 #6 progress line stating that frontend visible/local calibration UI exists, and adjust the remaining gap to server-side persistence and standalone decision input.

## Self-Review

- Spec coverage: Tasks cover store hydration/reset, Header visibility/editing, and todo update.
- Placeholder scan: No placeholder tasks remain.
- Type consistency: `AgentRunSnapshotContextSummary` is the shared frontend type for service, store, and Header.
