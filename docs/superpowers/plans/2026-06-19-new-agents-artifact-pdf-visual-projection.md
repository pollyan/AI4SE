# New Agents Artifact PDF 可视化投影实施计划

## 范围

增强 ArtifactPane PDF 文本投影：识别 `mermaid` 与 `ai4se-visual` fenced block，将其转换为可读摘要和结构化文本行。

## TDD 步骤

1. RED：在 `ArtifactPane.test.tsx` 增加 PDF 导出测试，构造 Mermaid + `ai4se-visual risk-board`，断言 PDF 包含图表摘要、标题、列名和行值。
2. RED：断言 PDF 不再包含 Mermaid fence 标记和原始 JSON 字段文本。
3. GREEN：在 `ArtifactPane.tsx` 中引入 `parseStructuredVisual`。
4. GREEN：扩展 `projectMarkdownToPdfLines` 的 fenced block 处理：
   - `mermaid` 输出 `Mermaid 图表：<diagramType>` 和若干语义行。
   - `ai4se-visual` 输出 `结构化可视化：<title/type>`、列名、行值。
   - 非特殊 fence 保持原代码块投影。
5. 验证：运行 ArtifactPane 测试、组合测试、`npm run lint`、`npm run build`、`git diff --check`。

## 风险控制

- 只改 PDF 投影，不碰 artifact runtime、Mermaid 预览、结构化可视化组件或后端契约。
- `ai4se-visual` 复用现有 parser，避免另起一套协议。
- 保留真正图形化 PDF 为后续高保真切片。
