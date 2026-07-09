# 测试策略 (Testing Strategy)

## 测试金字塔

```
        ┌─────────────┐
        │    E2E      │  ← 少量，验证关键用户流程 (Chrome DevTools MCP)
        │  (手动/MCP) │
        ├─────────────┤
        │ Integration │  ← 中等，验证模块协作 (mock 外部服务)
        ├─────────────┤
        │     API     │  ← 较多，验证端点契约 (Flask test_client)
        ├─────────────┤
        │    Unit     │  ← 最多，验证纯逻辑 (无 I/O)
        └─────────────┘
```

## 测试类型与边界定义

| 类型 | 框架 | 测什么 | Mock 范围 |
|------|------|--------|-----------|
| **后端单元** | pytest | 纯函数、Pydantic 模型、工具类 | 无外部依赖 |
| **后端 API** | pytest + Flask test_client | HTTP 端点、请求/响应格式、状态码 | LLM 服务、外部 API |
| **后端集成** | pytest | 多模块协作、状态流转、工作流 | LLM、外部服务 |
| **代理测试** | Jest | MidScene Server API、WebSocket | Playwright 调用 |

## Mock 策略

| 被 Mock 对象 | Mock 方式 | 使用场景 |
|-------------|-----------|----------|
| **LLM 服务** | `unittest.mock.patch` + `FakeLLM` | 所有非 `slow` 标记的测试 |
| **数据库** | SQLite `:memory:` (conftest.py / test fixtures) | 所有需要持久化的测试 |
| **外部 API** | `responses` 库 / `httpx.MockTransport` | API 测试 |
| **OpenAI Client** | `unittest.mock.patch('llm_client.OpenAI')` | new-agents-backend 测试 |

## 测试文件组织

```text
tools/intent-tester/tests/
├── conftest.py              # 共享 fixtures
├── proxy/                   # MidScene API 测试 (Jest)
└── test_*.py                # Python 测试

tools/new-agents/backend/tests/
├── conftest.py              # Flask app / SQLite / 环境隔离 fixtures
├── test_api.py              # 基础 API 端点测试
├── test_agent_*.py          # PydanticAI Agent Runtime 与 typed SSE 端点测试
├── test_*_service.py        # 后端 service 层单元测试
└── test_backend_layering.py # 后端分层架构约束测试
```

## 测试命名规范

| 类型 | 命名模式 | 示例 |
|------|----------|------|
| Python 测试文件 | `test_<模块名>.py` | `test_api.py` |
| Python 测试函数 | `test_<行为>_<条件>` | `test_chat_stream_returns_sse` |
| TypeScript 测试文件 | `<组件名>.test.tsx` | `ArtifactPane.test.tsx` |
| TypeScript 测试用例 | `it('<动作> when <条件>')` | `it('renders error when fetch fails')` |

## 何时写哪种测试

| 场景 | 推荐测试类型 | 理由 |
|------|-------------|------|
| 新增 Pydantic 模型 | `unit` | 验证字段约束，快速反馈 |
| 新增 API 端点 | `api` | 验证契约，mock 下游服务 |
| 新增 React 组件 | component test | 验证渲染和交互 |
| 修复线上 Bug | 先写复现测试 | 防止回归 |
| 重构已有代码 | 确保已有测试通过 | 不新增测试，除非发现覆盖盲区 |

## 场景覆盖率口径与准入标准

这里的“覆盖率”首先指**场景覆盖率**，不是单纯的工具行覆盖率。对于 LLM/Agent 功能，优先看关键不变量是否被机械保护，再看 `pytest-cov` / Vitest coverage 这类辅助指标。

场景覆盖率按以下维度审计：

| 维度 | 必须回答的问题 | 示例 |
|------|----------------|------|
| 正向场景 | 主路径是否能产出正确字段、状态和 UI 写入 | `agent_turn` 成功返回后，左侧只显示 `chat`，右侧更新 `artifact_update.markdown` |
| 异常场景 | 输入缺失、模型输出非法、协议损坏、依赖缺失是否会明确失败 | 缺默认 LLM 配置返回 503；坏 SSE JSON 直接报错 |
| 边界场景 | 空值、最后阶段、非法阶段、无 artifact 更新等边界是否被保护 | 最后阶段不能请求下一阶段；必需 artifact 阶段不能返回 `none` |
| 跨字段不变量 | 多个字段之间是否存在串位风险，并被测试明确约束 | `chat` 禁止承载 Markdown artifact；`NEXT_STAGE` 不直接写入未确认下一阶段产物 |
| 跨层不变量 | 后端契约、SSE、前端解析、状态写入是否在同一规则下协作 | API 测试解析 SSE JSON；前端状态层只消费 `chatResponse` / `newArtifact` |
| 供应商兼容 | 真实模型或供应商特性是否有可选冒烟验证 | DeepSeek V4 禁用 thinking、提高 retries；真实模型 smoke 只显式运行 |

### 当前准入标准

| 区域 | 必跑命令 | 当前要求 |
|------|----------|----------|
| `tools/new-agents/backend` | `cd tools/new-agents/backend && python3 -m pytest -m "not slow" -q` | 常规门禁通过；真实模型冒烟单独运行 |
| `tools/new-agents/backend` 场景覆盖 | 对照本文件 New Agents 职责分层和审计清单逐项确认 | 新增或修改智能体链路时必须补正向/异常/边界/跨层不变量测试 |
| `tools/new-agents/backend` 工具覆盖率 | `cd tools/new-agents/backend && python3 -m pytest -m "not slow" --cov=<关键模块> --cov-report=term-missing -q` | 辅助审计指标；不得替代场景矩阵判断 |
| `tools/new-agents/frontend` | `cd tools/new-agents/frontend && npm test` | 全量通过 |
| `tools/new-agents/frontend` 类型检查 | `cd tools/new-agents/frontend && npm run lint` | 必须通过 |
| 全仓关键 Python 语法检查 | `flake8 --select=E9,F63,F7,F82 .` | 必须通过 |

### 覆盖率解释规则

- **契约层优先**：`agent_contracts.py`、`request_schemas.py`、`sse_schemas.py` 这类边界模型应追求高覆盖率，因为它们承担机械拦截职责。
- **场景矩阵优先于百分比**：如果测试只覆盖 happy path，即使工具行覆盖率很高，也不能认为智能体链路已被保护。
- **编排层看路径覆盖**：`stream_services.py`、`routes.py` 应覆盖成功、请求错误、LLM 错误、契约错误，不追求模拟所有 Flask/供应商细节。
- **前端状态层看行为覆盖**：`chatService.ts`、`agentCore.ts` 必须覆盖左侧消息、右侧 artifact、阶段推进三类状态写入，不能只看组件渲染覆盖。
- **协议错误不能静默跳过**：typed SSE、结构化 JSON、Pydantic 输出一旦损坏，应报错暴露问题，不通过“忽略坏事件继续处理”制造假成功。
- **真实模型不纳入覆盖率门禁**：`test_agent_real_smoke.py` 是供应商兼容冒烟，依赖环境变量和额度，只作为发布前/本地专项验证。
- **前端覆盖率工具链需显式安装**：如果运行 `npm test -- --coverage` 报缺少 `@vitest/coverage-v8`，说明只能确认测试通过，不能声称已有前端覆盖率数据。
- **覆盖率下降必须解释**：如果新增代码导致覆盖率下降，要么补测试，要么在变更说明中明确为什么该代码不适合覆盖率衡量。

