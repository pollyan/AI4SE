# DeepSeek V4 REQ_REVIEW/REPORT 结构化产物数据设计

## 背景

`REQ_REVIEW/REVIEW` 已完成 `artifact_data` 迁移，需求评审问题清单现在由后端确定性生成。`REQ_REVIEW/REPORT` 仍要求模型直接输出完整《需求评审报告》、Mermaid `pie` 和 `priority-board`，这会继续让 DeepSeek V4 Flash 承担最终 Markdown 和 visual 格式职责。为了完成 Lisa 需求评审 workflow 的结构化产物闭环，本轮迁移 REPORT 阶段。

## 用户故事

作为使用 Lisa 做需求评审闭环的用户，当我完成深度评审并进入 `REQ_REVIEW/REPORT` 阶段时，我希望 DeepSeek V4 只输出结构化报告数据，由后端确定性渲染正式评审报告、优先级饼图和优先级看板，从而减少模型直接拼最终文档格式导致的失败率。

## 范围

本轮纳入：

- 新增 `REQ_REVIEW/REPORT` 的 `artifact_data` Pydantic schema。
- 新增 deterministic renderer，输出当前 contract 要求的《需求评审报告》全部 H1/H2/H3 和必需字段。
- renderer 生成 Mermaid `pie` 和 `ai4se-visual` `priority-board`。
- runtime 在 `REQ_REVIEW/REPORT` 阶段选择 artifact_data instruction，并在 retry prompt 中要求修正数据而非重写 Markdown。
- 后端测试覆盖合法渲染、统计不一致拒绝、runtime instruction、runtime parse 和 raw stream final rendering。
- 更新 DeepSeek V4 todo 的当前进展。

本轮不纳入：

- 迁移 `VALUE_DISCOVERY`、`IDEA_BRAINSTORM`、`INCIDENT_REVIEW`。
- 前端协议变更。输出仍使用 `AgentTurnOutput`、typed SSE 和 artifact persistence。
- 真实 DeepSeek V4 Flash smoke。该验证需要外部凭证、网络和额度。
- 新增 Lisa/Alex/DeepSeek 专属 runtime、API path、store 或 renderer。

## 数据契约

`ReqReviewReportArtifactData` 使用严格 schema：未知字段拒绝，字符串字段不得为空，数组字段至少一项。

字段：

- `conclusion`: artifact 名称、评审结果、结论理由、是否允许进入开发/测试设计、是否需要复审、摘要。
- `review_info`: 被评审需求、评审时间、评审输入、评审参与方。
- `issue_statistics`: P0/P1/P2 数量。
- `issue_closures`: 按问题优先级记录问题描述、所属章节、影响、责任方、下一步、关闭状态和复审条件。
- `review_conditions`: 复审条件、关联问题、验证方式、责任方、状态。
- `signoffs`: 产品、研发、测试等签署角色、意见和状态。
- `change_log`: 版本、日期、变更内容、原因、责任方。

跨字段校验：

- `issue_statistics.p0_count`、`p1_count`、`p2_count` 必须等于 `issue_closures` 中对应优先级的问题数量。
- `review_conditions.related_issues` 只能引用已存在的问题 ID。
- `conclusion.review_result` 必须与 P0/P1 状态保持一致：存在未关闭 P0 时不能为“通过”；无 P0 但存在未关闭 P1 时不能为“通过”。

## 渲染契约

renderer 必须稳定输出：

- `# 需求评审报告`
- `## 评审结论`
- `### 判定标准`
- `## 评审信息`
- `## 问题统计`
- `## 优先级看板`
- `## 问题关闭清单`
- `### P0 阻塞性问题`
- `### P1 重要问题`
- `### P2 优化建议`
- `## 复审条件`
- `## 签署确认`
- `## 变更记录`

`priority-board` 必须使用 fenced `ai4se-visual` JSON block，`type` 为 `priority-board`，列为 `问题`、`优先级`、`影响范围`、`责任方`、`下一步`、`关闭状态`。renderer 输出必须通过 `validate_agent_turn()`，同一输入重复渲染结果完全一致。

## 失败处理

缺字段、空字符串、空数组、统计不一致、未知问题引用和明显不一致的评审结论必须显式失败。runtime retry prompt 应提示修正 `artifact_data`，禁止输出 Markdown 文档、Mermaid 代码块、`priority-board` JSON 代码块或表格。

## 验收条件

1. 合法 REPORT `artifact_data` 能渲染为 contract-valid artifact，并包含 Mermaid `pie` 和 `priority-board`。
2. REPORT 问题统计不一致时 schema 校验失败，不生成伪造 artifact。
3. runtime 在 `REQ_REVIEW/REPORT` 下要求 `artifact_data`，不再要求模型输出完整 Markdown。
4. raw JSON stream final output 能先渲染 REPORT artifact_data，再进入现有 `AgentTurnOutput`/typed SSE 路径。
5. DeepSeek V4 todo 记录 `REQ_REVIEW/REPORT` 已迁移和其他 workflow 仍待迁移。

## 验证计划

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py -q`
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_agent_contracts.py tools/new-agents/backend/tests/test_agent_endpoint.py tools/new-agents/backend/tests/test_stream_services.py -q`
- `.venv/bin/python -m py_compile tools/new-agents/backend/agent_runtime.py tools/new-agents/backend/artifact_data_renderers.py`
- `git diff --cached --check`
