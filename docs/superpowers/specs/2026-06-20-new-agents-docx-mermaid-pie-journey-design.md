# New Agents DOCX Mermaid Pie/Journey Design

## Current State Gap Analysis

事实源快照：
- 已读取：`AGENTS.md`、`docs/strategy/goal-mode-playbook.md`、`docs/index.md`、`docs/todos/new-agents-ux-professionalization.md`。
- 已读取代码：`tools/new-agents/frontend/src/core/docxExport.ts`、`tools/new-agents/frontend/src/core/__tests__/docxExport.test.ts`、`tools/new-agents/frontend/src/components/ArtifactPane.tsx`、`tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`。
- 当前 git 状态：主工作区仍有两个无关 zip 修改，当前切片在独立 worktree `codex/new-agents-docx-mermaid-pie-journey` 中执行。

能力包聚合：

| 能力包 | 聚合的原始缺口 | 用户动作链 / 工程信任闭环 | 为什么不能再拆薄 | 验收证据 |
| --- | --- | --- | --- | --- |
| DOCX `pie` / `journey` SVG 嵌入 | todo P1 #7 剩余 `DOCX pie/journey SVG 嵌入`、P0 #3 专业产出物导出质量 | 右侧 artifact 包含 Mermaid pie/journey -> 用户下载 Word/DOCX -> Word 中看到真实图形和可搜索语义文本 | 单独只做 pie 或只做 journey 会留下同一导出路径的相邻缺口；二者已有 PDF 侧保守解析经验，合并实现更合理 | `docxExport.test.ts` 新增 pie/journey SVG media 断言，lint/build/diff check |
| Artifact 更复杂三方 merge | todo #7 剩余移动语义自动合并、复杂冲突解析 | 多标签冲突 -> 用户对比 -> 系统自动合并更复杂修改 -> 审计轨迹 | 涉及 `ArtifactPane.tsx` 高冲突区域和复杂语义判断，应单独做更厚协作切片 | ArtifactPane/store 测试 |
| 左侧自然对话可读性尾项 | todo #5 左侧自然表达与重点可扫描 | 模型回复 -> 左侧自然聊天但更可扫读 | 当前契约已完成基础约束，剩余更偏 prompt 质量/evidence；不如导出缺口可验证 | contract/prompt/judge 证据 |
| 模型/供应商治理尾项 | todo #6 运行统计与供应商诊断后续 | 失败 -> 统计定位 -> 设置/检测 -> 重试 | 主要链路已闭环，剩余尾项价值低于导出可视化缺口 | backend/frontend observability 测试 |

排序结论：
1. 选择 DOCX `pie` / `journey` SVG 嵌入，因为它直接补齐刚完成的 DOCX Mermaid SVG 嵌入能力，用户可见、边界清楚、测试稳定，也复用共享 DOCX 导出路径。
2. Artifact 更复杂三方 merge 暂不选，因为它触及 `ArtifactPane.tsx` 大型协作逻辑，应独立规划更厚切片。
3. 左侧自然对话与模型治理尾项暂不选，因为已有基础闭环，当前更适合作为后续质量证据或观测增强。

切片厚度门禁：
- 入口：用户在右侧 artifact 中获得包含 Mermaid `pie` 或 `journey` 的专业产出物。
- 动作：用户点击 Word/DOCX 下载。
- 处理：DOCX 导出器解析 Mermaid `pie` / `journey`，生成本地保守 SVG media part，并写入 OOXML relationship。
- 可见结果：Word 文档中出现图形，同时保留 `Mermaid 图表：pie/journey` 和清洗后的标题、分类、阶段、任务等文本。
- 状态承接：导出仍是无副作用下载，不改变 artifact、history 或 run snapshot；不支持/无法解析时继续文本降级。
- 失败反馈：非法或复杂 Mermaid 不阻断下载，保留现有语义文本投影。
- 证据：`docxExport.test.ts` 新增 RED/GREEN 测试，覆盖 SVG media、relationship、文本清洗和 XML 转义。
- 结论：通过。该切片不是单 helper，而是完整导出能力增量。

本轮 milestone：
作为需要交付 Word 文档的用户，当产出物包含优先级分布 `pie` 或用户旅程 `journey` 图时，我下载 DOCX 后能看到实际图形，并且仍能复制/搜索标题、分类、阶段和任务文本，从而提升交付物专业感。

## 用户故事

作为 Lisa / Alex 工作流用户，我希望右侧产出物中的 Mermaid 饼图和用户旅程图在导出的 Word 文档中呈现为图形，而不是只显示源码或纯文本摘要，这样客户能更快理解优先级分布、旅程阶段和关键任务。

## 验收条件

1. Given 文档中包含 Mermaid `pie`
   When 调用 `buildDocxPackage`
   Then DOCX 包包含 `word/media/mermaid-1.svg`、`word/_rels/document.xml.rels`、`w:drawing`，SVG 中包含标题、分类和值，并转义潜在 HTML。

2. Given 文档中包含 Mermaid `journey`
   When 调用 `buildDocxPackage`
   Then DOCX 包包含 SVG media，SVG 中包含标题、阶段、任务、评分和角色，并转义潜在 HTML。

3. Given `pie` / `journey` 被图形化
   Then `word/document.xml` 仍保留 `Mermaid 图表：pie` 或 `Mermaid 图表：journey` 与可搜索语义文本，并不暴露 fenced source、`pie title ...`、`title ...`、`section ...` 等源码控制行。

4. Given 不支持或无法解析的 Mermaid 类型
   Then 保持现有文本语义投影和降级路径，不阻断 DOCX 下载。

## 边界

- 不改 ArtifactPane/PDF 导出；只从 PDF 侧已有解析规则借鉴语义。
- 不做浏览器截图或 Mermaid runtime 渲染。
- 不支持任意 SVG/HTML 输入，只用本地保守投影生成 SVG。
- 不新增 workflow-specific 或 agent-specific 导出分支。
- 不处理完整三方 merge、移动语义自动合并或新的 prompt/contract 可视化要求。

## 验证计划

- `cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/docxExport.test.ts -t "embeds supported Mermaid"`
- `cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/docxExport.test.ts`
- `cd tools/new-agents/frontend && npm run lint`
- `cd tools/new-agents/frontend && npm run build`
- `git diff --check`
