# New Agents 右侧产物段落级真实流式设计

## Current State Gap Analysis

### 事实源快照

- 已读取：`AGENTS.md`、`docs/strategy/goal-mode-playbook.md`、`docs/strategy/goal-mode-cga-template.md`、`docs/strategy/goal-mode-subagents.md`、`docs/index.md`、`docs/ARCHITECTURE.md`、`docs/api-contracts.md`、`docs/TESTING.md`、三个活跃 refactor todo、`tools/new-agents/backend/agent_runtime.py`、`tools/new-agents/backend/stream_services.py`、`tools/new-agents/backend/sse_response.py`、`nginx/nginx.conf`、`tools/new-agents/frontend/src/core/llm.ts`、`tools/new-agents/frontend/src/services/chatService.ts`、`tools/new-agents/frontend/src/core/agentCore.ts`、`tools/new-agents/frontend/src/components/ArtifactPane.tsx`。
- 当前工作区：`dist/intent-test-proxy.zip`、`tools/intent-tester/frontend/static/intent-test-proxy.zip`、`tools/intent-tester/test-results/proxy/junit.xml` 是既有脏文件，本轮不触碰、不 stage。
- 本轮允许写入：`tools/new-agents/backend/**`、`tools/new-agents/frontend/**`、`docs/superpowers/**`、`docs/todos/refactor/**`。

### 候选能力包

| 候选 | 来源 | 目标态 | 当前能力 | 缺口 | 去向 |
| --- | --- | --- | --- | --- | --- |
| 右侧产物段落级真实流式闭环 | `2026-06-25-new-agents-artifact-streaming-deep-diagnosis.md` | final 前按完整段落/章节增量显示正式 artifact，下一段生成时在当前位置显示轻量提示 | 后端只在完整 `artifact_data` 对象闭合后渲染；前端无 renderable delta 时 final 后 synthetic reveal | 用户仍感知为一次性生成；已有测试无法区分真实 final 前增量和 final 后模拟揭示 | 本轮 |
| STRATEGY 格式错误回归 | `2026-06-25-new-agents-test-strategy-artifact-format-regression.md` | 第二阶段稳定生成可渲染《测试策略蓝图》 | renderer 与 prompt 已有结构化契约，但缺真实失败样例 | 需要捕获真实 payload 才能判定是否是模型输出、renderer、Mermaid 或前端解析问题 | 下一轮或并入真实失败样例修复 |
| 错误信息位置与折叠 UX | `2026-06-25-new-agents-error-message-placement-ux.md` | 错误作为最新事件低占用展示，可展开详情 | 当前错误文本仍进入对话主流 | 独立 UI 故事，不应混入 streaming 主链路提交 | 下一轮 |

排序结论：选择右侧产物段落级真实流式闭环。它是 P0，并且是用户最新明确要求“深度调研，不要表层修”的主路径问题。STRATEGY 格式错误可能与 artifact 链路共用根因，但缺少真实失败样例，本轮不做猜测式 prompt 微调。错误信息 UX 是独立体验故事，保留为后续候选。

## Superpowers 自问自答

### Explore Project Context

后端 `/api/agent/runs/stream` 通过共享 Agent Runtime 返回 typed SSE。`sse_response.py` 已设置 `text/event-stream`、`Cache-Control: no-cache` 和 `X-Accel-Buffering: no`；`nginx.conf` 的 `/new-agents/api/` 也已关闭 `proxy_buffering`。因此本轮不能把问题简单归因到网关缓冲。

`agent_runtime.py` 当前 `build_partial_agent_delta(...)` 只能从 JSON 字符串中抽取 `chat`、`markdown` 或已经完整闭合的 `artifact_data` 对象。对于当前结构化 artifact 契约，模型输出的是 `artifact_data`，不是手写 Markdown；所以真实生成期间只有当整个 `artifact_data` 对象完整闭合，后端才会渲染一次 artifact delta。既有 “before final” 测试只是证明完整对象在 `stage_action` 前到达时会发 delta，不能证明段落级逐步显示。

前端 `llm.ts` 会消费 `agent_delta.output.artifact_update.replace.markdown`，`chatService.ts` 会对每个 artifact chunk 写 `artifactContent`。如果没有 renderable artifact delta，前端会在最终 `agent_turn` 后用 synthetic reveal 拆最终文档。这个行为能让单测看到多帧，但不等于真实模型生成过程中右侧逐段增长。

