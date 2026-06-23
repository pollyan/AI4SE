# Lisa Test Asset Quality Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a unified Lisa test asset quality loop where persisted issues, test point coverage, and risk lifecycle states drive one visible `qualitySummary`.

**Architecture:** Add `qualitySummary` to the existing persisted test asset collection serialization, parse it strictly in the existing frontend service, and render it in the shared Lisa asset center plus Header shortcut panel. Reuse current test asset APIs and refresh flows; do not add workflow-specific runtime infrastructure.

**Tech Stack:** Python 3.11, Flask/SQLAlchemy backend tests with pytest, React/TypeScript frontend with Vitest and Testing Library.

---

### Task 1: Backend Quality Summary Contract

**Files:**
- Modify: `tools/new-agents/backend/test_assets.py`
- Modify: `tools/new-agents/backend/tests/test_test_assets.py`

- [ ] **Step 1: Write the failing backend tests**

Add tests that materialize Lisa assets, inspect `qualitySummary`, then update issue/test point/risk state and assert the summary changes from `blocked` to `ready` through persisted collection reloads.

- [ ] **Step 2: Run RED backend tests**

Run:

```bash
/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest tools/new-agents/backend/tests/test_test_assets.py -q
```

Expected: fails because `qualitySummary` is missing.

- [ ] **Step 3: Implement minimal backend summary builder**

Add a private helper in `test_assets.py` that counts issue statuses, coverage states, and risk statuses, then appends `qualitySummary` inside `_serialize_collection`.

- [ ] **Step 4: Run GREEN backend tests**

Run the same pytest command and verify the backend suite passes.

### Task 2: Frontend Service Parser Contract

**Files:**
- Modify: `tools/new-agents/frontend/src/core/types.ts`
- Modify: `tools/new-agents/frontend/src/services/testAssetService.ts`
- Modify: `tools/new-agents/frontend/src/services/__tests__/testAssetService.test.ts`

- [ ] **Step 1: Write failing parser tests**

Update the valid fixture with `qualitySummary`, assert parsed status/gates are exposed, and add invalid-response coverage for missing or malformed summary.

- [ ] **Step 2: Run RED service tests**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- src/services/__tests__/testAssetService.test.ts
```

Expected: fails because the type/parser does not know `qualitySummary`.

- [ ] **Step 3: Implement types and strict parser**

Add `TestAssetQualitySummary`, `TestAssetQualityGate`, `TestAssetQualityStatus`, and parser validation for all required fields.

- [ ] **Step 4: Run GREEN service tests**

Run the same Vitest target and verify service tests pass.

### Task 3: Shared Frontend Quality Summary Recalculation

**Files:**
- Create: `tools/new-agents/frontend/src/core/testAssetQuality.ts`
- Create: `tools/new-agents/frontend/src/core/__tests__/testAssetQuality.test.ts`
- Modify: `tools/new-agents/frontend/src/core/types.ts`

- [ ] **Step 1: Write failing utility tests**

Cover blocked, attention, and ready summaries from in-memory `TestAssetCollection` data so issue-only local updates can refresh UI without a full backend fetch.

- [ ] **Step 2: Run RED utility tests**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- src/core/__tests__/testAssetQuality.test.ts
```

Expected: fails because the helper does not exist.

- [ ] **Step 3: Implement `withTestAssetQualitySummary`**

Create a small pure helper that mirrors backend summary rules and returns a collection with recalculated `qualitySummary`.

- [ ] **Step 4: Run GREEN utility tests**

Run the same Vitest target and verify utility tests pass.

### Task 4: Asset Center Quality Loop UI

**Files:**
- Modify: `tools/new-agents/frontend/src/pages/TestAssetsPage.tsx`
- Modify: `tools/new-agents/frontend/src/pages/__tests__/TestAssetsPage.test.tsx`

- [ ] **Step 1: Write failing UI tests**

Add assertions that the asset center shows the quality state/gates, updates after issue confirmation, updates after test point coverage edit, and updates after risk accepted/closed edit.

- [ ] **Step 2: Run RED page tests**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- src/pages/__tests__/TestAssetsPage.test.tsx
```

Expected: fails because the page does not render `qualitySummary`.

- [ ] **Step 3: Implement asset center display and local summary refresh**

Render a quality status panel above metric cards. Use `withTestAssetQualitySummary` after local issue updates and rely on fetched collection summary after point/risk saves.

- [ ] **Step 4: Run GREEN page tests**

Run the same Vitest target and verify page tests pass.

### Task 5: Header Shortcut Quality Visibility

**Files:**
- Modify: `tools/new-agents/frontend/src/components/Header.tsx`
- Modify: `tools/new-agents/frontend/src/components/__tests__/Header.test.tsx`

- [ ] **Step 1: Write failing Header tests**

Update fixtures with `qualitySummary` and assert the Lisa asset modal shows the same status and gate details.

- [ ] **Step 2: Run RED Header tests**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- src/components/__tests__/Header.test.tsx
```

Expected: fails because Header does not show quality summary.

- [ ] **Step 3: Implement Header summary display**

Add a compact quality panel in the existing modal, without adding duplicate full editing workflows.

- [ ] **Step 4: Run GREEN Header tests**

Run the same Vitest target and verify Header tests pass.

### Task 6: Documentation, Todo, and Final Verification

**Files:**
- Modify: `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md`
- Modify as needed: `docs/todos/refactor/README.md`

- [ ] **Step 1: Update todo status**

Mark E04 as completed for the quality summary/quality loop slice, with explicit remaining risks if real model smoke or broader UX polish remains out of scope.

- [ ] **Step 2: Run focused validation**

Run:

```bash
/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest tools/new-agents/backend/tests/test_test_assets.py -q
cd tools/new-agents/frontend && npm run test -- src/services/__tests__/testAssetService.test.ts src/core/__tests__/testAssetQuality.test.ts src/pages/__tests__/TestAssetsPage.test.tsx src/components/__tests__/Header.test.tsx
cd tools/new-agents/frontend && npm run build
git diff --check
```

- [ ] **Step 3: Commit**

If verification passes and no unrelated files are staged, commit the focused milestone:

```bash
git add tools/new-agents/backend/test_assets.py tools/new-agents/backend/tests/test_test_assets.py tools/new-agents/frontend/src/core/types.ts tools/new-agents/frontend/src/core/testAssetQuality.ts tools/new-agents/frontend/src/core/__tests__/testAssetQuality.test.ts tools/new-agents/frontend/src/services/testAssetService.ts tools/new-agents/frontend/src/services/__tests__/testAssetService.test.ts tools/new-agents/frontend/src/pages/TestAssetsPage.tsx tools/new-agents/frontend/src/pages/__tests__/TestAssetsPage.test.tsx tools/new-agents/frontend/src/components/Header.tsx tools/new-agents/frontend/src/components/__tests__/Header.test.tsx docs/superpowers/specs/2026-06-23-lisa-test-asset-quality-loop-design.md docs/superpowers/plans/2026-06-23-lisa-test-asset-quality-loop.md docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md docs/todos/refactor/README.md
git commit -m "feat(new-agents): 补齐 Lisa 测试资产质量闭环"
```
