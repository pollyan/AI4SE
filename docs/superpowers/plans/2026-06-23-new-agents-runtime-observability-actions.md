# New Agents Runtime Observability Actions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add deterministic diagnosis and action suggestions to the existing New Agents runtime observability summary and modal.

**Architecture:** Extend the existing `/api/agent/observability` summary with derived `diagnostics` entries from persisted metrics and config issues. Parse the new contract in the frontend service and render it inside the existing Header runtime statistics modal without changing Agent Runtime, typed SSE, workflow manifest, artifact contracts, or persistence tables.

**Tech Stack:** Python 3.11, Flask, SQLAlchemy, pytest, React, TypeScript, Vitest, Testing Library.

---

### Task 1: Backend Diagnostics Contract

**Files:**
- Modify: `tools/new-agents/backend/run_persistence.py`
- Modify: `tools/new-agents/backend/tests/test_agent_endpoint.py`

- [ ] **Step 1: Write the failing endpoint test**

Add assertions to `test_agent_runs_stream_records_default_llm_missing_observability_issue`:

```python
diagnostics = observability_response.json["diagnostics"]
assert diagnostics == [
    {
        "id": "provider-issue-default-llm-config-missing",
        "severity": "warning",
        "title": "模型/供应商异常集中",
        "detail": "默认模型配置 最近出现 1 次 DEFAULT_LLM_CONFIG_MISSING。",
        "action": "打开模型设置，检查默认模型、API Key、Base URL、额度和网络连通性。",
        "workflowId": None,
        "stageId": None,
        "provider": "默认模型配置",
        "metric": "providerIssueCount",
        "count": 1,
    },
    {
        "id": "stage-success-TEST_DESIGN-CLARIFY",
        "severity": "warning",
        "title": "阶段成功率偏低",
        "detail": "TEST_DESIGN / CLARIFY 成功率 0.0%，失败 1/1 轮。",
        "action": "优先复查该阶段输入完整性、stage prompt、artifact contract 和最近失败错误码。",
        "workflowId": "TEST_DESIGN",
        "stageId": "CLARIFY",
        "provider": None,
        "metric": "successRate",
        "count": 1,
    },
]
```

Add a second test or extend an existing runtime failure test with persisted turn metrics where `contractRetryCount` is greater than zero, asserting a `contract-retry-...` diagnostic appears before low success-rate diagnostics.

- [ ] **Step 2: Run the backend test to verify RED**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_endpoint.py::test_agent_runs_stream_records_default_llm_missing_observability_issue -q
```

Expected: FAIL with `KeyError: 'diagnostics'`.

- [ ] **Step 3: Implement minimal backend diagnostics**

In `get_runtime_observability_summary()`, compute `by_stage` and `by_provider` local variables, return them, and add:

```python
"diagnostics": _build_observability_diagnostics(
    by_stage,
    by_provider,
    config_issues,
),
```

Add helper functions in the same file:

```python
def _build_observability_diagnostics(
    by_stage: list[dict],
    by_provider: list[dict],
    config_issues: list[AgentRuntimeConfigIssue],
) -> list[dict]:
    diagnostics: list[dict] = []
    diagnostics.extend(_contract_retry_diagnostics(by_stage))
    diagnostics.extend(_provider_issue_diagnostics(by_provider, config_issues))
    diagnostics.extend(_low_success_stage_diagnostics(by_stage))
    return diagnostics
```

Implement deterministic sorting and ID-safe code normalization with lowercase alphanumeric/hyphen output.

- [ ] **Step 4: Run backend endpoint tests**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_endpoint.py::test_agent_runs_stream_records_default_llm_missing_observability_issue -q
```

Expected: PASS.

### Task 2: Frontend Parsing Contract

**Files:**
- Modify: `tools/new-agents/frontend/src/core/types.ts`
- Modify: `tools/new-agents/frontend/src/services/observabilityService.ts`
- Modify: `tools/new-agents/frontend/src/services/__tests__/observabilityService.test.ts`

- [ ] **Step 1: Write the failing service tests**

Extend `OBSERVABILITY_PAYLOAD` with:

```typescript
diagnostics: [
  {
    id: 'contract-retry-TEST_DESIGN-CLARIFY',
    severity: 'warning',
    title: '结构化产物重试集中',
    detail: 'TEST_DESIGN / CLARIFY 最近触发 2 次 contract retry。',
    action: '优先检查该阶段 artifact_data schema、required headings、visual contract 与 prompt 示例是否一致。',
    workflowId: 'TEST_DESIGN',
    stageId: 'CLARIFY',
    provider: null,
    metric: 'contractRetryCount',
    count: 2,
  },
],
```

