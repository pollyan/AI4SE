# New Agents Config Unification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make online New Agents frontend workflow listing, slug mapping, and structured-runtime eligibility derive from the shared `WORKFLOWS` runtime definitions while preserving behavior.

**Architecture:** `WORKFLOWS` becomes the frontend source for online workflow slug and listing metadata. Dev/plan cards stay in a separate non-runtime list. Backend contracts remain unchanged and continue to be verified by sync tests.

**Tech Stack:** React, TypeScript, Vitest, Flask/PydanticAI backend contract tests.

---

### Task 1: Frontend Config Tests

**Files:**
- Modify: `tools/new-agents/frontend/src/core/config/__tests__/workflows.test.ts`

- [ ] **Step 1: Write failing slug derivation tests**

Add assertions that each workflow's slug is available through `WORKFLOW_SLUGS`, reversible through `SLUG_TO_WORKFLOW`, and non-empty.

- [ ] **Step 2: Write failing online listing derivation tests**

Add assertions that every online workflow card returned by `getAgentWorkflows()` matches its `WORKFLOWS` source for slug, agent ownership, link, listing text, and icon.

- [ ] **Step 3: Run focused test and confirm RED**

Run: `cd tools/new-agents/frontend && npm run test -- --run src/core/config/__tests__/workflows.test.ts`

Expected: tests fail because `WorkflowDef` does not yet expose `slug` or `listing`.

### Task 2: Workflow Metadata Source

**Files:**
- Modify: `tools/new-agents/frontend/src/core/types.ts`
- Modify: `tools/new-agents/frontend/src/core/workflows.ts`
- Modify: `tools/new-agents/frontend/src/core/config/agentWorkflows.ts`

- [ ] **Step 1: Add workflow listing types**

Extend `WorkflowDef` with `slug` and `listing` fields. `listing` contains `name`, `description`, and `icon`.

- [ ] **Step 2: Move existing online card metadata into `WORKFLOWS`**

For each online workflow, add the current slug and exact current card name, description, and icon.

- [ ] **Step 3: Derive slug maps from `WORKFLOWS`**

Export `WORKFLOW_SLUGS` and `SLUG_TO_WORKFLOW` from `core/workflows.ts`; remove the hardcoded slug table from `core/types.ts`.

- [ ] **Step 4: Derive online agent cards**

Build online `AgentWorkflowConfig` entries from `Object.values(WORKFLOWS)`, preserving the exact current `id`, `agentId`, `status`, `name`, `description`, `icon`, and `link` values.

- [ ] **Step 5: Keep non-runtime cards explicit**

Keep dev/plan cards in a separate constant and combine them with the derived online cards before filtering by agent id.

- [ ] **Step 6: Run focused test and confirm GREEN**

Run: `cd tools/new-agents/frontend && npm run test -- --run src/core/config/__tests__/workflows.test.ts`

Expected: all tests in the file pass.

### Task 3: Runtime List Removal

**Files:**
- Modify: `tools/new-agents/frontend/src/core/llm.ts`
- Test: `tools/new-agents/frontend/src/core/config/__tests__/workflows.test.ts`

- [ ] **Step 1: Remove `STRUCTURED_RUNTIME_WORKFLOWS`**

Update `getStructuredRuntimeStageId()` to rely on `WORKFLOWS[workflow]` stage lookup, so any `WorkflowType` in `WORKFLOWS` is automatically structured-runtime eligible.

- [ ] **Step 2: Confirm no hardcoded structured-runtime workflow list remains**

Run: `rg -n "STRUCTURED_RUNTIME_WORKFLOWS|当前工作流未接入结构化 Agent Runtime" tools/new-agents/frontend/src`

Expected: no matches.

- [ ] **Step 3: Run focused streaming/core tests**

Run: `cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/llm.test.ts src/services/__tests__/chatService.test.ts`

Expected: all tests pass.

### Task 4: Verification

**Files:**
- No production files beyond Tasks 2 and 3.

- [ ] **Step 1: Run frontend config and prompt tests**

Run: `cd tools/new-agents/frontend && npm run test -- --run src/core/config/__tests__/workflows.test.ts src/core/prompts/__tests__/buildSystemPrompt.test.ts src/__tests__/testHygiene.test.ts`

Expected: all tests pass.

- [ ] **Step 2: Run frontend TypeScript check**

Run: `cd tools/new-agents/frontend && npm run lint`

Expected: TypeScript exits 0.

- [ ] **Step 3: Run backend contract sync test**

Run: `/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest tools/new-agents/backend/tests/test_workflow_contract_sync.py -q`

Expected: `2 passed`.
