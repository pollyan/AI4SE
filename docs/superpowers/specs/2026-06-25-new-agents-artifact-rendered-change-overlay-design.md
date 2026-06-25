# New Agents Artifact 正式渲染变更标记设计

## Current State Gap Analysis

事实源快照：
- 已读取：`AGENTS.md`、`docs/index.md`、`docs/strategy/goal-mode-playbook.md`、`docs/strategy/goal-mode-cga-template.md`、`docs/strategy/goal-mode-ci-verification.md`、`docs/ARCHITECTURE.md`、`docs/TESTING.md`、`docs/DESIGN_PRINCIPLES.md`、`docs/CODING_STANDARDS.md`。
- 已读取代码：`tools/new-agents/frontend/src/components/ArtifactPane.tsx`、`tools/new-agents/frontend/src/core/artifactSections.ts`、`tools/new-agents/frontend/src/core/artifactDiff.ts`、`tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`。
- 已扫描：`docs/todos/`、`docs/plans/`、`docs/superpowers/specs/`、`docs/superpowers/plans/` 中与 artifact、diff、渲染、变更相关条目。
- 工作区状态：已有无关脏文件 `dist/intent-test-proxy.zip`、`tools/intent-tester/frontend/static/intent-test-proxy.zip`、`tools/intent-tester/test-results/proxy/junit.xml`；本轮输入产生 `docs/mockups/artifact-incremental-rendering-preview.html`。本轮只允许写入 New Agents 前端、spec/plan 和必要记录，不回滚无关文件。

能力包聚合：

| 能力包 | 聚合的原始缺口 | 用户动作链 / 工程信任闭环 | 为什么不能再拆薄 | 验收证据 |
| --- | --- | --- | --- | --- |
| A. 右侧产出物正式渲染变更标记 | 用户反馈截图中“本轮变更”以源码 diff 展示；用户确认 HTML 原型目标效果 | 用户生成/更新 artifact -> 右侧默认正式预览 -> 当前变更在行/条目/节点局部标记 -> 修改项可见原值 -> 后续下载/编辑仍使用干净 Markdown | 只改按钮或只改颜色仍会保留源码 diff；只做表格行不处理段落/列表会让正式文档体验不完整 | `ArtifactPane` 组件 RED/GREEN 测试、前端聚焦测试、lint/build、`git diff --check` |
| B. 后端结构化 patch 继续扩大阶段覆盖 | 已归档 streaming 深度诊断指出非 STRATEGY 阶段仍可能较晚出现 artifact delta | 真实 provider 输出 artifact_data -> 后端局部 renderer -> SSE 多帧正式 artifact -> 前端逐段更新 | 与当前“显示格式错误”不是同一用户动作链；本轮不需要改 provider/runtime 才能解决截图问题 | 后端 runtime/renderer 测试、真实 SSE smoke |
| C. Artifact 审阅/历史 diff 信息架构重整 | 历史 diff、冲突 diff、审阅面板已有多套变更表达 | 用户审阅历史/冲突/当前变更 -> 在不同视图获得一致的审阅语言 | 范围更大，会触及保存冲突、历史恢复和审计操作，不适合并入本轮 | ArtifactPane 全量交互测试、浏览器回归 |

候选 gap：

| 候选 | 来源 | 目标态 | 当前能力 | 缺口 | 价值 | 风险/复杂度 | 可测试性 | 去向 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | 用户最新确认的 HTML 原型 | 默认正式预览，局部标记新增/修改，修改项显示原值，不重复列删除清单 | `ArtifactPane` 有 Markdown 预览、历史 diff、`artifactChangeIndex`、line diff | 当前自动打开 `current-artifact-diff` 源码面板，表格行和列表项没有正式渲染注解 | 直接解决用户可见主路径问题 | 中等，集中在前端渲染 | 组件测试可覆盖 | 本轮 |
| B | streaming 深度诊断归档 | 更多阶段支持段落级 artifact delta | STRATEGY 已有多帧正式 delta | 其他阶段中途帧较少 | 提升流式感知 | 中高，涉及后端 renderer/schema | 后端测试和 SSE smoke | 下一轮候选 |
| C | UX 专业化历史候选 | 当前变更、历史 diff、冲突 diff 统一审阅语言 | 多套 UI 并存 | 信息架构不一致 | 长期专业度 | 高，触及多条路径 | 组件/E2E | 后续更大能力包 |

