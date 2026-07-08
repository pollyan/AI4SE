# Alex 单故事需求包持久化设计

## 目标承接检查

事实源快照：
- 已读取：`AGENTS.md`、`docs/index.md`、`docs/strategy/goal-mode-playbook.md`、`docs/strategy/goal-mode-cga-template.md`、`docs/todos/2026-07-08-new-agents-alex-requirement-to-user-story-handoff.md`、`docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md`。
- 已读取代码：`workflow_handoffs.py`、`models.py`、`run_persistence.py`、`routes.py`、`app.py`、`artifact_data_renderers.py`、`runSnapshotService.ts`、`workflowHandoffService.ts`、`ArtifactPane.tsx`、`store.ts` 和相关测试。
- 当前工作区：存在大量与本轮无关的删除、文档和生成物变更；本轮只允许写入 `tools/new-agents/` 相关代码/测试、Alex todo、API/TESTING 文档和本 spec/plan。

已确认目标来源：
- 来源：`docs/todos/2026-07-08-new-agents-alex-requirement-to-user-story-handoff.md`。
- 本轮承接：第 4 轮“单个 ready 用户故事可形成持久化 handoff packet”。
- 上一轮状态：第 3 轮已完成，`USER_STORY_BREAKDOWN` 四阶段已支持结构化 `artifact_data` 并持久化到 `agent_artifact_versions.artifact_data`。

改道条件检查：
- 用户新反馈：Playbook 增加“独立价值点后验证、commit、push GitHub”的规则；当前文件已包含该规则，第 5 节和第 9 节已覆盖，无需重复修改。
- 新 P0/P1：结构化失败治理 todo 仍是 P0，但当前 Alex 第 4 轮直接消费第 3 轮 `artifact_data` 持久化成果，且是已声明顺序中的下一轮，继续承接。
- 未关闭质量门：上一轮全量 `test-local.sh all` 只因 sandbox 权限和平台额度阻塞失败，New Agents 聚焦验证通过；本轮仍需提交前重跑聚焦和全量验证，若环境阻塞需记录。
- 架构冲突：不得新增 Alex 专属 runtime/store/transport；packet 能力必须挂在共享 Flask API、SQLAlchemy model、ArtifactPane 和 typed frontend service 上。
- 工作区冲突：无关脏文件不触碰、不格式化、不 stage。
- 子智能体 / 旁路审查：本轮代码跨后端和前端，但接口、持久化和 UI 需要连续 TDD 集成，当前不拆给写入型 worker；验证前可用聚焦命令替代旁路审查，收尾记录未派发原因。

边界复核：
- 本轮纳入：从 `USER_STORY_BREAKDOWN/HANDOFF` 当前 artifact version 的结构化 `artifactData` 中列出 ready stories；用户选择单张 ready story 后，后端生成并持久化单故事需求包；API 可读取；ArtifactPane 展示摘要、复制内容并提示 stale。
- 本轮排除：真实 AI Coding workflow 消费协议、Lisa handoff 改造、跨 workflow 一等 handoff 关系表、全链路 idea -> packet 浏览器证据收口。
- 厚度门禁：入口、动作、处理、可见结果、状态承接、失败反馈和验证证据均成立。

结论：继续承接 Alex 第 4 轮。

## Superpowers 自问自答记录

### Explore Project Context

现有 `workflow_handoffs.py` 负责 workflow 之间的 prompt handoff，但它不适合承载单故事 packet，因为本轮不创建目标 run，也不把 Markdown prompt 当作正式数据。第 3 轮已经把 `artifact_data` 保存到 `AgentArtifactVersion`，`get_run_snapshot` 会返回 `artifactData`，但前端当前类型和 parser 还没有使用它。

`artifact_data_renderers.py` 中 `UserStoryHandoffArtifactData` 已经定义了 `ready_story_overview`、`single_story_packets`、`upstream_traceability` 和 `ai_coding_input_boundary`。这正好是 packet 生成的可信来源。不能从 Markdown 反解析故事卡。

### Visual Companion Decision

本轮有 UI 入口，但不涉及复杂布局选型或视觉风格探索；直接在现有 ArtifactPane 工具表面增加紧凑操作区即可，不使用浏览器 visual companion。

### Clarifying Questions

