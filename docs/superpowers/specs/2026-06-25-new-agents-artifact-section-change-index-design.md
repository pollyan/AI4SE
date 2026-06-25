# New Agents 产出物章节变更索引设计

## Current State Gap Analysis

### 事实源快照

- 已读取：`AGENTS.md`、`docs/strategy/goal-mode-playbook.md`、`docs/index.md`、`docs/ARCHITECTURE.md`、`docs/TESTING.md`、`docs/DESIGN_PRINCIPLES.md`、剩余活跃 todo、`store.ts`、`core/types.ts`、`agentCore.ts`、`llm.ts`、`ArtifactPane.tsx`、`markdownCodeRenderer.tsx` 和相关前端测试。
- 当前工作区：`dist/intent-test-proxy.zip`、`tools/intent-tester/frontend/static/intent-test-proxy.zip`、`tools/intent-tester/test-results/proxy/junit.xml` 为既有脏文件，本轮不触碰、不 stage。
- 本轮允许写入：`tools/new-agents/frontend/src/core/artifactSections.ts`、相关 core/store/component 测试、`store.ts`、`core/types.ts`、`ArtifactPane.tsx`、本 spec / plan，以及 active 增量渲染 todo 的进展记录。

### 能力包聚合

| 候选能力包 | 聚合的原始缺口 | 用户动作链 / 工程信任闭环 | 排序结论 | 验收证据 |
| --- | --- | --- | --- | --- |
| 前端章节变更索引 | `artifact-incremental-rendering.md` 中“前端能知道本轮变化涉及哪些章节/块”；ArtifactPane 目前只有整篇 `artifactContent`，当前 diff 只能逐行显示 | 用户生成或更新 Artifact -> 前端 store 记录本轮变化章节 -> ArtifactPane 显示变化章节摘要 -> 后续 patch / memoized rendering 有稳定锚点基础 | 本轮选择。它不改 runtime contract，却把“局部变更感知”的状态基础落到共享 store 和 UI | artifactSections 单测、store 测试、ArtifactPane 测试、frontend lint |
| 完整 artifact patch / changed_sections SSE 协议 | 后端 typed SSE、前端 parser、store patch 应用、最终完整内容校验 | 服务端发 patch，前端局部应用并校验 | 暂缓。它跨后端 schema、runtime、前端 parser 和存储，风险显著更高；需要基于本轮章节索引继续设计 | 后续跨层 plan |
| 块级 memoized rendering | ReactMarkdown 按章节拆分、未变化章节不 re-mount | 长文档更新时减少闪动和重排 | 暂缓。ArtifactPane 的 Mermaid / structured visual blockIndex 依赖共享 code renderer 计数，直接拆 ReactMarkdown 需要先有稳定章节索引和视觉诊断锚点策略 | 后续组件性能测试 |

### 切片厚度门禁

- 入口：任意当前阶段 Artifact 内容更新，包括模型生成、手工编辑保存和局部 protected artifact 写入。
- 动作：前端状态层比较上一份当前内容与下一份当前内容。
- 处理：按 Markdown 标题章节生成稳定 anchor，忽略 fenced code 内部伪标题，识别 added / removed / modified 章节，并标记结构化块变更的保守原因。
- 可见结果：右侧 ArtifactPane 在本轮 diff 视图中显示“变更章节”摘要，用户能从章节粒度理解变化影响范围。
- 状态承接：store 保留完整 `artifactContent` 作为事实源；章节索引是派生状态，不持久化，不进入导出、prompt 或后端 persistence。
- 失败反馈：没有标题或无法形成章节时，索引为空，不伪造局部变更成功。
- 证据：纯函数单测覆盖重复标题、fenced heading、结构化块；store 测试证明更新/切换/清空行为；组件测试证明 UI 摘要可见。
- 结论：通过。

## Superpowers 自问自答

### Explore Project Context

`ArtifactPane.tsx` 目前内部有 `extractMarkdownSections(...)`，用于批注和章节锁，但它只服务当前组件，且没有输出“哪些章节变化”。`store.ts` 的 `setArtifactContent(...)` 是前端当前阶段 artifact 内容写入的集中入口；`chatService.ts` 在模型 delta / final artifact 到达时会调用它。`llm.ts` 和后端 SSE schema 仍只传完整或阶段性 Markdown，本轮不改协议。

