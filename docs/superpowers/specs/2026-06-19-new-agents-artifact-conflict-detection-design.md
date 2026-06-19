# New Agents Artifact Conflict Detection Design

## Current State

- Manual artifact edits can be persisted through `POST /api/agent/runs/<run_id>/artifacts`.
- The endpoint writes a new artifact version without checking which version the user started editing from.
- In a restored session or multiple browser tabs, a stale edit can overwrite a newer server artifact version without warning.

## Gap

Users need a visible conflict guard so manual calibration does not silently overwrite a newer artifact version. The guard belongs in the shared Agent Runtime artifact update path, not in workflow-specific UI branches.

## Decision

Extend the shared artifact update contract with optional optimistic concurrency:

- Request body may include `expectedVersionNumber`.
- If provided, the server compares it with the current artifact version for the same run/stage.
- When they differ, the server returns HTTP `409` with a stable error message and the current artifact snapshot.
- The frontend service raises a typed conflict error.
- `ArtifactPane` sends the base version when it can infer it from the current run/stage history and keeps the edit draft open on conflict.

## Non-Goals

- No realtime collaboration, section locks, or merge editor in this slice.
- No automatic merge of conflicting Markdown.
