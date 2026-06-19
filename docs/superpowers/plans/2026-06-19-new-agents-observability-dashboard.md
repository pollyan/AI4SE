# New Agents Observability Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a read-only frontend runtime statistics view for the existing New Agents observability API.

**Architecture:** Keep backend unchanged. Add a focused frontend service that parses `GET /api/agent/observability`, then wire a Header modal that displays totals, stage/provider aggregation, and recent turn details.

**Tech Stack:** React, TypeScript, Vitest, Zustand store, existing Flask observability endpoint.

---

### Task 1: Observability Service

**Files:**
- Create: `tools/new-agents/frontend/src/services/observabilityService.ts`
- Create: `tools/new-agents/frontend/src/services/__tests__/observabilityService.test.ts`
- Modify: `tools/new-agents/frontend/src/core/types.ts`

- [ ] **Step 1: Write failing service tests**

Cover successful fetch, URL limit query, and malformed payload failure.

- [ ] **Step 2: Run service test red**

Run: `cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/observabilityService.test.ts`

Expected: FAIL because `observabilityService` does not exist.

- [ ] **Step 3: Add types and parser**

Define `ObservabilitySummary`, `ObservabilityStageSummary`, `ObservabilityProviderSummary`, and `ObservabilityTurn` in `core/types.ts`. Implement strict parser in `observabilityService.ts`.

- [ ] **Step 4: Run service test green**

Run: `cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/observabilityService.test.ts`

Expected: PASS.

### Task 2: Header Modal

**Files:**
- Modify: `tools/new-agents/frontend/src/components/Header.tsx`
- Modify: `tools/new-agents/frontend/src/components/__tests__/Header.test.tsx`

- [ ] **Step 1: Write failing Header test**

Mock `fetchObservabilitySummary`, click “运行统计”, and assert totals, stage, provider, and recent turn content render.

- [ ] **Step 2: Run Header test red**

Run: `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/Header.test.tsx`

Expected: FAIL because the button/modal does not exist.

- [ ] **Step 3: Wire Header UI**

Add a button with a compact chart icon, modal state, loading/error states, and read-only summary sections.

- [ ] **Step 4: Run Header test green**

Run: `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/Header.test.tsx`

Expected: PASS.

### Task 3: Documentation and Verification

**Files:**
- Modify: `docs/todos/new-agents-evolution.md`
- Modify: `docs/component-inventory.md`
- Modify: `docs/api-contracts.md`

- [ ] **Step 1: Update docs**

Record the frontend observability view, service module, remaining gaps, and verification commands.

- [ ] **Step 2: Run regression verification**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/observabilityService.test.ts src/components/__tests__/Header.test.tsx src/pages/__tests__/Workspace.test.tsx src/__tests__/store.test.ts
cd tools/new-agents/frontend && npm run lint
cd tools/new-agents/backend && python3 -m pytest tests/test_agent_endpoint.py::test_agent_observability_endpoint_returns_runtime_turn_summary -q
git diff --check
```

Expected: all commands pass.
