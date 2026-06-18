# New Agents Default LLM Config Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development and superpowers:systematic-debugging. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the New Agents backend able to initialize and maintain the active `llm_config.default` record from deployment environment variables so the Agent Runtime has a reliable first-run configuration path.

**Architecture:** Keep API Keys server-side. The backend owns `llm_config`; frontend remains read-only for `/api/config`. `config_service.py` should parse and upsert env-sourced defaults. `app.py` should expose `init_db(...)` for startup and maintenance scripts, and production scripts should call that supported entry point.

**Tech Stack:** Flask, SQLAlchemy, pytest, Docker Compose env injection.

### Task 1: Add Service-Level Env Initialization Contract

**Files:**
- Modify: `tools/new-agents/backend/config_service.py`
- Modify: `tools/new-agents/backend/tests/test_config_service.py`

- [x] **Step 1: Write RED tests**

Cover:
- Complete env values create an active `default` config.
- Complete env values update and reactivate an existing inactive `default` config.
- Missing `NEW_AGENTS_DEFAULT_LLM_API_KEY` or `NEW_AGENTS_DEFAULT_LLM_MODEL` does not create a partial config.
- Public payload still excludes `api_key`.

- [x] **Step 2: Implement minimal service**

Add `upsert_default_llm_config_from_env(...)` with explicit env names:
- `NEW_AGENTS_DEFAULT_LLM_API_KEY`
- `NEW_AGENTS_DEFAULT_LLM_BASE_URL`
- `NEW_AGENTS_DEFAULT_LLM_MODEL`
- `NEW_AGENTS_DEFAULT_LLM_DESCRIPTION`

Default `base_url` to `https://api.openai.com/v1` when API key and model are present but base URL is omitted.

### Task 2: Restore Supported DB Initialization Entry Point

**Files:**
- Modify: `tools/new-agents/backend/app.py`
- Modify: `tools/new-agents/backend/tests/test_api.py`
- Modify: `scripts/migrate_llm_config_prod.sh`

- [x] **Step 1: Write RED test**

Assert `init_db(app)` can be imported and creates/seeds the default config from env.

- [x] **Step 2: Implement `init_db(app)`**

Move startup `db.create_all()` into `init_db(app)` and call `upsert_default_llm_config_from_env()` after tables exist.

- [x] **Step 3: Keep migration script on supported API**

Update `scripts/migrate_llm_config_prod.sh` to call `init_db(app)` without relying on manual app context push order.

### Task 3: Wire Docker Env

**Files:**
- Modify: `docker-compose.dev.yml`
- Modify: `docker-compose.dev-cn.yml`
- Modify: `docker-compose.prod.yml`

- [x] **Step 1: Pass New Agents default LLM env vars into backend container**

Add the four `NEW_AGENTS_DEFAULT_LLM_*` variables to the `new-agents-backend` service.

### Task 4: Verification And Debt Record

**Files:**
- Modify: `docs/plans/tech-debt.md`

- [ ] **Step 1: Run focused backend tests**

Run:

```bash
cd tools/new-agents/backend && python3 -m pytest tests/test_config_service.py tests/test_api.py
```

Blocked in the current local environment: both `python3` and `pytest` point to Python 3.14 and hang before producing output; Codex bundled Python does not include `pytest`, `flask`, or `flask_sqlalchemy`.

- [x] **Step 2: Run import/compile fallback if pytest is blocked**

If local Python cannot run pytest, verify the touched Python files with a Python runtime that is available and record the pytest blocker.

Completed fallback checks:
- `/Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m py_compile tools/new-agents/backend/config_service.py tools/new-agents/backend/app.py tools/new-agents/backend/tests/test_config_service.py tools/new-agents/backend/tests/test_api.py`
- `bash -n scripts/migrate_llm_config_prod.sh`
- `rg "NEW_AGENTS_DEFAULT_LLM" docker-compose.dev.yml docker-compose.dev-cn.yml docker-compose.prod.yml tools/new-agents/backend tools/new-agents/backend/tests scripts/migrate_llm_config_prod.sh`

- [x] **Step 3: Update debt record**

Record the fix and verification evidence under the 2026-06-17 New Agents functional issues section.
