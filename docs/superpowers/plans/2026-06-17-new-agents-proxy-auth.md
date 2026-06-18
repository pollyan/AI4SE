# New Agents Proxy Auth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:systematic-debugging, superpowers:test-driven-development, and superpowers:verification-before-completion.

**Goal:** Fix the `PROXY_API_KEY` deployment mode so browser traffic through the Nginx gateway can use New Agents endpoints without exposing the backend proxy key to frontend code, while direct backend calls remain protected.

**Architecture:** Keep `PROXY_API_KEY` server-side. Nginx marks trusted internal gateway traffic with `X-AI4SE-Gateway: new-agents`. The backend accepts either a correct `X-API-Key` or that internal gateway marker. Docker Compose keeps `new-agents-backend` off host ports so external callers cannot rely on spoofing the internal marker.

**Tech Stack:** Flask middleware, Nginx reverse proxy, Docker Compose, pytest contracts.

### Task 1: Capture Auth Contract

**Files:**
- Modify: `tools/new-agents/backend/tests/test_api_auth.py`

- [x] **Step 1: Add failing tests**

Added coverage for:
- Gateway-forwarded `/api/agent/runs/stream` POST with `X-AI4SE-Gateway: new-agents` should not fail at auth.
- Gateway-forwarded Mermaid repair POST should not fail at auth.
- Wrong gateway marker should still return 401.

### Task 2: Implement Gateway Auth Boundary

**Files:**
- Modify: `tools/new-agents/backend/app.py`
- Modify: `nginx/nginx.conf`

- [x] **Step 1: Allow trusted gateway marker**

Backend auth now accepts either the configured `X-API-Key` or `X-AI4SE-Gateway: new-agents`.

- [x] **Step 2: Inject gateway marker in Nginx**

`/new-agents/api/` proxy block now sets `X-AI4SE-Gateway new-agents`.

### Task 3: Fix Compose Deployment Boundary

**Files:**
- Modify: `docker-compose.dev.yml`
- Modify: `docker-compose.dev-cn.yml`
- Modify: `docker-compose.prod.yml`

- [x] **Step 1: Keep backend API internal**

Removed dev/dev-cn host `5002:5002` mappings for `new-agents-backend`; prod already had no backend host port.

- [x] **Step 2: Move New Agents env vars to the owning service**

Moved `NEW_AGENTS_DEFAULT_LLM_*` variables from `intent-tester` to `new-agents-backend`, and added `PROXY_API_KEY` to `new-agents-backend`.

### Task 4: Verification

- [x] **Step 1: Python syntax check**

`/Users/anhui/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m py_compile tools/new-agents/backend/app.py tools/new-agents/backend/tests/test_api_auth.py`

- [x] **Step 2: Search for secret leakage**

`rg "X-AI4SE-Gateway|PROXY_API_KEY|NEW_AGENTS_DEFAULT_LLM" nginx/nginx.conf docker-compose.dev.yml docker-compose.dev-cn.yml docker-compose.prod.yml tools/new-agents/backend/app.py tools/new-agents/backend/tests/test_api_auth.py tools/new-agents/frontend/src`

Result: no `PROXY_API_KEY` usage in frontend source.

- [x] **Step 3: Compose config validation**

`docker compose -f docker-compose.dev.yml config --services`

`docker compose -f docker-compose.dev-cn.yml config --services`

`docker compose -f docker-compose.prod.yml config --services`

`docker compose -f docker-compose.dev.yml config new-agents-backend`

`docker compose -f docker-compose.dev-cn.yml config new-agents-backend`

`docker compose -f docker-compose.prod.yml config new-agents-backend`

Result: services render successfully; `new-agents-backend` has New Agents env vars and no host port mapping.

- [ ] **Step 4: Backend pytest**

Blocked in the current local environment: `python3` / `pytest` point to Python 3.14 and hang before output; Codex bundled Python lacks backend test dependencies.

- [ ] **Step 5: Nginx syntax test**

Blocked locally: no `nginx` binary; Docker API permission denied for image inspection, so containerized `nginx -t` was not run.
