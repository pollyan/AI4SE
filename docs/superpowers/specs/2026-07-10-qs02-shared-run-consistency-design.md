# QS-02 Shared Run Consistency Design

## Context and outcome

`QS-02` owns `QG-003` and `QG-017`: a shared New Agents run must not report success, persist a normal artifact version, or leave either pane starved when its stream or persistence lifecycle is incomplete. All workflows stay on the shared `/api/agent/runs/stream` runtime and typed SSE contract.

## Invariants

1. Before a client renders its first renderable artifact for a run, it has rendered a non-placeholder progress frame; the two renders are separated by a visible asynchronous frame.
2. Chat and artifact updates are monotonic within a run. A locally synthesized artifact-first progress message is retained when the final natural-language summary arrives.
3. A client treats success as `agent_turn` followed by `[DONE]`; EOF after only deltas is a typed protocol failure, not normal completion or a version-save trigger.
4. Server persistence commits the durable outcome as one boundary. User message, assistant message, artifact version, and success metric must not leave a partial successful history if one write fails.
5. A retry of the same client-generated `(runId, requestId)` observes one durable run outcome; `requestId` is required at the API boundary and is never server-generated. Sequence and artifact-version conflicts are explicit, never `max + 1` races. The identity is a durable `Turn request`, not a `Run` or frontend cache key.

## First tracer-bullet decision

For artifact-first model output, the backend emits the truthful shared progress text `我正在整理当前输入并生成右侧结构化初稿，随后会同步关键结论。` alongside the partial artifact. The frontend is defensive for older or malformed valid deltas: it emits a chat-only progress frame before applying the first artifact and preserves that progress when the terminal chat arrives. This is intentionally shared-runtime behavior, not a Lisa/agent-specific path.

## Fault matrix and boundaries

| Boundary | Required verdict | Evidence owner |
|---|---|---|
| raw model token order (`artifact_data` before `chat`) | progress then artifact, both panes monotonic | backend runtime + frontend SSE tests |
| typed SSE EOF after delta | explicit protocol error; no normal local version | frontend parser/state test |
| persistence write failure | sanitized typed error; no partial durable success | backend stream/persistence fault injection |
| duplicate request / concurrent sequence or version write | one idempotent outcome or explicit conflict | persistence/API contract tests |

The durable `AgentRunTurnRequest` model is the idempotency ledger. It is uniquely keyed by `(run_id, request_id)`, records active/completed/failed state, and carries the serialized typed terminal event for replay. The first logical send includes a client-created run ID and request ID; a retry retains both, while the next logical send creates only a new request ID. A duplicate active request is an explicit retryable conflict; completed and failed requests replay the stored outcome without a model call.

## Non-goals

This slice does not introduce workflow-specific transports, change artifact semantics, call an external LLM judge, or redesign deployment. Judge quality remains `QS-06`; production-shaped infrastructure remains `QS-05`.
