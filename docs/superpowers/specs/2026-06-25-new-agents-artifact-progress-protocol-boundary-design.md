# New Agents Artifact Progress Protocol Boundary Design

> 日期: 2026-06-25
> Milestone: Artifact 进度占位与正式产物协议边界重构
> 状态: 已完成

## Current State Gap Analysis

当前缺口不是“右侧流式动画不够细”，而是后端协议语义被污染: `agent_delta.artifact_update.replace` 同时承载了正式产物、正式产物局部更新和调试式进度占位。用户在右侧看到 `# 产出物生成中`、`已接收字符数`、`已识别字段: artifact_data`，说明调试占位已经进入正式 artifact 渲染链路。

候选能力包:

1. Artifact 进度占位与正式产物协议边界重构。本轮选定。它直接消除重复出现的右侧调试页，收束后端 typed SSE 语义，并保留前端防御测试。
2. 右侧章节位置级 streaming indicator。延期。它是体验增强，应建立在正式 artifact 协议干净之后，否则 indicator 仍可能污染 Markdown。
3. 测试策略阶段格式与流式渲染专项修复。延期。它涉及阶段模板和 renderer 质量，风险面更大，适合作为后续独立 Superpowers 切片。

工作区存在历史未提交改动。本轮不使用 worktree，原因是用户已明确要求目标模式后续不要使用 worktree；本轮会只修改与协议边界重构相关的文件，提交时只 stage 聚焦文件。

## Superpowers Brainstorming Record

问题自问自答:

- Q: 用户真正不能接受的是什么?
- A: 右侧正式产物区域出现了调试式进度页。用户可以接受按段落/章节渐进渲染，但不能接受数字、字段名、内部协议字段冒充正式产物。

- Q: 为什么问题重复出现?
- A: 后端 `build_partial_agent_delta()` 在看到局部 `"artifact_data"` 时主动构造 Markdown 进度页，并通过 `artifact_update.replace` 发给前端；同时后端测试还在断言这个行为存在。前端兜底只能降低暴露概率，不能修正协议边界。

- Q: 只做前端过滤是否足够?
- A: 不足够。过滤属于防御层，但源头仍会把错误语义送进 SSE，未来复制、持久化、快照、导出或其他 UI 入口都可能再次踩中。

- Q: 是否需要新增 `agent_progress` SSE 类型?
- A: 本轮不需要。当前验收目标是禁止调试占位进入 artifact。章节位置级 indicator 可以作为后续 UI-only 或 typed hint 能力包处理。

- Q: 什么是正确协议语义?
- A: `artifact_update.type="replace"` 只代表正式 Markdown artifact 或经过正式 renderer 产生的局部正式 artifact。进度、字段名、字符数、解析状态不得进入这个字段。

## Spec

### User Story

作为 New Agents 用户，我希望右侧产出物区域只显示正式产物格式内容。生成期间可以有左侧对话状态或右侧非持久化 UI loading，但不能把后端调试信息、字段名、字符数当成正式文档显示。

### Scope

- 后端 `tools/new-agents/backend/agent_runtime.py`
  - 禁止在局部 `artifact_data` 出现时构造 Markdown 进度页。
  - `build_partial_agent_delta()` 只允许从 `chat` 和显式 `artifact_update.markdown` 中提取局部正式内容。
- 后端测试 `tools/new-agents/backend/tests/test_agent_runtime.py`
  - 将现有“要求 artifact progress 出现”的测试改为“禁止 partial artifact_data 产生 artifact_update”。
  - 继续确认最终 `agent_turn` 会把完整 `artifact_data` 渲染为正式 Markdown artifact。
- 前端 `tools/new-agents/frontend/src/core/llm.ts`
  - 保留对历史/异常进度占位的防御过滤，避免旧后端或异常 SSE 再污染 UI。
- 前端测试 `tools/new-agents/frontend/src/core/__tests__/llm.test.ts`
  - 保留回归测试: 如果收到进度占位 delta，右侧不显示占位，最终正式 artifact 仍按段渐进揭示。
- 文档
  - 更新 API contract，明确 `artifact_update.replace` 不能承载调试进度占位。
  - 更新测试说明，说明后端 runtime 和前端 stream parser 都要保护该协议边界。
  - 更新相关 active todo 的当前状态。

### Non-Goals

- 不实现章节位置级 streaming indicator。
- 不要求逐字 token 级右侧 artifact 渲染。
- 不新增 workflow/agent 专属 runtime、API path、store 或 renderer。
- 不修改 artifact persistence/export/copy 语义。
- 不改变最终 artifact_data renderer 的文档格式。

### Protocol Invariants

- `agent_delta.output.artifact_update.type="replace"` 的 `markdown` 必须是正式 artifact markdown。
- `agent_turn.output.artifact_update.type="replace"` 的 `markdown` 必须是最终正式 artifact markdown。
- 下列内容不得出现在 `artifact_update.replace.markdown` 中:
  - `# 产出物生成中`
  - `已接收字符数`
  - `已识别字段`
  - 用于调试的裸字段名进度，例如只展示 `artifact_data`
- partial raw JSON 中出现 `"artifact_data"` 只能说明模型正在输出结构化数据；在完整 JSON 解析和契约校验完成前，不得伪造 artifact markdown。

### Acceptance Criteria

- 后端 raw JSON streaming 在 partial `"artifact_data"` 到达时不会发出 `artifact_update.replace` 进度页。
- 后端最终输出仍能把合法 `artifact_data` 渲染为正式 Markdown artifact。
- 前端遇到历史进度占位 delta 时不会让右侧 artifact 显示该占位。
- 相关后端单测、前端 stream parser 测试和 lint 通过。
- `docs/todos/` 记录本轮协议边界重构已消化该类调试占位重复出现问题。
