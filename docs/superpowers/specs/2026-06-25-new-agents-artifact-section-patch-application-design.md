# New Agents 产出物章节 Patch 应用设计

## Current State Gap Analysis

### 事实源快照

- 已读取：`AGENTS.md`、`docs/strategy/goal-mode-playbook.md`、`docs/strategy/goal-mode-ci-verification.md`、`docs/index.md`、剩余 active todo、最近提交、`artifactSections.ts`、`store.ts`、`chatService.ts`、`agentCore.ts`、`llm.ts` 与相关前端测试。
- 当前工作区：仅 `dist/intent-test-proxy.zip`、`tools/intent-tester/frontend/static/intent-test-proxy.zip`、`tools/intent-tester/test-results/proxy/junit.xml` 为既有/全量测试生成的无关脏文件，本轮不触碰、不 stage。
- 本轮允许写入：`tools/new-agents/frontend/src/core/artifactSections.ts`、`tools/new-agents/frontend/src/core/types.ts`、相关 core/store 测试、`tools/new-agents/frontend/src/store.ts`、本 spec / plan，以及 active 增量渲染 todo 的进展记录。

### 能力包聚合

| 候选能力包 | 聚合的原始缺口 | 用户动作链 / 工程信任闭环 | 排序结论 | 验收证据 |
| --- | --- | --- | --- | --- |
| 前端章节 patch 应用与显式降级 | todo 中“前端增量应用”“patch 不安全时明确降级”；上一切片已有章节 anchor 与变更索引，但还不能应用局部 patch | 调用方拿到同 base 的 section patch -> store 尝试只替换目标章节 -> 成功后完整 artifact 事实源更新且变更索引记录目标章节 -> 失败时返回明确 fallbackReason，不伪造局部更新成功 | 本轮选择。它不触碰后端 SSE，先补齐前端局部应用契约和失败语义，是后续 typed SSE patch 的最小前置能力 | `artifactSections` 单测、store 测试、frontend lint / test |
| 后端 typed SSE `artifact_patch` / `changed_sections` | 后端 schema、runtime stream、前端 parser 与 store patch 应用需要同时变更 | 模型/后端发 patch，前端局部应用并校验最终完整内容 | 暂缓。没有前端安全应用契约前直接跨层扩展风险较高 | 后续跨层 plan |
| ReactMarkdown section memoization | 未变化章节不重新 mount，减少闪动和渲染成本 | 产出物更新后只重渲染变化章节 | 暂缓。需要先有安全 patch 应用和稳定章节边界；Mermaid / structured visual blockIndex 仍需单独处理 | 后续组件性能测试 |

### 切片厚度门禁

- 入口：前端调用方持有当前 artifact 的同 base section patch。
- 动作：store 尝试应用 patch。
- 处理：校验 base 内容、目标 section anchor、replacement section 内容和结构化安全边界；只支持 `replace` 操作。
- 可见结果：调用方能从返回值知道 patch 是否应用；应用成功时当前 artifact 内容只替换目标章节，`artifactChangeIndex` 只记录目标章节变化；失败时内容不变，并返回可诊断原因。
- 状态承接：完整 `artifactContent` 和 `stageArtifacts[currentStageId]` 仍是事实源；patch result 不持久化。
- 失败反馈：`base_mismatch`、`section_not_found`、`unsafe_section`、`invalid_patch` 显式返回，调用方可降级为完整 Markdown 替换。
- 证据：纯函数和 store 测试覆盖成功替换、base mismatch、锚点缺失、结构化块降级和 store 状态更新。
- 结论：通过。

## Brainstorming 自问自答

### Explore Project Context

上一切片新增 `extractArtifactSections(...)` 和 `buildArtifactSectionChangeIndex(...)`，但 section 对象还没有暴露 start/end line，无法安全拼接局部内容。`store.ts` 目前只有 `setArtifactContent(...)` 作为整篇替换入口。`chatService.ts` 仍接收完整 `artifact_update.markdown` 并调用 `setArtifactContent(...)`，本轮不改 SSE parser 和流式传输协议。

