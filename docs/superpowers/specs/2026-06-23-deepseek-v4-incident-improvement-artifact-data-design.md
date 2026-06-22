# DeepSeek V4 INCIDENT_REVIEW/IMPROVEMENT 结构化产物数据设计

## 背景

DeepSeek V4 Flash 当前按 `json_object_only` 能力使用，不能依赖供应商 strict schema。`INCIDENT_REVIEW/TIMELINE` 和 `INCIDENT_REVIEW/ROOT_CAUSE` 已迁移为模型输出 `artifact_data`、后端确定性渲染 Markdown/Mermaid/ai4se-visual。`INCIDENT_REVIEW/IMPROVEMENT` 仍要求模型直接拼完整故障复盘最终报告、Mermaid `pie` 和 `ai4se-visual action-board`，容易在复杂表格、行动项字段和 fenced block 中出现格式错误。

## 本轮目标

让 `INCIDENT_REVIEW/IMPROVEMENT` 支持 DeepSeek V4 兼容的结构化产物数据输出：

- 模型只输出 JSON object，包含 `chat`、`artifact_data`、`stage_action`、`warnings`。
- 后端用 Pydantic schema 校验报告信息、事件摘要、根因摘要、改进优先级、SMART/CAPA 行动项、根因覆盖、复查计划、遗留风险、经验教训、组织学习、签署确认和阶段门禁。
- 后端确定性渲染 `# 故障复盘报告`、事件还原、根因分析、改进措施、Mermaid `pie`、`ai4se-visual action-board`、防复发清单、复查计划、风险接受、经验教训、组织学习、签署确认和阶段门禁。
- 继续复用共享 Agent Runtime、typed SSE、artifact contract、run/artifact persistence 和共享 UI，不新增 Lisa、DeepSeek 或 Incident Review 专属 runtime/API/store/renderer。

## Artifact Data Contract

`artifact_data` 必须包含：

- `report_info`：故障名称、严重等级、报告版本、生成时间、行动项总数、复查日期、关闭状态。
- `timeline_summary`：关键事件、影响摘要、恢复摘要。
- `root_cause_summary`：直接原因、根本原因、促成因素、证据摘要。
- `priority_distribution`：紧急、重要、常规行动数量。
- `improvement_actions`：行动 ID、改进措施、类型、对应根因、建议负责人、完成期限、验证方式、验收标准、优先级、当前状态、追踪机制。
- `root_cause_coverage`：根因 ID、根因类型、说明、覆盖行动、覆盖状态、未覆盖原因、风险接受人。
- `prevention_checklist`：防复发检查项、对应根因、负责人、状态。
- `review_plan`：复查项、复查日期、复查人、证据、通过标准、状态。
- `residual_risks`：风险 ID、风险描述、影响、接受理由、风险接受人、复查期限、状态。
- `lessons_learned`：经验 ID、经验内容、适用范围、传播建议。
- `organizational_learning`：组织学习项、受众、渠道、负责人、期限、状态。
- `signoffs`：签署角色、确认人、确认项、状态。
- `stage_gate`：阶段门禁检查项。

## Validation Rules

- 所有字符串非空，未知字段拒绝，数组至少包含一项。
- `report_info.action_count` 必须等于 `improvement_actions` 数量。
- `improvement_actions.action_id` 必须唯一。
- `priority_distribution` 的紧急、重要、常规数量必须与行动项 `priority` 计数一致。
- `root_cause_coverage.action_ids` 只能引用已存在的行动 ID。
- 每个行动项的 `root_cause_id` 必须能在 `root_cause_coverage.cause_id` 中找到。
- 覆盖状态为“已覆盖”的根因必须至少有一个行动 ID。

## Rendering Requirements

renderer 必须稳定输出并通过 `validate_agent_turn()`：

- `# 故障复盘报告`
- `## 报告信息`
- `## 第一部分：事件还原`
- `## 第二部分：根因分析`
- `## 第三部分：改进措施`
- `### 7. 改进措施`
- `#### 7.1 改进优先级分布`，包含 Mermaid `pie`
- `#### 7.2 改进行动清单`，包含 `ai4se-visual` fenced block，`type` 为 `action-board`
- `#### 7.3 根因覆盖检查`
- `### 8. 防复发检查清单`
- `### 9. 复查计划`
- `### 10. 遗留风险与风险接受`
- `### 11. 经验教训`
- `### 12. 组织学习`
- `## 签署确认`
- `### 13. 阶段门禁`
- contract 关键词：`ID`、`改进措施`、`类型`、`对应根因`、`建议负责人`、`完成期限`、`验证方式`、`验收标准`、`优先级`、`当前状态`、`追踪机制`、`复查日期`、`覆盖状态`、`风险接受人`

## Non-goals

- 不迁移 `IDEA_BRAINSTORM`。
- 不改前端 typed SSE 协议。
- 不新增故障复盘专属 runtime。
- 不运行真实 DeepSeek smoke；该验证需要凭证、网络和额度。
