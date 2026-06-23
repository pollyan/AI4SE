# Alex PRD 质量评审与补全 Workflow 设计

## 背景

Goal mode 当前工作池中，New Agents 的 P0 缺口已经从“能生成 artifact”转向“能诊断、能审阅、能修订、能复用、能验收”的专业闭环。Alex 现有在线 workflow 覆盖创意发散和价值发现，但缺少面向已有 PRD、需求草案、Epic 或用户故事的质量评审与补全链路。

本切片把 Alex 的 PRD 质量评审与补全做成一个完整在线 workflow，而不是只补一个 prompt、一个入口卡片、一个 schema 或一个 renderer 分支。

## 用户故事

作为产品经理或业务分析师，我可以在 Alex 中选择 `PRD 质量评审与补全`，输入已有 PRD 或需求草案，获得一份覆盖输入盘点、质量问题、补全建议和修订蓝图的结构化产物，从而知道 PRD 哪些地方不完整、哪些问题会阻断研发或测试、下一步应如何修订，并能把可测试性相关输入交给 Lisa 继续评审。

## 范围

纳入本轮：

- 新增在线 workflow `PRD_REVIEW`，slug 为 `prd-review`，归属 Alex。
- 在共享 `tools/new-agents/workflow_manifest.json` 中声明 listing、onboarding、阶段、artifact contract 和 visual contract。
- 阶段为 `INVENTORY`、`QUALITY_AUDIT`、`COMPLETION_PLAN`、`REVISION_BLUEPRINT`。
- 前端 `WorkflowType`、prompt/template registry、Alex workflow listing 自动出现在线卡片。
- 后端 `WORKFLOW_STAGES`、artifact headings、structured visual、artifact_data readiness 同步。
- 新增 deterministic `artifact_data` schema 和 renderer，禁止要求模型直接输出完整 Markdown、Mermaid 或 `ai4se-visual`。
- 覆盖前后端最小验收测试，证明 `PRD_REVIEW` 使用共享 Agent Runtime、typed SSE、manifest、artifact contract 和共享 UI 配置。

不纳入本轮：

- 不新增 Alex 专属 API、store、SSE path、runtime 或 renderer pipeline。
- 不接入 Jira、禅道、Confluence 等外部系统。
- 不实现 `STORY_BREAKDOWN`，该 workflow 保留为下一轮候选。
- 不做真实 LLM judge/e2e smoke；真实模型 smoke 需要凭证、网络和额度，保留为后续可选验证。
- 不实现跨 workflow 自动推荐排序。

## 用户动作链

1. 用户进入 New Agents，选择 Alex。
2. 用户在 workflow listing 中看到 `PRD 质量评审与补全` 在线卡片，理解适用场景、输入要求、预期产物和样例输入。
3. 用户进入 `/workspace/alex/prd-review`，粘贴 PRD、需求草案或 Epic/User Story 材料。
4. 共享 Agent Runtime 按 `INVENTORY -> QUALITY_AUDIT -> COMPLETION_PLAN -> REVISION_BLUEPRINT` 推进。
5. 模型只返回 `artifact_data` JSON；后端 Pydantic schema 校验业务数据并确定性渲染 artifact。
6. 右侧 artifact 显示 PRD 输入盘点、质量评分矩阵、问题清单、补全行动、修订结构、验收标准和 Lisa Handoff 输入。
7. 若模型返回缺字段、空数组、非法引用或缺 stage gate，后端显式失败并进入既有 retry/错误路径，不伪造成功产物。

## 阶段设计

### INVENTORY / PRD 输入盘点

识别文档目标、业务背景、目标用户、范围边界、输入材料、已有验收材料和缺失信息。产物用于判断是否具备进入质量评审的基本上下文。

### QUALITY_AUDIT / PRD 质量评审

从业务目标、用户价值、范围边界、功能完整性、异常路径、非功能需求、成功指标、依赖风险和证据强度评审 PRD，并输出评分矩阵与问题清单。

### COMPLETION_PLAN / 补全建议

把质量问题映射为可执行补全动作，包含优先级、owner、验证方式、依赖和复审条件，帮助 PM 知道先补什么、谁确认、用什么证据验收。

