# New Agents Artifact Comment Selection Anchor Design

## Current State Gap Analysis

Artifact 批注已支持新增、删除、回复、解决状态和服务端同步，但批注仍只能自动引用 artifact 的首个正文行。用户在审阅长产出物时，如果想针对某一条风险、测试点或验收口径留言，系统无法记录“我批的是哪段文字”，后续回看成本较高。

候选能力包：

- 选区摘录锚点：用户在右侧产物中选中文字后新增批注，批注摘录优先使用该选区，并保存轻量锚点字段。该能力直接改善现有批注动作链。
- DOM 高亮与滚动定位：需要稳定 Markdown render source map，复杂度较高，适合作为后续增强。
- 服务端审阅轨迹：需要记录操作事件和审计视图，应在批注锚点之后独立推进。

本轮选择选区摘录锚点。

## User Story

作为 Lisa/Alex 工作区用户，当我在右侧产出物中选中某段文字并新增批注时，批注应引用我选中的内容，而不是默认引用文档开头。之后恢复历史 run 时，该批注仍能保留选区摘录。

## Scope

- ArtifactPane 预览区支持捕获当前用户选中的 artifact 文本。
- 新增批注时，如果选区位于 artifact 预览容器内，则 `artifactExcerpt` 使用选中文本。
- 批注新增 `anchorText` 字段，记录被选中的规范化文本；旧批注缺少该字段时兼容为 `null`。
- 后端 artifact collaboration 状态保存并恢复 `anchorText`。
- 选区摘录需要做空白规范化和长度限制，避免把整篇文档写入批注。

## Non-Goals

- 不实现正文高亮、滚动定位或 source map。
- 不做跨 Markdown AST 节点的精确 offset。
- 不把批注送入模型上下文。
- 不新增 agent/workflow 专属批注渲染分支。

## Acceptance

1. 用户选中 artifact 预览区文本后新增批注，批注引用选中文本。
2. 没有有效选区时，批注继续使用原有文档摘录 fallback。
3. 服务端 collaboration API 和 run snapshot 保留 `anchorText`。
4. 旧本地缓存或旧服务端批注缺少 `anchorText` 时不会恢复失败。
5. 现有批注回复/解决状态、章节锁、人工编辑和导出能力不退化。

## Verification

- `npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx src/__tests__/store.test.ts src/services/__tests__/runSnapshotService.test.ts`
- `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_run_persistence.py tools/new-agents/backend/tests/test_agent_endpoint.py`
- `npm run lint`
- `npm run build`
- `git diff --check`
