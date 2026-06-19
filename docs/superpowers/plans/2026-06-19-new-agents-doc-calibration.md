# New Agents Documentation Calibration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 校准 New Agents 稳定文档，使其反映当前 typed Agent Runtime、共享 workflow manifest、artifact/Mermaid contract、LLM judge 和 ChatPane Markdown 事实。

**Architecture:** 只更新稳定文档和 todo 记录，不修改运行时代码；用关键词检查和 diff check 作为文档验收。

**Tech Stack:** Markdown documentation, ripgrep, git diff check.

---

### Task 1: 更新稳定文档

**Files:**
- Modify: `AGENTS.md`
- Modify: `docs/ARCHITECTURE.md`
- Modify: `docs/api-contracts.md`
- Modify: `docs/TESTING.md`
- Modify: `docs/component-inventory.md`

- [x] **Step 1: 更新 New Agents 配置原则**

在 `AGENTS.md` 和 `docs/ARCHITECTURE.md` 中加入共享 manifest、prompt/template、后端 contract、Mermaid contract 和 judge 证据的同步要求。

- [x] **Step 2: 更新 API/SSE 示例**

在 `docs/api-contracts.md` 中展示 `artifact_update.type=replace` 的主路径示例，并说明 `none` 只用于无 artifact 更新场景。

- [x] **Step 3: 更新测试和组件清单**

在 `docs/TESTING.md` 和 `docs/component-inventory.md` 中加入 manifest sync、Mermaid contract、LLM judge trace/verdict 和 ChatPane Markdown 渲染职责。

### Task 2: 更新 todo 和验证

**Files:**
- Modify: `docs/todos/new-agents-evolution.md`
- Modify: `docs/superpowers/plans/2026-06-19-new-agents-doc-calibration.md`

- [x] **Step 1: 记录 P1 #9 首轮完成情况**

记录本轮校准过的文件、覆盖的代码事实和未进入本轮的文档范围。

- [x] **Step 2: 运行文档关键词检查**

Run: `rg -n "workflow_manifest|REQUIRED_ARTIFACT_MERMAID_DIAGRAMS|WorkflowRunResult|dimension_scores|ChatPane|artifact_update.type=replace" AGENTS.md docs/ARCHITECTURE.md docs/api-contracts.md docs/TESTING.md docs/component-inventory.md docs/todos/new-agents-evolution.md`

Expected: key terms appear in the calibrated docs.

- [x] **Step 3: 检查旧误导描述**

Run: `rg -n "5 个工作流定义（阶段、prompt 模板）" docs/component-inventory.md`

Expected: no output.

- [x] **Step 4: 格式检查**

Run: `git diff --check -- AGENTS.md docs/ARCHITECTURE.md docs/api-contracts.md docs/TESTING.md docs/component-inventory.md docs/todos/new-agents-evolution.md docs/superpowers/specs/2026-06-19-new-agents-doc-calibration-design.md docs/superpowers/plans/2026-06-19-new-agents-doc-calibration.md`

Expected: no output, exit 0.
