# Lisa Test Assets Risk Matrix Visibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Display Lisa risk matrix data in the existing test assets modal.

**Architecture:** Reuse `TestAssetCollection.riskMatrix` from the existing materialize API. Render it in `Header` as read-only context next to the case editor and asset issue list.

**Tech Stack:** React, TypeScript, Vitest, Testing Library.

---

### Task 1: Risk Matrix Read-Only Display

**Files:**
- Modify: `tools/new-agents/frontend/src/components/__tests__/Header.test.tsx`
- Modify: `tools/new-agents/frontend/src/components/Header.tsx`
- Modify: `docs/todos/new-agents-evolution.md`
- Modify: `docs/ARCHITECTURE.md`

- [ ] **Step 1: Write the failing test**

Create a `TestAssetCollection` fixture with one `riskMatrix` row. Open the test assets modal and assert `风险矩阵`, `R-LOGIN-001`, `TC-001`, `登录主链路`, `P0`, and `已覆盖` are visible.

- [ ] **Step 2: Run Header test to verify it fails**

Run: `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/Header.test.tsx`

Expected: FAIL because the modal does not render `riskMatrix` yet.

- [ ] **Step 3: Implement the display**

Render a compact read-only `风险矩阵` section in the existing right side panel when `riskMatrix.length > 0`.

- [ ] **Step 4: Update docs**

Record that risk matrix visibility is now available while independent risk management remains future work.

- [ ] **Step 5: Verify**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/Header.test.tsx src/services/__tests__/testAssetService.test.ts
cd tools/new-agents/frontend && npm run lint
git diff --check
```
