# Lisa Intent Tester Execution Handoff Design

## Current State Gap Analysis

Lisa 测试资产目前已经可以导出 `intentTesterDrafts`，并在测试资产弹层中手动导入 intent-tester 用例。导入成功后，用户只能看到 “去执行 #id” 链接，跳转到 `/intent-tester/execution?testcase_id=<id>` 后由 intent-tester 执行页接管。

这个能力还不是一个完整的用户可感知闭环：

- 用户在 New Agents 资产中心看不到某条 Lisa 用例是否已经导入 intent-tester。
- 用户无法在资产中心创建 intent-tester 执行记录，也无法刷新查看最近一次执行状态。
- intent-tester 执行页的真实浏览器执行依赖本地 `localhost:3001` MidScene proxy；New Agents 不应该在没有代理状态和执行反馈的情况下伪装成“已真实执行”。
- 当前仅做跳转链接属于过薄切片，不能满足目标模式每轮都交付可感知能力的要求。

## Slice Thickness Gate

本切片必须按“用户能力包”交付，而不是单独的 endpoint、service 或按钮：

- 用户能在 Lisa 测试资产中心看到每条测试用例对应的 intent-tester 草稿状态。
- 用户能从资产中心导入单条草稿，并看到 intent-tester 用例 ID。
- 用户能为已导入用例创建 intent-tester 执行记录，并看到执行记录 ID 与状态。
- 用户能刷新已导入用例最近执行结果，并从资产中心跳转到 intent-tester 执行页继续真实浏览器执行。
- 系统必须明确区分“执行记录已创建”和“真实浏览器执行已完成”，不制造假成功。

## Scope

### In Scope

- 在 New Agents 前端新增 intent-tester 执行 API service：
  - `POST /intent-tester/api/executions`
  - `GET /intent-tester/api/executions?testcase_id=<id>&size=1`
- 在 Lisa 测试资产中心的测试用例卡片中加入导入、创建执行记录、刷新执行状态、去执行入口。
- 前端状态只保存在当前页面会话中，沿用已有 intent-tester 导入能力的短期状态策略。
- 为 service parser 和资产中心用户流程补充 Vitest/Testing Library 测试。
- 更新 todo，记录本切片完成后剩余的真实自动执行和结果回写边界。

### Out of Scope

- 不从 New Agents 直接调用 `localhost:3001/api/execute-testcase`。
- 不新增后台异步浏览器执行编排。
- 不持久化 New Agents 与 intent-tester testcase/execution 的映射。
- 不把 intent-tester 执行结果写回 New Agents 数据库中的测试资产版本。

## User Experience

在 Lisa 测试资产中心中，每条测试用例根据是否存在 matching `intentTesterDrafts.sourceCaseId` 展示：

- 无草稿：不展示 intent-tester 操作区。
- 有草稿且未导入：显示草稿告警摘要和“导入 intent-tester”按钮。
- 已导入：显示“已导入 intent-tester #<id>”，显示“创建执行记录”“刷新执行结果”“去执行 #<id>”。
- 已创建或刷新到执行记录：显示“最近执行 #<execution_id> · <status>”。

“去执行”仍跳转 `/intent-tester/execution?testcase_id=<id>`，intent-tester 执行页会自动选择该用例，并由用户点击开始执行；真实浏览器执行仍受本地 proxy 健康状态约束。

## Contracts

新增前端类型：

- `IntentTesterExecutionCreateResult`
  - `executionId: string`
  - `status: string`
  - `testcaseName: string`
  - `startTime: string`
- `IntentTesterExecutionRecord`
  - `executionId: string`
  - `testCaseId: number`
  - `status: string`
  - `mode: string`
  - `browser: string`
  - `startTime: string | null`
  - `endTime: string | null`
  - `duration: number | null`
  - `errorMessage: string | null`

Parser 必须显式失败：

- create 响应缺少 `data.execution_id`、`data.status`、`data.testcase_name` 或 `data.start_time` 时抛错。
- list 响应缺少 `data.items` 数组时抛错。
- execution item 缺少 `execution_id`、`test_case_id` 或 `status` 时抛错。

## Risks

- intent-tester 后端 `POST /executions` 当前只创建 pending 执行记录，不会自动调起本地浏览器代理。UI 文案必须避免误导。
- 当前导入 ID 是页面会话状态，刷新页面后会丢失。本切片保持一致，后续需要持久化映射。
- 浏览器执行页和 New Agents 前端是不同应用路径；本切片只提供可追踪接力，不承诺执行页内状态实时回流。

## Verification

- `cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/intentTesterExecutionService.test.ts src/pages/__tests__/TestAssetsPage.test.tsx`
- `cd tools/new-agents/frontend && npm run lint`
- `git diff --check`
