# Lisa Test Asset Issue Status Persistence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist Lisa test asset issue triage status through backend storage and frontend API wiring.

**Architecture:** Store issue status on `AgentTestAssetIssue`, serialize it with issue ids, expose a focused PATCH endpoint, and have the existing Header test asset modal update from the backend response.

**Tech Stack:** Python 3.11, Flask, SQLAlchemy, Pytest, React, TypeScript, Vitest, Testing Library.

---

### Task 1: Backend Persistence

**Files:**
- Modify: `tools/new-agents/backend/models.py`
- Modify: `tools/new-agents/backend/test_assets.py`
- Modify: `tools/new-agents/backend/tests/test_test_assets.py`
- Modify: `tools/new-agents/backend/routes.py`
- Modify: `tools/new-agents/backend/tests/test_agent_endpoint.py`

- [x] **Step 1: Write failing backend tests**

Add tests that materialized asset issues include `id` and `status: "pending"`, and that `update_lisa_test_asset_issue_status(collectionId, issueId, {"status": "confirmed"})` persists `confirmed` in `get_lisa_test_asset_collection()`.

- [x] **Step 2: Run backend tests to verify RED**

Run: `cd tools/new-agents/backend && python3 -m pytest tests/test_test_assets.py -k "issue_status" -q`

Expected: fail because issues have no status update function yet.

- [x] **Step 3: Implement model, serialization, and service function**

Add `status` column, default new issues to `pending`, serialize `id/status`, and implement status update validation.

- [x] **Step 4: Add route and endpoint test**

Add the PATCH route and a route-level test that confirms `PATCH /api/agent/test-assets/{collectionId}/issues/{issueId}` returns updated issue JSON.

- [x] **Step 5: Run backend tests to verify GREEN**

Run: `cd tools/new-agents/backend && python3 -m pytest tests/test_test_assets.py tests/test_agent_endpoint.py -q`

Expected: backend tests pass.

### Task 2: Frontend Service And UI

**Files:**
- Modify: `tools/new-agents/frontend/src/core/types.ts`
- Modify: `tools/new-agents/frontend/src/services/testAssetService.ts`
- Modify: `tools/new-agents/frontend/src/services/__tests__/testAssetService.test.ts`
- Modify: `tools/new-agents/frontend/src/components/Header.tsx`
- Modify: `tools/new-agents/frontend/src/components/__tests__/Header.test.tsx`

- [x] **Step 1: Write failing frontend tests**

Add service test for `updateTestAssetIssueStatus()` and update Header issue triage test to expect the service call.

- [x] **Step 2: Run frontend tests to verify RED**

Run: `cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/testAssetService.test.ts src/components/__tests__/Header.test.tsx -t "issue status|triages Lisa"`

Expected: fail because the service does not exist and Header still uses local-only status.

- [x] **Step 3: Implement frontend service and parser changes**

Add `id/status` parsing and `updateTestAssetIssueStatus(collectionId, issueId, status)`.

- [x] **Step 4: Wire Header buttons to the service**

Call the service from issue status buttons and replace the matching issue in `testAssetCollection.assetIssues`.

- [x] **Step 5: Run frontend tests to verify GREEN**

Run: `cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/testAssetService.test.ts src/components/__tests__/Header.test.tsx`

Expected: frontend tests pass.

### Task 3: Todo Record And Verification

**Files:**
- Modify: `docs/todos/new-agents-evolution.md`

- [x] **Step 1: Update progress record**

Add a dated P1 #7 note that issue status is now persisted through backend PATCH and frontend service/UI.

- [x] **Step 2: Run focused verification**

Run backend and frontend focused suites:

`cd tools/new-agents/backend && python3 -m pytest tests/test_test_assets.py tests/test_agent_endpoint.py -q`

`cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/testAssetService.test.ts src/components/__tests__/Header.test.tsx`

- [x] **Step 3: Run TypeScript check and diff check**

Run:

`cd tools/new-agents/frontend && npm run lint`

`git diff --check`
