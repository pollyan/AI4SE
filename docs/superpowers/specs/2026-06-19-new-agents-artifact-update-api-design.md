# New Agents Artifact Update API Design

## Current State

- `record_artifact_version(run_id, stage_id, content)` already creates versioned artifacts and updates artifact-derived context summaries.
- `GET /api/agent/runs/<run_id>` already returns artifact snapshots.
- `ArtifactPane` supports local manual edits, but those edits are not yet persisted back to the server run snapshot.

## Gap

Manual artifact calibration should become a persisted run-level action so that later reloads, context summaries, and collaboration flows can observe the edited artifact version.

## Decision

Add a shared Agent Runtime endpoint:

- `POST /api/agent/runs/<run_id>/artifacts`
- Request body: `{ "stageId": string, "content": string }`
- Response body: `{ "stageId": string, "content": string, "versionNumber": number }`

The endpoint reuses `record_artifact_version` so artifact history, current artifact snapshot, and derived context summaries stay consistent. It is intentionally workflow-neutral and must not add Lisa/Alex-specific branches.

## Non-Goals

- No section lock, comment, accept/reject, share, or permission workflow in this slice.
- No UI save wiring in this slice; the frontend service boundary is prepared first so the next slice can connect `ArtifactPane` with clear tests.
