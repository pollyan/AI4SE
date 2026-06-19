# Lisa Intent Tester Mapping Persistence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist Lisa source-case to intent-tester testcase/execution mappings so the asset center restores imported and latest execution state after refresh.

**Architecture:** Add a child model under `AgentTestAssetCollection`, expose record APIs from New Agents, serialize `intentTesterMappings` through the existing collection endpoint, and have the asset center write mappings after successful intent-tester operations. This keeps intent-tester execution separate while giving New Agents a stable cross-system reference.

**Tech Stack:** Flask, Flask-SQLAlchemy, pytest, React, TypeScript, Vitest, Testing Library.

---

## File Map

- Modify `tools/new-agents/backend/models.py`: add `AgentTestAssetIntentTesterMapping` and collection relationship.
- Modify `tools/new-agents/backend/test_assets.py`: serialize mappings, record imported cases, record latest executions, preserve mappings during materialize.
- Modify `tools/new-agents/backend/routes.py`: add two mapping routes.
- Modify `tools/new-agents/backend/tests/test_test_assets.py`: service-level persistence tests.
- Modify `tools/new-agents/backend/tests/test_agent_endpoint.py`: API contract tests.
- Modify `tools/new-agents/frontend/src/core/types.ts`: add mapping type and collection field.
- Modify `tools/new-agents/frontend/src/services/testAssetService.ts`: parse and record mappings.
- Modify `tools/new-agents/frontend/src/services/__tests__/testAssetService.test.ts`: frontend service tests.
- Modify `tools/new-agents/frontend/src/pages/TestAssetsPage.tsx`: initialize state from mappings and write back after import/execution actions.
- Modify `tools/new-agents/frontend/src/pages/__tests__/TestAssetsPage.test.tsx`: restored-state and write-back tests.
- Modify `docs/todos/new-agents-evolution.md`: update P1 #7 status.

### Task 1: Backend Mapping Service

**Files:**
- Modify: `tools/new-agents/backend/models.py`
- Modify: `tools/new-agents/backend/test_assets.py`
- Test: `tools/new-agents/backend/tests/test_test_assets.py`

- [ ] **Step 1: Write failing tests**

Add tests that:

- Materialize a collection.
- Call `record_lisa_test_asset_intent_tester_case(collection_id, "TC-001", {"intentTesterCaseId": 42, "intentTesterCaseName": "TC-001 用户登录成功"})`.
- Assert `get_lisa_test_asset_collection(collection_id)["intentTesterMappings"][0]` includes the mapping.
- Call `record_lisa_test_asset_intent_tester_execution(...)` with an execution payload and assert `latestExecution` is persisted.
- Re-materialize with a changed artifact that still contains `TC-001` and assert mapping survives.
- Re-materialize with an artifact that removes `TC-001` and assert stale mapping is removed.

- [ ] **Step 2: Run RED**

Run:

```bash
cd tools/new-agents/backend && python3 -m pytest tests/test_test_assets.py -q
```

Expected: fail because record functions and mapping model do not exist.

- [ ] **Step 3: Implement model and service**

Add `AgentTestAssetIntentTesterMapping` with unique `(collection_id, source_case_id)`.

Add functions:

```python
def record_lisa_test_asset_intent_tester_case(collection_id: int, case_id: str, patch: dict) -> dict:
    ...

def record_lisa_test_asset_intent_tester_execution(collection_id: int, case_id: str, patch: dict) -> dict:
    ...
```

Add `_serialize_intent_tester_mapping(mapping)` and include `intentTesterMappings` in `_serialize_collection`.

- [ ] **Step 4: Run GREEN**

Run:

```bash
cd tools/new-agents/backend && python3 -m pytest tests/test_test_assets.py -q
```

Expected: all tests pass.

### Task 2: Backend Routes

**Files:**
- Modify: `tools/new-agents/backend/routes.py`
- Test: `tools/new-agents/backend/tests/test_agent_endpoint.py`

- [ ] **Step 1: Write failing endpoint tests**

Add tests for:

```http
PATCH /api/agent/test-assets/<collection_id>/intent-tester/cases/TC-001
PATCH /api/agent/test-assets/<collection_id>/intent-tester/cases/TC-001/execution
```

Assert route responses and collection detail payload include persisted mappings.

- [ ] **Step 2: Run RED**

Run:

```bash
cd tools/new-agents/backend && python3 -m pytest tests/test_agent_endpoint.py -q
```

Expected: fail because routes do not exist.

- [ ] **Step 3: Add routes**

Import the new service functions and wire validation errors to 400/404 based on message prefix.

- [ ] **Step 4: Run GREEN**

Run:

```bash
cd tools/new-agents/backend && python3 -m pytest tests/test_agent_endpoint.py -q
```

Expected: all tests pass.

### Task 3: Frontend Service and Asset Center

**Files:**
- Modify: `tools/new-agents/frontend/src/core/types.ts`
- Modify: `tools/new-agents/frontend/src/services/testAssetService.ts`
- Modify: `tools/new-agents/frontend/src/services/__tests__/testAssetService.test.ts`
- Modify: `tools/new-agents/frontend/src/pages/TestAssetsPage.tsx`
- Modify: `tools/new-agents/frontend/src/pages/__tests__/TestAssetsPage.test.tsx`

- [ ] **Step 1: Write failing frontend tests**

Service tests must parse `intentTesterMappings` and call:

```typescript
recordTestAssetIntentTesterCase(7, 'TC-001', { intentTesterCaseId: 42, intentTesterCaseName: 'TC-001 用户登录成功' })
recordTestAssetIntentTesterExecution(7, 'TC-001', execution)
```

Page tests must prove:

- Initial collection mapping renders `已导入 intent-tester #42` and `最近执行 exec-456 · success`.
- Import success calls `recordTestAssetIntentTesterCase`.
- Create/refresh execution calls `recordTestAssetIntentTesterExecution`.

- [ ] **Step 2: Run RED**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/testAssetService.test.ts src/pages/__tests__/TestAssetsPage.test.tsx
```

Expected: fail because parser/functions/page wiring do not exist.

- [ ] **Step 3: Implement frontend service and page wiring**

Add `TestAssetIntentTesterMapping` to collection type. Parse mapping array. In `TestAssetsPage`, initialize local maps from `collection.intentTesterMappings`, and record mappings after successful operations.

- [ ] **Step 4: Run GREEN**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/testAssetService.test.ts src/pages/__tests__/TestAssetsPage.test.tsx
```

Expected: all tests pass.

### Task 4: Verification and Todo

**Files:**
- Modify: `docs/todos/new-agents-evolution.md`

- [ ] **Step 1: Update todo**

Record that New Agents now persists intent-tester testcase/execution mapping and restores it in the asset center. Remaining work: true proxy-backed execution and rich result write-back.

- [ ] **Step 2: Run verification**

Run:

```bash
cd tools/new-agents/backend && python3 -m pytest tests/test_test_assets.py tests/test_agent_endpoint.py -q
cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/testAssetService.test.ts src/pages/__tests__/TestAssetsPage.test.tsx
cd tools/new-agents/frontend && npm run lint
git diff --check
```

Expected: all pass.
