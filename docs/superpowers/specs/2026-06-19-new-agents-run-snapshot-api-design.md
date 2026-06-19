# New Agents Run Snapshot API Design

## Current State Gap Analysis

- Backend now persists stream turns into run/message/artifact version tables.
- `run_persistence.get_run_snapshot(run_id)` already returns a deterministic snapshot for tests and future consumers.
- No HTTP API exposes this snapshot, so frontend restore, audit tooling, sharing, and LLM judge data collection still need direct database access or browser traces.

## Chosen Design

- Add `GET /api/agent/runs/<runId>` to return the existing repository snapshot.
- The endpoint is read-only and does not require default LLM config because it does not call a model.
- Unknown `runId` returns JSON 404: `{"error": "未知 runId: <id>"}`.
- The response shape is exactly the repository snapshot:
  - `run`
  - `messages`
  - `artifacts`

## Requirements

- Existing persisted stream runs can be fetched by `runId`.
- Snapshot messages are ordered by `sequenceIndex`.
- Snapshot artifacts expose current artifact content and version number.
- Unknown run IDs return JSON 404, not HTML 500.

## Non-Goals

- No list endpoint.
- No share-token or permission model.
- No frontend restore UI in this slice.
- No write/update endpoint outside the typed SSE path.

## Verification

- Endpoint tests create a stream run and fetch its snapshot.
- Endpoint tests cover unknown run ID 404.
- Backend test suite remains green.
