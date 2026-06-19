# New Agents DOCX 可视化语义投影设计

## Current State Gap Analysis

事实源快照：
- 已读取：`AGENTS.md`、`docs/strategy/goal-mode-playbook.md`、`docs/todos/new-agents-ux-professionalization.md`、`tools/new-agents/frontend/src/core/docxExport.ts`、`tools/new-agents/frontend/src/core/__tests__/docxExport.test.ts`、`tools/new-agents/frontend/src/components/ArtifactPane.tsx`、`tools/new-agents/frontend/src/core/structuredVisuals.ts`。
- 当前 git 状态：主工作区仍有两个无关 zip 文件改动；本轮在 `.worktrees/codex-new-agents-docx-visual-projection` 隔离 worktree 中实现。

能力包聚合：

| 能力包 | 聚合的原始缺口 | 用户动作链 / 工程信任闭环 | 为什么不能再拆薄 | 验收证据 |
| --- | --- | --- | --- | --- |
| DOCX 可视化语义投影 | Artifact 协作剩余项中的 DOCX 高保真、可视化专业交付物；全流程专业产出物可视化增强 | 用户在 ArtifactPane 下载 Word -> 系统把 Mermaid / `ai4se-visual` 转为 Word 可读摘要和表格 -> 用户得到更专业的交付文档 | 只支持 Mermaid 或只支持结构化可视化都会留下同一导出动作中的明显割裂体验 | `docxExport.test.ts` 解包检查 `word/document.xml` 不再暴露 fenced marker / 原始 JSON，并包含图表摘要和真实 `w:tbl` |
| PDF 复杂 Mermaid/SVG 图片级嵌入 | Artifact 剩余项中的 PDF Mermaid/SVG 高保真 | 用户下载 PDF -> 系统嵌入高保真图形 | 涉及 runtime Mermaid 渲染、SVG/图片打包、分页布局，风险高于当前切片 | 需要浏览器/渲染层验证和 PDF 图像对象断言 |
| 更复杂三方 merge 语义 | Artifact 冲突合并剩余项 | 用户遇到冲突 -> 系统自动处理改写/移动/删除 | 与可视化专业输出目标弱相关，且冲突算法风险较高 | 多组冲突算法测试 |

排序结论：
1. 选择 DOCX 可视化语义投影。它直接提升用户下载交付物的专业感，复用现有 `buildDocxPackage` 和 `parseStructuredVisual`，风险可控。
2. PDF 复杂 SVG 嵌入暂缓。当前已有 PDF Mermaid 矢量投影和结构化表格绘制，进一步高保真需要更大渲染方案。
3. 更复杂 merge 语义暂缓。Artifact 协作主链路已有人工编辑、冲突提示、块级合并和活动轨迹。

切片厚度门禁：
- 入口：ArtifactPane 的 Word 下载动作。
- 动作：用户下载包含 Mermaid / `ai4se-visual` 的产出物。
- 处理：`buildDocxPackage` 在 Markdown 转 Word 时识别 Mermaid 和结构化可视化 fenced block。
- 可见结果：Word 文档中出现 `Mermaid 图表：<type>` 摘要、节点/边文本、结构化可视化标题和真实 Word 表格。
- 状态承接：不改变 artifact 状态，只改变导出投影；仍复用同一个 DOCX 包生成函数。
- 失败反馈：非法 `ai4se-visual` 在 DOCX 中输出结构化可视化错误摘要，不阻断下载。
- 证据：`docxExport.test.ts`、ArtifactPane 下载回归测试、lint、build、`git diff --check`。
- 结论：通过。完成后，用户现在可以下载更像专业交付物的 DOCX，而不是在 Word 中看到原始 Mermaid / JSON 块。

## 用户故事

作为 Lisa / Alex 的工作流用户，当我把右侧产出物下载为 Word 时，我希望文档中的图表和结构化可视化被转换成可读摘要和可编辑表格，从而能直接交给业务方评审或继续编辑。

## 设计边界

- 只修改共享 DOCX 导出逻辑，不新增 Lisa/Alex 或 workflow-specific 分支。
- Mermaid 本轮做语义文本投影，不做截图、SVG、图片嵌入或复杂布局。
- `ai4se-visual` 使用现有 `parseStructuredVisual`，合法内容转换为真实 `w:tbl`；非法内容输出错误摘要。
- 不改变 PDF 导出路径、ArtifactPane UI 或 artifact 持久化。

## 验收条件

- DOCX 中的 Mermaid fenced block 不再以普通代码块形式输出，`word/document.xml` 包含 `Mermaid 图表：flowchart` 和关键节点/边文本。
- DOCX 中的合法 `ai4se-visual` 不再暴露原始 JSON 或 fenced marker，`word/document.xml` 包含结构化可视化标题、列名、行值和真实 `w:tbl`。
- DOCX 中的非法 `ai4se-visual` 输出 `结构化可视化错误：...`，下载仍成功。
- 既有 Markdown 标题、列表、表格、代码块、转义行为保持不变。

## 验证计划

- RED：`npm run test -- --run src/core/__tests__/docxExport.test.ts`
- GREEN：同命令通过。
- 回归：`npm run test -- --run src/core/__tests__/docxExport.test.ts src/components/__tests__/ArtifactPane.test.tsx`
- 质量门禁：`npm run lint`、`npm run build`、`git diff --check`。
