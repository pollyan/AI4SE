# New Agents LLM Config Current Form Check Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make SettingsModal “检测连接” validate the current form config instead of stale saved defaults, without persisting temporary values.

**Architecture:** Preserve `/api/config/check` compatibility. Add request-body semantics for temporary form checks, reuse the existing model connectivity helper, and keep API keys write-only.

**Tech Stack:** React, Flask, Pydantic request schemas, SQLAlchemy model object, Vitest, pytest.

---

### Task 1: Red Tests

**Files:**
- Modify: `tools/new-agents/frontend/src/components/__tests__/SettingsModal.test.tsx`
- Modify: `tools/new-agents/backend/tests/test_api.py`

- [x] **Step 1: Frontend form payload test**

Update the settings check test to change `baseUrl`, `model`, `description`, and `apiKey`, click “检测连接”, and assert fetch was called with JSON body for the current form values.

- [x] **Step 2: Frontend notification boundary**

Update the successful check test to assert `notifyDefaultLlmConfigChanged` is not called by a temporary form check.

- [x] **Step 3: Backend temporary config test**

Add an API test that posts JSON to `/api/config/check`, mocks `routes.check_default_llm_config`, and asserts the helper receives the temporary `apiKey`, `base_url`, and `model`. Assert the DB saved default remains unchanged.

- [x] **Step 4: Backend saved key reuse test**

Add an API test that posts JSON without `apiKey` while a saved default exists. Assert the helper receives the saved secret plus temporary `baseUrl` and `model`.

### Task 2: Implementation

**Files:**
- Modify: `tools/new-agents/frontend/src/components/SettingsModal.tsx`
- Modify: `tools/new-agents/backend/config_service.py`
- Modify: `tools/new-agents/backend/routes.py`

- [x] **Step 1: Frontend sends current form**

Build the same trimmed payload as save and send it as JSON in `handleCheckConfig`.

- [x] **Step 2: Backend temporary config builder**

Add a helper that builds a transient `LlmConfig` from `DefaultLlmConfigUpdateRequest` and optional saved default config. Use `update.api_key` or saved `api_key`; raise `ValueError("apiKey 不能为空")` when neither exists.

- [x] **Step 3: Route body branch**

In `/api/config/check`, if `_read_json_body()` returns data, parse it and check the transient config. If no body exists, keep the old default-config behavior.

### Task 3: Verify and Archive

- [x] **Step 1: Run backend focused tests**

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_api.py tools/new-agents/backend/tests/test_config_service.py -q
```

- [x] **Step 2: Run frontend focused tests**

```bash
cd tools/new-agents/frontend && npm run test -- src/components/__tests__/SettingsModal.test.tsx src/services/__tests__/configService.test.ts
```

- [x] **Step 3: Run broad verification**

Run `./scripts/test/test-local.sh all`; if sandbox blocks ports or Chromium, rerun with elevated permissions and record both.

- [x] **Step 4: Archive todo**

Move the completed todo to `docs/todos/archive/` and remove it from `docs/todos/refactor/README.md`.
