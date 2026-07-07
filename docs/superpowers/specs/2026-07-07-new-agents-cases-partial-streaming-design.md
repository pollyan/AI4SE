# New Agents 测试用例集真实 Partial Streaming 设计

日期：2026-07-07

关联 todo：`docs/todos/2026-07-07-new-agents-partial-artifact-streaming-vertical-slices.md`

## 背景

New Agents 的共享 `/api/agent/runs/stream` typed SSE、前端 `generateResponseStream()`、`chatService`、Zustand 和 `ArtifactPane` 已支持流式传输与逐 chunk 写入。当前 5 个在线 workflow、17 个阶段都能完成最终 `artifact_data -> Markdown` 渲染，但只有 `TEST_DESIGN/CLARIFY` 和 `TEST_DESIGN/STRATEGY` 能在完整 `artifact_data` 对象闭合前，根据已完成顶层字段生成正式 partial artifact delta。

本轮执行 todo 中声明的第 1 轮纵切：`TEST_DESIGN/CASES`。目标是在 Lisa 生成测试用例集时，让右侧《测试用例集》按正式章节逐步出现，同时保持最终 artifact contract、run persistence 和 Lisa 测试资产解析链路不变。

## Current State Gap Analysis

### 事实源快照

- 已读取：`AGENTS.md`、`docs/strategy/goal-mode-playbook.md`、`docs/strategy/goal-mode-cga-template.md`、`docs/index.md`、`docs/ARCHITECTURE.md`、`docs/api-contracts.md`、`docs/TESTING.md`、本 todo、`agent_runtime.py`、`artifact_data_renderers.py` 和相关 backend/frontend 测试。
- 当前代码事实：`render_agent_turn_from_artifact_data()` 已支持 `TEST_DESIGN/CASES` final renderer；`render_partial_agent_turn_from_artifact_data()` 只支持 `TEST_DESIGN/CLARIFY` 和 `TEST_DESIGN/STRATEGY`。
- 当前测试事实：backend 已有 `CASES` final renderer contract 与 test asset parser 回归；raw JSON streaming final-before partial delta 只覆盖 `CLARIFY/STRATEGY` 的段落级能力。
- 工作区保护：不触碰当前已有无关变更 `dist/intent-test-proxy.zip`、`tools/intent-tester/frontend/static/intent-test-proxy.zip`、`tools/intent-tester/test-results/proxy/junit.xml` 和 `docs/mockups/`。

### 候选 gap

| 候选 | 来源 | 目标态 | 当前能力 | 缺口 | 去向 |
| --- | --- | --- | --- | --- | --- |
| A. Lisa 测试用例集真实 partial streaming | todo 第 1 轮 | `TEST_DESIGN/CASES` 能在 final 前输出正式章节 delta，最终仍可解析为测试资产 | final renderer、contract、测试资产解析已存在 | partial renderer 与 raw streaming 段落级证据缺失 | 本轮 |
| B. Lisa 测试设计交付文档 partial streaming | todo 第 2 轮 | `TEST_DESIGN/DELIVERY` 交付文档章节逐步出现 | final renderer 已存在 | partial renderer 缺失 | 下一轮 |
| C. 全工作流 streaming 契约收口 | todo 第 7 轮 | 17 阶段 partial/final 边界、文档和证据归档完整 | 只有部分阶段有真实 partial 证据 | 实现事实未完成，提前文档化会失真 | 第 7 轮 |

排序结论：选择 A。它是用户明确要求的纵切路线第 1 轮，也是 Lisa 测试资产、覆盖摘要、风险矩阵等下游能力的上游输入。B 保留为第 2 轮，C 保留到全部实现轮之后。

### 切片厚度门禁

- 入口：Lisa 用户处于 `TEST_DESIGN/CASES` 阶段，通过共享 `/api/agent/runs/stream` 请求生成测试用例集。
- 动作：模型按 `artifact_data` 字段顺序流式输出结构化测试用例数据。
- 处理：后端 raw JSON streaming 提取已闭合 `artifact_data` 顶层字段，使用 shared partial renderer 渲染正式 Markdown 章节，并沿用 `artifact_patch` 的 `add_after` 增量描述。
- 可见结果：右侧 ArtifactPane 能先看到 `## 1. 用例统计`，随后看到 `## 2. 用例设计依据`、`## 3. 按维度分组的用例清单` 等正式章节。
- 状态承接：最终 `agent_turn` 仍通过完整 `TEST_DESIGN/CASES` artifact contract，持久化为当前 artifact，并继续被 `parse_lisa_test_asset_markdown()` 解析。
- 失败反馈：不输出进度页、裸 JSON、字段名或假成功；非法 partial 字段不会进入 artifact delta，最终非法 `artifact_data` 仍走现有 validation/retry/typed error。
- 证据：partial renderer 测试、raw JSON streaming final-before delta 测试、final contract/test asset parser 回归、前端 typed SSE / chat service 既有 delta 消费测试。
- 结论：通过。该切片不是单 helper 或单测试，而是一个可见 artifact streaming 闭环。

