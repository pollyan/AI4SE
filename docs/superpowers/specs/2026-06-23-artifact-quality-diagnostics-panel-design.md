# Artifact 审阅诊断中心设计

## 背景

当前 New Agents 已通过共享 Agent Runtime、typed SSE、workflow manifest、artifact contract、后端 deterministic renderer 和共享 UI 生成多 workflow artifact。DeepSeek V4 全 workflow readiness 已证明所有在线 stage 都有结构化 `artifact_data` 与 renderer，但用户在右侧 Artifact 预览区仍只能看到最终文档，不能直接判断当前阶段产物是否满足 manifest 声明的必填标题、Mermaid 图、`ai4se-visual` 和阶段门禁要求，也不能快速聚合当前 artifact 中的待补信息、阻断项和下一步。

本切片把已有 contract 和 artifact 自身暴露的缺失信息从“散落在正文中的事实”转成“用户可见审阅诊断事实”，不新增 agent-specific runtime、API path、store 或 renderer。

## Superpowers 头脑风暴记录

### Explore Project Context

问: 当前仓库事实说明这个需求应该落在哪里？

答: New Agents 已经有共享 `/api/agent/runs/stream`、typed SSE、workflow manifest、artifact contract、后端 deterministic renderer、前端 `ArtifactPane`、运行时 visual diagnostics 和持久化 artifact。todo 中 E02 指向阶段缺失信息清单，E03 指向 Artifact 质量诊断面板；它们属于同一个用户动作链：用户在右侧审阅 artifact 时判断当前产物是否可信、缺什么、下一步该做什么。因此本轮应把 E02 的 artifact 审阅侧和 E03 合并为一个厚切片，而不是拆成标题检查、Mermaid 检查、缺失信息提取等小任务。

问: 当前需求是否过大，需要拆成多个 spec？

答: 不需要。它只影响前端 artifact 审阅体验和共享诊断纯函数，不新增后端 API、不改 Agent Runtime、不改持久化 schema、不引入 LLM judge。自动修复、跨 run 质量趋势、Lisa 测试资产 issue 闭环属于其他用户动作链，应排除。

### Visual Companion Decision

问: 是否需要视觉辅助或浏览器 mockup？

答: 不需要。这里不是重新设计布局或视觉风格，而是在既有 `ArtifactPane` 审阅面板中增加紧凑诊断区。验收重点是诊断事实是否来自 manifest 和当前 artifact，视觉风险可通过组件测试与现有样式约束控制，不需要单独浏览器 companion。

### Clarifying Questions

问: 这个功能服务的用户是谁？

答: 正在使用 Lisa 或 Alex workflow 审阅右侧 artifact 的 New Agents 用户，包括 PM、测试专家和研发评审者。

问: 用户要完成什么？

答: 用户要在不阅读整篇 artifact 的情况下先判断当前阶段产物是否满足 workflow/stage 契约，并快速看到缺失标题、可视化、阶段门禁、渲染异常、待澄清和阻断信息。

问: 成功状态是什么？

答: 用户打开产物审阅区后，能看到通过/失败/警告/待处理数量，展开可定位到具体缺失项，并获得下一步建议：补充输入、重试生成或手工修订。空 artifact 不应误报一堆失败。

问: 输入来源有哪些？

答: 当前 workflow/stage、当前 artifact Markdown、`workflow_manifest.json` 中的 artifact/visual contract，以及现有 runtime visual diagnostics。

问: 关键约束是什么？

答: 必须复用共享 workflow manifest、ArtifactPane 和 visual diagnostic 机制；不得新增 Lisa/Alex/DeepSeek 专属 runtime、API path、store 或 renderer；不得用 mock 或假成功掩盖 contract 缺口。

问: 失败路径是什么？

答: manifest 缺少某类 visual contract 时跳过该类检查但保留 artifact heading 检查；artifact 为空时显示空状态；runtime visual diagnostics 只聚合当前 stage；正文提取不到缺失信息时不伪造开放问题。

问: 下游承接是什么？

答: 本轮只提供确定性诊断事实，为后续 Lisa 测试资产质量闭环、handoff 上下文强化和质量评分提供可见基础；不直接触发自动修复或跨 run 分析。

### Approaches

方案 A: 前端确定性诊断核心，从 manifest + Markdown + runtime visual diagnostics 计算结果，并由 `ArtifactPane` 展示。

取舍: 实现面小、无需 API 迁移、能直接复用前端已有 manifest registry 和 visual diagnostics；风险是文本规则不能覆盖全部语义，但足以覆盖 contract 和正文显式缺失信息。本轮推荐采用。

方案 B: 后端新增只读 diagnostic endpoint，统一由后端解析 artifact 并返回诊断。

取舍: 后端更接近 artifact contract 源头，但会新增 API surface、认证/持久化/路由测试和前后端协议，同一轮风险更高；当前缺口主要是审阅展示，不需要后端新路径。本轮不选。

方案 C: 引入 LLM judge 或质量评分模型生成诊断。

取舍: 可覆盖语义质量，但需要模型凭证、成本、可重复性和 judge evidence 管理；不适合作为当前 deterministic trust layer 的首个闭环。本轮不选。

### Presented Design

Architecture: 新增 `artifactDiagnostics.ts` 作为前端共享纯函数模块。它从 typed workflow registry 读取当前 stage 的 `artifactContract` 和 `visualContract`，解析当前 Markdown 和 runtime visual diagnostics，输出结构化诊断结果。`ArtifactPane` 只负责展示，不承担业务判断。

Components: `types.ts` 和 `workflowRegistry.ts` 补齐 manifest contract 类型；`artifactDiagnostics.ts` 提供诊断 summary、items 和 openQuestions；`ArtifactPane.tsx` 在既有产物审阅面板中渲染“审阅诊断”区；对应 Vitest 覆盖核心函数和 UI 行为。

Data Flow: `workflowId + stageId + artifactContent + visualDiagnostics` 进入 `buildArtifactQualityDiagnostics()`，函数读取 manifest contract，扫描 required headings、Mermaid 类型、`ai4se-visual` 类型、阶段门禁和缺失信息章节，返回 pass/fail/warn/neutral 项。UI 使用结果显示数量、明细、缺失信息和下一步。

Error Handling: 空 artifact 返回空状态；未知 workflow/stage 返回空诊断；manifest 未声明 visual contract 时不报错；非法 structured visual 或 Mermaid 渲染失败沿用现有 runtime diagnostics 并以警告聚合。

Testing: 先写核心函数 RED 测试覆盖缺 heading/visual、完整通过、runtime visual warning、阻断缺失信息提取；再写 `ArtifactPane` RED 测试覆盖审阅诊断 UI、runtime visual failure 和缺失信息清单；最后运行 workflow config 同步测试、test hygiene、lint 和 `git diff --check`。

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
