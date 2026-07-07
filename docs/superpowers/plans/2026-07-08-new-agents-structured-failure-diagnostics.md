# New Agents Structured Failure Diagnostics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a shared typed diagnostic path for New Agents structured-output failures so SSE errors, chat recovery cards, and observability recent turns expose actionable workflow/stage/field/validator context while still failing explicitly.

**Architecture:** Extend the existing shared Agent Runtime path instead of adding workflow-specific branches. Backend `ErrorEvent` remains backward compatible with `code/message` and adds optional `diagnostic`; stream services build sanitized diagnostics, persistence stores diagnostic summaries on turn metrics, and frontend parser/chat/UI consume the same typed shape.

**Tech Stack:** Flask, SQLAlchemy, Pydantic, typed SSE, pytest, React, TypeScript, Zustand, Vitest, Testing Library.

## Global Constraints

- Do not lower schema, artifact, Mermaid, or structured visual validation strictness.
- Do not create fallback drafts, synthetic success, production mocks, or hidden success responses.
- Do not record API keys, complete model outputs, complete user inputs, or complete prompts in diagnostic persistence.
- Do not add Lisa-, Alex-, workflow-, or stage-specific runtime, API, transport, store, or rendering branches.
- Preserve backward compatibility for SSE errors that only contain `code` and `message`.
- Limit writes to this feature's spec, plan, New Agents backend/frontend code and tests, API/TESTING docs, and the structured failure todo record.

---

## File Map

- Modify: `tools/new-agents/backend/sse_schemas.py`
  Add `ErrorDiagnostic` and optional `diagnostic` on `ErrorEvent`.
- Modify: `tools/new-agents/backend/stream_services.py`
  Build sanitized diagnostics for request, structured output, contract, runtime, and provider failures; pass diagnostics to SSE and metrics.
- Modify: `tools/new-agents/backend/models.py`
  Add optional diagnostic columns to `AgentRunTurnMetric`.
- Modify: `tools/new-agents/backend/app.py`
  Add startup column migration for existing `agent_run_turn_metrics`.
- Modify: `tools/new-agents/backend/run_persistence.py`
  Persist diagnostic summary fields and expose `recentTurns[].diagnostic`.
- Modify: `tools/new-agents/backend/tests/test_sse_encoder.py`
  Cover error event diagnostic serialization and validation.
- Modify: `tools/new-agents/backend/tests/test_stream_services.py`
  Cover schema/provider diagnostic SSE and metric calls.
- Modify: `tools/new-agents/backend/tests/test_run_persistence.py`
  Cover metric diagnostic persistence and observability response.
- Modify: `tools/new-agents/frontend/src/core/types.ts`
  Extend message and observability diagnostic types.
- Modify: `tools/new-agents/frontend/src/core/llm.ts`
  Parse typed SSE error diagnostics and throw a typed runtime error.
- Modify: `tools/new-agents/frontend/src/services/chatService.ts`
  Prefer typed diagnostics when building assistant error feedback.
- Modify: `tools/new-agents/frontend/src/services/observabilityService.ts`
  Parse recent turn diagnostics.
- Modify: `tools/new-agents/frontend/src/components/ChatPane.tsx`
  Show workflow/stage, field path, validator, and retry suggestion in expanded diagnostic details.
- Modify: `tools/new-agents/frontend/src/components/Header.tsx`
  Show recent turn diagnostic summary in observability.
- Modify tests under `tools/new-agents/frontend/src/core/__tests__/llm.test.ts`, `services/__tests__/chatService.test.ts`, `services/__tests__/observabilityService.test.ts`, `components/__tests__/ChatPane.test.tsx`, and optionally `components/__tests__/Header.test.tsx`.
- Modify docs: `docs/api-contracts.md`, `docs/TESTING.md`, `docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md`.

---

### Task 1: Backend SSE Diagnostic Contract

**Files:**
- Modify: `tools/new-agents/backend/sse_schemas.py`
- Modify: `tools/new-agents/backend/tests/test_sse_encoder.py`

**Interfaces:**
- Produces: `ErrorDiagnostic` Pydantic model with fields `phase`, `workflow_id`, `stage_id`, `field_path`, `validator`, `retryable`, `public_reason`.
- Produces: `ErrorEvent(diagnostic: ErrorDiagnostic | None = None)` serialized with camelCase aliases: `workflowId`, `stageId`, `fieldPath`, `publicReason`.
- Consumed by: `stream_services.py`, frontend `core/llm.ts`.

