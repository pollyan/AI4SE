# DeepSeek V4 TEST_DESIGN/CASES 结构化产物数据设计

## 背景

`TEST_DESIGN/CLARIFY` 和 `TEST_DESIGN/STRATEGY` 已经迁移为“模型输出 `artifact_data`，后端确定性渲染 Markdown/Mermaid/ai4se-visual”。当前 `TEST_DESIGN/CASES` 仍要求 DeepSeek V4 Flash 在 JSON 字符串里拼完整《测试用例集》、多段 Markdown 表格和 `ai4se-visual` traceability-matrix。该阶段不仅格式面复杂，还直接作为 Lisa 测试资产导出和实体化的来源。

本轮目标是把 CASES 阶段纳入同一结构化产物链路，同时保持共享 Agent Runtime、typed SSE、artifact contract、run/artifact persistence 和现有测试资产解析链路不变。前端仍只接收 `AgentTurnOutput.artifact_update.markdown`。

## 用户故事

作为测试负责人，当我已经完成测试策略并进入 `TEST_DESIGN/CASES` 阶段时，我希望 DeepSeek V4 只输出结构化测试用例数据，由后端稳定生成《测试用例集》和覆盖追溯矩阵，从而减少 Markdown 表格或 visual JSON 格式不完整导致的失败，并让生成后的 CASES artifact 继续可以导出 Lisa 测试资产。

## 范围

纳入本轮：

- 为 `TEST_DESIGN/CASES` 定义严格 Pydantic `artifact_data` schema。
- 后端确定性渲染完整《测试用例集》 Markdown。
- 渲染用例统计、设计依据、按维度分组的用例表、测试数据与环境、自动化候选、覆盖追溯、开放问题和阶段门禁。
- 渲染 `ai4se-visual` traceability-matrix，继续使用现有 `type/columns/rows` 结构。
- Runtime 对 `TEST_DESIGN/CASES` 使用 `artifact_data` 输出指令和数据纠错 retry。
- 增加测试证明 renderer 输出通过 artifact contract，并可被现有 Lisa 测试资产解析/导出链路消费。
- 更新 DeepSeek todo 当前进展。

不纳入本轮：

- `TEST_DESIGN/DELIVERY` 或其它 workflow 的迁移。
- 持久化原始 `artifact_data`。
- 前端 typed SSE、store、ArtifactPane、StructuredVisual 或测试资产 UI 变更。
- 新增 intent-tester 联动。
- 真实 DeepSeek V4 网络 smoke；需要显式凭证、网络和额度。

## 数据契约

`TEST_DESIGN/CASES` 的 `artifact_data` 必须包含：

- `document_info`: artifact 名称、workflow、stage、状态。
- `case_statistics`: P0/P1/P2 数量和总数。
- `design_bases`: 用例设计依据。
- `case_groups`: 按测试维度分组的用例列表，每条用例包含 ID、标题、优先级、测试维度、测试点、风险、前置条件、步骤、测试数据、预期结果、断言、执行层级、自动化建议和状态。
- `test_data_environments`: 测试数据与环境准备项。
- `automation_candidates`: 自动化候选。
- `coverage_trace`: 测试点覆盖追溯。
- `open_questions`: 开放问题。
- `stage_gate`: 阶段门禁检查项。

所有字符串必须非空；关键列表必须至少一项；未知字段必须拒绝；`case_statistics.total` 必须等于所有用例数量；`p0_count/p1_count/p2_count` 必须等于对应优先级用例数量；`coverage_trace.covered_cases` 必须引用已存在的用例 ID。

## 渲染契约

renderer 输出必须满足现有 `TEST_DESIGN/CASES` artifact contract：

- 固定 H1: `# 测试用例集`。
- 包含所有必需 H2 章节和用例表字段。
- `## 3. 按维度分组的用例清单` 下按维度输出子标题和完整用例表。
- `## 6. 测试点覆盖追溯` 同时输出 Markdown 表格和 fenced `ai4se-visual` traceability-matrix。
- 输出继续通过 `validate_agent_turn()`。
- 保存后的 Markdown 继续可被 `parse_lisa_test_asset_markdown()` 和 `export_lisa_test_assets()` 解析为测试资产。

## 失败处理

当模型输出缺字段、空数组、空白字符串、未知字段、统计不一致或覆盖追溯引用不存在的用例 ID 时：

- Pydantic schema 直接拒绝。
- raw JSON streaming 触发有限 retry。
- retry prompt 要求修正 `artifact_data` 数据，不要求模型重写 Markdown 表格或 visual JSON。
- 最终失败显式暴露，不伪造 artifact。

## 验收条件

1. Given `TEST_DESIGN/CASES` 收到合法 `artifact_data`
   When 后端解析 raw JSON
   Then 返回 contract-valid `AgentTurnOutput`，artifact 包含完整《测试用例集》和 traceability-matrix。

2. Given 合法 CASES `artifact_data`
   When renderer 生成 Markdown
   Then `parse_lisa_test_asset_markdown()` 能解析出测试用例、覆盖追溯、覆盖摘要、风险矩阵和 asset issues。

3. Given 保存了 renderer 输出的 CASES artifact
   When 调用 `export_lisa_test_assets(run_id)`
   Then 导出结果包含正确的 `testCases`、`coverageTrace`、`coverageSummary` 和 `riskMatrix`。

4. Given CASES `artifact_data` 统计或覆盖引用不一致
   When Pydantic 校验
   Then 校验失败并定位到对应数据问题。

5. Given DeepSeek raw JSON streaming 处于 `TEST_DESIGN/CASES`
   When 第一次输出不合格
   Then retry prompt 要求修正 `artifact_data`，并禁止输出 Markdown 文档、Mermaid/visual 代码块或表格。

## 验证计划

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py -q`
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_agent_contracts.py tools/new-agents/backend/tests/test_agent_endpoint.py tools/new-agents/backend/tests/test_stream_services.py tools/new-agents/backend/tests/test_test_asset_parsing.py tools/new-agents/backend/tests/test_test_assets.py -q`
- `.venv/bin/python -m py_compile tools/new-agents/backend/agent_runtime.py tools/new-agents/backend/artifact_data_renderers.py`
- `git diff --check -- <本轮文件>`

## 风险

- CASES schema 比前两个阶段更宽，过度建模会增加模型填充难度。本轮只建模现有 artifact contract 和测试资产解析需要的字段。
- 当前测试资产解析依赖 Markdown 表格列名；renderer 必须保持这些列名稳定。
- 真实 DeepSeek V4 是否稳定填充完整 CASES schema 需要后续带凭证 smoke 验证。
