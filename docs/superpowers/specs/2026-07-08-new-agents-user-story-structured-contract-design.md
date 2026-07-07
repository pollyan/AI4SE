# New Agents Alex 用户故事结构化契约设计

## 目标承接检查

事实源快照：

- 已读取：`AGENTS.md`、`docs/strategy/goal-mode-playbook.md`、`docs/strategy/goal-mode-cga-template.md`、`docs/strategy/goal-mode-ci-verification.md`、`docs/index.md`、`docs/ARCHITECTURE.md`、`docs/api-contracts.md`、`docs/TESTING.md`。
- 已读取 todo：`docs/todos/2026-07-08-new-agents-alex-requirement-to-user-story-handoff.md`、`docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md`、`docs/todos/2026-07-07-new-agents-partial-artifact-streaming-vertical-slices.md`、`docs/todos/2026-06-25-new-agents-strategy-chart-generator-schema-hardening.md`。
- 已读取代码与测试：`tools/new-agents/workflow_manifest.json`、`tools/new-agents/backend/agent_contracts.py`、`tools/new-agents/backend/agent_runtime.py`、`tools/new-agents/backend/artifact_data_renderers.py`、`tools/new-agents/backend/tests/test_artifact_data_renderers.py`、`tools/new-agents/backend/tests/test_agent_runtime.py`、`tools/new-agents/backend/tests/test_workflow_contract_sync.py`、`tests/e2e/new_agents_browser/sse_mock.py`、`tests/e2e/new_agents_browser/test_alex_user_story_breakdown_workflow.py`。
- 当前工作区：`HEAD` 与上游均为 `a7863d4c0d9b284c2ce3d8aface33a72bdeddc33`；工作区有大量既有无关脏改动，主要在 BMad、Intent Tester 产物、根文档和 Lisa 场景文件。本轮只写入 Alex 第 3 轮相关文件，不回滚、不格式化、不 stage 无关改动。

已确认目标来源：

- 来源：`docs/todos/2026-07-08-new-agents-alex-requirement-to-user-story-handoff.md`。
- 本轮承接：第 3 轮，用户故事卡片具备结构化契约和质量校验。
- 上一轮状态：第 2 轮已完成并推送，新增 `USER_STORY_BREAKDOWN` 工作流、`VALUE_DISCOVERY/BLUEPRINT -> USER_STORY_BREAKDOWN/SCOPE` handoff 和浏览器级 mock E2E。

改道条件检查：

- 新 P0/P1：`structured-artifact-failure-reduction` 仍是 P0，但本轮 Alex 第 3 轮同样处理结构化 `artifact_data` 和显式失败，不冲突；该文件第 3 轮的“可计算字段后端化”不抢占本轮。
- 未关闭质量门：上一轮全量本地自动化提权后通过；当前没有新的 LLM judge 低分或用户反馈要求先修复。
- 架构冲突：无。实现必须继续复用共享 Agent Runtime、typed SSE、manifest、后端 contract、artifact renderer、前端共享 workflow 配置，不新增 Alex 专属 runtime、store、API 或渲染管线。
- 工作区冲突：无关脏改动很多，但本轮可通过限定 stage 文件规避。
- 子智能体 / 旁路审查：不派发写入 worker。原因是 schema、renderer、runtime 指令和测试共享同一数据模型，拆给多个 worker 容易造成 contract drift；后续用聚焦测试、New Agents 回归和全量本地自动化做旁路验证。

边界复核：

- 本轮纳入：`USER_STORY_BREAKDOWN` 四个阶段支持结构化 `artifact_data`，后端确定性渲染用户故事拆解文档和单故事 Handoff 清单，契约测试覆盖 story/requirement/slice/ready 状态等关键失败路径。
- 本轮排除：第 4 轮的单故事 packet 持久化、故事卡 UI 选择、上游版本 stale 提示、真实 AI Coding workflow、Lisa handoff 新能力。
- 厚度门禁：入口是现有用户故事拆解 workflow；动作是用户让 Alex 拆用户故事；处理是模型输出结构化需求数据、后端校验并渲染；结果是右侧稳定 Markdown artifact 和可持久化结构化原始数据；承接是后续 packet 可从 artifact version 的结构化数据读取；失败反馈是 Pydantic/contract 显式拒绝非法故事；证据是 TDD、runtime、contract、E2E mock 和回归命令。

结论：继续承接 Alex 路线第 3 轮。

## Brainstorming 自问自答记录

### Explore Project Context

当前 `USER_STORY_BREAKDOWN` 已在线，阶段为 `SCOPE -> STORY_MAP -> STORIES -> HANDOFF`，但后端只校验 Markdown 标题。`agent_runtime.py` 的 `supports_artifact_data_rendering()` 尚未包含该 workflow；`build_structured_output_instruction()` 也没有用户故事拆解指令。因此模型现在可以输出看起来完整的 Markdown，但 storyId、requirementId、Ready 状态、验收标准和引用关系无法被机械拦截。

