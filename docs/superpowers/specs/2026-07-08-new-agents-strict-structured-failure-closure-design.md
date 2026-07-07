# New Agents 严格结构化失败闭环设计

- 日期：2026-07-08
- 状态：目标模式第 2 轮设计
- 来源：`docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md`
- 本轮用户故事：当 raw JSON 流式生成已经出现 partial artifact delta，但最终 JSON 无效、被截断、为空或中断时，调用方只会得到显式错误事件和失败 metric，不会得到成功 `agent_turn`、正式 artifact 持久化或阶段推进。

## 目标承接检查

事实源快照：

- 已读取：`AGENTS.md`、`docs/strategy/goal-mode-playbook.md`、`docs/strategy/goal-mode-cga-template.md`、`docs/index.md`、`docs/ARCHITECTURE.md`、`docs/api-contracts.md`、`docs/TESTING.md`、`docs/CODING_STANDARDS.md`、`docs/DESIGN_PRINCIPLES.md`、结构化失败 todo、Alex handoff todo、`agent_runtime.py`、`stream_services.py`、相关 backend tests。
- 当前工作区：存在大量与本轮无关的既有删除和修改；本轮只触碰 strict failure closure 相关 spec、plan、runtime、stream tests、todo 和必要文档，不回滚、不格式化无关文件。

已确认目标来源：

- 来源：结构化失败治理 todo 的第 2 轮“移除 raw JSON 截断后的伪最终输出路径”。
- 上一轮状态：第 1 轮结构化失败诊断透明化已完成并记录验证结果。
- 本轮承接：严格失败闭环，聚焦 raw JSON 截断、空内容、JSON decode failure、provider 中断后的最终失败语义。

改道条件检查：

- 新 P0/P1 或用户新目标：用户运行中新增要求“完成独立价值后批量验证、commit 并 push 到 GitHub”；已更新 `docs/strategy/goal-mode-playbook.md`，不改变本轮技术边界。
- 未关闭质量门或明确反馈：当前第 2 轮尚未实现；第 1 轮验证记录通过。无 LLM judge 被本轮启用或引用。
- 测试失败或生产阻断：当前未发现阻断测试失败；本轮将先写失败测试复现现有伪最终输出行为。
- 架构冲突：无。改动继续复用共享 Agent Runtime、typed SSE、run persistence 和现有 frontend error path，不新增 workflow 专属分支。
- 子智能体 / 旁路审查决策：不派发。原因是写入范围集中在 `agent_runtime.py`、`test_agent_runtime.py`、`stream_services.py` 测试和文档，且当前工作区已有大量脏改动，拆给 worker 容易制造同文件冲突；以 TDD 和聚焦回归替代。

边界复核：

- 本轮纳入：raw JSON streaming 在最终 JSON 无效时显式失败；partial delta 可先出现，但最终不能被包装成成功 output。
- 本轮排除：DeepSeek tool calling spike、第 3 轮派生字段后端化、第 4-7 轮 ID / 视觉治理、Alex 用户故事拆解工作流。
- 厚度门禁：入口是共享 `/api/agent/runs/stream`；动作是模型流式生成右侧 artifact；处理是 runtime 解析 final JSON 并由 stream service 输出 typed SSE；可见结果是 partial delta 后跟 `error` 而不是 `agent_turn`；状态承接是无正式 artifact 持久化、无成功 metric；失败反馈是 typed schema error diagnostic；证据是 runtime 和 stream service 回归测试。

结论：继续承接第 2 轮。

## Superpowers Brainstorming 自问自答

### Explore Project Context

`PydanticAgentRuntime._stream_raw_json_turn()` 当前在 `json.JSONDecodeError` 且已经发过 partial delta 时，会构造一个 `AgentTurnOutput`，带 `warnings=["artifact_truncated"]`。`stream_services.py` 无法区分这个 output 是“中断后兜底”还是正式成功，会按成功路径写 assistant message、record artifact version、success metric，并发送最终 `agent_turn`。

这与当前 API 文档和 todo 的原则冲突：partial delta 只能是流式预览，最终 `agent_turn` 必须通过完整 schema、renderer 和 workflow contract；最终 JSON 无效时必须显式失败。

### Visual Companion Decision

本轮不涉及 UI 视觉设计。已有前端 typed error 展示能力来自第 1 轮，本轮只保证后端不会发出伪成功 final frame。

### Clarifying Questions

1. partial delta 是否仍允许出现？
   允许。用户可以在生成过程中看到已闭合字段渲染出的正式局部 Markdown，但它不是最终成功结果。

2. 最终 JSON 截断后是否应该保留最新 delta 作为 artifact？
   不应该。最新 delta 只能停留为本轮流式预览，不能作为 final `AgentTurnOutput`、不能持久化、不能推进 stage。

