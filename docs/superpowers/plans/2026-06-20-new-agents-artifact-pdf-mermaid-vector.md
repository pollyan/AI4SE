# New Agents Artifact PDF Mermaid 矢量投影计划

## 范围

将 Artifact PDF 导出中的简单 Mermaid flowchart 从纯文本摘要推进到可见的 PDF 矢量图形骨架。

## 步骤

1. 补失败测试：
   - 准备包含三节点 Mermaid flowchart 的 Artifact。
   - 下载 PDF。
   - 断言 PDF 保留节点标签文本。
   - 断言 PDF content stream 包含 Mermaid 专属绘制颜色、多个矩形和连线命令。
2. 实现 Mermaid 解析：
   - 支持 `flowchart` / `graph`。
   - 提取 `A[标签] --> B[标签]` 形式的节点和边。
   - 避免后续无标签节点覆盖已解析标签。
3. 扩展 PDF 投影模型：
   - 在 `PdfProjectedDocument` 中保存 Mermaid diagram 元数据。
   - 保留原有 Mermaid 文字摘要和源边描述。
4. 扩展 PDF 绘制：
   - 按页面位置绘制节点矩形。
   - 绘制连接线和简化箭头。
   - 与现有结构化表格绘制命令合并输出。
5. 验证：
   - 聚焦测试先失败后通过。
   - 运行 ArtifactPane 相关测试和 store 测试。
   - 运行 frontend lint/build 与 `git diff --check`。
