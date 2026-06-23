# DeepSeek V4 全 Workflow Readiness 收口设计

## 背景

当前 New Agents 已经把 Lisa、Alex 的在线 workflow 逐步迁移到 `artifact_data`：模型输出业务 JSON，后端 Pydantic schema 校验并确定性渲染 Markdown、Mermaid 和 `ai4se-visual`。上一轮新增了 `PRD_REVIEW` 与 `STORY_BREAKDOWN`，但当前基线还缺少一个全局 readiness 门禁来证明所有 manifest stage 都继续满足 DeepSeek V4 Flash 的 `json_object_only` 约束。

DeepSeek V4 Flash 不能被当作 OpenAI strict Structured Outputs 使用。可靠边界必须是：只要求模型返回合法 JSON object，后端负责字段完整性、跨字段一致性、renderer 和 artifact contract。

## 用户故事

作为 New Agents 的维护者，我希望有一个确定性 readiness 门禁，证明当前所有在线 workflow stage 在 DeepSeek V4 Flash 路径下都走 `artifact_data`、Pydantic schema、后端 renderer 和 artifact contract，而不是让模型直接拼完整 Markdown 文档。这样以后新增 workflow 或 stage 时，如果没有同步 structured renderer、fixture、runtime instruction 或 DeepSeek JSON mode，测试会立即失败。

## 范围

纳入本轮：

- 新增 `tools/new-agents/backend/tests/test_deepseek_v4_readiness.py`。
- 覆盖所有 `workflow_manifest.json` 中的 workflow/stage，包括 `PRD_REVIEW` 和 `STORY_BREAKDOWN`。
- 新增 renderer stage key 查询 helper，供 readiness test 证明 renderer 覆盖与 manifest 对齐。
- 验证每个 stage 的 fixture 能通过 `render_agent_turn_from_artifact_data()` 与 `validate_agent_turn()`。
- 验证每个 stage 的 `build_structured_output_instruction()` 要求 `artifact_data`，不要求 `artifact_update.markdown`，且包含禁止直接输出完整 Markdown 的约束。
- 验证 DeepSeek V4 Flash capability 为 `json_object_only`、请求 `response_format={"type":"json_object"}`、thinking disabled。
- 验证 raw streaming runtime 对每个 stage 都能把 DeepSeek JSON object fixture 转成 typed SSE final artifact。
- 更新 DeepSeek todo 与 refactor README，记录本轮 readiness 收口。

不纳入本轮：

- 不调用真实 DeepSeek V4 Flash；真实 smoke 需要凭证、网络和额度。
- 不新增 provider 专属 runtime、API path、store 或 renderer。
- 不改变 typed SSE schema、run/artifact persistence 或前端协议。
- 不做 Artifact 质量诊断 UI、Lisa 测试资产质量闭环或 Handoff UI 增强。

## 设计

### Readiness 覆盖

测试从 `workflow_manifest.json` 读取全部 stage keys，并断言：

- `get_artifact_data_ready_stages()` 等于 manifest stage keys。
- `get_artifact_data_renderer_stage_keys()` 等于 manifest stage keys。
- `ARTIFACT_DATA_FIXTURES` 等于 manifest stage keys。

这样新增 workflow/stage 时，如果只改 manifest 或只改 prompt，readiness 会失败。

### Runtime 边界

每个 stage 都必须返回 artifact_data instruction：

- 包含 `artifact_data`。
- 不包含 `artifact_update.markdown`。
- 包含“不要输出完整 Markdown”。

DeepSeek V4 Flash 的 provider capability 必须保持：

- `tier == "json_object_only"`。
- `response_format == {"type": "json_object"}`。
- `build_model_settings()` 返回 thinking disabled。

### Renderer 边界

每个 stage 使用同一份测试 fixture 经过 renderer，输出必须通过 `validate_agent_turn()`。这验证 schema、renderer 和 artifact contract 的闭环，而不是只验证 helper 返回值。

### Raw Streaming 边界

测试 monkeypatch `stream_chat_completion_content()`，模拟 DeepSeek JSON mode 分片返回完整 JSON object。`PydanticAgentRuntime.stream_turn()` 必须：

- 给 DeepSeek 调用传递 `response_format={"type":"json_object"}`。
- 给 DeepSeek 调用传递 `extra_body={"thinking":{"type":"disabled"}}`。
- 在 system prompt 中包含 artifact_data instruction。
- 最终输出 typed SSE artifact delta，且 artifact markdown 非空。

## 验收条件

- 新增 readiness test 在实现前失败，失败原因是缺少 readiness test 依赖的 renderer stage key helper 或 PRD/Story fixture 覆盖。
- 实现后 readiness test 全部通过。
- 现有 `test_agent_runtime.py`、`test_artifact_data_renderers.py`、workflow contract sync/registry/handoff tests 继续通过。
- DeepSeek todo 明确记录当前所有在线 workflow stage 已纳入 readiness 门禁，真实 DeepSeek smoke 仍为可选外部验证。
- 不引入 DeepSeek 专属 runtime、API path、store 或 renderer。

## 风险

- readiness test fixture 较多，可能与 artifact renderer fixture 命名耦合。本轮接受该耦合，因为它的价值正是检测新增 stage 时是否补齐可渲染 fixture。
- 真实模型输出质量不由本地测试证明；本轮只证明系统边界与 provider 调用参数正确。真实 smoke 仍需要单独凭证与网络条件。
