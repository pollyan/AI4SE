# New Agents Contract Retry Metrics Design

## Context

`agent_run_turn_metrics.contract_retry_count` exists, but `stream_services.py` currently records `0` for every turn. `docs/todos/new-agents-evolution.md` #12 still lists real contract retry count collection as missing. PydanticAI surfaces exhausted structured output retries through errors such as `Exceeded maximum output retries (3)`, which is the first available runtime signal for failed schema/contract retry attempts.

## Goal

Record the retry count from exhausted PydanticAI structured output errors into Agent Runtime turn metrics.

## Scope

- Parse retry counts from schema error messages matching `Exceeded maximum output retries (N)`.
- Pass the parsed count into `_record_turn_metric` for `SCHEMA_VALIDATION_FAILED` paths.
- Keep successful turns and non-retry errors unchanged.
- Keep database schema and observability response schema unchanged.

## Non-Goals

- No provider token usage extraction.
- No per-attempt trace table.
- No frontend UI changes; the existing `contractRetryCount` field in recent turns will show the recorded value.
- No change to retry policy.

## Design

Add a small helper in `stream_services.py` that extracts an integer retry count from an exception message. The helper returns `0` when no exhausted retry count is present. In the `AgentRuntimeSchemaError` and PydanticAI schema error handlers, pass the parsed count to `record_metric`.

This is intentionally narrow: it records the true exhausted retry count when the runtime exposes it, and keeps all other turns at zero until richer runtime attempt tracing exists.

## Testing

Add a backend stream service test where `runtime.stream_turn` raises `AgentRuntimeSchemaError("Exceeded maximum output retries (3)")`. The emitted error remains `SCHEMA_VALIDATION_FAILED`, and the recorded metric has `contract_retry_count == 3`.

## Acceptance

- Schema retry exhaustion records a non-zero `contract_retry_count`.
- Existing model error and success metric tests remain unchanged.
- Focused stream service tests pass.
