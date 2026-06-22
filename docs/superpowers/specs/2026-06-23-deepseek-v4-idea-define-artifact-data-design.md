# DeepSeek V4 IDEA_BRAINSTORM/DEFINE 结构化产物数据设计

## 背景

DeepSeek V4 Flash 当前按 `json_object_only` 能力使用，不能依赖供应商 strict schema。`TEST_DESIGN`、`REQ_REVIEW`、`VALUE_DISCOVERY` 和 `INCIDENT_REVIEW` 已按阶段迁移为模型输出 `artifact_data`、后端确定性渲染 Markdown/Mermaid/ai4se-visual。`IDEA_BRAINSTORM/DEFINE` 仍要求模型直接拼完整 `# 问题域分析` Markdown 和 Mermaid `mindmap`，容易在复杂表格、阶段门禁和 Mermaid 代码块中出现格式缺失。

## 本轮目标

让 `IDEA_BRAINSTORM/DEFINE` 支持 DeepSeek V4 兼容的结构化产物数据输出：

- 模型只输出 JSON object，包含 `chat`、`artifact_data`、`stage_action`、`warnings`。
- 后端用 Pydantic schema 校验问题假设、目标用户画像、问题域节点、证据与验证状态、问题-用户-场景匹配、约束与边界、反向验证和阶段门禁。
- 后端确定性渲染 `# 问题域分析`、Mermaid `mindmap`、证据等级、验证动作、验证状态和阶段门禁。
- 继续复用共享 Agent Runtime、typed SSE、artifact contract、run/artifact persistence 和共享 UI，不新增 Alex、DeepSeek 或 IDEA_BRAINSTORM 专属 runtime/API/store/renderer。

## Artifact Data Contract

`artifact_data` 必须包含：

- `problem_statement`：目标用户、场景、核心痛点、现有替代方案、替代方案不足、不解决后果、验证状态。
- `target_users`：维度、描述、证据等级、验证状态。
- `problem_landscape`：核心问题、子问题节点和表现节点，用于后端渲染 Mermaid `mindmap`。
- `evidence_items`：证据 ID、关联问题、证据来源、证据等级、验证动作、owner、验证状态。
- `problem_user_fit`：检验维度、当前判断、证据或假设、验证动作、验证状态。
- `constraints_boundaries`：类型、内容、影响、状态。
- `reverse_validation`：失败假设、触发信号、验证动作、验证状态。
- `stage_gate`：阶段门禁检查项。

## Validation Rules

- 所有字符串非空，未知字段拒绝，数组至少包含一项。
- `evidence_items.evidence_id` 必须唯一。
- `problem_user_fit.evidence_ids` 只能引用已存在的 evidence ID。
- `problem_landscape.subproblems.problem_id` 必须唯一。
- `problem_landscape.root_problem` 必须能被至少一个 evidence item 或 problem-user-fit item 引用。
- `stage_gate` 必须至少包含一个已勾选检查项，避免完全未满足的入口阶段被推进。

## Rendering Requirements

renderer 必须稳定输出并通过 `validate_agent_turn()`：

- `# 问题域分析`
- `## 问题假设陈述`
- `## 目标用户画像`
- `## 问题域全景`，包含 Mermaid `mindmap`
- `## 证据与验证状态`
- `## 问题-用户-场景匹配`
- `## 约束与边界`
- `## 反向验证（风险思考）`
- `## 阶段门禁`
- contract 关键词：`证据等级`、`验证动作`、`验证状态`

## Non-goals

- 不迁移 `IDEA_BRAINSTORM/DIVERGE`、`CONVERGE` 或 `CONCEPT`。
- 不改前端 typed SSE 协议。
- 不新增创意头脑风暴专属 runtime。
- 不运行真实 DeepSeek smoke；该验证需要凭证、网络和额度。
