# New Agents DeepSeek Tool Calls 能力 Spike 设计

## 目标

本轮只回答一个工程信任问题：DeepSeek tool calls 是否值得进入 Alex / Lisa 共享 Agent Runtime 的正式结构化产出主链路。

结论先行：当前不启用。DeepSeek 官方文档支持 tool calls，并为 strict tool calls 提供 beta 模式，但官方 Chat Completion streaming 文档没有明确展示 `delta.tool_calls` 或 streaming tool arguments；本地 `llm_client.py` 也只消费 `delta.content`，没有 `tools`、`tool_choice` 或 tool call 参数流解析。缺少 `DEEPSEEK_API_KEY`，本轮不能做真实 provider smoke，因此不能声称 DeepSeek V4 Flash 已稳定支持 streaming tool arguments。

## 事实源

- DeepSeek 官方 [Tool Calls](https://api-docs.deepseek.com/guides/tool_calls) 文档：展示 OpenAI SDK 兼容的 `tools` 调用；strict 模式属于 beta，需要 `/beta` base URL，并要求函数定义显式启用 strict。
- DeepSeek 官方 [Create Chat Completion](https://api-docs.deepseek.com/api/create-chat-completion) 文档：`response_format.type` 只列出 `text` 和 `json_object`；streaming chunk 示例是 `delta.content` / `delta.role`，`finish_reason` 可为 `tool_calls`。
- DeepSeek 官方 [JSON Output](https://api-docs.deepseek.com/guides/json_mode) 文档：JSON Output 只保证有效 JSON 字符串，仍要求 prompt 中明确要求 JSON，并提示可能出现空内容或截断风险。
- 本地 `tools/new-agents/backend/llm_client.py`：`ChatDelta` 只定义 `content`，`stream_chat_completion_content()` 只传 `response_format` / `extra_body`，只 yield 文本内容。
- 本地 `tools/new-agents/backend/agent_runtime.py`：`deepseek-v4-*` 解析为 `json_object_only`，使用 `response_format={"type": "json_object"}`，并在 DeepSeek V4 下关闭 thinking。
- 本地 `tools/new-agents/backend/stream_services.py`：结构化输出失败已经能通过 typed diagnostic 暴露，但当前没有 tool call argument 专属失败路径。

## 自问自答 Brainstorming 记录

**Explore Project Context**

New Agents 的高优先级架构原则要求 Lisa、Alex 和未来 Agent 共享 runtime、transport、state 和 UI。任何 provider 能力都不能为 Alex 单独分叉 API、SSE、store 或 renderer。当前失败治理主线已经证明更稳的方向是减少模型维护派生字段和引用关系，而不是把全部希望放在 provider 结构化能力上。

**Visual Companion Decision**

本轮不涉及 UI、图表或视觉协议设计，不需要视觉伴随。

**Clarifying Questions**

- 用户是谁：后续维护 New Agents 结构化产出链路的工程师，以及目标模式继续选题的 Agent。
- 成功状态是什么：能明确判断 DeepSeek tool calls 当前是否进入主线；若不能进入，写清阻塞和后续触发条件。
- 输入来源是什么：官方 DeepSeek 文档、本地 runtime 代码、当前 todo 失败证据。
- 失败路径是什么：缺少真实 provider key 时不伪造“已验证稳定”；官方 streaming schema 不明确时不写成支持。
- 不做什么：不把 tool calls 接入正式 workflow，不让模型调用渲染工具，不降低 Pydantic / artifact contract 严格性。

**Approaches**

1. 推荐方案：静态 capability spike，记录官方能力、本地差距、阻塞和 future gate。优点是风险低，不改变主链路；缺点是不能给出真实稳定性数字。
2. 直接实现 shared tool-call stream parser。优点是为未来铺路；缺点是没有官方 streaming arguments 文档和真实 smoke，容易做出未被 provider 证明的死代码。
3. 直接切换 artifact_data 到 tool calls。优点是理论上减少 JSON markdown 混杂；缺点是当前 runtime 不支持，且 strict schema 子集不足以替代业务 validator，风险最高。

采用方案 1。方案 2 必须等真实 DeepSeek key、最小 toy schema smoke 和 documented / observed stream shape 都存在后再做；方案 3 不进入候选。

## 能力判断

| 问题 | 结论 | 依据 |
| --- | --- | --- |
| DeepSeek 是否支持 tool calls | 支持非 strict tool calls | 官方 Tool Calls 页面展示 `tools` 参数和 assistant `tool_calls` 消息模式 |
| strict tool call 是否需要 `/beta` | 需要 | 官方 Tool Calls strict 模式说明要求 beta base URL |
| strict schema 子集是否能覆盖当前 artifact_data | 不能完整覆盖 | strict object 要求全部字段 required 且 `additionalProperties=false`；不支持 `minLength`、`maxLength`、`minItems`、`maxItems`，不能替代 Pydantic validator 和业务不变量 |
| Chat Completion `response_format` 是否支持 OpenAI strict JSON Schema | 不支持直接照搬 | 官方 Chat Completion 只列出 `text`、`json_object` |
| streaming tool arguments 是否已被官方文档明确支持 | 未明确 | 官方 streaming chunk 示例和 schema 只展示 content/role/reasoning/logprobs 等文本增量；`finish_reason` 可为 `tool_calls`，但未展示 `delta.tool_calls` arguments |
| 当前 New Agents 是否能消费 tool calls | 不能 | `llm_client.py` 只 yield `delta.content`，请求参数没有 `tools` / `tool_choice` |
| 失败时是否能 typed error 显式暴露 | 现有结构化输出失败可以；tool call argument 失败尚无专属路径 | `stream_services.py` 有 structured output diagnostic，但 tool argument parser 不存在 |

## 设计结论

DeepSeek tool calls 暂不进入正式 artifact 主链路。当前治理主线继续保持：

- DeepSeek V4 Flash 使用 `json_object_only`。
- 模型只输出语义事实和原子判断。
- 派生字段、统计、排序、ID 和引用一致性优先由后端确定性生成或校验。
- Pydantic validators、artifact contract 和 deterministic renderer 继续作为最终成功门禁。

如果后续要启用 tool calls，必须先新增一个独立能力包：

- provider capability registry 标明 `supports_tools`、`supports_strict_tools`、`requires_beta_base_url`、`streaming_tool_arguments_verified_at`。
- `llm_client.py` 新增独立 stream event 类型，不改变现有 content streaming 契约。
- 用 mock fixture 覆盖 OpenAI-compatible `delta.tool_calls` 拼接、未知 tool、无效 JSON arguments、finish_reason=`tool_calls` 但缺少 arguments 等失败路径。
- 使用 toy `submit_artifact_data` 工具做真实 DeepSeek smoke；请求只能发送非用户业务数据。
- tool arguments 仍必须进入 Pydantic / artifact contract 校验；校验失败继续走 typed error，不持久化 artifact，不推进 stage。

## 验收

- 本轮输出明确结论：不启用 DeepSeek tool calls 主链路。
- 本轮记录了 `/beta`、strict schema 子集、JSON mode 边界、streaming arguments 未证实、本地 runtime 差距、typed error 后续要求。
- 本轮不新增 workflow 专属 runtime、API、SSE、store 或 renderer。
- 本轮不运行真实 DeepSeek smoke，因为环境没有 `DEEPSEEK_API_KEY`；这必须作为阻塞记录，而不是被当作通过。