现有 artifact-data 体系集中在 `artifact_data_renderers.py`：Pydantic 模型、业务不变量、final renderer、partial renderer 和测试都在同一共享路径。第 3 轮应顺着这个路径扩展，而不是新建 Alex 专用解析器。

### Visual Companion Decision

本轮不新增新的前端视觉组件。`SCOPE` 与 `STORY_MAP` 继续由后端 deterministic renderer 生成 Mermaid `flowchart`，`STORIES` 和 `HANDOFF` 主要是结构化表格。第 4 轮若需要故事卡交互再考虑 UI。

### Clarifying Questions

- 用户是谁？产品经理或需求梳理者，目标是把需求蓝图拆成可交给后续 AI Coding 的细粒度用户故事。
- 成功状态是什么？每个阶段的右侧 artifact 都由结构化 `artifact_data` 渲染，Ready story 必须满足可交付需求字段，非法数据显式失败。
- 输入来自哪里？可以来自上游 `VALUE_DISCOVERY/BLUEPRINT` handoff，也可以是用户新输入。
- 下游需要什么？第 4 轮需要从 artifact version 中读取结构化 story 数据生成单故事 packet，因此本轮不能依赖 Markdown 反解析。
- 什么不做？不输出实现任务、文件路径、测试命令、架构方案，也不设计真实 AI Coding workflow。
- 失败如何处理？缺少来源需求、验收标准、业务规则/不适用说明、不做范围、依赖、not_ready 阻塞原因，或 storyId 重复、引用不存在、Ready 状态非法时，Pydantic 校验失败并进入现有 typed error 路径。

### Approaches

方案 A：只强化 Markdown contract。改动小，但仍要从 Markdown 反解析 story，无法满足后续 packet 的结构化数据要求，不选。

方案 B：只给 `STORIES` 和 `HANDOFF` 增加结构化契约。能解决卡片质量，但 `SCOPE` 和 `STORY_MAP` 的 requirement/activity/task/slice ID 仍没有结构化来源，跨阶段追溯不稳定，不选为完整第 3 轮。

方案 C：为 `USER_STORY_BREAKDOWN` 四阶段接入共享 `artifact_data` 体系。模型只输出需求事实、故事地图、故事卡和 handoff 清单的结构化数据；后端负责 Markdown、Mermaid 和质量校验。该方案覆盖入口、处理、结果、失败反馈和后续承接，推荐采用。

### Presented Design

Architecture：

- 在 `agent_runtime.py` 增加四个 `USER_STORY_BREAKDOWN` artifact-data structured output instruction，并纳入 `supports_artifact_data_rendering()` 和 `build_structured_output_instruction()`。
- 在 `artifact_data_renderers.py` 增加四阶段 Pydantic 模型、final renderer 和 partial renderer，复用 `StrictArtifactDataModel`、`StageGateCheck`、`AgentTurnOutput`。
- 继续通过 `validate_agent_turn()` 校验 Markdown headings、Mermaid 和 stage action，不新增运行时分支。

Data model：

- `SCOPE`：`document_info`、`in_scope_requirements`、`traceability_index`、`out_of_scope_items`、`blocking_questions`、`stage_gate`。
- `STORY_MAP`：`activities`、`tasks`、`story_map_items`、`mvp_slices`、`release_slices`、`stage_gate`。
- `STORIES`：`split_principles`、`story_cards`、`ready_story_summaries`、`not_ready_stories`、`open_questions`、`stage_gate`。
- `HANDOFF`：`ready_story_overview`、`single_story_packets`、`upstream_traceability`、`not_ready_blockers`、`ai_coding_input_boundary`、`stage_gate`。

Quality rules：

- `requirement_id`、`story_id`、`activity_id`、`task_id`、`slice_id` 在各自集合内唯一。
- 所有 story 必须引用已存在 requirement；story map 必须引用已存在 activity/task。
- `ready` story 必须包含用户故事正文、验收标准、来源需求、业务规则或明确 `N/A` 说明、不做范围、依赖，且状态只能是 `ready`。
- `not_ready` story 必须包含阻塞原因和待补充问题，状态只能是 `not_ready`。
- Handoff 清单只能包含 `ready` story，不包含实现计划、代码路径、开发任务或测试命令。

Testing：

- 先写失败测试：renderer final/partial、非法 story 校验、runtime instruction、raw JSON streaming、workflow contract sync、browser mock 数据。
- 验证从 unit 到 E2E mock 的共享路径，不运行真实模型 smoke，除非用户明确批准外部调用。
