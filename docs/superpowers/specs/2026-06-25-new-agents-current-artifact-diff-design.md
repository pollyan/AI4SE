# New Agents 当前产出物本轮 Diff 标识设计

## Current State Gap Analysis

### 事实源快照

- 已读取：`AGENTS.md`、`docs/strategy/goal-mode-playbook.md`、`docs/index.md`、`docs/ARCHITECTURE.md`、`docs/TESTING.md`、`docs/DESIGN_PRINCIPLES.md`、剩余活跃 todo、`ArtifactPane.tsx`、`artifactDiff.ts`、`chatService.ts`、`agentCore.ts` 和现有 ArtifactPane / diff / 下载测试。
- 当前工作区：`dist/intent-test-proxy.zip`、`tools/intent-tester/frontend/static/intent-test-proxy.zip`、`tools/intent-tester/test-results/proxy/junit.xml` 为既有脏文件，本轮不触碰、不 stage。
- 本轮允许写入：`tools/new-agents/frontend/src/components/ArtifactPane.tsx`、`tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`、相关 diff 单测（如需要）、本 spec / plan，以及 `docs/todos/2026-06-25-new-agents-artifact-change-diff-highlighting.md` 的归档记录。

### 能力包聚合

| 候选能力包 | 聚合的原始缺口 | 用户动作链 / 工程信任闭环 | 排序结论 | 验收证据 |
| --- | --- | --- | --- | --- |
| 当前产出物本轮 diff 标识 | `artifact-change-diff-highlighting.md`；右侧正式预览无法直接看到本轮新增/删除；已有 `buildLineDiff(...)` 只在历史/冲突视图中使用 | 用户生成或手工更新右侧 Artifact -> 在当前产物阅读区看到绿色新增、红色删除线删除 -> 可隐藏回干净预览 -> 下载/导出仍用干净 Markdown | 本轮选择。它完整覆盖用户审阅变化的主路径，改动局限于 ArtifactPane UI 与测试，不新增 Agent Runtime / SSE / store 分支 | ArtifactPane 组件测试、download 回归、frontend lint |
| 完整增量 patch / 局部 memoized rendering | `artifact-incremental-rendering.md` 剩余能力；patch schema、stable section anchor、只更新变化块、最终校验 | 用户长文档生成时未变化章节不闪动；系统可诊断 patch 降级 | 暂缓。它跨 SSE schema、store、ArtifactPane 渲染性能和协作状态，明显大于本轮 diff 标识，且前面仅完成了 CLARIFY partial renderer 子能力 | 后续需要跨层 plan、runtime/store/UI 测试 |

### 切片厚度门禁

- 入口：用户在 New Agents 工作台完成一次当前阶段 Artifact 更新，或手工编辑保存当前产物。
- 动作：在右侧 ArtifactPane 正式阅读区域审阅本轮变化。
- 处理：以前一个当前阶段版本作为基线、当前内容作为结果构造行级 diff；新增行绿色，删除行红色且删除线；可切回干净预览。
- 可见结果：用户不用打开历史版本弹窗，也能看到本轮改变了什么。
- 状态承接：`artifactContent`、`stageArtifacts`、历史版本、下载、DOCX/PDF 导出、下一轮 prompt 仍使用干净最终 Markdown。
- 失败反馈：没有可用基线或内容无变化时不显示 diff toggle，不制造空状态假成功。
- 证据：组件测试证明默认本轮 diff、关闭 diff、下载不污染；lint 证明前端类型与规则通过。
- 结论：通过。

## Superpowers 自问自答

### Explore Project Context

`ArtifactPane.tsx` 已导入 `buildLineDiff(...)`，并在历史版本弹窗和手工保存冲突视图中展示红绿行级差异。`chatService.ts` 在生成成功后通过 `planArtifactVersionUpdate(...)` 将最终 artifact 追加到 `artifactHistory`；手工编辑保存也会保存前后版本。因此当前阶段倒数第二个版本可作为“本轮前基线”，当前内容或最新版本可作为“本轮后结果”。

