# IDEA CONVERGE 契约同步纵切设计

## 目标承接检查

当前 Alex 需求拆分路线已完成 5 轮并收口；继续推进的 P0 来源是 `docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md`。上一轮已完成 `TEST_DESIGN/CASES` 与 `TEST_DESIGN/STRATEGY` 的统计 / 引用治理，并修复了 Alex 需求蓝图 LLM Judge 质量门。当前没有未关闭的阻断测试失败或低分 judge。

本轮承接结构化产物失败治理中的横切项：建立 schema / prompt / contract 单源同步机制。待办明确指出 `IDEA_BRAINSTORM/CONVERGE` 仍存在 prompt / schema / contract 单源同步残余风险，因此本轮只做 `CONVERGE` 首个纵切，不进入视觉协议第 7 轮，也不改 Lisa / Alex 专属 runtime、SSE、store 或 ArtifactPane。

工作区存在大量与本轮无关的既有脏文件和删除项。本轮只允许写入：

- `tools/new-agents/workflow_manifest.json`
- `tools/new-agents/backend/workflow_manifest.py`
- `tools/new-agents/backend/agent_runtime.py`
- `tools/new-agents/backend/tests/test_agent_runtime.py`
- `tools/new-agents/backend/tests/test_workflow_contract_sync.py`
- `tools/new-agents/frontend/src/core/workflowRegistry.ts`
- `tools/new-agents/frontend/src/core/workflows.ts`
- `tools/new-agents/frontend/src/core/config/__tests__/workflows.test.ts`
- `docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md`
- 本 spec 和对应 plan

子智能体 / 旁路审查决策：本轮触点较少，主要是同一共享配置从 manifest 到后端 instruction、前端 prompt 的纵向链路，串行 TDD 更可靠；不分发子智能体。

## 当前问题

`IDEA_BRAINSTORM/CONVERGE` 的关键不变量已经由 Pydantic validator 机械保护，例如 `ice_evaluations.idea_id` 唯一、`rank` 唯一、`ice_score = impact * confidence / effort`、推荐方案必须同时出现在 ICE 结论和决策矩阵中、实验和合并路径只能引用已存在的 idea ID。

问题在于这些约束仍散落在多个地方：

- 后端 `IDEA_CONVERGE_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION` 手写一段约束说明。
- 前端 `CONVERGE_PROMPT` 手写一组相近但不完全等价的任务说明。
- `workflow_manifest.json` 只声明 artifact headings 和 Mermaid contract，没有 artifact_data 关键不变量。
- 同步测试目前只证明 manifest stage、artifact headings、visual contract 和 prompt file 存在，不证明关键 artifact_data 约束在后端 instruction 和前端 prompt 同时出现。

这会导致后续改 validator 时，prompt 或 manifest 容易漏改，模型继续输出后端会拒绝的数据。

## 设计决策

采用 `workflow_manifest.json` 作为首个共享配置源，在 `IDEA_BRAINSTORM/CONVERGE` stage 下新增 `artifactDataContract`：

- `modelOutputRules`：模型必须遵守的 artifact_data 业务不变量。
- `forbiddenOutputs`：模型不得直接输出的产物形态，例如完整 Markdown、Markdown 表格、Mermaid 代码块和 `quadrantChart`。
- `rendererOutputs`：由后端确定性渲染的产物，例如右侧收敛聚焦产物和 Mermaid `quadrantChart`。

后端新增 manifest 读取 helper：

- `get_stage_artifact_data_contract(workflow_id, stage_id)` 返回该 stage 的 contract。
- `format_artifact_data_contract_instruction(workflow_id, stage_id)` 把 contract 格式化为后端 structured output instruction 的约束句。

前端新增同等格式化能力：

- `workflowRegistry.ts` 扩展 stage 类型，读取 `artifactDataContract`。
- `workflows.ts` 在构建 `WORKFLOWS` 时，把 manifest 中的 contract guidance 追加到 stage `description`，使用户侧 prompt 和后端 instruction 共享同一份规则来源。

Pydantic validator 继续是最终强校验；manifest 只承担“把约束同步给模型和测试”的配置来源，不替代后端 validator。

## 非目标

- 不把所有 workflow 一次性迁移到 `artifactDataContract`。
- 不把 Pydantic schema 自动生成到 JSON Schema。
- 不改变 raw JSON streaming、typed SSE、run persistence、frontend store 或 ArtifactPane。
- 不处理视觉协议第 7 轮的 `ai4se-visual` 扩展和 Mermaid 强渲染门禁。
- 不降低任何 existing validator；模型输出不满足 schema 时仍显式失败。

## 验收标准

- `workflow_manifest.json` 的 `IDEA_BRAINSTORM/CONVERGE` 声明 `artifactDataContract`。
- 后端 structured output instruction 包含从 manifest 生成的 CONVERGE contract rules。
- 前端 `WORKFLOWS.IDEA_BRAINSTORM.stages[2].description` 包含同一份 manifest contract rules。
- 同步测试能在 manifest 缺少、后端 instruction 未消费或前端 prompt 未消费这些场景下失败。
- 现有 CONVERGE Pydantic validator、partial renderer 和 raw JSON streaming 行为不回退。
- New Agents 局部回归通过；提交前按目标模式执行全量验证或记录明确环境权限例外。
