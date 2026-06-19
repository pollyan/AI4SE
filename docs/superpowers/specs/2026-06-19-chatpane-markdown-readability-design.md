# ChatPane 左侧 Markdown 可读性恢复设计

## 背景

`docs/todos/new-agents-evolution.md` P1 #10 记录用户反馈：左侧 assistant 对话变长后格式较差，看起来没有原来的 Markdown 格式。审计发现 `ChatPane` 已经使用 `ReactMarkdown` 和 `remarkGfm`，流式 content 存储也保留原始 Markdown；主要缺口是 message markdown components 只定制了段落、粗体、代码和表格，没有给列表、链接、引用、标题等基础 Markdown 元素提供可读样式。Tailwind preflight 会重置列表默认样式，导致列表层级尤其不明显。

## 用户故事

作为 New Agents 使用者，当 assistant 在左侧对话里输出较长的总结、方法说明、关键风险和下一步引导时，我希望列表、强调、行内代码、代码块、链接和段落层级保持清晰，而不是退化成难以扫描的纯文本。

## 范围

进入本轮：

- 为 `ChatPane` assistant/user message Markdown 增加基础组件样式：列表、列表项、链接、引用、标题、斜体、分割线。
- 保持现有 `ReactMarkdown`、`remarkGfm` 和 `createMarkdownCodeRenderer` 管线，不新增解析器。
- 增加组件测试，使用真实 `ReactMarkdown` 验证 assistant 长 Markdown 回复的结构样式。
- 更新 todo 进展记录。

不进入本轮：

- 不允许左侧对话重新承载完整 artifact 正文。
- 不修改 chat/artifact 服务层职责分离协议。
- 不重写 ChatPane 布局。

## 验收条件

1. assistant 消息中的 Markdown 列表渲染为带 `list-disc` 或 `list-decimal` 的列表。
2. 链接、强调、行内代码和代码块具备可读样式。
3. 现有 ChatPane 行为和阶段确认控件测试继续通过。
4. 不新增独立 Markdown 解析管线。

## 验证计划

- 先写失败组件测试。
- 更新 `ChatPane` Markdown components。
- 运行 ChatPane 组件测试和 diff 检查。
