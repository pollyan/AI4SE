# 跨 run 工作流质量趋势闭环设计

## 背景

New Agents 已具备单 run 内的规则型工作流质量治理：前端 `workflowQuality` 可以基于 workflow manifest、阶段 artifact、可视化诊断和开放问题计算每个 stage 的质量分、状态和待处理项。运行统计也已通过共享 `/api/agent/observability` 展示 success rate、provider、stage、格式化失败 drilldown 和最近失败队列。

当前缺口是两类证据没有接上：用户能看到运行是否失败、单个 run 的当前 artifact 是否可推进，但不能从历史 run 维度判断某个 workflow/stage 的产物质量是否持续退化、阻塞集中在哪些阶段、最近哪些 run 需要处理。这使 E08 “工作流质量评分”只停留在单 run 质量治理，尚未形成跨 run 趋势闭环。

## 目标

本轮交付一个完整用户能力：用户在 Header 的“运行统计”中按 workflow/stage 查看历史 run 的产物质量趋势，识别平均质量分、blocked/attention/ready/not-started 分布、最差阶段和最近质量问题样本，并获得下一步行动建议。

该能力复用共享 Agent Runtime、typed SSE、workflow manifest、artifact contract、持久化 run/artifact 模型和 Header 运行统计 UI；不新增 Lisa、Alex、DeepSeek 或未来 agent 专属 runtime、API path、store 或 renderer。

## 用户故事

作为 New Agents 使用者，我希望在同一个运行统计入口里同时看到运行稳定性和产物质量趋势，这样当某个工作流输出质量下降时，我能判断是模型/供应商失败、格式化输出失败，还是 artifact contract / stage gate / 缺失信息导致质量阻塞。

## 范围

纳入本轮：

- 后端在现有 `/api/agent/observability` 响应中新增 `qualityTrend`。
- `qualityTrend` 从持久化 `AgentRun`、当前 `AgentArtifactVersion` 和 workflow manifest/contract 派生，不新增数据库字段。
- 后端质量评估使用 deterministic 规则：artifact 是否存在、required headings 是否存在、required Mermaid / `ai4se-visual` 是否满足、阶段门禁和未确认/阻断类文本是否存在。
- 前端 `observabilityService` 严格解析 `qualityTrend`，缺字段或类型错误时显式失败。
- Header 运行统计展示质量趋势摘要、阶段分布、最近问题样本、空态和筛选后的结果。
- 文档更新记录 E08 跨 run 趋势已完成，LLM judge 仍保留为后续外部/高成本证据能力。

不纳入本轮：

- LLM judge 或真实模型评分。
- DeepSeek V4 Flash 真实 smoke。
- 新 workflow scaffold/codegen。
- Prompt/template version registry。
- 跨 run artifact diff、收藏、分享或外部项目管理系统联动。

## 后端契约

`GET /api/agent/observability` 保持原有 query：

- `limit`: 最近 turn / 最近质量问题样本数量上限，沿用 1..100 clamp。
- `workflowId`: 可选 workflow 过滤。
- `stageId`: 可选 stage 过滤，必须与 `workflowId` 同用。

新增响应字段：

```json
{
  "qualityTrend": {
    "totalRuns": 3,
    "artifactRuns": 2,
    "averageScore": 72,
    "statusCounts": {
      "ready": 1,
      "attention": 1,
      "blocked": 1,
      "notStarted": 0,
      "insufficientEvidence": 0
    },
    "worstStage": {
      "workflowId": "TEST_DESIGN",
      "stageId": "CLARIFY",
      "averageScore": 40,
      "status": "blocked",
      "pendingCount": 2,
      "runCount": 2,
      "action": "补齐必填标题、可视化和阶段门禁后再推进。"
    },
    "byStage": [
      {
        "workflowId": "TEST_DESIGN",
        "stageId": "CLARIFY",
        "runCount": 2,
        "artifactCount": 2,
        "averageScore": 40,
        "statusCounts": {
          "ready": 0,
          "attention": 1,
          "blocked": 1,
          "notStarted": 0,
          "insufficientEvidence": 0
        },
        "topPending": [
          {
            "title": "缺少必填标题",
            "count": 1,
            "severity": "blocker",
            "action": "补齐 artifact contract 要求的标题。"
          }
        ]
      }
    ],
    "recentIssues": [
      {
        "runId": "run-1",
        "workflowId": "TEST_DESIGN",
        "stageId": "CLARIFY",
        "score": 40,
        "status": "blocked",
        "title": "缺少必填标题",
        "detail": "缺少 ## 1. 需求背景",
        "action": "补齐 artifact contract 要求的标题。",
        "createdAt": "2026-06-23T09:00:00"
      }
    ]
  }
}
```

