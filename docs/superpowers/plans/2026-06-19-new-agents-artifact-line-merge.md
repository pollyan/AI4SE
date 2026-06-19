# New Agents Artifact 逐行合并 MVP 实施计划

## 范围

本计划实现冲突对比面板中的最小逐行合并能力：只针对 `服务端版本 vs 你的草稿` 中的草稿新增行提供 `采纳到草稿` 和 `丢弃此行`。

## TDD 步骤

1. RED：在 `ArtifactPane.test.tsx` 增加测试，构造保存冲突，打开对比后点击 `丢弃此行`，断言编辑框草稿删除该行且 diff 更新。
2. RED：增加测试，点击 `采纳到草稿`，断言编辑框以服务端版本为基准并包含该草稿新增行。
3. GREEN：在 `ArtifactPane.tsx` 中为冲突 diff 的 added 行渲染逐行操作按钮。
4. GREEN：实现 `discardConflictDraftLine`，从 `editDraft` 中删除对应草稿行。
5. GREEN：实现 `acceptConflictDraftLine`，以 `conflictArtifact.content` 为基准追加或插入该草稿行；MVP 先采用稳定可解释的追加策略，避免错误上下文合并。
6. REFACTOR：提取轻量 helper，保持按钮只在可操作 added 行出现。
7. 验证：运行 `npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx`、`npm run lint`、`npm run build`、`git diff --check`。

## 风险控制

- 只改前端冲突恢复 UI，不触碰后端 artifact API。
- 不修改 Lisa/Alex 工作流配置或共享 runtime。
- 对无法定位的复杂 diff 不显示逐行操作，避免制造错误合并。
- 采纳操作不自动保存，仍由用户点击 `保存修改` 走现有冲突检测。
