# DeepSeek V4 INCIDENT_REVIEW/ROOT_CAUSE 结构化产物数据设计

## 背景

DeepSeek V4 Flash 当前按 `json_object_only` 能力使用，不能依赖供应商 strict schema。`INCIDENT_REVIEW/TIMELINE` 已迁移为模型输出 `artifact_data`、后端确定性渲染 Markdown/Mermaid。`INCIDENT_REVIEW/ROOT_CAUSE` 仍要求模型直接拼完整 Markdown、Mermaid `mindmap` 和 `ai4se-visual cause-map`，容易在复杂表格、fenced block 和可视化 JSON 中出现格式错误。

## 本轮目标

让 `INCIDENT_REVIEW/ROOT_CAUSE` 支持 DeepSeek V4 兼容的结构化产物数据输出：

- 模型只输出 JSON object，包含 `chat`、`artifact_data`、`stage_action`、`warnings`。
- 后端用 Pydantic schema 校验 5-Why 分析链、根因证据、鱼骨图分类、根因结论、排除项、未验证原因和阶段门禁。
- 后端确定性渲染 `# 故障复盘报告`、`## 6. 根因分析`、`ai4se-visual cause-map`、Mermaid `mindmap`、证据表、结论表、排除项、未验证原因和阶段门禁。
- 继续复用共享 Agent Runtime、typed SSE、artifact contract、run/artifact persistence 和共享 UI，不新增 Lisa、DeepSeek 或 Incident Review 专属 runtime/API/store/renderer。

## Artifact Data Contract

`artifact_data` 必须包含：

- `analysis_context`：故障名称、分析范围、上游事实摘要、当前判断。
- `why_chain`：现象和至少 3 层 Why，包含层级、问题、回答、原因类型、证据、证据强度、置信度、可行动性、验证状态。
- `cause_evidence`：原因 ID、原因描述、关联层级、证据、证据强度、置信度、可行动性、验证状态。
- `fishbone_categories`：鱼骨图分类和原因项，至少覆盖 2 个分类。
- `root_cause_conclusions`：直接原因、根本原因、促成因素等结论。
- `excluded_causes`：排除项、曾经怀疑原因、排除依据、证据强度、仍需关注。
- `unverified_causes`：未验证原因、未验证原因说明、可能影响、后续验证动作、owner、状态。
- `stage_gate`：阶段门禁检查项。

## Validation Rules

- 所有字符串非空，未知字段拒绝，数组至少包含一项。
- `why_chain` 至少包含 4 行，其中至少 3 行层级以 `Why-` 开头。
- `cause_evidence.cause_id` 必须唯一。
- `cause_evidence.related_level`、`root_cause_conclusions.related_cause_id` 和 `fishbone_categories.cause_ids` 只能引用已存在的 Why 层级或原因 ID。
- `fishbone_categories` 至少包含 2 个分类，避免不合格的单维度鱼骨图。
- `root_cause_conclusions` 至少包含一个类型为“根本原因”的结论。

## Rendering Requirements

renderer 必须稳定输出并通过 `validate_agent_turn()`：

- `# 故障复盘报告`
- `## 6. 根因分析`
- `### 6.1 5-Why 分析链`
- `ai4se-visual` fenced block，`type` 为 `cause-map`
- `### 6.2 根因证据表`
- `### 6.3 原因鱼骨图`，包含 Mermaid `mindmap`
- `### 6.4 根因结论`
- `### 6.5 排除项`
- `### 6.6 未验证原因`
- `### 6.7 阶段门禁`
- contract 关键词：`证据强度`、`置信度`、`可行动性`

## Non-goals

- 不迁移 `INCIDENT_REVIEW/IMPROVEMENT`。
- 不改前端 typed SSE 协议。
- 不新增故障复盘专属 runtime。
- 不运行真实 DeepSeek smoke；该验证需要凭证、网络和额度。
