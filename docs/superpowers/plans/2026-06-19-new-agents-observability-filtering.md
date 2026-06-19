# New Agents Observability Filtering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add workflow/stage filtering to runtime observability.

**Architecture:** Extend the existing observability endpoint and service instead of adding routes. Reuse `WORKFLOW_STAGES` validation on the backend and `WORKFLOWS` metadata on the frontend.

**Tech Stack:** Flask, SQLAlchemy, React, TypeScript, Vitest, Pytest.

---

### Task 1: Backend Filter Contract

**Files:**
- Modify: `tools/new-agents/backend/tests/test_agent_endpoint.py`
- Modify: `tools/new-agents/backend/routes.py`
- Modify: `tools/new-agents/backend/run_persistence.py`

- [ ] **Step 1: Write backend failing tests**

Add tests for `GET /api/agent/observability?workflowId=TEST_DESIGN&stageId=CLARIFY` returning only matching metrics and `stageId` without `workflowId` returning 400.

- [ ] **Step 2: Run tests to verify failure**

Run: `cd tools/new-agents/backend && python3 -m pytest tests/test_agent_endpoint.py::test_agent_observability_endpoint_filters_by_workflow_and_stage tests/test_agent_endpoint.py::test_agent_observability_endpoint_rejects_stage_without_workflow -q`

- [ ] **Step 3: Implement backend filters**

Validate workflow/stage arguments, filter the metric query, and pass the parameters from the route.

### Task 2: Frontend Service And UI

**Files:**
- Modify: `tools/new-agents/frontend/src/services/__tests__/observabilityService.test.ts`
- Modify: `tools/new-agents/frontend/src/services/observabilityService.ts`
- Modify: `tools/new-agents/frontend/src/components/__tests__/Header.test.tsx`
- Modify: `tools/new-agents/frontend/src/components/Header.tsx`

- [ ] **Step 1: Write service and Header failing tests**

Assert the service serializes `workflowId` and `stageId`. Assert the modal calls `fetchObservabilitySummary` with selected filters after `应用筛选`.

- [ ] **Step 2: Run frontend tests to verify failure**

Run: `cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/observabilityService.test.ts src/components/__tests__/Header.test.tsx`

- [ ] **Step 3: Implement service and UI**

Add filter state, workflow/stage selects, apply button, and reload logic.

### Task 3: Docs And Verification

**Files:**
- Modify: `docs/todos/new-agents-evolution.md`
- Modify: `docs/api-contracts.md`

- [ ] **Step 1: Update docs**

Record workflow/stage filtering and update the observability endpoint contract.

- [ ] **Step 2: Verify**

Run:

```bash
cd tools/new-agents/backend && python3 -m pytest tests/test_agent_endpoint.py::test_agent_observability_endpoint_returns_runtime_turn_summary tests/test_agent_endpoint.py::test_agent_observability_endpoint_filters_by_workflow_and_stage tests/test_agent_endpoint.py::test_agent_observability_endpoint_rejects_stage_without_workflow -q
cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/observabilityService.test.ts src/components/__tests__/Header.test.tsx
cd tools/new-agents/frontend && npm run lint
git diff --check
```
