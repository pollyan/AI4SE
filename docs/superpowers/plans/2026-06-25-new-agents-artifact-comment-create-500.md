# New Agents Artifact Comment Create 500 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Artifact comment collaboration saves reliable and diagnosable, without adding a dedicated comment API or changing shared persistence contracts.

**Architecture:** Keep the shared Artifact collaboration state endpoint and shared UI/store path. Add route-level persistence error handling and frontend API error parsing.

**Tech Stack:** Flask, SQLAlchemy, React service layer, pytest, Vitest.

---

### Task 1: Red Tests

**Files:**
- Modify: `tools/new-agents/backend/tests/test_agent_endpoint.py`
- Modify: `tools/new-agents/frontend/src/services/__tests__/runSnapshotService.test.ts`

- [x] **Step 1: Backend persistence error response**

Add an endpoint test that makes `replace_artifact_collaboration_state` raise `SQLAlchemyError` and asserts the route returns JSON `{ "error": "协作状态保存失败" }` with status 500.

- [x] **Step 2: Backend missing artifact response**

Add an endpoint or persistence test proving a run without an artifact version cannot save non-empty comments and returns a 400 diagnostic error.

- [x] **Step 3: Frontend service error message**

Add a service test that mocks a non-2xx collaboration response with JSON `error` and asserts the thrown error includes that message.

- [x] **Step 4: Frontend rollback on failed sync**

Add a component test that rejects collaboration sync and asserts the new local comment is removed while the error message is shown.

### Task 2: Implementation

**Files:**
- Modify: `tools/new-agents/backend/routes.py`
- Modify: `tools/new-agents/backend/run_persistence.py`
- Modify: `tools/new-agents/frontend/src/services/runSnapshotService.ts`
- Modify: `tools/new-agents/frontend/src/components/ArtifactPane.tsx`

- [x] **Step 1: Backend artifact precondition**

Require referenced collaboration stages to have persisted artifact versions; allow empty collaboration state replacement.

- [x] **Step 2: Backend catch and rollback**

Catch `SQLAlchemyError` in `agent_run_artifact_collaboration_update`, rollback the session, log request id and run id, and return a uniform JSON error response.

- [x] **Step 3: Frontend parse JSON error**

In `updateRunArtifactCollaboration`, parse error JSON when possible and include `error` in the thrown message.

- [x] **Step 4: Frontend rollback failed optimistic update**

Pass explicit next collaboration state to sync and restore previous state on failure.

### Task 3: Verify and Archive

- [x] **Step 1: Run focused backend tests**

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_agent_endpoint.py tools/new-agents/backend/tests/test_run_persistence.py -q
```

- [x] **Step 2: Run focused frontend tests**

```bash
cd tools/new-agents/frontend && npm run test -- src/services/__tests__/runSnapshotService.test.ts src/components/__tests__/ArtifactPane.test.tsx
```

- [x] **Step 3: Run broad verification**

Run `./scripts/test/test-local.sh all`; if sandbox blocks ports or Chromium, rerun with elevated permissions and record both.

- [x] **Step 4: Archive todo**

Move the completed todo to `docs/todos/archive/` and remove it from `docs/todos/refactor/README.md`.
