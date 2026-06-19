# New Agents SSE Persistence Design

## Current State Gap Analysis

- `agent_runs`、`agent_messages`、`agent_artifacts` 和 `agent_artifact_versions` 模型以及 `run_persistence.py` repository 已存在，但 `/api/agent/runs/stream` 仍未写入任何服务端会话轨迹。
- `stream_services.py` 是纯 generator，现有单元测试不依赖 Flask app context。直接把数据库写入硬编码到 service 会让测试和运行时上下文耦合。
- `workflow_manifest.json` 已包含 workflow 到 `agentId` 的归属，后端不应再硬编码一份 Lisa/Alex 映射。
- typed SSE 主链路必须保持单一路径，不新增 Lisa/Alex 专属路径，也不新增与 `/api/agent/runs/stream` 并行的持久化 stream。

## Chosen Design

Use a small optional persistence adapter:

- `stream_agent_run_events(..., persistence=None)` keeps current pure behavior when no adapter is supplied.
- The Flask route supplies a real adapter that uses `run_persistence.py`.
- The adapter creates a run when the request has no `runId`, or validates/reuses an existing run when `runId` is supplied.
- `RunStartedEvent` gains optional `runId`; existing consumers can ignore it, while future frontend migration can retain it.
- The user prompt is recorded as a `user` message before runtime generation.
- The final `AgentTurnOutput.chat` is recorded as an `assistant` message.
- A final `artifact_update.type="replace"` records a new artifact version for the current stage.

## Alternatives Considered

- Route-only wrapper around the generator: simpler, but hard to persist final output without duplicating stream logic.
- A new persistence endpoint: easier to isolate, but violates the typed SSE single-main-path constraint and creates frontend coordination risk.
- Direct database writes inside `stream_services.py`: minimal code, but makes service tests require app context and database setup.

## Requirements

- Existing requests without `runId` remain valid.
- Requests may include nonblank `runId`; blank `runId` is rejected.
- `run_started` emits the canonical `runId` for both new and reused runs.
- Endpoint tests prove a successful stream creates one run, one user message, one assistant message, and one current artifact version.
- Stream service tests prove persistence adapter calls happen without requiring a real database.
- Existing typed SSE event parsing remains backward compatible.

## Non-Goals

- No frontend storage migration in this slice.
- No run resume/list/detail REST endpoints in this slice.
- No context builder or summarization in this slice.
- No multi-user access control in this slice.

## Verification

- Request schema tests cover optional `runId` parsing and blank rejection.
- SSE encoder/schema tests cover `run_started` with `runId`.
- Stream service tests cover adapter call order.
- Endpoint tests cover actual database side effects.
- Backend test suite remains green.
