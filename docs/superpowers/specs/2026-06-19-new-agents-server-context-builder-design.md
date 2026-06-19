# New Agents Server Context Builder Design

## Current State Gap Analysis

- P1 #6 requires replacing frontend-only history concatenation and moving toward a server-side context builder.
- Backend now persists runs, ordered messages, current artifacts, and exposes run snapshots.
- Frontend still builds the runtime prompt by concatenating local `chatHistory` in `llm.ts` for every request.
- For requests that already have `currentRunId`, the backend has a trustworthy ordered message source and can build the conversation context itself.
- Frontend attachments are still only available in the browser request payload, and previous-stage artifact injection still comes from `buildSystemPrompt`; those concerns stay outside this first slice.

## Chosen Design

Use the server builder only when a persisted run exists:

- Add backend `context_builder.py` to build a bounded runtime prompt from persisted messages plus the current user prompt.
- Exclude assistant control/error feedback from server context, matching the current frontend filtering behavior.
- Use explicit role labels (`[用户]`, `[助手]`) to preserve the current prompt shape.
- Add a conservative character budget and append a visible-in-prompt truncation notice when older context is dropped.
- Extend the stream persistence adapter with `build_runtime_prompt(run_id, current_prompt)`.
- `stream_agent_run_events` will use the server-built prompt only when persistence is enabled and a run has been ensured.
- Frontend `llm.ts` will send only the current user content when `currentRunId` exists, avoiding duplicate history injection.
- First-turn requests without `currentRunId` keep the existing frontend prompt path, so attachment handling and current behavior remain compatible.

## Alternatives Considered

- Move all prompt building to the server immediately: larger blast radius because attachments, stage artifacts, and frontend-only state would need new server contracts.
- Keep frontend history forever and only add backend snapshot APIs: preserves the current P1 #6 gap and keeps context policy split across clients.
- Server context for every request even before `runId`: impossible for the first turn because no persisted history exists yet.

## Requirements

- Backend context builder returns the current prompt unchanged when there is no prior usable message.
- Backend context builder includes prior persisted user/assistant messages in sequence order.
- Backend context builder filters assistant control/error feedback.
- Backend context builder truncates oldest context when over budget and includes a truncation notice.
- Stream service passes the server-built prompt to `runtime.stream_turn`.
- Frontend omits local chat history from `prompt` when `currentRunId` is present, while still sending attachment content and current user text.
- Existing first-turn behavior remains unchanged.

## Non-Goals

- No server-side attachment storage or extraction in this slice.
- No previous-stage artifact summarization migration in this slice.
- No generated summaries stored in the database yet.
- No visible UI warning for truncation yet; the notice is injected into the model prompt for this first backend context-builder slice.

## Verification

- Backend unit tests cover context builder ordering, filtering, and truncation.
- Backend stream tests prove persisted context is passed into runtime.
- Frontend llm tests prove `currentRunId` requests do not send local chat history.
- Existing backend/frontend focused tests remain green.
