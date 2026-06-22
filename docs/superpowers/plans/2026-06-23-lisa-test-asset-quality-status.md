# Lisa Test Asset Quality Status Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a shared Lisa test asset quality status so users can see whether a materialized TEST_DESIGN/CASES asset collection is blocked, needs attention, or ready.

**Architecture:** Add one focused frontend core module that derives quality state from the already persisted `TestAssetCollection` fields. Reuse it in `Header.tsx` and `TestAssetsPage.tsx` without adding backend API, runtime branches, or new persistence fields.

**Tech Stack:** React 19, TypeScript 5.x, Vitest, Testing Library, existing New Agents frontend service/types.

---

### Task 1: Shared Quality State

**Files:**
- Create: `tools/new-agents/frontend/src/core/testAssetQuality.ts`
- Create: `tools/new-agents/frontend/src/core/__tests__/testAssetQuality.test.ts`

- [ ] **Step 1: Write failing tests**

Add tests that import `deriveTestAssetQualityStatus` and assert:

- Pending issue + uncovered point + open unowned risk returns `blocked`.
- Confirmed issue no longer blocks, but mitigating/accepted risks return `attention`.
- Fully covered points, closed risks, and no pending issues return `ready`.

- [ ] **Step 2: Run RED**

Run:

```bash
cd tools/new-agents/frontend
npm run test -- --run src/core/__tests__/testAssetQuality.test.ts
```

Expected: fail because `testAssetQuality.ts` does not exist.

- [ ] **Step 3: Implement minimal pure function**

Create `deriveTestAssetQualityStatus(collection: TestAssetCollection)` returning `status`, `label`, `summary`, `blockingItems`, `attentionItems`, and `nextAction`.

- [ ] **Step 4: Run GREEN**

Run the same Vitest command. Expected: all new pure function tests pass.

### Task 2: Header Test Asset Modal

**Files:**
- Modify: `tools/new-agents/frontend/src/components/Header.tsx`
- Modify: `tools/new-agents/frontend/src/components/__tests__/Header.test.tsx`

- [ ] **Step 1: Write failing component test**

Extend the Lisa test asset quality issue test to expect the modal to display:

- `质量状态`
- blocked label
- a next action mentioning pending issue or uncovered point

- [ ] **Step 2: Run RED**

Run:

```bash
cd tools/new-agents/frontend
npm run test -- --run src/components/__tests__/Header.test.tsx
```

Expected: fail because the modal has no unified quality state section.

- [ ] **Step 3: Render quality summary**

Import `deriveTestAssetQualityStatus`, derive state from `testAssetCollection`, and render a compact summary above the metric cards.

- [ ] **Step 4: Run GREEN**

Run the same Header test command. Expected: Header tests pass.

### Task 3: Asset Center Quality Summary

**Files:**
- Modify: `tools/new-agents/frontend/src/pages/TestAssetsPage.tsx`
- Modify: `tools/new-agents/frontend/src/pages/__tests__/TestAssetsPage.test.tsx`

- [ ] **Step 1: Write failing page tests**

Add assertions that the asset center shows the quality state and that confirming the pending issue updates the visible quality details.

- [ ] **Step 2: Run RED**

Run:

```bash
cd tools/new-agents/frontend
npm run test -- --run src/pages/__tests__/TestAssetsPage.test.tsx
```

Expected: fail because the page has no quality state section.

- [ ] **Step 3: Render quality summary**

Import the shared quality function, derive state from `collection`, and render the same status before the existing metric cards.

- [ ] **Step 4: Run GREEN**

Run the same TestAssetsPage command. Expected: page tests pass.

### Task 4: Todo Record And Validation

**Files:**
- Modify: `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md`

- [ ] **Step 1: Update E04 completion record**

Mark E04 as consumed with a concise completion definition and validation commands.

- [ ] **Step 2: Run focused validation**

Run:

```bash
cd tools/new-agents/frontend
npm run test -- --run src/core/__tests__/testAssetQuality.test.ts src/components/__tests__/Header.test.tsx src/pages/__tests__/TestAssetsPage.test.tsx
npm run lint
git diff --check
```

Expected: all commands exit 0.

- [ ] **Step 3: Commit**

Stage only this milestone's files and commit:

```bash
git add docs/superpowers/specs/2026-06-23-lisa-test-asset-quality-status-design.md docs/superpowers/plans/2026-06-23-lisa-test-asset-quality-status.md docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md tools/new-agents/frontend/src/core/testAssetQuality.ts tools/new-agents/frontend/src/core/__tests__/testAssetQuality.test.ts tools/new-agents/frontend/src/components/Header.tsx tools/new-agents/frontend/src/components/__tests__/Header.test.tsx tools/new-agents/frontend/src/pages/TestAssetsPage.tsx tools/new-agents/frontend/src/pages/__tests__/TestAssetsPage.test.tsx
git commit -m "feat: 增加 Lisa 测试资产质量状态"
```