## New Agents 测试职责分层

New Agents 的核心风险不是单个函数错误，而是 LLM 输出、后端契约、SSE 传输、前端状态写入之间的职责混用。测试必须覆盖跨字段不变量，不能只验证 happy path。

### 后端契约层：`agent_contracts.py`

职责：定义 AgentTurnOutput 的唯一合法形态，机械拦截模型输出污染。

必须覆盖：
- `chat` 只承载左侧对话的简短说明，禁止包含 Markdown 标题、表格、代码块、Mermaid、完整 artifact 正文或 `<CHART>/<ARTIFACT>/<CHAT>` 旧标签协议。
- `artifact_update.type=replace` 时 `markdown` 必须非空。
- 有必需模板的阶段必须更新 artifact，不能返回 `artifact_update.type=none`。
- 各工作流阶段的必需标题必须完整出现。
- 关键阶段的 Mermaid 可视化 contract 必须完整出现，例如 `REQUIRED_ARTIFACT_MERMAID_DIAGRAMS` 要求的 `quadrantChart`、`timeline`、`mindmap`、`journey` 等。
- 阶段推进只能指向下一个合法阶段，最后阶段不能请求下一阶段。
- 外部模型偶发把嵌套对象编码成 JSON 字符串时，只接受可解析为对象的 JSON 字符串，拒绝非 JSON 字符串。

典型测试文件：`tools/new-agents/backend/tests/test_agent_contracts.py`

### 后端运行时层：`agent_runtime.py`

职责：把 PydanticAI 输出转成项目契约对象，并在返回前调用工作流契约校验。

必须覆盖：
- PydanticAI 返回 dict 或模型对象时都经过 `AgentTurnOutput` 校验。
- 违反工作流规则的输出会被拒绝，不进入 SSE 层。
- raw JSON streaming 的 partial `artifact_data` 不能被合成为 `artifact_update.replace` 进度页；只有完整解析并通过 renderer / 契约校验的正式 Markdown 才能进入右侧 artifact。若支持段落级流式，只允许已闭合、已通过子模型校验的局部正式章节进入 delta，最终 `agent_turn` 仍必须通过完整工作流契约。
- 模型特定配置可测，例如 DeepSeek V4 禁用 thinking、提高结构化输出 retries。

典型测试文件：`tools/new-agents/backend/tests/test_agent_runtime.py`

#### Partial Artifact Streaming 覆盖矩阵

真实 partial artifact streaming 的验收口径是：raw JSON streaming 期间，后端在完整 `agent_turn` 前基于已闭合顶层 `artifact_data` 字段生成正式 `agent_delta.output.artifact_update.replace.markdown`；最终 `agent_turn` 仍通过完整 workflow contract。`artifact_patch` 是可选局部应用元数据，部分阶段因多字段依赖或一次新增多个标题可以没有 patch。

该能力必须作为 New Agents 回归门禁保留。`scripts/test/test-local.sh new-agents` 会运行 `tools/new-agents/backend` 下的 `pytest -m "not slow" -q`，因此下列不带 `slow` 标记的测试已经进入本地 New Agents 回归测试集：

- `test_artifact_data_structured_output_instruction_puts_artifact_data_before_chat_for_visible_streaming`：覆盖 25 个 artifact-data 阶段，防止结构化指令退回 `chat` 先于 `artifact_data`，导致真实 UI 右侧产物只能最后刷新。
- `test_runtime_raw_json_stream_turn_renders_*artifact_data*` 用例：覆盖各阶段在 final `agent_turn` 前产生至少一个正式 `artifact_delta.output.artifact_update.replace.markdown`；其中 `STORY_BREAKDOWN` 四阶段由 `test_runtime_raw_json_stream_turn_renders_all_story_breakdown_stages_from_artifact_data` 参数化覆盖，`PRD_REVIEW` 四阶段由 artifact-data registry 参数化覆盖。当前强门禁是“final 前有正式 artifact delta + final contract 通过”，不是每个阶段都有多段字段级 partial。
- 字段级 partial renderer 当前只覆盖 `TEST_DESIGN/CLARIFY`，由 `_render_partial_test_design_clarify_markdown` 和对应 runtime 测试保护。其他阶段当前在完整顶层 `artifact_data` 对象可解析后生成 before-final 正式 delta；`artifact_patch` 是可选局部应用元数据，当前不作为全阶段强门禁。

第 8 轮全工作流回归门禁新增 `ARTIFACT_DATA_STAGE_FIXTURES` 测试登记表：所有 `supports_artifact_data_rendering()` 支持的在线阶段都必须在该 registry 中有固定 `artifact_data` 样例；registry 样例必须能通过 deterministic renderer 和 `validate_agent_turn()`。`test_agent_runtime.py` 的 artifact-data instruction 顺序矩阵从该 registry 派生，避免新增阶段时漏掉 raw JSON visible streaming 门禁。`test_workflow_contract_sync.py` 同时反向校验 `workflow_manifest.json` 的 `visualContract` 与后端 required Mermaid / structured visual maps 完全一致。

`artifact_data` 字段来源与视觉协议矩阵用于说明当前工程事实，不替代 Pydantic schema、renderer tests 或 `workflow_manifest.json`；维护时以 `ARTIFACT_DATA_STAGE_FIXTURES`、`REQUIRED_ARTIFACT_MERMAID_DIAGRAMS`、`REQUIRED_ARTIFACT_STRUCTURED_VISUALS`、`artifact_data_renderers.py` 和对应 renderer / runtime tests 为事实源。

