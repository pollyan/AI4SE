# New Agents 上下文摘要持久校准设计

## Current State Gap Analysis

事实源快照：

- 已读取 `AGENTS.md`、`docs/strategy/goal-mode-playbook.md`、`docs/todos/new-agents-evolution.md`。
- 已核对 `tools/new-agents/backend/models.py`、`tools/new-agents/backend/run_persistence.py`、`tools/new-agents/backend/routes.py`、`tools/new-agents/backend/tests/test_run_persistence.py`、`tools/new-agents/backend/tests/test_agent_endpoint.py`。
- 已核对前端 `tools/new-agents/frontend/src/services/runSnapshotService.ts`、`tools/new-agents/frontend/src/store.ts`、`tools/new-agents/frontend/src/components/Header.tsx`。

候选 gap：

| 候选 | 来源 | 目标态 | 当前能力 | 缺口 | 价值 | 风险/复杂度 | 可测试性 | 去向 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A. 服务端摘要校准写回 | P1 #6 | 用户在前端校准摘要后，服务端 `agent_context_summaries` 被更新，后续 context builder 使用校准内容 | 后端有摘要表和 snapshot；前端只能本地编辑 | 编辑不会进入服务端上下文 | 直接闭合“可见但不生效”的缺口 | 后端 + 前端小纵切；不做权限模型 | repository/API/service/Header 测试 | 本轮 |
| B. 用户级摘要写回权限控制 | P1 #6 / P1 #5 | 只有有权访问 run 的用户能修改摘要 | 当前 New Agents 尚无用户身份模型 | 缺认证与授权事实源 | 分享/多用户前置能力 | 需要系统级权限设计 | 需要认证集成测试 | 后续与分享权限合并 |
| C. 独立决策录入表单 | P1 #6 | 用户能新建决策摘要，而不依赖已有摘要 | 当前摘要来自确定性提取 | 缺新增语义和表单 | 决策追踪更完整 | 需要摘要创建/分类规则 | 前后端测试 | 下一轮候选 |

排序结论：

1. 选择 A，因为它沿用现有唯一键和 snapshot 数据形态，能让校准结果真正进入服务端 context builder。
2. B 暂不选，因为仓库当前没有用户身份和 run 分享权限模型；贸然实现会制造伪权限。
3. C 暂不选，因为新增决策需要更清晰的创建和展示语义；先完成已有摘要的写回更稳。

## 目标

当用户在 Header 的“上下文摘要”弹层编辑已有摘要并保存时，前端通过共享 New Agents API 更新服务端 `agent_context_summaries`。后续恢复 snapshot 和继续对话时，服务端 context builder 都使用校准后的摘要内容。

## API 设计

新增：

`PATCH /api/agent/runs/<runId>/context-summaries`

请求体：

```json
{
  "sourceType": "artifact",
  "sourceStageId": "CLARIFY",
  "summaryType": "stage_conclusion",
  "content": "校准后的摘要"
}
```

响应体为更新后的摘要：

```json
{
  "sourceType": "artifact",
  "sourceStageId": "CLARIFY",
  "summaryType": "stage_conclusion",
  "content": "校准后的摘要"
}
```

规则：

- 只更新已有摘要；找不到 run 或摘要时返回 404。
- 请求体只能包含上述四个字段，缺字段或字段类型错误返回 400。
- `content` trim 后不能为空；保存原始字符串，允许用户保留换行和缩进。
- 不新增 agent/workflow 专属 endpoint。

## 前端设计

- `runSnapshotService.ts` 新增 `updateRunContextSummary(runId, summary, content)`。
- Header 保存摘要时，如果存在 `currentRunId`，先调用服务端 PATCH，成功后用服务端返回内容更新 store。
- 保存失败时显示“无法保存上下文摘要”，不修改 store。
- UI 文案从“本地校准不写回服务端”改为“保存后会更新当前 run 的服务端摘要”。

## 边界

本轮不新增：

- 用户身份、分享权限或 run ACL。
- 新建摘要 API。
- 独立决策录入表单。
- 摘要编辑历史和审计日志。

## 验收条件

1. Given run 中已有 `stage_conclusion`
   When 调用 repository 更新该摘要
   Then `get_run_snapshot()` 返回新内容。
   Evidence: `tools/new-agents/backend/tests/test_run_persistence.py`。

2. Given run 中已有摘要
   When `PATCH /api/agent/runs/<runId>/context-summaries` 传入合法请求
   Then 返回 200 和更新后的摘要，后续 snapshot 返回新内容。
   Evidence: `tools/new-agents/backend/tests/test_agent_endpoint.py`。

3. Given 请求缺字段、字段类型错误、空内容或不存在摘要
   When 调用 PATCH endpoint
   Then 返回 400 或 404，不创建假摘要。
   Evidence: 后端 endpoint 测试。

4. Given Header 摘要弹层存在当前 runId
   When 用户编辑并保存摘要
   Then 前端调用 PATCH service，并用服务端返回内容更新 store。
   Evidence: `tools/new-agents/frontend/src/components/__tests__/Header.test.tsx`。

## 风险

- 现阶段无用户级权限控制，因此 endpoint 仍是本地开发/演示能力；后续分享权限模型必须接管访问控制。
- 自动提取摘要的下一轮 artifact 写入可能覆盖用户校准内容；后续若要保护人工校准，需要在模型中区分 `manual` 与 `derived` 来源或增加锁定语义。
