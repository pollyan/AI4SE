# New Agents Structured Streaming Design

## Goal

Restore real streaming feedback for the New Agents chat panel and artifact panel while keeping final model output strongly structured and validated.

## Requirements

- The first visible response must be fast. The backend should send an immediate SSE event once a run starts.
- The left assistant message and right artifact panel must update progressively during generation.
- The final persisted result must remain stable: PydanticAI structured output, Pydantic validation, and the existing business artifact contract remain authoritative.
- Partial streaming frames are drafts only. They may be incomplete and must not create artifact history entries, trigger stage transitions, or be treated as successful final output.
- Invalid final output must fail explicitly with the existing typed `error` SSE behavior.
- Do not restore the legacy `/api/chat/stream` endpoint or `<CHAT>/<ARTIFACT>` tag parsing.

## Architecture

The backend keeps `/api/agent/runs/stream` as the single Agent Runtime endpoint. It changes the runtime boundary from a synchronous `run_turn()` call to an iterable run that can produce draft frames before the final validated turn.

SSE gains two non-final event types:

- `run_started`: emitted before the model call starts so the frontend can show immediate generation feedback.
- `agent_delta`: emitted for partial structured output. It carries the current cumulative `chat`, optional cumulative artifact markdown, warnings, and stage action if available.

The existing `agent_turn` event remains the only final success event. It is emitted after the final output passes `validate_agent_turn()`. The existing `error` event remains the only failure event.

## Backend Data Flow

1. `routes.py` continues to parse the POST body and uses `build_sse_response(...)`.
2. `stream_services.py` builds the runtime and yields `RunStartedEvent`.
3. `PydanticAgentRuntime.stream_turn(...)` uses PydanticAI streaming when available.
4. Each partial structured output is converted to an `AgentTurnDeltaEvent` without business-contract enforcement.
5. The final output is validated with `validate_agent_turn(...)` and emitted as `AgentTurnEvent`.
6. Schema, model, contract, and request failures still map to typed `ErrorEvent`.

If the installed PydanticAI test double or runtime does not expose streaming, the runtime can still produce `run_started` followed by the final `agent_turn`; this preserves correctness while tests cover the streaming contract through a runtime double.

## Frontend Data Flow

1. `llm.ts` parses `run_started`, `agent_delta`, `agent_turn`, and `error`.
2. `run_started` yields a non-artifact stream chunk with a short in-progress assistant placeholder.
3. `agent_delta` yields draft chunks. Chat and artifact content are cumulative, so existing `chatService.ts` can update the last assistant message and artifact panel.
4. `agent_turn` yields the final chunk. Existing reducer logic then handles final artifact content and `NEXT_STAGE`.
5. `chatService.ts` records artifact history only after the stream completes successfully, so partial artifact frames are not persisted as versions.

## Error Handling

- Malformed SSE remains a protocol error.
- `error` events throw with their typed code and message.
- Partial frames with no visible content are ignored.
- Final bad Mermaid or final bad artifact contract still blocks the final update.
- If streaming fails after draft artifact updates, the existing chat service behavior marks the artifact as truncated.

## Testing

- Backend unit tests verify `run_started`, `agent_delta`, final `agent_turn`, and typed error mapping.
- Frontend parser tests verify the new events produce immediate placeholder chunks, draft UI chunks, and final chunks.
- Chat service tests verify progressive chunks update the assistant message and artifact panel before the stream completes.
- Existing hygiene tests continue to prevent legacy endpoint and tag protocol regressions.

## Out of Scope

- Token-level plain text parsing.
- A second model call for "fast text then structured cleanup".
- UI redesign beyond the existing progressive state updates.
