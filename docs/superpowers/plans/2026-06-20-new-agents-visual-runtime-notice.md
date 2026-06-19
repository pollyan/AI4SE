# New Agents 可视化运行时失败左侧提示 Implementation Plan

**Goal:** 右侧 Mermaid / `ai4se-visual` 运行时失败时，左侧 ChatPane 显示轻量提示，帮助用户发现并处理右侧产物问题。

**Architecture:** 复用共享 store、ArtifactPane、ChatPane、Mermaid、StructuredVisual。不新增 Lisa/Alex/workflow-specific 分支，不写 chat history。

**Working tree:** `/Users/anhui/Documents/myProgram/AI4SE/.worktrees/codex-new-agents-visual-runtime-notice`

## File Structure

- Modify: `tools/new-agents/frontend/src/core/types.ts`
  - Add artifact visual diagnostic type and store actions.
- Modify: `tools/new-agents/frontend/src/store.ts`
  - Add ephemeral diagnostic state, set/clear actions, and reset on workflow/stage/content changes.
- Modify: `tools/new-agents/frontend/src/components/Mermaid.tsx`
  - Add render success/error callbacks.
- Modify: `tools/new-agents/frontend/src/components/StructuredVisual.tsx`
  - Add validation success/error callbacks.
- Modify: `tools/new-agents/frontend/src/components/ArtifactPane.tsx`
  - Wire diagnostics for current artifact preview only.
- Modify: `tools/new-agents/frontend/src/components/ChatPane.tsx`
  - Render lightweight current-stage visual diagnostic hint.
- Modify tests:
  - `ArtifactPane.test.tsx`
  - `ChatPane.test.tsx`
  - `StructuredVisual.test.tsx`
- Modify todo:
  - `docs/todos/new-agents-ux-professionalization.md`

## Task 1: Store Diagnostic Contract

- [x] Add failing component tests proving current-stage diagnostics can be set, read, and ignored across stages.
- [x] Add `artifactVisualDiagnostics`, `setArtifactVisualDiagnostic`, `clearArtifactVisualDiagnostic`, and stage clear action.
- [x] Keep diagnostics out of persisted `partialize`.
- [x] Reset diagnostics when artifact content changes, workflow changes, stage changes, clear history, handoff, or snapshot restore.

## Task 2: ArtifactPane Reporting

- [x] Add failing ArtifactPane test for invalid `ai4se-visual` recording a current-stage diagnostic.
- [x] Add Mermaid component tests for render error and success callbacks.
- [x] Wire `StructuredVisual` and `Mermaid` callbacks from current preview only.

## Task 3: ChatPane Notice

- [x] Add failing ChatPane test: current-stage visual diagnostic shows a lightweight notice.
- [x] Add test that diagnostic from another stage does not show.
- [x] Implement ChatPane notice without writing chat history.

## Task 4: Regression Verification And Todo

- [x] Run RED: `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx src/components/__tests__/ChatPane.test.tsx src/components/__tests__/StructuredVisual.test.tsx` failed with 4 expected behavior gaps.
- [x] Run GREEN: `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/Mermaid.test.tsx src/components/__tests__/ArtifactPane.test.tsx src/components/__tests__/ChatPane.test.tsx src/components/__tests__/StructuredVisual.test.tsx`.
- [x] Run `cd tools/new-agents/frontend && npm run build`.
- [x] Run `git diff --check`.
- [x] Update `docs/todos/new-agents-ux-professionalization.md`.