`markdownCodeRenderer.tsx` 的 Mermaid / structured visual blockIndex 由单个 components object 内的计数器维护。直接把 ArtifactPane 渲染拆成多个 memoized ReactMarkdown section 可能影响诊断锚点和 retry blockIndex，因此本轮先建立章节变更索引，不触碰渲染拆分。

### Visual Companion Decision

本轮 UI 变化是已有“本轮变更”区域中的一行章节摘要，不需要额外视觉 mockup。

### Clarifying Questions

- 用户是谁：审阅长文档 Artifact 更新范围的使用者，以及后续实现 patch / 局部渲染的工程调用方。
- 用户要完成什么：知道本轮变化影响了哪些章节，而不只看到整篇行级 diff。
- 成功状态是什么：store 能记录本轮变化章节；ArtifactPane 能显示章节摘要；完整 artifact 事实源不变。
- 不做什么：不新增 SSE patch 协议，不改变模型 prompt 要求，不实现 memoized section rendering。

### Approaches

1. 推荐：新增 `core/artifactSections.ts`，提供纯函数 `extractArtifactSections(...)` 和 `buildArtifactSectionChangeIndex(...)`；store 在 `setArtifactContent(...)` 中维护派生 `artifactChangeIndex`；ArtifactPane 只显示摘要。优点是边界清晰、可测试、后续 patch 可以复用；缺点是还不减少 ReactMarkdown 渲染成本。
2. 不选：直接在 ArtifactPane 内部临时计算章节摘要。它快，但不会形成 store 层局部变更感知，也不利于后续 patch / memoized rendering。
3. 不选：直接拆分 ReactMarkdown 为多个 memoized section。它更接近性能目标，但会触及 Mermaid、structured visual、批注高亮和视觉诊断 blockIndex，当前缺少稳定索引基础。

### Presented Design

新增 `core/artifactSections.ts`：

- `extractArtifactSections(markdown)`：按 `#` 到 `######` 标题提取章节，忽略 fenced code block 内标题；重复标题使用 occurrence 生成稳定 anchor，格式沿用 `h<level>:<title>:<occurrence>`。
- `buildArtifactSectionChangeIndex(previousContent, currentContent)`：比较前后章节 anchor 和 content，输出 `added`、`removed`、`modified`。
- 每个 change 带 `safeForPatch` 和 `unsafeReason`。当章节内容包含 fenced block、Markdown 表格、顶层列表或 `ai4se-visual` 时标记为不适合自动 patch，仅可用于摘要和保守源码 diff。

扩展 `ChatState`：

- 新增非持久化 `artifactChangeIndex: ArtifactSectionChange[]`。
- `setArtifactContent(next)` 用旧 `state.artifactContent` 与 `next` 计算索引。
- 切换 workflow、切换 stage、handoff、restore snapshot、clear history 等“加载/重置”路径把索引清空，避免把旧阶段变化误认为本轮变化。

扩展 `ArtifactPane`：

- 读取 `artifactChangeIndex`。
- 在“本轮变更”diff 视图头部显示 `变更章节：A、B`；若没有章节索引则不显示摘要。
- 不改变当前行级 diff、不改变下载/导出、不改变历史弹窗。

## 验收条件

1. Given 前后 Markdown 只有一个章节正文变化，When 调用 `buildArtifactSectionChangeIndex(...)`，Then 只返回该章节 `modified`，不把整篇文档标为变化。
2. Given Markdown fenced code block 内包含 `## 伪标题`，When 提取章节，Then 不把 fenced block 内标题当作章节。
3. Given 重复标题出现两次，When 提取章节，Then anchor 带 occurrence，能区分两个同名章节。
4. Given 变化章节包含表格、列表、代码块或 `ai4se-visual`，When 建立索引，Then `safeForPatch=false` 并给出保守原因。
5. Given store 调用 `setArtifactContent(...)` 更新当前 Artifact，When 内容变化涉及一个章节，Then `artifactChangeIndex` 记录该章节；When 切换 stage / clear history，Then 索引清空。
6. Given ArtifactPane 当前 diff 可见且 store 有章节索引，When 渲染，Then “本轮变更”区域显示变更章节摘要。

## 非目标

- 不新增后端 `artifact_patch` / `changed_sections` SSE 字段。
- 不把章节索引持久化到 localStorage 或后端。
- 不用章节索引修改 `artifactContent`。
- 不实现 ReactMarkdown section memoization。
- 不改变批注、章节锁、历史版本、手工编辑冲突和导出行为。
