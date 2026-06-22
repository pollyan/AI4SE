# DeepSeek V4 TEST_DESIGN/STRATEGY 结构化产物数据设计

## 背景

上一轮已经把 `TEST_DESIGN/CLARIFY` 从“模型直接输出完整 Markdown”改为“模型输出 `artifact_data`，后端校验并确定性渲染 artifact”。当前 `TEST_DESIGN/STRATEGY` 仍要求 DeepSeek V4 Flash 在 JSON 字符串中拼完整 Markdown、Mermaid `quadrantChart`、Mermaid `block-beta` 和 `ai4se-visual` risk-board。该阶段格式面更复杂，是 DeepSeek JSON mode 下继续降低产物失败率的最高价值相邻切片。

本轮继续复用共享 Agent Runtime、typed SSE、workflow manifest、artifact contract、持久化 run/artifact 模型和共享 UI。前端协议仍接收 `AgentTurnOutput.artifact_update.markdown`，不会新增 DeepSeek 或 Lisa 专属 API、store、runtime 或 renderer。

## 用户故事

作为使用 Lisa 生成测试策略的测试负责人，当我在 `TEST_DESIGN/CLARIFY` 后进入 `STRATEGY` 阶段时，我希望 DeepSeek V4 只负责输出测试策略业务数据，由后端稳定生成《测试策略蓝图》、风险矩阵、测试金字塔和 risk-board，从而减少 Markdown/Mermaid/visual 格式不完整导致的生成失败，并能继续进入用例编写。

## 范围

纳入本轮：

- 为 `TEST_DESIGN/STRATEGY` 定义严格 Pydantic `artifact_data` schema。
- 后端确定性渲染完整《测试策略蓝图》 Markdown。
- 渲染 `quadrantChart` 风险矩阵、`block-beta` 测试金字塔和 `ai4se-visual` risk-board。
- Runtime 对 `TEST_DESIGN/STRATEGY` 使用 `artifact_data` 输出指令和 schema 纠错 retry 文案。
- 保持 DeepSeek V4 capability 为 `json_object_only`，仍只发送 `response_format={"type":"json_object"}`。
- 增加 TDD 测试，证明 schema 校验、确定性渲染、contract validation、runtime parse/retry 均覆盖该阶段。
- 更新 DeepSeek todo 当前进展。

不纳入本轮：

- `TEST_DESIGN/CASES`、`TEST_DESIGN/DELIVERY` 或其它 workflow 的迁移。
- 持久化原始 `artifact_data`。
- 前端 typed SSE、store、ArtifactPane 或 renderer 协议变更。
- 真实 DeepSeek V4 网络 smoke；该验证需要显式凭证、网络和额度。

## 数据契约

`TEST_DESIGN/STRATEGY` 的 `artifact_data` 必须包含：

- `document_info`: artifact 名称、workflow、stage、策略状态。
- `strategy_summary`: 策略结论、依据、进入用例阶段判断。
- `quality_goals`: 质量目标列表。
- `risks`: FMEA 风险列表，包含 S/O/D 与 RPN。
- `test_techniques`: 测试技术选型。
- `test_layers`: 测试分层策略。
- `test_points`: 测试点拓扑。
- `tradeoffs`: 资源与取舍。
- `stage_gate`: 阶段门禁检查项。

所有字符串必须非空；关键列表必须至少一项；未知字段必须拒绝；RPN 必须等于 `severity * occurrence * detection`；风险坐标由后端根据 S/O/D 确定性归一化。

## 渲染契约

renderer 输出必须包含现有 `REQUIRED_ARTIFACT_HEADINGS[("TEST_DESIGN", "STRATEGY")]` 的所有标题和关键词，并满足现有 visual contract：

- Mermaid `quadrantChart`。
- Mermaid `block-beta`。
- `ai4se-visual` fenced block，`type` 为 `risk-board`。

renderer 输出继续通过 `validate_agent_turn()` 作为最终守门。前端和持久化层只看到既有 Markdown artifact，不需要理解 `artifact_data`。

## 失败处理

当模型返回缺字段、空字符串、空列表、未知字段、非法 RPN 或 renderer/contract 不合格时：

- raw JSON streaming 尝试有限 retry。
- retry prompt 明确要求修正 `artifact_data` 数据，而不是重写完整 Markdown。
- 最终仍失败时抛出 schema/contract 错误，不伪造 artifact，不静默降级。

## 验收条件

1. Given `TEST_DESIGN/STRATEGY` 收到合法 `artifact_data`
   When 后端解析 raw JSON
   Then 返回 `AgentTurnOutput`，其中 artifact Markdown 包含策略蓝图、风险矩阵、测试金字塔、risk-board 和阶段门禁，并通过 `validate_agent_turn()`。

2. Given `TEST_DESIGN/STRATEGY` 收到非法 `artifact_data`
   When 字段为空、列表为空、未知字段或 RPN 不一致
   Then Pydantic 校验失败，错误可定位到字段路径。

3. Given DeepSeek raw JSON streaming 处于 `TEST_DESIGN/STRATEGY`
   When 第一次输出不合格
   Then retry prompt 要求修正 `artifact_data`，并保持 JSON object 输出约束。

4. Given 其它 workflow/stage
   When 构建结构化输出指令
   Then 未迁移阶段继续使用既有 Markdown JSON contract。

## 验证计划

- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py -q`
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_agent_contracts.py tools/new-agents/backend/tests/test_agent_endpoint.py tools/new-agents/backend/tests/test_stream_services.py -q`
- `.venv/bin/python -m py_compile tools/new-agents/backend/agent_runtime.py tools/new-agents/backend/artifact_data_renderers.py`
- `git diff --check -- <本轮文件>`

## 风险

- STRATEGY schema 较 CLARIFY 更宽，字段过细会增加模型填充难度。本轮只定义策略阶段当前 artifact contract 必需的数据，不引入跨阶段完整测试设计模型。
- `risk-board` JSON 必须稳定，但不能改变前端 visual renderer contract；因此 renderer 输出沿用现有 fenced `ai4se-visual` 形态。
- 真实 DeepSeek 输出质量仍需后续 smoke 验证，本轮本地测试只能证明后端 contract 和失败边界。
