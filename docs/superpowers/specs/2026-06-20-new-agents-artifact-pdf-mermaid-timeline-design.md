# New Agents Artifact PDF Mermaid Timeline 投影设计

## Current State Gap Analysis

### 事实源快照

- `docs/todos/new-agents-ux-professionalization.md`
- `docs/superpowers/specs/2026-06-20-new-agents-artifact-pdf-mermaid-vector-design.md`
- `docs/superpowers/plans/2026-06-20-new-agents-artifact-pdf-mermaid-vector.md`
- `tools/new-agents/frontend/src/components/ArtifactPane.tsx`
- `tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`
- `tools/new-agents/frontend/src/core/prompts/incident_review/timeline.ts`

### 能力包聚合

| 能力包 | 原始缺口 | 用户动作链 / 工程闭环 | 为什么不能再拆薄 | 验收证据 |
| --- | --- | --- | --- | --- |
| PDF Timeline 图形化投影 | PDF 已能画 flowchart，但 incident timeline 等非 flowchart Mermaid 仍是文本摘要。 | 用户生成故障复盘 timeline -> 下载 PDF -> PDF 中能看到时间轴骨架和事件节点。 | 只改文案无法提升导出专业感；只支持解析不绘图对用户不可见。 | ArtifactPane PDF 导出测试断言 timeline 文本和矢量命令。 |
| 更完整 Mermaid/SVG 嵌入 | 复杂 Mermaid 高保真仍不足。 | 用户下载 PDF/DOCX -> 图表接近预览效果。 | 涉及 SVG/raster 渲染、字体、分页和异步渲染，超出当前小切片。 | 后续专门验收。 |
| 更复杂三方合并 | Artifact 冲突改写/移动仍可增强。 | 用户处理冲突 -> 自动/半自动合并更多语义场景。 | 与 PDF 专业交付不是同一用户动作链。 | 后续冲突测试。 |

### 候选 gap

| 候选 | 来源 | 目标态 | 当前能力 | 缺口 | 价值 | 风险/复杂度 | 可测试性 | 去向 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PDF Timeline 图形化投影 | P1 Artifact 高保真导出剩余项 | `timeline` Mermaid 在 PDF 中有可见时间轴和事件框。 | 只有 flowchart/graph 会绘制矢量骨架。 | timeline 仍只有文本摘要。 | 覆盖故障复盘首阶段，提升专业交付第一印象。 | 中：需要扩展同一 PDF projection，但不引入依赖。 | 前端 PDF 导出测试可直接检查 content stream。 | 本轮 |
| PDF mindmap / journey 图形化投影 | P1 可视化导出剩余项 | mindmap/journey 在 PDF 中有树状/旅程骨架。 | 文本摘要。 | 类型语义更复杂。 | 价值高。 | 高于 timeline。 | 可测但布局复杂。 | 后续 |
| 改写/移动语义自动合并 | P1 Artifact 协作剩余项 | 更复杂冲突自动处理。 | 已支持插入、删除、修改块保留/采纳。 | 移动/改写仍需人工。 | 协作增强。 | 中高。 | ArtifactPane 测试。 | 后续 |

### 排序结论

1. 选择 PDF Timeline 图形化投影，因为它直接回应“产出物更专业、可视化更丰富”的目标，且能在现有 PDF 导出架构内形成独立可验收增量。
2. mindmap/journey 暂不选，因为布局更复杂，适合在 timeline 证明非 flowchart 扩展点后继续推进。
3. 更复杂冲突合并暂不选，因为当前 Artifact 协作已经连续补了多个冲突处理切片，本轮优先回到专业交付质量。

### 切片厚度门禁

- 入口：ArtifactPane 下载菜单中的 `PDF`。
- 动作：用户导出包含 Mermaid `timeline` 的产出物。
- 处理：Markdown -> PDF 投影阶段识别 timeline，content stream 阶段绘制时间轴、刻度、事件框和连接线。
- 可见结果：PDF content stream 包含 timeline 专属矢量绘制命令；文本仍保留事件时间和描述。
- 状态承接：不改变 artifact 内容、run snapshot 或预览，只增强导出。
- 失败反馈：无法解析的 timeline 保持现有文本摘要降级，不阻断下载。
- 证据：先写失败测试，再实现，运行 ArtifactPane 测试、lint/build 和 `git diff --check`。
- 结论：通过。该切片不是单 helper，而是完整导出动作链的一段可见能力增强。

## 本轮 Milestone

作为 New Agents 用户，当我导出包含故障复盘 Mermaid `timeline` 的 Artifact PDF 时，我可以在 PDF 中看到时间轴式矢量骨架和事件节点，而不是只看到源码文本，从而提升复盘文档的专业交付感。

## 范围

- 扩展 Artifact PDF 的 Mermaid 投影模型，支持 `timeline`。
- 对简单 timeline 语法提取 section、时间点和事件描述。
- 在 PDF content stream 中绘制时间轴线、刻度、事件框和连接线。
- 保留现有可搜索文本摘要和降级路径。

## 非目标

- 不引入浏览器截图、canvas、SVG 渲染或新依赖。
- 不追求与 Mermaid runtime 完全一致的视觉渲染。
- 不改变 PDF 下载入口、DOCX 导出、Markdown 导出或 Artifact 预览。
- 不为 Incident Review 或某个 workflow 创建专属导出分支。

## 验收条件

1. 含 `timeline` Mermaid 的 PDF 导出保留 `Mermaid 图表：timeline`、section、时间点和事件描述文本。
2. PDF content stream 包含 Mermaid 绘制色、时间轴横线、刻度线、事件框和连接线。
3. 现有 flowchart PDF 矢量绘制和结构化表格绘制测试继续通过。
4. 无法解析的非支持 Mermaid 继续按文本摘要导出，不阻断 PDF。
