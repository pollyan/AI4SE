# New Agents Artifact PDF Markdown Layout Design

## Current State Gap Analysis

当前 ArtifactPane 已支持 Markdown、Word-compatible HTML 和多页 PDF 导出。PDF 导出已不再截断长文档，但仍直接把 Markdown 源文本写入 PDF，因此用户会在交付物里看到 `#`、`| --- |`、代码围栏等编辑态符号。该体验还没有满足 todo 中“Markdown 富排版 PDF”的目标。

候选能力包：

- PDF Markdown 结构化排版：沿用现有下载入口，把 Markdown 投影成更专业的 PDF 文本布局。该切片与刚完成的 PDF 分页属于同一用户动作链，可用组件测试验证。
- Artifact 批注与逐行接受/拒绝：协作价值更高，但涉及新状态模型和 UI 交互，适合作为独立后续切片。
- 真正 DOCX 导出：需要包级文档生成能力，当前不新增依赖，后续单独评估。

本轮选择 PDF Markdown 结构化排版。边界是不做 Mermaid 图形渲染进 PDF、不做真实 PDF 表格边框、不新增导出依赖。

## User Story

作为 Lisa/Alex 工作区用户，当我把右侧产出物导出为 PDF 时，我希望标题、列表、表格和代码块在 PDF 中更像交付文档，而不是带着 Markdown 源码符号的草稿。

## Scope

- 将 Markdown 标题投影为不含 `#` 的 PDF 文本行。
- 将无序/有序列表投影为项目符号或编号文本。
- 将 Markdown 表格投影为表头、分隔线和对齐后的文本行，不保留 `| --- |` 分隔符。
- 将 fenced code block 投影为缩进代码行，不导出 ``` 围栏。
- 继续复用现有 UTF-16BE 文本 PDF 和分页逻辑。

## Acceptance

1. 给定包含标题、列表、表格和代码块的 artifact，导出 PDF 后，PDF 内容流包含清理后的业务文本。
2. PDF 内容流不再包含对应的 Markdown 编辑态符号：`# 标题`、`| --- |`、```。
3. 长文档分页能力保持不退化。
4. 不新增 workflow-specific 或 agent-specific 导出分支。

## Verification

- `npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx`
- `npm run lint`
- `npm run build`
- `git diff --check`