## Superpowers Brainstorming 自问自答

### Explore Project Context

`AGENTS.md` 要求 `tools/new-agents` 所有 agents 共享 runtime、transport、state 和 UI infrastructure，差异通过 workflow/stage contract 和 renderer 配置表达。`docs/api-contracts.md` 要求 `artifact_update.replace.markdown` 只能承载正式产物或经过正式 renderer 生成的局部正式产物。`docs/TESTING.md` 明确 raw JSON streaming 的 partial `artifact_data` 不能合成进度页，只有已闭合、已通过子模型校验的局部正式章节才能进入右侧 artifact。

当前需求已被 todo 拆成 7 个纵切轮次，本轮只覆盖 `TEST_DESIGN/CASES`，范围足够形成一个用户可感知闭环，不需要继续拆分。

### Visual Companion Decision

本轮不涉及视觉版式、交互布局或新的页面控件。ArtifactPane 已存在，前端只消费 typed SSE delta；设计问题是后端 partial renderer 与测试证据，不需要浏览器 visual companion。

### Clarifying Questions

- 用户是谁？Lisa 测试设计工作流使用者，尤其是需要生成测试用例集并实体化测试资产的测试负责人。
- 用户要完成什么？在 CASES 阶段生成《测试用例集》，并在模型输出过程中实时看到正式章节逐步成形。
- 成功状态是什么？final `agent_turn` 前至少出现多个正式 `agent_delta.output.artifact_update.replace.markdown`，章节递增；final artifact 仍通过 contract 并可解析为测试资产。
- 输入来源是什么？DeepSeek/raw JSON streaming 的 `artifact_data` 顶层字段，字段顺序沿用现有 CASES schema 和 final renderer 顺序。
- 约束是什么？不新增 workflow 专属 runtime、API path、store、ArtifactPane 或 bespoke rendering pipeline；不使用 synthetic reveal 或假进度。
- 失败路径是什么？partial 字段不完整或子模型校验失败时，不生成该字段对应的 artifact delta；最终 JSON 校验失败时走现有 retry 或 typed error。
- 下游承接是什么？`parse_lisa_test_asset_markdown()` 仍能从最终《测试用例集》中解析 `testCases`、`coverageTrace`、`coverageSummary` 和 `riskMatrix`。
- 不做什么？不实现 `TEST_DESIGN/DELIVERY`，不修改前端渲染管线，不引入真实模型网络 smoke 作为本轮硬依赖。

### Approaches

1. 推荐：在现有 `render_partial_agent_turn_from_artifact_data()` registry 中增加 `TEST_DESIGN/CASES` 分支，复用 final renderer 的章节 helper，按已闭合字段逐段渲染正式 Markdown。优点是改动小、复用 shared runtime 和 artifact patch；风险是 CASES 字段之间存在统计/覆盖引用关系，需要测试保证 final contract 不退化。
2. 不选：在 runtime 中为 CASES 写专用 streaming parser。它会违反共享 runtime 约束，并把 stage 差异变成基础设施分支。
3. 不选：前端根据最终 Markdown 做 synthetic reveal。它不能证明模型输出过程中已有正式字段闭合，也不满足“真实 partial artifact streaming”目标。

### Presented Design

Architecture：继续使用 shared raw JSON streaming。`build_partial_agent_delta()` 已能提取已闭合 `artifact_data` 顶层字段，本轮只扩展 partial renderer registry 和 CASES partial renderer。

Components：`artifact_data_renderers.py` 新增 `render_partial_test_design_cases_markdown(data: Any) -> str | None`，复用 `CaseStatistics`、`DesignBasis`、`CaseGroup`、`TestDataEnvironment`、`AutomationCandidate`、`CoverageTraceItem`、`OpenQuestion`、`StageGateCheck` 和既有 `_render_*` helpers。