| Workflow / Stage | 模型负责的 artifact_data | 后端派生 / 归一化 | 视觉来源 | 证据 |
|---|---|---|---|---|
| `TEST_DESIGN/CLARIFY` | 文档信息、需求事实、系统边界、业务规则、链路、澄清问题、质量需求、下游输入、阶段门禁 | 校验必填值和列表，不派生字段；已迁入 `artifactDataContract` manifest sync | 后端由 `flow_links` 生成 Mermaid `flowchart` | `ClarifyArtifactData`、`test_clarify_artifact_data_rejects_*`、`test_test_design_clarify_artifact_data_contract_manifest_drives_backend_instruction`、`REQUIRED_ARTIFACT_MERMAID_DIAGRAMS` |
| `TEST_DESIGN/STRATEGY` | 文档信息、策略摘要、质量目标、风险 S/O/D、测试技术、测试分层、测试点、取舍、阶段门禁 | `risks[].rpn` 缺省时由 S/O/D 派生；显式错误 RPN 失败；ID/引用只校验不派生；已迁入 `artifactDataContract` manifest sync | 后端由 `risks` 生成 Mermaid `quadrantChart` 和 `ai4se-visual risk-board`；由 `test_layers` 生成 Mermaid `block-beta` | `test_strategy_artifact_data_computes_missing_rpn_for_generated_visuals`、`test_strategy_artifact_data_rejects_inconsistent_rpn`、`test_strategy_artifact_data_contract_manifest_drives_backend_instruction`、visual contract maps |
| `TEST_DESIGN/CASES` | 文档信息、设计依据、用例分组、测试数据环境、自动化候选、覆盖追溯、开放问题、阶段门禁 | `case_statistics` 缺省时由 `case_groups` 派生；`case_groups[].cases[].dimension` 缺省时由外层 `case_groups[].dimension` 派生；显式不一致统计或维度失败；case_id 引用只校验不派生；已迁入 `artifactDataContract` manifest sync | 后端由 `coverage_trace` 生成 `ai4se-visual traceability-matrix` | `test_cases_artifact_data_derives_statistics_when_missing`、`test_cases_artifact_data_derives_case_dimension_from_group_when_missing`、`test_cases_artifact_data_rejects_inconsistent_statistics`、`test_cases_artifact_data_rejects_case_dimension_mismatching_group`、`test_cases_artifact_data_rejects_unknown_*_case_reference`、`test_cases_artifact_data_contract_manifest_drives_backend_instruction` |
| `TEST_DESIGN/DELIVERY` | 文档信息、交付指标基础信息、执行摘要、需求摘要、策略摘要、用例摘要 P0/P1/P2、覆盖地图、开放风险、验收、签署、变更记录 | `case_summary_items[].case_count` 缺省时由 P0/P1/P2 派生；`delivery_metrics.total_cases`、`high_risk_count` 缺省时由用例摘要和开放风险派生；显式不一致统计失败；已迁入 `artifactDataContract` manifest sync | 后端由 `coverage_map` 生成 `ai4se-visual coverage-map` | `test_delivery_artifact_data_derives_case_count_and_metrics_when_missing`、`test_delivery_artifact_data_rejects_inconsistent_case_totals`、`test_delivery_artifact_data_rejects_inconsistent_high_risk_count_when_present`、`test_test_design_delivery_artifact_data_contract_manifest_drives_backend_instruction`、`REQUIRED_ARTIFACT_STRUCTURED_VISUALS` |
| `REQ_REVIEW/REVIEW` | 评审信息、评审范围、质量总览、问题统计描述、问题分组、修订建议、阶段门禁 | `issue_statistics.p0_count/p1_count/p2_count` 缺省时由 `issue_groups[].issues[].priority` 派生；`issue_groups[].issues[].dimension` 缺省时由外层 `issue_groups[].dimension` 派生；显式不一致统计或维度失败；已迁入 `artifactDataContract` manifest sync | 后端生成静态需求质量 Mermaid `flowchart`；由 `quality_overview` 生成 `ai4se-visual score-matrix` | `test_req_review_artifact_data_derives_issue_statistics_counts_when_missing`、`test_req_review_artifact_data_derives_issue_dimension_from_group_when_missing`、`test_req_review_artifact_data_rejects_inconsistent_issue_statistics`、`test_req_review_artifact_data_rejects_issue_dimension_mismatching_group`、`test_req_review_review_artifact_data_contract_manifest_drives_backend_instruction`、visual contract maps |
| `REQ_REVIEW/REPORT` | 评审结论、评审信息、关闭清单、复审条件、签署、变更记录 | `issue_statistics` 缺省时由 `issue_closures[].priority` 派生；显式不一致统计失败；已迁入 `artifactDataContract` manifest sync | 后端由 `issue_statistics` 生成 Mermaid `pie`；由 `issue_closures` 生成 `ai4se-visual priority-board` | `test_req_review_report_artifact_data_derives_issue_statistics_when_missing`、`test_req_review_report_artifact_data_rejects_inconsistent_issue_statistics`、`test_req_review_report_artifact_data_contract_manifest_drives_backend_instruction`、visual contract maps |
| `INCIDENT_REVIEW/TIMELINE` | 事件概要、影响指标、事实来源、时间线、事实/推测隔离、事实摘要、参与人、缺失信息、阶段门禁 | fact_id 引用只校验不派生；已迁入 `artifactDataContract` manifest sync | 后端由 `timeline_events` 生成 Mermaid `timeline` | `test_incident_timeline_artifact_data_rejects_*`、`test_incident_timeline_artifact_data_contract_manifest_drives_backend_instruction`、`REQUIRED_ARTIFACT_MERMAID_DIAGRAMS` |
| `INCIDENT_REVIEW/ROOT_CAUSE` | 分析上下文、5-Why、根因证据、鱼骨分类、根因结论、排除项、未验证原因、阶段门禁 | cause_id 引用和 5-Why 深度只校验不派生；已迁入 `artifactDataContract` manifest sync | 后端由 `why_chain` 生成 `ai4se-visual cause-map`；由 `fishbone_categories` 生成 Mermaid `mindmap` | `test_render_incident_root_cause_artifact_data_is_deterministic_and_contract_valid`、`test_incident_root_cause_artifact_data_rejects_*`、`test_incident_root_cause_artifact_data_contract_manifest_drives_backend_instruction`、cause-map contract tests |
| `INCIDENT_REVIEW/IMPROVEMENT` | 报告基础信息、时间线摘要、根因摘要、改进行动、根因覆盖、防复发、复查计划、遗留风险、经验教训、组织学习、签署、阶段门禁 | `report_info.action_count` 缺省时由 `improvement_actions` 数量派生；`priority_distribution` 缺省时由 `improvement_actions[].priority` 派生；显式不一致统计失败；根因覆盖 action/root_cause 引用和精确映射只校验不派生；已迁入 `artifactDataContract` manifest sync | 后端由 `priority_distribution` 生成 Mermaid `pie`；由 `improvement_actions` 生成 `ai4se-visual action-board` | `test_incident_improvement_artifact_data_derives_action_statistics_when_missing`、`test_incident_improvement_artifact_data_rejects_*`、`test_incident_improvement_artifact_data_rejects_action_mapped_to_wrong_root_cause_coverage`、`test_incident_improvement_artifact_data_rejects_missing_action_from_root_cause_coverage`、`test_incident_improvement_artifact_data_contract_manifest_drives_backend_instruction`、visual contract maps |
| `IDEA_BRAINSTORM/DEFINE` | 问题假设、目标用户、问题全景、证据、问题-用户匹配、约束、反向验证、阶段门禁 | problem/evidence 引用只校验不派生；已迁入 `artifactDataContract` manifest sync | 后端由 `problem_landscape` 生成 Mermaid `mindmap` | `test_idea_define_artifact_data_rejects_*`、`test_idea_define_structured_output_instruction_explains_root_problem_coverage`、`test_idea_define_artifact_data_contract_manifest_drives_backend_instruction` |
| `IDEA_BRAINSTORM/DIVERGE` | 发散方法、创意全景、创意卡、创意来源、搁置/排除记录、阶段门禁 | idea/source 引用和唯一性只校验不派生；已迁入 `artifactDataContract` manifest sync | 后端由 `idea_landscape` / `idea_cards` 生成 Mermaid `mindmap` | `test_idea_diverge_artifact_data_rejects_*`、partial 引用门禁 tests、`test_idea_diverge_artifact_data_contract_manifest_drives_backend_instruction` |
| `IDEA_BRAINSTORM/CONVERGE` | 决策矩阵、ICE 评估原子评分、资源约束、敏感性分析、验证实验、合并路径、阶段门禁 | `ice_score` 缺省时由后端按 `impact * confidence / effort` 派生；`rank` 缺省时由后端按 ICE 得分降序派生；显式错误值仍触发 validation failure；已迁入 `artifactDataContract` manifest sync | 后端由 `ice_evaluations` 生成 Mermaid `quadrantChart` | `test_idea_converge_artifact_data_derives_ice_score_when_missing`、`test_idea_converge_artifact_data_derives_rank_when_missing`、`test_idea_converge_artifact_data_rejects_*`、`test_idea_converge_artifact_data_contract_manifest_drives_backend_instruction` |
| `IDEA_BRAINSTORM/CONCEPT` | 定位声明、核心假设、Lean Canvas、MVP 功能、增长漏斗、风险、验证路线、不可做范围、决策记录、下一步、阶段门禁 | assumption/action 引用和必备画布格只校验不派生；MVP pie 计数仅在 renderer 中计算；已迁入 `artifactDataContract` manifest sync | manifest 只要求 `ai4se-visual mvp-map`；renderer 额外由 `mvp_features` 生成 Mermaid pie，由 `growth_funnel` 生成 Mermaid flowchart | `test_idea_concept_artifact_data_rejects_*`、`test_idea_concept_artifact_data_contract_manifest_drives_backend_instruction`、`REQUIRED_ARTIFACT_STRUCTURED_VISUALS` |
| `VALUE_DISCOVERY/ELEVATOR` | 文档信息、定位摘要、价值流、目标场景、痛点证据、差异化、商业可行性、评分矩阵、评分摘要、假设、电梯演讲、阶段门禁 | `score_summary.total_score` / `average_score` 由 `score_matrix` 归一化；显式不一致摘要失败；已迁入 `artifactDataContract` manifest sync | 后端由 `value_flow` 生成 Mermaid `flowchart`；由 `score_matrix` / `score_summary` 生成 `ai4se-visual score-matrix` | `test_value_elevator_artifact_data_computes_missing_score_summary_fields`、`test_value_elevator_artifact_data_rejects_inconsistent_score_summary`、`test_value_elevator_artifact_data_contract_manifest_drives_backend_instruction` |
| `VALUE_DISCOVERY/PERSONA` | 文档信息、画像摘要、画像、行为场景、决策链、痛点证据、反画像、优先级排序、阶段门禁 | persona 引用和优先级唯一性只校验不派生；已迁入 `artifactDataContract` manifest sync | 无 required visual；后端渲染画像、行为和决策链表格 | `test_value_persona_artifact_data_rejects_*`、`test_value_persona_artifact_data_contract_manifest_drives_backend_instruction`、`ARTIFACT_DATA_STAGE_FIXTURES` |
| `VALUE_DISCOVERY/JOURNEY` | 文档信息、旅程摘要、旅程阶段、痛点优先级、机会评分、切入策略、验证实验、阶段门禁 | stage/pain/opportunity 引用和唯一性只校验不派生；已迁入 `artifactDataContract` manifest sync | 后端由 `journey_stages` 生成 Mermaid `journey` 和 `ai4se-visual journey-map` | `test_value_journey_artifact_data_rejects_*`、`test_value_journey_artifact_data_contract_manifest_drives_backend_instruction`、visual contract maps |
| `VALUE_DISCOVERY/BLUEPRINT` | 文档信息、产品概述、目标用户、功能模块、需求、主流程、成功指标、MVP 计划、非功能需求、验收标准、路线图、风险、Lisa handoff 输入、阶段门禁 | requirement/handoff 引用只校验不派生；已迁入 `artifactDataContract` manifest sync | manifest 只要求 `ai4se-visual roadmap`；renderer 额外由 `feature_modules` 生成 Mermaid `mindmap`，由 `main_flow` 生成 Mermaid `flowchart` | `test_value_blueprint_artifact_data_rejects_*`、`test_value_blueprint_artifact_data_contract_manifest_drives_backend_instruction`、visual contract maps |
| `STORY_BREAKDOWN/INPUT_ANALYSIS` | 文档信息、输入分析、Epic、用户故事、验收标准、依赖、Sprint 切片、Lisa handoff 输入、阶段门禁 | `user_stories[].sprint` 缺省时由 `sprint_slices[].story_ids` 所属 `sprint_id` 派生，显式不一致失败；ID 唯一性、Epic / Story / Criterion / Dependency / handoff 引用和 `stage_gate` checked 只校验不派生；`story_points >= 1`；已迁入 `artifactDataContract` manifest sync | 后端由 `epics` 生成 Mermaid `flowchart`；由 `user_stories` 生成 `ai4se-visual story-map` | `test_story_breakdown_artifact_data_derives_story_sprint_from_sprint_slices`、`test_story_breakdown_artifact_data_rejects_story_sprint_mismatching_slice`、`test_story_breakdown_artifact_data_contract_manifest_drives_backend_instruction`、`REQUIRED_ARTIFACT_MERMAID_DIAGRAMS` |
| `STORY_BREAKDOWN/EPIC_MAPPING` | 文档信息、输入分析、Epic、用户故事、验收标准、依赖、Sprint 切片、Lisa handoff 输入、阶段门禁 | `user_stories[].sprint` 缺省时由 `sprint_slices[].story_ids` 所属 `sprint_id` 派生，显式不一致失败；ID 唯一性、Epic / Story / Criterion / Dependency / handoff 引用和 `stage_gate` checked 只校验不派生；`story_points >= 1`；已迁入 `artifactDataContract` manifest sync | 后端由 `epics` 生成 Mermaid `flowchart`；由 `user_stories` 生成 `ai4se-visual story-map` | `test_story_breakdown_artifact_data_derives_story_sprint_from_sprint_slices`、`test_story_breakdown_artifact_data_rejects_story_sprint_mismatching_slice`、`test_story_breakdown_artifact_data_contract_manifest_drives_backend_instruction`、`test_runtime_raw_json_stream_turn_renders_all_story_breakdown_stages_from_artifact_data` |
| `STORY_BREAKDOWN/STORY_BACKLOG` | 文档信息、输入分析、Epic、用户故事、验收标准、依赖、Sprint 切片、Lisa handoff 输入、阶段门禁 | `user_stories[].sprint` 缺省时由 `sprint_slices[].story_ids` 所属 `sprint_id` 派生，显式不一致失败；ID 唯一性、Epic / Story / Criterion / Dependency / handoff 引用和 `stage_gate` checked 只校验不派生；`story_points >= 1`；已迁入 `artifactDataContract` manifest sync | 后端由 `epics` 生成 Mermaid `flowchart`；由 `user_stories` 生成 `ai4se-visual story-map` | `test_story_breakdown_artifact_data_derives_story_sprint_from_sprint_slices`、`test_story_breakdown_artifact_data_rejects_story_sprint_mismatching_slice`、`test_story_breakdown_artifact_data_contract_manifest_drives_backend_instruction`、story handoff tests |
| `STORY_BREAKDOWN/SPRINT_PLAN` | 文档信息、输入分析、Epic、用户故事、验收标准、依赖、Sprint 切片、Lisa handoff 输入、阶段门禁 | `user_stories[].sprint` 缺省时由 `sprint_slices[].story_ids` 所属 `sprint_id` 派生，显式不一致失败；ID 唯一性、Epic / Story / Criterion / Dependency / handoff 引用和 `stage_gate` checked 只校验不派生；`story_points >= 1`；已迁入 `artifactDataContract` manifest sync | 后端由 `epics` 生成 Mermaid `flowchart`；由 `user_stories` 生成 `ai4se-visual story-map` | `test_story_breakdown_artifact_data_derives_story_sprint_from_sprint_slices`、`test_story_breakdown_artifact_data_rejects_story_sprint_mismatching_slice`、`test_story_handoff_candidates_use_sprint_derived_from_sprint_slices`、`test_story_breakdown_artifact_data_contract_manifest_drives_backend_instruction`、single story handoff tests |
| `PRD_REVIEW/INVENTORY` | 文档信息、PRD 输入盘点、质量发现、补全动作、修订章节、验收标准、handoff 输入、阶段门禁 | finding/action/section 引用和 stage gate 只校验不派生；已迁入 `artifactDataContract` manifest sync | 后端由 `prd_inventory` 生成 Mermaid `mindmap` | `test_prd_review_artifact_data_rejects_*`、`test_prd_review_artifact_data_contract_manifest_drives_backend_instruction`、`ARTIFACT_DATA_STAGE_FIXTURES` |
| `PRD_REVIEW/QUALITY_AUDIT` | 文档信息、PRD 输入盘点、质量发现、补全动作、修订章节、验收标准、handoff 输入、阶段门禁 | finding/action/section 引用和 stage gate 只校验不派生；已迁入 `artifactDataContract` manifest sync | 后端由 `quality_findings` 生成 `ai4se-visual score-matrix` | `test_prd_review_artifact_data_rejects_*`、`test_prd_review_artifact_data_contract_manifest_drives_backend_instruction`、visual contract maps |
| `PRD_REVIEW/COMPLETION_PLAN` | 文档信息、PRD 输入盘点、质量发现、补全动作、修订章节、验收标准、handoff 输入、阶段门禁 | finding/action/section 引用和 stage gate 只校验不派生；已迁入 `artifactDataContract` manifest sync | 后端由 `completion_actions` 生成 `ai4se-visual action-board` 和 `ai4se-visual roadmap` | `test_prd_review_artifact_data_rejects_*`、`test_prd_review_artifact_data_contract_manifest_drives_backend_instruction`、visual contract maps |
| `PRD_REVIEW/REVISION_BLUEPRINT` | 文档信息、PRD 输入盘点、质量发现、补全动作、修订章节、验收标准、handoff 输入、阶段门禁 | finding/action/section 引用和 stage gate 只校验不派生；已迁入 `artifactDataContract` manifest sync | 后端由 `completion_actions` 生成 `ai4se-visual action-board`，由 `revision_sections` 生成 `ai4se-visual roadmap` | `test_prd_review_artifact_data_rejects_*`、`test_prd_review_artifact_data_contract_manifest_drives_backend_instruction`、visual contract maps |