- [x] **Step 1: Write failing serialization test**

Add to `tools/new-agents/backend/tests/test_sse_encoder.py`:

```python
def test_encode_error_event_includes_optional_diagnostic_contract():
    encoded = encode_sse_event(ErrorEvent.model_validate({
        "code": "SCHEMA_VALIDATION_FAILED",
        "message": "artifact_data.requirement_facts.0.fact must be non-empty",
        "diagnostic": {
            "phase": "structured_output",
            "workflowId": "TEST_DESIGN",
            "stageId": "CLARIFY",
            "fieldPath": "artifact_data.requirement_facts.0.fact",
            "validator": "string_too_short",
            "retryable": True,
            "publicReason": "模型输出的结构化字段未通过校验，右侧产出物已保持不变。",
        },
    }))

    payload = json.loads(encoded.removeprefix("data: ").strip())

    assert payload["diagnostic"] == {
        "phase": "structured_output",
        "workflowId": "TEST_DESIGN",
        "stageId": "CLARIFY",
        "fieldPath": "artifact_data.requirement_facts.0.fact",
        "validator": "string_too_short",
        "retryable": True,
        "publicReason": "模型输出的结构化字段未通过校验，右侧产出物已保持不变。",
    }
```

- [x] **Step 2: Write failing validation test**

Add to the same file:

```python
def test_error_event_rejects_invalid_diagnostic_contract():
    with pytest.raises(ValueError, match="diagnostic phase cannot be blank"):
        ErrorEvent.model_validate({
            "code": "SCHEMA_VALIDATION_FAILED",
            "message": "failed",
            "diagnostic": {
                "phase": " ",
                "workflowId": "TEST_DESIGN",
                "stageId": "CLARIFY",
                "fieldPath": "artifact_data",
                "validator": "structured_output",
                "retryable": True,
                "publicReason": "结构化输出未通过校验。",
            },
        })
```

