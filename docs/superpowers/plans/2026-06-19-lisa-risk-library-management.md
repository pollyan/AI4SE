# Lisa 风险库稳定身份与管理 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 Lisa 测试资产中心具备稳定风险 ID，并支持新增、重命名和删除未关联风险。

**Architecture:** 后端复用现有 `AgentRiskMatrixAsset` 作为 collection 内风险实体，暴露数据库 `id`，新增 `is_manual` 字段，并把风险矩阵重建改为 upsert。前端风险矩阵区改用按 ID 的风险 service，新增手工风险创建、风险名称编辑和未关联风险删除。

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
- Modify: `tools/new-agents/frontend/src/components/__tests__/Header.test.tsx`
- Modify: `docs/todos/new-agents-evolution.md`

## Task 1: Backend Stable Risk Identity

- [ ] Step 1: Add failing tests in `tools/new-agents/backend/tests/test_test_assets.py`:
  - `test_lisa_test_asset_risks_include_stable_id_and_manual_flag`
  - `test_lisa_test_asset_risk_id_survives_risk_matrix_rebuild`
- [ ] Step 2: Run `cd tools/new-agents/backend && python3 -m pytest tests/test_test_assets.py -k 'stable_id' -q` and confirm failure because risk serialization lacks `id/isManual` or IDs change after rebuild.
- [ ] Step 3: Add `is_manual = db.Column(db.Boolean, nullable=False, default=False)` to `AgentRiskMatrixAsset`.
- [ ] Step 4: Update `_serialize_risk_matrix_item()` to return `id` and `isManual`.
- [ ] Step 5: Replace `_rebuild_risk_matrix()` clear-and-recreate behavior with upsert:
  - update existing risk rows by risk name
  - create new rows for new derived risks
  - preserve manual rows with empty relation arrays
  - delete non-manual rows no longer derived
- [ ] Step 6: Update `materialize_lisa_test_assets()` so existing collection refresh does not clear `risk_matrix`; instead call the same risk sync helper using exported risks.
- [ ] Step 7: Re-run `cd tools/new-agents/backend && python3 -m pytest tests/test_test_assets.py -k 'stable_id' -q` and confirm pass.

## Task 2: Backend Risk CRUD Services And Routes

- [ ] Step 1: Add failing service tests in `tools/new-agents/backend/tests/test_test_assets.py`:
  - `test_create_lisa_test_asset_risk_adds_manual_unlinked_risk`
  - `test_rename_lisa_test_asset_risk_by_id_updates_current_sources_and_preserves_id`
  - `test_delete_lisa_test_asset_risk_removes_unlinked_manual_risk`
  - `test_delete_lisa_test_asset_risk_rejects_linked_risk`
- [ ] Step 2: Run `cd tools/new-agents/backend && python3 -m pytest tests/test_test_assets.py -k 'risk_library' -q` and confirm missing service failures.
- [ ] Step 3: Implement services in `test_assets.py`:
  - `create_lisa_test_asset_risk(collection_id, patch)`
  - `update_lisa_test_asset_risk_by_id(collection_id, risk_id, patch)`
  - `delete_lisa_test_asset_risk(collection_id, risk_id)`
- [ ] Step 4: Keep existing `update_lisa_test_asset_risk(collection_id, risk, patch)` as a compatibility wrapper for lifecycle-only name-based updates.
- [ ] Step 5: Add failing endpoint tests in `tools/new-agents/backend/tests/test_agent_endpoint.py` for:
  - POST `/api/agent/test-assets/{collectionId}/risks`
  - PATCH `/api/agent/test-assets/{collectionId}/risks/by-id/{riskId}`
  - DELETE `/api/agent/test-assets/{collectionId}/risks/by-id/{riskId}`
- [ ] Step 6: Run `cd tools/new-agents/backend && python3 -m pytest tests/test_agent_endpoint.py -k 'risk_library' -q` and confirm route failures.
- [ ] Step 7: Add routes in `routes.py`, returning JSON payloads and preserving explicit 400/404 behavior.
- [ ] Step 8: Re-run backend risk library tests and confirm pass.

## Task 3: Frontend Service Contract

- [ ] Step 1: Update `TestAssetRisk` in `core/types.ts` with `id` and `isManual`; add `TestAssetRiskCreatePatch` and expand `TestAssetRiskPatch` to include `risk`.
- [ ] Step 2: Add failing tests in `src/services/__tests__/testAssetService.test.ts` for:
  - parsing `id/isManual`
  - `createTestAssetRisk()`
  - `updateTestAssetRiskById()`
  - `deleteTestAssetRisk()`
  - malformed risk payload missing `id`
- [ ] Step 3: Run `cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/testAssetService.test.ts` and confirm failures.
- [ ] Step 4: Implement parser and service methods in `testAssetService.ts`.
- [ ] Step 5: Re-run service tests and confirm pass.

## Task 4: Asset Center Risk Library UI

- [ ] Step 1: Update page and Header test fixtures to include `id` and `isManual` on every risk.
- [ ] Step 2: Add failing page tests in `TestAssetsPage.test.tsx`:
  - `creates a manual risk in the asset center`
  - `renames a linked risk and refreshes derived assets`
  - `deletes an unlinked manual risk`
- [ ] Step 3: Run `cd tools/new-agents/frontend && npm run test -- --run src/pages/__tests__/TestAssetsPage.test.tsx -t 'manual risk|renames a linked risk|deletes an unlinked'` and confirm missing UI failures.
- [ ] Step 4: Update `TestAssetsPage.tsx`:
  - import new service methods
  - add risk name to edit draft
  - add create risk form state and submit handler
  - call `updateTestAssetRiskById()` for editing risks, then refresh collection
  - call `deleteTestAssetRisk()` for unlinked risks and remove from collection
  - display risk ID and manual risk marker
- [ ] Step 5: Re-run targeted page tests and confirm pass.

## Task 5: Documentation And Verification

- [ ] Step 1: Update P1 #7 in `docs/todos/new-agents-evolution.md` to record stable risk library management completion and update remaining work.
- [ ] Step 2: Run `cd tools/new-agents/backend && python3 -m pytest tests/test_test_assets.py tests/test_agent_endpoint.py -q`.
- [ ] Step 3: Run `cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/testAssetService.test.ts src/pages/__tests__/TestAssetsPage.test.tsx`.
- [ ] Step 4: Run `cd tools/new-agents/frontend && npm run lint`.
- [ ] Step 5: Run `git diff --check`.
- [ ] Step 6: Report changes, verification, residual risk and next thick-slice candidates. Do not commit unless explicitly asked.
