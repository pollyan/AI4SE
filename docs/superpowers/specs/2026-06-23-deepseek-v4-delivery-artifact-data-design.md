# DeepSeek V4 DELIVERY 结构化产物数据设计

## 背景

DeepSeek V4 Flash 当前作为 `json_object_only` provider 使用，稳定边界应是模型输出合法 JSON，后端用 Pydantic schema、业务校验和确定性 renderer 生成最终 Markdown/visual artifact。`TEST_DESIGN/CLARIFY`、`STRATEGY`、`CASES` 已完成 `artifact_data` 迁移，但 `TEST_DESIGN/DELIVERY` 仍要求模型直接拼完整《测试设计文档》、表格和 `coverage-map`，这是 TEST_DESIGN 最终交付阶段的格式稳定性缺口。

## 用户故事

作为使用 Lisa 完成测试设计交付的用户，当我进入 `TEST_DESIGN/DELIVERY` 阶段时，我希望 DeepSeek V4 只输出结构化业务数据，由后端确定性渲染完整交付文档和覆盖地图，从而减少 Markdown 标题缺失、表格不完整、`ai4se-visual` 格式错误导致的生成失败。

## 范围

本轮纳入：

- 新增 `TEST_DESIGN/DELIVERY` 的 `artifact_data` Pydantic schema。
- 新增 deterministic renderer，输出当前 contract 要求的《测试设计文档》全部 H1/H2。
- renderer 生成 `ai4se-visual` `coverage-map`，列为 `需求`、`风险`、`测试点`、`用例`、`验收状态`。
- runtime 在 `TEST_DESIGN/DELIVERY` 阶段选择 artifact_data instruction，并在 retry prompt 中要求修正数据而非重写 Markdown。
- 后端测试覆盖合法渲染、不一致数据拒绝、runtime instruction、runtime parse 和 retry。
- 更新 DeepSeek V4 todo 的当前进展。

本轮不纳入：

- 迁移 `REQ_REVIEW`、`VALUE_DISCOVERY`、`IDEA_BRAINSTORM`、`INCIDENT_REVIEW`。
- 前端协议变更。输出仍使用现有 `AgentTurnOutput`、typed SSE 和 artifact persistence。
- 真实 DeepSeek V4 Flash smoke。该验证需要外部凭证、网络和额度。
- 新增 Lisa/Alex/DeepSeek 专属 runtime、API path、store 或 renderer。

## 数据契约

`DeliveryArtifactData` 使用严格 schema，未知字段拒绝，字符串字段不得为空，数组字段至少一项。建议字段：

- `document_info`: 复用 `DocumentInfo`。
- `delivery_metrics`: 项目/需求名称、版本、生成时间、交付状态、总用例数、高风险项数量。
- `executive_summary`: 测试范围、核心风险、用例覆盖、交付判断。
- `requirement_summary`: 需求事实、业务规则、链路和澄清问题摘要。
- `strategy_summary_items`: 质量目标、高风险项、测试分层、资源取舍摘要。
- `case_summary_items`: 按维度统计用例数量、P0/P1/P2、自动化候选、不可执行或需补环境数量。
- `coverage_map`: 需求、风险、测试点、用例、验收状态。
- `open_risks`: 开放风险、类型、影响、可接受性、责任方、后续处理、状态。
- `acceptance_checklist`: 交付验收清单，复用 `StageGateCheck` 语义。
- `signoffs`: 产品、研发、测试等签署角色、意见、状态。
- `change_log`: 版本、日期、变更内容、原因、责任方。

跨字段校验：

- `delivery_metrics.total_cases` 必须等于 `case_summary_items.case_count` 之和。
- `delivery_metrics.high_risk_count` 必须等于 `open_risks` 中 `risk_type` 包含风险且 `acceptable` 不是 `是` 的数量。
- `coverage_map.case_ids` 必须至少一项，并在渲染时合并为 `用例` 列。

## 渲染契约

renderer 必须稳定输出：

- `# 测试设计文档`
- `## 1. 文档信息`
- `## 2. 执行摘要`
- `## 3. 需求分析摘要`
- `## 4. 测试策略摘要`
- `## 5. 测试用例摘要`
- `## 6. 覆盖地图`
- `## 7. 开放风险`
- `## 8. 交付验收清单`
- `## 9. 签署确认`
- `## 10. 变更记录`

`coverage-map` 必须使用 fenced `ai4se-visual` JSON block，`type` 为 `coverage-map`，`columns` 为固定五列。renderer 输出必须通过 `validate_agent_turn()`，同一输入重复渲染结果完全一致。

## 失败处理

缺字段、空字符串、空数组、统计不一致和非法覆盖地图数据必须在 Pydantic/schema 层显式失败。runtime retry prompt 应提示修正 `artifact_data`，禁止输出 Markdown 文档、Mermaid 代码块、`coverage-map` JSON 代码块或表格。

## 验收条件

1. 合法 DELIVERY `artifact_data` 能渲染为 contract-valid artifact，并包含 `coverage-map`。
2. DELIVERY 统计不一致时 schema 校验失败，不生成伪造 artifact。
3. runtime 在 `TEST_DESIGN/DELIVERY` 下要求 `artifact_data`，不再要求模型输出完整 Markdown。
4. raw JSON stream final output 能先渲染 DELIVERY artifact_data，再进入现有 `AgentTurnOutput`/typed SSE 路径。
5. DeepSeek V4 todo 记录 DELIVERY 已迁移和仍未迁移的其他 workflow。

## 验证计划

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py -q`
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_agent_contracts.py tools/new-agents/backend/tests/test_agent_endpoint.py tools/new-agents/backend/tests/test_stream_services.py tools/new-agents/backend/tests/test_test_asset_parsing.py tools/new-agents/backend/tests/test_test_assets.py -q`
- `.venv/bin/python -m py_compile tools/new-agents/backend/agent_runtime.py tools/new-agents/backend/artifact_data_renderers.py`
- `git diff --cached --check`