### Visual Companion Decision

本轮是前端状态和纯函数契约，不涉及视觉布局问题，不需要视觉 companion。

### Clarifying Questions

- 用户是谁：后续 SSE patch 接入方、store 调用方，以及需要可诊断局部更新失败的工程链路。
- 用户要完成什么：在前端安全地应用单章节 replace patch，而不是只能整篇替换。
- 成功状态是什么：同 base、可定位、安全的 section patch 只替换目标章节；失败时不修改内容并返回原因。
- 不做什么：不新增后端字段，不解析真实 SSE patch，不做 ReactMarkdown memoization，不支持 section rename / insert / delete。

### Approaches

1. 推荐：在 `artifactSections.ts` 增加 `applyArtifactSectionPatch(...)` 纯函数，并在 store 暴露 `applyArtifactSectionPatch(...)` action。优点是边界清楚、可测试、后续 SSE 只需调用同一契约；缺点是 patch 来源仍未接入后端。
2. 不选：直接在 `chatService.ts` 临时处理 patch。它会把协议解析、锁定保护、section 安全判断和 store 更新混在一起，不利于后续复用。
3. 不选：一次性扩展后端 typed SSE 并接前端应用。它更完整，但会跨 schema、runtime、parser、store、UI，当前更适合作为下一切片。

### Presented Design

扩展 `artifactSections.ts`：

- `ArtifactMarkdownSection` 增加 `startLine` 与 `endLine`，仍兼容现有 title / anchor / content 字段。
- 导出 `getArtifactSectionUnsafeReason(content)`，复用上一切片对 fenced block、Markdown table、顶层 list、`ai4se-visual` 的保守判定。
- 新增 `applyArtifactSectionPatch(currentContent, patch)`，只支持 `operation: 'replace'`：
  - 如果 `patch.baseContent` 存在且不等于 `currentContent`，返回 `applied=false` 和 `fallbackReason='base_mismatch'`。
  - 如果 replacement 缺少 Markdown heading 或目标 anchor 不存在，返回 `invalid_patch` / `section_not_found`。
  - 如果目标 section 或 replacement section 不安全，返回 `unsafe_section`。
  - 成功时按目标 section 的 line range 替换完整 section Markdown，并基于替换前后内容返回 `changes`。

扩展 `ChatState` / store：

- 新增 action `applyArtifactSectionPatch(patch)`。
- 成功时更新 `artifactContent`、`stageArtifacts[currentStageId]`、`artifactChangeIndex`，并清理当前 artifact 视觉诊断。
- 失败时不改变 state，只返回 fallback result。
- 不把 patch result 持久化，不改变 `partialize`。

## 验收条件

1. Given 当前 Markdown 有多个章节，When 应用同 base 的 `replace` patch 到其中一个章节，Then 只替换目标章节，其他章节保持不变，并返回目标章节 `modified` change。
2. Given patch 的 `baseContent` 与当前内容不同，When 应用 patch，Then 返回 `base_mismatch`，当前内容不变。
3. Given patch 的 `sectionAnchor` 不存在，When 应用 patch，Then 返回 `section_not_found`，当前内容不变。
4. Given 目标章节或 replacement 包含表格、列表、fenced block 或 `ai4se-visual`，When 应用 patch，Then 返回 `unsafe_section`，当前内容不变。
5. Given store action 成功应用 patch，Then store 的 `artifactContent`、当前 stage artifact 和 `artifactChangeIndex` 同步更新；Given patch 失败，Then store 内容不变且返回 fallback reason。

## 非目标

- 不新增后端 `artifact_patch` / `changed_sections` SSE 字段。
- 不接入 `chatService.ts` 的真实流式 patch 解析。
- 不支持 section rename、insert、delete、move。
- 不实现 ReactMarkdown section memoization。
- 不改变批注、章节锁、历史版本、手工编辑冲突和导出行为。
