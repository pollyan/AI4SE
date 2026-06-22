# DeepSeek V4 REQ_REVIEW/REVIEW 结构化产物数据设计

## 背景

DeepSeek V4 Flash 当前作为 `json_object_only` provider 使用。`TEST_DESIGN` 四阶段已经完成 `artifact_data` 迁移：模型输出业务数据，后端用 Pydantic schema 校验并确定性渲染 Markdown、Mermaid 和 `ai4se-visual`。`REQ_REVIEW/REVIEW` 仍要求模型直接输出完整《需求评审问题清单》、Mermaid flowchart 和 `score-matrix`，这会继续暴露 Markdown 标题缺失、visual JSON 格式错误和表格截断风险。

## 用户故事

作为使用 Lisa 做需求评审的用户，当我提交需求文档并进入 `REQ_REVIEW/REVIEW` 阶段时，我希望 DeepSeek V4 只输出结构化评审数据，由后端确定性渲染需求评审问题清单、质量结构图和评分矩阵，从而降低模型直接拼最终文档格式导致的失败率。

## 范围

本轮纳入：

- 新增 `REQ_REVIEW/REVIEW` 的 `artifact_data` Pydantic schema。
- 新增 deterministic renderer，输出当前 contract 要求的《需求评审问题清单》全部 H1/H2 和问题表字段。
- renderer 生成 Mermaid `flowchart` 和 `ai4se-visual` `score-matrix`。
- runtime 在 `REQ_REVIEW/REVIEW` 阶段选择 artifact_data instruction，并在 retry prompt 中要求修正数据而非重写 Markdown。
- 后端测试覆盖合法渲染、统计不一致拒绝、runtime instruction、runtime parse 和 raw stream final rendering。
- 更新 DeepSeek V4 todo 的当前进展。

本轮不纳入：

- 迁移 `REQ_REVIEW/REPORT`。REPORT 依赖 REVIEW 的结构化问题清单，适合作为下一轮。
- 迁移 `VALUE_DISCOVERY`、`IDEA_BRAINSTORM`、`INCIDENT_REVIEW`。
- 前端协议变更。输出仍使用 `AgentTurnOutput`、typed SSE 和 artifact persistence。
- 真实 DeepSeek V4 Flash smoke。该验证需要外部凭证、网络和额度。
- 新增 Lisa/Alex/DeepSeek 专属 runtime、API path、store 或 renderer。

## 数据契约

`ReqReviewArtifactData` 使用严格 schema：未知字段拒绝，字符串字段不得为空，数组字段至少一项。

字段：

- `review_info`: artifact 名称、被评审需求、评审时间、需求概述、评审结论倾向。
- `scope_items`: 评审范围与不评审范围。
- `quality_overview`: 评审维度、质量判断、严重度评分、证据、测试风险、状态。
- `issue_statistics`: P0/P1/P2 数量和说明。
- `issue_groups`: 按评审维度分组的问题清单，每条问题包含 ID、维度、描述、优先级、阻断性、章节、影响、证据、建议、责任方、状态。
- `revision_suggestions`: 关联问题、修订建议、验收口径、责任方、状态。
- `stage_gate`: 复用 `StageGateCheck`。

跨字段校验：

- `issue_statistics.p0_count`、`p1_count`、`p2_count` 必须等于 `issue_groups` 中对应优先级的问题数量。
- `revision_suggestions.related_issues` 只能引用已存在的问题 ID。
- `quality_overview.severity_score` 必须是 1 到 5。

## 渲染契约

renderer 必须稳定输出：

- `# 需求评审问题清单`
- `## 评审信息`
- `## 评审范围与不评审范围`
- `## 需求质量总览`
- `## 需求质量结构图`
- `## 问题统计`
- `## 按维度问题清单`
- `## 修订建议`
- `## 阶段门禁`

`score-matrix` 必须使用 fenced `ai4se-visual` JSON block，`type` 为 `score-matrix`，列为 `评审维度`、`严重度评分`、`主要证据`、`测试风险`。renderer 输出必须通过 `validate_agent_turn()`，同一输入重复渲染结果完全一致。

## 失败处理

缺字段、空字符串、空数组、统计不一致、未知问题引用和严重度评分越界必须显式失败。runtime retry prompt 应提示修正 `artifact_data`，禁止输出 Markdown 文档、Mermaid 代码块、`score-matrix` JSON 代码块或表格。

## 验收条件

1. 合法 REVIEW `artifact_data` 能渲染为 contract-valid artifact，并包含 flowchart 和 `score-matrix`。
2. REVIEW 问题统计不一致时 schema 校验失败，不生成伪造 artifact。
3. runtime 在 `REQ_REVIEW/REVIEW` 下要求 `artifact_data`，不再要求模型输出完整 Markdown。
4. raw JSON stream final output 能先渲染 REVIEW artifact_data，再进入现有 `AgentTurnOutput`/typed SSE 路径。
5. DeepSeek V4 todo 记录 `REQ_REVIEW/REVIEW` 已迁移和 `REQ_REVIEW/REPORT` 仍待迁移。

## 验证计划

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py -q`
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_agent_contracts.py tools/new-agents/backend/tests/test_agent_endpoint.py tools/new-agents/backend/tests/test_stream_services.py -q`
- `.venv/bin/python -m py_compile tools/new-agents/backend/agent_runtime.py tools/new-agents/backend/artifact_data_renderers.py`
- `git diff --cached --check`
