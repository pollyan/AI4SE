# TEST_DESIGN CASES 用例统计后端化与引用门禁设计

## 目标承接检查

当前目标模式仍在消化 `docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md` 中的 P0 结构化产出失败治理。上一轮已完成 `IDEA_BRAINSTORM/DIVERGE` 与 `CONVERGE` partial 引用门禁，提交 `6fd9d5af` 已推送到 GitHub，`HEAD` 与 upstream 对齐。上一轮全量验证在默认沙箱中因端口绑定和 Playwright Mach port 权限失败；非沙箱重跑 `./scripts/test/test-local.sh all` 通过。

本轮承接 todo 中“第 6 轮 TEST_DESIGN CASES / STRATEGY 统计与覆盖治理”的首个纵切。当前 `TEST_DESIGN/STRATEGY` 已经由后端计算 RPN，因此本轮选择更直接的 `TEST_DESIGN/CASES`：用例统计仍要求模型输出，`coverage_trace.covered_cases` 的 final validator 已能拒绝未知用例，但 partial renderer 会在最终失败前预览未知引用章节。

工作区存在大量与本轮无关的脏文件和删除项。本轮允许写入范围仅限：

- `tools/new-agents/backend/artifact_data_renderers.py`
- `tools/new-agents/backend/agent_runtime.py`
- `tools/new-agents/backend/tests/test_artifact_data_renderers.py`
- `tools/new-agents/backend/tests/test_agent_runtime.py`
- `tools/new-agents/frontend/src/core/prompts/test_design/cases.ts`
- 本 spec、对应 implementation plan、结构化失败治理 todo

本轮不触碰 Lisa 专属 UI、测试资产编辑 API、共享 SSE/API 路径、前端 store、ArtifactPane 渲染管线或工作流 runtime。子智能体暂不分发：改动集中在同一组 backend schema / renderer / prompt / tests，大文件冲突概率高，主 Agent 内联推进更可控。

## 当前问题

`CasesArtifactData` 当前要求模型输出：

```json
"case_statistics": {"total": 2, "p0_count": 1, "p1_count": 1, "p2_count": 0}
```

同时后端 validator 又要求这些值必须和 `case_groups[].cases[].priority` 重新计算结果一致。这会把一个完全可计算的派生字段交给模型维护，形成典型结构化失败来源。当前 prompt 也写着“case_statistics 必须与 case_groups 一致”，但这只是把一致性负担转移给模型。

partial renderer 还有一个相邻问题：`coverage_trace.covered_cases` 只做字段形状校验，不会在 partial 阶段校验它是否引用了已存在的 `case_id`。因此如果模型输出未知 `TC-404`，右侧会先预览“测试点覆盖追溯”章节，最终 strict validation 才失败。这和上一轮 IDEA partial 引用门禁的原则不一致。

## 用户故事

作为使用 Lisa 测试设计工作流的人，当我进入“用例编写”阶段时，系统应根据已生成的用例清单自动计算用例总数和 P0/P1/P2 分布，并且只有在覆盖追溯引用的用例真实存在时才预览覆盖章节。这样我不需要让模型维护重复统计，右侧流式产物也不会先展示最终 validator 会拒绝的覆盖关系。

## 设计方案

### 1. 用例统计由后端派生

新增私有 helper：

- `_flatten_cases(case_groups: list[CaseGroup]) -> list[TestCaseItem]`
- `_derive_case_statistics(case_groups: list[CaseGroup]) -> CaseStatistics`
- `_validate_case_statistics_matches(case_statistics: CaseStatistics, case_groups: list[CaseGroup]) -> None`

`CasesArtifactData.case_statistics` 调整为可选输入：

- 缺省时，`model_validator(mode="after")` 根据 `case_groups` 写回派生的 `CaseStatistics`。
- 如果模型仍然输出了 `case_statistics`，必须和派生结果完全一致；错误值继续触发 `ValidationError`，不能静默覆盖。
- `render_test_design_cases_markdown()` 保持正式文档结构不变，仍输出 `## 1. 用例统计`，但使用后端派生后的 `data.case_statistics`。
- `AgentTurnOutput.artifact_data` 中继续包含最终计算后的 `case_statistics`，方便 run snapshot、导出和后续消费读取确定性结果。

### 2. partial renderer 等待可信统计输入

partial 渲染不再要求 `case_statistics` 作为第一段输入。它以 `design_bases + case_groups` 作为首个可信预览单元：

- 只有 `document_info`、`design_bases` 和 `case_groups` 都通过局部校验后，才输出第一帧 partial。
- 第一帧包含 `# 测试用例集`、后端派生的 `## 1. 用例统计`、`## 2. 用例设计依据` 和 `## 3. 按维度分组的用例清单`。
- 如果只有 `design_bases` 而没有 `case_groups`，返回 `None`，避免展示无法计算统计的半成品。
- 后续 `test_data_environments`、`automation_candidates`、`coverage_trace`、`open_questions`、`stage_gate` 继续按章节增量追加。

这个设计会让 CASES 第一帧 partial 比旧实现晚一点出现，但避免了模型先输出错误统计时右侧展示不可信内容。

