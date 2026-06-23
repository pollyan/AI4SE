# DeepSeek V4 格式化输出主线完成闭环 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 建立 DeepSeek V4 artifact_data 格式化输出 readiness gate，并把已完成的结构化产物数据迁移从活动 todo 中收口。

**Architecture:** 复用共享 Agent Runtime、OpenAI-compatible JSON mode、Pydantic artifact_data schema、deterministic renderer、typed SSE 和现有 artifact contract。后端只新增集中 stage readiness 入口和测试门禁，不新增 DeepSeek 专属 runtime、API path、store 或 renderer。

**Tech Stack:** Python 3.11、Flask 后端、Pydantic、pytest、Markdown/Mermaid deterministic renderer。

---

### Task 1: Readiness Gate RED

**Files:**
- Create: `tools/new-agents/backend/tests/test_deepseek_v4_readiness.py`
- Read: `tools/new-agents/workflow_manifest.json`
- Read: `tools/new-agents/backend/agent_runtime.py`
- Read: `tools/new-agents/backend/artifact_data_renderers.py`

- [x] Step 1: Write a failing test that imports `get_artifact_data_ready_stages` from `agent_runtime` and compares it with all manifest stages.
- [x] Step 2: In the same test file, assert every manifest stage returns a structured output instruction containing `artifact_data` and not `artifact_update.markdown`.
- [x] Step 3: Add DeepSeek V4 capability assertions for `json_object_only`, `{"type": "json_object"}`, and thinking disabled settings.
- [x] Step 4: Run `python3 -m pytest tools/new-agents/backend/tests/test_deepseek_v4_readiness.py -q`; expected RED is an import failure for the missing readiness helper or a mismatch in readiness coverage.

### Task 2: Minimal Readiness Implementation

**Files:**
- Modify: `tools/new-agents/backend/agent_runtime.py`
- Modify: `tools/new-agents/backend/artifact_data_renderers.py` only if a renderer support helper is needed.

- [x] Step 1: Add a single source of truth for artifact_data-ready stages, using the current 17 online workflow/stage pairs.
- [x] Step 2: Implement `get_artifact_data_ready_stages() -> set[tuple[str, str]]`.
- [x] Step 3: Update `supports_artifact_data_rendering()` to use the shared set.
- [x] Step 4: Keep `build_structured_output_instruction()` behavior unchanged for supported stages and `TEXT_STRUCTURED_OUTPUT_INSTRUCTION` for unknown stages.
- [x] Step 5: Re-run `python3 -m pytest tools/new-agents/backend/tests/test_deepseek_v4_readiness.py -q`; expected GREEN.

### Task 3: Regression Verification

**Files:**
- Test: `tools/new-agents/backend/tests/test_agent_runtime.py`
- Test: `tools/new-agents/backend/tests/test_artifact_data_renderers.py`
- Test: `tools/new-agents/backend/tests/test_agent_contracts.py`

- [x] Step 1: Run `python3 -m pytest tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_agent_contracts.py -q`.
- [x] Step 2: If failures appear, fix only regressions caused by this readiness gate.
- [x] Step 3: Re-run the same command until it exits 0.

### Task 4: Todo Closure

**Files:**
- Modify or move: `docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md`
- Modify: `docs/todos/refactor/README.md`
- Optional create/update: `docs/todos/archive/2026-06-23-deepseek-v4-structured-artifact-data.md`

- [x] Step 1: Mark the DeepSeek V4 structured artifact data work as completed, including the readiness gate verification.
- [x] Step 2: If archiving, remove the active refactor todo copy and update `docs/todos/refactor/README.md` so it no longer lists DeepSeek V4 as active.
- [x] Step 3: Record that real DeepSeek V4 Flash smoke was not run because it requires explicit credentials, network and quota.

### Task 5: Final Checkpoint

**Files:**
- All changed files in this plan.

- [x] Step 1: Run `git diff --check`.
- [x] Step 2: Run `git status --short` and verify only this milestone's files changed.
- [x] Step 3: Stage only this milestone's files.
- [x] Step 4: Commit with `chore: 收口 DeepSeek V4 格式化输出`.
