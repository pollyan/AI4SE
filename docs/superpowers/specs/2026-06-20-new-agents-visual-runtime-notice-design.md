# New Agents 可视化运行时失败左侧提示设计

## Current State Gap Analysis

事实源快照：
- 已读取：`docs/todos/new-agents-ux-professionalization.md`、`AGENTS.md` 当前约束。
- 已读取代码：`tools/new-agents/frontend/src/components/Mermaid.tsx`、`ArtifactPane.tsx`、`StructuredVisual.tsx`、`ChatPane.tsx`、`store.ts`、`core/types.ts`。
- 已读取测试：`ArtifactPane.test.tsx`、`ChatPane.test.tsx`、`StructuredVisual.test.tsx`。
- 当前主分支已包含 `e1882ef1 fix(new-agents): 补齐结构化失败恢复引导`。
- 本轮在 `.worktrees/codex-new-agents-visual-runtime-notice` 分支 `codex/new-agents-visual-runtime-notice` 中执行。

## Gap

右侧 artifact 中 Mermaid 或 `ai4se-visual` 运行时渲染失败时，右侧局部块已有错误 UI，但左侧对话区没有任何提示。用户如果停留在左侧对话或没有滚动到右侧失败位置，会误以为产出物已经完整可用。

## 目标行为

- Mermaid 运行时渲染失败后，右侧继续保留现有 `重新生成图表` / Live Editor 能力。
- 同一阶段的左侧 ChatPane 显示轻量提示：右侧产物里有可视化渲染失败，需要去右侧处理。
- `ai4se-visual` JSON 或 schema 解析失败时，也写入同一类可视化诊断，并在左侧提示。
- 当 artifact 内容、workflow、stage 或错误块恢复正常后，左侧提示自动消失。
- 不向 chat history 写入新的 assistant 消息，避免污染模型上下文。

## Architecture

- 在共享 store 增加 ephemeral 状态 `artifactVisualDiagnostics`，按当前 workflow stage 记录可视化渲染诊断。
- `Mermaid` 增加可选 `onRenderError` / `onRenderSuccess` 回调，运行时失败或恢复时通知 ArtifactPane。
- `StructuredVisual` 增加可选 `onValidationError` / `onValidationSuccess` 回调，解析失败或恢复时通知 ArtifactPane。
- `ArtifactPane` 在当前 artifact preview 渲染 Mermaid / `ai4se-visual` 时传入诊断回调；历史预览不参与当前阶段诊断。
- `ChatPane` 读取当前阶段诊断并显示自然、轻量的非 chat-history 提示块。

## 不做

- 不实现自动跳转到右侧错误块。
- 不把错误写入 chat history。
- 不改后端 contract 或 runtime。
- 不做 PDF/DOCX 高保真嵌入。

## 验收条件

1. Given 当前 artifact 包含渲染失败的 Mermaid
   When ArtifactPane 上报诊断
   Then ChatPane 显示右侧可视化失败提示，并提示用户去右侧重新生成图表。
2. Given Mermaid 后续渲染成功
   When ArtifactPane 清除诊断
   Then ChatPane 提示消失。
3. Given `ai4se-visual` 格式错误
   When ArtifactPane 渲染当前 artifact
   Then store 记录结构化可视化诊断，ChatPane 显示同类提示。
4. Given 切换工作流、阶段或清空历史
   Then 旧阶段可视化诊断不会污染新阶段。

## 风险

- React 渲染期间直接写 store 会引发副作用警告，因此 `StructuredVisual` 需要在 `useEffect` 中上报验证状态。
- Mermaid 渲染是异步的，需要用稳定的诊断 key 避免旧错误覆盖新内容。
- 诊断状态是 UI ephemeral 状态，不应持久化到 localStorage。

## 验证计划

- `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx src/components/__tests__/ChatPane.test.tsx src/components/__tests__/StructuredVisual.test.tsx`
- `cd tools/new-agents/frontend && npm run build`
- `git diff --check`
