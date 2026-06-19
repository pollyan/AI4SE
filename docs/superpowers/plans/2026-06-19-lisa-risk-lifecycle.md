# Lisa 风险生命周期管理 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让用户在 Lisa 测试资产中心处置风险矩阵项，并在资产刷新或矩阵重建后保留风险生命周期状态。

**Architecture:** 后端在现有 `AgentRiskMatrixAsset` 上保存 lifecycle 字段，并新增风险 PATCH service/route。风险矩阵重建时按风险名称保留 lifecycle。前端新增风险类型字段、service 方法和资产中心编辑表单。

**Tech Stack:** Flask + SQLAlchemy + Pytest；React + TypeScript + Vitest + Testing Library。

---

## Files

- Modify: `tools/new-agents/backend/models.py`
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

## Task 1: Backend Risk Lifecycle Model And Service

- [x] Step 1: Add failing tests in `tools/new-agents/backend/tests/test_test_assets.py` for updating risk lifecycle and preserving lifecycle after risk matrix rebuild.
- [x] Step 2: Run `cd tools/new-agents/backend && python3 -m pytest tests/test_test_assets.py -k 'risk_lifecycle' -q` and confirm failure.
- [x] Step 3: Add `status`, `owner`, `note` columns to `AgentRiskMatrixAsset`.
- [x] Step 4: Add `update_lisa_test_asset_risk(collection_id, risk, patch)` in `test_assets.py`.
- [x] Step 5: Include lifecycle fields in risk serialization and materialization.
- [x] Step 6: Preserve lifecycle fields in `_rebuild_risk_matrix()`.
- [x] Step 7: Re-run the risk lifecycle service tests and confirm pass.

## Task 2: Backend Risk Lifecycle Route

- [x] Step 1: Add failing endpoint tests in `tools/new-agents/backend/tests/test_agent_endpoint.py` for PATCH `/api/agent/test-assets/{collectionId}/risks/{risk}`.
- [x] Step 2: Run `cd tools/new-agents/backend && python3 -m pytest tests/test_agent_endpoint.py -k 'risk_lifecycle' -q` and confirm route failure.
- [x] Step 3: Add route in `routes.py`, importing `update_lisa_test_asset_risk`.
- [x] Step 4: Re-run endpoint tests and confirm pass.

## Task 3: Frontend Service Contract

- [x] Step 1: Add lifecycle fields to risk matrix type in `core/types.ts`.
- [x] Step 2: Add failing tests in `src/services/__tests__/testAssetService.test.ts` for `updateTestAssetRisk()` and malformed risk response.
- [x] Step 3: Run service test and confirm failure.
- [x] Step 4: Implement parser support and `updateTestAssetRisk()` in `testAssetService.ts`.
- [x] Step 5: Re-run service test and confirm pass.

## Task 4: Asset Center Risk Editing UI

- [x] Step 1: Add failing page test in `TestAssetsPage.test.tsx` for editing risk status/owner/note.
- [x] Step 2: Run page test and confirm missing UI failure.
- [x] Step 3: Add risk draft state, edit form, save handler and updated risk display in `TestAssetsPage.tsx`.
- [x] Step 4: Re-run page test and confirm pass.

## Task 5: Documentation And Verification

- [x] Step 1: Update P1 #7 in `docs/todos/new-agents-evolution.md`.
- [x] Step 2: Run backend and frontend verification commands from the spec.
- [x] Step 3: Run `git diff --check`.
- [x] Step 4: Report changes, verification, residual risk and next thick-slice candidates. Do not commit unless explicitly asked.
