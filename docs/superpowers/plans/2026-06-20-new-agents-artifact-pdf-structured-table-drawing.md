# New Agents Artifact PDF Structured Table Drawing Plan

## Steps

1. 写 RED 测试：包含 `ai4se-visual` 的 PDF 导出必须保留文本，并包含表格绘制操作。
2. 将 Markdown-to-PDF 投影扩展为轻量 document，记录结构化表格的列、行和起始行号。
3. 在 PDF content stream 中按页绘制结构化表格外框、列分隔线和行分隔线。
4. 运行目标组件测试，确认 RED 转 GREEN。
5. 运行完整 `ArtifactPane` 测试、lint、build、diff check。
6. 更新 `docs/todos/new-agents-ux-professionalization.md` 进展记录。
