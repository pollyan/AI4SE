# New Agents 智能体重构阶段 3 第一批计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` for independent implementation slices, or `superpowers:executing-plans` for serial implementation. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在阶段 1/2 契约护栏稳定后，开始拆分过大的共享模块。第一批只做 backend route 文件分组，保持所有 URL、HTTP method、request/response JSON 和 runtime 行为不变。

**Architecture:** 继续保留单一 `new_agents_api` blueprint 和 `/api` prefix。拆分方式是让 `routes.py` 保留 blueprint、通用 helper 和 route registration 入口，test assets 相关 route 移入独立模块并注册到同一 blueprint，不新增 API path 或 workflow-specific runtime。

**Tech Stack:** Python 3.11, Flask, pytest.

---

## Current State Gap Analysis

### 事实源快照

已读取：

- `docs/todos/refactor/2026-06-21-new-agents-refactor-options.md`
- `docs/todos/refactor/2026-06-21-new-agents-refactor-phase1-plan.md`
- `docs/todos/refactor/2026-06-21-new-agents-refactor-phase2-plan.md`
- `tools/new-agents/backend/routes.py`
- `tools/new-agents/backend/app.py`
- `tools/new-agents/backend/tests/test_routes_blueprint.py`
- `tools/new-agents/backend/tests/test_backend_layering.py`
- `tools/new-agents/backend/tests/test_api.py`
- `tools/new-agents/backend/tests/test_mermaid_repair_endpoint.py`

### 能力包聚合

| 能力包 | 聚合的原始缺口 | 工程信任闭环 | 为什么不能再拆薄 | 验收证据 |
| --- | --- | --- | --- | --- |
| Backend route 分组闭环 | `routes.py` 同时承载 runtime、config、observability、test assets、handoff、mermaid repair | test assets route 从主 routes 文件分离，但仍注册到同一 blueprint 和同一路径 | 只移动一个 endpoint 没有结构收益；一次移动所有 backend 大模块风险过高 | route blueprint tests、test asset endpoint tests、agent endpoint tests |

### 候选 Gap

| 候选 | 目标态 | 当前能力 | 缺口 | 价值 | 风险/复杂度 | 去向 |
| --- | --- | --- | --- | --- | --- | --- |
| Backend route 分组闭环 | `routes.py` 不再直接承载 Lisa test assets endpoint 实现 | URL 行为可用，但 routes 文件混合通用 runtime 和 workflow 特化资产 API | 后续更多资产 API 容易继续堆进主 blueprint 文件 | 降低特化 API 污染主 runtime route 的风险 | 中 | 目标模式第 6 轮 |
| `run_persistence.py` repository 边界 | 按 message/artifact/collaboration/metrics 分层 | 功能可用但文件大 | 拆分范围更大，需更完整持久化测试 | 长期维护收益 | 高 | 后续轮 |
| `ArtifactPane.tsx` 模块化 | UI 子组件和 pure helpers 拆分 | 功能复杂但测试多 | UI 回归面最大 | 长期维护收益 | 高 | 后续可选轮 |

### 排序结论

1. 先做 route 文件分组，因为它可保持 URL 完全兼容，且能把 Lisa test assets 特化能力从主 runtime route 文件移出。
2. 暂不拆 `run_persistence.py`、`test_assets.py` 内部服务和 `ArtifactPane.tsx`，避免同时扩大持久化与 UI 回归面。

## 目标模式第 6 轮：Backend route 分组闭环

### 目标

将 test assets HTTP route handlers 从 `routes.py` 移入 `routes_test_assets.py`，但仍注册在同一个 `api_bp` 上，保持所有路径兼容：

- `/api/agent/runs/<run_id>/test-assets`
- `/api/agent/runs/<run_id>/test-assets/materialize`
- `/api/agent/test-assets/<collection_id>`
- `/api/agent/test-assets/<collection_id>/test-cases/<case_id>`
- `/api/agent/test-assets/<collection_id>/issues/<issue_id>`
- `/api/agent/test-assets/<collection_id>/intent-tester/cases/<case_id>`
- `/api/agent/test-assets/<collection_id>/intent-tester/cases/<case_id>/execution`
- `/api/agent/test-assets/<collection_id>/intent-tester/cases/<case_id>/result`
- `/api/agent/test-assets/<collection_id>/test-points/<test_point>`
- risk create/update/delete endpoints

### 文件范围

- Modify: `tools/new-agents/backend/routes.py`
- Create: `tools/new-agents/backend/routes_test_assets.py`
- Modify: `tools/new-agents/backend/tests/test_routes_blueprint.py`
- Modify or run: `tools/new-agents/backend/tests/test_test_assets.py`
- Run: relevant API/endpoint tests.

### TDD 任务

- [x] **Step 1: route split RED**

  在 `test_routes_blueprint.py` 中新增测试，断言 `routes.py` 不再直接包含 `def agent_run_test_assets`，并且 source 包含 `register_test_asset_routes(api_bp)`。

- [x] **Step 2: create `routes_test_assets.py`**

  把 test assets endpoint handlers 和对应 error status helpers 移入新文件，提供 `register_test_asset_routes(api_bp)`。所有 decorators 继续挂在传入的 `api_bp` 上，不创建新 blueprint。

- [x] **Step 3: simplify `routes.py`**

  从 `routes.py` 删除 test assets endpoint 实现和相关 imports，只保留 `from routes_test_assets import register_test_asset_routes` 并在 `api_bp` 创建后调用。

- [x] **Step 4: run verification**

  ```bash
  /Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest tools/new-agents/backend/tests/test_routes_blueprint.py tools/new-agents/backend/tests/test_backend_layering.py tools/new-agents/backend/tests/test_test_assets.py tools/new-agents/backend/tests/test_agent_endpoint.py -q
  git diff --check
  ```

### 执行记录

- RED: `test_routes_module_delegates_test_asset_routes` 先失败，证明 `routes.py` 仍直接承载 test assets endpoint。
- GREEN: 新增 `routes_test_assets.py`，通过 `register_test_asset_routes(api_bp)` 把原 test assets handlers 注册回同一个 `new_agents_api` blueprint。
- 验证:
  - `/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest tools/new-agents/backend/tests/test_routes_blueprint.py tools/new-agents/backend/tests/test_backend_layering.py tools/new-agents/backend/tests/test_test_assets.py tools/new-agents/backend/tests/test_agent_endpoint.py -q` -> `89 passed`
  - `git diff --check` -> passed

### 完成标准

- 所有 test assets URL 保持不变。
- `api_bp.name == "new_agents_api"` 且 `api_bp.url_prefix == "/api"` 不变。
- `routes.py` 继续承载通用 runtime/config/handoff/mermaid repair routes，但不再直接实现 test assets endpoints。
- 不新增 `/api/lisa/*`、`/api/alex/*` 或独立 workflow-specific blueprint。
