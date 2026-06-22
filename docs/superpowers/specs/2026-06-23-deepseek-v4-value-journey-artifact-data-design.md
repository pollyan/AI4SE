# DeepSeek V4 VALUE_DISCOVERY/JOURNEY 结构化产物数据设计

## 背景

DeepSeek V4 Flash 只作为 `json_object_only` 能力使用，不能依赖供应商 strict schema。当前 `VALUE_DISCOVERY/ELEVATOR` 和 `VALUE_DISCOVERY/PERSONA` 已迁移到 `artifact_data -> Pydantic schema -> deterministic renderer -> artifact contract` 链路；`VALUE_DISCOVERY/JOURNEY` 仍要求模型直接生成完整 Markdown、Mermaid `journey` 和 `ai4se-visual` `journey-map`，格式失败风险较高。

## 本轮目标

让 `VALUE_DISCOVERY/JOURNEY` 支持 DeepSeek V4 兼容的结构化产物数据输出：

- 模型只输出 JSON object，包含 `chat`、`artifact_data`、`stage_action`、`warnings`。
- 后端用 Pydantic schema 校验用户旅程业务数据和跨字段引用。
- 后端确定性渲染 `# 用户旅程分析`、Mermaid `journey`、`ai4se-visual` `journey-map`、痛点优先级、机会评分、产品切入策略、验证实验和阶段门禁。
- 输出继续走共享 Agent Runtime、typed SSE、artifact contract 和 run artifact persistence，不新增 workflow 专属 runtime/API/store/renderer。

## Artifact Data Contract

`artifact_data` 必须包含：

- `document_info`：复用现有 `DocumentInfo`，标明 `VALUE_DISCOVERY/JOURNEY`。
- `journey_summary`：核心画像、核心痛点、切入策略和进入蓝图的就绪判断。
- `journey_stages`：至少一个旅程阶段，包含阶段 ID、阶段名称、用户任务、触点渠道、用户目标、用户行为、情绪评分、痛点 ID、关键痛点、现有方案不足、机会 ID、机会假设、成功指标和验证状态。
- `pain_priorities`：高/中/低痛点优先级，必须引用已存在的 `stage_id` 和 `pain_id`。
- `opportunity_scores`：机会评分，必须引用已存在的 `opportunity_id` 和 `pain_id`。
- `entry_strategy`：产品切入策略，必须引用已存在的 `opportunity_id`。
- `validation_experiments`：验证实验，必须引用已存在的 `opportunity_id`。
- `stage_gate`：阶段门禁检查项。

## Validation Rules

- 所有字符串非空，未知字段拒绝。
- `journey_stages.stage_id`、`pain_id`、`opportunity_id` 分别唯一。
- `emotion_score` 只能是 1 到 5。
- `pain_priorities.stage_id` 必须存在于 `journey_stages`。
- `pain_priorities.pain_id` 和 `opportunity_scores.pain_id` 必须存在于 `journey_stages.pain_id`。
- `opportunity_scores.opportunity_id`、`entry_strategy.related_opportunity`、`validation_experiments.opportunity_id` 必须存在于 `journey_stages.opportunity_id`。

## Rendering Requirements

renderer 必须稳定输出并通过 `validate_agent_turn()`：

- H1：`# 用户旅程分析`
- `## 用户旅程地图`：Mermaid `journey`，由阶段和情绪评分确定性生成。
- `## 结构化旅程地图`：`ai4se-visual` fenced JSON，`type` 为 `journey-map`。
- `## 关键阶段详细分析`：每个阶段有固定维度表，包含 artifact contract 要求的专业字段。
- `## 痛点优先级排序`：必须包含 `高优先级痛点`、`中等优先级痛点`、`低优先级痛点`。
- `## 机会评分`
- `## 产品切入策略`
- `## 验证实验`
- `## 阶段门禁`

## Non-goals

- 不迁移 `VALUE_DISCOVERY/BLUEPRINT`。
- 不修改前端 typed SSE 协议。
- 不新增 DeepSeek、Alex 或 VALUE_DISCOVERY 专属运行时路径。
- 不运行真实 DeepSeek smoke；该验证需要凭证、网络和额度。
