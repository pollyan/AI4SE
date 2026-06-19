# Lisa Test Assets Intent Tester Import Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users import one Lisa test asset draft into intent-tester from the existing test assets modal.

**Architecture:** Keep backend unchanged. Add a focused frontend import service for `/intent-tester/api/testcases`, type the existing `intentTesterDrafts`, and add per-case import controls in Header's test assets modal.

**Tech Stack:** React, TypeScript, Vitest, existing intent-tester REST API.

---

### Task 1: Import Service

**Files:**
- Modify: `tools/new-agents/frontend/src/core/types.ts`
- Modify: `tools/new-agents/frontend/src/services/testAssetService.ts`
- Create: `tools/new-agents/frontend/src/services/intentTesterImportService.ts`
- Create: `tools/new-agents/frontend/src/services/__tests__/intentTesterImportService.test.ts`

- [ ] **Step 1: Write failing service tests**

Assert `importIntentTesterDraft(draft)` posts to `/intent-tester/api/testcases`, sends the draft without `sourceCaseId` and `draftWarnings`, and parses `data.id/name`.

- [ ] **Step 2: Run service test red**

Run: `cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/intentTesterImportService.test.ts`

Expected: FAIL because the service does not exist.

- [ ] **Step 3: Implement typed draft parsing and import service**

Add `IntentTesterDraft` and `IntentTesterImportResult` types, parse drafts in `testAssetService`, and implement strict import response parsing.

- [ ] **Step 4: Run service test green**

Run: `cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/intentTesterImportService.test.ts src/services/__tests__/testAssetService.test.ts`

Expected: PASS.

### Task 2: Header Import UI

**Files:**
- Modify: `tools/new-agents/frontend/src/components/Header.tsx`
- Modify: `tools/new-agents/frontend/src/components/__tests__/Header.test.tsx`

- [ ] **Step 1: Write failing Header test**

Mock `importIntentTesterDraft`, open “测试资产”, click “导入 TC-001”, and assert the service receives the matching draft and the UI shows the created ID.

- [ ] **Step 2: Run Header test red**

Run: `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/Header.test.tsx`

Expected: FAIL because the import button does not exist.

- [ ] **Step 3: Implement import button and status**

Find drafts by `sourceCaseId`, show per-case import button, and track imported IDs/errors in Header local state.

- [ ] **Step 4: Run Header test green**

Run: `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/Header.test.tsx`

Expected: PASS.

### Task 3: Docs and Verification

**Files:**
- Modify: `docs/todos/new-agents-evolution.md`
- Modify: `docs/component-inventory.md`
- Modify: `docs/api-contracts.md`

- [ ] **Step 1: Update docs**

Record the manual single-draft import capability and the remaining gaps.

- [ ] **Step 2: Run verification**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/intentTesterImportService.test.ts src/services/__tests__/testAssetService.test.ts src/components/__tests__/Header.test.tsx
cd tools/new-agents/frontend && npm run lint
git diff --check
```

Expected: all commands pass.