空数据行为：

- 没有匹配 run 时：`totalRuns=0`，`artifactRuns=0`，`averageScore=0`，数组为空，`worstStage=null`。
- 有 run 但没有 artifact 时：按 stage 产生 `notStarted` 或 `insufficientEvidence`，最近问题样本说明“暂无可评估 artifact”。
- workflow/stage 过滤沿用现有校验，非法过滤返回 400。

## 前端体验

Header 运行统计详情在格式化输出诊断和基础运行指标之间增加“跨 run 质量趋势”区域：

- 顶部显示平均质量分、已评估 artifact run 数、blocked/attention/ready 分布。
- 若 `worstStage` 存在，突出展示最差阶段和行动建议。
- 按 stage 展示质量分和 top pending，复用当前筛选条件。
- 最近问题样本展示 runId、workflow/stage、状态、分数、问题和行动建议。
- 空态明确显示“当前筛选范围暂无质量趋势证据”。

## 质量评分口径

本轮采用 deterministic 规则，不调用 LLM：

- 无 artifact：0 分，`notStarted`。
- 缺 required heading：每项扣 20，产生 blocker。
- 缺 required Mermaid：每项扣 20，产生 blocker。
- 缺 required `ai4se-visual`：每项扣 20，产生 blocker。
- 缺阶段门禁文本：扣 16，产生 blocker。
- 出现“待确认 / 未确认 / 阻断 / 缺失信息 / 开放问题”类文本：扣 8，产生 attention；包含“阻断”时作为 blocker。
- 分数 clamp 到 0..100。
- status：有 blocker 为 `blocked`；有 attention 为 `attention`；无问题为 `ready`。

该口径不是替代前端单 run `workflowQuality`，而是在后端为跨 run aggregation 提供同源但可持久化查询的保守规则。后续 LLM judge 可以作为额外 evidence 接入，而不是替换 deterministic gate。

## 验收条件

- 后端 observability 测试能构造多个 run/artifact，证明 `qualityTrend` 聚合平均分、状态分布、最差阶段、最近问题和 workflow/stage 过滤。
- 前端 service 测试能解析合法 `qualityTrend`，并在字段缺失或类型错误时失败。
- Header 测试能看到“跨 run 质量趋势”、平均分、最差阶段、最近问题样本和空态。
- 现有运行统计、格式化失败诊断和 provider alert 测试保持通过。
- docs/todos 记录 E08 跨 run 趋势已消化，LLM judge、DeepSeek real smoke、scaffold/codegen、prompt/template version 仍是后续候选。

## 风险与取舍

- 后端规则与前端单 run `workflowQuality` 会有少量重复。当前为了避免 Header 为每个历史 run 拉 snapshot 并在客户端聚合，接受后端 deterministic 子集规则；后续如果质量规则继续扩张，应抽取共享 contract 或由 manifest 派生更多规则。
- 质量趋势只基于当前 artifact version，不追溯每个 version 的历史变化。这样能满足“跨 run”而不是“单 run 内版本趋势”，避免扩大到 artifact diff/审计闭环。
- 不做 LLM judge，避免引入凭证、网络、成本和非确定性验证；LLM judge 后续应作为可选 evidence provider。

## 验证计划

- 后端：`/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_endpoint.py::test_agent_observability_endpoint_returns_quality_trend_from_persisted_artifacts tools/new-agents/backend/tests/test_agent_endpoint.py::test_agent_observability_endpoint_filters_quality_trend_by_workflow_and_stage -q`
- 前端：`/Users/anhui/Documents/myProgram/AI4SE/tools/new-agents/frontend/node_modules/.bin/vitest run src/services/__tests__/observabilityService.test.ts src/components/__tests__/Header.test.tsx`
- 回归：`/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_endpoint.py::test_agent_observability_endpoint_returns_runtime_turn_summary tools/new-agents/backend/tests/test_agent_endpoint.py::test_agent_observability_endpoint_groups_formatted_output_diagnostics -q`
- 回归：`/Users/anhui/Documents/myProgram/AI4SE/tools/new-agents/frontend/node_modules/.bin/vitest run src/core/__tests__/workflowQuality.test.ts src/services/__tests__/observabilityService.test.ts src/components/__tests__/Header.test.tsx`
