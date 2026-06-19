# Lisa Test Asset Issue Status Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add local triage status controls for Lisa test asset quality issues in the existing test asset modal.

**Architecture:** Keep modal-local issue status state in `Header.tsx`, derive stable issue keys from issue content, render status labels and action buttons per issue, and leave backend persistence for a later slice.

**Tech Stack:** React, TypeScript, Vitest, Testing Library.

---

### Task 1: Header Issue Status Test

**Files:**
- Modify: `tools/new-agents/frontend/src/components/__tests__/Header.test.tsx`

- [x] **Step 1: Write failing UI test**

Add a test that opens Lisa test assets with `TEST_ASSET_COLLECTION_WITH_ISSUES`, expects `1 个问题 · 1 待处理`, clicks `确认问题`, expects `已确认` and `1 个问题 · 0 待处理`, then clicks `忽略问题` and expects `忽略`.

- [x] **Step 2: Run test to verify RED**

Run: `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/Header.test.tsx -t "triages Lisa test asset quality issue status locally"`

Expected: fail because the modal currently has no issue status controls.

### Task 2: Header Issue Status Implementation

**Files:**
- Modify: `tools/new-agents/frontend/src/components/Header.tsx`

- [x] **Step 1: Add issue status state**

Add `issueStatuses` state and helper functions for issue keys, labels, and pending count.

- [x] **Step 2: Reset status on modal open**

Clear `issueStatuses` in `handleOpenTestAssets()` so every fresh load starts as pending.

- [x] **Step 3: Render status controls**

Render each asset issue with a status pill plus `确认问题` and `忽略问题` buttons that update local state.

- [x] **Step 4: Run test to verify GREEN**

Run: `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/Header.test.tsx -t "triages Lisa test asset quality issue status locally"`

Expected: test passes.

### Task 3: Todo Record And Verification

**Files:**
- Modify: `docs/todos/new-agents-evolution.md`

- [x] **Step 1: Update progress record**

Append a dated P1 #7 note that the frontend test asset modal now supports local issue triage statuses, while backend persistence remains open.

- [x] **Step 2: Run focused frontend tests**

Run: `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/Header.test.tsx`

Expected: Header tests pass.

- [x] **Step 3: Run TypeScript check**

Run: `cd tools/new-agents/frontend && npm run lint`

Expected: TypeScript check passes.

- [x] **Step 4: Run diff whitespace verification**

Run: `git diff --check`

Expected: no whitespace errors.
