# New Agents Artifact 批注锚点重新绑定设计

## Current State Gap Analysis 摘要

事实源快照：

- 已读取：`AGENTS.md`、`docs/strategy/goal-mode-playbook.md`、`docs/index.md`、`docs/todos/new-agents-ux-professionalization.md`、`tools/new-agents/frontend/src/components/ArtifactPane.tsx`、`tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`、`tools/new-agents/frontend/src/store.ts`、`tools/new-agents/frontend/src/core/types.ts`。
- 当前 git 状态：主工作区只有两个既有 zip 改动，本轮在独立 worktree `codex/new-agents-comment-anchor-rebind` 中实施。
- 子智能体：CGA 阶段尝试分发只读 explorer，但工具返回 `agent thread limit reached`，因此本轮由主 Agent 顺序完成探索、实现和验证。

能力包聚合：

| 能力包 | 聚合的原始缺口 | 用户动作链 / 工程信任闭环 | 验收证据 |
| --- | --- | --- | --- |
| 批注锚点重新绑定 | todo #7 中“批注锚点稳定性增强”；上一切片已提示 `锚点已失效`，但没有修复手段 | 用户看到失效批注 -> 在当前 artifact 正文选中新位置 -> 重新绑定 -> 批注摘录和锚点更新 -> 定位正文恢复可用并同步 | `ArtifactPane` 组件测试、store 测试、协作同步 mock 断言、lint/build |
| 更复杂三方 merge 解析 | todo #7 中“更复杂但可证明安全的三方 merge” | 用户保存旧草稿遇到冲突 -> 系统识别更多安全合并或明确拒绝 | 需要先定义新的安全场景，留作下一轮候选 |

排序结论：选择批注锚点重新绑定。它直接补齐上一切片“发现失效”之后的用户动作链，风险比继续扩展三方 merge 长尾更可控，且不改变 Agent Runtime、后端 API 主契约或 workflow contract。

本轮 milestone：

作为正在审阅和校准 New Agents 产出物的用户，当模型或我自己改写了正文导致批注锚点失效时，我可以选中新的正文位置并重新绑定批注，从而让批注继续准确定位、同步和参与后续审阅。

## 用户故事

作为 New Agents 工作区用户，当我打开产物批注发现某条批注显示 `锚点已失效` 时，我希望能在当前产物正文中选中新的相关文本，并把这条批注重新绑定到新位置。重新绑定后，这条批注应该再次支持 `定位正文`，并在刷新或恢复 run 后保留新的锚点。

## 场景

1. 用户或 Agent 改写 artifact 正文，旧批注的 `anchorText` 已不在当前正文中。
2. 用户打开 `更多产物操作 -> 批注`，看到 `锚点已失效`。
3. 用户在 artifact 预览里选中新正文片段。
4. 用户点击该批注上的 `重新绑定选区`。
5. 系统把批注的 `artifactExcerpt` 和 `anchorText` 更新为当前选区文本，并复用现有 collaboration sync。
6. 批注不再显示失效状态，`定位正文` 恢复可用。

## 范围

- 在前端 store 中增加更新单条批注锚点的 action。
- 在 `ArtifactPane` 批注面板中为失效批注提供 `重新绑定选区` 操作。
- 重新绑定时复用现有 artifact 预览选区读取逻辑，只接受 artifact 内的非空选区。
- 重新绑定后调用现有 `syncArtifactCollaborationState`，保持服务端 run collaboration snapshot 同步。
- 补充测试覆盖成功重绑、同步、定位恢复和无有效选区时不写入错误锚点。
- 更新 todo 记录本切片完成，并把更复杂三方 merge 解析保留为后续候选。

## 非目标

- 不新增后端字段，不改变 `ArtifactComment` 持久化 schema。
- 不做 fuzzy matching、多候选推荐或自动推断新锚点。
- 不做 range offset / DOM 路径锚点 schema。
- 不在审阅面板中直接做重绑定；本轮通过批注面板完成可写动作。
- 不做多人实时协同、分享权限、恢复中心或 intent-tester 自动打通。

## 验收条件

1. Given 批注有 `anchorText` 但当前 artifact 不包含该文本，When 用户选中 artifact 内的新文本并点击 `重新绑定选区`，Then store 中该批注的 `anchorText` 和 `artifactExcerpt` 更新为新文本，且失效提示消失。
2. Given 重新绑定后的批注，When 用户点击 `定位正文`，Then 当前 artifact 预览中新文本被高亮。
3. Given 当前存在可同步 run，When 用户重新绑定批注，Then 调用 `updateRunArtifactCollaboration` 并传入更新后的 comments。
4. Given 用户没有选中 artifact 内文本，When 点击 `重新绑定选区`，Then 不更新批注锚点，并显示 `请先在右侧正文中选中新的批注位置。`。
5. Given 无 `anchorText` 的普通批注或仍 active 的批注，When 打开批注面板，Then 不显示错误的失效重绑状态。

## 风险

- 当前选区读取依赖浏览器 Selection API；测试需要显式构造 range，避免只测试实现细节。
- 重绑只做精确文本锚点，正文再次改写仍可能失效；这是当前轻量锚点模型的既有边界。
- 如果同一新文本在 artifact 中出现多次，定位仍使用现有首次匹配策略；本轮不改变。
- `syncArtifactCollaborationState` 当前从 store 最新状态读取 collaboration 数据，store action 必须先完成更新再同步。

## 验证计划

- `npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "rebinds stale comment anchor"`
- `npm run test -- --run src/__tests__/store.test.ts -t "artifact comment anchor"`
- `npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "stale anchor|highlights anchored|syncs artifact comments"`
- `npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx`
- `npm run lint`
- `npm run build`
- `npm run test`
- `git diff --check`