当前矩阵不表示所有派生字段都已后端化。当前 25 个在线 artifact-data 阶段均已迁入 `artifactDataContract` manifest sync，关键不变量由 Pydantic model、renderer tests、runtime instruction、frontend prompt/config tests 和 artifact contract tests 共同保护。Mermaid 仍是后端 deterministic renderer 的编译目标；backend 仍不执行 Mermaid JS parse 或 `mmdc` 渲染门禁。

架构边界：流式机制是统一的，不为 Lisa、Alex、IDEA、VALUE 或后续 workflow 新增独立 runtime、SSE endpoint、前端 store 或 ArtifactPane 渲染管线。阶段差异只允许体现在 `workflow_manifest.json`、stage prompt、artifact_data schema、可选字段级 partial renderer 和 contract 测试里；每新增一个在线阶段，都必须进入下面的 25 阶段同类矩阵并补齐指令顺序、runtime raw JSON before-final delta 和最终 contract 验证。若要把某阶段升级为多段字段级 partial，必须单独补该阶段 partial renderer、子模型校验和聚焦测试。

25 个在线阶段的当前确定性覆盖如下：

| Workflow / Stage | 字段级 partial renderer | Runtime raw JSON streaming 测试 | 关键契约 / 下游 |
|---|---|---|---|
| `TEST_DESIGN/CLARIFY` | 已实现字段级 partial renderer | `test_runtime_raw_json_stream_turn_renders_paragraph_level_clarify_artifact_data` | 需求分析标题、Mermaid flowchart、最终 CLARIFY contract |
| `TEST_DESIGN/STRATEGY` | 暂未实现；完整 artifact_data 到齐时 before-final delta | `test_runtime_raw_json_stream_turn_renders_paragraph_level_strategy_artifact_data` | 测试策略标题、风险 / 技术 / 层级章节、最终 STRATEGY contract |
| `TEST_DESIGN/CASES` | 暂未实现；完整 artifact_data 到齐时 before-final delta | `test_runtime_raw_json_stream_turn_renders_paragraph_level_cases_artifact_data` | Lisa 测试资产解析、`traceability-matrix` |
| `TEST_DESIGN/DELIVERY` | 暂未实现；完整 artifact_data 到齐时 before-final delta | `test_runtime_raw_json_stream_turn_renders_delivery_artifact_data_before_final_output` | `coverage-map`、DELIVERY contract |
| `REQ_REVIEW/REVIEW` | 暂未实现；完整 artifact_data 到齐时 before-final delta | `test_runtime_raw_json_stream_turn_renders_req_review_artifact_data_before_final_output` | `score-matrix`、问题统计 Mermaid、REVIEW contract |
| `REQ_REVIEW/REPORT` | 暂未实现；完整 artifact_data 到齐时 before-final delta | `test_runtime_raw_json_stream_turn_renders_req_review_report_artifact_data_before_final_output` | `priority-board`、REPORT contract |
| `INCIDENT_REVIEW/TIMELINE` | 暂未实现；完整 artifact_data 到齐时 before-final delta | `test_runtime_raw_json_stream_turn_renders_incident_timeline_artifact_data_before_final_output` | Mermaid timeline、事实来源与时间线 contract |
| `INCIDENT_REVIEW/ROOT_CAUSE` | 暂未实现；完整 artifact_data 到齐时 before-final delta | `test_runtime_raw_json_stream_turn_renders_incident_root_cause_artifact_data_before_final_output` | `cause-map`、Mermaid mindmap、根因 contract |
| `INCIDENT_REVIEW/IMPROVEMENT` | 暂未实现；完整 artifact_data 到齐时 before-final delta | `test_runtime_raw_json_stream_turn_renders_incident_improvement_artifact_data_before_final_output` | Mermaid pie、`action-board`、改进报告 contract |
| `IDEA_BRAINSTORM/DEFINE` | 暂未实现；完整 artifact_data 到齐时 before-final delta | `test_runtime_raw_json_stream_turn_renders_idea_define_artifact_data_before_final_output` | Mermaid mindmap、问题域 contract |
| `IDEA_BRAINSTORM/DIVERGE` | 暂未实现；完整 artifact_data 到齐时 before-final delta | `test_runtime_raw_json_stream_turn_renders_idea_diverge_artifact_data_before_final_output` | Mermaid mindmap；`idea_landscape + idea_cards` 成对渲染 |
| `IDEA_BRAINSTORM/CONVERGE` | 暂未实现；完整 artifact_data 到齐时 before-final delta | `test_runtime_raw_json_stream_turn_renders_idea_converge_artifact_data_before_final_output` | Mermaid quadrantChart；`decision_matrix + ice_evaluations` 成对渲染 |
| `IDEA_BRAINSTORM/CONCEPT` | 暂未实现；完整 artifact_data 到齐时 before-final delta | `test_runtime_raw_json_stream_turn_renders_idea_concept_artifact_data_before_final_output` | Mermaid pie / flowchart、`mvp-map` |
| `VALUE_DISCOVERY/ELEVATOR` | 暂未实现；完整 artifact_data 到齐时 before-final delta | `test_runtime_raw_json_stream_turn_renders_value_elevator_artifact_data_before_final_output` | Mermaid flowchart、`score-matrix`；`score_matrix + score_summary` 成对渲染 |
| `VALUE_DISCOVERY/PERSONA` | 暂未实现；完整 artifact_data 到齐时 before-final delta | `test_runtime_raw_json_stream_turn_renders_value_persona_artifact_data_before_final_output` | 画像 / 行为 / 决策链；`personas` 提供映射 |
| `VALUE_DISCOVERY/JOURNEY` | 暂未实现；完整 artifact_data 到齐时 before-final delta | `test_runtime_raw_json_stream_turn_renders_value_journey_artifact_data_before_final_output` | Mermaid journey、`journey-map` |
| `VALUE_DISCOVERY/BLUEPRINT` | 暂未实现；完整 artifact_data 到齐时 before-final delta | `test_runtime_raw_json_stream_turn_renders_value_blueprint_artifact_data_before_final_output` | Mermaid mindmap / flowchart、`roadmap`、Lisa handoff 输入 |
| `STORY_BREAKDOWN/INPUT_ANALYSIS` | 暂未实现；完整 artifact_data 到齐时 before-final delta | `test_runtime_raw_json_stream_turn_renders_all_story_breakdown_stages_from_artifact_data` | 需求范围、需求追溯、阻塞问题、Mermaid flowchart |
| `STORY_BREAKDOWN/EPIC_MAPPING` | 暂未实现；完整 artifact_data 到齐时 before-final delta | `test_runtime_raw_json_stream_turn_renders_all_story_breakdown_stages_from_artifact_data` | Epic / Story Map、MVP slice、Mermaid flowchart |
| `STORY_BREAKDOWN/STORY_BACKLOG` | 暂未实现；完整 artifact_data 到齐时 before-final delta | `test_runtime_raw_json_stream_turn_renders_all_story_breakdown_stages_from_artifact_data` | 用户故事卡片、Ready / Not Ready 质量校验、storyId / requirementId 引用 |
| `STORY_BREAKDOWN/SPRINT_PLAN` | 暂未实现；完整 artifact_data 到齐时 before-final delta | `test_runtime_raw_json_stream_turn_renders_all_story_breakdown_stages_from_artifact_data` | Sprint 切片、Ready story handoff 清单、单故事需求包 JSON、AI Coding 输入边界 |
| `PRD_REVIEW/INVENTORY` | 暂未实现；完整 artifact_data 到齐时 before-final delta | artifact-data registry 参数化 raw JSON streaming 覆盖 | PRD 输入盘点、Mermaid mindmap、stage gate |
| `PRD_REVIEW/QUALITY_AUDIT` | 暂未实现；完整 artifact_data 到齐时 before-final delta | artifact-data registry 参数化 raw JSON streaming 覆盖 | PRD 质量评审、`score-matrix`、finding 引用 |
| `PRD_REVIEW/COMPLETION_PLAN` | 暂未实现；完整 artifact_data 到齐时 before-final delta | artifact-data registry 参数化 raw JSON streaming 覆盖 | PRD 补全建议、`action-board`、action/finding 引用 |
| `PRD_REVIEW/REVISION_BLUEPRINT` | 暂未实现；完整 artifact_data 到齐时 before-final delta | artifact-data registry 参数化 raw JSON streaming 覆盖 | PRD 修订蓝图、`roadmap`、验收标准和 handoff 输入 |

