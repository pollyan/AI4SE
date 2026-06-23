# Alex 用户故事拆解 Workflow 设计

## 背景

New Agents 当前 Alex 已具备 `IDEA_BRAINSTORM`、`VALUE_DISCOVERY` 和 `PRD_REVIEW`。`tools/new-agents/frontend/src/core/config/agentWorkflows.ts` 中仍存在 `story-breakdown` plan 卡片，说明用户入口已有预期，但还不能通过共享 Agent Runtime 生成可交付的用户故事包。

本切片把 `story-breakdown` 从 plan 卡片升级为在线 `STORY_BREAKDOWN` workflow，继续复用共享 `/api/agent/runs/stream`、typed SSE、workflow manifest、artifact contract、run/artifact persistence 和共享 UI。

## 用户价值

产品经理、业务分析师或研发负责人可以输入 PRD、需求蓝图、Epic 草案或业务目标，Alex 输出可进入研发排期的 Epic/User Story/验收标准/Sprint 切片包，并保留 Lisa 后续需求评审或测试设计所需输入。

## 范围

纳入本轮:

- 新增在线 workflow `STORY_BREAKDOWN`，slug 为 `story-breakdown`，归属 Alex。
- 阶段为 `INPUT_ANALYSIS`、`EPIC_MAPPING`、`STORY_WRITING`、`SPRINT_SLICING`。
- 在共享 manifest 中声明 listing、onboarding、stage、artifact contract 和 visual contract。
- 前端 workflow registry、`WorkflowType`、prompt/template 映射和 Alex 在线卡片同步。
- 后端 `WORKFLOW_STAGES`、artifact headings、structured visual contract、DeepSeek V4 artifact_data readiness 同步。
- 新增 deterministic `artifact_data` schema 和 renderer，模型只输出业务数据，后端渲染 Markdown 和 `ai4se-visual`。
- 新增前后端测试证明 workflow 接入共享链路。

不纳入本轮:

- 不写入 Jira、禅道、Linear 或其他外部项目管理系统。
- 不新增 Alex 专属 runtime、API path、store 或 renderer pipeline。
- 不做跨团队权限、分享和项目管理状态同步。
- 不运行真实 LLM smoke；缺少凭证、网络和额度时只做确定性本地验证。

## 阶段设计

1. `INPUT_ANALYSIS` / 需求输入分析
   - 识别业务目标、用户、场景、范围、约束、已有验收材料和拆解风险。
2. `EPIC_MAPPING` / Epic 映射
   - 将目标和场景聚合为 Epic，声明价值、边界、依赖、风险和优先级。
3. `STORY_WRITING` / Story 与 AC
   - 生成用户故事、Given/When/Then 验收标准、依赖、可测试性等级和 Lisa 输入。
4. `SPRINT_SLICING` / Sprint 切片
   - 形成 Sprint 候选包、排序、依赖处理、风险接受和交付门禁。

## Artifact Data Contract

后端新增 `StoryBreakdownArtifactData`，字段覆盖:

- `document_info`
- `input_insights`
- `epics`
- `stories`
- `acceptance_criteria`
- `dependencies`
- `sprint_slices`
- `handoff_inputs`
- `stage_gate`

一致性约束:

- 所有字符串非空，数组非空。
- `epics.epic_id`、`stories.story_id`、`acceptance_criteria.ac_id`、`sprint_slices.slice_id` 唯一。
- `stories.epic_id` 必须引用已存在 Epic。
- `acceptance_criteria.story_id` 必须引用已存在 Story。
- `dependencies.source_story_id` 和 `dependencies.target_story_id` 必须引用已存在 Story，且不能相同。
- `sprint_slices.story_ids` 必须引用已存在 Story。
- `handoff_inputs.story_ids` 必须引用已存在 Story。
- `stage_gate` 至少包含一个 `checked=true`。

## Artifact Contract

每个阶段有独立 H1 和必填 H2:

- `# 需求输入分析`
- `# Epic 映射`
- `# 用户故事与验收标准`
- `# Sprint 切片计划`

结构化可视化:

- `EPIC_MAPPING`: `roadmap`
- `STORY_WRITING`: `traceability-matrix`
- `SPRINT_SLICING`: `priority-board`

## 验收

- `WORKFLOWS.STORY_BREAKDOWN` 存在，归属 Alex，在线卡片 `story-breakdown` 可达。
- 原 plan 卡片不再重复显示为 `NON_RUNTIME_AGENT_WORKFLOWS`。
- 4 个阶段均有 prompt/template，且由共享 manifest 的 `promptTemplateId` 驱动。
- 后端 manifest/stage/artifact/prompt file 同步测试通过。
- DeepSeek V4 readiness 覆盖 `STORY_BREAKDOWN` 全阶段，instruction 要求 `artifact_data`，不要求 `artifact_update.markdown`。
- `StoryBreakdownArtifactData` 能拒绝非法引用，并能确定性渲染通过 `validate_agent_turn()` 的 Markdown artifact。
- 不新增 agent-specific runtime/API/store/renderer。