排序结论：
1. 选择 A，因为用户刚完成原型确认，且当前截图问题位于右侧 artifact 主阅读路径；不处理会让前面增量 patch 工作的可见效果继续被源码 diff 污染。
2. B 暂不选，因为它处理后端流式供给，不解决“已经有 diff 数据但展示方式错误”的当前 UI 问题。
3. C 暂不选，因为会扩展到历史版本、保存冲突和审计操作，风险高于本轮主问题。

切片准入判断：
- 用户功能包边界：本轮交付“当前 artifact 变更在正式预览中可读呈现”。并入摘要条、表格行、列表项、段落、流程/可视化块的局部高亮和修改原值提示；排除后端 patch 生成、历史 diff 重设计、冲突处理重设计和导出富文本 diff。
- 用户可感知动作链：用户在 New Agents 生成或更新 artifact -> 右侧当前产出物默认保持正式 Markdown 渲染 -> 用户打开/关闭本轮变更标记 -> 看到具体新增/修改位置和修改前值 -> 下载/编辑仍得到干净 artifact 内容。
- 相邻缺口合并：合并“默认不显示源码 diff”“当前行/条目标记”“修改原值可见”“删除重复变更索引”四个同一显示问题。
- 过薄风险检查：不是单控件或单字段；它改变的是当前 artifact 主阅读体验，并以组件测试覆盖用户可见结果。
- 能力增量句：完成后，用户现在可以在正式渲染的右侧产出物中核对本轮新增和修改，并直接看到修改前值，而不会被 Markdown 源码 diff 面板打断。

切片厚度门禁：
- 入口：New Agents 右侧 `ArtifactPane` 当前阶段产出物。
- 动作：用户让 Agent 生成新版本 artifact，或点击工具栏切换本轮变更标记。
- 处理：前端基于当前阶段 artifact 历史版本和当前内容构建行级变更注解，并交给共享 Markdown renderer 局部渲染。
- 可见结果：默认仍是正式文档；表格行、列表项、段落或节点只在当前变更位置显示新增/修改样式，修改项显示“原：...”。
- 状态承接：`artifactContent`、`stageArtifacts`、history、下载、编辑、保存、协作状态不写入任何 diff 标记。
- 失败反馈：无历史基线时不显示本轮变更按钮；无法定位到具体 Markdown 节点时最多退化为摘要 chip，不显示源码 diff 伪正文。
- 证据：组件测试证明不出现 `current-artifact-diff` 源码面板、正式表格行有变更标记、修改项显示原值、下载仍是干净 Markdown；运行前端聚焦测试、lint/build、`git diff --check`。
- 结论：通过。

本轮用户故事：
作为 New Agents 测试设计用户，当我让 Lisa 更新右侧产出物后，我可以在正式渲染的文档中看到本轮具体新增/修改位置和修改前值，从而像审阅正式交付物一样核对变化，而不是阅读 Markdown 源码 diff。

## Superpowers 自问自答需求细化

### Explore Project Context

`ArtifactPane.tsx` 已经有正式 Markdown 渲染、历史 diff、编辑保存、冲突处理、批注、章节锁和导出能力。当前不应新增 agent/workflow 专属 renderer。`artifactSections.ts` 已能计算 section-level `artifactChangeIndex`，`artifactDiff.ts` 已能计算 line-level diff；因此本轮可以在前端复用这些通用数据，避免改后端 typed SSE 或 workflow manifest。

### Visual Companion Decision

本轮涉及视觉体验，用户已经先审阅并确认 `docs/mockups/artifact-incremental-rendering-preview.html` 的方向。实现以该原型为产品目标，不再新增新的视觉方案。

### Clarifying Questions

