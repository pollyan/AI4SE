# Goal Mode Playbook Contract State Machine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the three overlapping goal-mode strategy documents with one behavior-preserving, contract-based state-machine Playbook whose rules are easier to execute, recover, and maintain.

**Architecture:** Rewrite `goal-mode-playbook.md` around explicit execution states, required artifacts, transition guards, and failure routes. Keep current implementation facts in `AGENTS.md`, `docs/TESTING.md`, package scripts, and CI; validate the new Playbook against a rule migration checklist and behavioral probes before retiring the two annexes.

**Tech Stack:** Markdown, Mermaid, Git, shell-based static document checks, read-only multi-agent review.

## Global Constraints

- Preserve all user-owned dirty changes in `AGENTS.md`, `docs/todos/refactor/README.md`, and `docs/todos/2026-07-10-new-agents-architecture-refactor.md`.
- Do not modify business code, tests, CI workflows, test runners, package scripts, or archived/historical execution records.
- Do not use line count, file count, or character count as a completion criterion.
- Keep `docs/strategy/goal-mode-playbook.md` as the only future-facing goal-mode entry point.
- Do not delete either annex until rule coverage and behavior review pass.
- Use `apply_patch` for every file change and stage only the paths owned by the current task.
- Treat `PASS`, `FAIL`, `NOT_RUN`, `BLOCKED`, `TIMEOUT`, and `FLAKY` as distinct verification states; retries never erase first-failure evidence.
- Historical statements that an earlier run read a retired annex remain unchanged because they are evidence, not future instructions.

---

### Task 1: Rewrite the Main Playbook as an Executable Contract

**Files:**
- Modify: `docs/strategy/goal-mode-playbook.md`
- Read: `docs/superpowers/specs/2026-07-10-goal-mode-playbook-contract-state-machine-design.md`
- Read: `docs/strategy/goal-mode-cga-template.md`
- Read: `docs/strategy/goal-mode-ci-verification.md`

**Interfaces:**
- Consumes: the approved design plus every normative rule in the current three strategy documents.
- Produces: a self-contained `goal-mode-playbook.md` with explicit states `BOOTSTRAP`, `ASSESS`, `MILESTONE`, `DESIGN`, `PLAN`, `IMPLEMENT`, `VERIFY`, `DELIVER`, `NEXT`, and `WAIT`.

- [ ] **Step 1: Capture the pre-rewrite baseline**

Run:

```bash
wc -l docs/strategy/goal-mode-playbook.md docs/strategy/goal-mode-cga-template.md docs/strategy/goal-mode-ci-verification.md
rg -n '^## |^### ' docs/strategy/goal-mode-playbook.md docs/strategy/goal-mode-cga-template.md docs/strategy/goal-mode-ci-verification.md
```

Expected: three files totaling roughly 700 lines, with duplicated CGA, thickness, verification, and delivery sections visible in the heading list.

- [ ] **Step 2: Run a red static contract check against the old Playbook**

Run:

```bash
rg -n 'BOOTSTRAP|ASSESS|MILESTONE|DESIGN|PLAN|IMPLEMENT|VERIFY|DELIVER|NEXT|WAIT|NOT_RUN|TIMEOUT|FLAKY' docs/strategy/goal-mode-playbook.md
```

Expected: FAIL to find the complete state and result contract; the old Playbook does not define all required state identifiers and honest verification states.

- [ ] **Step 3: Replace the main Playbook with the approved state-machine structure**

Use `apply_patch` to replace the full content of `docs/strategy/goal-mode-playbook.md`. The new file must contain these sections and responsibilities:

```markdown
# AI4SE 目标模式运行手册

## 1. 目标模式契约
- 规范语义：必须、默认、允许
- 唯一入口、事实源优先级、授权边界、暂停条件
- 长期 todo、CGA/承接、spec、plan、验证记录职责

## 2. 执行状态机
- Mermaid state flow
- BOOTSTRAP / ASSESS / MILESTONE / DESIGN / PLAN
- IMPLEMENT / VERIFY / DELIVER / NEXT / WAIT
- 每个状态均定义：进入条件、必需产物、离开门禁、失败路由

## 3. 评估与厚切片契约
- 完整 CGA 与承接检查的互斥选择条件
- 两套紧凑必填 schema
- 强制改道条件
- 入口、动作、处理、可见结果、状态承接、失败反馈、证据七项门禁
- 工程信任闭环的严格适用条件

## 4. 协作、设计与实现
- 单工作区与 dirty diff 保护
- 主 Agent / 子智能体责任、写入边界、复核和两次失败降级
- brainstorming -> 中文 spec -> implementation plan -> TDD/文档验证

## 5. 验证、CI 与证据
- 聚焦 -> 必要跨层 -> 动态 CI 映射 -> 完成型全量验证
- PASS / FAIL / NOT_RUN / BLOCKED / TIMEOUT / FLAKY
- 首错保留、retry-to-green 禁止冒充稳定通过
- deterministic/mock/真实 UI/真实前后端/真实外部服务与模型证据分层
- CI 等价最小记录字段
- 远端 CI 首错、比较、分类、复现、防复发和重跑闭环

## 6. 记录与交付
- 稳定事实源和 todo 更新
- 精确 staging、聚焦 commit、默认及时 push 及例外
- 完成说明、HEAD/远端/未提交 diff、残余风险
- 进度按能力包计算

## 7. 最小启动提示词
- 只声明目标、授权和 Playbook 路径
```

