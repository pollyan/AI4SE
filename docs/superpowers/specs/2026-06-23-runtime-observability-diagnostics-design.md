# DeepSeek 格式化失败运行统计诊断闭环 Spec

## 背景

上一轮已经让 shared Agent Runtime 在 raw JSON streaming 连续失败时，把格式化输出问题分类为 `json_decode`、`artifact_data_schema`、`artifact_data_renderer` 和 `artifact_contract`，并把诊断上下文写入 retry prompt。当前缺口是这些分类仍停留在 runtime 异常内：`stream_services.py` 记录 turn metric 时仍会把它们折叠成泛化 schema/contract 错误，`/api/agent/observability` 和 Header 运行统计无法告诉用户“哪类格式化失败正在集中发生、影响哪个 workflow/stage/provider、下一步该修什么”。

本切片把 DeepSeek 格式化失败诊断接入现有共享运行统计能力。它不新增 DeepSeek 专属 API、store、runtime 或 renderer；所有数据继续走 shared Agent Runtime、typed SSE、run persistence、observability endpoint 和 Header 共享 UI。

## 用户故事

作为 New Agents 运行排障用户，当 DeepSeek V4 格式化输出连续失败时，我可以在“运行统计”中看到失败分类、影响范围、重试次数和行动建议，从而判断应该修 JSON 输出、`artifact_data` schema、renderer 配置还是 artifact contract，而不是只看到泛化的结构化输出失败。

## 范围

纳入本轮：

- `FormattedOutputDiagnosticError` 在 stream service 中被记录为稳定 error code，例如 `FORMATTED_OUTPUT_ARTIFACT_DATA_SCHEMA`。
- SSE error 仍显式失败，不伪造 artifact，不 silent fallback。
- `get_runtime_observability_summary()` 返回格式化失败诊断汇总，包括 totals、byKind、byStage、byProvider 和 action suggestions。
- 前端 observability service 严格解析新增 contract。
- Header 运行统计弹窗展示格式化失败诊断区块和行动建议。
- observability alerts 能针对格式化失败集中出现给出高优先级提醒。
- `docs/todos/` 记录 E09 与 DeepSeek 后续状态。

不纳入本轮：

- 真实 DeepSeek V4 Flash smoke。该验证需要凭证、网络和额度，继续作为外部可选验证。
- 新增质量评分模型。E08 工作流质量评分另成厚切片。
- 章节级重生成。E05 另成用户功能厚切片。
- 新的 metrics 表或迁移。复用现有 `AgentRunTurnMetric.error_code`、`contract_retry_count`、workflow/stage/provider 维度。

## 数据契约

后端 observability summary 在现有字段基础上新增：

```json
{
  "formatFailureDiagnostics": {
    "total": 3,
    "byKind": [
      {
        "kind": "artifact_data_schema",
        "label": "artifact_data schema 校验失败",
        "count": 2,
        "retryCount": 4,
        "action": "检查当前 stage 的 artifact_data 必填字段、枚举值、空数组和跨字段引用。"
      }
    ],
    "byStage": [
      {
        "workflowId": "TEST_DESIGN",
        "stageId": "STRATEGY",
        "count": 2,
        "retryCount": 4,
        "kinds": { "artifact_data_schema": 2 },
        "topKind": "artifact_data_schema",
        "action": "检查当前 stage 的 artifact_data 必填字段、枚举值、空数组和跨字段引用。"
      }
    ],
    "byProvider": [
      {
        "provider": "deepseek",
        "count": 3,
        "retryCount": 5,
        "kinds": { "artifact_data_schema": 2, "json_decode": 1 },
        "topKind": "artifact_data_schema",
        "action": "优先检查 DeepSeek JSON mode 输出是否满足当前 stage 的 artifact_data contract。"
      }
    ]
  }
}
```

前端类型必须严格解析该结构。缺字段、错误类型、未知 workflow 都应失败显式抛错，保持现有 observability service 风格。

## 错误分类映射

| runtime kind | metric error code | 用户含义 | 行动建议方向 |
| --- | --- | --- | --- |
| `json_decode` | `FORMATTED_OUTPUT_JSON_DECODE` | 模型没有返回合法 JSON object | 检查 provider JSON mode、prompt 是否要求 fenced Markdown 或解释文字 |
| `artifact_data_schema` | `FORMATTED_OUTPUT_ARTIFACT_DATA_SCHEMA` | `artifact_data` 未通过 Pydantic schema | 检查必填字段、枚举、空数组、跨字段引用和 fixture |
| `artifact_data_renderer` | `FORMATTED_OUTPUT_ARTIFACT_DATA_RENDERER` | 后端 renderer 配置或输入不匹配 | 检查 renderer registry、stage schema 和 deterministic renderer |
| `artifact_contract` | `FORMATTED_OUTPUT_ARTIFACT_CONTRACT` | renderer 输出未通过 artifact contract | 检查 required headings、Mermaid/structured visual 和 stage gate |

## 验收条件

1. Given runtime 抛出 `FormattedOutputDiagnosticError(kind="artifact_data_schema")`
   When `stream_agent_run_events()` 处理异常
   Then turn metric 的 `error_code` 为 `FORMATTED_OUTPUT_ARTIFACT_DATA_SCHEMA`，`contract_retry_count` 保留异常中的 retry 次数，SSE error code 同步为该稳定 code。

2. Given observability 中存在多条格式化失败 metric
   When 调用 `/api/agent/observability`
   Then response 包含 `formatFailureDiagnostics.total/byKind/byStage/byProvider`，并按 workflow/stage/provider 聚合 count、retryCount、topKind 和 action。

3. Given 前端收到新增格式化失败诊断 summary
   When `fetchObservabilitySummary()` 解析
   Then 返回 typed `formatFailureDiagnostics`；payload 缺失或类型错误时显式失败。

4. Given 用户打开 Header 的“运行统计”
   When summary 中有格式化失败诊断
   Then 弹窗展示格式化失败总数、最高频 kind、受影响 stage/provider、重试次数和行动建议。

5. Given 本轮完成
   When 查看 `docs/todos/refactor/`
   Then E09 与 DeepSeek 结构化输出 todo 记录本轮已消化内容，真实 DeepSeek smoke 仍保留为外部验证。

## 风险与约束

- 不能把格式化失败归类为 provider issue；它们是产物 contract / schema 诊断，和鉴权、额度、网络不同。
- 不能新增 DeepSeek 专属 endpoint 或 UI state；DeepSeek 只是该诊断闭环的主要使用场景。
- 不能改变已有 observability 字段语义；新增字段必须向前兼容现有 summary。
- 不改数据库 schema，避免迁移风险；稳定分类通过 `error_code` 承接。

## 验证计划

- `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_stream_services.py tools/new-agents/backend/tests/test_agent_endpoint.py -q`
- `cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/observabilityService.test.ts src/core/__tests__/observabilityAlerts.test.ts src/components/__tests__/Header.test.tsx`
- `.venv/bin/python -m py_compile tools/new-agents/backend/stream_services.py tools/new-agents/backend/run_persistence.py`
- `git diff --check`
