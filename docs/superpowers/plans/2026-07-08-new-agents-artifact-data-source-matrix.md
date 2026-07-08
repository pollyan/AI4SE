# New Agents Artifact Data Source Matrix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 完成第 8B 轮全阶段 `artifact_data` 字段来源与视觉协议来源文档矩阵，让后续治理能清楚区分模型输出、后端派生、validation-only 和视觉生成来源。

**Architecture:** 本轮只修改文档，不改生产 runtime、schema、manifest、prompt 或测试代码。事实源来自 `artifact_data_renderers.py`、`agent_contracts.py`、`workflow_manifest.json` 和现有 backend tests；矩阵写入 `docs/TESTING.md`，执行证据写入结构化失败治理 todo。

**Tech Stack:** Markdown documentation, New Agents backend renderer contracts, goal-mode documentation checks.

---

## Files

- Modify: `docs/TESTING.md`
  - Add第 8B artifact_data source matrix after the第 8A fixture registry paragraph.
  - Record matrix maintenance sources and warnings.
- Modify: `docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md`
  - Update status line with第 8B.
  - Add progress note under第 8 轮回归门禁.
  - Add execution record with verification and residual risks.
- Create: `docs/superpowers/specs/2026-07-08-new-agents-artifact-data-source-matrix-design.md`
  - Record target handoff check and design.
- Create: `docs/superpowers/plans/2026-07-08-new-agents-artifact-data-source-matrix.md`
  - Record execution plan and checklist.

## Task 1: Confirm Source Facts

- [x] **Step 1: Confirm worktree safety**

Run:

```bash
git status -sb
```

Expected: clean or only current第 8B docs files after edits begin.

- [x] **Step 2: Confirm visual contract maps**

Run:

```bash
sed -n '397,460p' tools/new-agents/backend/agent_contracts.py
```

Expected: output includes `REQUIRED_ARTIFACT_MERMAID_DIAGRAMS` and `REQUIRED_ARTIFACT_STRUCTURED_VISUALS`.

- [x] **Step 3: Confirm derived-field tests**

Run:

```bash
rg -n "computes_missing|derives_statistics|rejects_inconsistent|rpn|score_summary|case_statistics" tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_runtime.py
```

Expected: output includes tests for STRATEGY `rpn`, CASES `case_statistics`, VALUE ELEVATOR `score_summary`, and inconsistent-statistics rejection tests.

## Task 2: Update `docs/TESTING.md`

- [x] **Step 1: Add matrix section**

In `docs/TESTING.md`, after the第 8A fixture registry paragraph, add a section titled:

```markdown
第 8B 轮补充了 `artifact_data` 字段来源与视觉协议矩阵。矩阵用于说明当前工程事实，不替代 Pydantic schema、renderer tests 或 `workflow_manifest.json`。维护时以 `ARTIFACT_DATA_STAGE_FIXTURES`、`REQUIRED_ARTIFACT_MERMAID_DIAGRAMS`、`REQUIRED_ARTIFACT_STRUCTURED_VISUALS`、`artifact_data_renderers.py` 和对应 renderer/runtime tests 为事实源。
```

- [x] **Step 2: Add 21-row matrix**

Add a Markdown table with these columns:

```markdown
| Workflow / Stage | 模型负责的 artifact_data | 后端派生 / 归一化 | 视觉来源 | 证据 |
|---|---|---|---|---|
```

Rows must cover all 21 stages:

```text
TEST_DESIGN/CLARIFY
TEST_DESIGN/STRATEGY
TEST_DESIGN/CASES
TEST_DESIGN/DELIVERY
REQ_REVIEW/REVIEW
REQ_REVIEW/REPORT
INCIDENT_REVIEW/TIMELINE
INCIDENT_REVIEW/ROOT_CAUSE
INCIDENT_REVIEW/IMPROVEMENT
IDEA_BRAINSTORM/DEFINE
IDEA_BRAINSTORM/DIVERGE
IDEA_BRAINSTORM/CONVERGE
IDEA_BRAINSTORM/CONCEPT
VALUE_DISCOVERY/ELEVATOR
VALUE_DISCOVERY/PERSONA
VALUE_DISCOVERY/JOURNEY
VALUE_DISCOVERY/BLUEPRINT
USER_STORY_BREAKDOWN/SCOPE
USER_STORY_BREAKDOWN/STORY_MAP
USER_STORY_BREAKDOWN/STORIES
USER_STORY_BREAKDOWN/HANDOFF
```

