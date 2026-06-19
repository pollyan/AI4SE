# New Agents 上下文摘要校准 UI 设计

## Current State Gap Analysis

事实源快照：

- 已读取 `AGENTS.md`、`docs/strategy/goal-mode-playbook.md`、`docs/todos/new-agents-evolution.md`。
- 已核对 `tools/new-agents/frontend/src/services/runSnapshotService.ts`、`tools/new-agents/frontend/src/store.ts`、`tools/new-agents/frontend/src/core/types.ts`、`tools/new-agents/frontend/src/components/Header.tsx`。
- 已核对 P1 #6 进展：后端已持久化 `agent_context_summaries`，snapshot API 已返回 `contextSummaries`，context builder 已消费这些摘要。

候选 gap：

| 候选 | 来源 | 目标态 | 当前能力 | 缺口 | 价值 | 风险/复杂度 | 可测试性 | 去向 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A. 上下文摘要前端可见与本地校准 | P1 #6 | 用户恢复 run 后能看到服务端结构化摘要，并在继续对话前校准本地显示内容 | service 已解析 `contextSummaries`，store 未保存，UI 不可见 | 摘要不可审计，用户无法发现错误摘要 | 提升跨阶段推进可信度，直接收敛 P1 #6 | 前端局部改动；不新增后端写入 | store/Header 测试 | 本轮 |
| B. 服务端摘要 PATCH 持久写回 | P1 #6 | 用户编辑摘要后持久写回 `agent_context_summaries` | 后端只有确定性 upsert，未开放用户编辑 API | 需要 API、权限、并发语义 | 完整校准闭环 | 跨后端/前端/访问控制，范围大 | 后端 endpoint + 前端集成测试 | 下一轮候选 |
| C. 独立决策录入表单 | P1 #6 | 用户能结构化录入关键决策 | 决策摘要由 artifact Markdown 确定性提取 | 缺人工录入表单与写回 | 有助于跨阶段决策追踪 | 依赖服务端写回语义 | 端到端测试 | 下一轮候选 |

排序结论：

1. 选择 A，因为它直接补齐当前最明显的前端缺口，并复用已有 snapshot 数据，不引入新的 runtime 分支或后端 API。
2. B 和 C 暂不选，因为它们需要服务端编辑语义、权限和冲突处理；应在 A 让摘要可见之后再做。

## 目标

当用户处于 New Agents 工作台，且当前 workspace 已从服务端 snapshot 恢复出 `contextSummaries` 时，用户可以从 Header 打开“上下文摘要”，按类型和阶段查看摘要，并在本地编辑校准展示内容。此切片不承诺服务端持久写回。

## 用户故事

作为 Lisa 或 Alex 的使用者，我恢复一个历史 run 后，可以看到当前 run 保存的用户补充、阶段结论、关键决策和产物摘要；如果发现摘要展示不准确，我可以在当前工作台内编辑文本，保证后续人工审阅时看到的是校准后的版本。

## 设计

采用 Header 轻量弹层，而不是新建完整恢复中心：

- `ChatState` 增加 `contextSummaries`，类型复用 `AgentRunSnapshotContextSummary`。
- `restoreRunSnapshot()` 将 snapshot 中的摘要保存到 store。
- `setWorkflow()`、`clearHistory()` 和 `applyWorkflowHandoff()` 清空摘要，避免跨 workflow 或跨 run 污染。
- Header 增加“上下文摘要”按钮。无摘要时按钮仍可打开空状态，用于明确当前 run 没有可校准摘要。
- 弹层按 `summaryType` 和 `sourceStageId` 展示摘要，提供 textarea 本地编辑；保存只更新 store 中对应摘要，不调用后端。

## 边界

本轮不新增：

- `PATCH /api/agent/runs/{runId}/context-summaries`。
- 用户级访问控制、分享权限或恢复中心。
- 独立决策录入表单。
- context builder 对前端本地编辑摘要的消费。继续对话时仍以服务端持久摘要为准，直到后续服务端写回切片补齐。

## 验收条件

1. Given snapshot 包含 `contextSummaries`
   When `restoreRunSnapshot(snapshot)` 被调用
   Then store 保存这些摘要，并可被 Header 渲染。
   Evidence: `tools/new-agents/frontend/src/__tests__/store.test.ts`。

2. Given 当前 store 有摘要
   When 用户点击“上下文摘要”
   Then 弹层展示摘要类型、阶段和内容。
   Evidence: `tools/new-agents/frontend/src/components/__tests__/Header.test.tsx`。

3. Given 用户在摘要弹层编辑某条摘要
   When 用户保存
   Then store 中该摘要内容更新，弹层显示新内容。
   Evidence: `tools/new-agents/frontend/src/components/__tests__/Header.test.tsx`。

4. Given 用户切换 workflow、清空会话或应用 handoff
   When workspace state 被重置
   Then 旧摘要不会残留。
   Evidence: `tools/new-agents/frontend/src/__tests__/store.test.ts`。

## 风险

- 本地编辑不持久写回，刷新页面或再次从服务端恢复会回到服务端摘要。UI 文案必须避免暗示已同步服务端。
- Header 已承载多个弹层，继续扩展会增加文件复杂度；本轮只做最小入口，后续完整恢复中心可迁移出去。
