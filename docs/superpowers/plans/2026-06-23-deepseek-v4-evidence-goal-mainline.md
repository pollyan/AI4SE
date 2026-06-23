# DeepSeek V4 Evidence Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增 DeepSeek V4 结构化输出证据门禁，证明本地 JSON mode -> artifact_data -> renderer -> contract 链路，并提供缺凭证时明确 skip 的可选真实 smoke。

**Current Baseline:** 本计划在隔离 worktree `codex/deepseek-v4-evidence-goal-mainline` 执行，并已 rebase 到当前 `master`，包含 2026-06-24 目标模式 playbook 对 Superpowers 头脑风暴的最新要求。主工作区存在既有未提交改动，本轮不触碰。

**Architecture:** Evidence gate 复用共享 Agent Runtime、provider capability、artifact_data renderer 和 artifact contract。它是 backend 工程验证入口，不新增 DeepSeek 专属 runtime、API path、store 或 renderer。

**Tech Stack:** Python 3.11, pytest, existing New Agents backend runtime, Pydantic artifact_data schemas.

---

## 文件结构

- Create: `tools/new-agents/backend/deepseek_v4_smoke_evidence.py`
- Create: `tools/new-agents/backend/tests/test_deepseek_v4_smoke_evidence.py`
- Modify: `docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md`
- Modify: `docs/todos/refactor/README.md`
- Create: `docs/superpowers/specs/2026-06-23-deepseek-v4-evidence-goal-mainline-design.md`
- Create: `docs/superpowers/plans/2026-06-23-deepseek-v4-evidence-goal-mainline.md`

## Task 1: RED - 写 evidence gate 验收测试

- [x] **Step 1: 新增 backend test file**

Create `tools/new-agents/backend/tests/test_deepseek_v4_smoke_evidence.py` with tests that import:

```python
from deepseek_v4_smoke_evidence import (
    EvidenceStatus,
    run_local_deepseek_v4_evidence,
    run_optional_real_deepseek_v4_smoke,
)
```

Tests:

- local evidence returns `passed`.
- fake client captured `response_format == {"type": "json_object"}`.
- fake client prompt contains `artifact_data`.
- missing real smoke env returns `skipped`.
- malformed fake output returns `failed` with contract/schema reason.

- [x] **Step 2: Run RED**

Run:

```bash
python3 -m pytest tools/new-agents/backend/tests/test_deepseek_v4_smoke_evidence.py -q
```

Expected: FAIL because `deepseek_v4_smoke_evidence` does not exist.

## Task 2: GREEN - 实现 local deterministic evidence gate

- [x] **Step 1: Create `deepseek_v4_smoke_evidence.py`**

Implement:

- `EvidenceStatus = Literal["passed", "failed", "skipped"]`
- `EvidenceResult`
- fake stream client
- `run_local_deepseek_v4_evidence()`
- CLI `main()`

The local gate must call the shared raw JSON runtime path with model `deepseek-v4-flash`, base URL `https://api.deepseek.com`, and a valid `artifact_data` fixture.

- [x] **Step 2: Reuse runtime helpers**

If tests need direct access to request-building evidence, expose minimal helper data from `agent_runtime.py` without changing runtime behavior. Do not create DeepSeek-only runtime branches.

- [x] **Step 3: Run GREEN**

Run:

```bash
python3 -m pytest tools/new-agents/backend/tests/test_deepseek_v4_smoke_evidence.py -q
```

Expected: PASS.

## Task 3: Optional real smoke skip/pass semantics

- [x] **Step 1: Add env-gated real smoke**

Implement `run_optional_real_deepseek_v4_smoke(env=os.environ)`:

- If required env vars are missing, return `skipped` with names.
- If present, call real runtime path.
- Never return passed without an actual runtime result.

- [x] **Step 2: Test skip behavior**

Run:

```bash
python3 -m pytest tools/new-agents/backend/tests/test_deepseek_v4_smoke_evidence.py::test_optional_real_smoke_skips_without_credentials -q
```

Expected: PASS.

## Task 4: 文档、验证和提交

- [x] **Step 1: Update todo**

Update DeepSeek V4 todo:

- Record evidence gate completed.
- Record command.
- Keep real smoke as optional when credentials/network are available.

Update refactor README current entry.

- [x] **Step 2: Run verification**

Run:

```bash
python3 -m pytest \
  tools/new-agents/backend/tests/test_deepseek_v4_smoke_evidence.py \
  tools/new-agents/backend/tests/test_agent_runtime.py \
  tools/new-agents/backend/tests/test_agent_contracts.py \
  -q
python3 -m py_compile tools/new-agents/backend/agent_runtime.py tools/new-agents/backend/deepseek_v4_smoke_evidence.py
git diff --check
```

Expected: all commands exit 0.

- [x] **Step 3: Commit**

Run:

```bash
git status --short
git add docs/superpowers/specs/2026-06-23-deepseek-v4-evidence-goal-mainline-design.md \
  docs/superpowers/plans/2026-06-23-deepseek-v4-evidence-goal-mainline.md \
  docs/todos/refactor/README.md \
  docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md \
  tools/new-agents/backend/agent_runtime.py \
  tools/new-agents/backend/deepseek_v4_smoke_evidence.py \
  tools/new-agents/backend/tests/test_deepseek_v4_smoke_evidence.py
git commit -m "feat(new-agents): 增加 DeepSeek V4 证据门禁"
```

Expected: focused commit on isolated worktree.

## Plan Self-Review

- Spec coverage: 覆盖 local deterministic evidence、optional real smoke skip、request params、artifact_data renderer、contract、todo 记录。
- Placeholder scan: no placeholder terms.
- Type consistency: `EvidenceStatus` uses `passed` / `failed` / `skipped`; function names match tests and spec.
- Superpowers brainstorming: spec 已按 playbook 覆盖 Explore Project Context、Visual Companion Decision、Clarifying Questions、Approaches 和 Presented Design。
