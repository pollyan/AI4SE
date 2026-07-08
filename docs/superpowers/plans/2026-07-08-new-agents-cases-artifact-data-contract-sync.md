# New Agents CASES ArtifactDataContract Sync Plan

## Goal

完成第 8C 轮 `TEST_DESIGN/CASES` 的 `artifactDataContract` manifest 同步纵切，使 CASES 的核心 `artifact_data` 约束由 `workflow_manifest.json` 单源声明，并同步驱动 backend structured output instruction 与 frontend stage prompt description。

## Scope

- In scope:
  - `workflow_manifest.json` 增加 `TEST_DESIGN/CASES.artifactDataContract`。
  - `agent_runtime.py` 的 CASES structured output instruction 改为复用 `format_artifact_data_contract_instruction("TEST_DESIGN", "CASES")`。
  - `frontend/src/core/prompts/test_design/cases.ts` 清理要求模型手写 Markdown 表格和 `ai4se-visual` fenced block 的旧描述。
  - Backend / frontend 增加 contract sync 回归测试。
  - 更新结构化失败治理 todo 的第 8C 执行记录。
- Out of scope:
  - 不改 CASES Pydantic schema、renderer、SSE runtime、store 或前端 ArtifactPane。
  - 不迁移其他 20 个 stage 的 `artifactDataContract`。
  - 不改变 Lisa / Alex 的共享 runtime 架构。

## Steps

1. RED: 增加 CASES backend manifest contract sync 测试。
   - 文件：`tools/new-agents/backend/tests/test_workflow_contract_sync.py`
   - 断言 `get_stage_artifact_data_contract("TEST_DESIGN", "CASES")` 存在，且 `build_structured_output_instruction("TEST_DESIGN", "CASES")` 包含 formatter 输出和每条 manifest rule。
   - 预期当前失败，因为 CASES 尚无 `artifactDataContract`。

2. RED: 增加 CASES runtime instruction 来源测试。
   - 文件：`tools/new-agents/backend/tests/test_agent_runtime.py`
   - 断言 CASES instruction 包含 manifest formatter 输出，且仍不要求模型输出 `"case_statistics"` 字段。

3. RED: 增加 CASES frontend prompt sync 测试。
   - 文件：`tools/new-agents/frontend/src/core/config/__tests__/workflows.test.ts`
   - 断言 `WORKFLOWS.TEST_DESIGN` 的 `CASES` description 包含 `【artifact_data 契约同步约束】` 和 CASES 关键规则。
   - 断言 CASES description 不再要求模型手写 Markdown 表格和 `ai4se-visual` fenced block。

4. GREEN: 实现 manifest 单源同步。
   - 文件：`tools/new-agents/workflow_manifest.json`
   - 增加 CASES `artifactDataContract`：
     - `case_statistics` 由后端根据 `case_groups` 计算，模型不要输出。
     - `case_groups[].cases[].case_id` 必须唯一。
     - `automation_candidates.case_id` 只能引用已存在 case id。
     - `coverage_trace.covered_cases` 只能引用已存在 case id。
     - 禁止输出完整 Markdown、Markdown 表格、Mermaid 代码块、`traceability-matrix` JSON 代码块。
     - 后端负责渲染右侧测试用例集和 `ai4se-visual traceability-matrix`。
   - 文件：`tools/new-agents/backend/agent_runtime.py`
   - 将 CASES instruction 底部硬编码 contract 文案替换为 manifest formatter placeholder。
   - 文件：`tools/new-agents/frontend/src/core/prompts/test_design/cases.ts`
   - 将旧的 renderer-owned 输出描述改成“模型只提供结构化覆盖关系，后端确定性渲染右侧 Markdown 表格和 `ai4se-visual traceability-matrix`”。

5. GREEN verification.
   - `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py::test_cases_artifact_data_contract_manifest_drives_backend_instruction tools/new-agents/backend/tests/test_agent_runtime.py::test_cases_structured_output_instruction_omits_derived_statistics tools/new-agents/backend/tests/test_agent_runtime.py::test_cases_structured_output_instruction_uses_manifest_artifact_data_contract -q`
   - `cd tools/new-agents/frontend && npm run test -- src/core/config/__tests__/workflows.test.ts -t "TEST DESIGN CASES|renderer-owned visuals"`

6. 扩展验证。
   - `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_agent_runtime.py::test_cases_structured_output_instruction_requests_artifact_data_not_markdown tools/new-agents/backend/tests/test_agent_runtime.py::test_cases_structured_output_instruction_omits_derived_statistics tools/new-agents/backend/tests/test_agent_runtime.py::test_cases_structured_output_instruction_uses_manifest_artifact_data_contract tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_cases_artifact_data_derives_statistics_when_missing tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_cases_artifact_data_rejects_inconsistent_statistics tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_cases_artifact_data_rejects_unknown_automation_candidate_case_reference tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_cases_artifact_data_rejects_unknown_coverage_case_reference -q`
   - `cd tools/new-agents/frontend && npm run test -- src/core/config/__tests__/workflows.test.ts`
   - `./scripts/test/test-local.sh new-agents`
   - `./scripts/test/test-local.sh all`

7. 收口。
   - 更新 `docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md` 的状态、进展和第 8C 执行记录。
   - 检查 `git diff --check`。
   - 独立提交并推送。
