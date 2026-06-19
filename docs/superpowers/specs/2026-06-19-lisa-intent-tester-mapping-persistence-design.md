# Lisa Intent Tester Mapping Persistence Design

## Current State Gap Analysis

Lisa 测试资产中心已经可以在用例卡片里导入 intent-tester 草稿、创建执行记录、刷新最近执行状态，并跳转到 `/intent-tester/execution?testcase_id=<id>`。但这些 import/execution 状态仍保存在 React 页面内存中。

这导致用户可感知断点：

- 刷新资产中心后，已导入的 intent-tester testcase ID 消失。
- 创建或刷新到的最近执行记录不会随集合详情接口返回。
- Header 弹层和资产中心会形成两套临时状态，无法沉淀到 New Agents 的测试资产集合。
- 后续“真实自动执行”和“结果回写”缺少 New Agents 侧稳定 mapping。

## Slice Thickness Gate

本切片必须交付一个完整、可感知的恢复性能力包，而不是单个字段或单个接口：

- 后端能在测试资产集合中持久化 Lisa source case 与 intent-tester testcase 的映射。
- 后端能持久化该映射上的最近 intent-tester execution 摘要。
- `GET /api/agent/test-assets/<collection_id>` 返回这些映射，刷新资产中心后仍能展示已导入状态和最近执行状态。
- 重新 materialize 同一集合时，仍存在的 source case 保留映射；已经不存在的 source case 映射被清理。
- 前端导入、创建执行记录、刷新执行结果后同步写回 New Agents 后端，之后页面重新加载可恢复。

## Scope

### In Scope

- 新增 `AgentTestAssetIntentTesterMapping` SQLAlchemy 模型。
- 在 `AgentTestAssetCollection` 下增加 `intentTesterMappings` 序列化字段。
- 新增 New Agents 后端接口：
  - `PATCH /api/agent/test-assets/<collection_id>/intent-tester/cases/<case_id>`
  - `PATCH /api/agent/test-assets/<collection_id>/intent-tester/cases/<case_id>/execution`
- 前端 `testAssetService` 增加 mapping parser 和 record API。
- `TestAssetsPage` 初始加载时从 persisted mapping 初始化卡片状态。
- 导入 intent-tester、创建执行记录、刷新最近执行状态后写回 New Agents mapping。
- 更新 todo，说明剩余工作变成真实自动执行和结果回写。

### Out of Scope

- 不直接调用 `localhost:3001/api/execute-testcase`。
- 不把 step executions、截图或完整报告写入 New Agents。
- 不跨 Header 弹层与资产中心做全局状态统一；本切片把资产中心作为主工作台。
- 不引入数据库迁移框架；当前 new-agents 后端仍使用 `db.create_all()` 初始化模型。

## Data Model

`AgentTestAssetIntentTesterMapping`:

- `id`
- `collection_id`
- `source_case_id`
- `intent_tester_case_id`
- `intent_tester_case_name`
- `latest_execution_id`
- `latest_execution_status`
- `latest_execution_mode`
- `latest_execution_browser`
- `latest_execution_start_time`
- `latest_execution_end_time`
- `latest_execution_duration`
- `latest_execution_error_message`
- `created_at`
- `updated_at`

Unique constraint:

- `(collection_id, source_case_id)`

## API Contracts

### Record Imported Case

Request:

```json
{
  "intentTesterCaseId": 42,
  "intentTesterCaseName": "TC-001 用户登录成功"
}
```

Response:

```json
{
  "sourceCaseId": "TC-001",
  "intentTesterCaseId": 42,
  "intentTesterCaseName": "TC-001 用户登录成功",
  "latestExecution": null
}
```

### Record Latest Execution

Request:

```json
{
  "executionId": "exec-123",
  "status": "pending",
  "mode": "headless",
  "browser": "chrome",
  "startTime": "2026-06-19T10:00:00",
  "endTime": null,
  "duration": null,
  "errorMessage": null
}
```

Response:

```json
{
  "sourceCaseId": "TC-001",
  "intentTesterCaseId": 42,
  "intentTesterCaseName": "TC-001 用户登录成功",
  "latestExecution": {
    "executionId": "exec-123",
    "testCaseId": 42,
    "status": "pending",
    "mode": "headless",
    "browser": "chrome",
    "startTime": "2026-06-19T10:00:00",
    "endTime": null,
    "duration": null,
    "errorMessage": null
  }
}
```

## Error Handling

- 未知 collection 返回 404。
- 未知 source case 返回 404。
- 缺少或非法 `intentTesterCaseId` 返回 400。
- 对未导入的 source case 记录 execution 返回 404，避免静默创建不完整 mapping。
- parser 对缺失字段显式失败，不做兼容 shim。

## Verification

- Backend:
  - `cd tools/new-agents/backend && python3 -m pytest tests/test_test_assets.py tests/test_agent_endpoint.py -q`
- Frontend:
  - `cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/testAssetService.test.ts src/pages/__tests__/TestAssetsPage.test.tsx`
  - `cd tools/new-agents/frontend && npm run lint`
- Workspace:
  - `git diff --check`