Do not copy the old fill-in templates, long example catalog, fixed command matrix, current CI job names, model settings, coverage thresholds, or numeric diff-size thresholds.

- [ ] **Step 4: Run the green static schema checks**

Run:

```bash
rg -n 'BOOTSTRAP|ASSESS|MILESTONE|DESIGN|PLAN|IMPLEMENT|VERIFY|DELIVER|NEXT|WAIT' docs/strategy/goal-mode-playbook.md
rg -n 'PASS|FAIL|NOT_RUN|BLOCKED|TIMEOUT|FLAKY' docs/strategy/goal-mode-playbook.md
rg -n '入口|动作|处理|可见结果|状态承接|失败反馈|证据' docs/strategy/goal-mode-playbook.md
rg -n '完整 CGA|目标承接检查|未选候选去向|工程信任闭环|首个真实错误|CI 等价' docs/strategy/goal-mode-playbook.md
```

Expected: every command finds the complete required vocabulary in a single file.

- [ ] **Step 5: Check document formatting and ownership**

Run:

```bash
git diff --check -- docs/strategy/goal-mode-playbook.md
git status --short
git diff -- docs/strategy/goal-mode-playbook.md
```

Expected: no whitespace errors; only `goal-mode-playbook.md` is changed by this task; the three pre-existing user changes remain untouched.

- [ ] **Step 6: Commit the independently usable new Playbook while the annexes still exist**

Run:

```bash
git add docs/strategy/goal-mode-playbook.md
git diff --cached --name-only
git commit -m "docs(goal-mode): 重构目标模式状态机"
```

Expected: the staged list contains only `docs/strategy/goal-mode-playbook.md`, and the commit succeeds.

### Task 2: Prove Rule Coverage and Behavioral Equivalence

**Files:**
- Modify if review finds gaps: `docs/strategy/goal-mode-playbook.md`
- Read: `docs/strategy/goal-mode-cga-template.md`
- Read: `docs/strategy/goal-mode-ci-verification.md`
- Read: `docs/superpowers/specs/2026-07-10-goal-mode-playbook-contract-state-machine-design.md`

**Interfaces:**
- Consumes: the new Playbook and the still-present annexes.
- Produces: reviewed Playbook with no unmapped P0/P1 rule and no failing behavioral probe.

- [ ] **Step 1: Build a temporary rule migration checklist during review**

For every normative rule in the three old documents, record one of these decisions in reviewer notes:

```text
KEEP:§2.1
MERGE:§3.2
SOURCE:docs/TESTING.md
DROP:exact duplicate of rule R-017
```

Expected: no rule is unclassified, and no `DROP` decision removes a transition guard, required artifact, failure route, evidence boundary, or delivery condition. The checklist remains review evidence and is not added as a permanent repository file.

- [ ] **Step 2: Dispatch independent read-only reviewers**

Reviewer A checks rule loss, contradictory requirements, unreachable states, and bypassable transition guards. Reviewer B checks CGA/continuation choice, thick-slice behavior, CI mapping, honest verification states, evidence layering, and remote-CI recovery. Neither reviewer may edit files.

Expected: each reviewer returns findings with severity, source rule, new section, and recommended correction. P0/P1 findings block annex deletion.

- [ ] **Step 3: Run the twelve behavior probes from the approved design**

Review the Playbook against these inputs and require the stated decision:

```text
1. No user goal -> full CGA with at least two capability candidates or a single-candidate reason.
2. Confirmed next slice, no changed facts -> continuation check.
3. Confirmed next slice plus blocking failure/user correction -> reroute, not continuation.
4. Single field/parser/button/test request -> expand, justify trust-loop exception, or defer.
5. Dirty unrelated worktree changes -> protect and isolate ownership.
6. Shared API/SSE/persistence change -> cross-layer verification plus dynamic CI mapping.
7. Full script passes but a CI risk is unmapped -> do not claim CI equivalence.
8. Skip/no collection/timeout/missing dependency -> not PASS.
9. Mock browser E2E passes -> do not claim real backend or real-model quality.
10. Remote CI fails -> compare local evidence, reproduce, prevent recurrence, rerun.
11. Subagent fails or edits out of scope -> main agent verifies, retries smaller once, then degrades.
12. Slice is not fully verified -> no delivery and no NEXT transition.
```

Expected: all twelve outcomes are directly required by the Playbook without relying on either annex.

- [ ] **Step 4: Fix every P0/P1 review gap**

Use `apply_patch` to update `goal-mode-playbook.md`. Do not add new permanent files. Repeat Steps 1–3 until reviewers find no P0/P1 execution regression.

- [ ] **Step 5: Verify fixes and commit only if the review changed the Playbook**

Run:

