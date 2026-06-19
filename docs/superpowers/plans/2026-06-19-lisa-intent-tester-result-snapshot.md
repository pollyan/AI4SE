# Lisa Intent Tester Result Snapshot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let Lisa asset center pull an intent-tester execution detail, persist a compact result snapshot in New Agents, and restore that result after refresh.

**Architecture:** Keep true browser execution in intent-tester. New Agents stores a compact projection on the existing `AgentTestAssetIntentTesterMapping`, exposes it through the existing collection detail payload, and lets the asset center explicitly “承接执行结果” for a known execution ID.

**Tech Stack:** Flask, Flask-SQLAlchemy, pytest, React, TypeScript, Vitest, Testing Library.

---

## File Map

- Modify `tools/new-agents/backend/models.py`: add `latest_execution_result_json`.
- Modify `tools/new-agents/backend/test_assets.py`: normalize and serialize result snapshots.
- Modify `tools/new-agents/backend/routes.py`: add result snapshot route.
- Modify `tools/new-agents/backend/tests/test_test_assets.py`: service tests.
- Modify `tools/new-agents/backend/tests/test_agent_endpoint.py`: API tests.
- Modify `tools/new-agents/frontend/src/core/types.ts`: add result snapshot and step types.
- Modify `tools/new-agents/frontend/src/services/intentTesterExecutionService.ts`: fetch execution detail with steps.
- Modify `tools/new-agents/frontend/src/services/__tests__/intentTesterExecutionService.test.ts`: parser tests.
- Modify `tools/new-agents/frontend/src/services/testAssetService.ts`: parse and record result snapshots.
- Modify `tools/new-agents/frontend/src/services/__tests__/testAssetService.test.ts`: New Agents result record tests.
- Modify `tools/new-agents/frontend/src/pages/TestAssetsPage.tsx`: add result handoff action and display.
- Modify `tools/new-agents/frontend/src/pages/__tests__/TestAssetsPage.test.tsx`: UI tests.
- Modify `docs/todos/new-agents-evolution.md`: update remaining scope.

### Task 1: Backend Result Snapshot

**Files:**
- Modify: `tools/new-agents/backend/models.py`
- Modify: `tools/new-agents/backend/test_assets.py`
- Test: `tools/new-agents/backend/tests/test_test_assets.py`

- [ ] **Step 1: Write failing tests**

Add a test that imports a source case into intent-tester mapping, calls:

```python
record_lisa_test_asset_intent_tester_result(collection["id"], "TC-001", {
    "executionId": "exec-456",
    "status": "failed",
    "duration": 60,
    "errorMessage": "断言失败",
    "steps": [
        {"stepIndex": 0, "description": "打开登录页", "status": "success", "screenshotPath": "/static/screenshots/0.png", "action": "ai_assert"},
        {"stepIndex": 1, "description": "验证预期结果", "status": "failed", "errorMessage": "未看到工作台", "screenshotPath": "/static/screenshots/1.png", "action": "ai_assert"}
    ]
})
```

Assert `latestResult` contains `stepsTotal: 2`, `stepsPassed: 1`, `stepsFailed: 1`, screenshots, and failed step details. Assert collection reload preserves it.

- [ ] **Step 2: Run RED**

Run:

```bash
cd tools/new-agents/backend && python3 -m pytest tests/test_test_assets.py -q
```

Expected: fail because the result function/field does not exist.

- [ ] **Step 3: Implement model/service**

Add `latest_execution_result_json` to mapping model. Add `record_lisa_test_asset_intent_tester_result`, `_normalize_intent_tester_result_snapshot`, and include `latestResult` in mapping serialization.

- [ ] **Step 4: Run GREEN**

Run:

```bash
cd tools/new-agents/backend && python3 -m pytest tests/test_test_assets.py -q
```

Expected: pass.

### Task 2: Backend Result Route

**Files:**
- Modify: `tools/new-agents/backend/routes.py`
- Test: `tools/new-agents/backend/tests/test_agent_endpoint.py`

