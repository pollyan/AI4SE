# Lisa Test Assets Intent-Tester Execution Link Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show an intent-tester execution-page link after Lisa imports a draft.

**Architecture:** Keep New Agents as a frontend handoff surface. Use the existing imported intent-tester ID state in `Header` to derive a deterministic link.

**Tech Stack:** React, TypeScript, Vitest, Testing Library.

---

### Task 1: Execution Link After Import

**Files:**
- Modify: `tools/new-agents/frontend/src/components/__tests__/Header.test.tsx`
- Modify: `tools/new-agents/frontend/src/components/Header.tsx`
- Modify: `docs/todos/new-agents-evolution.md`
- Modify: `docs/ARCHITECTURE.md`
- Modify: `docs/component-inventory.md`

- [ ] **Step 1: Write the failing assertion**

In the existing single import test, assert that the link named `去执行 #42` has href `/intent-tester/execution?testcase_id=42` after import success.

- [ ] **Step 2: Run the Header test to verify it fails**

Run: `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/Header.test.tsx`

Expected: FAIL because the execution handoff link is not rendered yet.

- [ ] **Step 3: Implement the link**

Render an anchor beside the imported ID when `importedCaseId` exists. Use `target="_blank"` and `rel="noreferrer"`.

- [ ] **Step 4: Update docs**

Record that New Agents now links imported cases to the intent-tester execution page, without directly triggering execution.

- [ ] **Step 5: Verify**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/Header.test.tsx src/services/__tests__/intentTesterImportService.test.ts src/services/__tests__/testAssetService.test.ts
cd tools/new-agents/frontend && npm run lint
git diff --check
```
