# DeepSeek V4 IDEA_BRAINSTORM/CONCEPT 结构化产物数据设计

## 背景

DeepSeek V4 Flash 当前按 `json_object_only` 能力使用，不能依赖供应商 strict schema。`IDEA_BRAINSTORM/DEFINE`、`DIVERGE` 和 `CONVERGE` 已迁移为模型输出 `artifact_data`、后端校验并确定性渲染。`IDEA_BRAINSTORM/CONCEPT` 仍要求模型直接拼完整《产品概念简报》Markdown、Mermaid 图和 `ai4se-visual` `mvp-map`，是创意头脑风暴全流程里最后一个格式稳定性缺口。

## 本轮目标

让 `IDEA_BRAINSTORM/CONCEPT` 支持 DeepSeek V4 兼容的结构化产物数据输出：

- 模型只输出 JSON object，包含 `chat`、`artifact_data`、`stage_action`、`warnings`。
- 后端用 Pydantic schema 校验定位声明、核心假设、Lean Canvas、MVP 功能分布、增长漏斗、Pre-mortem 风险、验证路线、不可做范围、决策记录、下一步行动和阶段门禁。
- 后端确定性渲染 `# 产品概念简报`、`## 定位声明`、`## 核心假设`、`## Lean Canvas 产品画布`、`## MVP 功能分布`、`## 核心增长漏斗`、`## Pre-mortem 风险分析`、`## 验证路线`、`## 不可做范围`、`## 决策记录`、`## 下一步行动` 和 `## 阶段门禁`。
- 后端确定性渲染 Mermaid `pie`、Mermaid `flowchart` 和 `ai4se-visual` `mvp-map`，保留现有 artifact/visual contract。
- 继续复用共享 Agent Runtime、typed SSE、artifact contract、run/artifact persistence 和共享 UI，不新增 Alex、DeepSeek 或 IDEA_BRAINSTORM 专属 runtime/API/store/renderer。

## Artifact Data Contract

`artifact_data` 必须包含：

- `positioning_statement`：目标用户、痛点、产品名称、产品品类、核心价值、替代方案和差异化优势。
- `core_assumptions`：假设 ID、内容、来源、重要性、验证动作、owner 和状态。
- `lean_canvas`：问题、用户群体、独特价值主张、解决方案、渠道、收入来源、成本结构、关键指标和竞争壁垒。
- `mvp_features`：模块、MVP 层级、用户价值、验证指标、取舍理由、关联假设和状态。
- `growth_funnel`：获客、激活、留存、变现和传播阶段的用户行为、核心指标和 MVP 实现方式。
- `premortem_risks`：市场、产品、执行等风险维度、失败原因、可能性和缓解措施。
- `validation_roadmap`：验证阶段、目标、实验方式、成功指标、时间窗口、owner、状态和关联假设。
- `out_of_scope`：不做项、原因、重新考虑条件和状态。
- `decision_records`：决策项、结论、依据、决策人/角色、日期和状态。
- `next_actions`：行动 ID、行动、关联假设或风险、owner、截止时间、验收标准和状态。
- `stage_gate`：阶段门禁检查项。

## Validation Rules

- 所有字符串非空，未知字段拒绝，数组至少包含一项。
- `core_assumptions.assumption_id`、`validation_roadmap.validation_id` 和 `next_actions.action_id` 必须唯一。
- `mvp_features.assumption_ids` 和 `validation_roadmap.assumption_ids` 只能引用已存在的假设 ID。
- `next_actions.related_ids` 必须引用已存在的假设 ID、验证 ID 或风险 ID。
- `growth_funnel.stage` 必须覆盖 `Acquisition`、`Activation`、`Retention`、`Revenue`、`Referral`。
- `lean_canvas` 必须覆盖 9 个 Lean Canvas 格子。
- `stage_gate` 必须至少包含一个已勾选检查项。

## Rendering Requirements

renderer 必须稳定输出并通过 `validate_agent_turn()`：

- `# 产品概念简报`
- `## 定位声明`
- `## 核心假设`
- `## Lean Canvas 产品画布`
- `## MVP 功能分布`，包含 Mermaid `pie`
- `## 核心增长漏斗`，包含 Mermaid `flowchart`
- `ai4se-visual` `mvp-map`
- `## Pre-mortem 风险分析`
- `## 验证路线`
- `## 不可做范围`
- `## 决策记录`
- `## 下一步行动`
- `## 阶段门禁`
- contract 关键词：`owner`、`状态`

## Non-goals

- 不改前端 typed SSE 协议。
- 不新增创意头脑风暴专属 runtime。
- 不迁移或新增其它 workflow。
- 不运行真实 DeepSeek smoke；该验证需要凭证、网络和额度。
