# Milestone Ledger Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `docs/todos/` reflect verified goal-mode milestone evidence, separating completed-but-pending-merge work from truly remaining active capability packages.

**Architecture:** Add a single status ledger under `docs/todos/refactor/`, then update the refactor README and active todo files to point to that ledger. This is a document-only engineering trust loop; it does not merge feature branches or push to GitHub.

**Tech Stack:** Markdown docs, git evidence, shell/rg validation checks.

---

## File Structure

- Create: `docs/todos/refactor/2026-06-24-goal-mode-milestone-ledger.md`
  - Authoritative ledger for completed pending merge, remaining active packages, final integration queue, and protected main-worktree changes.
- Modify: `docs/todos/refactor/README.md`
  - Point current goal-mode recovery to the ledger and state which entries are active.
- Modify: `docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md`
  - Mark DeepSeek structured artifact migration as locally complete pending final merge.
- Modify: `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md`
  - Mark E01/E02/E03/E04/E05/E06/E07/E08/E09/E12/E13/E14 as completed pending merge with commit evidence; keep E10/E11 as remaining active.
- Modify: `docs/superpowers/plans/2026-06-24-milestone-ledger-sync.md`
  - Track plan execution and validation evidence.

## Task 1: RED Documentation Acceptance Check

**Files:**
- Test target: `docs/todos/refactor/2026-06-24-goal-mode-milestone-ledger.md`

- [x] **Step 1: Run missing-ledger RED check**

Run:

```bash
test -f docs/todos/refactor/2026-06-24-goal-mode-milestone-ledger.md
```

Expected: FAIL with exit code 1 because the ledger file does not exist yet.

Actual: failed with exit code 1 as expected.

- [x] **Step 2: Run missing-evidence RED check**

Run:

```bash
rg "50f444f7|9739fc27|dfa2b1b6|c265ae4a|32bffcbc|eb957d55|1782001b|f088cf91|fdcc3887|43cfe0bc|0ab900f2|8072a866" docs/todos/refactor/2026-06-24-goal-mode-milestone-ledger.md
```

Expected: FAIL because the file does not exist.

Actual: failed because the ledger file did not exist.

## Task 2: Create Milestone Ledger

**Files:**
- Create: `docs/todos/refactor/2026-06-24-goal-mode-milestone-ledger.md`

- [x] **Step 1: Create ledger document**

Create a Markdown document with these sections:

```markdown
# Goal Mode Milestone Ledger

> 状态: 活动事实源
> 更新日期: 2026-06-24
> 用途: 记录目标模式已验证 milestone、待最终合回提交、剩余能力包和最终集成条件。

## 当前结论

- DeepSeek V4 结构化产物数据改造: 本地确定性完成，待最终合回。
- New Agents 增强诊断: E01/E02/E03/E04/E05/E06/E07/E08/E09/E12/E13/E14 已有提交证据，待最终合回或主线复核。
- 当前仍作为后续能力包候选: E10 专业方法库配置、E11 Prompt/template 版本管理。
- 最终 merge/push/删分支: 仅在所有活跃能力包完成、主线脏文件处理完、integration branch 验证通过后执行。
```

Add a `completed_pending_merge` table with these rows:

| Capability | Todo | Commit | Branch | Evidence |
| --- | --- | --- | --- | --- |
| DeepSeek V4 格式化输出 readiness gate | DeepSeek V4 structured artifact data | `50f444f7` | `codex/deepseek-v4-format-output-readiness` | runtime readiness, renderer contract |
| E09 运行统计产品化诊断建议 | E09 | `9739fc27` | `codex/runtime-observability-actions-current` | observability API/service/Header tests |
| E03/E08 Artifact 与工作流质量治理 | E03/E08 | `dfa2b1b6` | `codex/workflow-quality-governance-current` | workflowQuality + ArtifactPane tests |
| E06 Run 历史中心增强 | E06 | `c265ae4a` | `codex/run-history-reuse-goal-current` | backend persistence/API + Header/service tests |
| E07 Workflow handoff 上下文强化 | E07 | `32bffcbc` | `codex/workflow-handoff-context-goal-mainline` | handoff backend/frontend tests |
| E04 Lisa 测试资产质量闭环 | E04 | `eb957d55` | `codex/lisa-test-asset-quality-loop-goal-mainline` | test asset backend/frontend tests |
| E13 Alex 用户故事拆解 workflow | E13 | `1782001b` | `codex/alex-story-breakdown-goal-current` | workflow manifest/runtime/contract/prompt tests |
| E14 Alex PRD 质量评审 workflow | E14 | `f088cf91` | `codex/alex-prd-review-goal-mainline` | workflow manifest/runtime/contract/prompt tests |
| E05 章节级重生成 / 定向修订闭环 | E05 | `fdcc3887` | `codex/artifact-section-regeneration` | artifactSections/chatService/ArtifactPane tests |
| E12 Workflow schema dry-run/scaffold | E12 | `43cfe0bc` | `codex/workflow-dry-run-gate` | workflow dry-run validation tests |
| E02 阶段缺失信息清单 | E02 | `0ab900f2` | `codex/new-agents-missing-info-checklist` | ChatPane/ArtifactPane/artifactQuality tests |
| E01 Workflow 入口 preview | E01 | `8072a866` | historical branch evidence | WorkflowSelect/workflows tests |

