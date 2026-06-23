# 历史会话复用中心 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 让 New Agents 历史中心支持质量筛选、artifact 预览、继续原 run 和复制为新 run。

**Architecture:** 在现有 run persistence/list/snapshot 基础上扩展共享 run API，不新增 runtime、SSE path、agent-specific store 或 renderer。后端负责质量状态和 clone 语义，前端 service 严格解析，Header 历史弹窗负责展示与操作。

**Tech Stack:** Flask + SQLAlchemy + pytest；React 19 + TypeScript + Zustand + Vitest。

---

### Task 1: Backend Run List Contract

**Files:**
- Modify: `tools/new-agents/backend/run_persistence.py`
- Modify: `tools/new-agents/backend/routes.py`
- Test: `tools/new-agents/backend/tests/test_run_persistence.py`
- Test: `tools/new-agents/backend/tests/test_agent_endpoint.py`

- [x] Step 1: Write RED tests for `qualityStatus`, `currentArtifact.preview`, and `qualityStatus` filtering.
- [x] Step 2: Run backend tests and confirm failure is missing fields or unsupported filter.
- [x] Step 3: Implement `quality_status` derivation and current artifact preview in run list item.
- [x] Step 4: Add route parsing for `qualityStatus` and invalid status rejection.
- [x] Step 5: Re-run backend tests and confirm pass.

### Task 2: Backend Clone Contract

**Files:**
- Modify: `tools/new-agents/backend/run_persistence.py`
- Modify: `tools/new-agents/backend/routes.py`
- Test: `tools/new-agents/backend/tests/test_run_persistence.py`
- Test: `tools/new-agents/backend/tests/test_agent_endpoint.py`

- [x] Step 1: Write RED tests for clone creating an independent run with copied messages, artifacts, and context summaries.
- [x] Step 2: Run backend tests and confirm clone endpoint/function is missing.
- [x] Step 3: Implement `clone_agent_run(run_id)` in persistence and `POST /agent/runs/<run_id>/clone`.
- [x] Step 4: Ensure clone does not copy comments, locks, audit events, or mutate source run.
- [x] Step 5: Re-run backend tests and confirm pass.

### Task 3: Frontend Service Contract

**Files:**
- Modify: `tools/new-agents/frontend/src/core/types.ts`
- Modify: `tools/new-agents/frontend/src/services/runSnapshotService.ts`
- Test: `tools/new-agents/frontend/src/services/__tests__/runSnapshotService.test.ts`

- [x] Step 1: Write RED tests for new run list fields, `qualityStatus` query param, malformed payload rejection, and `cloneRun`.
- [x] Step 2: Run service tests and confirm failure.
- [x] Step 3: Extend `AgentRunListItem`, strict parser, fetch options, and `cloneRun`.
- [x] Step 4: Re-run service tests and confirm pass.

### Task 4: Header History UI

**Files:**
- Modify: `tools/new-agents/frontend/src/components/Header.tsx`
- Test: `tools/new-agents/frontend/src/components/__tests__/Header.test.tsx`

- [x] Step 1: Write RED tests for quality filter, artifact preview expansion, continue action, clone action, and clone error.
- [x] Step 2: Run Header tests and confirm failure.
- [x] Step 3: Add quality filter state, preview UI, continue / copy buttons, and clone navigation.
- [x] Step 4: Re-run Header tests and confirm pass.

### Task 5: Docs, Verification, Commit

**Files:**
- Modify: `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md`
- Modify: `docs/todos/refactor/README.md`

- [x] Step 1: Mark E06 as consumed with actual scope and verification.
- [x] Step 2: Run backend validation.
- [x] Step 3: Run frontend targeted tests.
- [x] Step 4: Run frontend lint.
- [x] Step 5: Run `git diff --check`.
- [x] Step 6: Stage and commit focused changes.