Assert:

```typescript
expect(summary.diagnostics[0].metric).toBe('contractRetryCount');
expect(summary.diagnostics[0].workflowId).toBe('TEST_DESIGN');
```

Add malformed payload test where `diagnostics[0].count` is `'2'`, expecting `Invalid observability summary response`.

- [ ] **Step 2: Run service tests to verify RED**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/observabilityService.test.ts
```

Expected: FAIL because `diagnostics` is not parsed.

- [ ] **Step 3: Implement parsing**

Add `ObservabilityDiagnostic` to `types.ts`, add `diagnostics: ObservabilityDiagnostic[]` to `ObservabilitySummary`, and add `parseDiagnostic()` in `observabilityService.ts` using existing `parseString`, `parseNullableString`, `parseInteger`, and `parseWorkflowType`.

- [ ] **Step 4: Run service tests**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/observabilityService.test.ts
```

Expected: PASS.

### Task 3: Header Diagnosis Rendering

**Files:**
- Modify: `tools/new-agents/frontend/src/components/Header.tsx`
- Modify: `tools/new-agents/frontend/src/components/__tests__/Header.test.tsx`

- [ ] **Step 1: Write the failing Header test**

Extend the mocked observability summary with a diagnostic:

```typescript
diagnostics: [
  {
    id: 'contract-retry-TEST_DESIGN-CLARIFY',
    severity: 'warning',
    title: '结构化产物重试集中',
    detail: 'TEST_DESIGN / CLARIFY 最近触发 2 次 contract retry。',
    action: '优先检查该阶段 artifact_data schema、required headings、visual contract 与 prompt 示例是否一致。',
    workflowId: 'TEST_DESIGN',
    stageId: 'CLARIFY',
    provider: null,
    metric: 'contractRetryCount',
    count: 2,
  },
],
```

Add test assertions:

```typescript
expect(await screen.findByText('诊断建议')).toBeTruthy();
expect(screen.getByText('结构化产物重试集中')).toBeTruthy();
expect(screen.getByText(/artifact_data schema/)).toBeTruthy();
```

- [ ] **Step 2: Run Header test to verify RED**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/Header.test.tsx -t "opens runtime observability summary"
```

Expected: FAIL because Header does not render diagnostics yet.

- [ ] **Step 3: Render diagnostics**

In `Header.tsx`, after `运行告警` and before metric cards, render `observabilitySummary.diagnostics` when non-empty. Each item should show title, detail, action, and optional workflow/stage/provider tags using existing compact modal styling.

- [ ] **Step 4: Run Header tests**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/Header.test.tsx
```

Expected: PASS.

### Task 4: Todo Record And Verification

**Files:**
- Modify: `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md`
- Modify: `docs/superpowers/specs/2026-06-23-new-agents-runtime-observability-actions-design.md`
- Modify: `docs/superpowers/plans/2026-06-23-new-agents-runtime-observability-actions.md`

- [ ] **Step 1: Update todo progress**

Mark E09 as consumed in the active diagnostic todo and add a short note that runtime observability now surfaces deterministic diagnostics and action suggestions for contract retry, provider issues, and low stage success rate.

- [ ] **Step 2: Run focused verification**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_endpoint.py -q
cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/observabilityService.test.ts src/core/__tests__/observabilityAlerts.test.ts src/components/__tests__/Header.test.tsx
git diff --check
```

Expected: all commands pass.

- [ ] **Step 3: Commit**

Run:

```bash
git add docs/superpowers/specs/2026-06-23-new-agents-runtime-observability-actions-design.md docs/superpowers/plans/2026-06-23-new-agents-runtime-observability-actions.md docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md tools/new-agents/backend/run_persistence.py tools/new-agents/backend/tests/test_agent_endpoint.py tools/new-agents/frontend/src/core/types.ts tools/new-agents/frontend/src/services/observabilityService.ts tools/new-agents/frontend/src/services/__tests__/observabilityService.test.ts tools/new-agents/frontend/src/components/Header.tsx tools/new-agents/frontend/src/components/__tests__/Header.test.tsx
git commit -m "feat: 产品化运行统计诊断建议"
```

Expected: focused commit created on `codex/runtime-observability-actions`.
