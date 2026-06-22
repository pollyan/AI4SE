# DeepSeek V4 用户画像结构化产物数据设计

## 背景

`VALUE_DISCOVERY/ELEVATOR` 已迁移为模型输出 `artifact_data`、后端校验并确定性渲染。用户在 Alex 价值发现中的下一步是 `PERSONA` 用户画像阶段，但当前仍要求模型直接输出最终 Markdown。该阶段包含多层标题和多张表格，DeepSeek V4 Flash JSON mode 虽能保证合法 JSON，却不能保证最终 Markdown 表格、标题和阶段门禁稳定完整。

本轮迁移 `VALUE_DISCOVERY/PERSONA`，继续复用共享 Agent Runtime、typed SSE、workflow manifest、artifact contract、run/artifact persistence 和共享 UI，不新增 Alex、DeepSeek 或未来 agent 专属 runtime/API/store/renderer。

## 用户故事

作为 Alex 价值发现用户，当我完成价值定位并进入用户画像阶段时，我希望 DeepSeek V4 Flash 只输出结构化画像数据，由后端稳定生成《用户画像分析》，从而能继续进入用户旅程阶段，而不被 Markdown 表格缺失、标题缺失或画像引用不一致阻断。

## 范围

纳入本轮：

- `VALUE_DISCOVERY/PERSONA` 的 Pydantic `artifact_data` schema。
- 后端 deterministic renderer，生成当前 contract 要求的标题、画像摘要、主要用户画像、行为与场景、决策链、痛点证据、反画像、用户优先级排序和阶段门禁。
- Runtime structured output instruction、support registry 和 artifact_data retry 路径接入。
- 后端测试覆盖 schema 跨字段失败、renderer contract、runtime parse、instruction、retry 和 DeepSeek raw JSON streaming。
- 更新 DeepSeek todo 当前进展和剩余迁移范围。

不纳入本轮：

- `VALUE_DISCOVERY/JOURNEY`、`VALUE_DISCOVERY/BLUEPRINT` 迁移。
- `IDEA_BRAINSTORM`、`INCIDENT_REVIEW` 迁移。
- 前端协议、UI、store 或 API path 变更。
- 真实 DeepSeek V4 Flash smoke；它需要外部凭证、网络和额度，保留为可选人工验证。

## 产物数据模型

`artifact_data` 使用 stage-specific schema：

- `document_info`: artifact 名称、workflow、stage、状态。
- `persona_summary`: 核心用户判断、主要痛点、验证状态、进入旅程阶段判断。
- `personas`: 一个或多个用户画像，每个画像包含：
  - `persona_id`、`name`、`priority`、`summary`。
  - `basic_features`: 用户类型、人口/企业属性、技术水平、决策角色等。
  - `behavior_features`: 日常模式、信息来源、决策模式、工具习惯等。
- `behavior_scenarios`: 画像关联场景。
- `decision_chain`: 使用者、决策者、付费者等角色。
- `pain_evidence`: 画像关联痛点。
- `anti_personas`: 非目标用户和不服务边界。
- `priority_ranking`: 核心用户、重要用户、潜在用户排序。
- `stage_gate`: 阶段门禁检查项。

强校验规则：

- 所有字符串必须非空；所有业务数组至少一项。
- `persona_id` 必须唯一。
- `behavior_scenarios.persona_id`、`decision_chain.persona_id`、`pain_evidence.persona_id`、`priority_ranking.persona_id` 必须引用已存在 persona。
- `priority_ranking.persona_id` 不能重复，避免同一画像被排入多个优先级。

## 渲染要求

renderer 必须确定性生成：

- `# 用户画像分析`
- `## 画像摘要`
- `## 主要用户画像`
- 至少一个 `### 画像 1`
- `#### 基础特征`
- `#### 行为特征`
- `## 行为与场景`
- `## 决策链`
- `## 痛点证据`
- `## 反画像`
- `## 用户优先级排序`
- `## 阶段门禁`

输出必须通过 `validate_agent_turn()` 对 `VALUE_DISCOVERY/PERSONA` 的 required headings 校验，并保留 `证据等级`、`验证状态` 等关键词。

## 验收条件

1. Given 合法 `VALUE_DISCOVERY/PERSONA` `artifact_data`，When renderer 执行，Then 输出 deterministic `AgentTurnOutput`，artifact 通过 `validate_agent_turn()`，并请求下一阶段 `JOURNEY`。
2. Given 场景、决策链、痛点证据或优先级引用未知 persona，When schema 校验执行，Then 抛出明确 validation error，不进入 renderer。
3. Given 同一 persona 被重复排入优先级，When schema 校验执行，Then 抛出明确 validation error。
4. Given runtime 解析包含 PERSONA `artifact_data` 的 raw JSON，When workflow/stage 为 `VALUE_DISCOVERY/PERSONA`，Then 返回后端渲染 artifact，并保留 `stage_action.target_stage_id = "JOURNEY"`。
5. Given DeepSeek V4 raw streaming，When system prompt 构造，Then instruction 要求输出 `artifact_data`、禁止完整 Markdown/表格，并包含 `personas`、`decision_chain`、`priority_ranking` 和 `target_stage_id: "JOURNEY"`。
6. Given `artifact_data` 校验失败，When retry prompt 构造，Then 要求修正 `artifact_data` 数据问题，而不是重写 Markdown。

## 风险

- `artifact_data_renderers.py` 继续增长；本轮按既有模式追加 stage-specific schema/renderer，不做跨阶段拆分，避免扩大风险。
- `PERSONA` 没有 visual contract，主要风险来自 Markdown 多层标题和表格稳定性；后端 renderer 必须覆盖全部 required headings。
- 真实模型可能给出低质量画像；本轮保证结构、引用和输出格式稳定，不替代真实用户研究。

## 验证计划

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py -q`
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_agent_contracts.py tools/new-agents/backend/tests/test_agent_endpoint.py tools/new-agents/backend/tests/test_stream_services.py -q`
- `/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m py_compile tools/new-agents/backend/agent_runtime.py tools/new-agents/backend/artifact_data_renderers.py`
- `git diff --check`