### REVISION_BLUEPRINT / 修订蓝图

形成可交付的 PRD 修订蓝图，包含推荐结构、核心改写建议、验收标准、Lisa handoff 输入、复审条件和阶段门禁。

## Artifact Contract

各阶段必须包含稳定 H1/H2 结构。

`INVENTORY` 必须包含：

- `# PRD 输入盘点`
- `## 文档信息`
- `## PRD 目标与范围`
- `## 输入事实清单`
- `## 用户与场景`
- `## 现有验收材料`
- `## 缺失信息清单`
- `## 阶段门禁`

`QUALITY_AUDIT` 必须包含：

- `# PRD 质量评审`
- `## 文档信息`
- `## PRD 目标与范围`
- `## 质量评审摘要`
- `## 质量评分矩阵`
- `## 问题清单`
- `## 风险影响`
- `## 阶段门禁`
- structured visual: `score-matrix`

`COMPLETION_PLAN` 必须包含：

- `# PRD 补全建议`
- `## 文档信息`
- `## PRD 目标与范围`
- `## 质量评审摘要`
- `## 补全任务清单`
- `## 推荐 PRD 结构`
- `## 验证方式与复审条件`
- `## 阶段门禁`
- structured visual: `action-board`

`REVISION_BLUEPRINT` 必须包含：

- `# PRD 修订蓝图`
- `## 文档信息`
- `## PRD 目标与范围`
- `## 质量评审摘要`
- `## 补全任务清单`
- `## 推荐 PRD 结构`
- `## 核心需求改写`
- `## 验收标准与可测试性`
- `## Lisa Handoff 输入`
- `## 复审条件`
- `## 阶段门禁`
- structured visual: `roadmap`

## Artifact Data Contract

后端新增 PRD Review artifact_data schema，字段覆盖：

- `document_info`
- `prd_inventory`
- `quality_findings`
- `completion_actions`
- `revision_sections`
- `acceptance_criteria`
- `handoff_inputs`
- `stage_gate`

约束：

- 字符串非空，数组非空。
- `quality_findings.finding_id` 唯一。
- `completion_actions.action_id` 唯一。
- `completion_actions.finding_ids` 只能引用已存在 finding。
- `revision_sections.section_id` 唯一。
- `acceptance_criteria.related_section_ids` 只能引用已存在 section。
- `handoff_inputs.related_section_ids` 只能引用已存在 section。
- `stage_gate` 至少一个 `checked=true`。
- renderer 输出必须通过 `validate_agent_turn()`。

## 风险与取舍

- `PRD_REVIEW` 与 Lisa `REQ_REVIEW` 容易边界混淆。本轮把 Alex 定位为产品完整性、业务价值和 PRD 修订质量；Lisa 继续负责需求可测试性、测试风险和测试设计输入。
- 新 workflow 会同步触达 manifest、前端 registry、后端 contract、runtime 和 renderer。为降低风险，所有差异通过共享配置、prompt/template、Pydantic model 和共享 renderer dispatch 表达，不新增专属 runtime 或 API。
- 真实 DeepSeek V4 Flash smoke 不作为默认本地门禁，因为需要外部凭证、网络和额度；本轮用 deterministic artifact_data tests 证明格式化输出链路。

## 验收条件

- `WORKFLOWS.PRD_REVIEW` 存在，归属 Alex，slug 为 `prd-review`，在线卡片可达。
- 每个 `PRD_REVIEW` stage 都有 prompt/template 内容，且来源于共享 manifest 的 `promptTemplateId`。
- 后端 manifest sync 测试证明 `PRD_REVIEW` stage keys 与 artifact contract、visual contract、prompt files 对齐。
- `build_structured_output_instruction("PRD_REVIEW", stage)` 明确要求 `artifact_data`，并禁止模型直出完整 Markdown/Mermaid/`ai4se-visual`。
- `PrdReviewArtifactData` 拒绝未知 finding/section 引用和缺 stage gate 的数据。
- 同一份合法 `artifact_data` 对 4 个阶段渲染结果确定性一致，并通过 `validate_agent_turn()`。
- 不引入 agent-specific runtime/API/store/renderer。
