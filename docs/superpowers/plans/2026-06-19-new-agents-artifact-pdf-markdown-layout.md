# New Agents Artifact PDF Markdown Layout Plan

## Steps

1. 在 `ArtifactPane.test.tsx` 新增 RED 测试，覆盖 Markdown PDF 导出中的标题、列表、表格和代码块清理。
2. 运行组件测试，确认当前实现因为导出 Markdown 源文本而失败。
3. 在 `ArtifactPane.tsx` 新增 PDF 文本投影 helper，复用现有 Markdown block 识别逻辑。
4. 将 `buildPlainTextPdf` 的输入从源 Markdown 行改为投影后的 PDF 文本行，保留现有分页与 UTF-16BE 编码。
5. 运行组件测试、TypeScript 检查、前端构建和 diff 检查。
6. 更新 `docs/todos/new-agents-ux-professionalization.md` 的 Artifact 协作进展记录。