3. 是否要为 JSONDecodeError 增加重试？
   本轮不增加。当前风险是“截断被伪装成成功”；先把失败语义收紧。后续如要重试，应作为单独 provider/runtime 策略设计，并继续保证最终失败显式可见。

4. provider 中断如何处理？
   `LlmClientError` 已映射为 `AgentRuntimeModelError`，stream service 会输出 `LLM_ERROR`。本轮不改变 provider 分类，只增加测试口径确保中断后不产生最终成功 artifact。

5. 是否要改前端？
   不需要新增前端能力。第 1 轮已经支持 typed error diagnostic；本轮后端将输出错误事件，前端继续按既有错误卡展示。

### Approaches

推荐方案：删除 runtime 中 `artifact_truncated` final output 分支，让 `json.JSONDecodeError` 一律冒泡到 `stream_turn()`，再被包装成 `AgentRuntimeSchemaError`。

- 优点：改动最小、语义最清晰，符合“最终 JSON 无效就是失败”；stream service 既有错误映射和 metric 可复用。
- 缺点：现有测试里“保留最新 delta 为 final output”的断言需要改成失败断言。

备选方案 A：新增 warning 类型并让 stream service 特判不持久化。

- 优点：可继续在最终事件中带出 latest markdown。
- 缺点：仍会混淆 final success 与 preview，增加 stream service 分支，容易再次形成伪成功路径。

备选方案 B：在前端收到 `artifact_truncated` 时拒绝写入。

- 优点：前端用户不会看到成功 artifact。
- 缺点：后端仍会写 success metric / artifact version，状态已经被污染，不能解决根因。

结论：采用推荐方案。

## 后端设计

### Runtime 行为

`PydanticAgentRuntime._stream_raw_json_turn()` 在每次尝试结束后解析 `accumulated`。如果 `parse_agent_turn_output_text()` 抛出 `json.JSONDecodeError`：

- 不再构造 `AgentTurnOutput`。
- 不再返回 `warnings=["artifact_truncated"]`。
- 直接抛出，让外层 `stream_turn()` 转换成 `AgentRuntimeSchemaError`。

空内容、非 JSON、未闭合 JSON、被截断 JSON 都走同一失败语义。已经 yield 出去的 `AgentTurnDeltaOutput` 不回收，但不会被提升为正式最终输出。

### Stream Service 行为

`stream_agent_run_events()` 已在外层捕获 `AgentRuntimeSchemaError`：

- 在 partial delta 后继续允许发送 `ErrorEvent(code="SCHEMA_VALIDATION_FAILED")`。
- 不发送 `AgentTurnEvent`。
- 不调用 `append_assistant_message()`。
- 不调用 `record_artifact_version()`。
- 写入 error metric，`status="error"`，`error_code="SCHEMA_VALIDATION_FAILED"`，保留第 1 轮的 typed diagnostic。

### 文档与观测

API 和 TESTING 文档已经声明 partial delta 不能替代 final contract。本轮如代码测试完成后发现文档已有覆盖，只在 todo 执行记录中补充第 2 轮证据；若测试名或行为口径发生变化，则同步 `docs/TESTING.md`。

## 验收条件

1. Given raw JSON streaming 期间已产生 `AgentTurnDeltaOutput`
   When 最终 accumulated JSON 未闭合
   Then runtime 抛出 `AgentRuntimeSchemaError`，不会返回 `AgentTurnOutput(warnings=["artifact_truncated"])`
   Evidence: `test_runtime_raw_json_stream_turn_fails_final_json_truncation_after_partial_delta`

2. Given `/api/agent/runs/stream` 的 runtime 先 yield partial delta 后抛出 schema error
   When stream service 消费该 runtime
   Then SSE 序列为 `run_started`、`agent_delta`、`error`，没有 `agent_turn`
   Evidence: `test_stream_agent_run_events_errors_after_partial_delta_without_persisting_artifact`

3. Given 上述失败发生时传入 persistence adapter
   When 事件流结束
   Then 不记录 assistant message，不记录 artifact version，metric 为 error 且 diagnostic 为 structured output
   Evidence: 同一 stream service 测试断言 persistence calls

4. Given 本轮代码落定
   When 运行聚焦 backend 测试和 New Agents 回归
   Then strict failure closure 不破坏现有 17 阶段 partial streaming happy path
   Evidence: 聚焦 pytest、`./scripts/test/test-local.sh new-agents` 或明确记录无法运行原因。

## 非目标

- 不降低 schema、contract、Mermaid 或 `ai4se-visual` 校验严格性。
- 不新增 fallback 草稿、缓存旧 artifact 成功路径、生产 mock 或隐藏失败。
- 不改变 Lisa、Alex 或任一 workflow 的专属 runtime / API / store / renderer。
- 不实现 DeepSeek tool calling、strict tool call 或 JSONDecodeError 自动重试。
- 不处理派生字段后端化、ID 引用收敛或视觉协议分层。
