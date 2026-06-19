# New Agents Observability Auto Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a scoped auto-refresh toggle to the existing Header runtime statistics modal.

**Architecture:** Reuse the current `fetchObservabilitySummary` service and Header modal state. Add local UI state plus a cleanup-safe interval effect that refreshes with the active workflow/stage filters.

**Tech Stack:** React, TypeScript, Vitest, Testing Library, Markdown docs.

---

### Task 1: Header Auto Refresh Behavior

**Files:**
- Modify: `tools/new-agents/frontend/src/components/Header.tsx`
- Modify: `tools/new-agents/frontend/src/components/__tests__/Header.test.tsx`

- [x] **Step 1: Write the failing test**

Add a test named `auto-refreshes runtime observability with active filters until the modal closes`. Use `vi.useFakeTimers()`, open the modal, select `TEST_DESIGN` and `CLARIFY`, enable the `自动刷新` checkbox, advance timers by `30000`, and assert the last service call includes the active filters. Close the modal, advance timers again, and assert the service call count does not change.

- [x] **Step 2: Run test to verify it fails**

Run: `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/Header.test.tsx -t "auto-refreshes runtime observability with active filters until the modal closes"`

Expected: FAIL because `自动刷新` control does not exist yet.

- [x] **Step 3: Implement minimal Header state and interval**

Import `useEffect`, add `isObservabilityAutoRefreshEnabled` state, create a helper that returns active observability filters, and add a cleanup-safe `useEffect` interval with `30000` ms delay while the modal is open and auto-refresh is enabled.

- [x] **Step 4: Add the checkbox control**

Render a checkbox labeled `自动刷新` in the existing observability filter form and bind it to `isObservabilityAutoRefreshEnabled`.

- [x] **Step 5: Run Header tests**

Run: `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/Header.test.tsx`

Expected: all Header tests pass.

### Task 2: Todo Record And Verification

**Files:**
- Modify: `docs/todos/new-agents-evolution.md`

- [x] **Step 1: Update progress**

Record that Header runtime statistics now has a 30 second auto-refresh toggle that reuses the active workflow/stage filters and stops on modal close.

- [x] **Step 2: Run focused verification**

Run: `cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/observabilityService.test.ts src/components/__tests__/Header.test.tsx`

Expected: observability service and Header tests pass.

- [x] **Step 3: Run lint and whitespace check**

Run: `cd tools/new-agents/frontend && npm run lint`

Expected: lint passes.

Run: `git diff --check`

Expected: no whitespace errors.
