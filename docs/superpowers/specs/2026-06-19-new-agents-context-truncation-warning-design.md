# New Agents Context Truncation Warning Design

## Current State Gap Analysis

- Backend `context_builder.py` can truncate persisted run history and inject a truncation notice into the model prompt.
- Users currently cannot see that this truncation happened unless the model chooses to mention it.
- Frontend already has an artifact truncation banner, but context truncation is different: the artifact may be complete while the model saw only recent conversation history.
- Typed SSE already starts every stream with `run_started`, which is the right place to expose pre-runtime metadata without changing `agent_turn`.

## Chosen Design

- `context_builder.py` returns both the runtime prompt and warning codes.
- When prior context is truncated, the warning code is `context_truncated`.
- `stream_services.py` passes these warnings in `RunStartedEvent`.
- Frontend parses optional `run_started.warnings`.
- If `context_truncated` is present, the initial left-chat chunk says the assistant is generating and that older conversation context was truncated.

## Requirements

- No truncation keeps `run_started` compatible with existing consumers.
- Truncation emits `run_started.warnings=["context_truncated"]`.
- Frontend shows a visible chat message for context truncation.
- Artifact truncation behavior remains unchanged.

## Non-Goals

- No artifact truncation banner reuse for context truncation.
- No persisted summary table in this slice.
- No UI panel for context window diagnostics.

## Verification

- Backend context builder tests cover warning emission.
- Backend stream tests cover `RunStartedEvent` warnings.
- Frontend llm tests cover visible first chunk when `run_started.warnings` contains `context_truncated`.
