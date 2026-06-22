# DeepSeek V4 价值定位结构化产物数据设计

## 背景

DeepSeek V4 Flash 当前适合通过 JSON mode 输出合法 JSON，但不能等同于供应商 strict Structured Outputs。`TEST_DESIGN` 和 `REQ_REVIEW` 已经迁移为模型输出 `artifact_data`、后端校验并确定性渲染 Markdown/Mermaid/`ai4se-visual`。`VALUE_DISCOVERY/ELEVATOR` 仍要求模型直接拼完整 Markdown、Mermaid `flowchart` 和 `score-matrix`，容易出现格式缺失、fence 损坏或结构化 visual 不合规。

本轮只迁移 `VALUE_DISCOVERY/ELEVATOR`，作为 Alex workflow 的首个 DeepSeek 结构化产物切片。它必须继续复用共享 Agent Runtime、typed SSE、workflow manifest、artifact contract、持久化 run/artifact 模型和共享 UI，不新增 Alex 或 DeepSeek 专属 runtime/API/store/renderer。

## 用户故事

作为使用 Alex 价值发现的用户，当我输入产品方向并使用 DeepSeek V4 Flash 生成价值定位分析时，我希望模型只输出结构化业务数据，由后端稳定渲染《价值定位分析》、价值结构图和评分矩阵，从而降低格式不完整导致的生成失败，并能继续进入用户画像阶段。

## 范围

纳入本轮：

- `VALUE_DISCOVERY/ELEVATOR` 的 `artifact_data` Pydantic schema。
- 后端 deterministic renderer，输出现有 artifact contract 要求的标题、Markdown 表格、Mermaid `flowchart`、`ai4se-visual` `score-matrix` 和阶段门禁。
- Runtime structured output instruction 与 retry prompt 路径接入，让 DeepSeek JSON mode 要求输出 `artifact_data` 而不是最终 Markdown。
- 后端测试覆盖 schema 校验、renderer contract、runtime parse、instruction、retry 和 raw JSON streaming。
- 更新 DeepSeek todo 当前进展和剩余迁移范围。

不纳入本轮：

- `VALUE_DISCOVERY/PERSONA/JOURNEY/BLUEPRINT` 迁移。
- `IDEA_BRAINSTORM`、`INCIDENT_REVIEW` 迁移。
- 前端协议、UI、store 或 API path 变更。
- 真实 DeepSeek V4 Flash smoke；它需要外部凭证、网络和额度，保留为可选人工验证。

## 产物数据模型

`artifact_data` 采用 stage-specific schema，字段面向价值定位业务语义：

- `document_info`: artifact 名称、workflow、stage、状态。
- `positioning_summary`: 一句话定位、核心用户、核心痛点、独特价值、当前判断。
- `value_flow`: value structure graph 的节点和有向连线，后端渲染 Mermaid `flowchart TD`。
- `target_scenarios`: 目标用户、核心场景、现有应对方式、现有方案不足，带证据等级和状态。
- `pain_evidence`: 痛点 ID、描述、场景、影响、证据等级、验证动作和状态。
- `differentiators`: 我们、现有方案、差异化证据和状态。
- `business_feasibility`: 付费意愿、商业模式、市场规模感知等判断。
- `score_matrix`: 痛点强度、目标用户清晰度、差异化、付费意愿、证据强度等评分项。
- `score_summary`: 总分、平均分、判断，用于跨字段一致性校验。
- `assumptions`: 未验证假设、影响范围、验证动作、责任方和状态。
- `elevator_pitch`: 60 秒电梯演讲稿。
- `stage_gate`: 阶段门禁检查项。

强校验规则：

- 所有字符串必须非空，所有业务数组至少一项。
- `score_matrix.score` 必须为 1 到 5 的整数。
- `score_summary.total_score` 必须等于所有评分之和。
- `score_summary.average_score` 必须等于评分平均值，允许两位小数表示。
- `value_flow.links` 只能引用已存在的节点 ID。

## 渲染要求

renderer 必须确定性生成：

- `# 价值定位分析`
- `## 定位摘要`
- `## 价值结构图`
- Mermaid `flowchart TD`
- `## 目标用户与场景`
- `## 痛点证据`
- `## 差异化价值`
- `## 商业可行性`
- fenced `ai4se-visual` `score-matrix`
- `## 未验证假设`
- `## 60 秒电梯演讲`
- `## 阶段门禁`

输出必须通过 `validate_agent_turn()` 对 `VALUE_DISCOVERY/ELEVATOR` 的 required headings、Mermaid 和 structured visual contract 校验。

## 验收条件

1. Given 合法 `VALUE_DISCOVERY/ELEVATOR` `artifact_data`，When `render_agent_turn_from_artifact_data()` 执行，Then 输出 deterministic `AgentTurnOutput`，artifact 通过 `validate_agent_turn()`，并包含 `flowchart TD` 与 `"type": "score-matrix"`。
2. Given `score_summary` 与 `score_matrix` 不一致，When schema 校验执行，Then 抛出明确 validation error，不进入 renderer。
3. Given `value_flow.links` 引用未知节点，When schema 校验执行，Then 抛出明确 validation error。
4. Given runtime 解析包含 `artifact_data` 的 raw JSON，When workflow/stage 为 `VALUE_DISCOVERY/ELEVATOR`，Then 返回后端渲染 artifact，并继续保留 `stage_action.target_stage_id = "PERSONA"`。
5. Given DeepSeek V4 raw streaming，When system prompt 构造，Then instruction 要求输出 `artifact_data`、禁止 Markdown/Mermaid/表格，并包含 `score_matrix`、`value_flow` 和 `target_stage_id: "PERSONA"`。
6. Given artifact_data 校验失败，When retry prompt 构造，Then 要求修正 `artifact_data` 数据问题，而不是重写 Markdown。

## 风险

- `artifact_data_renderers.py` 已经承担多个 stage renderer，本轮只追加同类 stage，不做文件拆分，避免扩大风险。
- 现有 artifact contract 对 ELEVATOR 要求中文关键词和 visual 类型，renderer 必须逐项满足，不能依赖 prompt 兜底。
- 真实 DeepSeek 输出质量仍受模型影响；本轮只保证本地 schema、renderer、runtime 和 contract 闭环。

## 验证计划

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py -q`
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_agent_contracts.py tools/new-agents/backend/tests/test_agent_endpoint.py tools/new-agents/backend/tests/test_stream_services.py -q`
- `.venv/bin/python -m py_compile tools/new-agents/backend/agent_runtime.py tools/new-agents/backend/artifact_data_renderers.py`
- `git diff --check`
