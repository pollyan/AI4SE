# New Agents 产物视觉写入前校验设计

## 目标承接检查

事实源快照：

- 已读取：`AGENTS.md`、`docs/strategy/goal-mode-playbook.md`、`docs/strategy/goal-mode-cga-template.md`、`docs/strategy/goal-mode-ci-verification.md`、`docs/index.md`、`docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md`、`tools/new-agents/frontend/src/core/llm.ts`、`tools/new-agents/frontend/src/core/structuredVisuals.ts`、`tools/new-agents/frontend/src/services/chatService.ts`、`tools/new-agents/backend/agent_contracts.py` 和相关测试。
- 当前工作区：`git status -sb` 显示本地与 `origin/codex/structured-failure-diagnostics` 同步，无未提交改动。
- 已确认目标来源：结构化产出失败治理第 7 轮视觉产物稳定化，上一切片已完成 Mermaid repair parse gate 与 artifact contract gate。
- 改道条件：无新的用户目标、阻断测试失败或 LLM judge 低分；第 8 轮全工作流回归门禁仍排在视觉强校验之后。
- 子智能体 / 旁路审查：已派发只读 explorer `Sagan` 审查前端流式消费路径。结论：Mermaid final 写入前已有 parse gate，但真实 `agent_delta` partial 没有视觉预校验；`ai4se-visual` 仅在渲染和导出时解析，没有在写入 ArtifactPane/store 前 gate。

本轮承接：正式 / 流式 artifact 的前端视觉写入前校验闭环。它是第 7 轮“视觉渲染强校验门禁”的一个完整工程信任闭环：用户不会再因为无效 `ai4se-visual` 或 partial 视觉块被写入右侧产物而误以为生成成功。

## Superpowers 自问自答

### Explore Project Context

后端 `validate_agent_turn()` 已能校验必需的 `ai4se-visual` block，包括 `cause-map` 的 `nodes/edges` 协议和其他视觉的 `columns/rows` 协议。前端 `parseStructuredVisual()` 也具备同等解析能力，但当前只在 `StructuredVisual` 组件和 PDF/DOCX 导出中调用。`llm.ts` 在 final `agent_turn` 写出 chunk 前会校验 Mermaid；`agent_delta` partial 没有同等校验，`ai4se-visual` 也没有写入前校验。

### Visual Companion Decision

本轮不涉及 UI 布局或视觉样式设计。问题是数据写入前的契约校验，不需要浏览器 mockup。

### Clarifying Questions

- 用户是谁：New Agents 用户，以及后续依赖 artifact 版本、导出和 E2E 证据的工程调用方。
- 用户要完成什么：在模型生成包含结构化视觉的产物时，只接受可解析、可渲染的视觉块；失败时保留原产物并提示结构化输出失败。
- 成功状态：final `agent_turn` 和真实 `agent_delta` partial 都会在产物写入前校验 `ai4se-visual`。无效 JSON、不支持类型、矩阵结构缺失、`cause-map` 边引用不存在都会显式失败。
- 失败路径：抛出 `Artifact structured visual validation failed: ...`，`chatService` 将其归类为结构化输出生成失败，右侧产物不被无效视觉污染。
- 不做事项：不引入新的可视化类型；不接入 `mmdc`；不迁移 Mermaid mindmap；不修改后端正式 contract；不新增 workflow 专属 runtime、API、store 或渲染管线。

### Approaches

1. **推荐方案：前端共享视觉 gate**
   - 在 `structuredVisuals.ts` 增加 fenced `ai4se-visual` 提取和校验函数，`llm.ts` 在 artifact chunk 写出前统一调用 Mermaid + structured visual 校验。
   - 优点：复用已有 parser，覆盖 final 与 partial 写入路径，改动集中，符合共享 runtime / UI 基础设施原则。
   - 代价：前端只能校验浏览器可解析性，不能替代后端 Pydantic / artifact contract。

2. **后端扩展每个 partial renderer 的 visual contract**
   - 在每个 backend partial renderer 生成 delta 时校验视觉块。
   - 优点：更靠近产物生成源头。
   - 代价：需要触碰大量 renderer，容易变成横切大改；前端仍可能被其他入口写入坏视觉。

