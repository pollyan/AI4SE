# New Agents 运行统计产品化闭环设计

## 背景

当前 New Agents 已经通过共享 Agent Runtime、typed SSE、run persistence 和 `/api/agent/observability` 暴露基础运行统计。DeepSeek V4 结构化产物数据迁移完成后，最需要被用户理解的是 schema/contract/renderer 重试、模型供应商异常和低成功率 stage 的集中位置。

现有统计弹窗已经能展示 totals、stage、provider 和 recent turns，但它更像计数面板。用户仍需要自己推断失败原因和下一步动作。

## 目标

- 后端 observability summary 增加确定性诊断建议，不改变现有 API path、SSE 协议、Agent Runtime 或持久化表结构。
- 建议覆盖三类高价值问题：
  - contract retry 集中：提示检查 artifact_data schema、stage contract、renderer 或 prompt 边界。
  - provider issue 集中：提示检查模型配置、额度、鉴权、网络和连通性。
  - stage 成功率偏低：提示先从最低成功率 workflow/stage 排查输入、contract 和阶段提示词。
- 前端严格解析新增建议数组，并在运行统计弹窗展示“诊断建议”区域。
- 现有 provider issue alert 的“打开模型设置/检测连接”能力继续保留。

## 非目标

- 不新增 Lisa/Alex 专属 runtime、API path、store 或 renderer。
- 不改变 `agent_run_turn_metrics` 模型和 migration。
- 不做 LLM judge、真实 DeepSeek smoke 或外部监控系统集成。
- 不把建议写入持久化表；本轮只做 summary-time deterministic inference。

## 设计

### 后端 summary contract

`get_runtime_observability_summary()` 返回新增字段：

```json
{
  "diagnostics": [
    {
      "id": "contract-retry-TEST_DESIGN-CLARIFY",
      "severity": "warning",
      "title": "结构化产物重试集中",
      "detail": "TEST_DESIGN / CLARIFY 最近触发 3 次 contract retry。",
      "action": "优先检查该阶段 artifact_data schema、required headings、visual contract 与 prompt 示例是否一致。",
      "workflowId": "TEST_DESIGN",
      "stageId": "CLARIFY",
      "provider": null,
      "metric": "contractRetryCount",
      "count": 3
    }
  ]
}
```

规则：

- `contractRetryCount > 0` 的 stage 生成 `contract_retry` 诊断，按 retry 次数降序，最多 3 条。
- `providerIssueCount > 0` 的 provider 生成 `provider_issue` 诊断，按问题数降序，最多 3 条。
- `failedTurns > 0 && successRate < 80` 的 stage 生成 `low_success_rate` 诊断，按成功率升序，最多 3 条。
- 空数据返回空数组，不伪造建议。

### 前端 parsing 与展示

`observabilityService.ts` 新增 `ObservabilityDiagnostic` 解析：

- `id/title/detail/action/severity/metric` 必须是字符串。
- `workflowId/stageId/provider` 允许 `null`。
- `count` 必须是整数。

`Header.tsx` 在运行告警之后、指标卡片之前展示“诊断建议”。每条建议展示标题、detail、action 和定位标签。

## 验收

- 后端 endpoint 测试证明 summary 包含 contract retry、provider issue、低成功率 stage 的诊断建议。
- 前端 service 测试证明新增字段被严格解析，缺失或类型错误会失败。
- Header 测试证明用户能在运行统计弹窗看到诊断建议和行动文案。
- focused backend/frontend 测试通过，`git diff --check` 通过。

## 风险

- `Header.tsx` 已经较大，本轮只做局部渲染，不重构组件。
- 主工作区存在未提交 todo 文档，本轮在隔离 worktree 更新本分支文档，收尾时明确提示主目录未被修改。
