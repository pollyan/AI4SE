# New Agents Artifact PDF Mermaid 矢量投影设计

## 背景

Artifact PDF 导出已经支持 Markdown 文本整理、分页、结构化可视化表格线绘制，以及 Mermaid 的可搜索文字摘要。但 Mermaid 在 PDF 中仍只是源代码文本，用户拿到导出文档时缺少图形化信息，不利于展示系统边界、流程、依赖关系等专业产出。

## 目标

- 对简单 `flowchart` / `graph` Mermaid 代码块生成 PDF 原生矢量图形骨架。
- 在 PDF content stream 中绘制节点矩形、连接线和箭头，形成可见流程图。
- 保留 Mermaid 摘要和节点标签文本，确保 PDF 仍可搜索和可读。
- 复用现有 Artifact PDF 导出路径，不新增 agent/workflow 专属导出分支。

## 非目标

- 不引入浏览器截图、canvas 渲染或异步 Mermaid runtime 到下载链路。
- 不追求完整 Mermaid 语法渲染一致性。
- 不改变 DOCX、Markdown 导出。
- 不改变 Artifact 内容或前端预览渲染。

## 设计

1. Markdown 投影阶段：
   - 解析 Mermaid fence。
   - 对 `flowchart` / `graph` 提取节点和边。
   - 额外保留节点标签为 PDF 文本行。
   - 记录 `PdfMermaidDiagram` 元数据，包括起始行、节点和边。
2. PDF content stream 阶段：
   - 根据 diagram 起始行估算当前页位置。
   - 绘制节点矩形。
   - 绘制节点间连接线和简化箭头。
   - 与结构化表格绘制命令并存。
3. 降级策略：
   - 解析失败或非 flowchart/graph Mermaid 不绘制图形。
   - 原有 Mermaid 文本摘要仍保留，PDF 导出不中断。

## 验收

- 含简单 Mermaid flowchart 的 PDF content stream 包含节点矩形绘制命令。
- PDF content stream 包含连接线绘制命令。
- PDF 文本中保留 Mermaid 类型、节点标签和原始 Mermaid 边描述。
- 既有结构化表格 PDF 绘制测试继续通过。