聚焦回归命令：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py::test_artifact_data_structured_output_instruction_puts_artifact_data_before_chat_for_visible_streaming -q
```

21 阶段 raw JSON streaming 回归：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_paragraph_level_clarify_artifact_data tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_paragraph_level_strategy_artifact_data tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_paragraph_level_cases_artifact_data tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_delivery_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_req_review_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_req_review_report_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_incident_timeline_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_incident_root_cause_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_incident_improvement_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_idea_define_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_idea_diverge_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_idea_converge_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_idea_concept_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_value_elevator_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_value_persona_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_value_journey_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_value_blueprint_artifact_data_before_final_output tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_renders_all_story_breakdown_stages_from_artifact_data -q
```

后端共享回归：

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_stream_services.py tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_agent_contracts.py -q
```

前端共享流式消费回归：

```bash
cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/llm.test.ts src/services/__tests__/chatService.test.ts src/components/__tests__/ArtifactPane.incrementalRender.test.tsx
```

### 后端服务与 API 层：`stream_services.py` / `routes.py`

职责：只做编排、异常映射和 typed SSE 输出，不承担模型修补。

必须覆盖：
- 成功事件必须是 typed `agent_turn`，且 mock 输出本身要满足当前阶段契约。
- `run_started` 可以携带 `runId`，endpoint 层必须证明同一 typed SSE 主链路会创建或复用服务端 run。
- `GET /api/agent/runs/{runId}` 必须返回 JSON snapshot，未知 run ID 返回 JSON 404，不能泄露 Flask HTML 404/500。
- PydanticAI 输出失败必须映射为 typed `error`，不能泄露 HTML 500。
- 结构化输出、contract、request、runtime 和 provider 失败必须在 typed `error.diagnostic` 中暴露脱敏的 `phase`、`workflowId`、`stageId`、`fieldPath`、`validator`、`retryable` 和 `publicReason`；失败仍必须显式暴露，不能持久化为正式 artifact 或推进阶段。
- 注入 runtime 的 system prompt 必须包含 artifact 更新契约和 chat/artifact 分离契约。
- API 测试要解析 SSE JSON，分别断言 `chat` 与 `artifact_update.markdown`，避免用字符串包含掩盖字段混用。

典型测试文件：
- `tools/new-agents/backend/tests/test_stream_services.py`
- `tools/new-agents/backend/tests/test_agent_endpoint.py`

### 后端持久化层：`models.py` / `run_persistence.py`

职责：为后续会话恢复、审计、分享和 judge 数据采集提供通用 run/session/message/artifact version 数据源，不改变 typed SSE 主链路。

必须覆盖：
- `agent_runs` 保存通用 workflow、agent、current stage、status 和 model 元数据。
- `agent_messages` 对同一 run 使用稳定递增 `sequence_index`。
- `agent_artifacts` 对同一 run/stage 只有一个当前 artifact 容器。
- `agent_artifact_versions` 对同一 artifact 追加版本，并维护当前版本指针。
- 结构化 `artifact_data` 阶段的正式 artifact version 必须持久化规范化后的 `artifactData`，并能在 snapshot 中恢复；后续 packet / handoff 不能依赖 Markdown 反解析。
- repository 复用 `WORKFLOW_STAGES` 拒绝未知 workflow/stage，拒绝未知 message role。
- `ensure_agent_run` 复用已有 `runId` 时必须校验 workflow/agent，并更新当前阶段和模型。
- snapshot 返回有序消息、当前 artifact 内容和可选 `artifactData`，供后续 API、恢复、packet 生成和 judge 读取。
- turn metric 必须持久化脱敏 error diagnostic，并在 `GET /api/agent/observability` 的 `recentTurns[].diagnostic` 中返回，供 Header 运行统计定位失败字段和 validator。

典型测试文件：`tools/new-agents/backend/tests/test_run_persistence.py`

### Workflow Handoff 层：`workflow_handoffs.py` / `workflowHandoffService.ts` / `ChatPane.tsx`

职责：用持久化 run、artifact version 和 manifest 配置完成工作流之间的可追溯承接，不改变共享 Agent Runtime 主链路。

必须覆盖：
- source-side handoff：已有 source run 产出指定 stage artifact 后，`GET /api/agent/runs/{runId}/handoffs` 返回配置化下游目标。
- target-side handoff：目标 workflow 空会话启动时，`GET /api/agent/workflow-handoff-candidates` 能按 target workflow/stage 返回可继承的上游 run、source stage、artifact version、digest、summary 和 prompt。
- `start_workflow_handoff` 必须创建目标 run，并把 source run、source workflow/stage、artifact version 和 digest 写入目标 run 第一条 user message，形成可恢复追溯。
- 无上游 artifact 时返回空候选，不伪造 prompt 或目标 run。
- 未知 workflow、stage mismatch 或未知 handoff 必须显式 JSON 失败。
- 前端进入 Alex `VALUE_DISCOVERY/ELEVATOR` 或 `STORY_BREAKDOWN/INPUT_ANALYSIS` 空会话时必须展示“开启新话题 / 基于已有内容继续”选择；无候选时仍允许开启新话题。
- 选择候选后必须通过既有 `POST /api/agent/runs/{sourceRunId}/handoffs/{handoffId}/start` 创建目标 run，并继续使用共享 `/api/agent/runs/stream`。
- 修改共享 handoff 能力时，必须回归 Alex `IDEA_BRAINSTORM/CONCEPT -> VALUE_DISCOVERY/ELEVATOR`、Alex `VALUE_DISCOVERY/BLUEPRINT -> STORY_BREAKDOWN/INPUT_ANALYSIS` 和既有 `VALUE_DISCOVERY/BLUEPRINT -> Lisa` 路径。

典型测试文件：
- `tools/new-agents/backend/tests/test_workflow_handoffs.py`
- `tools/new-agents/backend/tests/test_agent_endpoint.py`
- `tools/new-agents/frontend/src/services/__tests__/workflowHandoffService.test.ts`
- `tools/new-agents/frontend/src/components/__tests__/ChatPane.test.tsx`
- `tools/new-agents/frontend/src/__tests__/store.test.ts`
- `tests/e2e/new_agents_browser/test_alex_user_story_breakdown_workflow.py`
- `tests/e2e/new_agents_browser/test_alex_value_discovery_workflow.py`

### Story Handoff Packet 层：`story_handoff_packets.py` / `storyHandoffPacketService.ts` / `ArtifactPane.tsx`

职责：把 Alex `STORY_BREAKDOWN/SPRINT_PLAN` 的单张 ready story 转成可保存、可恢复、可复制的 AI Coding 需求输入；该层不创建真实 AI Coding workflow，也不复用 workflow start handoff prompt。

必须覆盖：
- 候选查询只能读取 `STORY_BREAKDOWN/SPRINT_PLAN` 当前 artifact version 的结构化 `artifactData`，不得从 Markdown 反解析用户故事。
- 创建 packet 必须持久化 `sourceRunId`、`sourceWorkflowId`、`sourceStageId`、`sourceArtifactVersion`、`sourceArtifactDigest`、`storyId` 和 `requirementIds` 等追溯字段。
- packet payload 只能包含需求信息和追溯信息；不得包含 task、file path、implementation plan、test command 或 architecture plan。
- 当前 artifact version 或 digest 与已保存 packet 不一致时，API 和前端必须能标记 stale，提示“源需求已更新”。
- 缺少 artifactData、未知 story、非 `SPRINT_PLAN` stage 或非 `STORY_BREAKDOWN` run 必须显式失败，不生成假 packet。
- ArtifactPane 必须能加载 ready story 候选、触发生成、显示 packet 摘要并复制完整 packet 内容。
- 浏览器级 mock E2E 至少覆盖 `STORY_BREAKDOWN` 最终阶段生成和复制单故事需求包，并覆盖 `VALUE_DISCOVERY/BLUEPRINT -> STORY_BREAKDOWN/INPUT_ANALYSIS -> 单故事 packet` 全链路证据。

典型测试文件：
- `tools/new-agents/backend/tests/test_story_handoff_packets.py`
- `tools/new-agents/frontend/src/services/__tests__/storyHandoffPacketService.test.ts`
- `tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`
- `tests/e2e/new_agents_browser/test_alex_user_story_breakdown_workflow.py`

### 后端上下文构建层：`context_builder.py`

职责：在已有服务端 run 的情况下，用持久化消息构造模型上下文，逐步替代前端本地历史拼接。

必须覆盖：
- 无历史消息时返回当前用户输入，保持首轮行为轻量。
- 按 `sequenceIndex` 注入历史 user/assistant 消息。
- 过滤助手控制反馈和错误反馈，避免把失败 UI 文案喂回模型。
- 将已保存 current artifact 以 bounded 摘要形式注入上下文，帮助后续阶段使用前序产物。
- `record_artifact_version` 必须 upsert `agent_context_summaries` 中的 current artifact summary，`get_run_snapshot` 必须返回 `contextSummaries`。
- context builder 必须优先使用持久化 `contextSummaries`，旧数据缺 summary 时才从 current artifact 回退生成。
- 单个 artifact 过长时必须在 artifact 摘要内标明截断，不能让原文无限扩张 prompt。
- 超过上下文预算时丢弃最旧消息，并在 prompt 中保留截断说明。
- 上下文截断必须通过 `run_started.warnings=["context_truncated"]` 暴露给前端，不得混用 artifact truncation 状态。
- `stream_services.py` 使用 context builder 产物调用 runtime，而不是直接使用前端拼接历史。

典型测试文件：`tools/new-agents/backend/tests/test_context_builder.py`

### 前端 LLM 流解析层：`core/llm.ts`

职责：消费 typed SSE，把 `agent_turn.output.chat` 转成左侧渐进文本，把 `artifact_update.markdown` 转成右侧产物更新。

必须覆盖：
- 只调用 `/new-agents/api/agent/runs/stream`，不回退旧 `/chat/stream`。
- `run_started.runId` 到达后写入前端 workspace state，后续请求带回 `runId` 以复用服务端 run。
- `run_started.warnings=["context_truncated"]` 到达后，左侧对话首帧必须显示上下文截断提示。
- 已有 `currentRunId` 时，前端请求 prompt 只包含当前用户输入和附件内容，不再注入本地聊天历史。
- 单个 `agent_turn` 的长 chat 会渐进拆分，但最终 chunk 才携带 artifact 更新。
- 如果历史后端或异常 SSE 发送 `# 产出物生成中`、字符数、字段名等进度占位，前端 parser 必须忽略该 artifact delta，并在最终正式 artifact 到达时继续渐进揭示。
- artifact 中 Mermaid 语法错误时拒绝写入右侧。
- SSE `error` 事件直接抛出用户可见错误。
- SSE `error.diagnostic` 必须被解析并随 typed error 传给上层服务，不得退化为只能字符串匹配的普通 `Error`。

