# New Agents Artifact Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立 New Agents 在线 workflow artifact 专业审计基线。

**Architecture:** 新增独立审计文档，引用现有 `WORKFLOWS` 与后端 artifact heading contract，不改运行时代码。Todo 记录只写进展和后续候选。

**Tech Stack:** Markdown documentation, existing New Agents frontend/backend contract files.

---

### Task 1: 编写审计文档

**Files:**
- Create: `docs/plans/2026-06-19-new-agents-artifact-audit.md`

- [x] **Step 1: 列出事实源**

记录审计基于 `tools/new-agents/frontend/src/core/workflows.ts`、`tools/new-agents/backend/agent_contracts.py` 和 `docs/todos/new-agents-evolution.md`。

- [x] **Step 2: 覆盖五个 workflow**

为 `TEST_DESIGN`、`REQ_REVIEW`、`INCIDENT_REVIEW`、`IDEA_BRAINSTORM`、`VALUE_DISCOVERY` 各写一节，包含专业目标、当前 contract 摘要、主要差距和推荐后续切片。

### Task 2: 更新 todo

**Files:**
- Modify: `docs/todos/new-agents-evolution.md`

- [x] **Step 1: 记录 P0 #2 审计基线**

在 P0 #2 下记录审计文档路径和本轮结论。

### Task 3: 文档验证

**Files:**
- Check: `docs/plans/2026-06-19-new-agents-artifact-audit.md`
- Check: `docs/todos/new-agents-evolution.md`

- [x] **Step 1: 占位符扫描**

Run: `rg -n 'TODO|TBD' docs/plans/2026-06-19-new-agents-artifact-audit.md docs/todos/new-agents-evolution.md`

Expected: no unexplained placeholders.

- [x] **Step 2: 格式检查**

Run: `git diff --check -- docs/plans/2026-06-19-new-agents-artifact-audit.md docs/todos/new-agents-evolution.md docs/superpowers/specs/2026-06-19-new-agents-artifact-audit-design.md docs/superpowers/plans/2026-06-19-new-agents-artifact-audit.md`

Expected: no output, exit 0.
