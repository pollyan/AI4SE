# New Agents Artifact Comment Anchor Highlight Plan

## Steps

1. 写 RED 测试：带 anchorText 的批注点击 `定位正文` 后正文出现高亮标记。
2. 在 ArtifactPane 中加入活动锚点状态和 `定位正文` 按钮。
3. 扩展 Markdown components，在常见文本容器中高亮第一个匹配锚点文本。
4. 点击定位时切换预览模式，并尝试滚动到高亮元素。
5. 运行组件测试、lint、build、diff check。
6. 更新 `docs/todos/new-agents-ux-professionalization.md` 进展记录。