典型测试文件：`tools/new-agents/frontend/src/core/__tests__/llm.test.ts`

### 前端状态编排层：`chatService.ts` / `agentCore.ts`

职责：决定左侧消息、右侧 artifact、阶段推进状态分别写入哪里。

必须覆盖：
- assistant 消息只写 `chatResponse`，不能把 `newArtifact` 拼进左侧对话。
- `hasArtifactUpdate=true` 时只更新当前阶段 artifact。
- `NEXT_STAGE` 只设置待确认推进，不直接写入未确认下一阶段产物。
- 用户确认阶段推进时保存来源阶段 artifact，并载入目标阶段 artifact。

典型测试文件：
- `tools/new-agents/frontend/src/services/__tests__/chatService.test.ts`
- `tools/new-agents/frontend/src/core/__tests__/agentCore.test.ts`

### 真实模型冒烟层：`test_agent_real_smoke.py`

职责：少量验证真实模型与 PydanticAI/供应商兼容性，不替代确定性单元测试。

必须覆盖：
- 真实模型能返回合法 `AgentTurnOutput`。
- `artifact_update.markdown` 包含阶段必需标题。
- `chat` 不包含 artifact Markdown 结构。
- 仅在显式提供 `NEW_AGENTS_SMOKE_*` 环境变量时运行，避免普通测试依赖外部网络和额度。