- [x] **Step 3: Run tests and confirm red**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_sse_encoder.py::test_encode_error_event_includes_optional_diagnostic_contract tools/new-agents/backend/tests/test_sse_encoder.py::test_error_event_rejects_invalid_diagnostic_contract -q
```

Expected: tests fail because `ErrorEvent` does not support `diagnostic`.

- [x] **Step 4: Implement backend SSE models**

In `tools/new-agents/backend/sse_schemas.py`, add `ErrorDiagnostic`:

```python
class ErrorDiagnostic(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    phase: str = Field(min_length=1)
    workflow_id: str = Field(min_length=1, alias="workflowId")
    stage_id: str = Field(min_length=1, alias="stageId")
    field_path: str = Field(min_length=1, alias="fieldPath")
    validator: str = Field(min_length=1)
    retryable: bool
    public_reason: str = Field(min_length=1, alias="publicReason")

    @field_validator("phase")
    @classmethod
    def validate_phase_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("diagnostic phase cannot be blank")
        return value
```

Then update `ErrorEvent`:

```python
class ErrorEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["error"] = "error"
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    diagnostic: ErrorDiagnostic | None = None
```

- [x] **Step 5: Run tests and confirm green**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_sse_encoder.py -q
```

Expected: all tests in `test_sse_encoder.py` pass.

---

### Task 2: Backend Diagnostic Builder, Metrics, and Observability

**Files:**
- Modify: `tools/new-agents/backend/stream_services.py`
- Modify: `tools/new-agents/backend/models.py`
- Modify: `tools/new-agents/backend/app.py`
- Modify: `tools/new-agents/backend/run_persistence.py`
- Modify: `tools/new-agents/backend/tests/test_stream_services.py`
- Modify: `tools/new-agents/backend/tests/test_run_persistence.py`

**Interfaces:**
- Produces: `build_error_diagnostic(error, code, workflow_id, stage_id) -> ErrorDiagnostic`.
- Produces: `record_turn_metric(..., diagnostic: ErrorDiagnostic | dict | None = None)`.
- Produces: `recentTurns[].diagnostic` object or `null`.
- Consumes: `ErrorDiagnostic` from Task 1.

- [x] **Step 1: Write failing stream service test for schema diagnostics**

Add to `tools/new-agents/backend/tests/test_stream_services.py`:

```python
@patch("stream_services.build_pydantic_agent_runtime")
def test_stream_agent_run_events_returns_typed_schema_diagnostic_and_metric(
    mock_build_runtime: MagicMock,
) -> None:
    runtime = MagicMock()
    runtime.stream_turn.side_effect = AgentRuntimeSchemaError(
        "Exceeded maximum output retries (2): artifact_data.requirement_facts.0.fact"
    )
    mock_build_runtime.return_value = runtime
    persistence = FakePersistence()
    request = AgentRunStreamRequest.model_validate({
        "prompt": "用户需求",
        "systemPrompt": "你是 Lisa。",
        "workflowId": "TEST_DESIGN",
        "stageId": "CLARIFY",
    })

    events = list(stream_agent_run_events(
        request,
        api_key="test-api-key",
        base_url="https://api.deepseek.com/v1",
        model_name="deepseek-chat",
        persistence=persistence,
    ))

    error = events[-1]
    assert isinstance(error, ErrorEvent)
    assert error.code == "SCHEMA_VALIDATION_FAILED"
    assert error.diagnostic is not None
    assert error.diagnostic.phase == "structured_output"
    assert error.diagnostic.workflow_id == "TEST_DESIGN"
    assert error.diagnostic.stage_id == "CLARIFY"
    assert error.diagnostic.field_path == "artifact_data"
    assert error.diagnostic.validator == "pydantic_ai_output_retry"
    assert error.diagnostic.retryable is True
    metric_call = [call for call in persistence.calls if call[0] == "record_turn_metric"][-1][1]
    assert metric_call["diagnostic"]["phase"] == "structured_output"
    assert metric_call["diagnostic"]["fieldPath"] == "artifact_data"
```

- [x] **Step 2: Write failing stream service test for provider diagnostics**

Add to the same file:

```python
@patch("stream_services.build_pydantic_agent_runtime")
def test_stream_agent_run_events_returns_typed_provider_diagnostic(
    mock_build_runtime: MagicMock,
) -> None:
    runtime = MagicMock()
    runtime.stream_turn.side_effect = AgentRuntimeModelError("401 invalid api key")
    mock_build_runtime.return_value = runtime
    request = AgentRunStreamRequest.model_validate({
        "prompt": "用户需求",
        "systemPrompt": "你是 Lisa。",
        "workflowId": "TEST_DESIGN",
        "stageId": "CLARIFY",
    })

    events = list(stream_agent_run_events(
        request,
        api_key="test-api-key",
        base_url="https://api.example.com/v1",
        model_name="test-model",
    ))

    error = events[-1]
    assert isinstance(error, ErrorEvent)
    assert error.code == "LLM_ERROR"
    assert error.diagnostic is not None
    assert error.diagnostic.phase == "provider"
    assert error.diagnostic.field_path == "provider"
    assert error.diagnostic.validator == "provider_authentication"
    assert error.diagnostic.retryable is False
```

- [x] **Step 3: Write failing persistence / observability test**

Add to `tools/new-agents/backend/tests/test_run_persistence.py`:

```python
def test_observability_recent_turns_include_sanitized_error_diagnostic(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")
        record_turn_metric(
            run_id=run.id,
            workflow_id="TEST_DESIGN",
            stage_id="CLARIFY",
            model_name="deepseek-chat",
            provider="deepseek",
            status="error",
            error_code="SCHEMA_VALIDATION_FAILED",
            duration_ms=1200,
            input_chars=80,
            output_chars=0,
            estimated_tokens=20,
            contract_retry_count=2,
            diagnostic={
                "phase": "structured_output",
                "fieldPath": "artifact_data.requirement_facts.0.fact",
                "validator": "string_too_short",
                "publicReason": "模型输出的结构化字段未通过校验，右侧产出物已保持不变。",
                "retryable": True,
            },
        )

        summary = get_runtime_observability_summary(limit=5)

    turn = summary["recentTurns"][0]
    assert turn["diagnostic"] == {
        "phase": "structured_output",
        "fieldPath": "artifact_data.requirement_facts.0.fact",
        "validator": "string_too_short",
        "publicReason": "模型输出的结构化字段未通过校验，右侧产出物已保持不变。",
        "retryable": True,
    }
```

- [x] **Step 4: Run tests and confirm red**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_stream_services.py::test_stream_agent_run_events_returns_typed_schema_diagnostic_and_metric tools/new-agents/backend/tests/test_stream_services.py::test_stream_agent_run_events_returns_typed_provider_diagnostic tools/new-agents/backend/tests/test_run_persistence.py::test_observability_recent_turns_include_sanitized_error_diagnostic -q
```

Expected: tests fail because diagnostics are not implemented.

- [x] **Step 5: Implement diagnostic builder and metric wiring**

In `stream_services.py`, add helpers:

```python
def _diagnostic_payload(diagnostic: ErrorDiagnostic | None) -> dict | None:
    if diagnostic is None:
        return None
    return diagnostic.model_dump(by_alias=True)


def _build_error_diagnostic(
    *,
    code: str,
    error: Exception,
    workflow_id: str,
    stage_id: str,
) -> ErrorDiagnostic:
    # Classify by code and exception type. Keep output sanitized.
```

Update each exception branch to:

```python
diagnostic = _build_error_diagnostic(
    code="SCHEMA_VALIDATION_FAILED",
    error=e,
    workflow_id=agent_request.workflow_id,
    stage_id=agent_request.stage_id,
)
record_metric("error", "SCHEMA_VALIDATION_FAILED", diagnostic=diagnostic, ...)
yield ErrorEvent(code="SCHEMA_VALIDATION_FAILED", message=..., diagnostic=diagnostic)
```

Update `_record_turn_metric()` and nested `record_metric()` to accept `diagnostic`.

- [x] **Step 6: Implement metric columns and observability serialization**

In `models.py`, add nullable columns to `AgentRunTurnMetric`:

```python
diagnostic_phase = db.Column(db.String(64))
diagnostic_field_path = db.Column(db.Text)
diagnostic_validator = db.Column(db.String(128))
diagnostic_public_reason = db.Column(db.Text)
diagnostic_retryable = db.Column(db.Boolean)
```

In `app.py`, add `_ensure_turn_metric_diagnostic_columns()` and call it from `init_db()`.

In `run_persistence.py`, persist diagnostic fields and add `_turn_metric_diagnostic_snapshot(metric)`.

- [x] **Step 7: Run backend focused tests**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_sse_encoder.py tools/new-agents/backend/tests/test_stream_services.py tools/new-agents/backend/tests/test_run_persistence.py -q
```

Expected: selected backend tests pass.

---

### Task 3: Frontend Typed Error Propagation

**Files:**
- Modify: `tools/new-agents/frontend/src/core/types.ts`
- Modify: `tools/new-agents/frontend/src/core/llm.ts`
- Modify: `tools/new-agents/frontend/src/services/chatService.ts`
- Modify: `tools/new-agents/frontend/src/core/__tests__/llm.test.ts`
- Modify: `tools/new-agents/frontend/src/services/__tests__/chatService.test.ts`

**Interfaces:**
- Produces: frontend `AgentRuntimeError` carrying `code`, `backendMessage`, and `diagnostic`.
- Produces: `MessageErrorDiagnostic` fields `phase`, `workflowId`, `stageId`, `fieldPath`, `validator`, `retryable`.
- Consumes: backend `error.diagnostic`.

- [x] **Step 1: Write failing llm parser test**

Add to `tools/new-agents/frontend/src/core/__tests__/llm.test.ts` near existing SSE error tests:

```ts
it('propagates typed backend error diagnostics from SSE error events', async () => {
  mockFetchSse([
    'data: {"type":"run_started","runId":"run-123"}',
    'data: {"type":"error","code":"SCHEMA_VALIDATION_FAILED","message":"schema failed","diagnostic":{"phase":"structured_output","workflowId":"TEST_DESIGN","stageId":"CLARIFY","fieldPath":"artifact_data.requirement_facts.0.fact","validator":"string_too_short","retryable":true,"publicReason":"模型输出的结构化字段未通过校验，右侧产出物已保持不变。"}}',
    'data: [DONE]',
  ]);

  await expect(collectStream(generateResponseStream('生成'))).rejects.toMatchObject({
    code: 'SCHEMA_VALIDATION_FAILED',
    diagnostic: {
      phase: 'structured_output',
      workflowId: 'TEST_DESIGN',
      stageId: 'CLARIFY',
      fieldPath: 'artifact_data.requirement_facts.0.fact',
      validator: 'string_too_short',
      retryable: true,
      publicReason: '模型输出的结构化字段未通过校验，右侧产出物已保持不变。',
    },
  });
});
```

- [x] **Step 2: Write failing chat service test**

Add to `tools/new-agents/frontend/src/services/__tests__/chatService.test.ts` by mocking `generateResponseStream()` to throw an error object with diagnostic:

```ts
it('uses typed structured diagnostics when generation fails', async () => {
  const error = Object.assign(new Error('schema failed'), {
    code: 'SCHEMA_VALIDATION_FAILED',
    backendMessage: 'schema failed',
    diagnostic: {
      phase: 'structured_output',
      workflowId: 'TEST_DESIGN',
      stageId: 'CLARIFY',
      fieldPath: 'artifact_data.requirement_facts.0.fact',
      validator: 'string_too_short',
      retryable: true,
      publicReason: '模型输出的结构化字段未通过校验，右侧产出物已保持不变。',
    },
  });
  vi.mocked(generateResponseStream).mockImplementation(async function* () {
    throw error;
  });

  await renderHookAndSendMessage('生成测试分析');

  const latest = useStore.getState().chatHistory.at(-1);
  expect(latest?.errorDiagnostic).toMatchObject({
    kind: 'structured',
    phase: 'structured_output',
    workflowId: 'TEST_DESIGN',
    stageId: 'CLARIFY',
    fieldPath: 'artifact_data.requirement_facts.0.fact',
    validator: 'string_too_short',
    retryable: true,
    code: 'SCHEMA_VALIDATION_FAILED',
  });
});
```

Use existing helper names in the file; if helpers differ, adapt only the setup lines, not the assertion shape.

- [x] **Step 3: Run tests and confirm red**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/llm.test.ts src/services/__tests__/chatService.test.ts
```

Expected: new tests fail because typed diagnostics are not propagated.

- [x] **Step 4: Implement typed error parser**

In `core/llm.ts`, add frontend diagnostic type and error class:

```ts
export class AgentRuntimeError extends Error {
  code: string;
  backendMessage: string;
  diagnostic?: AgentRuntimeErrorDiagnostic;
}
```

When parsing `event.type === 'error'`, throw `AgentRuntimeError` instead of plain `Error`.

- [x] **Step 5: Implement chat service diagnostic mapping**

In `chatService.ts`, update `getErrorMessage()` / error feedback path to preserve the original error object and prefer `error.diagnostic` when available. Map `phase` to `kind`:

```ts
const kind = diagnostic.phase === 'provider'
  ? 'provider'
  : ['structured_output', 'contract_validation'].includes(diagnostic.phase)
    ? 'structured'
    : 'generic';
```

Extend `MessageErrorDiagnostic` in `core/types.ts`.

- [x] **Step 6: Run frontend focused tests**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/llm.test.ts src/services/__tests__/chatService.test.ts
```

Expected: tests pass.

---

### Task 4: Frontend Display and Observability Parsing

**Files:**
- Modify: `tools/new-agents/frontend/src/services/observabilityService.ts`
- Modify: `tools/new-agents/frontend/src/components/ChatPane.tsx`
- Modify: `tools/new-agents/frontend/src/components/Header.tsx`
- Modify: `tools/new-agents/frontend/src/services/__tests__/observabilityService.test.ts`
- Modify: `tools/new-agents/frontend/src/components/__tests__/ChatPane.test.tsx`
- Modify: `tools/new-agents/frontend/src/components/__tests__/Header.test.tsx`

**Interfaces:**
- Consumes: `MessageErrorDiagnostic.phase/workflowId/stageId/fieldPath/validator/retryable`.
- Consumes: `ObservabilityTurn.diagnostic`.
- Produces: visible diagnostic details in ChatPane and recent-turn observability display.

- [x] **Step 1: Write failing ChatPane display test**

Add to `ChatPane.test.tsx`:

```tsx
it('shows typed structured diagnostic fields in expanded error details', async () => {
  setupStoreWithMessages([{
    id: 'assistant-1',
    role: 'assistant',
    content: '⚠️ 模型输出的结构化字段未通过校验，右侧产出物已保持不变。',
    timestamp: Date.now(),
    errorDiagnostic: {
      kind: 'structured',
      summary: '模型输出的结构化字段未通过校验，右侧产出物已保持不变。',
      rawMessage: 'schema failed',
      code: 'SCHEMA_VALIDATION_FAILED',
      phase: 'structured_output',
      workflowId: 'TEST_DESIGN',
      stageId: 'CLARIFY',
      fieldPath: 'artifact_data.requirement_facts.0.fact',
      validator: 'string_too_short',
      retryable: true,
    },
  }]);

  render(<ChatPane />);
  await userEvent.click(screen.getByRole('button', { name: /查看详情/ }));

  expect(screen.getByText(/TEST_DESIGN \/ CLARIFY/)).toBeInTheDocument();
  expect(screen.getByText(/artifact_data.requirement_facts.0.fact/)).toBeInTheDocument();
  expect(screen.getByText(/string_too_short/)).toBeInTheDocument();
  expect(screen.getByText(/建议重试：是/)).toBeInTheDocument();
});
```

Use existing store setup helper names in `ChatPane.test.tsx`; keep the assertion texts.

- [x] **Step 2: Write failing observability parser test**

Add to `observabilityService.test.ts`:

```ts
it('parses recent turn diagnostics', async () => {
  mockFetchJson({
    totals: baseTotals,
    byStage: [],
    byProvider: [],
    recentTurns: [{
      id: 1,
      runId: 'run-1',
      workflowId: 'TEST_DESIGN',
      stageId: 'CLARIFY',
      model: 'deepseek-chat',
      provider: 'deepseek',
      status: 'error',
      errorCode: 'SCHEMA_VALIDATION_FAILED',
      durationMs: 1200,
      inputChars: 80,
      outputChars: 0,
      estimatedTokens: 20,
      contractRetryCount: 2,
      createdAt: '2026-07-08T00:00:00',
      diagnostic: {
        phase: 'structured_output',
        fieldPath: 'artifact_data.requirement_facts.0.fact',
        validator: 'string_too_short',
        publicReason: '模型输出的结构化字段未通过校验，右侧产出物已保持不变。',
        retryable: true,
      },
    }],
  });

  const summary = await fetchObservabilitySummary();

  expect(summary.recentTurns[0].diagnostic).toMatchObject({
    phase: 'structured_output',
    fieldPath: 'artifact_data.requirement_facts.0.fact',
    validator: 'string_too_short',
    retryable: true,
  });
});
```

- [x] **Step 3: Run tests and confirm red**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/ChatPane.test.tsx src/services/__tests__/observabilityService.test.ts
```

Expected: tests fail until UI/parser fields exist.

- [x] **Step 4: Implement ChatPane details**

In `ChatPane.tsx`, inside expanded diagnostic details, render extra rows only when fields exist:

```tsx
{msg.errorDiagnostic.workflowId && msg.errorDiagnostic.stageId && (
  <p className="mt-1"><span className="font-semibold">阶段：</span>{msg.errorDiagnostic.workflowId} / {msg.errorDiagnostic.stageId}</p>
)}
{msg.errorDiagnostic.fieldPath && (
  <p className="mt-1"><span className="font-semibold">字段路径：</span>{msg.errorDiagnostic.fieldPath}</p>
)}
{msg.errorDiagnostic.validator && (
  <p className="mt-1"><span className="font-semibold">校验器：</span>{msg.errorDiagnostic.validator}</p>
)}
{msg.errorDiagnostic.retryable !== undefined && (
  <p className="mt-1"><span className="font-semibold">建议重试：</span>{msg.errorDiagnostic.retryable ? '是' : '否'}</p>
)}
```

- [x] **Step 5: Implement observability parsing and display**

In `core/types.ts`, add `ObservabilityTurnDiagnostic`. In `observabilityService.ts`, parse nullable `diagnostic`. In `Header.tsx`, show recent turn diagnostic under error code:

```tsx
{turn.diagnostic && (
  <div className="mt-1 text-[11px] text-amber-100/80">
    {turn.diagnostic.fieldPath} · {turn.diagnostic.validator}
  </div>
)}
```

- [x] **Step 6: Run frontend display tests**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/ChatPane.test.tsx src/services/__tests__/observabilityService.test.ts src/components/__tests__/Header.test.tsx
```

Expected: tests pass.

---

### Task 5: Documentation, Todo Record, and Focused Verification

**Files:**
- Modify: `docs/api-contracts.md`
- Modify: `docs/TESTING.md`
- Modify: `docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md`

**Interfaces:**
- Consumes: implemented SSE `error.diagnostic`.
- Produces: updated route contract, testing strategy, and target-mode execution record.

- [x] **Step 1: Update API docs**

In `docs/api-contracts.md`, under Agent Runtime SSE response format, add an `error` example:

```json
{
  "type": "error",
  "code": "SCHEMA_VALIDATION_FAILED",
  "message": "模型连续生成的结构化结果未通过校验。",
  "diagnostic": {
    "phase": "structured_output",
    "workflowId": "TEST_DESIGN",
    "stageId": "CLARIFY",
    "fieldPath": "artifact_data.requirement_facts.0.fact",
    "validator": "string_too_short",
    "retryable": true,
    "publicReason": "模型输出的结构化字段未通过校验，右侧产出物已保持不变。"
  }
}
```

- [x] **Step 2: Update testing docs**

In `docs/TESTING.md`, add a short New Agents subsection stating that structured output failures must be covered by:

```text
- backend typed ErrorEvent diagnostic contract tests
- stream service schema/provider failure tests
- run metric / observability diagnostic tests
- frontend SSE parser and ChatPane diagnostic display tests
```

- [x] **Step 3: Update todo execution record**

In `docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md`, add a "第 1 轮执行记录" section with spec path, plan path, implementation summary, verification commands, and residual risk.

- [x] **Step 4: Run document checks**

Run:

```bash
git diff --check -- docs/api-contracts.md docs/TESTING.md docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md docs/superpowers/specs/2026-07-08-new-agents-structured-failure-diagnostics-design.md docs/superpowers/plans/2026-07-08-new-agents-structured-failure-diagnostics.md
```

Expected: no output.

Run:

```bash
rg -n "T[B]D|T[O]DO|待[补]|待[定]|<[填]|implement[ ]later" docs/api-contracts.md docs/TESTING.md docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md docs/superpowers/specs/2026-07-08-new-agents-structured-failure-diagnostics-design.md docs/superpowers/plans/2026-07-08-new-agents-structured-failure-diagnostics.md
```

Expected: no matches.

- [x] **Step 5: Run focused backend and frontend verification**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_sse_encoder.py tools/new-agents/backend/tests/test_stream_services.py tools/new-agents/backend/tests/test_run_persistence.py -q
```

Expected: pass.

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/llm.test.ts src/services/__tests__/chatService.test.ts src/services/__tests__/observabilityService.test.ts src/components/__tests__/ChatPane.test.tsx src/components/__tests__/Header.test.tsx
```

Expected: pass.

- [x] **Step 6: Run wider New Agents regression if focused tests pass**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_endpoint.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_workflow_contract_sync.py -q
```

Expected: pass.

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/llm.test.ts src/services/__tests__/chatService.test.ts src/components/__tests__/ChatPane.test.tsx src/components/__tests__/Header.test.tsx
```

Expected: pass.

- [x] **Step 7: Decide full local automation**

Because this is a completed code user story touching backend and frontend shared runtime behavior, default target-mode rule is to run:

```bash
./scripts/test/test-local.sh all
```

If sandbox blocks MidScene / Playwright / port binding, rerun with approved escalation or record exact environment blockage and run the closest New Agents-focused equivalent.

Decision recorded for this slice: run New Agents-focused local automation because the change is scoped to `tools/new-agents` shared runtime/backend/frontend behavior, not intent-tester, common frontend, or browser E2E. Executed:

```bash
./scripts/test/test-local.sh new-agents
```

Result: New Agents frontend `701 passed`; New Agents backend `553 passed, 1 deselected`.

---

## Self-Review

- Spec coverage: all spec requirements map to Tasks 1-5.
- Placeholder scan: no open placeholders are intentionally left in this plan.
- Type consistency: backend alias names use `workflowId`, `stageId`, `fieldPath`, `publicReason`; frontend message fields use the same camelCase names.
- Scope check: this plan does not implement derived-field backendization, ID convergence, Alex handoff, or real LLM smoke.
