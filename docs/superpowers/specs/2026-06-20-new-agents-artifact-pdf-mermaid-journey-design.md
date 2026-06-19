# New Agents Artifact PDF Mermaid Journey 投影设计

## Current State Gap Analysis

### 事实源快照

- `docs/todos/new-agents-ux-professionalization.md`
- `tools/new-agents/frontend/src/components/ArtifactPane.tsx`
- `tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`
- `tools/new-agents/backend/agent_contracts.py`
- `tools/new-agents/frontend/src/core/prompts/value_discovery/journey.ts`

### 能力包聚合

| 能力包 | 原始缺口 | 用户动作链 / 工程闭环 | 为什么不能再拆薄 | 验收证据 |
| --- | --- | --- | --- | --- |
| PDF Journey 图形化投影 | `VALUE_DISCOVERY/JOURNEY` contract 强制 Mermaid `journey`，但 PDF 仍按源码摘要降级。 | 用户完成价值发现旅程分析 -> 下载 PDF -> PDF 中看到旅程阶段、任务和情绪评分的轻量图形骨架。 | 只清洗文本不解决“旅程图不是图”的交付感；只做 parser 不绘图对用户不可见。 | ArtifactPane PDF 测试断言 journey 清洗文本和矢量命令。 |
| SVG/图片级高保真嵌入 | 复杂 Mermaid/SVG 与预览仍不完全一致。 | 用户下载 PDF/DOCX -> 图表接近浏览器预览。 | 涉及 Mermaid runtime、SVG/raster、字体和分页，超出当前小切片。 | 后续专门验收。 |
| 重复标题精确锚点 | 章节锁/批注/合并仍以轻量文本锚点为主。 | 用户锁定或定位重复标题章节 -> 系统能精确定位。 | 与当前导出专业感不是同一动作链。 | 后续协作测试。 |

### 候选 gap

| 候选 | 来源 | 目标态 | 当前能力 | 缺口 | 价值 | 风险/复杂度 | 可测试性 | 去向 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PDF Journey 图形化投影 | P1 可视化导出剩余项 / required Mermaid | `journey` Mermaid 在 PDF 中有旅程阶段、任务卡片和情绪评分骨架。 | flowchart/timeline/mindmap/pie 已有轻量矢量投影。 | journey 仍只有源码摘要。 | 补齐价值发现旅程文档的专业导出体验。 | 中：只支持模板中的稳定子集。 | 前端 PDF content stream 测试。 | 本轮 |
| SVG/图片级高保真嵌入 | 高保真导出剩余项 | PDF/DOCX 嵌入接近预览的图形。 | 当前是无依赖矢量近似和语义投影。 | 不是真实 Mermaid 图像。 | 价值高。 | 高。 | 需要浏览器/SVG/PDF 证据。 | 后续 |
| 重复标题精确锚点 | Artifact 协作剩余项 | 重复标题也能精确锁定/定位。 | 多数协作能力已可用。 | 锚点仍轻量。 | 协作可靠性提升。 | 中高。 | 可测。 | 下一轮候选 |

### 排序结论

1. 选择 PDF Journey 图形化投影，因为它是当前 required Mermaid 中尚未图形化的主路径类型，且直接提升价值发现工作流交付物专业感。
2. SVG/图片级高保真暂不选，因为会跨越 runtime 渲染、图片嵌入和分页，风险大于本轮目标切片。
3. 重复标题精确锚点暂不选，因为它属于协作精度主线，不如本轮补齐 Journey PDF 交付链路直接。

### 切片厚度门禁

- 入口：ArtifactPane 下载菜单中的 `PDF`。
- 动作：用户导出包含 Mermaid `journey` 的价值发现旅程产出物。
- 处理：Markdown -> PDF 投影识别 `journey`、`title`、`section` 和任务评分行。
- 可见结果：PDF 中有旅程主线、阶段分隔、任务卡片和评分文本。
- 状态承接：不改变 artifact 内容、run snapshot 或预览，只增强导出。
- 失败反馈：无法解析或超复杂 journey 保持文本摘要降级，不阻断下载。
- 证据：先写失败测试，再实现，运行 ArtifactPane 测试、lint/build 和 `git diff --check`。
- 结论：通过。该切片形成完整导出动作链的可见增量。

## 本轮 Milestone

作为 New Agents 用户，当我导出价值发现用户旅程 Artifact PDF 时，我可以在 PDF 中看到旅程阶段、任务和情绪评分的轻量图形骨架，而不是 Mermaid journey 源码，从而让旅程分析更像专业交付文档。

## 范围

- 支持 Mermaid `journey` 的稳定子集：`title`、`section`、`任务: 评分: 角色`。
- 清洗为可搜索文本：标题、阶段、任务、评分和角色。
- 在 PDF content stream 中绘制旅程主线、阶段分隔和任务卡片。
- 保留现有 flowchart、timeline、mindmap、pie 和结构化表格绘制路径。

## 非目标

- 不引入浏览器截图、canvas、SVG 或新依赖。
- 不追求 Mermaid runtime 完全一致布局。
- 不支持所有 journey 扩展语法、actor 样式或主题。
- 不改变 DOCX、Markdown 导出或前端预览。

## 验收条件

1. 含 `journey` Mermaid 的 PDF 导出保留 `Mermaid 图表：journey`、标题、阶段和任务评分文本。
2. PDF 不再把 `title ...`、`section ...` 或原始 `任务: 评分: 角色` 行作为主要内容暴露。
3. PDF content stream 包含 Mermaid 绘制色、阶段/任务矩形和连接线。
4. 现有 flowchart、timeline、mindmap、pie 和结构化表格 PDF 测试继续通过。