## New Agents 策略符合性审计清单

当智能体链路发生重构、模型供应商切换、输出协议变更或 UI 左右栏行为变化时，必须逐项审计：

| 审计项 | 通过标准 | 主要测试文件 |
|--------|----------|--------------|
| 字段职责分离 | `chat` 不承载 artifact；`artifact_update.markdown` 承载完整 Markdown | `test_agent_contracts.py`, `chatService.test.ts` |
| 阶段产物完整性 | 有模板的阶段必须 `replace` 并包含必需标题 | `test_agent_contracts.py` |
| Workflow 配置同步 | `workflow_manifest.json`、后端 `WORKFLOW_STAGES` 和 artifact contract stage keys 保持一致 | `test_workflow_contract_sync.py` |
| Mermaid 可视化契约 | 每个核心 workflow 至少一个关键阶段要求适配的 Mermaid 图类型 | `test_agent_contracts.py`, `mermaid.test.ts` |
| 阶段推进安全 | 只能请求合法下一阶段；前端只设置待确认推进 | `test_agent_contracts.py`, `agentCore.test.ts`, `chatService.test.ts` |
| SSE 契约稳定 | 成功/错误事件都是 typed SSE；API 测试解析 JSON 字段 | `test_stream_services.py`, `test_agent_endpoint.py`, `test_sse_encoder.py` |
| 供应商兼容性 | DeepSeek/OpenAI 等模型特定设置有单测；真实冒烟可选运行 | `test_agent_runtime.py`, `test_agent_real_smoke.py` |
| 前端写入边界 | assistant message 只来自 `chatResponse`；artifact 只来自 `newArtifact` | `llm.test.ts`, `chatService.test.ts`, `agentCore.test.ts` |
| 左侧 Markdown 可读性 | `ChatPane` 长回复保留列表、强调、链接和代码样式，但不承载完整 artifact | `ChatPane.markdown.test.tsx`, `markdownCodeRenderer.test.tsx` |
| 旧协议清理 | 前端不再调用旧 `/api/chat/stream`，不保留 `<CHAT>/<ARTIFACT>` 协议 | `testHygiene.test.ts` |

