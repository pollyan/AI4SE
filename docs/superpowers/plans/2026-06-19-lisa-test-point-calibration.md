# Lisa 测试点校准闭环 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让用户在 Lisa 测试资产中心直接校准测试点覆盖信息，并让覆盖概览与风险矩阵按保存结果同步刷新。

**Architecture:** 后端复用 `AgentTestPointAsset`，新增测试点 PATCH service 与 route，保存后重建当前 collection 的风险矩阵。前端新增 service 方法和资产中心编辑表单，保存后重新读取完整 collection 以保持派生数据一致。

**Tech Stack:** Flask + SQLAlchemy + Pytest；React + TypeScript + Vitest + Testing Library。

---

## Files

- Modify: `tools/new-agents/backend/test_assets.py`
- Modify: `tools/new-agents/backend/routes.py`
- Modify: `tools/new-agents/backend/tests/test_test_assets.py`
- Modify: `tools/new-agents/backend/tests/test_agent_endpoint.py`
- Modify: `tools/new-agents/frontend/src/core/types.ts`
- Modify: `tools/new-agents/frontend/src/services/testAssetService.ts`
- Modify: `tools/new-agents/frontend/src/services/__tests__/testAssetService.test.ts`
- Modify: `tools/new-agents/frontend/src/pages/TestAssetsPage.tsx`
- Modify: `tools/new-agents/frontend/src/pages/__tests__/TestAssetsPage.test.tsx`
- Modify: `docs/todos/new-agents-evolution.md`

## Task 1: Backend Test Point Update Service

- [ ] Step 1: Add failing service tests in `tools/new-agents/backend/tests/test_test_assets.py`.
  - Test successful update persists `priority`, `risk`, `status`, `testCases`.
  - Test refreshed collection recalculates `coverageSummary` and `riskMatrix`.
  - Test invalid status fails explicitly.
- [ ] Step 2: Run `cd tools/new-agents/backend && python3 -m pytest tests/test_test_assets.py -k 'test_point' -q` and confirm the new tests fail because the function does not exist.
- [ ] Step 3: Implement `update_lisa_test_point_asset(collection_id, test_point, patch)` in `tools/new-agents/backend/test_assets.py`.
  - Validate allowed fields: `priority`, `risk`, `status`, `testCases`.
  - Validate status in `{"已覆盖", "部分覆盖", "未覆盖"}`.
  - Validate `testCases` is a list of non-empty strings.
  - Update `AgentTestPointAsset`.
  - Rebuild collection `risk_matrix` from current test cases and current test points.
  - Return serialized test point.
- [ ] Step 4: Run `cd tools/new-agents/backend && python3 -m pytest tests/test_test_assets.py -k 'test_point' -q` and confirm pass.

## Task 2: Backend Route

- [ ] Step 1: Add failing API tests in `tools/new-agents/backend/tests/test_agent_endpoint.py`.
  - PATCH `/api/agent/test-assets/{collectionId}/test-points/{testPoint}` returns updated point.
  - Unknown test point returns JSON 404.
- [ ] Step 2: Run targeted API tests and confirm route is missing.
- [ ] Step 3: Import `update_lisa_test_point_asset` in `routes.py` and add PATCH route using `<path:test_point>`.
- [ ] Step 4: Run `cd tools/new-agents/backend && python3 -m pytest tests/test_agent_endpoint.py -k 'test_point' -q` and confirm pass.

## Task 3: Frontend Service Contract

- [ ] Step 1: Add `TestAssetPoint` and `TestAssetPointPatch` types in `tools/new-agents/frontend/src/core/types.ts`.
- [ ] Step 2: Add failing service tests in `tools/new-agents/frontend/src/services/__tests__/testAssetService.test.ts`.
  - `updateTestAssetPoint(7, "登录异常链路", patch)` calls encoded PATCH URL.
  - Malformed response throws `Invalid test asset point response`.
- [ ] Step 3: Run `cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/testAssetService.test.ts` and confirm failure.
- [ ] Step 4: Implement parser and `updateTestAssetPoint()` in `testAssetService.ts`.
- [ ] Step 5: Run the service test again and confirm pass.

## Task 4: Asset Center Test Point Editing UI

- [ ] Step 1: Add failing page test in `tools/new-agents/frontend/src/pages/__tests__/TestAssetsPage.test.tsx`.
  - Click `编辑测试点 登录异常链路`.
  - Change status to `已覆盖`, risk to `R-LOGIN-LOCK`, test cases to `TC-002`.
  - Save.
  - Assert `updateTestAssetPoint()` is called and `fetchTestAssetCollection()` is called again.
  - Assert updated coverage and risk matrix are visible.
- [ ] Step 2: Run `cd tools/new-agents/frontend && npm run test -- --run src/pages/__tests__/TestAssetsPage.test.tsx` and confirm failure.
- [ ] Step 3: Update `TestAssetsPage.tsx`.
  - Add test point draft state.
  - Add edit form in “测试点覆盖”.
  - Save through `updateTestAssetPoint()`, then refetch full collection.
  - Show success and error states.
- [ ] Step 4: Run the page test again and confirm pass.

## Task 5: Documentation And Verification

- [ ] Step 1: Update `docs/todos/new-agents-evolution.md` P1 #7 progress and remaining gaps.
- [ ] Step 2: Run backend verification:
  - `cd tools/new-agents/backend && python3 -m pytest tests/test_test_assets.py tests/test_agent_endpoint.py -q`
- [ ] Step 3: Run frontend verification:
  - `cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/testAssetService.test.ts src/pages/__tests__/TestAssetsPage.test.tsx`
  - `cd tools/new-agents/frontend && npm run lint`
- [ ] Step 4: Run `git diff --check`.
- [ ] Step 5: Report changed files, verification results, remaining risks, and next thick-slice candidates. Do not commit unless the user explicitly asks.
