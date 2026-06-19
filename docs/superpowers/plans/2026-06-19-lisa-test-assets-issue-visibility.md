# Lisa Test Assets Issue Visibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Display Lisa test asset quality issues in the test assets modal.

**Architecture:** Keep issue generation and persistence unchanged in the backend. `Header` renders the existing `assetIssues` array as read-only context beside the case list.

**Tech Stack:** React, TypeScript, Vitest, Testing Library.

---

### Task 1: Asset Issue Read-Only Display

**Files:**
- Modify: `tools/new-agents/frontend/src/components/__tests__/Header.test.tsx`
- Modify: `tools/new-agents/frontend/src/components/Header.tsx`
- Modify: `docs/todos/new-agents-evolution.md`
- Modify: `docs/ARCHITECTURE.md`

- [ ] **Step 1: Write the failing test**

Create a collection fixture with one `assetIssues` entry. Open the test assets modal and assert `资产问题`, `1 个问题`, the message, and `TC-999` are visible.

- [ ] **Step 2: Run Header test to verify it fails**

Run: `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/Header.test.tsx`

Expected: FAIL because the modal does not render asset issues yet.

- [ ] **Step 3: Implement the display**

Render a compact issue list in the right side panel when `testAssetCollection.assetIssues.length > 0`.

- [ ] **Step 4: Update docs**

Record read-only issue visibility and leave persisted issue status flow as remaining work.

- [ ] **Step 5: Verify**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/Header.test.tsx
cd tools/new-agents/frontend && npm run lint
git diff --check
```
