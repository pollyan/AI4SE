# 目标模式 Milestone 状态账本设计

## 背景

当前 `master` 的 `docs/todos/` 仍显示 DeepSeek V4 和 New Agents 增强诊断为活动候选，但多个目标模式 milestone 已经在隔离 worktree 中形成聚焦提交。由于这些提交尚未合回主线，目标模式每次恢复时都会从过期 todo 出发，导致“还剩几个功能”“哪些已经完成”“什么时候可以 merge/push”没有统一事实源。

本轮目标是建立一个可审计的状态账本，把活跃 todo、已完成分支提交、待最终合回工作和剩余能力包对齐。它不替代最终 merge/push，也不直接修改主工作区未提交改动。

## Superpowers 头脑风暴自问自答

### Explore Project Context

- 问：当前代码、文档、测试和 git 状态说明了什么？
  答：`master` 当前 HEAD 为 `e35c9643`，主工作区有 5 个既有未提交改动需要保护；`docs/todos/refactor/README.md` 仍列出 DeepSeek 和 New Agents 增强诊断为活动候选。与此同时，worktree 中存在多个已提交 milestone，例如 DeepSeek readiness `50f444f7`、E09 `9739fc27`、E03/E08 `dfa2b1b6`、E06 `c265ae4a`、E07 `32bffcbc`、E04 `eb957d55`、E13 `1782001b`、E14 `f088cf91`。
- 问：当前需求是否过大？
  答：如果本轮同时 cherry-pick 所有分支、解决冲突、跑完整回归、merge master 并 push，会和用户“全部做完后再最终 merge/push”的边界冲突，也可能覆盖主工作区脏文件。合适切片是先建立状态账本和 todo 对齐，作为最终集成前置证据。
- 问：当前事实源冲突是什么？
  答：主线 todo 文档是过期事实源；worktree commit 证据是已完成事实源。账本需要明确“完成但待合回”和“仍未完成”两类状态，不能把未合回误报成已在主线可用。

### Visual Companion Decision

- 问：是否需要视觉辅助？
  答：不需要。本轮是仓库状态、提交证据和文档账本，不涉及 UI 视觉或交互设计。

### Clarifying Questions

- 问：真实用户是谁？
  答：持续运行目标模式的维护者，以及需要知道“还剩几个功能、哪些可以最终合回”的用户。
- 问：用户要完成什么？
  答：从 `docs/todos/` 看到当前真实工作池：哪些能力包已由提交证明完成但待最终合回，哪些仍是下一轮可做能力包，哪些不能再重复逐项迁移。
- 问：成功状态是什么？
  答：`docs/todos/` 中出现一个明确账本，列出 completed-but-pending-merge、remaining-active、final-integration 条目；README 指向该账本；DeepSeek todo 不再作为逐 stage 活动候选；New Agents 增强诊断 todo 中每个 E 编号有准确状态口径。
- 问：输入来源是什么？
  答：`git show --stat`、`git worktree list`、现有 todo 文档和已提交 spec/plan 文件。
- 问：失败路径是什么？
  答：如果账本遗漏已完成提交，会继续误导后续 CGA；如果把未合回提交写成主线完成，会误导最终 merge/push；如果直接修改主工作区，会破坏用户未提交改动。
- 问：下游如何承接？
  答：后续目标模式先读取账本，再选择 E10/E11 或最终集成；最终 merge/push 时按账本中的 pending merge 清单逐项合入和验证。
- 问：本轮不做什么？
  答：不 push GitHub，不删除分支，不在 `master` 工作区改文件，不把全部 worktree commit 强行 cherry-pick 到主线，不做 E10/E11 的具体实现。

### Approaches

1. 推荐方案：新增状态账本文档并更新 README / todo 状态。
   - 优点：最小风险，直接解决进度口径混乱；不触碰主工作区脏文件；为最终集成提供清单。
   - 代价：功能代码仍未合入 `master`，需要后续最终集成。
2. 备选方案：创建 integration branch 并一次性 cherry-pick 所有已完成 commit。
   - 优点：能更接近最终 merge/push。
   - 代价：多个分支都修改 `workflow_manifest.json`、`agent_runtime.py`、`Header.tsx`、todo 文档，冲突和验证面很大；不适合作为当前事实源修复的第一步。
