# New Agents 第 5 轮 IDEA_BRAINSTORM partial artifact streaming 实施计划

## 范围

本轮覆盖 `IDEA_BRAINSTORM/DEFINE`、`IDEA_BRAINSTORM/DIVERGE`、`IDEA_BRAINSTORM/CONVERGE`、`IDEA_BRAINSTORM/CONCEPT`。目标是在 raw JSON streaming 期间，后端基于已闭合顶层 `artifact_data` 字段生成正式 partial artifact delta；最终 artifact 仍通过完整 contract、Mermaid 和 `ai4se-visual` 校验。

允许写入：

- `docs/superpowers/specs/2026-07-07-new-agents-idea-brainstorm-partial-streaming-design.md`
- `docs/superpowers/plans/2026-07-07-new-agents-idea-brainstorm-partial-streaming.md`
- `docs/todos/2026-07-07-new-agents-partial-artifact-streaming-vertical-slices.md`
- `tools/new-agents/backend/artifact_data_renderers.py`
- `tools/new-agents/backend/tests/test_artifact_data_renderers.py`
- `tools/new-agents/backend/tests/test_agent_runtime.py`

不写入 frontend runtime/store/UI、workflow 专属 API、shared transport 或无关脏文件。前端只运行现有通用回归验证。

## 子智能体策略

- 已派发只读 explorer 复核 IDEA contract、final renderer/helper、runtime tests 和拆分风险。
- 已派发只读 explorer 复核 Lisa judge 质量门、前端通用消费链路和第 5 轮记录风险。
- 不派发 worker：实现集中编辑同一 backend renderer 与 tests，多个 worker 会产生写入冲突。
- 子智能体结果返回后，由主 Agent 纳入设计或收尾记录；完成证明仍以主 Agent 本地 diff 和验证命令为准。

## TDD 步骤

### 1. RED：partial renderer tests

在 `tools/new-agents/backend/tests/test_artifact_data_renderers.py` 新增四个失败测试：

- `test_render_partial_idea_define_artifact_data_builds_formal_incremental_markdown_and_patch`
- `test_render_partial_idea_diverge_artifact_data_builds_formal_incremental_markdown_and_patch`
- `test_render_partial_idea_converge_artifact_data_builds_formal_incremental_markdown_and_patch`
- `test_render_partial_idea_concept_artifact_data_builds_formal_incremental_markdown_and_patch`

测试要求：

- partial Markdown 必须包含阶段正式 H1/H2，不包含进度页或裸 JSON。
- DEFINE 和 CONCEPT 的单 section 增量应生成 `artifact_patch.add_after`。
- DIVERGE 首个可视化增量需要 `idea_landscape + idea_cards`，可一次加入多个 section，允许 patch 为空。
- CONVERGE 首个可视化增量需要 `decision_matrix + ice_evaluations`，后续单 section 增量应生成 patch。
- 必须断言 `mindmap`、`quadrantChart` 或 `mvp-map` 在相应阶段出现。

先运行这四个测试，预期失败原因是 IDEA partial dispatch 返回 `None`。

### 2. GREEN：实现 IDEA partial renderer 与 dispatch

在 `tools/new-agents/backend/artifact_data_renderers.py` 中：

- 为四个 IDEA stage 增加 `render_partial_idea_brainstorm_*_markdown()`。
- 复用现有 final renderer helper 和 `Idea*` Pydantic 子模型。
- 只在最小可校验字段闭合后返回 Markdown；无效或不完整字段返回 `None`。
- 在 `render_partial_agent_turn_from_artifact_data()` 中增加四个 IDEA dispatch 分支和 field order。
- 保持 `artifact_update.type="replace"`、`artifact_patch`、`stage_action`、`warnings` 的共享返回结构。

运行 renderer tests，确认四个测试通过。

### 3. RED/GREEN：runtime raw JSON streaming tests

改造 `tools/new-agents/backend/tests/test_agent_runtime.py` 中四个 IDEA raw JSON streaming 测试：

- 把单次完整 JSON chunk 拆成多个 prefix chunk。
- 断言 final `agent_turn` 前存在多个 `agent_delta.output.artifact_update.replace.markdown`。
- 断言 artifact Markdown 随字段闭合递增出现阶段章节。
- 断言 final output 仍通过完整 stage contract。

推荐 chunk 点：

- DEFINE：`problem_statement`、`target_users`、`problem_landscape`。
- DIVERGE：`divergence_method`、`idea_cards`、`idea_sources`。
- CONVERGE：`ice_evaluations`、`resource_constraints`、`validation_experiments`。
- CONCEPT：`positioning_statement`、`core_assumptions`、`mvp_features`。

先运行 IDEA runtime tests，确认改造后在未实现或实现不完整时会失败；实现后确认通过。

### 4. 聚焦回归

运行：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_idea_define_artifact_data_builds_formal_incremental_markdown_and_patch tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_idea_diverge_artifact_data_builds_formal_incremental_markdown_and_patch tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_idea_converge_artifact_data_builds_formal_incremental_markdown_and_patch tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_idea_concept_artifact_data_builds_formal_incremental_markdown_and_patch -q
```

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_idea_define_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_idea_diverge_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_idea_converge_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_idea_concept_artifact_data_before_final_output -q
```

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_paragraph_level_clarify_artifact_data tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_paragraph_level_strategy_artifact_data tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_paragraph_level_cases_artifact_data tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_delivery_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_req_review_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_req_review_report_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_incident_timeline_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_incident_root_cause_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_incident_improvement_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_idea_define_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_idea_diverge_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_idea_converge_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_idea_concept_artifact_data_before_final_output -q
```

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_stream_services.py tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_agent_contracts.py -q
```

```bash
cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/llm.test.ts src/services/__tests__/chatService.test.ts src/components/__tests__/ArtifactPane.incrementalRender.test.tsx
```

### 5. 记录与全量验证

更新 `docs/todos/2026-07-07-new-agents-partial-artifact-streaming-vertical-slices.md`：

- 状态改为第 1-5 轮已完成确定性验证，第 6-7 轮后续执行。
- 当前事实快照加入四个 IDEA stages。
- 新增第 5 轮执行记录、聚焦验证、全量验证、LLM judge 说明、残余风险和下一轮候选。

文档和代码落定后运行：

```bash
git diff --check -- docs/todos/2026-07-07-new-agents-partial-artifact-streaming-vertical-slices.md docs/superpowers/specs/2026-07-07-new-agents-idea-brainstorm-partial-streaming-design.md docs/superpowers/plans/2026-07-07-new-agents-idea-brainstorm-partial-streaming.md tools/new-agents/backend/artifact_data_renderers.py tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py
```

```bash
rg -n "T[B]D|implement[ ]later|<填[入]|待[补]" docs/todos/2026-07-07-new-agents-partial-artifact-streaming-vertical-slices.md docs/superpowers/specs/2026-07-07-new-agents-idea-brainstorm-partial-streaming-design.md docs/superpowers/plans/2026-07-07-new-agents-idea-brainstorm-partial-streaming.md
```

```bash
NEW_AGENTS_E2E_LLM_JUDGE=0 ./scripts/test/test-local.sh all
```

本轮未新增 IDEA 专属 LLM judge；如果后续开启或引用 judge，按 playbook 默认通过线 `score >= 80` 执行。
