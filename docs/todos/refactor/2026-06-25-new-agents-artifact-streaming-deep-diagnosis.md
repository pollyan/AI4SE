# New Agents 右侧产物流式渲染缺失深度诊断 Todo

状态：已完成确定性修复，待本地真实模型 smoke 复核
创建日期：2026-06-25
相关模块：`tools/new-agents/`

## 背景

用户在本地部署后再次验证发现：New Agents 右侧产出物到现在仍没有真实流式渲染效果。这个问题此前已经反复修过多次，包括右侧 Artifact 流式渲染、流式位置提示、TEST_DESIGN / STRATEGY 结构化流式契约等相关修复记录，但真实使用中仍持续暴露问题。

用户明确要求：下一轮处理时必须做深度调研和系统性根因分析，不要继续每次只修一个表层问题，导致深层问题在下一轮继续暴露。

## 当前观察

- 复现场景：本地部署后使用 New Agents 生成产出物。
- 现象：右侧产出物没有按预期逐步流式渲染，用户感知仍像一次性生成或没有真实增量。
- 历史背景：已有多条相关归档记录，但问题仍未被彻底消除：
  - `docs/todos/archive/2026-06-25-new-agents-artifact-streaming-not-working-p0.md`
  - `docs/todos/archive/2026-06-24-new-agents-artifact-streaming-position-indicator.md`
  - `docs/todos/archive/2026-06-24-new-agents-test-strategy-artifact-format-streaming-bug.md`
- 风险：如果继续只看局部 parser、单个阶段模板或单个测试样例，可能再次遗漏 runtime、SSE、前端状态、渲染节流、真实模型 chunk、浏览器更新节奏之间的系统性问题。

## 2026-06-25 目标模式处理记录

### 根因结论

- 后端 `sse_response.py` 已设置 `text/event-stream`、`Cache-Control: no-cache`、`X-Accel-Buffering: no`，`nginx/nginx.conf` 的 `/new-agents/api/` 也已 `proxy_buffering off`，当前仓库证据不支持把首要根因归到 Nginx / Flask 响应缓冲。
- 前端 `llm.ts`、`chatService.ts` 和 Zustand store 会消费每个 `agent_delta.output.artifact_update.replace` 并多次写入右侧 `artifactContent`；只要后端给出 renderable artifact delta，前端不会把它压扁成最终一次写入。
- 真正断点在 raw JSON streaming 的 `artifact_data` 局部解析：历史实现只有当整个 `artifact_data` 对象可完整 JSON decode 后，才调用 deterministic renderer 生成 `artifact_update.markdown`。这只能做到“完整对象在 final 前提前一帧”，不能做到用户要求的段落级 / 章节级增量。
- 既有测试没有区分“final 后 synthetic reveal”和“final 前真实 artifact delta”，因此会出现测试通过但用户仍感知为一次性生成的情况。

### 本轮修复

- `tools/new-agents/backend/agent_runtime.py` 增加已完成顶层字段解析：当 `artifact_data` 对象尚未闭合时，只提取已经完整闭合的顶层 JSON 成员，不猜测半截字符串、半截数组或半截对象。
- `tools/new-agents/backend/artifact_data_renderers.py` 增加共享 partial renderer 入口，首批覆盖 `TEST_DESIGN/STRATEGY`。已闭合且通过 Pydantic 子模型校验的 `strategy_summary`、`quality_goals`、`risks` 等章节会复用现有 deterministic section renderer 生成正式 Markdown delta。
- `tools/new-agents/frontend/src/components/ArtifactPane.tsx` 将正文后的流式位置提示改为“正在生成下一段...”，保持提示在 artifact Markdown 外，不进入下载、复制或后续 prompt。
- `docs/TESTING.md` 同步测试口径：禁止 partial `artifact_data` 伪造成进度页；允许已闭合、已通过子模型校验的局部正式章节进入 delta；最终 `agent_turn` 仍必须通过完整工作流契约。

### 已运行验证

- 红测：`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_agent_runtime.py -k "paragraph_level_strategy_artifact_data" -q`，先失败于 final 前只有 1 帧完整 artifact，修复后通过。
- 后端聚焦：`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_agent_runtime.py -k "paragraph_level_strategy_artifact_data or artifact_data_before_final_output or partial_artifact_data" -q`，17 passed。
- STRATEGY renderer 聚焦：`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_artifact_data_renderers.py -k "strategy" -q`，2 passed。
- 前端回归：`npm run test -- src/core/__tests__/llm.test.ts src/services/__tests__/chatService.test.ts src/components/__tests__/ArtifactPane.test.tsx`，273 passed。`ArtifactPane.test.tsx` 仍有既有 React `act(...)` warning，退出码为 0。
- 确定性全量：`NEW_AGENTS_E2E_LLM_JUDGE=0 ./scripts/test/test-local.sh all`，通过；覆盖 Intent Tester API、关键 lint、MidScene proxy、公共前端 lint/build、New Agents 前端全量、New Agents 后端全量和 New Agents browser E2E。

### 额外验证发现

默认环境中 `NEW_AGENTS_E2E_LLM_JUDGE=1` 时，`./scripts/test/test-local.sh all` 在可选外部 LLM judge 失败。确定性 E2E 已通过，judge 给 Lisa 最终产物 83 分，指出第三方登录、弱网支付、安全审计日志和阶段引导质量缺口。该问题已记录到 STRATEGY / 产物格式质量回归 todo，作为独立质量候选处理，不归入本轮 streaming 根因。

