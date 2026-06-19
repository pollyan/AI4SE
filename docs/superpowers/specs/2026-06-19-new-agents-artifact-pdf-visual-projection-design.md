# New Agents Artifact PDF 可视化投影设计

## Current State Gap Analysis

事实源快照：
- 已读取：`docs/todos/new-agents-ux-professionalization.md`、`tools/new-agents/frontend/src/components/ArtifactPane.tsx`、`tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`、`tools/new-agents/frontend/src/core/structuredVisuals.ts`。
- 当前 PDF 已支持分页和 Markdown 文本布局，但 Mermaid / `ai4se-visual` fenced block 仍按代码块输出，用户在 PDF 中会看到 Mermaid 语法或 JSON，而不是专业可读的图表信息。

能力包聚合：

| 能力包 | 聚合的原始缺口 | 用户动作链 / 工程信任闭环 | 为什么不能再拆薄 | 验收证据 |
| --- | --- | --- | --- | --- |
| PDF 可视化语义投影 | PDF Mermaid/结构化可视化图形化导出仍未完成；当前导出泄露语法/JSON | 用户下载 PDF -> PDF 中看到 Mermaid 图表摘要和结构化可视化行 -> 不再需要读代码块 | 只过滤 fence 没价值，必须保留图表语义、标题、列和行 | ArtifactPane PDF 下载测试 |
| PDF 真正图形化 | Mermaid SVG/Canvas 渲染进 PDF、结构化表格边框 | 用户下载 PDF -> 图表以图形呈现 | 需要浏览器渲染截图或 PDF 图形绘制，本轮风险高 | 视觉/像素或 PDF 结构测试 |
| 服务端 PDF 渲染 | 后端统一生成带图形 PDF | 下载 -> 服务端生成高保真 PDF | 需要新 API 和渲染依赖 | API/集成测试 |

排序结论：
1. 选择“PDF 可视化语义投影”，因为它能立即避免 PDF 出现 Mermaid/JSON 原文，提升客户可读性。
2. 真正图形化和服务端渲染保留为后续；本轮不假装完成图形绘制。

切片厚度门禁：
- 入口：ArtifactPane 下载菜单 `PDF`。
- 动作：用户导出包含 Mermaid 或 `ai4se-visual` 的产出物。
- 处理：PDF 文本投影阶段识别 special fence，转为图表摘要和结构化行。
- 可见结果：PDF 文本中出现 `Mermaid 图表`、图表类型、结构化可视化标题、列和行；不再出现原始 JSON 字段。
- 状态承接：不改变 artifact、history 或服务端状态。
- 失败反馈：无效 `ai4se-visual` 输出错误摘要，不吞掉异常。
- 证据：组件测试读取 PDF 字符串中的 UTF-16BE 文本。

## 用户故事

作为下载专业产出物的用户，当产出物中包含 Mermaid 或 `ai4se-visual` 时，我希望 PDF 至少保留图表语义和结构化表格内容，而不是直接显示 Mermaid 代码或 JSON。

## 验收条件

1. Given artifact 包含 Mermaid fenced block
   When 用户导出 PDF
   Then PDF 包含 `Mermaid 图表` 和图表类型摘要，不包含 Mermaid fence 标记。

2. Given artifact 包含合法 `ai4se-visual`
   When 用户导出 PDF
   Then PDF 包含结构化可视化标题、列名和行值，不包含原始 JSON 字段文本。

3. Given artifact 包含非法 `ai4se-visual`
   When 用户导出 PDF
   Then PDF 包含结构化可视化错误摘要，便于用户定位问题。

## 非目标

- 不把 Mermaid 渲染成 SVG/Canvas 图片。
- 不绘制 PDF 表格边框。
- 不新增导出服务端 API。
- 不改变右侧 ArtifactPane 预览渲染。