3. **引入 `mmdc` / 浏览器截图渲染门禁**
   - 优点：能捕捉部分 parse 通过但渲染失败的问题。
   - 代价：依赖更重，CI 环境复杂，无法作为本轮最小稳定闭环。

选择方案 1。本轮先补上前端写入前强校验，后续第 8 轮再把 CI / fixture 渲染门禁纳入全工作流回归矩阵。

## 设计

### Architecture

继续使用共享 Agent Runtime SSE、`generateResponseStream()`、`chatService`、Zustand store 和 ArtifactPane。新增校验函数只处理 Markdown 中已闭合的 `ai4se-visual` fenced block，复用 `parseStructuredVisual()` 判断结构合法性。`llm.ts` 统一通过 `validateArtifactVisualBlocks()` 在输出 artifact chunk 前校验 Mermaid 和 `ai4se-visual`。

### Components

- `tools/new-agents/frontend/src/core/structuredVisuals.ts`
  - 新增 `extractStructuredVisualBlocks(markdown)`：提取 Markdown 中所有 ` ```ai4se-visual ` fenced block 的内容。
  - 新增 `validateStructuredVisualBlocks(markdown)`：逐块调用 `parseStructuredVisual()`；遇到无效块时抛出 `Artifact structured visual validation failed: <原因>`。
- `tools/new-agents/frontend/src/core/llm.ts`
  - 引入 `validateStructuredVisualBlocks`。
  - 新增或收敛 `validateArtifactVisualBlocks(markdown)`：先校验 `ai4se-visual`，再校验 Mermaid。
  - 覆盖 `mapAgentTurnToStreamChunks`、`mapAgentTurnToFinalChunk`、`mapAgentTurnToArtifactRevealChunks` 和 `mapAgentDeltaToStreamChunks`。
- `tools/new-agents/frontend/src/services/chatService.ts`
  - 将 `Artifact structured visual validation failed` 归类为结构化输出生成失败。

### Data Flow

1. 后端 SSE 返回 `agent_delta` 或 `agent_turn`。
2. `llm.ts` 解析事件并发现可渲染 artifact update。
3. 在 yield `StreamChunk` 前调用共享视觉校验。
4. 校验通过后，`chatService` 才会写入 `setStageArtifact()` / `setArtifactContent()` 并在成功结束后记录 artifact version。
5. 校验失败时抛错，`chatService` 显示结构化失败恢复消息，并保持右侧产物不被失败 chunk 覆盖。

### Error Handling

- `ai4se-visual` JSON 解析失败、不支持类型、矩阵缺少 `columns/rows`、`cause-map` 缺少 `nodes/edges` 或边引用不存在，都抛出统一前缀错误。
- Mermaid 仍沿用 `Artifact Mermaid parse failed`。
- 如果失败发生在已有合法 partial 写入之后，已有合法 preview 保留并标记生成中断；新的无效 chunk 不写入。

### Testing

- `structuredVisuals.test.ts` 覆盖 fenced block 提取、多个 block 校验、坏 JSON、不支持类型、`cause-map` 边引用失败。
- `llm.test.ts` 覆盖 final `agent_turn` 无效 `ai4se-visual` 被拒绝、valid visual 仍可写入、invalid `agent_delta` partial 被拒绝。
- `chatService.test.ts` 覆盖结构化视觉校验错误被归类为结构化输出生成失败，并且 `artifactContent` / `artifactHistory` 保持不变。
- 聚焦回归覆盖 `llm`、`chatService`、`structuredVisuals` 和已有 `StructuredVisual` 渲染测试。

## 验收条件

1. Given SSE final `agent_turn` 返回包含非法 `ai4se-visual` 的 artifact
   When 前端消费该事件
   Then `generateResponseStream()` 抛出 `Artifact structured visual validation failed`，不产生 artifact chunk。

2. Given SSE `agent_delta` 返回包含非法 `ai4se-visual` 的 partial artifact
   When 前端消费该 partial
   Then 无效 partial 不写入右侧产物，错误显式暴露。

3. Given `chatService` 收到结构化视觉校验错误
   When 本轮生成失败
   Then 左侧显示“结构化输出生成失败”，右侧 artifact 和 history 保持原值。

4. Given artifact 包含合法 `ai4se-visual`
   When 前端消费 final 或 partial artifact
   Then 现有渲染、导出和流式消费路径保持可用。