## New Agents 浏览器工作流测试

New Agents 另有一套独立于 intent-tester/MidScene 的浏览器级工作流测试，位于 `tests/e2e/new_agents_browser/`。它使用 Python Playwright 打开真实 React 前端，通过 mock typed SSE 响应验证 Lisa `test-design` 和 Alex `value-discovery` 的完整阶段组织逻辑。`workflow_runner.py` 返回结构化 `WorkflowRunResult`，包含 `final_artifact`、`stage_artifacts`、`conversation_events` 和 `stage_transitions`，供确定性断言和可选 LLM judge 共用。

默认确定性运行：

```bash
python3 -m pytest -o addopts='' tests/e2e/new_agents_browser -m e2e -q
```

可选 LLM judge 运行：

```bash
NEW_AGENTS_E2E_LLM_JUDGE=1 \
NEW_AGENTS_E2E_JUDGE_API_KEY=<api-key> \
NEW_AGENTS_E2E_JUDGE_BASE_URL=https://api.deepseek.com \
NEW_AGENTS_E2E_JUDGE_MODEL=deepseek-v4-flash \
python3 -m pytest -o addopts='' tests/e2e/new_agents_browser -m e2e -q
```

不要把 API key 写入仓库。默认测试不需要模型网络调用。

可选 LLM judge 要求模型只返回严格 JSON verdict，至少包含 `pass`、`score`、`dimension_scores`、`issues`、`evidence` 和 `recommendations`。Lisa judge 侧重测试专家维度，Alex judge 侧重业务分析师维度，两者都包含交互体验和可视化维度。启用、要求或引用 LLM judge 时，默认通过线为 `score >= 80`；低于 80 是质量门失败，必须分析差距并修复后重跑，不能用关闭 judge 的确定性测试替代。未启用 judge 时，只能声称确定性链路通过，不能声称真实模型质量评分。

## 测试标记 (pytest)

```bash
pytest -m unit        # 仅单元测试
pytest -m api         # 仅 API 测试
pytest -m integration # 集成测试
pytest -m "not slow"  # 跳过慢速测试
```