```bash
git diff --check -- docs/strategy/goal-mode-playbook.md
git diff -- docs/strategy/goal-mode-playbook.md
```

If there are changes:

```bash
git add docs/strategy/goal-mode-playbook.md
git diff --cached --name-only
git commit -m "docs(goal-mode): 补齐状态机执行门禁"
```

Expected: no formatting errors; any commit contains only the Playbook.

### Task 3: Retire the Two Annexes Safely

**Files:**
- Delete: `docs/strategy/goal-mode-cga-template.md`
- Delete: `docs/strategy/goal-mode-ci-verification.md`
- Modify only if a future-facing reference exists: the exact active file containing that reference

**Interfaces:**
- Consumes: a reviewed Playbook with all behavior probes passing.
- Produces: a single future-facing target-mode rule source with no live dependency on either annex.

- [ ] **Step 1: Prove there are no future-facing references before deletion**

Run:

```bash
rg -n 'goal-mode-cga-template\.md|goal-mode-ci-verification\.md' docs/strategy AGENTS.md docs/index.md docs/todos/refactor/README.md docs/plans/2026-06-25-new-agents-agent-framework-phase1-phase2.md docs/todos/2026-07-10-new-agents-architecture-refactor.md
```

Expected: no matches outside the two annex files themselves. If a future-facing match remains, replace it with `docs/strategy/goal-mode-playbook.md` using `apply_patch`; do not edit dated execution snapshots.

- [ ] **Step 2: Delete the annexes with `apply_patch`**

Delete both files only after Task 2 has no blocking finding.

- [ ] **Step 3: Verify deletion and historical-reference handling**

Run:

```bash
test ! -e docs/strategy/goal-mode-cga-template.md
test ! -e docs/strategy/goal-mode-ci-verification.md
rg -n 'goal-mode-cga-template\.md|goal-mode-ci-verification\.md' docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md docs/todos/archive || true
```

Expected: both files are absent. Remaining matches, if any, are dated historical facts only and are intentionally unchanged.

- [ ] **Step 4: Run final static document checks for this task**

Run:

```bash
git diff --check -- docs/strategy/goal-mode-cga-template.md docs/strategy/goal-mode-ci-verification.md
git status --short
git diff --stat
```

Expected: no whitespace errors; the task diff contains the two deletions and only explicitly justified future-reference edits; user dirty files remain unmodified by this task.

- [ ] **Step 5: Commit annex retirement**

Run:

```bash
git add docs/strategy/goal-mode-cga-template.md docs/strategy/goal-mode-ci-verification.md
git diff --cached --name-only
git commit -m "docs(goal-mode): 退役目标模式重复附录"
```

Expected: only the two deleted annexes and any necessary future-reference migration are committed.

### Task 4: Final Acceptance and Handoff

**Files:**
- Verify: `docs/strategy/goal-mode-playbook.md`
- Verify: `docs/superpowers/specs/2026-07-10-goal-mode-playbook-contract-state-machine-design.md`
- Verify: `docs/superpowers/plans/2026-07-10-goal-mode-playbook-contract-state-machine.md`

**Interfaces:**
- Consumes: the committed Playbook rewrite and annex retirement.
- Produces: evidence-backed completion report and a clean handoff back to the test-quality scan prompt design.

- [ ] **Step 1: Run the complete static acceptance suite**

Run:

```bash
rg -n 'BOOTSTRAP|ASSESS|MILESTONE|DESIGN|PLAN|IMPLEMENT|VERIFY|DELIVER|NEXT|WAIT' docs/strategy/goal-mode-playbook.md
rg -n 'PASS|FAIL|NOT_RUN|BLOCKED|TIMEOUT|FLAKY' docs/strategy/goal-mode-playbook.md
rg -n '完整 CGA|目标承接检查|未选候选去向|入口|状态承接|失败反馈|工程信任闭环|首个真实错误|CI 等价' docs/strategy/goal-mode-playbook.md
git diff --check 584ea756..HEAD
```

Expected: all mandatory contracts are present and recent commits have no whitespace errors.

- [ ] **Step 2: Confirm future-reference and worktree ownership**

Run:

```bash
rg -n 'goal-mode-cga-template\.md|goal-mode-ci-verification\.md' docs/strategy AGENTS.md docs/index.md docs/todos/refactor/README.md docs/plans/2026-06-25-new-agents-agent-framework-phase1-phase2.md docs/todos/2026-07-10-new-agents-architecture-refactor.md
git status -sb
git log -4 --oneline
```

Expected: no future-facing old-annex references; user dirty files are still present and unstaged; the log shows focused design, plan, Playbook, and retirement commits.

- [ ] **Step 3: Record validation scope honestly**

The completion report must state that this was a documentation-governance change validated by rule migration, static checks, behavior probes, and independent review. It must not claim application tests, real browser tests, external services, or LLM quality gates were run.

- [ ] **Step 4: Resume the original task**

Use the new Playbook as the sole governance source when completing the test-strategy and quality-assurance scan prompt. Keep scan evidence in the scan report, target states and thick slices in the active todo, and future implementation details in per-slice specs/plans.
