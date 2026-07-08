# New Agents CASES ArtifactDataContract Sync Design

## 目标承接检查

事实源快照：

- 已读取：`AGENTS.md`、`docs/index.md`、`docs/strategy/goal-mode-playbook.md`、`docs/strategy/goal-mode-cga-template.md`、`docs/strategy/goal-mode-ci-verification.md`、`docs/TESTING.md`、`docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md`、`docs/superpowers/specs/2026-07-08-new-agents-artifact-data-source-matrix-design.md`、`tools/new-agents/workflow_manifest.json`、`tools/new-agents/backend/workflow_manifest.py`、`tools/new-agents/backend/agent_runtime.py`、`tools/new-agents/backend/tests/test_agent_runtime.py`、`tools/new-agents/backend/tests/test_workflow_contract_sync.py`、`tools/new-agents/frontend/src/core/workflows.ts`、`tools/new-agents/frontend/src/core/config/__tests__/workflows.test.ts`。
- 当前工作区：`git status -sb` 干净，`HEAD` 与 `origin/codex/structured-failure-diagnostics` 同步。

已确认目标来源：

- 来源：`docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md` 中“建立 schema / prompt / contract 单源同步机制”和第 8B 残余风险“20 个阶段尚未迁移 `artifactDataContract` 到 manifest”。
- 本轮承接：第 8C 轮 `TEST_DESIGN/CASES` 的 `artifactDataContract` manifest 同步纵切。
- 上一轮状态：第 8B 字段来源与视觉协议矩阵已完成，提交 `97aa4c35` 已推送。

改道条件检查：

- 新 P0/P1 或用户新目标：无。
- 未关闭质量门：无。第 8B 是纯文档切片，文档检查已通过；第 8A 的非沙箱全量验证通过。
- LLM judge：本轮不启用或引用真实模型 / judge 分数。
- 架构冲突：无。本轮继续使用共享 `workflow_manifest.json`、共享 `format_artifact_data_contract_instruction()`、共享前端 `formatArtifactDataContractPrompt()`；不新增 Lisa 专属 runtime、API、store 或渲染管线。
- 工作区冲突：无未提交变更。
- 子智能体 / 旁路审查决策：已派发只读 explorer `019f4150-6310-7663-93f1-786b9a65e9c8`，范围为 CONVERGE 现有同步模式和 CASES 最小迁移清单；主 Agent 并行推进设计，待返回后校准 plan。

结论：继续承接第 8 轮，不升级为完整 CGA。

## Brainstorming 自问自答

### Explore Project Context

当前只有 `IDEA_BRAINSTORM/CONVERGE` 通过 `workflow_manifest.json` 的 `artifactDataContract` 驱动 backend structured output instruction 和 frontend prompt description。`TEST_DESIGN/CASES` 已在代码中具备清晰的结构化治理成果：`case_statistics` 可由后端根据 `case_groups` 派生，显式错误统计会失败，`case_groups[].cases[].case_id` 必须唯一，`automation_candidates.case_id` 和 `coverage_trace.covered_cases` 必须引用已存在 case id。问题是这些关键约束仍写在 `agent_runtime.py` 的 CASES 硬编码 instruction 和前端 prompt 文案里，没有进入 manifest 单源同步；同时 CASES 前端 prompt 仍有要求模型手写 Markdown 表格和 `ai4se-visual` fenced block 的旧描述，和后端确定性渲染边界冲突。

本轮适合做 CASES 而不是一次迁移 20 个阶段，因为 CASES 是高失败阶段之一，也是 Lisa 测试资产下游消费入口；其关键约束数量适中，已有 renderer/runtime/test_asset 回归证据，能形成可独立验证的 contract sync 纵切。

### Visual Companion Decision

本轮不涉及 UI 视觉设计，只涉及 prompt / manifest / backend instruction 同步，不需要视觉伴随工具。

### Clarifying Questions

1. 用户是谁？
   - 后续维护 Lisa TEST_DESIGN/CASES workflow 的工程师和目标模式 Agent。
2. 用户要完成什么动作？
   - 当 CASES 的 `artifact_data` 关键约束变化时，只改 manifest，就能同步影响 backend instruction 和 frontend prompt description，并由测试证明不漂移。
3. 成功状态是什么？
   - `workflow_manifest.json` 的 `TEST_DESIGN/CASES` stage 有 `artifactDataContract`；backend `build_structured_output_instruction("TEST_DESIGN", "CASES")` 包含 manifest formatter 输出；frontend `WORKFLOWS.TEST_DESIGN.stages[CASES].description` 包含同一 contract guidance；原有“不输出 case_statistics”等行为继续成立。
4. 失败路径是什么？
   - 若 manifest 缺字段或字段为空，现有 formatter 会显式 ValueError；若 backend instruction 或 frontend prompt 未消费 manifest，新增测试失败。
5. 不做什么？
   - 不改 CASES Pydantic schema、renderer、test asset parser、SSE runtime 或前端 store；不迁移 DELIVERY / STRATEGY / VALUE 等其他阶段；不改变模型输出 JSON 示例的字段顺序。

### Approaches

推荐方案：迁移 CASES 的关键约束到 manifest，并让 backend hardcoded instruction 使用 `format_artifact_data_contract_instruction("TEST_DESIGN", "CASES")`。

- 优点：延续 CONVERGE 模式；改动小；能用 backend + frontend tests 证明单源同步；降低 CASES prompt 漂移风险。
- 缺点：仍保留 CASES JSON schema 示例在 `agent_runtime.py` 中，未彻底生成化整个 instruction。

备选方案 A：一次迁移 TEST_DESIGN 全部阶段。

