# Lisa Test Assets Batch Intent-Tester Import Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add manual batch import for Lisa intent-tester drafts in the existing test assets modal.

**Architecture:** Keep the backend contract unchanged and reuse the existing frontend import service. `Header` owns modal-local batch progress, imported ID mapping, and summary messaging.

**Tech Stack:** React, TypeScript, Vitest, Testing Library.

---

### Task 1: Header Batch Import UI

**Files:**
- Modify: `tools/new-agents/frontend/src/components/__tests__/Header.test.tsx`
- Modify: `tools/new-agents/frontend/src/components/Header.tsx`
- Modify: `docs/todos/new-agents-evolution.md`
- Modify: `docs/api-contracts.md`
- Modify: `docs/component-inventory.md`
- Modify: `docs/ARCHITECTURE.md`

- [ ] **Step 1: Write the failing test**

Add a test that materializes a two-case collection, clicks `批量导入草稿`, expects `importIntentTesterDraft` to receive both draft payloads, and verifies `已批量导入 2 条 intent-tester 用例` plus imported IDs.

- [ ] **Step 2: Run the targeted test to verify it fails**

Run: `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/Header.test.tsx`

Expected: FAIL because the batch import button does not exist yet.

- [ ] **Step 3: Implement minimal batch import state and handler**

Add modal-local state for batch import progress and summary. Import all not-yet-imported drafts sequentially through `importIntentTesterDraft`, update the existing imported ID map, and show a success or no-op summary.

- [ ] **Step 4: Add the button and summary to the modal**

Render `批量导入草稿` when `intentTesterDrafts.length > 0`. Disable it while the batch is running, and render the summary near the coverage cards.

- [ ] **Step 5: Update docs**

Record the manual batch import capability and clarify that import is still user-triggered rather than automatic.

- [ ] **Step 6: Verify**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/Header.test.tsx src/services/__tests__/intentTesterImportService.test.ts src/services/__tests__/testAssetService.test.ts
cd tools/new-agents/frontend && npm run lint
git diff --check
```
