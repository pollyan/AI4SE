# New Agents Shared Workflow Manifest Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增 New Agents 在线 workflow 的共享 manifest 首轮数据源，降低前后端 workflow 元数据漂移风险。

**Architecture:** `tools/new-agents/workflow_manifest.json` 承载 workflow id、agentId、slug、展示文案、stage id/name 和 onboarding；前端 `WORKFLOWS` 从 manifest 读取基础元数据并继续挂接 TS prompt/template；后端测试读取同一 JSON 校验 stage 顺序与 artifact contract 覆盖。

**Tech Stack:** TypeScript/Vite JSON import, Python pytest, JSON manifest.

---

### Task 1: 后端 manifest sync RED

**Files:**
- Modify: `tools/new-agents/backend/tests/test_workflow_contract_sync.py`

- [x] **Step 1: 写失败测试**

新增读取 `tools/new-agents/workflow_manifest.json` 的 helper，并断言 manifest workflow/stage 与后端 `WORKFLOW_STAGES`、`REQUIRED_ARTIFACT_HEADINGS` 同步。

- [x] **Step 2: 运行测试确认失败**

Run: `cd tools/new-agents/backend && python3 -m pytest tests/test_workflow_contract_sync.py -q`

Expected: FAIL，因为 `tools/new-agents/workflow_manifest.json` 尚不存在。

### Task 2: 新增共享 manifest 并接入前端

**Files:**
- Create: `tools/new-agents/workflow_manifest.json`
- Modify: `tools/new-agents/frontend/tsconfig.json`
- Modify: `tools/new-agents/frontend/src/core/workflows.ts`

- [x] **Step 1: 新增 workflow_manifest.json**

覆盖 `TEST_DESIGN`、`REQ_REVIEW`、`INCIDENT_REVIEW`、`IDEA_BRAINSTORM`、`VALUE_DISCOVERY` 的基础元数据、stage id/name 和 onboarding。

- [x] **Step 2: 允许前端导入 JSON**

在 `tsconfig.json` 增加 `resolveJsonModule: true`。

- [x] **Step 3: 前端 WORKFLOWS 从 manifest 组装**

保留现有 prompt/template imports，新增 stage prompt/template 映射，使用 manifest 元数据生成 `WORKFLOWS`。

### Task 3: 验证和记录

**Files:**
- Modify: `docs/todos/new-agents-evolution.md`
- Modify: `docs/superpowers/plans/2026-06-19-new-agents-shared-workflow-manifest.md`

- [x] **Step 1: 运行后端同步测试**

Run: `cd tools/new-agents/backend && python3 -m pytest tests/test_workflow_contract_sync.py -q`

Expected: PASS。

- [x] **Step 2: 运行前端 workflow 配置测试**

Run: `cd tools/new-agents/frontend && npm run test -- --run src/core/config/__tests__/workflows.test.ts`

Expected: PASS。

- [x] **Step 3: 运行 TypeScript 检查**

Run: `cd tools/new-agents/frontend && npm run lint`

Expected: PASS。

- [x] **Step 4: 更新 todo 进展记录**

在 P1 #4 下记录共享 manifest 首轮落地、范围和验证命令。

- [x] **Step 5: 格式检查**

Run: `git diff --check -- tools/new-agents/workflow_manifest.json tools/new-agents/frontend/tsconfig.json tools/new-agents/frontend/src/core/workflows.ts tools/new-agents/backend/tests/test_workflow_contract_sync.py docs/todos/new-agents-evolution.md docs/superpowers/specs/2026-06-19-new-agents-shared-workflow-manifest-design.md docs/superpowers/plans/2026-06-19-new-agents-shared-workflow-manifest.md`

Expected: no output, exit 0.
