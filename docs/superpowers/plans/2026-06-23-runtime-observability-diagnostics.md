# DeepSeek 格式化失败运行统计诊断闭环 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 DeepSeek/raw JSON streaming 的格式化失败分类接入共享 turn metrics、observability API 和 Header 运行统计，让用户能从统计入口完成失败归因和行动承接。

**Architecture:** 复用现有 `AgentRunTurnMetric.error_code` 记录稳定格式化失败 code，不新增表。`run_persistence.py` 在 summary 中派生 `formatFailureDiagnostics`，前端 service 严格解析新增 contract，Header 在现有运行统计弹窗中展示诊断区块。

**Tech Stack:** Flask + SQLAlchemy + Pydantic/PydanticAI backend；React 19 + TypeScript + Vitest frontend；pytest backend tests。

---

## File Structure

- Modify: `tools/new-agents/backend/stream_services.py`
  - 将 `FormattedOutputDiagnosticError.kind` 映射为稳定 metric/SSE error code。
- Modify: `tools/new-agents/backend/run_persistence.py`
  - 基于现有 turn metrics 派生格式化失败 diagnostics 汇总和行动建议。
- Modify: `tools/new-agents/backend/tests/test_stream_services.py`
  - RED/GREEN 覆盖 runtime diagnostic exception 被持久化为分类 metric。
- Modify: `tools/new-agents/backend/tests/test_agent_endpoint.py`
  - RED/GREEN 覆盖 observability response 新增 drilldown。
- Modify: `tools/new-agents/frontend/src/core/types.ts`
  - 增加格式化失败诊断类型。
- Modify: `tools/new-agents/frontend/src/services/observabilityService.ts`
  - 严格解析 `formatFailureDiagnostics`。
- Modify: `tools/new-agents/frontend/src/core/observabilityAlerts.ts`
  - 增加格式化失败集中告警。
- Modify: `tools/new-agents/frontend/src/components/Header.tsx`
  - 在运行统计详情中展示格式化失败诊断区块。
- Modify: `tools/new-agents/frontend/src/services/__tests__/observabilityService.test.ts`
  - RED/GREEN 覆盖 service 解析和 malformed payload。
- Modify: `tools/new-agents/frontend/src/core/__tests__/observabilityAlerts.test.ts`
  - RED/GREEN 覆盖格式化失败告警。
- Modify: `tools/new-agents/frontend/src/components/__tests__/Header.test.tsx`
  - RED/GREEN 覆盖运行统计弹窗展示诊断区块。
- Modify: `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md`
  - 记录 E09 本轮消化。
- Modify: `docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md`
  - 记录 DeepSeek 格式化失败统计产品化状态。
- Modify: `docs/todos/refactor/README.md`
  - 更新当前入口和下一轮候选。

## Task 1: Backend stream metric classification

**Files:**
- Test: `tools/new-agents/backend/tests/test_stream_services.py`
- Modify: `tools/new-agents/backend/stream_services.py`

- [ ] **Step 1: Write failing test**

Add a test that monkeypatches `build_pydantic_agent_runtime()` to return a runtime whose `stream_turn()` raises `FormattedOutputDiagnosticError(kind="artifact_data_schema", retry_count=2, ...)`. Assert the final SSE error uses `FORMATTED_OUTPUT_ARTIFACT_DATA_SCHEMA` and the recorded metric has the same `error_code` and retry count.

- [ ] **Step 2: Run RED**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_stream_services.py::test_stream_records_formatted_output_diagnostic_metric -q
```

Expected: fail because `stream_services.py` does not yet catch `FormattedOutputDiagnosticError`.

- [ ] **Step 3: Implement minimal classification**

Import `FormattedOutputDiagnosticError`, add a mapping helper from diagnostic kind to stable error code, catch it before generic schema errors, call `record_metric("error", code, contract_retry_count=e.retry_count)`, and yield `ErrorEvent(code=code, message=str(e))`.

- [ ] **Step 4: Run GREEN**

Run the same pytest command. Expected: pass.

## Task 2: Backend observability drilldown

**Files:**
- Test: `tools/new-agents/backend/tests/test_agent_endpoint.py`
- Modify: `tools/new-agents/backend/run_persistence.py`

- [ ] **Step 1: Write failing endpoint test**

Add a test that records metrics with `FORMATTED_OUTPUT_ARTIFACT_DATA_SCHEMA`, `FORMATTED_OUTPUT_JSON_DECODE`, and a non-format error. Assert `/api/agent/observability` returns `formatFailureDiagnostics.total`, `byKind`, `byStage`, and `byProvider` with counts, retry counts, top kind and action.

- [ ] **Step 2: Run RED**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_endpoint.py::test_agent_observability_endpoint_groups_formatted_output_diagnostics -q
```

