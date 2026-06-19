# Lisa Intent Tester Result Snapshot Design

## Current State Gap Analysis

Lisa 测试资产中心已经具备 intent-tester testcase/execution mapping 持久化：刷新后可以恢复 “已导入 #id” 和最近 execution 状态。但最近 execution 仍只是轻量摘要，缺少用户判断测试结果所需的信息：

- 看不到步骤总数、通过数、失败数。
- 看不到失败步骤、错误信息、截图路径。
- intent-tester 执行页完成真实浏览器执行后，New Agents 资产中心无法承接这次执行详情。
- 后续质量闭环需要一个 New Agents 侧结果快照，才能继续做失败用例 triage、资产版本标记或报告导出。

## Slice Thickness Gate

本切片必须交付用户可感知的结果承接能力包：

- 前端能从 intent-tester `/api/executions/<execution_id>` 读取 execution detail，包括 `step_executions`。
- New Agents 后端能把 execution detail 压缩为稳定 result snapshot 并持久化到 source case mapping。
- 资产集合详情返回 result snapshot，刷新资产中心后仍能看到结果摘要。
- 资产中心用例卡片展示步骤总数、通过数、失败数、失败步骤和截图路径数量。
- 失败或未导入状态显式报错，不做静默 fallback。

## Scope

### In Scope

- 扩展 `AgentTestAssetIntentTesterMapping`，增加 `latest_execution_result_json`。
- 新增 New Agents 后端 service/API：
  - `PATCH /api/agent/test-assets/<collection_id>/intent-tester/cases/<case_id>/result`
- 扩展前端 intent-tester execution service：
  - `fetchIntentTesterExecutionDetail(executionId)`，解析 `step_executions`。
- 扩展前端 New Agents test asset service：
  - `recordTestAssetIntentTesterResult(...)`
- 资产中心新增“承接执行结果 #id”操作，保存并展示 persisted result snapshot。
- 测试覆盖 service parser、后端持久化、API 和资产中心恢复展示。

### Out of Scope

- 不直接调用 `localhost:3001/api/execute-testcase`。
- 不修改 intent-tester 执行引擎。
- 不把截图文件复制到 New Agents 存储，只保存 intent-tester 暴露的截图路径。
- 不修改 Lisa 测试用例定义版本；本切片先保存结果快照，后续再决定是否把结果转成测试资产版本状态。

## Result Snapshot Contract

`latestResult`:

```json
{
  "executionId": "exec-456",
  "status": "failed",
  "stepsTotal": 3,
  "stepsPassed": 2,
  "stepsFailed": 1,
  "duration": 60,
  "errorMessage": "断言失败",
  "screenshots": ["/static/screenshots/step-2.png"],
  "failedSteps": [
    {
      "stepIndex": 2,
      "description": "验证预期结果",
      "status": "failed",
      "errorMessage": "未看到进入工作台",
      "screenshotPath": "/static/screenshots/step-2.png",
      "action": "ai_assert"
    }
  ]
}
```

Rules:

- `stepsTotal/stepsPassed/stepsFailed` 优先使用 intent-tester execution 顶层字段；缺失时从步骤数组计算。
- `screenshots` 从所有步骤的 `screenshot_path` 去重提取。
- `failedSteps` 只保留 `status === "failed"` 的步骤，按 `step_index` 排序。
- `latestExecution` 和 `latestResult` 可以同时存在；result snapshot 是更丰富的执行承接信息。

## Error Handling

- 未知 collection 或 source case 返回 404。
- source case 尚未导入 intent-tester 返回 404。
- result payload 缺少 `executionId/status` 返回 400。
- step payload 类型错误返回 400。
- 前端 parser 对 malformed intent-tester detail 显式抛错。

## Verification

- `cd tools/new-agents/backend && python3 -m pytest tests/test_test_assets.py tests/test_agent_endpoint.py -q`
- `cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/intentTesterExecutionService.test.ts src/services/__tests__/testAssetService.test.ts src/pages/__tests__/TestAssetsPage.test.tsx`
- `cd tools/new-agents/frontend && npm run lint`
- `git diff --check`
