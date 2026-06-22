# DeepSeek V4 IDEA_BRAINSTORM/DIVERGE 结构化产物数据设计

## 背景

DeepSeek V4 Flash 当前按 `json_object_only` 能力使用，适合返回合法 JSON，但不能保证完整 Markdown、表格或 Mermaid 代码块。`IDEA_BRAINSTORM/DEFINE` 已迁移为模型输出 `artifact_data`、后端校验并确定性渲染《问题域分析》。`IDEA_BRAINSTORM/DIVERGE` 仍要求模型直接拼 `# 创意发散` artifact，容易在创意卡片表、来源假设、搁置记录和全景图中出现格式缺失。

## 本轮目标

让 `IDEA_BRAINSTORM/DIVERGE` 支持 DeepSeek V4 兼容的结构化产物数据输出：

- 模型只输出 JSON object，包含 `chat`、`artifact_data`、`stage_action`、`warnings`。
- 后端用 Pydantic schema 校验发散方法、创意全景、创意卡片、来源假设、搁置/排除记录和阶段门禁。
- 后端确定性渲染 `# 创意发散`、`## 发散方法说明`、`## 发散全景图`、`## 创意卡片库`、`## 创意来源与假设`、`## 搁置/排除记录` 和 `## 阶段门禁`。
- `## 发散全景图` 由后端渲染 Mermaid `mindmap`，并同步到 manifest/backend visual contract。
- 继续复用共享 Agent Runtime、typed SSE、artifact contract、run/artifact persistence 和共享 UI，不新增 Alex、DeepSeek 或 IDEA_BRAINSTORM 专属 runtime/API/store/renderer。

## Artifact Data Contract

`artifact_data` 必须包含：

- `divergence_method`：方法名、目标、输入依据、覆盖维度和发散约束。
- `idea_landscape`：根主题与发散分组，每个分组引用已存在的创意 ID，用于渲染 Mermaid `mindmap`。
- `idea_cards`：创意 ID、名称、一句话说明、目标用户、使用场景、价值主张、关键假设、创新来源、证据等级、验证动作、当前状态和状态理由。
- `idea_sources`：来源 ID、来源类型、来源内容、引用的创意 ID、关键假设和状态理由。
- `parked_or_excluded`：记录 ID、创意或方向、搁置/排除原因、重新考虑条件和状态理由。
- `stage_gate`：阶段门禁检查项。

## Validation Rules

- 所有字符串非空，未知字段拒绝，数组至少包含一项。
- `idea_cards.idea_id` 必须唯一。
- `idea_sources.source_id` 必须唯一。
- `parked_or_excluded.record_id` 必须唯一。
- `idea_landscape.groups.idea_ids` 和 `idea_sources.idea_ids` 只能引用已存在的 `idea_cards.idea_id`。
- 每个创意卡片至少有一个 `key_hypotheses`。
- `stage_gate` 必须至少包含一个已勾选检查项，避免完全未满足的发散阶段推进。

## Rendering Requirements

renderer 必须稳定输出并通过 `validate_agent_turn()`：

- `# 创意发散`
- `## 发散方法说明`
- `## 发散全景图`，包含 Mermaid `mindmap`
- `## 创意卡片库`
- `## 创意来源与假设`
- `## 搁置/排除记录`
- `## 阶段门禁`
- contract 关键词：`关键假设`、`状态理由`

## Non-goals

- 不迁移 `IDEA_BRAINSTORM/CONVERGE` 或 `IDEA_BRAINSTORM/CONCEPT`。
- 不改前端 typed SSE 协议。
- 不新增创意头脑风暴专属 runtime。
- 不运行真实 DeepSeek smoke；该验证需要凭证、网络和额度。
