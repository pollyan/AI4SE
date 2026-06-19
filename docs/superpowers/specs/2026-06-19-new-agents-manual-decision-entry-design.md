# New Agents 独立决策录入设计

## Current State Gap Analysis

事实源快照：

- 已读取 `docs/strategy/goal-mode-playbook.md`、`docs/todos/new-agents-evolution.md`。
- 已核对 `tools/new-agents/backend/context_builder.py`、`tools/new-agents/backend/run_persistence.py`、`tools/new-agents/backend/routes.py`。
- 已核对 `tools/new-agents/frontend/src/components/Header.tsx` 和 `tools/new-agents/frontend/src/services/runSnapshotService.ts`。

候选 gap：

| 候选 | 来源 | 目标态 | 当前能力 | 缺口 | 价值 | 风险/复杂度 | 可测试性 | 去向 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A. 独立关键决策录入 | P1 #6 | 用户无需等待 artifact 自动提取，就能把关键决策写入服务端摘要 | 已有摘要展示、编辑和 PATCH 写回 | 只能编辑已有摘要，不能新建决策 | 让人工决策进入后续 context builder | 小纵切，复用摘要表 | 后端/前端单元测试 | 本轮 |
| B. 决策锁定与人工优先级 | P1 #6 | 人工决策不会被后续 artifact 自动摘要覆盖 | 当前自动 upsert 会覆盖同 stage decision | 缺 source/priority/lock 语义 | 保护人工校准 | 需 schema/策略设计 | 后续测试 | 下一轮候选 |
| C. 多条决策列表与审计 | P1/P2 | 支持多条决策、历史、操作者、时间 | 当前 summary 是唯一键单文本 | 缺列表模型 | 更完整协作 | 需新模型和权限 | 后续测试 | 后续增强 |

排序结论：选择 A。它直接收敛 todo 中“单独的决策录入表单”缺口，并复用已验证的摘要持久化链路。B/C 暂缓，因为它们需要额外 schema 和权限模型。

## 目标

在 Header 的“上下文摘要”弹层内新增“关键决策录入”表单。用户输入一段决策后，系统将其保存为当前 run 当前阶段的 `artifact/decision` 摘要。后续 snapshot 和 context builder 会读取这条决策。

## 设计

后端新增：

- `upsert_manual_decision_summary(run_id, patch)`。
- `POST /api/agent/runs/{runId}/context-summaries/decisions`。

请求体：

```json
{
  "stageId": "STRATEGY",
  "content": "决定优先覆盖第三方登录回调失败"
}
```

响应沿用 `AgentRunSnapshotContextSummary`：

```json
{
  "sourceType": "artifact",
  "sourceStageId": "STRATEGY",
  "summaryType": "decision",
  "content": "决定优先覆盖第三方登录回调失败"
}
```

前端新增：

- `createRunDecisionSummary(runId, stageId, content)` service。
- Header “上下文摘要”弹层中的决策 textarea 和“保存关键决策”按钮。
- 保存成功后 upsert 当前 store 的 `contextSummaries`，让新决策立即显示在摘要列表中。

## 边界

本轮不新增：

- 多条决策实体和决策历史。
- 用户权限、分享 ACL。
- 人工摘要锁定、自动摘要覆盖保护。
- 独立页面级恢复中心。

## 验收条件

1. Given run 属于 `TEST_DESIGN/STRATEGY`
   When 调用 `upsert_manual_decision_summary(run.id, {"stageId": "STRATEGY", "content": "..."})`
   Then snapshot 出现 `artifact/STRATEGY/decision`。

2. Given 请求 stage 不属于 run workflow 或 content 为空
   When 调用 repository 或 endpoint
   Then 返回显式错误，不写入摘要。

3. Given Header 有 `currentRunId`
   When 用户在“关键决策录入”中保存
   Then 前端调用 service，并把返回的 decision summary 加入 store。

4. Given 保存失败
   When 用户点击保存
   Then UI 显示错误，不伪造本地决策。

## 风险

当前设计将人工决策写入 `artifact/decision`，以便现有 context builder 立即消费。后续 artifact 自动摘要仍可能覆盖同 stage decision；这已在 todo 中保留为锁定/优先级后续切片。
