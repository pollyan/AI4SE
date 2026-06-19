# New Agents Observability Alerts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add deterministic frontend-derived alerts to the existing runtime statistics modal.

**Architecture:** Create a pure alert builder in `src/core/observabilityAlerts.ts` and render its output in `Header.tsx`. Keep the backend observability API unchanged.

**Tech Stack:** React, TypeScript, Vitest, Testing Library, Markdown docs.

---

### Task 1: Alert Rule Unit Tests

**Files:**
- Create: `tools/new-agents/frontend/src/core/observabilityAlerts.ts`
- Create: `tools/new-agents/frontend/src/core/__tests__/observabilityAlerts.test.ts`

- [x] **Step 1: Write the failing helper tests**

Create tests that import `buildObservabilityAlerts` and assert:

```typescript
expect(alerts.map(alert => alert.title)).toEqual([
  '检测到失败运行',
  '阶段成功率偏低',
  '供应商成功率偏低',
]);
```

Also add a healthy summary test expecting an empty array.

- [x] **Step 2: Run tests to verify RED**

Run: `cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/observabilityAlerts.test.ts`

Expected: FAIL because `observabilityAlerts.ts` does not exist yet.

- [x] **Step 3: Implement `buildObservabilityAlerts`**

Return at most one total failure alert, one lowest-success stage alert, and one lowest-success provider alert. Use `failedTurns > 0` and `successRate < 80` for stage/provider alerts.

- [x] **Step 4: Run helper tests to verify GREEN**

Run: `cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/observabilityAlerts.test.ts`

Expected: all helper tests pass.

### Task 2: Header Alert Rendering

**Files:**
- Modify: `tools/new-agents/frontend/src/components/Header.tsx`
- Modify: `tools/new-agents/frontend/src/components/__tests__/Header.test.tsx`

- [x] **Step 1: Write the failing Header test**

Add a test that opens `运行统计` and expects `运行告警`, `检测到失败运行`, `阶段成功率偏低`, and `供应商成功率偏低` to be visible.

- [x] **Step 2: Run Header test to verify RED**

Run: `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/Header.test.tsx -t "shows runtime observability alerts"`

Expected: FAIL because Header does not render derived alerts yet.

- [x] **Step 3: Render alerts in Header**

Import `buildObservabilityAlerts`, derive alerts from `observabilitySummary`, and render a compact `运行告警` section above the metric cards when the array is non-empty.

- [x] **Step 4: Run Header tests**

Run: `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/Header.test.tsx`

Expected: all Header tests pass.

### Task 3: Todo Record And Verification

**Files:**
- Modify: `docs/todos/new-agents-evolution.md`
- Modify: `docs/superpowers/plans/2026-06-19-new-agents-observability-alerts.md`

- [x] **Step 1: Update progress**

Record that the Header runtime statistics modal now derives lightweight alerts from totals, stage summaries, and provider summaries without changing the backend API.

- [x] **Step 2: Run focused verification**

Run: `cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/observabilityAlerts.test.ts src/services/__tests__/observabilityService.test.ts src/components/__tests__/Header.test.tsx`

Expected: alert helper, observability service, and Header tests pass.

- [x] **Step 3: Run lint and whitespace check**

Run: `cd tools/new-agents/frontend && npm run lint`

Expected: TypeScript check passes.

Run: `git diff --check`

Expected: no whitespace errors.
