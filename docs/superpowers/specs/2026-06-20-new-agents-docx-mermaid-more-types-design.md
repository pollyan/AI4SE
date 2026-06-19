# New Agents DOCX Mermaid More Types Design

## Current State Gap Analysis

事实源快照：
- 已读取：`docs/todos/new-agents-ux-professionalization.md`、`tools/new-agents/frontend/src/core/docxExport.ts`、`tools/new-agents/frontend/src/core/__tests__/docxExport.test.ts`。
- 当前能力：DOCX 导出已经把 Mermaid `flowchart` / `graph` 转成安全本地 SVG media，并在 Word 文档中通过 `w:drawing` 引用；其他 Mermaid 类型只保留文本语义投影。
- 当前剩余：todo P1 #7 明确保留 `DOCX 更多 Mermaid 类型嵌入`，P0 #3 / P1 #4 也强调专业产出物和可视化交付质量。

候选排序：

| 候选 | 用户价值 | 范围 | 风险 | 去向 |
| --- | --- | --- | --- | --- |
| DOCX `timeline` + `mindmap` SVG 嵌入 | 故障复盘 timeline、创意/问题树 mindmap 在 Word 中可见为图形 | `docxExport.ts` + `docxExport.test.ts` | 低到中；只扩展 core 导出 | 本轮 |
| DOCX `pie` + `journey` SVG 嵌入 | 分布图和旅程图更专业 | 解析和布局更复杂 | 中；journey 语义较多 | 后续 |
| PDF 图片级 SVG 嵌入 | PDF 更高保真 | `ArtifactPane.tsx` 大文件和 PDF 对象结构 | 高 | 后续 |
| 移动语义自动合并 | 协作合并增强 | `ArtifactPane.tsx` 冲突逻辑 | 高 | 后续 |

切片准入判断：
- 用户动作链：右侧产物包含 Mermaid timeline/mindmap -> 用户下载 Word/DOCX -> Word 中看到真实图形，而非只有文本摘要。
- 相邻缺口合并：本轮只合并 timeline/mindmap 两类，避免一次性吃下 journey/pie/PDF。
- 架构约束：继续复用共享 DOCX 导出路径，不新增 Lisa/Alex/workflow 专属分支，不把模型生成的任意 SVG/HTML 原样写入包。
- 能力增量句：完成后，DOCX 对工作流常见的时间线和问题树图也能输出本地 SVG media。

## 用户故事

作为把 Agent 产出物交付给客户的用户，当产物里包含事件时间线或问题树 / mindmap 时，我下载 Word 文档后能看到实际图形，并且仍能复制图表标题和节点文字，而不是只能看到 Mermaid 源码或纯文本摘要。

## 验收条件

1. Given 文档中包含 Mermaid `timeline`
   When 调用 `buildDocxPackage`
   Then DOCX 包包含 `word/media/mermaid-1.svg`、`word/_rels/document.xml.rels`、`w:drawing`，SVG 中包含标题、section 和事件文本。

2. Given 文档中包含 Mermaid `mindmap`
   When 调用 `buildDocxPackage`
   Then DOCX 包包含 SVG media，SVG 中包含 root 和子节点文本，并转义潜在 HTML。

3. Given timeline/mindmap 被图形化
   Then `word/document.xml` 仍保留 `Mermaid 图表：timeline` 或 `Mermaid 图表：mindmap` 与可搜索语义文本，并不暴露 fenced source。

4. Given 不支持或无法解析的 Mermaid 类型
   Then 保持现有文本语义投影和降级路径，不阻断 DOCX 下载。

## 边界

- 不改 ArtifactPane / PDF 导出。
- 不做浏览器截图或 Mermaid runtime 渲染。
- 不支持任意 SVG/HTML 输入，只用本地保守投影生成 SVG。
- 不新增 workflow-specific 导出分支。
- 本轮不做 pie/journey；保留为后续切片。

## 验证计划

- `cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/docxExport.test.ts`
- `cd tools/new-agents/frontend && npm run lint`
- `cd tools/new-agents/frontend && npm run build`
- `git diff --check`

## 实现结果

- DOCX Mermaid 本地 SVG media 投影从 `flowchart/graph` 扩展到 `timeline` 与 `mindmap`。
- `timeline` 投影会清洗 `title` / `section` 控制行，生成白底时间轴、分段标签和事件卡片，并保留标题、分段、时间点与事件文本作为可搜索 DOCX 语义段落。
- `mindmap` 投影会按缩进层级生成节点框和父子连接线，清洗 `root((...))`、`[...]`、`(...)` 等常见节点包装，并保留节点文本作为可搜索 DOCX 语义段落。
- SVG 内容继续由本地保守投影生成，所有文本走 XML 转义；不支持或无法解析的 Mermaid 类型仍走文本语义投影降级，不阻断下载。
