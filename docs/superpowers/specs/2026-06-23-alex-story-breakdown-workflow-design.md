# Alex 用户故事拆解 Workflow 设计

## 背景

`docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md` 将 E13 标记为 P0：Alex 需要把需求蓝图、PRD 或自然语言需求拆成 Epic、User Story、验收标准、依赖和 Sprint 切片，并可作为 Lisa 测试设计输入。当前代码只有 `frontend/src/core/config/agentWorkflows.ts` 中的 `story-breakdown` plan 卡片，没有共享 Agent Runtime workflow。

## 目标

- 将 `story-breakdown` 转为 Alex 在线 workflow：`STORY_BREAKDOWN`。
- 首批采用单阶段完整厚切片 `BACKLOG`，一次生成可评审用户故事包。
- 继续复用共享 `/api/agent/runs/stream`、typed SSE、workflow manifest、artifact contract、run/artifact persistence、共享前端 workspace 和 handoff 机制。
- 模型输出 `artifact_data`，后端用 Pydantic schema 校验并确定性渲染 Markdown、Mermaid 和 `ai4se-visual`，不让新 workflow 回退到模型拼最终 Markdown。
- 为 `STORY_BREAKDOWN/BACKLOG` 提供 Lisa handoff 到 `TEST_DESIGN/CLARIFY` 和 `REQ_REVIEW/REVIEW`。

## 非目标

- 不接入 Jira、禅道或其他外部项目管理工具。
- 不新增 Alex 专属 runtime、API path、store 或 renderer。
- 不在本轮实现多阶段故事拆解流程；后续可以在保持同一 workflow id 的前提下拆分更多 stage。
- 不实现 PRD Review；E14 留作下一轮候选。

## 用户故事

作为产品经理或需求分析师，当我已有 PRD、需求蓝图或需求描述时，我可以在 Alex 中选择“用户故事拆解”，生成完整 Epic/User Story/AC/依赖/Sprint 切片包，并把结果交给 Lisa 做测试设计或需求评审。

## Workflow 设计

- Workflow ID: `STORY_BREAKDOWN`
- Slug: `story-breakdown`
- Agent: `alex`
- Stage: `BACKLOG`
- Stage 名称: `故事拆解`

`BACKLOG` artifact 包含：

- `# 用户故事拆解包`
- 文档信息
- 输入理解与拆解边界
- Epic 地图
- User Story Backlog
- 验收标准矩阵
- 依赖与风险
- Sprint 切片建议
- Lisa Handoff 输入
- 阶段门禁

可视化 contract：

- Mermaid `flowchart`：Epic 到 Story 的拆解关系。
- `ai4se-visual` `story-map`：按 Epic、Story、优先级、Sprint、状态展示故事地图。

## artifact_data schema

`artifact_data` 至少包含：

- `document_info`
- `scope_summary`
- `epics`
- `user_stories`
- `acceptance_criteria`
- `dependencies`
- `risks`
- `sprint_slices`
- `lisa_handoff_inputs`
- `stage_gate`

后端校验：

- 所有字符串非空，数组至少一项。
- `epics.epic_id`、`user_stories.story_id`、`acceptance_criteria.ac_id`、`dependencies.dependency_id`、`risks.risk_id`、`sprint_slices.slice_id` 唯一。
- `user_stories.epic_id` 只能引用已存在 Epic。
- `acceptance_criteria.story_id` 只能引用已存在 Story。
- `dependencies.related_story_ids`、`risks.related_story_ids`、`sprint_slices.story_ids` 只能引用已存在 Story。
- `lisa_handoff_inputs.reference_id` 只能引用已存在 Story、AC、Dependency、Risk 或 Sprint Slice。
- `stage_gate` 至少一项 `checked=true`。

## 验收条件

1. Alex workflow 列表中 `story-breakdown` 由 plan 变为 online，并链接 `/workspace/alex/story-breakdown`。
2. `STORY_BREAKDOWN/BACKLOG` 出现在 workflow manifest、frontend `WORKFLOWS`、backend `WORKFLOW_STAGES`、required artifact/visual contracts 和 prompt registry 中。
3. 合法 `artifact_data` 能渲染完整用户故事拆解包，并通过 `validate_agent_turn()`。
4. 非法跨字段引用会被 Pydantic schema 拒绝。
5. `build_structured_output_instruction("STORY_BREAKDOWN", "BACKLOG")` 要求模型输出 `artifact_data` 而非 Markdown。
6. 持久化 Story Breakdown artifact 后，handoff endpoint 能返回到 Lisa `TEST_DESIGN/CLARIFY` 和 `REQ_REVIEW/REVIEW` 的目标上下文。

## 风险与边界

- 本轮会触及共享 workflow 配置面，必须用 sync tests 保证 manifest、frontend prompt、backend contract 同步。
- 主工作区有未提交 todo 改动，本轮在隔离 worktree 中复制当前 todo 文档事实并记录 E13 消化；不修改主工作区。
- 新 workflow 使用单阶段完整包控制范围；多阶段精细化留到后续，不阻断用户完成“需求到故事包”的核心动作。