### Visual Companion Decision

本轮是运行时链路和文档生成体验修复，不需要单独做视觉方案对比。现有 ArtifactPane 已有生成中位置提示，只需让文案和出现位置匹配“正在生成下一段”的目标。

### Clarifying Questions

- 用户是谁：本地使用 New Agents 生成测试策略、需求分析、价值发现等产物的业务/测试设计用户。
- 成功状态是什么：final 前右侧出现正式 Markdown 增量；每次增量是完整段落或完整章节，不是逐字打字机。
- 输入来源是什么：真实 LLM streaming 中已闭合的 `artifact_data` 顶层字段或数组。
- 不做什么：不输出调试页、不用固定延迟伪造进度、不改成手写 Markdown 契约、不新增 agent/workflow 专属 runtime、API path、store 或 UI renderer。
- 失败路径：如果当前 provider 或输出顺序无法产生可验证的局部 `artifact_data` 字段，前端仍显示生成中状态，最终结果到达后收敛；后续真实 smoke 需要记录 provider 能力限制。

### Approaches

1. 推荐：在共享 raw JSON streaming 路径解析已经闭合的 `artifact_data` 顶层字段，并用现有 deterministic renderer 的局部 section 渲染器生成正式 Markdown 增量。优点是保留结构化契约和最终 renderer；缺点是需要给当前阶段补局部渲染映射。
2. 不选：让模型额外输出 `artifact_update.markdown`。它能天然流式，但会绕过 artifact_data 确定性 renderer，容易重新引入 STRATEGY Markdown/Mermaid 格式错误。
3. 不选：前端在 final 后继续 synthetic reveal。它不能解决用户反馈的“真实流式缺失”，只是最终结果到达后的视觉模拟。

### Presented Design

后端新增一个共享的“已完成顶层字段”解析器：当 `artifact_data` 对象本身尚未闭合时，仍可按 JSON 语义提取已经完整闭合的顶层字段值。解析器只接收完整 JSON value，不猜测半截字符串、半截数组或半截对象。

`artifact_data_renderers.py` 增加局部 artifact 渲染入口。首批覆盖 TEST_DESIGN 的 `STRATEGY` 阶段：当 `strategy_summary`、`quality_goals`、`risks` 等顶层字段依次闭合时，用现有 section render 函数生成 `# 测试策略蓝图` 加已完成章节。每个章节都先通过对应 Pydantic 子模型校验，校验失败则只保留此前已通过的章节。最终完整对象仍走现有 `render_agent_turn_from_artifact_data(...)` 和完整 contract validation。

前端保持共享 typed SSE/parser/store 主链路。ArtifactPane 已经把生成中指示器放在当前 artifact 内容之后，本轮只把文案改为“正在生成下一段...”，让它明确表达段落级生成状态。

## 验收条件

1. Given TEST_DESIGN/STRATEGY 的 raw JSON stream 已输出完整 `strategy_summary` 但 `artifact_data` 对象尚未闭合，When 后端处理当前累计文本，Then 在 final 前发出包含 `# 测试策略蓝图` 和 `## 1. 策略摘要` 的 `agent_delta.artifact_update.replace`，且不包含尚未闭合的后续章节。
2. Given 后续 `quality_goals` 完整闭合，When 后端继续处理流，Then 下一帧 artifact Markdown 递增包含 `## 2. 质量目标`。
3. Given 半截字段或半截数组尚未形成完整 JSON value，When 后端处理当前累计文本，Then 不生成调试式 artifact 占位。
4. Given 前端正在生成且已有 artifact 内容，When ArtifactPane 渲染，Then 当前内容后出现轻量状态“正在生成下一段...”。
5. Given 最终 `agent_turn` 到达，When 前端收敛最终输出，Then 右侧 artifact 与最终 renderer 输出一致，未新增 workflow 专属 runtime、API path、store 或 UI pipeline。

## 非目标

- 不处理错误信息折叠 UX。
- 不在没有真实失败 payload 的情况下修 STRATEGY 格式错误回归。
- 不覆盖所有 workflow 的局部 section renderer；本轮先建立共享解析机制和 STRATEGY 主路径回归，后续按真实用户故事扩展其他阶段。
- 不调用外部模型作为默认门禁；真实 smoke 若需要 provider 凭证，单独记录。
