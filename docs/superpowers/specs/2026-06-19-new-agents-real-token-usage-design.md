# New Agents Real Token Usage Design

## Context

`docs/todos/new-agents-evolution.md` #12 still lists real token usage collection as missing. The current metric pipeline records `estimated_tokens` with a character-count heuristic in `stream_services.py`. New Agents raw streaming uses `llm_client.stream_chat_completion_content()`, which calls OpenAI-compatible chat completions with `stream=True` but does not request or capture streamed usage.

## Goal

Capture provider-reported `total_tokens` for raw OpenAI-compatible streaming turns when the provider returns usage, and use it for `agent_run_turn_metrics.estimated_tokens`.

## Scope

- Add an optional usage callback to `stream_chat_completion_content()`.
- When a usage callback is supplied, request `stream_options={"include_usage": True}`.
- Extract `usage.total_tokens` from streamed chunks that expose usage.
- Store the latest usage value on `PydanticAgentRuntime.last_token_usage` during raw streaming.
- Make `stream_services.py` prefer `runtime.last_token_usage` over the character-count estimate when recording success metrics.
- Keep the existing metric field name `estimated_tokens` and API field `estimatedTokens` for schema compatibility; the value can now be provider-reported.

## Non-Goals

- No database schema migration for separate prompt/completion/total token fields.
- No token usage capture for PydanticAI non-raw streaming until that runtime exposes usage through a stable API.
- No frontend schema changes.
- No retry or billing UI changes.

## Design

`llm_client.stream_chat_completion_content()` keeps returning `Iterator[str]` for compatibility. It accepts `on_usage: Callable[[int], None] | None = None`. If supplied, the OpenAI request includes `stream_options={"include_usage": True}`. During iteration, chunks are still parsed for delta content as before. Separately, a helper checks whether the chunk has `usage.total_tokens`; when present and an integer, it calls `on_usage(total_tokens)`.

`PydanticAgentRuntime` initializes `last_token_usage` to `None`. Raw streaming resets it at the start of each turn and passes a small callback into `stream_chat_completion_content()`. The callback stores the latest `total_tokens`.

`stream_services.py` adds an optional `actual_token_count` path to metric recording. Successful turns use `runtime.last_token_usage` if it is a non-negative integer; otherwise they keep using `_estimated_tokens(input_chars, output_chars)`.

## Testing

- `test_llm_client.py` verifies that an `on_usage` callback causes `stream_options={"include_usage": True}` and receives `usage.total_tokens` from a stream chunk.
- `test_agent_runtime.py` verifies raw streaming stores `last_token_usage`.
- `test_stream_services.py` verifies success metric recording uses `runtime.last_token_usage` instead of the character estimate.

## Acceptance

- Existing string-only callers continue to call chat completions without `stream_options`.
- Raw streaming turns can record provider-reported total tokens.
- Missing usage gracefully falls back to the existing estimate.