Add `remaining_active` with E10 and E11 only.

Add `protected_main_worktree_changes` listing the five current dirty paths from CGA.

Add `final_integration_policy` explaining no push/delete/merge until integration branch verifies all pending commits and protected changes are handled.
```

## Task 3: Update Todo Entry Points

**Files:**
- Modify: `docs/todos/refactor/README.md`
- Modify: `docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md`
- Modify: `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md`

- [x] **Step 1: Update README**

Set current entry to the ledger first, then remaining active todos:

```markdown
## 当前入口

- `2026-06-24-goal-mode-milestone-ledger.md`：目标模式当前事实源；先读它，再决定下一轮是否做 E10、E11 或最终集成。
- `2026-06-23-new-agents-enhancement-diagnostic.md`：剩余活跃能力包保留 E10、E11；其他 E 编号见账本的 completed_pending_merge。
- `2026-06-23-deepseek-v4-structured-artifact-data.md`：本地确定性改造已完成，待最终合回；除非 CGA 发现回归或真实 smoke 失败，不恢复为逐 stage 活动候选。
```

- [x] **Step 2: Update DeepSeek todo**

Change the status line to:

```markdown
> 状态: 本地确定性改造已完成，待最终合回；真实 DeepSeek V4 Flash smoke 仍需显式凭证、网络和额度
```

Add a short note pointing to the ledger and commit `50f444f7`.

- [x] **Step 3: Update New Agents diagnostic todo**

In the opportunity table, rewrite E01/E02/E03/E04/E05/E06/E07/E08/E09/E12/E13/E14 acceptance text to start with `已完成待合回:` and include the commit SHA. Leave E10 and E11 unchanged as remaining active.

Add a section:

```markdown
## 当前剩余能力包

- E10 专业方法库配置。
- E11 Prompt/template 版本管理。

其余 E 编号如果需要恢复，必须先通过 CGA 证明当前主线集成后仍存在回归或未验收缺口。
```

## Task 4: GREEN Documentation Verification

**Files:**
- Validate: `docs/todos/refactor/2026-06-24-goal-mode-milestone-ledger.md`
- Validate: `docs/todos/refactor/README.md`
- Validate: `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md`
- Validate: `docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md`

- [x] **Step 1: Run ledger evidence check**

Run:

```bash
rg "50f444f7|9739fc27|dfa2b1b6|c265ae4a|32bffcbc|eb957d55|1782001b|f088cf91|fdcc3887|43cfe0bc|0ab900f2|8072a866" docs/todos/refactor/2026-06-24-goal-mode-milestone-ledger.md
```

Expected: all listed commit SHAs are present.

Actual: all listed commit SHAs are present.

- [x] **Step 2: Run remaining-active check**

Run:

```bash
rg "remaining_active|E10|E11|completed_pending_merge|最终合回" docs/todos/refactor/2026-06-24-goal-mode-milestone-ledger.md docs/todos/refactor/README.md docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md
```

Expected: output shows ledger sections, README pointer, and E10/E11 remaining section.

Actual: output shows ledger sections, README pointer, and E10/E11 remaining section.

- [x] **Step 3: Run placeholder and whitespace checks**

Run:

```bash
rg "TB[D]|TO[D]O|待[补]|占[位]" docs/todos/refactor/2026-06-24-goal-mode-milestone-ledger.md docs/superpowers/specs/2026-06-24-milestone-ledger-sync-design.md docs/superpowers/plans/2026-06-24-milestone-ledger-sync.md
git diff --check
git status --short
```

Expected: no placeholder matches, diff check exits 0, status only contains this milestone's docs.

Actual: placeholder check returned no matches, `git diff --check` exited 0, and status only contains this milestone's docs.

## Task 5: Commit

**Files:**
- Add/Modify this milestone's docs only.

- [x] **Step 1: Review scope**

Run:

```bash
git diff --stat
git status --short
```

Expected: only `docs/todos/refactor/*` and `docs/superpowers/*/2026-06-24-milestone-ledger-sync*` are changed.

Actual: `git diff --stat` shows only tracked refactor todo docs; `git status --short` additionally shows the new spec, plan, and milestone ledger docs for this milestone.

- [x] **Step 2: Commit**

Run:

```bash
git add docs/todos/refactor/2026-06-24-goal-mode-milestone-ledger.md docs/todos/refactor/README.md docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md docs/superpowers/specs/2026-06-24-milestone-ledger-sync-design.md docs/superpowers/plans/2026-06-24-milestone-ledger-sync.md
git commit -m "docs(goal): 对齐目标模式 milestone 状态账本"
```

Actual: staged only the six milestone documentation files and committed them with this message. The closeout note records the final branch HEAD SHA after any amend.

## Self-Review

- Spec coverage: plan covers ledger creation, README/todo updates, RED/GREEN document checks, protected worktree state, and commit.
- Placeholder scan: no unresolved markers.
- Type consistency: not applicable; document-only milestone.
