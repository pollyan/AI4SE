# New Agents Artifact PDF Structured Table Drawing Design

## Current State Gap Analysis

Artifact PDF 导出已经能把 Mermaid 和 `ai4se-visual` 转成可读文本，避免客户在 PDF 中看到 fenced code 或原始 JSON。但结构化可视化仍然只是被摊平成多行文本，没有表格外框、行列边界或任何图形化信号，专业交付感不足。

候选能力包：

- 结构化可视化表格绘制：在 PDF content stream 中为 `ai4se-visual` 生成基础外框、行线和列线，同时保留原有文本，便于搜索和复制。
- Mermaid SVG/图片嵌入：需要浏览器渲染、SVG/image 编码和 PDF image object，复杂度更高。
- 完整 PDF 排版引擎：支持分页表格、字体嵌入、图文流式布局，当前切片过重。

本轮选择结构化可视化表格绘制。

## User Story

作为 New Agents 用户，当我把右侧专业产出物导出为 PDF 时，风险矩阵、覆盖矩阵、行动看板等结构化可视化不只是纯文字，而是带基础表格视觉边界，能更像一份可交付文档。

## Scope

- PDF 投影从纯文本行扩展为轻量 document：文本行加结构化表格元数据。
- 对合法 `ai4se-visual` 记录列、行和起始行号。
- PDF content stream 为当前页内的结构化表格绘制外框、列分隔线和行分隔线。
- 原有文本内容继续保留，确保 PDF 仍可搜索、测试仍能断言导出内容。
- 保持现有 Markdown、分页、Mermaid 文本摘要和下载入口不变。

## Non-Goals

- 不把 Mermaid 渲染为 SVG/图片嵌入 PDF。
- 不处理跨页表格拆分。
- 不引入第三方 PDF 排版库。
- 不做复杂字体嵌入、表头背景色或单元格自动换行。

## Acceptance

1. 导出包含 `ai4se-visual` 的 PDF 时，content stream 包含 `re S`、`m`、`l S` 等基础绘制操作。
2. PDF 仍包含结构化可视化标题、列和行文本。
3. 既有普通 PDF、Markdown 表格、Mermaid 摘要、分页导出测试不退化。

## Verification

- `npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx`
- `npm run lint`
- `npm run build`
- `git diff --check`
