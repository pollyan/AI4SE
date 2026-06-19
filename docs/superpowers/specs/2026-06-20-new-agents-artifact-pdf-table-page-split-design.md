# New Agents Artifact PDF Table Page Split Design

## Current State Gap Analysis

Artifact PDF 导出已经能为 `ai4se-visual` 结构化可视化绘制基础表格边框。但长风险矩阵、覆盖矩阵或行动看板跨页时，只有表格起始页会绘制边框，后续页面虽然保留文本，却缺少表格视觉结构，导出物的专业感和可读性会下降。

候选能力包：

- 按页片段绘制：用结构化表格在 PDF 文本行中的全局位置与当前页范围求交集，每个包含表格行的页面绘制当前页可见片段的外框、列线和行线。
- 完整跨页表格排版：重复表头、自动计算行高、跨页断行和单元格换行，复杂度较高。
- 引入 PDF 排版库：能力更完整，但会改变当前无依赖导出路径。

本轮选择按页片段绘制。

## User Story

作为 New Agents 用户，当我导出包含大量风险项或测试覆盖项的 PDF 时，即使表格跨到第二页，后续页面也应保留表格边界，便于客户扫描和阅读。

## Scope

- 计算结构化表格的表头/数据行在 PDF 文本流中的起止行。
- 对每个 PDF 页面，判断该页是否包含表格行。
- 对包含表格行的页面绘制该页可见片段的外框、列分隔线和行分隔线。
- 保留现有文本分页、可搜索文本和短表格绘制行为。

## Non-Goals

- 不重复表头。
- 不做单元格自动换行或真实行高测量。
- 不嵌入 Mermaid/SVG 图片。
- 不引入第三方 PDF 排版引擎。

## Acceptance

1. 长 `ai4se-visual` 导出为两页 PDF 时，第二页也包含表格矩形绘制指令。
2. PDF 仍包含最后一行结构化表格文本。
3. 短表格绘制、普通分页、Mermaid 文本摘要和既有 Artifact 行为不退化。

## Verification

- `npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx`
- `npm run lint`
- `npm run build`
- `git diff --check`