### 残余风险

- 本轮没有调用外部真实模型 provider，也没有捕获用户现场的完整 SSE payload；本地真实模型 smoke 需要在部署后由具备 provider 配置的环境复核。
- 本轮只把段落级 partial renderer 落到 `TEST_DESIGN/STRATEGY` 主痛点；其他 artifact_data 阶段仍会沿用“完整对象闭合后生成 artifact delta”的旧行为，后续应按用户故事逐步扩展。
- 如果真实 provider 输出顺序不按 prompt 中的字段顺序，局部 renderer 会等待已知章节字段闭合；最终完整输出仍可收敛，但中途段落级帧数可能减少。

## 目标能力包

对右侧产物流式渲染链路做端到端深度诊断，建立可复现证据和根因树，再决定修复方案。修复目标不是“让某个测试变绿”，而是让本地部署真实运行时右侧产出物在用户可感知层面稳定逐步呈现。

目标体验应是段落级增量渲染，而不是逐字或逐 token 打字机效果。每个段落生成完整后再显示当前段落；当下一个段落正在生成时，应在对应位置给出轻量提示，例如“正在生成下一段...”或等价的段落占位状态，让用户知道右侧产出物仍在推进。逐字流式不符合当前商务文档的阅读习惯，不应作为本问题的目标形态。

该能力包必须继续复用共享 Agent Runtime、typed SSE、workflow manifest、artifact contract、run persistence 和共享 UI 渲染基础设施，不允许为单个 agent、workflow、provider 或阶段新增专属 runtime、API path、store 或 renderer。

## 必须先做的深度调研

下一轮进入实现前，必须先形成 Current State Gap Analysis，并至少覆盖以下链路：

1. 模型层：真实 provider 是否实际按 token/chunk 返回，还是 SDK/代理层聚合后一次性返回。
2. Runtime 层：`PydanticAgentRuntime.stream_turn()` 和 raw JSON streaming 是否在 artifact 可用时发出多个 `AgentTurnDeltaOutput`，还是只在最终输出时发 artifact。
3. SSE 层：后端 `/api/agent/runs/stream` 是否持续 flush `agent_delta`，Nginx / gunicorn / Flask 是否缓冲响应。
4. 持久化层：run/artifact persistence 是否阻塞或延迟最终前的 delta。
5. 前端 parser 层：`llm.ts` 是否持续 yield 多个 artifact update chunk，还是被 `receivedRenderableArtifactDelta`、placeholder 过滤或 final chunk 逻辑压扁。
6. 状态层：`chatService` / store 是否每个 chunk 都更新 `artifactContent`，是否被 `NEXT_STAGE`、错误、截断、生成中状态提前停止。
7. 渲染层：`ArtifactPane` 是否因 Markdown/Mermaid/StructuredVisual 渲染开销、memo、key、scroll 或 diff 逻辑导致用户看不到增量。
8. 浏览器层：真实 UI 下是否有 React batch、CSS、滚动位置或 layout 问题掩盖了增量。

## 需要采集的证据

- 一次本地部署真实运行的 `/api/agent/runs/stream` 原始 SSE 日志，带时间戳。
- 后端 runtime 每次 yield 的事件类型、artifact_update 长度和时间戳。
- 前端 `generateResponseStream()` 每次 yield 的 `hasArtifactUpdate`、`newArtifact.length` 和时间戳。
- store 中 `artifactContent` 更新次数和长度变化。
- 浏览器实际录屏或截图序列，证明用户层是否看到右侧递增。
- 如果某层一次性聚合，必须明确是哪一层开始聚合。

## 验收标准

- 明确给出根因树：哪些历史修复只覆盖了表层，当前真正阻断用户可感知流式的原因是什么。
- 至少有一个稳定复现脚本或手动步骤，可以在本地部署环境捕获 SSE 与前端更新证据。
- 修复后，本地部署真实运行时右侧产出物能按段落逐段增长，而不是最终一次性替换，也不是逐字打字机效果。
- 当前段落生成完成后应显示完整段落；下一段落生成期间，应在该位置显示轻量的“正在生成下一段”类占位或状态提示。
- 自动化测试覆盖端到端等价链路，不能只覆盖某个工具函数。
- 如果真实 provider 本身不支持有效 streaming，必须明确暴露能力限制，并在 UI 上给出真实状态，而不是伪装为流式。
- 不允许用固定延迟假进度、裸进度条或隐藏错误来替代真实 artifact 增量，除非明确标注为非真实流式并获得用户确认。

## 建议测试

- 后端 stream 服务测试：多段 runtime delta 必须立即编码为多个 SSE event。
- Nginx/gunicorn 等价测试：本地部署路径下 SSE 不被缓冲到最终一次性返回。
- 前端 parser 测试：真实 SSE 样例应 yield 多个递增长度 artifact chunk。
- store/service 测试：多段 artifact chunk 会多次更新右侧 artifact state。
- 浏览器 E2E 或等价 Playwright 测试：右侧 artifact 在 final event 前出现至少一次完整段落增长，并在下一段生成期间显示轻量占位提示。

## 非目标

- 不重新设计整个 ArtifactPane。
- 不为某个阶段写专属流式 renderer。
- 不用假进度替代真实数据增量。
- 不在缺少端到端证据时只改 prompt 或 parser 后归档。

## 待补充证据

- 当前本地部署的具体模型/provider。
- 复现输入和工作流阶段。
- 原始 SSE 捕获日志。
- UI 录屏或截图序列。
