# Lisa Test Assets Test Point Coverage Visibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Display Lisa test point coverage details in the existing test assets modal.

**Architecture:** Reuse `TestAssetCollection.testPoints` from the materialize API. Render it read-only in `Header` beside issue and risk context.

**Tech Stack:** React, TypeScript, Vitest, Testing Library.

---

### Task 1: Test Point Coverage Read-Only Display

**Files:**
- Modify: `tools/new-agents/frontend/src/components/__tests__/Header.test.tsx`
- Modify: `tools/new-agents/frontend/src/components/Header.tsx`
- Modify: `docs/todos/new-agents-evolution.md`
- Modify: `docs/ARCHITECTURE.md`

- [ ] **Step 1: Write the failing test**

Create a fixture with one `testPoints` row. Open the test assets modal and assert `测试点覆盖`, `支付异常链路`, `未覆盖`, `P1`, `R-PAY-001`, and `无关联用例` are visible.

- [ ] **Step 2: Run Header test to verify it fails**

Run: `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/Header.test.tsx`

Expected: FAIL because the modal does not render test point coverage details yet.

- [ ] **Step 3: Implement the display**

Render a compact read-only `测试点覆盖` section in the existing right side panel when `testPoints.length > 0`.

- [ ] **Step 4: Update docs**

Record test point coverage visibility and leave independent test point management as future work.

- [ ] **Step 5: Verify**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/Header.test.tsx src/services/__tests__/testAssetService.test.ts
cd tools/new-agents/frontend && npm run lint
git diff --check
```
