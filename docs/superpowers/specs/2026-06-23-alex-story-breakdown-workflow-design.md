# Alex 用户故事拆解 Workflow 设计

## 背景

当前 New Agents 已在 Alex 中提供 `IDEA_BRAINSTORM`、`VALUE_DISCOVERY` 和 `PRD_REVIEW`。用户可以从创意形成价值蓝图，也可以评审和补全 PRD，但还不能把 PRD、需求蓝图或 PRD Review 修订蓝图进一步拆成研发评审可用的 Epic、User Story、验收标准、依赖风险和 Sprint 切片。

`docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md` 将 E13 `Alex 用户故事拆解 workflow` 标为 P0。本轮把它作为完整在线 workflow 主线化，而不是只补 prompt、单个 backlog schema 或旧的单阶段 story parser。

## 用户故事

作为产品经理或业务分析师，我可以在 Alex 中选择 `用户故事拆解`，输入 PRD、需求蓝图或 PRD Review 修订蓝图，得到一份结构化用户故事包，包含 Epic map、User Story backlog、验收标准、依赖/风险、Sprint 切片建议和 Lisa handoff 输入，从而把产品需求交给研发和测试继续评审。

## 范围

纳入本轮：

- 新增在线 workflow `STORY_BREAKDOWN`，slug 为 `story-breakdown`，归属 Alex。
- 在共享 `tools/new-agents/workflow_manifest.json` 中声明 listing、onboarding、阶段、artifact contract、visual contract 和 handoff。
- 阶段为 `INPUT_ANALYSIS`、`EPIC_MAPPING`、`STORY_BACKLOG`、`SPRINT_PLAN`。
- 前端 `WorkflowType`、prompt/template registry、Alex workflow listing 自动出现在线卡片，并移除旧 plan placeholder。
- 后端 `WORKFLOW_STAGES`、artifact headings、structured visual、runtime structured output instruction 同步。
- 新增 `StoryBreakdownArtifactData` Pydantic schema 和 deterministic renderer，禁止要求模型直接输出完整 Markdown、Mermaid 或 `ai4se-visual`。
- 最终阶段可生成面向 Lisa `TEST_DESIGN` 或 `REQ_REVIEW` 的 handoff 输入。
- 覆盖前后端最小验收测试，证明 `STORY_BREAKDOWN` 使用共享 Agent Runtime、typed SSE、manifest、artifact contract 和共享 UI 配置。

不纳入本轮：

- 不写入 Jira、禅道、飞书项目或其他外部项目管理工具。
- 不新增 Alex 专属 API、store、SSE path、runtime 或 renderer pipeline。
- 不做 Artifact 质量诊断面板、Lisa 测试资产质量闭环或历史中心增强。
- 不做真实 LLM judge/e2e smoke；真实模型 smoke 需要凭证、网络和额度，保留为后续可选验证。

## 用户动作链

1. 用户进入 New Agents，选择 Alex。
2. 用户在 workflow listing 中看到 `用户故事拆解` 在线卡片，理解适用场景、输入要求、预期产物和样例输入。
3. 用户进入 `/workspace/alex/story-breakdown`，粘贴 PRD、需求蓝图或 PRD Review 修订蓝图。
4. 共享 Agent Runtime 按 `INPUT_ANALYSIS -> EPIC_MAPPING -> STORY_BACKLOG -> SPRINT_PLAN` 推进。
5. 模型只返回 `artifact_data` JSON；后端 Pydantic schema 校验业务数据并确定性渲染 artifact。
6. 右侧 artifact 显示输入分析、Epic Map、User Story Backlog、验收标准、依赖风险、Sprint 切片和 Lisa Handoff 输入。
7. 若模型返回缺字段、空数组、非法引用、重复 ID 或缺 stage gate，后端显式失败并进入既有 retry/错误路径，不伪造成功产物。

## 阶段设计

### INPUT_ANALYSIS / 输入分析

盘点输入材料、业务目标、目标用户、范围边界、约束、已有验收材料和缺失信息，判断是否具备拆分故事的上下文。

### EPIC_MAPPING / Epic 映射

把 PRD 或需求蓝图拆成 Epic、能力边界、用户价值、业务目标、依赖关系和优先级，形成故事拆解骨架。

### STORY_BACKLOG / Story Backlog

生成 User Story、验收标准、优先级、依赖、测试提示和可测试性等级，形成可进入研发评审的 backlog。

