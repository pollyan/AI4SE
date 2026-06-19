# New Agents 运行统计前端视图设计

## 背景

`docs/todos/new-agents-evolution.md` #12 已完成后端 `agent_run_turn_metrics` 记录和 `GET /api/agent/observability` 基础统计 API，但前端没有入口查看这些数据。用户仍无法从 UI 判断近期运行失败率、慢阶段、供应商错误集中点或最近 turn 状态。

## 用户故事

作为 New Agents 使用者或维护者，我希望在工作台里打开一个只读运行统计视图，快速看到总轮次、成功率、按阶段/供应商聚合的失败信息和最近 turn 列表，从而定位高失败率阶段或供应商侧异常。

## 范围

进入本轮：

- 新增前端 `observabilityService`，读取并校验 `GET /new-agents/api/agent/observability?limit=20`。
- 在 `Header` 增加“运行统计”入口，打开只读弹层。
- 弹层展示 totals、byStage、byProvider 和 recentTurns 的核心字段。
- API 异常或协议异常必须显式显示错误状态，不伪造空成功。
- 更新 todo、组件清单和 API 文档。

不进入本轮：

- 不改后端统计模型或接口。
- 不做告警、筛选、图表库、导出或自动刷新。
- 不补真实 token 用量或真实 contract retry 采集。
- 不做权限模型。

## 设计

前端新增 `src/services/observabilityService.ts`，用和 `runSnapshotService` / `testAssetService` 相同的 typed parser 风格校验响应结构。`fetchObservabilitySummary({ limit })` 只负责 HTTP 和协议解析，非 2xx 抛出 `Failed to fetch observability summary: <status>`，协议错误抛出 `Invalid observability summary response`。

`Header` 保持现有工作台顶部栏结构，新增“运行统计”按钮和弹层状态。弹层打开时调用 service，展示四块只读内容：总览、按阶段、按供应商、最近运行。没有数据时显示“暂无运行统计”，请求失败时显示“无法加载运行统计”。

## 验收条件

1. `observabilityService` 正确请求 `/new-agents/api/agent/observability?limit=20` 并解析 totals、byStage、byProvider、recentTurns。
2. 协议错误会显式失败，不能静默返回空对象。
3. Header 中“运行统计”按钮能打开弹层并展示成功率、阶段、供应商和最近 turn。
4. Header 请求失败时展示错误状态。
5. 相关前端测试、TypeScript 检查、后端 observability endpoint 回归和 `git diff --check` 通过。
