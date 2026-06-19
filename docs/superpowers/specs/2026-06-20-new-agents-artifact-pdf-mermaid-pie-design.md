# New Agents Artifact PDF Mermaid Pie 投影设计

## Current State Gap Analysis

### 事实源快照

- `docs/todos/new-agents-ux-professionalization.md`
- `tools/new-agents/frontend/src/components/ArtifactPane.tsx`
- `tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`
- `tools/new-agents/backend/agent_contracts.py`
- `tools/new-agents/frontend/src/core/prompts/req_review/report.ts`
- `tools/new-agents/frontend/src/core/prompts/incident_review/improvement.ts`
- `tools/new-agents/frontend/src/core/prompts/test_design/cases.ts`
- 只读 explorer 结论：PDF Mermaid 图形化目前覆盖 `flowchart/graph`、`timeline`、`mindmap`；`pie` 覆盖两个强制 contract 阶段，短期用户感知强于 `journey`。

### 能力包聚合

| 能力包 | 原始缺口 | 用户动作链 / 工程闭环 | 为什么不能再拆薄 | 验收证据 |
| --- | --- | --- | --- | --- |
| PDF Pie 图形化投影 | Mermaid `pie` 在 PDF 中仍是文本摘要；`REQ_REVIEW/REPORT` 与 `INCIDENT_REVIEW/IMPROVEMENT` 强制要求 `pie`。 | 用户生成评审报告或改进方案 -> 下载 PDF -> PDF 中看到分布图骨架、标题和分类值。 | 只清洗文本不能提供“统计图是图”的交付感；只写 parser 不绘制对用户不可见。 | ArtifactPane PDF 测试断言 pie 文本清洗和矢量绘制命令。 |
| PDF Journey 图形化投影 | `VALUE_DISCOVERY/JOURNEY` 强制 Mermaid `journey`。 | 用户下载价值发现旅程 PDF -> 看到旅程图骨架。 | 同阶段已有 `ai4se-visual journey-map` 表格绘制兜底，且 Mermaid journey 解析风险更高。 | 后续专门测试。 |
| 章节级冲突改写自动合并 | Artifact 冲突自动合并还不能处理非重叠章节改写。 | 用户在旧版本编辑不同章节 -> 保存冲突 -> 一键合并安全改写。 | 与当前导出专业感不是同一动作链。 | 后续冲突测试。 |

### 候选 gap

| 候选 | 来源 | 目标态 | 当前能力 | 缺口 | 价值 | 风险/复杂度 | 可测试性 | 去向 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PDF Pie 图形化投影 | P1 Artifact 高保真导出剩余项 / contract 强制 `pie` | `pie` Mermaid 在 PDF 中有轻量分布图和可搜索分类值。 | 所有 Mermaid 有语义文本摘要，只有 flowchart/timeline/mindmap 有矢量图形。 | `pie title ...` 与 `"label" : value` 仍按源码摘要进入 PDF。 | 覆盖需求评审报告、故障改进行动和测试用例优先级分布，专业交付感直接。 | 中：受控语法简单，不追求真实扇形。 | 前端 PDF content stream 测试。 | 本轮 |
| PDF Journey 图形化投影 | `VALUE_DISCOVERY/JOURNEY` required Mermaid | PDF 中显示旅程步骤骨架。 | `journey-map` 结构化表格已能绘制。 | Mermaid journey 仍无图形投影。 | 有价值但边际低于 pie。 | 中高。 | 可测。 | 下一轮候选 |
| Artifact 章节级非重叠改写自动合并 | Artifact 协作剩余项 | 安全章节改写冲突一键合并。 | 已支持插入、删除、行/块/修改块和部分自动合并。 | 不支持章节级非重叠改写自动合并。 | 提升协作效率。 | 中。 | 可测。 | 下一轮候选 |

### 排序结论

1. 选择 PDF Pie 图形化投影，因为它覆盖两个后端强制 contract 阶段，且继续回应用户最初强调的“全流程专业可视化”和“导出交付物专业性”。
2. Journey 暂不选，因为同阶段已经有 `ai4se-visual journey-map` 稳定兜底，Mermaid journey 的解析和布局复杂度更高。
3. Artifact 章节级改写自动合并暂不选，因为它属于协作体验主线，不如本轮导出可视化对专业交付物感知直接。

### 切片厚度门禁

- 入口：ArtifactPane 下载菜单中的 `PDF`。
- 动作：用户导出包含 Mermaid `pie` 的产出物。
- 处理：Markdown -> PDF 投影识别 `pie title` 与分类数值，清洗源码行，记录 diagram metadata。
- 可见结果：PDF 中有分布图轻量矢量骨架、分类值文本和统计图标题。
- 状态承接：不改变 artifact 内容、run snapshot 或预览，只增强导出。
- 失败反馈：无法解析或超复杂 `pie` 保持文本摘要降级，不阻断下载。
- 证据：先写失败测试，再实现，运行 ArtifactPane 测试、lint/build 和 `git diff --check`。
- 结论：通过。该切片形成完整导出动作链的可见增量。

## 本轮 Milestone

作为 New Agents 用户，当我导出包含评审问题优先级、改进行动优先级或测试用例优先级分布的 Artifact PDF 时，我可以在 PDF 中看到分布图形和分类数值，而不是 Mermaid pie 源码，从而让交付报告更像专业文档。

## 范围

- 支持 Mermaid `pie` 的稳定子集：`pie title 标题` 和 `"分类" : 数值` / `分类 : 数值`。
- 将标题和分类值清洗为可搜索 PDF 文本。
- 在 PDF content stream 中绘制轻量分布图：圆形轮廓、中心线和分类图例框。
- 保留现有 flowchart、timeline、mindmap 和结构化表格绘制路径。

## 非目标

- 不引入浏览器截图、canvas、SVG、PDF 图片嵌入或新依赖。
- 不追求 Mermaid runtime 完全一致扇形布局。
- 不支持所有 pie 扩展语法、样式、主题或百分比标签。
- 不改变 DOCX、Markdown 导出或前端预览。

## 验收条件

1. 含 `pie` Mermaid 的 PDF 导出保留 `Mermaid 图表：pie`、标题和分类值文本。
2. PDF 不再把 `pie title ...` 或 `"分类" : 数值` 作为主要内容暴露。
3. PDF content stream 包含 Mermaid 绘制色、圆形近似路径、图例矩形和连接/分隔线。
4. 现有 flowchart、timeline、mindmap 和结构化表格 PDF 测试继续通过。
