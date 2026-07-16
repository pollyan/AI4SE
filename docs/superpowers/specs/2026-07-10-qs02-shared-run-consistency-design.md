# QS-02 Shared Run Consistency Design

> 历史状态说明（2026-07-16）：本文记录 QS-02 当时的 run 一致性设计。其“合成固定进度话术后展示 artifact”只是旧的局部缓解，未完成 QG-017，现已由 [`2026-07-16-qg017-chat-before-artifact-design.md`](2026-07-16-qg017-chat-before-artifact-design.md) 的“有意义自然对话先行”共享契约取代。本文不再是 QG-017 的当前实现依据。

## Context and outcome

`QS-02` owns `QG-003`. It also introduced a historical partial mitigation for the then-open `QG-017`: a shared New Agents run must not report success, persist a normal artifact version, or leave either pane starved when its stream or persistence lifecycle is incomplete. All workflows stay on the shared `/api/agent/runs/stream` runtime and typed SSE contract.

## Invariants

1. Historical QS-02 invariant: before a client rendered its first artifact, it rendered a truthful local progress frame. Current QG-017 strengthens this to a model-produced, meaningful natural dialogue frame.
2. Chat and artifact updates remain monotonic within a run. The historical locally synthesized artifact-first message is no longer a valid substitute for final natural dialogue.
3. A client treats success as `agent_turn` followed by `[DONE]`; EOF after only deltas is a typed protocol failure, not normal completion or a version-save trigger.
4. Server persistence commits the durable outcome as one boundary. User message, assistant message, artifact version, and success metric must not leave a partial successful history if one write fails.
5. A retry of the same client-generated `(runId, requestId)` observes one durable run outcome; `requestId` is required at the API boundary and is never server-generated. Sequence and artifact-version conflicts are explicit, never `max + 1` races. The identity is a durable `Turn request`, not a `Run` or frontend cache key.

## First tracer-bullet decision

The original QS-02 tracer bullet emitted the shared progress text `我正在整理当前输入并生成右侧结构化初稿，随后会同步关键结论。` for artifact-first model output. That behavior is retained here only as historical context. QG-017 now rejects that fixed text as a successful final chat, buffers artifact-first deltas at the shared service boundary, and releases the first artifact only after actual natural dialogue; the frontend keeps an equivalent defensive boundary for historical streams.

## Fault matrix and boundaries

| Boundary | Required verdict | Evidence owner |
|---|---|---|
| raw model token order (`artifact_data` before `chat`) | historical QS-02: fixed progress then artifact; current QG-017: buffer artifact until natural dialogue, then keep both panes monotonic | backend stream sequencer + frontend SSE tests |
| typed SSE EOF after delta | explicit protocol error; no normal local version | frontend parser/state test |
| persistence write failure | sanitized typed error; no partial durable success | backend stream/persistence fault injection |
| duplicate request / concurrent sequence or version write | one idempotent outcome or explicit conflict | persistence/API contract tests |

The durable `AgentRunTurnRequest` model is the idempotency ledger. It is uniquely keyed by `(run_id, request_id)`, records active/completed/failed state, and carries the serialized typed terminal event for replay. The first logical send includes a client-created run ID and request ID; a retry retains both, while the next logical send creates only a new request ID. A duplicate active request is an explicit retryable conflict; completed and failed requests replay the stored outcome without a model call.

## Non-goals

This slice does not introduce workflow-specific transports, change artifact semantics, call an external LLM judge, or redesign deployment. Judge quality remains `QS-06`; production-shaped infrastructure remains `QS-05`.