3. 备选方案：继续做下一个功能，例如 E10 或 E11。
   - 优点：直接推进产品能力。
   - 代价：当前“还剩多少”仍不清楚，会继续在过期 todo 上重复决策。

推荐方案是 1。它是最终合回前必须具备的工程信任闭环。

### Presented Design

- Architecture：新增 `docs/todos/refactor/2026-06-24-goal-mode-milestone-ledger.md` 作为当前状态账本；更新 `docs/todos/refactor/README.md` 指向它；更新两个活动 todo 的状态口径，避免重复逐 stage 或重复已完成能力包。
- Components：
  - Milestone ledger：按 `completed_pending_merge`、`remaining_active`、`final_integration_pending` 组织。
  - DeepSeek todo：状态从活动候选调整为本地确定性完成、待最终合回证据。
  - New Agents enhancement todo：增强机会清单标明已完成/待合回/剩余。
  - Verification：用 shell/rg 检查关键 commit SHA、E 编号和剩余能力包是否出现在账本中。
- Data Flow：git/worktree evidence -> ledger -> README/current entries -> future CGA。
- Error Handling：发现某个 commit 无法定位或无明确验证证据时，标为“候选/需复核”，不写成已完成；发现主工作区脏文件时继续隔离，不直接合并。
- Testing：纯文档切片采用等价验收检查。先运行缺失账本的失败检查，再写文档，最后用 `rg`、`git diff --check` 和状态审查验证。

## 用户故事

作为目标模式维护者，我希望 `docs/todos/` 能准确显示已完成但待合回的 milestone、真实剩余能力包和最终集成前置条件，从而避免重复消化已完成工作，并能安全规划最终 merge/push。

## 范围

本轮包含：

- 新增目标模式 milestone 状态账本。
- 更新 refactor README 的当前入口。
- 更新 DeepSeek todo 的当前状态。
- 更新 New Agents 增强诊断 todo 的 E 编号状态口径。
- 记录本轮没有执行最终 merge/push 的原因。

本轮不包含：

- 不 cherry-pick 或合并全部功能分支。
- 不 push GitHub。
- 不删除当前或历史分支。
- 不运行真实 DeepSeek smoke。
- 不实现 E10/E11。

## 验收条件

1. Given 当前 worktree commit 证据  
   When 读取状态账本  
   Then 能看到每个已完成 milestone 的 commit、对应 todo、状态和最终合回要求。

2. Given 后续目标模式从 `docs/todos/` 启动  
   When 读取 README 和账本  
   Then 不会把 DeepSeek 17 stage 迁移、E01/E02/E03/E04/E05/E06/E07/E08/E09/E12/E13/E14 当作未开始工作。

3. Given 当前仍未完成工作  
   When 读取账本  
   Then 能看到 E10、E11 仍是 New Agents 增强诊断中的剩余能力包，最终 integration/push 仍待所有活跃能力包完成后执行。

4. Given 主工作区有未提交改动  
   When 本轮结束  
   Then 主工作区未提交改动未被覆盖或回滚。

## 验证计划

- `test ! -f docs/todos/refactor/2026-06-24-goal-mode-milestone-ledger.md` 作为 RED 检查。
- `rg "50f444f7|9739fc27|dfa2b1b6|c265ae4a|32bffcbc|eb957d55|1782001b|f088cf91|fdcc3887|43cfe0bc|0ab900f2|8072a866" docs/todos/refactor/2026-06-24-goal-mode-milestone-ledger.md`
- `rg "E10|E11|最终合回|completed_pending_merge|remaining_active" docs/todos/refactor/2026-06-24-goal-mode-milestone-ledger.md docs/todos/refactor/README.md docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md`
- `git diff --check`
- `git status --short`

## 风险

- 账本不是最终主线合并；已完成分支仍需要后续 integration branch 合入、解决冲突和扩大验证。
- 若某个历史 worktree commit 的验证证据不完整，账本只能标为“待合回/需复核”，不能等同于主线完成。
- 主工作区已有未提交 todo 文档改动，本轮在隔离 worktree 中更新同名文件，后续最终合并时需要手工协调。

## Spec 自检

- Placeholder scan：无未决标记。
- 一致性检查：设计聚焦状态账本，不包含最终 merge/push。
- 范围检查：单一工程信任闭环，后续功能和最终集成都留到下一轮。
- 歧义检查：已完成但未合回与主线已完成明确区分。