- 用户是谁：使用 Alex 做需求拆分的产品/需求负责人。
- 用户从哪里开始：已完成 `USER_STORY_BREAKDOWN/HANDOFF` 阶段并看到右侧“单故事 Handoff 清单”。
- 用户动作是什么：选择一张 ready story 并点击生成需求包。
- 成功状态是什么：需求包被保存，页面显示故事 ID、来源 artifact version/digest、需求字段摘要，并可复制完整 JSON/文本内容。
- 输入来源是什么：当前 run 的 `HANDOFF` artifact current version 的 `artifact_data`，不是 Markdown。
- 失败怎么处理：缺少 run、stage 不匹配、当前 artifact 不存在、artifactData 不存在或不合法、story 不存在、story 非 ready、packet 字段缺失时返回显式 4xx，不生成伪成功。
- stale 怎么定义：已保存 packet 的 `sourceArtifactVersion` 或 `sourceArtifactDigest` 与当前 `HANDOFF` artifact current version 不一致时标记 `isStale=true`。
- 不做什么：不输出 task、file path、implementation plan、architecture plan、test command；不启动真实 AI Coding workflow。

### Approaches

1. 推荐：新增共享 story handoff packet 持久化表与 API，前端通过专门 service 在 ArtifactPane 中读取候选、创建 packet、展示/复制。优点是数据可恢复、可追溯、错误边界清楚；缺点是需要跨后端和前端的厚切片实现。
2. 只在前端从 snapshot artifactData 生成临时 packet。优点是改动小；缺点是不可持久化，刷新丢失，不能通过 API 读取，不满足本轮目标。
3. 复用现有 workflow handoff prompt。优点是复用已有 endpoint；缺点是它面向创建目标 run，不适合单故事需求包，也会继续把 Markdown prompt 当数据源。

选择方案 1。

## 设计

### 后端数据模型

新增 `AgentStoryHandoffPacket`，归属一个 `AgentRun`，保存：
- `run_id`、`source_workflow_id`、`source_stage_id`
- `source_artifact_version`、`source_artifact_digest`
- `story_id`
- `packet_json`
- `created_at_ms`

`packet_json` 是面向后续 AI Coding 工具的需求数据，字段使用 camelCase：
`sourceRunId`、`sourceWorkflowId`、`sourceStageId`、`sourceArtifactVersion`、`sourceArtifactDigest`、`createdAt`、`storyId`、`requirementIds`、`userStory`、`acceptanceCriteria`、`businessRules`、`nonFunctionalNotes`、`outOfScope`、`dependencies`、`openQuestions`。

### 后端服务与 API

新增 `story_handoff_packets.py`：
- `list_story_handoff_candidates(run_id, stage_id="HANDOFF")`：读取 current artifact version 的 `artifact_data`，用 `UserStoryHandoffArtifactData.model_validate` 校验后返回 ready story 候选。
- `create_story_handoff_packet(run_id, story_id, stage_id="HANDOFF")`：从结构化数据生成 packet，保存并返回。
- `list_story_handoff_packets(run_id, stage_id="HANDOFF")`：返回已保存 packets，并根据当前 artifact version/digest 标记 `isStale`。

新增 API：
- `GET /api/agent/runs/<run_id>/story-handoff-candidates?stageId=HANDOFF`
- `GET /api/agent/runs/<run_id>/story-handoff-packets?stageId=HANDOFF`
- `POST /api/agent/runs/<run_id>/story-handoff-packets`，body: `{ "stageId": "HANDOFF", "storyId": "US-001" }`

失败返回沿用现有 `json_error_response`，不做 fallback。

### 前端交互

新增 `storyHandoffPacketService.ts` 和类型定义。ArtifactPane 在 `workflow=USER_STORY_BREAKDOWN`、当前阶段 `HANDOFF` 且存在 `currentRunId` 时显示“单故事需求包”操作区：
- 加载 ready story 候选和已保存 packet。
- 每个候选显示 storyId、title、来源 requirementIds 和生成按钮。
- 点击生成后调用 POST，成功后刷新 packet 列表。
- packet 摘要显示 storyId、source version、stale 状态和复制按钮。
- 复制内容为格式化 JSON；复制失败显式展示错误。

### 校验与测试

后端先写失败测试：
- 候选 API 从 `artifact_data` 返回 ready stories。
- 创建 packet 后可通过 API 读取，并包含追溯字段。
- packet 不包含禁止的实现字段。
- 非 ready / 不存在 story、缺少 artifactData、过期 packet 识别均有测试。

前端先写失败测试：
- service parser 校验候选和 packet 响应。
- ArtifactPane 加载候选，点击生成后显示 packet 摘要和复制按钮。
- stale packet 显示过期提示。

E2E mock 在第 4 轮至少覆盖 ArtifactPane packet 生成主路径；第 5 轮再做 idea -> 蓝图 -> 用户故事 -> packet 全链路证据收口。
