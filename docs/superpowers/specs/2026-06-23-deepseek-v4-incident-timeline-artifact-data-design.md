# DeepSeek V4 INCIDENT_REVIEW/TIMELINE 结构化产物数据设计

## 背景

DeepSeek V4 Flash 当前按 `json_object_only` 能力使用，不能依赖供应商 strict schema。`TEST_DESIGN`、`REQ_REVIEW` 和 `VALUE_DISCOVERY` 已完成结构化产物数据迁移，`INCIDENT_REVIEW/TIMELINE` 仍要求模型直接拼完整 Markdown 和 Mermaid `timeline`。该阶段 prompt 已明确指出 Mermaid timeline 中半角冒号时间点会导致渲染崩溃，因此应把时间线格式生成职责收束到后端 deterministic renderer。

## 本轮目标

让 `INCIDENT_REVIEW/TIMELINE` 支持 DeepSeek V4 兼容的结构化产物数据输出：

- 模型只输出 JSON object，包含 `chat`、`artifact_data`、`stage_action`、`warnings`。
- 后端用 Pydantic schema 校验事件概要、影响量化、事实来源、时间线事件、事实/推测隔离、事实摘要、参与人员、待补充信息和阶段门禁。
- 后端确定性渲染 `# 故障复盘报告`、事件概要、影响量化、事实来源、Mermaid `timeline`、事实/推测隔离、事实摘要、参与人员、待补充信息和阶段门禁。
- 继续复用共享 Agent Runtime、typed SSE、artifact contract、run/artifact persistence 和共享 UI，不新增 Lisa、DeepSeek 或 INCIDENT_REVIEW 专属 runtime/API/store/renderer。

## Artifact Data Contract

`artifact_data` 必须包含：

- `incident_summary`：故障名称、严重等级、发现时间、恢复时间、持续时长、影响范围、当前状态。
- `impact_metrics`：影响维度、量化结果、可信度、来源、状态。
- `fact_sources`：事实 ID、事实描述、来源、可信度、状态。
- `timeline_events`：时间线分组、时间点、事件描述、关联事实 ID。
- `fact_separation`：事实、推测、待确认信息的隔离清单，包含处理方式、阻断性、状态。
- `fact_summary`：3-5 句事实摘要，不包含因果推断。
- `participants`：角色、人员、主要行动、参与时间、状态。
- `missing_information`：信息项、为什么需要、补充方式、阻断性、owner、状态。
- `stage_gate`：阶段门禁检查项。

## Validation Rules

- 所有字符串非空，未知字段拒绝，数组至少包含一项。
- `fact_sources.fact_id` 唯一。
- `timeline_events.fact_ids` 只能引用已存在的 `fact_id`。
- `timeline_events.occurred_at` 可以包含用户原始时间表达，但 renderer 必须把 Mermaid timeline 行中的半角冒号转为全角冒号。
- `fact_separation.item_type` 至少应覆盖事实/推测/待确认中的一种；schema 不把枚举写死，避免阻塞真实事故文本，但 renderer 固定输出处理表。

## Rendering Requirements

renderer 必须稳定输出并通过 `validate_agent_turn()`：

- `# 故障复盘报告`
- `## 1. 事件概要`
- `## 2. 影响量化`
- `## 3. 事实来源`
- `## 4. 事件时间线`，包含 Mermaid `timeline`
- `## 5. 事实/推测隔离`
- `## 6. 事实摘要`
- `## 7. 参与人员`
- `## 8. 待补充信息`
- `## 9. 阶段门禁`
- contract 关键词：`可信度`、`阻断性`、`状态`

## Non-goals

- 不迁移 `INCIDENT_REVIEW/ROOT_CAUSE` 或 `INCIDENT_REVIEW/IMPROVEMENT`。
- 不改前端 typed SSE 协议。
- 不新增故障复盘专属 runtime。
- 不运行真实 DeepSeek smoke；该验证需要凭证、网络和额度。
