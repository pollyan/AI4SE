# New Agents 前端 Artifact Patch 流消费设计

## Current State Gap Analysis

### 事实源快照

- 已读取：`AGENTS.md`、目标模式 playbook / CI 附录、active 增量渲染 todo、最近两次章节索引 / patch 提交、`core/llm.ts`、`core/agentCore.ts`、`services/chatService.ts`、相关 `llm` / `agentCore` / `chatService` 测试。
- 当前工作区：仅 `dist/intent-test-proxy.zip`、`tools/intent-tester/frontend/static/intent-test-proxy.zip`、`tools/intent-tester/test-results/proxy/junit.xml` 为既有/全量测试生成的无关脏文件，本轮不触碰、不 stage。
- 本轮允许写入：`tools/new-agents/frontend/src/core/llm.ts`、`tools/new-agents/frontend/src/core/agentCore.ts`、`tools/new-agents/frontend/src/services/chatService.ts`、相关前端测试、本 spec / plan，以及 active 增量渲染 todo 的进展记录。

### 能力包聚合

| 候选能力包 | 聚合的原始缺口 | 用户动作链 / 工程信任闭环 | 排序结论 | 验收证据 |
| --- | --- | --- | --- | --- |
| 前端 typed SSE patch 消费 | todo 中“生成中 delta 到达时，只替换当前变更块；最终 agent_turn 到达后与完整内容校验一致”；现有前端已有 patch 应用 action，但 runtime stream 不会传递 patch | Agent Runtime event 带 `artifact_patch` + 完整 `artifact_update.markdown` -> `llm.ts` 校验并产出 stream chunk -> `agentCore` 形成 patch decision -> `chatService` 尝试 patch，失败用完整 markdown fallback | 本轮选择。它打通前端运行链路，不要求后端马上生成 patch，也不引入 workflow 专属通道 | llm parser 测试、agentCore reducer 测试、chatService 状态测试 |
| 后端 emit `artifact_patch` | 后端 schema/runtime/service 产生 patch metadata | 服务端真实发送 patch | 暂缓。前端消费契约先落地后，后端切片可以只负责生成 payload | 后续后端 plan |
| ReactMarkdown memoization | UI 只重渲染变更章节 | 解决最终可感知闪动 | 暂缓。需要真实 patch 消费链路稳定后再拆渲染 | 后续组件性能测试 |

### 切片厚度门禁

- 入口：typed Agent Runtime SSE `agent_turn` / `agent_delta` output 可选携带 `artifact_patch`。
- 动作：前端 parser 校验 patch 字段，stream chunk 和 reducer 保留 patch。
- 处理：`chatService` 对当前阶段 artifact update 优先尝试 store patch action；patch 失败或存在章节锁时，用完整 `artifact_update.markdown` 走既有整篇替换和锁定保护路径。
- 可见结果：前端调用链可以消费 patch，成功时局部应用，失败时不丢完整 artifact。
- 失败反馈：patch 字段格式错误抛出结构化 SSE 事件格式错误；patch 应用失败显式 fallback 到完整 markdown，不伪造 patch 成功。
- 证据：覆盖 parser、reducer、service 三层测试。
- 结论：通过。

## Brainstorming 自问自答

### Explore Project Context

`core/llm.ts` 的 `AgentArtifactUpdate` 只允许 `replace | none`，`StreamChunk` 只包含 `newArtifact` / `hasArtifactUpdate`。`core/agentCore.ts` 的 reducer 只输出整篇 `artifactUpdate.content`。`chatService.ts` 对每个 artifact update 先调用 `preserveLockedSections(...)`，再 `setStageArtifact(...)` 和 `setArtifactContent(...)`。上一切片已经提供 store 层 `applyArtifactSectionPatch(...)`，因此本轮只需把 patch 从 typed SSE 搬运到这个 action，并保留完整 Markdown fallback。

### Visual Companion Decision

本轮是运行链路和协议消费，不涉及视觉设计，不需要 visual companion。

### Clarifying Questions

- 用户是谁：后端 patch 生成切片、前端 stream 消费者、长文档局部更新链路。
- 用户要完成什么：让前端能消费 typed SSE 中的可选 patch，而不必等整套后端 patch 生成完成。
- 成功状态是什么：patch 字段格式被严格校验；stream chunk/reducer/chatService 能传递并尝试应用 patch；fallback 保留完整 artifact。
- 不做什么：不让模型 prompt 输出 patch，不改后端 Pydantic schema，不实现组件 memoization。

### Approaches

1. 推荐：允许 `artifact_patch` 与 `artifact_update.type='replace'` 同时出现。patch 用于局部应用，完整 markdown 是校验 / fallback 事实源。优点是失败安全，兼容现有完整替换；缺点是后端仍要发送完整 markdown。
2. 不选：允许 patch-only event。它更接近节省 payload，但 patch 失败时没有完整内容可降级，违背当前 todo 的完整内容校验要求。
3. 不选：把 patch 放入 `artifact_update` 内部。它会改变现有 contract 形状，影响更多旧测试；顶层可选 `artifact_patch` 更低风险。

### Presented Design

扩展 `core/llm.ts`：

- `StreamChunk` 增加 `artifactPatch?: ArtifactSectionPatch`。
- `AgentTurnOutput` / delta output 增加 `artifact_patch?: ArtifactSectionPatch | null`。
- 校验 `artifact_patch`：必须是 object，`operation='replace'`，`sectionAnchor` 和 `replacementMarkdown` 为非空 string，`baseContent` 若存在必须是 string。
- `agent_turn` 若带 patch，仍必须带 `artifact_update.type='replace'` 和非空 markdown，作为 fallback 和最终完整内容。
- map stream chunks 时只在 final chunk 携带 patch，避免中间 synthetic frame 重复应用。

扩展 `core/agentCore.ts`：

- `AgentStreamChunk` 增加 `artifactPatch?: ArtifactSectionPatch`。
- `AgentArtifactUpdateDecision` 增加 `patch?: ArtifactSectionPatch`。
- 当 chunk 有 artifact update 时，decision 同时携带完整 `content` 和可选 `patch`。

扩展 `chatService.ts`：

- 如果 update 有 patch 且当前阶段没有 section lock，先调用 `applyArtifactSectionPatch(...)`。
- patch 成功且结果内容等于锁定保护后的完整 markdown 时，使用 patch 结果。
- patch 失败、patch 结果与完整 markdown 不一致、或存在 section lock 时，继续使用完整 markdown 替换路径。
- fallback 不向用户伪造 patch 成功；本轮不新增 UI 诊断。

## 验收条件

1. Given `agent_turn` 同时包含完整 `artifact_update.markdown` 和合法 `artifact_patch`，When `generateResponseStream(...)` 收集最终 chunk，Then chunk 含完整 `newArtifact` 与 `artifactPatch`。
2. Given `agent_turn` patch 字段格式非法，When 解析 stream，Then 抛出结构化 SSE 事件格式错误。
3. Given reducer 收到带 patch 的 artifact chunk，When reduce，Then artifact update decision 同时包含完整 content 和 patch。
4. Given chatService 收到匹配完整 markdown 的 patch，When handleSend 完成，Then store 的 artifact 内容更新为 patch 后内容，且 `artifactChangeIndex` 记录目标章节。
5. Given patch 失败或 patch 结果与完整 markdown 不一致，When handleSend 完成，Then chatService fallback 到完整 markdown，artifact 不丢失。

## 非目标

- 不新增后端 `artifact_patch` 生成。
- 不允许 patch-only event。
- 不持久化 patch payload。
- 不新增 UI fallback 提示。
- 不实现 ReactMarkdown section memoization。