- 用户是谁：正在用 New Agents / Lisa 生成测试设计产出物的业务或测试人员。
- 要完成什么：核对本轮 artifact 更新，而不是阅读源码 diff。
- 成功状态是什么：右侧默认仍是正式文档，变更只落在具体行、列表项、段落或节点；修改项展示旧值。
- 输入来源是什么：当前阶段 `artifactHistory` 中上一版本和当前 `artifactContent`，以及 store 中 `artifactChangeIndex`。
- 约束是什么：不改后端协议，不把 diff 标记写进 artifact 内容，不影响下载、编辑、保存和历史 diff。
- 失败路径是什么：没有历史基线或 diff 为空时隐藏变更按钮；无法精确定位时只显示摘要，不回退到源码 diff 正文。
- 下游承接是什么：后续可在同一机制上继续完善更复杂的单元格级 diff，但本轮先交付行/条目级可读闭环。
- 不做什么：不做 Word/PDF 带批注导出，不重写历史版本 diff，不改冲突处理 diff。

### Approaches

1. 推荐：前端正式预览叠加局部注解。复用当前 line diff，在 ReactMarkdown components 中根据节点行号对 `tr`、`li`、`p` 等节点加样式和原值提示。优点是改动集中、能直接解决截图问题、不会污染 artifact 内容；缺点是依赖 Markdown AST position，测试必须覆盖。
2. 备选：后端生成结构化变更元数据。优点是语义更强，未来可做单元格级 diff；缺点是要改 SSE/API/store 契约，超出本轮主问题。
3. 备选：保留源码 diff 但改为弹窗或折叠。优点是改动小；缺点是没有解决用户要求的“和正式产出物一样的效果”。

结论：采用方案 1。

### Presented Design

Architecture：继续使用共享 `ArtifactPane` 和 Zustand store。新增或内联一个纯前端 helper，把 `currentChangeDiff` 转成按当前 Markdown 行号索引的渲染注解。`ReactMarkdown` 仍负责正式文档渲染，components 只叠加 CSS、badge 和原值提示。

Components：`ArtifactPane` 顶部在有变更时显示本轮摘要 chips；工具栏 `GitCompare` 按钮控制“显示/隐藏本轮变更标记”。预览区永远渲染正式 Markdown，不再把当前变更替换为 raw line diff 面板。历史版本弹窗仍保留 raw diff，因为那是审计/恢复视图。

Data Flow：`artifactHistory + artifactContent -> buildLineDiff -> buildRenderedChangeAnnotations -> createArtifactMarkdownComponents -> rendered markdown nodes`。下载、编辑和保存仍读取原始 `artifactContent`。

Error Handling：无基线、无有效 diff 或无法定位节点时不渲染注解。若只有删除没有当前行承接，只在摘要里体现删除数量，不在正文末尾重复列删除清单。

Testing：先改 `ArtifactPane.test.tsx`，RED 覆盖正式预览中表格行修改、新增行、修改原值、raw diff 不出现、下载内容干净。GREEN 后跑聚焦组件测试，再跑 New Agents 前端 lint/build 和 `git diff --check`；完成型代码故事提交前按目标模式决定是否运行全量本地验证。

## Acceptance Criteria

1. Given 当前阶段有上一版 artifact，且新版本修改 Markdown 表格行，When 用户打开右侧当前产出物，Then 默认显示正式渲染表格，修改行带局部标记，并显示旧行内容。
2. Given 当前阶段新增 Markdown 表格行或列表项，When 用户打开右侧当前产出物，Then 只标记新增行或新增列表项，不给整段章节大面积染色。
3. Given 当前阶段有删除内容，When 用户查看正式预览，Then 删除不在正文末尾或侧栏重复列出；只允许摘要中体现删除数量。
4. Given 用户点击隐藏本轮变更，When 预览仍处于正式渲染模式，Then 变更样式和原值提示消失，正文内容保持当前 artifact。
5. Given 用户下载 Markdown，When 预览中显示本轮变更标记，Then 下载内容仍等于干净的 `artifactContent`，不包含 `+`、`-`、`原：` 或 UI 标签。
