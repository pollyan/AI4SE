# New Agents Artifact Section Memo Rendering 设计

## Current State Gap Analysis

- 右侧 ArtifactPane 主预览当前把整篇 `displayContent` 交给单个 `ReactMarkdown`。
- Store 已能维护完整 artifact 事实源、章节变更索引，并能通过 `replace` / `add_after` patch 局部更新完整 markdown。
- 仍缺少 UI 层的章节级 memoization；即使只有一个章节变化，主预览仍会让整篇 Markdown renderer 重新执行。

## Selected Slice

只拆分主预览：

- 使用已存在的 Markdown heading anchor 规则把 `displayContent` 拆成可 memo 的 render blocks。
- 每个 block 独立调用 `ReactMarkdown`，并通过 `React.memo` 保持未变化 block 不重新渲染。
- Mermaid / 结构化视觉诊断仍使用全篇 blockIndex 语义；每个 block 根据前序内容计算 index offset。
- 历史版本预览、diff、编辑 textarea、导出、评论、锁定、保存路径继续使用完整 `artifactContent`。

## Acceptance

- 组件测试可证明更新第二个章节时，第一个章节的 mocked `ReactMarkdown` 不重新渲染。
- 主预览仍显示同样的 Markdown 内容。
- Mermaid / structured visual blockIndex 不因 section split 改变。
- 全量 ArtifactPane 测试、前端 lint、前端全量测试通过。

## Non-goals

- 不虚拟化长文档。
- 不改历史版本 preview。
- 不改变 markdown 样式或协作功能。
- 不引入 workflow / agent 专属渲染路径。