Required wording constraints:

- For STRATEGY, record `risks[].rpn` as backend-derived from S/O/D when absent; explicit inconsistent RPN still fails.
- For CASES, record `case_statistics` as backend-derived from `case_groups` when absent; explicit inconsistent statistics still fails.
- For VALUE ELEVATOR, record `score_summary.total_score` / `average_score` as normalized from `score_matrix`; explicit inconsistent summary still fails.
- For all ID/reference work that only rejects bad references, write `校验，不派生 ID`.
- For CONVERGE, record it as the only stage currently migrated to `artifactDataContract` manifest sync.
- For Mermaid visuals, write `后端由 <data> 生成 Mermaid <type>`.
- For `ai4se-visual`, write `后端由 <data> 生成 ai4se-visual <type>`.

- [x] **Step 3: Add residual boundary paragraph**

After the matrix, add:

```markdown
当前矩阵不表示所有派生字段都已后端化，也不表示所有阶段都完成 `artifactDataContract` manifest 同步。除 `IDEA_BRAINSTORM/CONVERGE` 外，其余阶段的关键 artifact_data 不变量仍主要由 Pydantic model、renderer tests、runtime instruction 和 artifact contract tests 共同保护。Mermaid 仍是后端 deterministic renderer 的编译目标；backend 仍不执行 Mermaid JS parse 或 `mmdc` 渲染门禁。
```

## Task 3: Update Structured Failure Todo

- [x] **Step 1: Update status line**

Append to the status line in `docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md`:

```text
；第 8B 轮 artifact_data 字段来源与视觉协议矩阵已完成
```

- [x] **Step 2: Update第 8 轮 progress**

Under “增加结构化失败回归门禁。（第 8 轮）”, append a progress sentence:

```markdown
第 8B 轮已在 `docs/TESTING.md` 补齐 21 个在线阶段的模型输出字段 / 后端派生字段 / 视觉协议来源矩阵，明确 validation-only 与 backend-derived 的边界，并记录 CONVERGE 是当前唯一完成 `artifactDataContract` manifest 同步迁移的阶段。
```

- [x] **Step 3: Add execution record**

Add a section before “每轮验收口径”:

```markdown
### 2026-07-08 第 8B 轮：artifact_data 字段来源与视觉协议矩阵
```

Include bullets for:

- `docs/TESTING.md` matrix added.
- Subagent explorer result incorporated.
- No production runtime/schema/manifest/test code changed.
- Verification commands and results.
- Residual risks.

## Task 4: Validate Docs

- [x] **Step 1: Run Markdown whitespace check**

Run:

```bash
git diff --check -- docs/TESTING.md docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md docs/superpowers/specs/2026-07-08-new-agents-artifact-data-source-matrix-design.md docs/superpowers/plans/2026-07-08-new-agents-artifact-data-source-matrix.md
```

Expected: no output.

- [x] **Step 2: Run placeholder scan**

Run:

```bash
rg -n "T[B]D|T[O]DO|implement[ ]later|<填[入]|待[补]" docs/TESTING.md docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md docs/superpowers/specs/2026-07-08-new-agents-artifact-data-source-matrix-design.md docs/superpowers/plans/2026-07-08-new-agents-artifact-data-source-matrix.md
```

Expected: exit code `1`, no matches.

- [x] **Step 3: Run matrix presence check**

Run:

```bash
rg -n "模型负责的 artifact_data|后端派生 / 归一化|视觉来源|第 8B" docs/TESTING.md docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md
```

Expected: matches in both files.

## Task 5: Commit and Push

- [x] **Step 1: Commit ownership check**

Run:

```bash
git status -sb
git diff --shortstat
git diff --cached --name-only
```

Expected: only第 8B docs files staged.

- [x] **Step 2: Stage docs**

Run:

```bash
git add docs/TESTING.md docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md docs/superpowers/specs/2026-07-08-new-agents-artifact-data-source-matrix-design.md docs/superpowers/plans/2026-07-08-new-agents-artifact-data-source-matrix.md
```

- [x] **Step 3: Commit and push**

Run:

```bash
git commit -m "docs(new-agents): 补齐 artifact data 来源矩阵"
git push
```

Expected: commit and push succeed on `codex/structured-failure-diagnostics`.
