# New Agents Artifact Comment Anchor Stale Status Design

## Current State Gap Analysis

事实源快照：

- 已读取：`AGENTS.md`、`docs/strategy/goal-mode-playbook.md`、`docs/index.md`、`docs/todos/new-agents-ux-professionalization.md`、`tools/new-agents/frontend/src/components/ArtifactPane.tsx`、`tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`、既有 `docs/superpowers/specs/2026-06-20-new-agents-artifact-comment-anchor-highlight-design.md`。
- 按需未展开：后端契约、SSE runtime、workflow manifest。本轮只读写前端本地协作状态，不改变后端 API、Agent Runtime 或 workflow contract。

能力包聚合：

| 能力包 | 聚合的原始缺口 | 用户动作链 / 工程信任闭环 | 为什么不能再拆薄 | 验收证据 |
| --- | --- | --- | --- | --- |
| 批注锚点稳定性 MVP | todo 中“批注锚点稳定性增强”；当前点击 `定位正文` 找不到正文时无反馈；审阅面板无法区分可定位批注和失效批注 | 用户打开批注或审阅面板 -> 看到锚点状态 -> 点击定位或确认失效 -> 决定是否重新确认批注位置 | 只加内部 helper 或只加测试都不能让用户知道批注失效；必须同时覆盖批注面板和审阅面板的可见状态 | ArtifactPane 组件测试覆盖失效批注在两个入口中的提示；lint/build/完整前端测试 |
| 批注锚点重新绑定 | 用户选中新正文后把旧批注重新绑定到新位置 | 用户看到失效 -> 选中新正文 -> 点击重新绑定 -> 批注 anchorText 更新并同步服务端 | 需要新增可写交互和同步语义，风险高于本轮；可在失效可见化后单独作为下一能力包 | 后续测试覆盖重新绑定、服务端 collaboration 同步和刷新恢复 |
| 审阅面板批量处理 | 在审阅面板集中解决批注、解锁章节、进入历史对比 | 用户从审阅入口直接处理所有待办 | 会触达多个现有动作的写入路径，和本轮锚点稳定性不是同一最小风险面 | 后续集成测试覆盖审阅面板动作链 |

候选 gap：

| 候选 | 来源 | 目标态 | 当前能力 | 缺口 | 价值 | 风险/复杂度 | 可测试性 | 去向 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 批注锚点失效可见化 | `docs/todos` Artifact 协作剩余项；当前测试覆盖定位成功但未覆盖定位失败 | 带 `anchorText` 的批注如果正文已改写，批注面板和审阅面板都显示 `锚点已失效` 与处理提示 | 批注可定位成功文本；审阅面板可列出未解决批注 | 找不到 anchorText 时用户没有反馈，会误以为点击无效或系统卡住 | 直接提升协作可信度，降低长产物改写后的批注误读 | 低。只读派生状态，不改持久化格式 | 前端组件红绿测试、ArtifactPane 回归 | 本轮 |
| 批注锚点重新绑定 | 同一 todo 后续增强 | 用户可把失效批注重新绑定到当前选区 | 选区捕获已有，批注写入已有 | 缺少针对已有批注更新 anchorText 的动作和同步 | 更完整，但需要新增写入操作 | 中。涉及 store action、服务端同步和 UI 误操作防护 | 需要 store/service/component 测试 | 下一轮候选 |
| 审阅面板批量处理 | 第五十五块审阅面板 MVP 后续 | 审阅面板可直接解决/定位/跳转 | 当前只读聚合 | 操作仍需进入批注或锁定面板 | 提升效率 | 中。多个状态写入汇聚 | 需要多入口交互测试 | 下一轮候选 |

排序结论：

1. 选择“批注锚点失效可见化”，因为它是当前批注锚点稳定性的最短完整动作链：用户能从批注或审阅入口看到可靠状态，并获得明确下一步。
2. “重新绑定”暂不选，因为它是可写能力，应该建立在失效状态可见之后，避免一次切片同时改显示、编辑、同步和恢复。
3. “审阅面板批量处理”暂不选，因为它跨批注、章节锁和历史轨迹多个动作链，当前优先把批注锚点这一条链闭环。

切片准入判断：