Expected: fail because `formatFailureDiagnostics` is absent.

- [ ] **Step 3: Implement summary derivation**

Add constants for known format failure error codes, kind labels and actions. Build diagnostics from filtered `AgentRunTurnMetric` rows. Keep output deterministic by sorting by count desc then key asc.

- [ ] **Step 4: Run GREEN**

Run the same pytest command. Expected: pass.

## Task 3: Frontend service and alerts contract

**Files:**
- Modify: `tools/new-agents/frontend/src/core/types.ts`
- Test: `tools/new-agents/frontend/src/services/__tests__/observabilityService.test.ts`
- Test: `tools/new-agents/frontend/src/core/__tests__/observabilityAlerts.test.ts`
- Modify: `tools/new-agents/frontend/src/services/observabilityService.ts`
- Modify: `tools/new-agents/frontend/src/core/observabilityAlerts.ts`

- [ ] **Step 1: Write failing service test**

Extend the fixture payload with `formatFailureDiagnostics`. Assert `fetchObservabilitySummary()` exposes typed diagnostics and rejects malformed diagnostics.

- [ ] **Step 2: Write failing alert test**

Assert `buildObservabilityAlerts()` returns an alert titled `格式化输出失败集中` when `formatFailureDiagnostics.total > 0`, and that the detail includes top kind label and action.

- [ ] **Step 3: Run RED**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/observabilityService.test.ts src/core/__tests__/observabilityAlerts.test.ts
```

Expected: fail because types/parser/alerts do not include diagnostics.

- [ ] **Step 4: Implement minimal frontend parsing and alert**

Add diagnostic types, parser helpers, and alert generation. Keep parsing strict and avoid `as any`.

- [ ] **Step 5: Run GREEN**

Run the same npm test command. Expected: pass.

## Task 4: Header observability UI

**Files:**
- Test: `tools/new-agents/frontend/src/components/__tests__/Header.test.tsx`
- Modify: `tools/new-agents/frontend/src/components/Header.tsx`

- [ ] **Step 1: Write failing Header test**

Extend mocked summary with format diagnostics, open “运行统计”, and assert the modal shows `格式化输出诊断`, top kind label, affected stage/provider and action suggestion.

- [ ] **Step 2: Run RED**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/Header.test.tsx
```

Expected: fail because Header does not render diagnostics.

- [ ] **Step 3: Implement UI section**

Add a compact section in the existing observability modal after alert cards and before totals. Use existing visual style, no nested cards beyond repeated items, and no new state store.

- [ ] **Step 4: Run GREEN**

Run the same Header test command. Expected: pass.

## Task 5: Docs and final verification

**Files:**
- Modify: `docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md`
- Modify: `docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md`
- Modify: `docs/todos/refactor/README.md`

- [ ] **Step 1: Update todo records**

Mark E09 as consumed by the DeepSeek 格式化失败运行统计诊断闭环. Keep E08 and E05 as next thick-slice candidates. Keep real DeepSeek smoke as external optional validation.

- [ ] **Step 2: Run backend verification**

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_stream_services.py tools/new-agents/backend/tests/test_agent_endpoint.py -q
.venv/bin/python -m py_compile tools/new-agents/backend/stream_services.py tools/new-agents/backend/run_persistence.py
```

- [ ] **Step 3: Run frontend verification**

```bash
cd tools/new-agents/frontend && npm run test -- --run src/services/__tests__/observabilityService.test.ts src/core/__tests__/observabilityAlerts.test.ts src/components/__tests__/Header.test.tsx
```

- [ ] **Step 4: Run diff checks**

```bash
git diff --check
git diff --cached --check
```

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/specs/2026-06-23-runtime-observability-diagnostics-design.md docs/superpowers/plans/2026-06-23-runtime-observability-diagnostics.md docs/todos/refactor/2026-06-23-new-agents-enhancement-diagnostic.md docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md docs/todos/refactor/README.md tools/new-agents/backend/stream_services.py tools/new-agents/backend/run_persistence.py tools/new-agents/backend/tests/test_stream_services.py tools/new-agents/backend/tests/test_agent_endpoint.py tools/new-agents/frontend/src/core/types.ts tools/new-agents/frontend/src/services/observabilityService.ts tools/new-agents/frontend/src/core/observabilityAlerts.ts tools/new-agents/frontend/src/components/Header.tsx tools/new-agents/frontend/src/services/__tests__/observabilityService.test.ts tools/new-agents/frontend/src/core/__tests__/observabilityAlerts.test.ts tools/new-agents/frontend/src/components/__tests__/Header.test.tsx
git commit -m "feat(new-agents): 产品化格式化失败运行统计"
```