正式预览当前只渲染 `artifactContent` 经 `preprocessMarkdown(...)` 后的 ReactMarkdown。下载 Markdown、DOCX、PDF 均直接使用 `artifactContent`。因此本轮 diff 必须只存在于 UI 层，不能写回 store。

### Visual Companion Decision

这是现有 UI 中的小型审阅状态，不需要额外浏览器 mockup。实现后用组件测试验证 DOM、样式类和下载数据边界。

### Clarifying Questions

- 用户是谁：审阅 New Agents 右侧 Artifact 变化的使用者。
- 用户要完成什么：快速知道本轮生成或更新新增了哪些内容、删除了哪些内容。
- 成功状态是什么：当前产物区域可显示本轮 diff，新增绿色、删除红色删除线，用户可隐藏。
- 不做什么：不实现字符级 diff，不把 diff 标记写入 Markdown，不替代历史版本对比，不实现完整 patch 协议。

### Approaches

1. 推荐：在 ArtifactPane 当前预览上方/替代态增加“本轮变更”视图，复用 `buildLineDiff(...)`，基线来自当前阶段历史版本。优点是改动集中、用户可见、不会污染内容事实源；缺点是第一版是行级 diff，改写整行时会显示删除旧行和新增新行。
2. 不选：把 diff HTML 注入 Markdown 再交给 ReactMarkdown 渲染。它容易污染复制/导出路径，也会破坏 Mermaid、代码块和表格结构。
3. 不选：新增后端 patch / changed_sections 协议。本轮用户反馈聚焦“能看到变化”，完整 patch 协议是增量渲染 todo 的后续大型能力包。

### Presented Design

ArtifactPane 增加当前阶段变更基线计算：

- 若 `latestStageArtifactVersion.content === artifactContent` 且当前阶段至少有两个版本，则基线为倒数第二个版本，结果为当前内容。
- 若 `latestStageArtifactVersion.content !== artifactContent`，则基线为最新历史版本，结果为当前内容，用于生成中或未保存的当前变化。
- 若无基线或内容相同，不显示本轮 diff 控件。

ArtifactPane 增加 `showCurrentChangeDiff` 状态。出现新的 diff key 时自动打开；用户点击“隐藏本轮变更”后回到干净预览。同一变更不会因为组件重渲染反复强制打开。

Diff 展示使用只读 monospaced 行列表，而不是重新渲染 Markdown。新增行使用绿色背景/文字，删除行使用红色背景/文字和删除线。这样对 Markdown 表格、Mermaid、`ai4se-visual`、代码块采取保守策略：显示源码级变化，不把半截结构化块交给 Markdown renderer。

下载 Markdown、Word、PDF 和下一轮上下文继续读 `artifactContent`。本轮只验证下载 Markdown 不含 `+ `、`- ` 前缀或已删除内容；DOCX/PDF 已有导出测试覆盖直接使用 `artifactContent`。

## 验收条件

1. Given 当前阶段历史中有上一版和当前版，When ArtifactPane 渲染正式阅读区，Then 默认显示“本轮变更”，新增行有绿色样式，删除行有红色删除线样式。
2. Given 用户关闭“本轮变更”，When ArtifactPane 渲染，Then 回到干净 Markdown 预览，不显示 diff 前缀。
3. Given 本轮 diff 可见，When 下载 Markdown，Then 下载内容等于干净 `artifactContent`，不包含删除行或 diff 前缀。
4. Given 当前阶段只有一个版本或基线与当前内容相同，When ArtifactPane 渲染，Then 不显示“本轮变更”控件。
5. Given Markdown 表格、Mermaid、代码块或 `ai4se-visual` 出现在变化行中，When 显示本轮 diff，Then 以源码行显示，不尝试渲染成破损 Markdown 结构。

## 非目标

- 不实现字符级、词级或段落级 diff。
- 不新增 Agent Runtime / typed SSE / store patch 协议。
- 不改变 `artifactContent`、`stageArtifacts`、历史版本保存格式或导出内容。
- 不替代历史版本弹窗中的恢复 / 丢弃行能力。
- 不处理完整增量 patch、块级 memoized rendering 或最终内容一致性校验；这些仍属于 `artifact-incremental-rendering.md` 后续能力包。