- 用户可感知动作链：用户打开 `更多产物操作 -> 批注` 或 `更多产物操作 -> 审阅`，系统判断 anchorText 是否仍存在于当前 artifact，存在则允许定位，不存在则显示失效提示和处理建议。
- 相邻缺口合并：本轮合并批注面板和审阅面板两个入口的失效状态；不只做一个 helper 或一个按钮文案。
- Superpowers 成本合理性：该能力直接影响用户对产物批注可靠性的判断，属于 Artifact 协作体验剩余能力包的一部分，值得完整 CGA/spec/plan/TDD/验证。
- 过薄风险检查：不是单控件或单字段；完成后用户从两个协作入口都能获得新的可靠状态反馈。
- 能力增量句：完成后，用户现在可以在产物改写导致批注锚点失效时立即看到提示，并知道需要重新确认批注位置。

切片厚度门禁：

- 入口：`更多产物操作 -> 批注`；`更多产物操作 -> 审阅`。
- 动作：用户查看带正文锚点的批注，或点击定位前先判断状态。
- 处理：前端用当前 `artifactContent` 和批注 `anchorText` 派生锚点状态。
- 可见结果：可定位批注保留 `定位正文`；失效批注显示 `锚点已失效` 和 `正文已变化，请重新确认这条批注的位置。`。
- 状态承接：本轮不写入新字段；状态由当前产物和已有批注派生，刷新后仍可重新计算。
- 失败反馈：找不到锚点时不再 silent no-op，而是在批注卡片和审阅卡片明确提示。
- 证据：新增 RED 测试先失败，再实现后通过；运行 ArtifactPane 组件测试、前端 lint/build/full test 和 `git diff --check`。
- 结论：通过。它形成了批注锚点可靠性的一条完整只读反馈链。

本轮 milestone：

作为 Lisa/Alex 工作区用户，当我在产物多次改写后查看批注时，可以直接知道批注还能否定位到当前正文，从而避免把过期批注误认为仍精确指向当前内容。

## User Story

作为 New Agents 工作区用户，当我打开产物批注或产物审阅面板时，如果一条批注原本绑定的正文已经被改写或删除，我希望系统明确告诉我锚点已失效，并提示我重新确认位置，而不是让我点击 `定位正文` 后没有任何反馈。

## Scope

- 在 `ArtifactPane` 中增加锚点状态派生逻辑，基于当前 `artifactContent` 和批注 `anchorText` 判断是否可定位。
- 批注面板中，带 `anchorText` 且仍可定位的批注继续显示 `定位正文`。
- 批注面板中，带 `anchorText` 但当前正文找不到该文本的批注显示 `锚点已失效` 和处理提示，不再只给一个无反馈的定位动作。
- 产物审阅面板的未解决批注列表展示同样的失效状态，避免审阅入口隐藏锚点风险。
- 不改变 `ArtifactComment` 持久化 schema，不新增后端字段或 API。

## Non-Goals

- 不做重新绑定当前选区。
- 不做跨节点 fuzzy match 或多候选定位。
- 不修改服务端 collaboration 同步契约。
- 不改变历史版本 diff、章节锁、审计轨迹或导出逻辑。

## Acceptance

1. Given 批注有 `anchorText` 且当前 artifact 仍包含该文本，When 用户打开批注面板并点击 `定位正文`，Then 现有高亮行为保持不变。
2. Given 批注有 `anchorText` 但当前 artifact 已不包含该文本，When 用户打开批注面板，Then 该批注显示 `锚点已失效` 和 `正文已变化，请重新确认这条批注的位置。`。
3. Given 同一失效批注，When 用户打开产物审阅面板，Then 未解决批注项同样显示 `锚点已失效`。
4. Given 批注没有 `anchorText`，When 用户打开批注或审阅面板，Then 不显示失效状态，因为它本来只是普通摘录批注。
5. 现有批注新增、删除、回复、解决状态、定位成功、审阅面板和 ArtifactPane 其他主路径测试不退化。

## Risks

- 简单 `includes` 判断只能覆盖精确文本仍存在的情况；如果正文轻微改写但语义仍相同，本轮会保守标记失效。
- 同一锚点文本多处出现时，现有定位仍高亮第一个匹配位置；本轮不改变该语义。
- UI 文案需要避免让用户误以为批注内容丢失；提示应表达为位置失效，而不是批注失效。

## Verification Plan

- `npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "stale anchor"`
- `npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx -t "artifact comment|artifact review panel|highlights anchored"`
- `npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx`
- `npm run lint`
- `npm run build`
- `npm run test`
- `git diff --check`
