# New Agents Artifact Comment Anchor Highlight Design

## Current State Gap Analysis

Artifact 批注已经能保存正文选区锚点 `anchorText`，但用户从批注回看正文时仍需要自己在长产物中查找对应文本。当前只解决了“批注引用什么”，还没有解决“如何回到被批注的位置”。

候选能力包：

- 轻量锚点定位/高亮：批注卡片提供定位按钮，点击后在当前预览中高亮第一个匹配锚点文本，并尝试滚动到高亮处。
- 精确 Markdown source map：需要维护 Markdown AST 到 DOM 的 offset 映射，复杂度较高。
- 持久化高亮状态：会影响阅读状态和历史恢复，暂不做。

本轮选择轻量锚点定位/高亮。

## User Story

作为 Lisa/Alex 工作区用户，当我看到一条带正文摘录的批注时，可以点击定位，右侧产物正文会高亮对应文本，让我快速回到被讨论的位置。

## Scope

- 带 `anchorText` 的批注显示 `定位正文` 操作。
- 点击后切换到预览模式，并设置当前活动锚点。
- Artifact Markdown 渲染会在标题、段落、列表项和表格单元格文本中高亮第一个匹配锚点。
- 高亮元素带 `data-artifact-anchor-highlight="true"`，便于测试和后续滚动定位。
- 如果当前 artifact 中找不到锚点文本，不改变正文，不报错。

## Non-Goals

- 不做跨节点精确 offset 高亮。
- 不做多处匹配选择器。
- 不持久化当前活动锚点。
- 不新增顶栏入口或独立侧栏。

## Acceptance

1. 带 `anchorText` 的批注显示 `定位正文`。
2. 点击 `定位正文` 后，正文中对应文本被 `<mark>` 高亮。
3. 不带 `anchorText` 的批注不显示定位操作。
4. 现有 Mermaid、结构化可视化、批注回复/解决状态、导出和历史测试不退化。

## Verification

- `npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx`
- `npm run lint`
- `npm run build`
- `git diff --check`