- [ ] **Step 1: Write failing endpoint test**

Add a test for:

```http
PATCH /api/agent/test-assets/<collection_id>/intent-tester/cases/TC-001/result
```

Assert response and collection detail include `latestResult`.

- [ ] **Step 2: Run RED**

Run:

```bash
cd tools/new-agents/backend && python3 -m pytest tests/test_agent_endpoint.py -q
```

Expected: 404 route failure.

- [ ] **Step 3: Add route**

Wire the result service into `routes.py`, using the existing intent-tester mapping error status helper.

- [ ] **Step 4: Run GREEN**

Run:

```bash
cd tools/new-agents/backend && python3 -m pytest tests/test_agent_endpoint.py -q
```

Expected: pass.

### Task 3: Frontend Services

**Files:**
- Modify: `tools/new-agents/frontend/src/core/types.ts`
- Modify: `tools/new-agents/frontend/src/services/intentTesterExecutionService.ts`
- Modify: `tools/new-agents/frontend/src/services/__tests__/intentTesterExecutionService.test.ts`
- Modify: `tools/new-agents/frontend/src/services/testAssetService.ts`
- Modify: `tools/new-agents/frontend/src/services/__tests__/testAssetService.test.ts`

- [ ] **Step 1: Write failing frontend service tests**

Add parser tests for intent-tester detail response:

```typescript
await fetchIntentTesterExecutionDetail('exec-456')
```

Expect fetch `/intent-tester/api/executions/exec-456` and parsed steps. Add test asset service test for `recordTestAssetIntentTesterResult`.

- [ ] **Step 2: Run RED**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/intentTesterExecutionService.test.ts src/services/__tests__/testAssetService.test.ts
```

Expected: fail because functions/types are absent.

- [ ] **Step 3: Implement services**

Add `IntentTesterExecutionDetail`, `IntentTesterExecutionStep`, `TestAssetIntentTesterResultSnapshot`, and `recordTestAssetIntentTesterResult`.

- [ ] **Step 4: Run GREEN**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/intentTesterExecutionService.test.ts src/services/__tests__/testAssetService.test.ts
```

Expected: pass.

### Task 4: Asset Center Result Handoff

**Files:**
- Modify: `tools/new-agents/frontend/src/pages/TestAssetsPage.tsx`
- Modify: `tools/new-agents/frontend/src/pages/__tests__/TestAssetsPage.test.tsx`

- [ ] **Step 1: Write failing UI tests**

Add tests that:

- Render a persisted mapping with `latestResult`, assert result summary is visible after load.
- Click `承接执行结果 #exec-456`, assert intent-tester detail fetch and New Agents record function are called, then assert failed step appears.

- [ ] **Step 2: Run RED**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/pages/__tests__/TestAssetsPage.test.tsx
```

Expected: fail because UI action/display is absent.

- [ ] **Step 3: Implement UI**

Add result state from persisted mappings. Render summary and failed step details inside the existing intent-tester panel. Add `承接执行结果` button for mappings with latest execution.

- [ ] **Step 4: Run GREEN**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/pages/__tests__/TestAssetsPage.test.tsx
```

Expected: pass.

### Task 5: Verification and Todo

**Files:**
- Modify: `docs/todos/new-agents-evolution.md`

- [ ] **Step 1: Update todo**

Record that New Agents can now persist intent-tester result snapshots and restore them in the asset center. Remaining scope: proxy-backed automatic execution and richer result-to-asset-version policy.

- [ ] **Step 2: Run verification**

Run:

```bash
cd tools/new-agents/backend && python3 -m pytest tests/test_test_assets.py tests/test_agent_endpoint.py -q
cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/intentTesterExecutionService.test.ts src/services/__tests__/testAssetService.test.ts src/pages/__tests__/TestAssetsPage.test.tsx
cd tools/new-agents/frontend && npm run lint
git diff --check
```

Expected: all pass.
