# New Agents Artifact DOCX Mermaid SVG 嵌入设计

## Current State Gap Analysis

事实源快照：
- 已读取：`AGENTS.md`、`docs/strategy/goal-mode-playbook.md`、`docs/index.md`、`docs/todos/new-agents-ux-professionalization.md`、`tools/new-agents/frontend/src/core/docxExport.ts`、`tools/new-agents/frontend/src/core/__tests__/docxExport.test.ts`、`tools/new-agents/frontend/src/components/ArtifactPane.tsx`、`tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`。
- 子 Agent 只读探索：Zeno 审计 Artifact 导出剩余缺口；Epicurus 审计 Artifact 协作/合并剩余缺口。
- 按需未展开：后端 collaboration 持久化细节，本轮不修改协作 API。

能力包聚合：

| 能力包 | 聚合的原始缺口 | 用户动作链 / 工程信任闭环 | 为什么不能再拆薄 | 验收证据 |
| --- | --- | --- | --- | --- |
| DOCX Mermaid SVG 嵌入 | Artifact 导出剩余：复杂 Mermaid/SVG 高保真图片级嵌入；DOCX 当前只有文本语义投影 | 用户在 ArtifactPane 点击 Word 下载 -> 系统生成 docx -> Word 中有实际 Mermaid 图形和可搜索摘要 | 只改 package 结构没有用户价值；必须同时生成 media、relationship、document drawing 和文本摘要 | DOCX ZIP entry、document.xml、rels、SVG 内容测试；前端 lint/build |
| 重复标题精确锚点 | Artifact 协作剩余：重复标题精确锚点、移动语义自动合并前置能力 | 用户锁定或合并同名章节 -> 系统区分具体章节 -> 后续合并更安全 | 只加字段不够，必须连到 UI、store、服务端 snapshot 和合并逻辑 | ArtifactPane/store/runSnapshot/backend 测试 |

候选 gap：

| 候选 | 来源 | 目标态 | 当前能力 | 缺口 | 价值 | 风险/复杂度 | 可测试性 | 去向 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| DOCX Mermaid SVG 嵌入 | Todo P1 #7、Zeno 探索 | 支持 flowchart/graph Mermaid 作为 SVG media 嵌入 docx，同时保留文本摘要 | DOCX 已是真包，Markdown 表格是真表格，Mermaid 仍是文本投影 | Word 打开后看不到实际图形 | 更接近专业交付物，客户能在 Word 中看到可视化 | OOXML relationship/drawing 结构需谨慎；先限制为本地生成的 flowchart/graph SVG | `docxExport.test.ts` 可直接解析 ZIP entry | 本轮 |
| 重复标题精确锚点 | Todo P1 #7、Epicurus 探索 | 同名章节可精确锁定与合并 | 章节锁与自动合并以 heading 为主，重复标题保守降级 | 同名章节会难以区分 | 改善协作可信度，为移动合并铺路 | 跨前后端 schema/API/UI，改动面更大 | 多层测试可覆盖 | 下一轮候选 |

排序结论：
1. 选择 DOCX Mermaid SVG 嵌入，因为它直接兑现用户对“专业产出物、高保真导出、可视化”的反馈，文件边界主要集中在 `docxExport`，可形成较小且可验证的专业交付物能力包。
2. 重复标题精确锚点暂不选，因为它是后续协作合并的基础能力，但需要跨前后端持久化和 ArtifactPane UI，适合下一个独立 worktree 切片。

切片准入判断：
- 用户可感知动作链：右侧产物 -> 下载 Word -> 打开 docx -> 看到 Mermaid 图形和文本摘要。
- 相邻缺口合并：本轮合并 DOCX package media、relationship、document drawing 和 SVG 安全生成；不合并 PDF 图片级嵌入。
- Superpowers 成本合理性：导出格式影响客户交付观感，且有明确可测试二进制包结构。
- 过薄风险检查：不是单 helper；完成后 Word 导出能力发生用户可观察变化。
- 能力增量句：完成后，用户现在可以把含有简单 Mermaid flowchart/graph 的 Artifact 导出为包含真实 SVG 图形的 DOCX。

切片厚度门禁：
- 入口：ArtifactPane 下载菜单的 Word 导出。
- 动作：用户下载当前阶段产出物。
- 处理：DOCX 构建器识别支持的 Mermaid flowchart/graph，生成本地 SVG media part、document relationship 和 drawing 引用。
- 可见结果：Word 文档中出现 Mermaid 图形，同时保留 `Mermaid 图表：flowchart` 和节点/边摘要文本。
- 状态承接：不改变 run、artifact history 或协作状态；只影响导出文件。
- 失败反馈：不支持或无法解析的 Mermaid 继续走现有文本摘要降级，不阻断下载。
- 证据：DOCX ZIP entry 和 XML/SVG 断言、docxExport 单测、ArtifactPane 下载回归、lint/build、`git diff --check`。
- 结论：通过。

## 用户故事

作为 Lisa/Alex 工作区用户，当我已经在右侧产物中获得 Mermaid 流程图或系统边界图时，我可以下载 Word 文档并在 Word 中看到实际图形，而不是只能看到文字化的“Mermaid 图表”摘要，从而更容易把产出物交给团队评审或客户沟通。

## 验收条件

1. Given Artifact Markdown 包含简单 Mermaid `flowchart` 或 `graph`
   When 用户下载 DOCX
   Then DOCX ZIP 包包含 `word/media/mermaid-1.svg`、`word/_rels/document.xml.rels`，`word/document.xml` 包含 `w:drawing` 与 `r:embed`，并保留节点文本摘要。

2. Given Mermaid 中包含 HTML / script-like 标签或特殊字符
   When 生成 DOCX SVG
   Then SVG 文本被 XML 转义，不出现 `<script>`、`foreignObject` 或事件属性。

3. Given Mermaid 类型暂不支持或解析失败
   When 用户下载 DOCX
   Then 导出继续成功，保持现有文本语义投影，不阻断用户。

## 边界

- 只覆盖本地可解析的 Mermaid `flowchart` / `graph` SVG media 嵌入。
- 不调用浏览器 Mermaid runtime，不依赖右侧预览 DOM。
- 不把模型输出的任意 SVG/HTML 原样写入 DOCX。
- 不做 PDF 图片级嵌入，不做完整 Mermaid 语法兼容。
- 不新增 Lisa/Alex/workflow 专属导出分支。

## 验证计划

- `cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/docxExport.test.ts src/components/__tests__/ArtifactPane.test.tsx`
- `cd tools/new-agents/frontend && npm run lint`
- `cd tools/new-agents/frontend && npm run build`
- `git diff --check`
