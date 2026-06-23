# Artifact 审阅诊断中心设计

## 背景

当前 New Agents 已通过共享 Agent Runtime、typed SSE、workflow manifest、artifact contract、后端 deterministic renderer 和共享 UI 生成多 workflow artifact。DeepSeek V4 全 workflow readiness 已证明所有在线 stage 都有结构化 `artifact_data` 与 renderer，但用户在右侧 Artifact 预览区仍只能看到最终文档，不能直接判断当前阶段产物是否满足 manifest 声明的必填标题、Mermaid 图、`ai4se-visual` 和阶段门禁要求，也不能快速聚合当前 artifact 中的待补信息、阻断项和下一步。

本切片把已有 contract 和 artifact 自身暴露的缺失信息从“散落在正文中的事实”转成“用户可见审阅诊断事实”，不新增 agent-specific runtime、API path、store 或 renderer。

## 用户故事

作为 New Agents 用户，我在当前阶段查看 Artifact 时，可以直接看到该产物是否满足当前 workflow/stage 的质量契约，并知道缺失的是标题、可视化、阶段门禁、结构化可视化渲染问题，还是 artifact 正文已经标出的待澄清/开放/未确认信息，从而决定补充输入、重试生成或手工修订。

## 范围

纳入本轮：

- 从前端共享 `workflow_manifest.json` 读取当前 stage 的 `artifactContract.requiredHeadings`、`visualContract.requiredMermaidDiagrams` 和 `visualContract.requiredStructuredVisuals`。
- 新增前端纯函数，基于当前 workflow/stage、artifact Markdown 和已有 visual runtime diagnostics 生成诊断项。
- 在 `ArtifactPane` 的审阅能力中展示诊断摘要、分类明细和缺失信息清单。
- 诊断项覆盖：
  - 必填标题/关键词存在性。
  - 必需 Mermaid 图类型存在性。
  - 必需 `ai4se-visual` 类型存在性。
  - 当前阶段已有 Mermaid/structured visual runtime diagnostic。
  - 阶段门禁信息是否存在。
  - Artifact 正文中的待澄清问题、开放问题、未验证假设、未确认项、阻断项和待处理项。
- 对空 artifact 显式显示“暂无产物可诊断”。
- 补充前端测试，证明诊断计算和 UI 展示来自真实 manifest/stage。
- 更新活跃 todo 记录本轮消化结果。

不纳入本轮：

- 自动修复 artifact。
- LLM judge 质量评分。
- 跨 run 质量趋势。
- 后端新增 diagnostic endpoint。
- Lisa 测试资产 issue 修复/确认/追踪闭环。

## 设计

新增 `frontend/src/core/artifactDiagnostics.ts`，作为共享前端诊断核心。它接收当前 `WorkflowType`、`stageId`、artifact Markdown 和 visual runtime diagnostics，返回 summary、contract 诊断项和缺失信息项。该模块只依赖 workflow registry、类型定义和字符串解析，不依赖 React 或 Zustand，便于 TDD。

`workflowRegistry.ts` 和 `types.ts` 补充 manifest contract 类型，让前端以显式类型读取 `artifactContract` 和 `visualContract`。`WORKFLOWS` 继续由 manifest 构造，不引入额外配置源。

`ArtifactPane.tsx` 在当前阶段和 artifact 内容变化时计算诊断结果，并在现有“产物审阅”面板顶部展示“审阅诊断”。展示保持紧凑：摘要显示通过、失败、警告和待处理信息数量；明细按类别列出状态和用户下一步；缺失信息区提取正文中最靠近缺失/阻断语义的条目。已有 visual runtime diagnostics 继续由现有 store 维护，新的面板只聚合展示，不改变渲染诊断生命周期。

缺失信息提取采用确定性文本规则，不尝试理解全部语义：

- 优先扫描标题包含 `待澄清`、`开放问题`、`未验证`、`未确认`、`缺失信息`、`阶段门禁`、`阻断`、`待处理` 的章节。
- 在这些章节中提取 bullet、表格行或包含 `阻断`、`待确认`、`需补充`、`未验证` 的短句。
- 每条输出包含 `title`、`blocking`、`detail` 和 `nextAction`。如果出现 `阻断`、`P0`、`必须`、`无法进入下一阶段`，标记为 blocking。
- 为避免噪声，最多展示 6 条，正文过长时截断。

## 错误与空状态

- 没有 current stage 时不生成诊断面板。
- artifact 为空时展示空状态，不把所有必填项都标红，避免生成前误报。
- manifest 缺少 visual contract 时只跳过该类检查；artifact contract 仍是必填事实。
- visual runtime diagnostic 只计入当前 stage。

## 验收条件

- 当前阶段 artifact 缺少 manifest required heading 时，诊断面板显示失败项和缺失标题。
- 当前阶段 artifact 包含 required heading、required Mermaid 类型、required structured visual 类型和阶段门禁时，诊断显示通过项。
- 当前阶段 structured visual 或 Mermaid 渲染失败时，诊断面板聚合已有 runtime diagnostic。
- Artifact 正文包含待澄清/开放/未确认/阻断信息时，诊断面板显示缺失信息清单、阻断性和下一步建议。
- 历史预览不写入 runtime diagnostics；质量诊断只针对当前 artifact。
- 不新增 Lisa/Alex/DeepSeek 专属 runtime、API、store 或 renderer。

## 验证计划

- `cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/artifactReview.test.ts`
- `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx`
- `cd tools/new-agents/frontend && npm run test -- --run src/core/config/__tests__/workflows.test.ts`
- `git diff --check`
