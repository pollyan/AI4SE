# New Agents Artifact PDF Mermaid Mindmap 投影设计

## Current State Gap Analysis

### 事实源快照

- `docs/todos/new-agents-ux-professionalization.md`
- `docs/superpowers/specs/2026-06-20-new-agents-artifact-pdf-mermaid-timeline-design.md`
- `tools/new-agents/frontend/src/components/ArtifactPane.tsx`
- `tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`
- `tools/new-agents/frontend/src/core/prompts/idea_brainstorm/define.ts`
- `tools/new-agents/frontend/src/core/prompts/incident_review/root_cause.ts`

### 能力包聚合

| 能力包 | 原始缺口 | 用户动作链 / 工程闭环 | 为什么不能再拆薄 | 验收证据 |
| --- | --- | --- | --- | --- |
| PDF Mindmap 图形化投影 | PDF 已支持 flowchart 和 timeline 的轻量矢量投影，但 mindmap 仍是文本摘要。 | 用户生成问题树/鱼骨图 -> 下载 PDF -> PDF 中可见树状骨架和节点。 | 只清洗文本不解决图形缺失；只写 parser 不绘图对用户不可见。 | ArtifactPane PDF 测试断言 mindmap 文本和矢量命令。 |
| 更完整 Mermaid/SVG 嵌入 | 复杂 Mermaid 高保真仍不足。 | 用户下载 PDF/DOCX -> 图表接近预览效果。 | 涉及 runtime SVG/raster、字体和分页，超出当前小切片。 | 后续专门验收。 |
| 改写/移动语义自动合并 | Artifact 冲突仍可继续自动化。 | 用户处理冲突 -> 系统识别更多安全语义。 | 与当前专业可视化交付动作链不同。 | 后续冲突测试。 |

### 候选 gap

| 候选 | 来源 | 目标态 | 当前能力 | 缺口 | 价值 | 风险/复杂度 | 可测试性 | 去向 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PDF Mindmap 图形化投影 | P1 Artifact 高保真导出剩余项 | `mindmap` Mermaid 在 PDF 中有树状节点和连接线。 | 只有 flowchart/graph/timeline 会绘制矢量骨架。 | mindmap 仍只有文本摘要。 | 覆盖创意问题树和故障根因鱼骨图，提升专业交付感。 | 中：需要支持缩进层级，但可做稳定子集。 | 前端 PDF 导出测试可检查 content stream。 | 本轮 |
| PDF Journey 图形化投影 | P1 可视化导出剩余项 | Mermaid journey 在 PDF 有旅程骨架。 | 文本摘要；另有 ai4se-visual journey-map。 | Mermaid journey 仍降级。 | 价值高但已有结构化兜底。 | 高于 mindmap。 | 可测但布局复杂。 | 后续 |
| 改写/移动语义自动合并 | P1 Artifact 协作剩余项 | 更多冲突场景自动合并。 | 已支持插入、删除和修改块。 | 移动/复杂改写仍人工。 | 协作增强。 | 中高。 | ArtifactPane 测试。 | 后续 |

### 排序结论

1. 选择 PDF Mindmap 图形化投影，因为它紧接 timeline 非 flowchart 扩展点，能覆盖 `IDEA_BRAINSTORM/DEFINE` 和 `INCIDENT_REVIEW/ROOT_CAUSE` 的专业图形导出。
2. Journey 暂不选，因为已有 `ai4se-visual journey-map` 表格化兜底，且 Mermaid journey 布局比 mindmap 更复杂。
3. 冲突合并暂不选，因为近期已连续补强多个协作切片，本轮继续消化用户最初强调的可视化与专业交付感。

### 切片厚度门禁

- 入口：ArtifactPane 下载菜单中的 `PDF`。
- 动作：用户导出包含 Mermaid `mindmap` 的产出物。
- 处理：Markdown -> PDF 投影识别 mindmap 缩进树，content stream 绘制节点框和树状连接线。
- 可见结果：PDF 中有 mindmap 专属矢量骨架；节点文本仍可搜索。
- 状态承接：不改变 artifact 内容、run snapshot 或预览，仅增强导出。
- 失败反馈：无法解析或超复杂 mindmap 保持文本摘要降级，不阻断下载。
- 证据：先写失败测试，再实现，运行 ArtifactPane 测试、lint/build 和 `git diff --check`。
- 结论：通过。该切片形成完整导出动作链的可见增量。

## 本轮 Milestone

作为 New Agents 用户，当我导出包含问题树或根因鱼骨图 Mermaid `mindmap` 的 Artifact PDF 时，我可以在 PDF 中看到树状图形骨架和节点文本，而不是只有源码摘要，从而提升头脑风暴和复盘文档的专业交付感。

## 范围

- 支持 Mermaid `mindmap` 的稳定子集：根节点、一级/二级缩进节点。
- 将节点文本清洗为可搜索 PDF 文本行。
- 在 PDF content stream 中绘制节点矩形和父子连接线。
- 保留现有 flowchart、timeline、结构化表格绘制路径。

## 非目标

- 不引入浏览器截图、canvas、SVG 或新依赖。
- 不追求 Mermaid runtime 完全一致布局。
- 不支持所有 mindmap 图标、markdown 装饰、深层复杂样式。
- 不改变 DOCX、Markdown 导出或前端预览。

## 验收条件

1. 含 `mindmap` Mermaid 的 PDF 导出保留 `Mermaid 图表：mindmap`、根节点和子节点文本。
2. PDF content stream 包含 Mermaid 绘制色、多个节点矩形和连接线。
3. 不再把 `mindmap` 控制行或 fenced marker 作为主要内容暴露。
4. 现有 flowchart、timeline 和结构化表格 PDF 测试继续通过。
