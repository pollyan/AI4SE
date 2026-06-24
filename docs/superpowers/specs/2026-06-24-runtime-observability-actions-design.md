# Runtime Observability Actions Design

## 背景

`docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md` 将 E09「运行统计产品化」列为 P1：用户需要在运行统计里看到 workflow/stage/provider 趋势、contract retry 原因和行动建议。当前 New Agents 已有 `/api/agent/observability`、Header「运行统计」modal、provider issue alert、workflow/stage 筛选和自动刷新，但它主要展示成功率、失败数、错误码和最近运行。用户看到失败后，仍需要自行判断下一步修配置、修 prompt/contract，还是重新运行。

本轮目标是把运行统计从“数字展示”升级为“诊断与行动建议闭环”，继续复用共享 Agent Runtime、持久化 metric、typed service parser 和 Header 运行统计 UI。

## Superpowers 头脑风暴结论

- 问：真实用户意图是什么？
  答：用户在运行失败或 contract retry 频繁时，需要快速定位失败集中点和下一步处理动作，而不是只看到原始错误码。
- 问：是否需要视觉辅助？
  答：不需要。现有运行统计 modal 已确定，本轮聚焦数据契约和信息结构。
- 问：哪些相邻缺口必须同轮并入？
  答：后端诊断字段、前端 typed parser、Header 展示和测试必须同轮完成。只做一个字段或一个卡片都无法形成可操作排障闭环。
- 问：本轮不做什么？
  答：不做新的 observability 页面，不新增 endpoint，不做外部模型调用，不做 artifact 章节级修订。
- 问：推荐方案是什么？
  答：扩展现有 `/agent/observability` 响应，加入确定性 `diagnostics` 和 `contractRetryReasons`。后端负责错误语义和建议，前端负责严格解析与展示。

## 用户故事

作为 New Agents 的运行维护用户，当我打开 Header 的「运行统计」时，我可以看到失败集中点、provider/config 问题、contract retry 原因和具体行动建议，从而决定应该检查模型配置、修复 stage prompt/contract、还是重试某个 workflow/stage。

## 范围

本轮包含：

- 扩展后端 `get_runtime_observability_summary()`，返回：
  - `diagnostics`: 全局诊断建议列表。
  - `contractRetryReasons`: contract retry 相关原因分布。
- 扩展前端 `ObservabilitySummary` / service parser，严格校验新增字段。
- 扩展 Header 运行统计 modal，展示“诊断建议”和 contract retry 原因。
- 更新 E09 todo 消化记录、spec 和 plan。

本轮不包含：

- 不新增 `/agent/observability/*` API path。
- 不改 Agent Runtime 执行流程、typed SSE 事件、run/artifact 持久化模型结构。
- 不新增 Lisa/Alex/DeepSeek 专属 runtime、store 或 renderer。
- 不引入 LLM judge 或真实模型 smoke。

## 响应契约

`GET /api/agent/observability` 在现有字段基础上新增：

```json
{
  "contractRetryReasons": {
    "STRUCTURED_OUTPUT_CONTRACT_RETRY": 3
  },
  "diagnostics": [
    {
      "id": "contract-retry",
      "severity": "warning",
      "title": "结构化输出重试偏高",
      "detail": "最近运行中有 3 次 contract retry，集中在 TEST_DESIGN / STRATEGY。",
      "action": "检查该阶段 prompt、artifact contract 和 renderer 输出是否同步。"
    }
  ]
}
```

约束：

- `diagnostics` 始终返回数组；没有建议时返回 `[]`。
- `contractRetryReasons` 始终返回 object；没有 retry 时返回 `{}`。
- `severity` 只允许 `info | warning | critical`。
- 现有 `totals`、`byStage`、`byProvider`、`recentTurns` 字段保持兼容。

## 诊断规则

首批确定性规则：

- 有 runtime config issue 或 provider issue 时，生成模型/供应商配置诊断。
- 有失败运行且成功率低于 80% 时，生成运行失败诊断。
- 任一 stage 的失败率低于 80% 时，生成 stage 集中失败诊断。
- `contractRetryCount` 总和大于 0 时，生成结构化输出 contract retry 诊断，并写入 `contractRetryReasons`。
- 没有问题时不生成诊断项。

## UI 设计

Header 运行统计 modal 在「运行告警」和概览卡片之间增加「诊断建议」区：

- 每条建议展示 severity、title、detail、action。
- contract retry 原因以 badge 或短列表展示。
- provider issue 仍保留现有“打开模型设置 / 检测连接”操作。
- 筛选 workflow/stage 后，诊断建议跟随后端返回的筛选结果更新。

## 错误处理

- 后端未知 `workflowId` 或不合法 `stageId` 仍返回 400。
- 前端 parser 遇到缺失或类型错误的 `diagnostics` / `contractRetryReasons` 时抛 `Invalid observability summary response`。
- UI 加载失败继续显示现有 `无法加载运行统计`。

## 验收条件

1. Given 最近运行有 contract retry  
   When 请求 `/agent/observability`  
   Then 响应包含 `contractRetryReasons` 和一条结构化输出重试诊断。  
   Evidence: `test_agent_endpoint.py`

2. Given 响应包含 diagnostics  
   When 前端调用 `fetchObservabilitySummary()`  
   Then service 严格解析 `diagnostics` 和 `contractRetryReasons`。  
   Evidence: `observabilityService.test.ts`

3. Given 运行统计有 contract retry 和失败集中点  
   When 用户打开 Header「运行统计」  
   Then modal 显示「诊断建议」和可操作 action 文案。  
   Evidence: `Header.test.tsx`

4. Given diagnostics malformed  
   When 前端解析响应  
   Then 明确抛出 `Invalid observability summary response`。  
   Evidence: `observabilityService.test.ts`

## 验证计划

- `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_endpoint.py -q`
- `cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/observabilityService.test.ts src/core/__tests__/observabilityAlerts.test.ts src/components/__tests__/Header.test.tsx`
- `cd tools/new-agents/frontend && npm run lint`
- `.venv/bin/python -m py_compile tools/new-agents/backend/run_persistence.py tools/new-agents/backend/routes.py`
- `git diff --check`

## 风险

- `contractRetryCount` 当前只有计数，没有精确 schema path；本轮的 `contractRetryReasons` 先以确定性类别表达，后续可接入更细的 contract failure taxonomy。
- Header 已经承载较多 modal，本轮只加诊断区，不做无关布局重构。
- 真实 provider 连通性仍依赖本地配置和外部服务；本轮不调用外部模型。
