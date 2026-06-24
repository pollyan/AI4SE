# Runtime Observability Actions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the existing New Agents runtime observability modal into an actionable diagnostic loop for failures, provider/config issues, and contract retries.

**Architecture:** Extend the existing `/api/agent/observability` response with deterministic `diagnostics` and `contractRetryReasons`, parse them through the current typed frontend service, and render them in the existing Header modal. No new API path, runtime branch, SSE event, persistence table, or agent-specific infrastructure.

**Tech Stack:** Flask, SQLAlchemy models already in use, pytest, React 19, TypeScript, Vitest, Testing Library.

---

## File Structure

- Modify: `tools/new-agents/backend/run_persistence.py`
  - Add deterministic diagnostic helper functions and include new fields in `get_runtime_observability_summary()`.
- Modify: `tools/new-agents/backend/tests/test_agent_endpoint.py`
  - Add RED assertions for diagnostics and contract retry reasons.
- Modify: `tools/new-agents/frontend/src/core/types.ts`
  - Add `ObservabilityDiagnostic` and `contractRetryReasons`.
- Modify: `tools/new-agents/frontend/src/services/observabilityService.ts`
  - Strictly parse new fields.
- Modify: `tools/new-agents/frontend/src/services/__tests__/observabilityService.test.ts`
  - Add RED tests for parsing and malformed diagnostics.
- Modify: `tools/new-agents/frontend/src/core/__tests__/observabilityAlerts.test.ts`
  - Synchronize existing observability fixtures with the extended `ObservabilitySummary` contract.
- Modify: `tools/new-agents/frontend/src/components/Header.tsx`
  - Render diagnostics and contract retry reason badges in the existing observability modal.
- Modify: `tools/new-agents/frontend/src/components/__tests__/Header.test.tsx`
  - Add RED UI test.
- Modify: `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md`
  - Mark E09 consumed with validation evidence.
- Modify: `docs/todos/refactor/README.md`
  - Record this milestone in the active todo pool.

## Task 1: Backend Observability Diagnostics RED/GREEN

**Files:**
- Modify: `tools/new-agents/backend/tests/test_agent_endpoint.py`
- Modify: `tools/new-agents/backend/run_persistence.py`

- [x] **Step 1: Write failing backend test**

Extend `test_agent_observability_endpoint_groups_provider_issue_codes` with assertions:

```python
    assert response.json["contractRetryReasons"] == {
        "STRUCTURED_OUTPUT_CONTRACT_RETRY": 3,
    }
    diagnostic_titles = [item["title"] for item in response.json["diagnostics"]]
    assert "模型/供应商配置异常" in diagnostic_titles
    assert "结构化输出重试偏高" in diagnostic_titles
    contract_retry_diagnostic = next(
        item for item in response.json["diagnostics"]
        if item["id"] == "contract-retry"
    )
    assert contract_retry_diagnostic["severity"] == "warning"
    assert "TEST_DESIGN / STRATEGY" in contract_retry_diagnostic["detail"]
    assert "prompt、artifact contract" in contract_retry_diagnostic["action"]
```

- [x] **Step 2: Run backend test to verify RED**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_endpoint.py::test_agent_observability_endpoint_groups_provider_issue_codes -q
```

Expected: FAIL because `contractRetryReasons` and `diagnostics` are missing.

- [x] **Step 3: Implement backend helpers**

In `run_persistence.py`:

- Add `CONTRACT_RETRY_REASON = "STRUCTURED_OUTPUT_CONTRACT_RETRY"`.
- Add `_contract_retry_reasons(metrics)` returning `{CONTRACT_RETRY_REASON: total_retry_count}` when total retry count is positive.
- Add `_top_contract_retry_stage(metrics)` returning `(workflow_id, stage_id, retry_count)` for the highest retry stage.
- Add `_runtime_diagnostics(...)` returning deterministic diagnostics:
  - provider/config issue diagnostic when provider issue count > 0;
  - failed runtime diagnostic when total success rate < 80 and failures > 0;
  - stage failure diagnostic for lowest success stage under 80;
  - contract retry diagnostic when retry count > 0.
- Include `"contractRetryReasons": ...` and `"diagnostics": ...` in the summary response.

- [x] **Step 4: Run backend test to verify GREEN**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_endpoint.py::test_agent_observability_endpoint_groups_provider_issue_codes -q
```

Expected: PASS.

## Task 2: Frontend Service Parser RED/GREEN

**Files:**
- Modify: `tools/new-agents/frontend/src/core/types.ts`
- Modify: `tools/new-agents/frontend/src/services/observabilityService.ts`
- Modify: `tools/new-agents/frontend/src/services/__tests__/observabilityService.test.ts`

- [x] **Step 1: Add failing service tests**

Update `OBSERVABILITY_PAYLOAD` with:

```ts
contractRetryReasons: { STRUCTURED_OUTPUT_CONTRACT_RETRY: 2 },
diagnostics: [
  {
    id: 'contract-retry',
    severity: 'warning',
    title: '结构化输出重试偏高',
    detail: '最近运行中有 2 次 contract retry。',
    action: '检查该阶段 prompt、artifact contract 和 renderer 输出是否同步。',
  },
],
```

Add expectations:

```ts
expect(summary.contractRetryReasons).toEqual({ STRUCTURED_OUTPUT_CONTRACT_RETRY: 2 });
expect(summary.diagnostics[0].title).toBe('结构化输出重试偏高');
```

