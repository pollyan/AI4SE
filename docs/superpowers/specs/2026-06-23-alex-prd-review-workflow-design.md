# Alex PRD 质量评审与补全 Workflow 设计

## 背景

Goal mode 当前工作池中，New Agents 的 P0/P1 缺口已经从“能生成 artifact”转向“能诊断、能审阅、能修订、能复用、能验收”的专业闭环。Alex 现有在线 workflow 覆盖创意发散和价值发现，但缺少面向已有 PRD/需求草案的质量评审与补全链路。

本切片选择把 Alex 的 PRD 质量评审与补全做成一个完整在线 workflow，而不是只补单个 prompt、单个卡片或单个 renderer 分支。

## 用户价值

产品经理或业务分析师可以把已有 PRD、需求草案、Epic 或用户故事输入 Alex，获得一份结构化的 PRD 质量评审与补全文档，覆盖事实盘点、质量问题、补全建议和修订蓝图，并能继续走共享 Agent Runtime、typed SSE、artifact contract、运行持久化和右侧 artifact 渲染链路。

## 范围

纳入本轮:

- 新增在线 workflow `PRD_REVIEW`，slug 为 `prd-review`，归属 Alex。
- 在共享 `workflow_manifest.json` 中声明 listing、onboarding、阶段、artifact contract 和 visual contract。
- 阶段为 `INVENTORY`、`QUALITY_AUDIT`、`COMPLETION_PLAN`、`REVISION_BLUEPRINT`。
- 前端 `WorkflowType`、prompt/template registry、Alex workflow listing 自动出现在线卡片。
- 后端 `WORKFLOW_STAGES`、artifact headings、structured visual、DeepSeek V4 artifact_data readiness 同步。
- 新增 deterministic `artifact_data` schema 和 renderer，禁止要求模型直接输出完整 Markdown。
- 覆盖前后端最小验收测试，证明 PRD_REVIEW 使用共享 runtime/manifest/contract。

不纳入本轮:

- 不新增 Alex 专属 API、store、SSE path、runtime 或 renderer pipeline。
- 不接入 Jira、禅道、Confluence 等外部系统。
- 不做真实 LLM judge/e2e smoke；仅保留后续候选。
- 不实现跨 workflow 自动推荐排序。

## 阶段设计

1. `INVENTORY` / PRD 输入盘点
   - 识别文档目标、用户、业务背景、范围、需求事实、验收材料和缺失信息。
2. `QUALITY_AUDIT` / PRD 质量评审
   - 从完整性、一致性、可测试性、边界、非功能、风险和证据强度评审 PRD。
3. `COMPLETION_PLAN` / 补全建议
   - 给出问题到补全动作的映射、优先级、owner、验证方式和复审条件。
4. `REVISION_BLUEPRINT` / 修订蓝图
   - 形成可交付的 PRD 修订蓝图，包含推荐结构、关键改写片段、验收标准、Lisa handoff 输入和阶段门禁。

## Artifact Contract

每个阶段必须有独立 H1 和必填 H2。最终阶段必须包含:

- `# PRD 修订蓝图`
- PRD 目标与范围
- 质量评审摘要
- 补全任务清单
- 推荐 PRD 结构
- 核心需求改写
- 验收标准与可测试性
- Lisa Handoff 输入
- 复审条件
- 阶段门禁

结构化可视化使用现有通用 visual renderer:

- `QUALITY_AUDIT`: `score-matrix`
- `COMPLETION_PLAN`: `action-board`
- `REVISION_BLUEPRINT`: `roadmap`

## Artifact Data Contract

后端新增 PRD Review artifact_data schema，字段覆盖:

- `document_info`
- `prd_inventory`
- `quality_findings`
- `completion_actions`
- `revision_sections`
- `acceptance_criteria`
- `handoff_inputs`
- `stage_gate`

约束:

- 字符串非空，数组非空。
- `quality_findings.finding_id` 唯一。
- `completion_actions.action_id` 唯一。
- `completion_actions.finding_ids` 必须引用已存在 finding。
- `revision_sections.section_id` 唯一。
- `acceptance_criteria.related_section_ids` 必须引用已存在 section。
- `handoff_inputs.related_section_ids` 必须引用已存在 section。
- `stage_gate` 至少一个 `checked=true`。

## 验收

- `WORKFLOWS.PRD_REVIEW` 存在，归属 Alex，在线卡片 `prd-review` 可达。
- 每个 PRD_REVIEW stage 都有 prompt/template 内容，且来源于共享 manifest 的 `promptTemplateId`。
- 后端 manifest sync 测试通过，PRD_REVIEW stage keys 与 artifact contract、prompt files 对齐。
- DeepSeek V4 readiness 测试通过，所有 manifest stages 都使用 artifact_data，不要求模型直出 Markdown。
- PRD_REVIEW artifact_data renderer 输出确定性 Markdown，且通过 `validate_agent_turn`。
- 不引入 agent-specific runtime/API/store/renderer。