- 优点：TEST_DESIGN 内部一致性更强。
- 缺点：触碰 STRATEGY / DELIVERY / CLARIFY 多个阶段，回归面大，且 STRATEGY 已有 RPN / ID 引用治理，可以独立成后续切片。

备选方案 B：只在文档中记录 CASES 仍未迁移。

- 优点：无代码风险。
- 缺点：不能推进单源同步机制，也不能消化当前 P0 待办。

## 设计

### Architecture

沿用 CONVERGE 的共享机制：

- `workflow_manifest.json`：在 `TEST_DESIGN/CASES` stage 增加 `artifactDataContract`，包含 `modelOutputRules`、`forbiddenOutputs`、`rendererOutputs`。
- `agent_runtime.py`：把 CASES instruction 底部硬编码 contract 文案替换为 `__ARTIFACT_DATA_CONTRACT_INSTRUCTION__` placeholder，并调用 `format_artifact_data_contract_instruction("TEST_DESIGN", "CASES")`。
- `test_workflow_contract_sync.py`：新增 CASES manifest contract 驱动 backend instruction 的测试。
- `test_agent_runtime.py`：保留并扩展 `test_cases_structured_output_instruction_omits_derived_statistics()`，证明 formatter 输出仍在 instruction 中，且不要求模型输出 `case_statistics`。
- `frontend/src/core/prompts/test_design/cases.ts`：清理要求模型手写 Markdown 表格和 `ai4se-visual` fenced block 的旧描述，改为要求提供结构化覆盖关系。
- `frontend/src/core/config/__tests__/workflows.test.ts`：新增 CASES prompt description 的 manifest contract guidance 断言，并防止 prompt 再次要求模型手写 renderer-owned 视觉产物。

### Contract Content

CASES 的 `artifactDataContract` 应包含：

- `modelOutputRules`
  - `case_statistics` 由后端根据 `case_groups` 计算，模型不要输出。
  - `case_groups[].cases[].case_id` 必须唯一。
  - `automation_candidates.case_id` 只能引用 `case_groups[].cases[].case_id` 中已存在的 case id。
  - `coverage_trace.covered_cases` 只能引用 `case_groups[].cases[].case_id` 中已存在的 case id。
  - `stage_gate` 至少包含一个 `checked=true`。
- `forbiddenOutputs`
  - 完整 Markdown 文档
  - Markdown 表格
  - Mermaid 代码块
  - traceability-matrix JSON 代码块
- `rendererOutputs`
  - 右侧测试用例集
  - `ai4se-visual traceability-matrix`

### Error Handling

本轮不改变 runtime error behavior。若模型输出错误统计或未知 case id，仍由 `CasesArtifactData` Pydantic validation 触发 `SCHEMA_VALIDATION_FAILED`。若 manifest contract 配置无效，`format_artifact_data_contract_instruction()` 继续显式 ValueError。

### Testing

按 TDD 执行：

1. RED backend：
   - 新增 `test_cases_artifact_data_contract_manifest_drives_backend_instruction()`，预期当前 `get_stage_artifact_data_contract("TEST_DESIGN", "CASES") is None` 或 instruction 不含 formatter 输出而失败。
   - 扩展 / 新增 CASES instruction 测试，断言 instruction 包含 `case_statistics 由后端根据 case_groups 计算`、`automation_candidates.case_id`、`coverage_trace.covered_cases`、`traceability-matrix JSON 代码块`。
2. RED frontend：
   - 新增 `appends manifest artifact data contract guidance to TEST DESIGN CASES prompt description`，预期当前 `description` 不含 `【artifact_data 契约同步约束】`。
   - 新增 `does not ask TEST DESIGN CASES to handwrite renderer-owned visuals`，预期当前 `description` 仍包含要求模型手写 Markdown 表格和 `ai4se-visual` fenced block 的旧描述而失败。
3. GREEN：
   - 修改 manifest 和 CASES instruction placeholder。
   - 清理 CASES frontend prompt 中和 renderer-owned 产物冲突的旧描述。
4. 聚焦验证：
   - `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py::test_cases_artifact_data_contract_manifest_drives_backend_instruction tools/new-agents/backend/tests/test_agent_runtime.py::test_cases_structured_output_instruction_omits_derived_statistics -q`
   - `cd tools/new-agents/frontend && npm run test -- src/core/config/__tests__/workflows.test.ts -t "TEST DESIGN CASES"`
5. 扩展验证：
   - `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_agent_runtime.py::test_cases_structured_output_instruction_omits_derived_statistics tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_cases_artifact_data_derives_statistics_when_missing tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_cases_artifact_data_rejects_inconsistent_statistics tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_cases_artifact_data_rejects_unknown_automation_candidate_case_reference tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_cases_artifact_data_rejects_unknown_coverage_case_reference -q`
   - `cd tools/new-agents/frontend && npm run test -- src/core/config/__tests__/workflows.test.ts`
   - `./scripts/test/test-local.sh new-agents`
   - 本轮是代码 + manifest + frontend prompt test 变更，提交前按目标模式运行 `./scripts/test/test-local.sh all`；若默认沙箱阻塞端口 / Chromium，则非沙箱重跑并记录。

## Scope Review

本轮是工程信任闭环。完成后，维护者现在可以通过 `workflow_manifest.json` 单源维护 TEST_DESIGN/CASES 的核心 `artifact_data` 约束，并由 backend 和 frontend 同步测试保证 prompt / instruction 不漂移。它不让用户看到新 UI，但会降低 CASES 作为 Lisa 测试资产入口的结构化失败风险，并为后续迁移其他阶段提供第二个可复用样本。