### 3. case_id 引用门禁

新增 helper：

- `_collect_case_ids(case_groups: list[CaseGroup]) -> set[str]`
- `_validate_unique_case_ids(case_groups: list[CaseGroup]) -> None`
- `_validate_automation_candidate_case_references(automation_candidates: list[AutomationCandidate], case_ids: set[str]) -> None`
- `_validate_coverage_trace_case_references(coverage_trace: list[CoverageTraceItem], case_ids: set[str]) -> None`

final validator 继续拒绝重复 `case_id` 和未知 `coverage_trace.covered_cases`。本轮额外把 `automation_candidates.case_id` 也纳入同一 case_id 引用门禁，因为它同样是明确的用例 ID 引用。

partial renderer 在渲染对应章节前复用这些 helper：

- `automation_candidates.case_id` 引用未知用例时，停在上一段可信章节，不预览自动化候选。
- `coverage_trace.covered_cases` 引用未知用例时，停在上一段可信章节，不预览覆盖追溯。
- 最终 strict validation 仍显式失败，不生成成功 artifact，不推进 stage。

### 4. Prompt 与模板同步

`CASES_ARTIFACT_DATA_STRUCTURED_OUTPUT_INSTRUCTION` 删除 `case_statistics` 输入要求，并明确：

- 模型只输出 `design_bases`、`case_groups`、环境、自动化候选、覆盖追溯、开放问题和阶段门禁。
- 用例总数和 P0/P1/P2 分布由后端根据 `case_groups` 计算。
- `coverage_trace.covered_cases` 和 `automation_candidates.case_id` 只能引用已存在的 `case_groups[].cases[].case_id`。

前端 `CASES_PROMPT` 补一句同向约束，避免系统提示一边要求结构化契约、一边暗示模型手写统计。`CASES_TEMPLATE` 保持最终文档模板不变，因为右侧正式 artifact 仍包含“用例统计”章节。

## 非目标

- 不做跨阶段 `STRATEGY.test_points` 到 `CASES.test_point` 的强 ID 校验。当前 `CASES.test_point` 是自由文本，不是结构化 `point_id`；强校验需要先改上游数据形态。
- 不改 Lisa 测试资产解析、测试资产编辑 API 或前端 Header 测试资产面板。
- 不移除最终 artifact 的“用例统计”章节。
- 不把错误统计静默修正为成功；只有缺省统计可由后端派生，显式错误统计仍失败。
- 不引入 workflow 专属 runtime、SSE endpoint、store 或渲染管线。

## 验收标准

- 缺少 `case_statistics` 的 `CasesArtifactData` 可以通过校验，并生成正确的 `total`、`p0_count`、`p1_count`、`p2_count`。
- 显式错误的 `case_statistics` 仍触发 `ValidationError`。
- `automation_candidates.case_id` 或 `coverage_trace.covered_cases` 引用未知 `case_id` 时，final validation 显式失败。
- CASES partial 在只有 `design_bases` 时不输出 artifact；在 `design_bases + case_groups` 到齐后输出后端派生统计和用例清单。
- CASES partial 不预览包含未知用例引用的自动化候选或覆盖追溯章节。
- `build_structured_output_instruction("TEST_DESIGN", "CASES")` 不再要求模型输出 `case_statistics`，但仍要求输出 `case_groups` 和 `coverage_trace`。
- raw JSON streaming 测试证明 CASES 在 `case_groups` 到齐后产生正式 partial delta，最终 `agent_turn` 仍通过完整 workflow contract，并包含 `traceability-matrix`。
- 本轮不破坏 `TEST_DESIGN/STRATEGY`、`DELIVERY`、Alex 工作流或共享 Agent Runtime。

## 验证计划

聚焦 RED / GREEN：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_cases_artifact_data_derives_statistics_when_missing tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_cases_artifact_data_rejects_unknown_automation_candidate_case_reference tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_cases_artifact_data_derives_statistics_from_case_groups tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_cases_artifact_data_skips_automation_candidates_with_unknown_case_reference tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_cases_artifact_data_skips_coverage_trace_with_unknown_case_reference tools/new-agents/backend/tests/test_agent_runtime.py::test_cases_structured_output_instruction_omits_derived_statistics tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_cases_after_case_groups_without_model_statistics -q
```

聚焦回归：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_cases_artifact_data_rejects_inconsistent_statistics tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_cases_artifact_data_rejects_unknown_coverage_case_reference tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_cases_artifact_data_is_contract_valid_and_asset_parseable tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_cases_artifact_data_builds_formal_incremental_markdown_and_patch tools/new-agents/backend/tests/test_agent_runtime.py::test_parse_agent_turn_output_text_renders_cases_artifact_data tools/new-agents/backend/tests/test_agent_runtime.py::test_cases_retry_prompt_requests_artifact_data_fix_not_markdown_rewrite tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_paragraph_level_cases_artifact_data -q
```

扩大回归：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_stream_services.py tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_agent_contracts.py -q
```

完成型代码用户故事提交前，按 Playbook 运行：

```bash
./scripts/test/test-local.sh new-agents
./scripts/test/test-local.sh all
```
