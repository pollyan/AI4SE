# DeepSeek V4 IDEA_BRAINSTORM/CONVERGE 结构化产物数据设计

## 背景

DeepSeek V4 Flash 当前按 `json_object_only` 能力使用，不能依赖供应商 strict schema。`IDEA_BRAINSTORM/DEFINE` 和 `IDEA_BRAINSTORM/DIVERGE` 已迁移为模型输出 `artifact_data`、后端校验并确定性渲染。`IDEA_BRAINSTORM/CONVERGE` 仍要求模型直接拼完整 `# 收敛聚焦` Markdown、ICE 表和 Mermaid `quadrantChart`，容易在评分计算、推荐方案、淘汰理由、验证实验和图表代码中出现格式缺失或不一致。

## 本轮目标

让 `IDEA_BRAINSTORM/CONVERGE` 支持 DeepSeek V4 兼容的结构化产物数据输出：

- 模型只输出 JSON object，包含 `chat`、`artifact_data`、`stage_action`、`warnings`。
- 后端用 Pydantic schema 校验决策矩阵、ICE 评分、资源约束、敏感性分析、验证实验、整合演进路径和阶段门禁。
- 后端确定性渲染 `# 收敛聚焦`、`## 决策矩阵`、`## ICE 评估表`、`## 资源约束`、`## 敏感性分析`、`## 验证实验`、`## 整合演进路径（如果触发合并）` 和 `## 阶段门禁`。
- 后端确定性渲染 Mermaid `quadrantChart`，保留现有 artifact/visual contract。
- 继续复用共享 Agent Runtime、typed SSE、artifact contract、run/artifact persistence 和共享 UI，不新增 Alex、DeepSeek 或 IDEA_BRAINSTORM 专属 runtime/API/store/renderer。

## Artifact Data Contract

`artifact_data` 必须包含：

- `decision_matrix`：评分口径、候选创意决策项、推荐方案和用户确认状态。
- `ice_evaluations`：创意 ID、创意名称、影响力、信心、实现难度、ICE 得分、排名、结论、淘汰理由、证据来源和下一步验证。
- `resource_constraints`：约束类型、内容、影响、处理方式和状态。
- `sensitivity_analysis`：敏感变量、变化方向、影响、观察信号和下一步验证。
- `validation_experiments`：实验 ID、关联创意、实验目标、方法、成功指标、owner、下一步验证和状态。
- `merge_paths`：合并逻辑、来源创意、整合方案、适用条件、风险和用户确认状态。
- `stage_gate`：阶段门禁检查项。

## Validation Rules

- 所有字符串非空，未知字段拒绝，数组至少包含一项。
- `ice_evaluations.idea_id` 必须唯一。
- `ice_score` 必须等于 `impact * confidence / effort`，允许两位小数误差内的数值表示。
- `impact`、`confidence` 和 `effort` 必须是 1 到 5 的整数。
- `rank` 必须唯一；至少一个 ICE 条目的 `conclusion` 或 `decision_matrix.recommended_idea_id` 指向推荐方案。
- `decision_matrix.recommended_idea_id`、`validation_experiments.idea_ids` 和 `merge_paths.source_idea_ids` 只能引用已存在的 `idea_id`。
- `stage_gate` 必须至少包含一个已勾选检查项。

## Rendering Requirements

renderer 必须稳定输出并通过 `validate_agent_turn()`：

- `# 收敛聚焦`
- `## 决策矩阵`，包含 Mermaid `quadrantChart`
- `## ICE 评估表`
- `## 资源约束`
- `## 敏感性分析`
- `## 验证实验`
- `## 整合演进路径（如果触发合并）`
- `## 阶段门禁`
- contract 关键词：`评分口径`、`影响力`、`信心`、`实现难度`、`ICE得分`、`淘汰理由`、`推荐方案`、`下一步验证`、`合并逻辑`、`证据来源`、`用户确认状态`

## Non-goals

- 不迁移 `IDEA_BRAINSTORM/CONCEPT`。
- 不改前端 typed SSE 协议。
- 不新增创意头脑风暴专属 runtime。
- 不运行真实 DeepSeek smoke；该验证需要凭证、网络和额度。
