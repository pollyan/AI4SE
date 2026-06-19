# New Agents Artifact DOCX 表格高保真导出设计

## Current State Gap Analysis

事实源快照：
- 已读取：`AGENTS.md`、`docs/strategy/goal-mode-playbook.md`、`docs/todos/new-agents-ux-professionalization.md`、`tools/new-agents/frontend/src/core/docxExport.ts`、`tools/new-agents/frontend/src/core/__tests__/docxExport.test.ts`、`tools/new-agents/frontend/src/components/ArtifactPane.tsx`。
- 按需未展开：后端 runtime、SSE、workflow manifest。本切片只涉及前端 Artifact 导出，不改变 Agent Runtime 或 workflow 配置。

能力包聚合：
| 能力包 | 聚合的原始缺口 | 用户动作链 / 工程信任闭环 | 为什么不能再拆薄 | 验收证据 |
| --- | --- | --- | --- | --- |
| DOCX 表格高保真导出 | Artifact 协作体验深化、真正富文本 DOCX 导出、专业产出物交付感 | 用户在 ArtifactPane 点击 Word -> 系统生成 `.docx` -> Word 中表格是 OOXML 表格并带基础样式入口 | 只加样式或只改文件名都无法改变用户打开文档后的专业感；表格结构和 styles 入口必须一起闭环 | `docxExport` 单测解析 ZIP entry，断言 `word/document.xml` 含 `w:tbl` 且包内存在 `word/styles.xml` |
| PDF 图形化可视化 | PDF Mermaid / 结构化可视化图形化导出 | 用户点击 PDF -> 系统输出带图形的 PDF | 需要浏览器渲染、SVG/Canvas 转换或 PDF 图形绘制，复杂度明显高于当前切片 | 后续以 Playwright 或 PDF 解析验证 |
| 批注/锁定服务端同步 | Artifact 协作状态跨刷新恢复 | 用户添加批注/锁定 -> 刷新或恢复 run 后仍存在 | 涉及服务端 schema、snapshot 和前端恢复，比 DOCX 导出影响面更大 | 后续后端 + 前端测试 |

候选 gap：
| 候选 | 来源 | 目标态 | 当前能力 | 缺口 | 价值 | 风险/复杂度 | 可测试性 | 去向 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| DOCX 表格高保真导出 | Todo P1.7 | Word 产物中的 Markdown 表格成为真正 OOXML 表格，并提供 styles part | 目前 `.docx` 包有效，但表格只是 `模块 | 状态` 段落 | 客户打开交付物时更像正式咨询/测试报告 | 低到中，只改无依赖 DOCX builder | 高，解析 ZIP 和 XML | 本轮 |
| PDF 图形化可视化 | Todo P1.7 剩余 | PDF 中 Mermaid / 结构化可视化成为图形 | 目前是语义投影文本 | 专业感更强 | 高，需要渲染链路 | 中 | 下一轮候选 |
| 协作状态服务端同步 | Todo P1.7 剩余 | 批注/锁定可随 run snapshot 恢复 | 目前是前端工作区状态 | 协作连续性更好 | 中高，跨前后端 | 高 | 下一轮候选 |

排序结论：
1. 选择 DOCX 表格高保真导出，因为它直接提升用户下载交付物后的专业第一印象，范围集中，能在当前前端测试内闭环。
2. PDF 图形化暂不选，因为需要更复杂的渲染基础设施。
3. 协作状态服务端同步暂不选，因为会触及持久化模型和 run snapshot 合约。

切片准入判断：
- 用户可感知动作链：ArtifactPane 下载 Word -> 生成 `.docx` -> 打开文档看到真实表格和基础样式。
- 相邻缺口合并：把 Markdown 表格 OOXML 化和 styles.xml 包入口合并处理，避免只做半个富排版能力。
- Superpowers 成本合理性：这是 P1 Artifact 协作体验深化下的交付质量能力，值得独立 TDD 验证。
- 过薄风险检查：不是单 helper；完成后影响用户下载 Word 的完整交付链路。
- 能力增量句：完成后，用户现在可以导出包含真实 Word 表格结构的专业产出物。

切片厚度门禁：
- 入口：ArtifactPane 的 Word 下载按钮。
- 动作：用户下载当前阶段产出物。
- 处理：`buildDocxPackage` 将 Markdown 表格转为 OOXML `w:tbl`，并打包 styles part。
- 可见结果：`.docx` 包内有 `word/document.xml` 表格结构和 `word/styles.xml`。
- 状态承接：导出仍基于当前 `artifactContent`，不改变 artifact state。
- 失败反馈：导出路径保持同步生成；测试覆盖 XML 转义，避免恶意 HTML 被当成标签。
- 证据：Vitest 解析 DOCX ZIP entry，lint、build、diff check。
- 结论：通过。

## 用户故事

作为使用 Lisa / Alex 生成专业交付物的用户，当我下载 Word 文档时，我希望评分矩阵、风险矩阵、覆盖矩阵等 Markdown 表格在 Word 里就是可编辑的表格，而不是带管道符的文本，从而让我更容易把产出物交给客户或继续二次编辑。

## 验收条件

1. Given artifact 中包含 Markdown 表格，When 用户导出 Word，Then `word/document.xml` 包含 `w:tbl`、`w:tr`、`w:tc`，并包含表头和数据单元格文本。
2. Given artifact 中包含 `<script>` 等 HTML，When 用户导出 Word，Then 内容仍被 XML 转义，不作为真实标签进入文档。
3. Given 用户导出 Word，When 解析 DOCX 包，Then 包内存在 `word/styles.xml`，`[Content_Types].xml` 和 `_rels/.rels` 能引用必要 OOXML part。

## 文件范围

- 修改：`tools/new-agents/frontend/src/core/docxExport.ts`
- 修改：`tools/new-agents/frontend/src/core/__tests__/docxExport.test.ts`
- 修改：`docs/todos/new-agents-ux-professionalization.md`

## 非目标

- 不把 Mermaid 或结构化可视化嵌入为 DOCX 图片。
- 不新增外部 DOCX 库。
- 不改变 ArtifactPane 的下载入口、文件名或 MIME。
- 不改 Lisa/Alex/workflow runtime。
