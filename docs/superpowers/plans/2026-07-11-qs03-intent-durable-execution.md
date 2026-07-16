# QS-03 Intent Durable Execution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 Intent Tester 的真实 Flask→Node 执行、回调、停止与恢复共享同一个 durable execution ID。

**Architecture:** Flask `ExecutionHistory` 是状态权威；proxy client 只调 Node production app，Node 接收 Flask 生成的 ID 并回调 lifecycle endpoint。所有 callback 和 stop 都以状态转移和幂等规则保护。

**Tech Stack:** Flask/SQLAlchemy、Node Express、Jest/Supertest、pytest。

> 本计划全文只服务于 `QS-03` 一个厚切片。下面的 task/checkbox 是内部 TDD 步骤，不是可单独计进度、验收、提交或交付的子切片；只有完整用户链路和全部门禁收口后才结束 `QS-03`。

**切片身份基线：** [QS-03 中文 spec 的“厚切片身份基线”](../specs/2026-07-11-qs03-intent-durable-execution-design.md#厚切片身份基线)。

**历史顺序基线：** [已归档的 AI Coding 测试质量改进待办](../../todos/archive/2026-07-10-ai-coding-test-quality-improvement.md#厚切片序列)。该旧序列已于 2026-07-16 由用户取消，不再是当前执行入口。

## Global Constraints

- 不新增真实 AI provider 依赖；测试使用 fake adapter。
- 不改 QS-04 的认证/CSP 边界，不改 QS-05 部署事务。
- 所有执行器路径复用 canonical `execution_id`，非法状态显式失败。

### 内部实现步骤 1（非切片）：Durable lifecycle contract

**Files:**
- Modify: `tools/intent-tester/backend/api/executions.py`
- Modify: `tools/intent-tester/backend/services/database_service.py`
- Test: `tools/intent-tester/tests/api/test_execution_api.py`

- [x] 写失败测试：重复 started/result callback 仅保留一条 execution；终态不能被旧 callback 覆盖；非法 payload/未知 ID 返回 4xx。
- [x] 运行 `pytest tests/api/test_execution_api.py -q`，确认新增断言先失败。
- [x] 实现 `POST /executions/<execution_id>/lifecycle`，严格接受 `started|result`、`running|success|failed|stopped`，并在单事务内更新 `ExecutionHistory`/步骤快照。
- [x] 重新运行同一 pytest，确认通过。

### 内部实现步骤 2（非切片）：Canonical ID proxy dispatch and scoped stop

**Files:**
- Modify: `tools/intent-tester/backend/api/executions.py`
- Create: `tools/intent-tester/backend/services/proxy_execution_client.py`
- Test: `tools/intent-tester/tests/api/test_execution_api.py`

- [x] 写失败测试：创建 execution 调 proxy 时 body 包含 Flask ID；proxy 拒绝不把 DB 标为完成；stop 只发同一 ID。
- [x] 运行对应 pytest，确认失败。
- [x] 实现可注入 `ProxyExecutionClient`，创建后 dispatch、stop 后持久化 explicit 状态；网络失败返回可诊断错误而不伪造终态。
- [x] 运行对应 pytest，确认通过。

### 内部实现步骤 3（非切片）：Production Node contract

**Files:**
- Modify: `tools/intent-tester/browser-automation/midscene_server.js`
- Modify: `tools/intent-tester/tests/proxy/midscene-integration.test.js`
- Modify: `tools/intent-tester/tests/proxy/midscene-server-api.test.js`

- [x] 写失败 Jest：`/api/execute-testcase` 缺 `executionId` 返回 400；提供 ID 时 response/state/callback 全部使用该 ID；stop 不影响另一 execution。
- [x] 运行 `npm run test:proxy -- --runInBand`，确认失败。
- [x] 删除服务端随机 ID 路径，导出可启动 production app seam，并以 caller-supplied ID 创建 state/control。
- [x] 重新运行 Jest，确认通过。

### 内部实现步骤 4（非切片）：Complete the remaining canonical user loop and evidence

**Files:**
- Modify: `tools/intent-tester/frontend/templates/execution.html`
- Create: `tools/intent-tester/frontend/static/js/durable-execution-control.js`
- Create: `tools/intent-tester/tests/api/test_execution_page_contract.py`
- Create: `tools/intent-tester/tests/frontend/test_durable_execution_control.js`
- Test: `tools/intent-tester/tests/api/test_execution_page_contract.py`
- Test: `tools/intent-tester/tests/frontend/test_durable_execution_control.js`
- Modify: `tools/intent-tester/backend/api/executions.py`
- Test: `tools/intent-tester/tests/api/test_execution_api.py`
- Create: `tools/intent-tester/tests/integration/test_durable_execution_loop.py`
- Modify: `scripts/ci/build-proxy-package.js`
- Create: `tools/intent-tester/proxy_templates/.env.example`
- Modify: `dist/intent-test-proxy/**`（生成产物）
- Modify: `dist/intent-test-proxy.zip`（生成产物）
- Modify: `tools/intent-tester/frontend/static/intent-test-proxy.zip`（同步生成产物）
- Create: `tools/intent-tester/tests/integration/test_proxy_package_smoke.py`

- [x] 写失败页面契约测试：Flask create 是唯一 dispatch；页面直接采用返回的 `execution_id`，stop/status 都走 Flask durable API，不再二次直调 Node。
- [x] 删除页面 `/api/execute-testcase` 二次 dispatch、Node stop/status 旁路与 `local_execution_id` 竞争源，保留 WebSocket 仅作为同 ID 的可见进度通道。
- [x] 用 deferred-promise Node 测试保护 completion 先于 lifecycle callback 的有界终态对账、旧 refresh 乱序隔离、stop 非成功保留可重试状态与延迟进度事件 ID 复核。
- [x] 运行页面契约与 execution API 回归，确认通过。
- [x] 写失败 API 测试并实现 `POST /executions/<execution_id>/retry`：仅复用 pending/running 的 canonical ID，terminal 状态显式拒绝，dispatch 失败保留可诊断原状态。
- [x] 页面在 create 502 含 canonical ID 或 durable 对账耗尽时保留同一任务并显示 retry；retry 失败保持可重试，成功后继续同 ID durable reconciliation。
- [x] 写 real HTTP 测试：Flask 创建一次、Node fixture started/result 回调、重启 Flask 后 GET 仍返回同一终态；duplicate callback 不复制 steps；stop/retry 有解释状态。
- [x] 运行该 pytest，确认失败。
- [x] 以 production Node app 和 fake Playwright/AI 边界完成组合测试；运行 API、real HTTP 与 proxy Jest 回归。
- [x] 写失败测试：tracked zip 与 deterministic builder 输出一致，包含当前 production server、lockfile 与 `.env.example`。
- [x] 收口现有 `scripts/ci/build-proxy-package.js` 为 deterministic builder，过滤缓存、包含 lockfile/配置模板，并机械同步两个 zip 与展开目录。
- [x] 从干净临时目录解压下载 zip，使用已安装依赖边界启动 production server 并验证 `/health`；缺必要配置必须显式失败。
- [x] 运行 package smoke、下载 API 与 Intent 模块回归；记录 clean-room 证明与依赖边界。

### QS-03 整片验证与交付（唯一交付边界）

- [x] 用 `superpowers:requesting-code-review` 按标准与 spec 两轴复审。
- [x] 完成全量 Intent/Python、Node proxy、必要浏览器验证；更新 `docs/todos/2026-07-10-ai-coding-test-quality-improvement.md` 的 QS-03 证据。
- [x] 精确暂存并提交一个 `feat(intent): 收口真实执行持久化闭环` 提交；远端可用则按 Playbook 推送。