Add malformed test:

```ts
it('fails explicitly when diagnostics are malformed', async () => {
  vi.mocked(fetch).mockResolvedValue(new Response(
    JSON.stringify({
      ...OBSERVABILITY_PAYLOAD,
      diagnostics: [{ id: 'bad', severity: 'unknown' }],
    }),
    { status: 200, headers: { 'Content-Type': 'application/json' } },
  ));

  await expect(fetchObservabilitySummary({ limit: 20 })).rejects.toThrow(
    'Invalid observability summary response'
  );
});
```

- [x] **Step 2: Run service test to verify RED**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/observabilityService.test.ts
```

Expected: FAIL because types/parser do not support new fields.

- [x] **Step 3: Implement parser and types**

Add:

```ts
export type ObservabilityDiagnosticSeverity = 'info' | 'warning' | 'critical';

export type ObservabilityDiagnostic = {
    id: string;
    severity: ObservabilityDiagnosticSeverity;
    title: string;
    detail: string;
    action: string;
};
```

Extend `ObservabilitySummary` with:

```ts
contractRetryReasons: Record<string, number>;
diagnostics: ObservabilityDiagnostic[];
```

In `observabilityService.ts`, add `parseDiagnosticSeverity`, `parseDiagnostic`, and parse `payload.contractRetryReasons` / `payload.diagnostics`.

- [x] **Step 4: Run service test to verify GREEN**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/observabilityService.test.ts
```

Expected: PASS.

## Task 3: Header Diagnostics UI RED/GREEN

**Files:**
- Modify: `tools/new-agents/frontend/src/components/Header.tsx`
- Modify: `tools/new-agents/frontend/src/components/__tests__/Header.test.tsx`

- [x] **Step 1: Add failing Header test**

Add to the runtime observability tests:

```ts
it('shows actionable runtime diagnostics and contract retry reasons', async () => {
  renderHeader();
  clickMoreAction(/运行统计/);

  expect(await screen.findByText('诊断建议')).toBeTruthy();
  expect(screen.getByText('结构化输出重试偏高')).toBeTruthy();
  expect(screen.getByText(/检查该阶段 prompt、artifact contract/)).toBeTruthy();
  expect(screen.getByText('STRUCTURED_OUTPUT_CONTRACT_RETRY x2')).toBeTruthy();
});
```

Ensure the mocked observability summary in the test file includes the same `diagnostics` and `contractRetryReasons` fields.

- [x] **Step 2: Run Header test to verify RED**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/Header.test.tsx -t "actionable runtime diagnostics"
```

Expected: FAIL because Header does not render diagnostics yet.

- [x] **Step 3: Render diagnostics**

In Header observability modal, after `运行告警` and before metric cards:

- Render `诊断建议` when `observabilitySummary.diagnostics.length > 0`.
- Render each diagnostic title, detail, and action.
- Render contract retry reason badges when `Object.keys(observabilitySummary.contractRetryReasons).length > 0`.

- [x] **Step 4: Run Header test to verify GREEN**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/Header.test.tsx -t "actionable runtime diagnostics"
```

Expected: PASS.

## Task 4: Todo, Full Verification, Commit

**Files:**
- Modify: `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md`
- Modify: `docs/todos/refactor/README.md`
- Modify: `docs/superpowers/plans/2026-06-24-runtime-observability-actions.md`

- [x] **Step 1: Update todo records**

Mark E09 consumed and record:

- backend summary adds diagnostics and contract retry reasons;
- Header observability modal shows actionable diagnostics;
- verification commands and known non-goals.

- [x] **Step 2: Run focused verification**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_endpoint.py -q
.venv/bin/python -m py_compile tools/new-agents/backend/run_persistence.py tools/new-agents/backend/routes.py
cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/observabilityService.test.ts src/core/__tests__/observabilityAlerts.test.ts src/components/__tests__/Header.test.tsx
cd tools/new-agents/frontend && npm run lint
git diff --check
```

Expected: all commands exit 0.

- [ ] **Step 3: Review scope**

Run:

```bash
git status --short
git diff --stat
```

Expected: only E09 code, tests, spec/plan, and todo docs changed.

- [ ] **Step 4: Commit**

Run:

```bash
git add docs/superpowers/specs/2026-06-24-runtime-observability-actions-design.md docs/superpowers/plans/2026-06-24-runtime-observability-actions.md docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md docs/todos/refactor/README.md tools/new-agents/backend/run_persistence.py tools/new-agents/backend/tests/test_agent_endpoint.py tools/new-agents/frontend/src/core/types.ts tools/new-agents/frontend/src/services/observabilityService.ts tools/new-agents/frontend/src/services/__tests__/observabilityService.test.ts tools/new-agents/frontend/src/components/Header.tsx tools/new-agents/frontend/src/components/__tests__/Header.test.tsx
git commit -m "feat(new-agents): 产品化运行统计诊断建议"
```

Expected: one focused commit on `codex/runtime-observability-actions-current`.

## Self-Review

- Spec coverage: plan covers backend contract, frontend parser, Header UI, todo records, verification, and commit.
- Placeholder scan: no placeholder work remains; all file paths and commands are explicit.
- Type consistency: `ObservabilitySummary` gains `diagnostics` and `contractRetryReasons`, which service parser and Header consume.