### SPRINT_PLAN / Sprint 计划

把 Story backlog 组织成 Sprint 切片和交付包，明确风险、依赖、拆分理由、验收门禁和 Lisa handoff 输入。

## Artifact Contract

各阶段必须包含稳定 H1/H2 结构。

`INPUT_ANALYSIS` 必须包含：

- `# 用户故事拆解包`
- `## 输入分析`
- `## 目标用户与场景`
- `## 范围与约束`
- `## 待澄清问题`
- `## 阶段门禁`

`EPIC_MAPPING` 必须包含：

- `# 用户故事拆解包`
- `## 输入分析`
- `## Epic Map`
- `## Epic 依赖`
- `## 阶段门禁`

`STORY_BACKLOG` 必须包含：

- `# 用户故事拆解包`
- `## 输入分析`
- `## Epic Map`
- `## User Story Backlog`
- `## 验收标准`
- `## 依赖与风险`
- `## 阶段门禁`

`SPRINT_PLAN` 必须包含：

- `# 用户故事拆解包`
- `## 输入分析`
- `## Epic Map`
- `## User Story Backlog`
- `## 验收标准`
- `## 依赖与风险`
- `## Sprint 切片建议`
- `## Lisa Handoff 输入`
- `## 阶段门禁`
- structured visual: `story-map`

## Artifact Data Contract

后端新增 Story Breakdown artifact_data schema，字段覆盖：

- `document_info`
- `input_analysis`
- `epics`
- `stories`
- `acceptance_criteria`
- `dependencies`
- `risks`
- `sprint_slices`
- `handoff_inputs`
- `stage_gate`

约束：

- 字符串非空，数组非空。
- `epic_id`、`story_id`、`criterion_id`、`sprint_id` 唯一。
- `stories.epic_id` 只能引用已存在 Epic。
- `acceptance_criteria.story_id` 只能引用已存在 Story。
- `dependencies.source_story_id` 与 `dependencies.target_story_id` 只能引用已存在 Story，且不能相同。
- `risks.related_story_ids`、`sprint_slices.story_ids`、`handoff_inputs.story_ids` 只能引用已存在 Story。
- `stage_gate` 至少一个 `checked=true`。
- renderer 输出必须通过 `validate_agent_turn()`。

## Handoff

最终 `SPRINT_PLAN` 阶段提供 Lisa handoff 输入，目标 workflow 为：

- `TEST_DESIGN/CLARIFY`：把 Story、AC、依赖和风险作为测试设计输入。
- `REQ_REVIEW/REVIEW`：把 Story 和 AC 作为可测试性/一致性评审输入。

handoff 必须继续通过现有 manifest/handoff 基础设施表达，不新增专属路径。

## 风险与取舍

- `STORY_BREAKDOWN` 会触及 manifest、前端 registry、后端 contract、runtime、renderer、handoff 和测试。为降低同步风险，本轮用 contract sync、runtime 和 frontend config tests 覆盖。
- 与 `PRD_REVIEW` 的边界是：PRD Review 判断 PRD 是否完整并给出修订蓝图；Story Breakdown 把可用 PRD/蓝图拆成研发和测试可消费的故事包。
- 外部项目管理工具写入不进入本轮，因为那会引入认证、映射、失败重试和权限模型，属于独立能力包。

## 验收条件

- `WORKFLOWS.STORY_BREAKDOWN` 存在，归属 Alex，slug 为 `story-breakdown`，在线卡片可达。
- 每个 `STORY_BREAKDOWN` stage 都有 prompt/template 内容，且来源于共享 manifest 的 `promptTemplateId`。
- 后端 manifest sync 测试证明 `STORY_BREAKDOWN` stage keys 与 artifact contract、visual contract、prompt files 对齐。
- `build_structured_output_instruction("STORY_BREAKDOWN", stage)` 明确要求 `artifact_data`，并禁止模型直出完整 Markdown/Mermaid/`ai4se-visual`。
- `StoryBreakdownArtifactData` 拒绝未知 Epic/Story 引用、重复 ID 和缺 stage gate 的数据。
- 同一份合法 `artifact_data` 对 4 个阶段渲染结果确定性一致，并通过 `validate_agent_turn()`。
- 最终阶段 handoff 能生成 Lisa `TEST_DESIGN` 或 `REQ_REVIEW` 可读上下文。
- 不引入 agent-specific runtime/API/store/renderer。