Data Flow：模型输出 `document_info` 后不会生成 artifact；输出 `case_statistics` 后生成 H1 + 第 1 节；后续每完成一个 CASES 顶层字段，renderer 追加对应正式章节。`_build_partial_add_after_patch()` 继续生成 `add_after` patch，前端可用现有逻辑消费。

Error Handling：partial renderer 只接受 dict、合法 `document_info` 和合法子模型。当前字段非法时返回上一段可渲染结果或 `None`，不输出调试占位。完整 JSON 到达后仍由 `CasesArtifactData` 和 `validate_agent_turn()` 承担完整一致性校验。

Testing：先写 backend failing tests，再实现。验证包括 partial renderer、runtime raw JSON streaming 多个 final-before delta、final renderer contract/test asset parser，以及现有 frontend typed SSE delta 消费测试。

## 用户故事

作为 Lisa 测试设计工作流使用者，当我在 `TEST_DESIGN/CASES` 阶段生成测试用例集时，我可以在右侧 ArtifactPane 看到用例统计、设计依据、用例清单、测试数据、自动化候选、覆盖追溯等正式章节随模型结构化字段逐步出现，从而更早检查测试资产质量，同时最终用例集仍可保存、恢复和实体化为 Lisa 测试资产。

## 范围

纳入本轮：

- `TEST_DESIGN/CASES` partial artifact renderer。
- CASES field order 到 partial renderer registry。
- raw JSON streaming final-before delta 回归。
- final renderer contract 与测试资产解析回归。
- 现有前端 SSE / chat service delta 消费验证。
- 更新本 todo 第 1 轮状态、spec / plan 链接和验证证据。

不纳入本轮：

- `TEST_DESIGN/DELIVERY` 或其它 workflow/stage。
- 新 API、store、runtime 分支或 ArtifactPane 渲染管线。
- 持久化原始 `artifact_data`。
- 逐 token 打字机、固定延迟、进度条或 synthetic reveal。
- 真实模型 smoke 的硬性执行；如本地没有默认模型配置，仅记录未运行原因。

## 验收条件

1. Given `TEST_DESIGN/CASES` raw JSON streaming 已输出 `document_info` 和 `case_statistics`
   When 后端构建 partial delta
   Then delta artifact markdown 包含 `# 测试用例集` 和 `## 1. 用例统计`，不包含 `## 2. 用例设计依据`。

2. Given streaming 继续输出 `design_bases`
   When 后端再次构建 partial delta
   Then delta artifact markdown 追加 `## 2. 用例设计依据`，并提供 `add_after` artifact patch 指向 `## 1. 用例统计`。

3. Given streaming 最终输出完整合法 `artifact_data`
   When runtime 结束本轮
   Then final `AgentTurnOutput` 包含完整《测试用例集》和 `traceability-matrix`，并通过 `validate_agent_turn()`。

4. Given final CASES artifact markdown
   When 调用 `parse_lisa_test_asset_markdown()`
   Then 能解析出 `TC-001`、`TC-002`、覆盖摘要和风险矩阵。

5. Given 前端收到 typed `agent_delta` artifact update
   When `generateResponseStream()` 和 `chatService` 消费该事件
   Then `artifactContent` 会随 delta 更新，不等待 final `agent_turn` 才一次性写入。

## 验证计划

- Backend focused RED/GREEN：
  - `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_partial_cases_artifact_data_builds_formal_incremental_markdown_and_patch -q`
  - `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_paragraph_level_cases_artifact_data -q`
- Backend regression：
  - `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_stream_services.py tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_test_assets.py -q`
- Frontend regression：
  - `cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/llm.test.ts src/services/__tests__/chatService.test.ts src/components/__tests__/ArtifactPane.incrementalRender.test.tsx`
- Pre-commit goal-mode verification：
  - `git diff --check`
  - `./scripts/test/test-local.sh all`，除非环境权限或耗时阻塞，并在收尾说明中记录风险。

## 风险

- CASES 的 `case_statistics` 与 `case_groups` 存在跨字段一致性；partial 阶段只对已闭合子模型做局部校验，完整一致性仍由 final `CasesArtifactData` 保证。
- `coverage_trace` 会渲染 `ai4se-visual` traceability-matrix；partial renderer 必须复用现有 helper，避免引入与 final renderer 不一致的可视化格式。
- 如果本地没有真实模型配置，本轮只能用确定性 mock streaming 证明后端/前端链路，真实模型 smoke 留作有凭证环境下的补充证据。
