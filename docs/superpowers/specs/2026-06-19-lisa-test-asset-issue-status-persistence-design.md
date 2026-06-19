# Lisa Test Asset Issue Status Persistence Design

## Goal

Persist Lisa test asset issue triage status so issue review does not reset when the test asset modal closes or the collection is reloaded.

## Scope

This slice adds backend persistence and frontend API wiring for `assetIssues` status. It does not add a full asset center, issue assignment, comments, audit history, or workflow-level permissions.

Supported statuses:

- `pending`
- `confirmed`
- `ignored`

## Backend

- Add `status` to `AgentTestAssetIssue`, defaulting to `pending`.
- Include `id` and `status` when serializing `assetIssues`.
- Add `update_lisa_test_asset_issue_status(collection_id, issue_id, patch)` in `test_assets.py`.
- Add `PATCH /api/agent/test-assets/{collectionId}/issues/{issueId}`.
- Reject unknown collections, unknown issue ids within a collection, missing status, and unsupported status values.

## Frontend

- Add `TestAssetIssue` and `TestAssetIssueStatus` types.
- Parse `id` and `status` in `testAssetService`.
- Add `updateTestAssetIssueStatus(collectionId, issueId, status)`.
- In `Header`, issue buttons call the service and update the collection returned by the backend. If the backend call fails, show the existing test asset error area.

## Testing

- Backend test confirms materialized issues serialize `id/status=pending`.
- Backend test confirms issue status update persists and rejects invalid status.
- Frontend service test confirms PATCH endpoint and response parsing.
- Header test confirms clicking `确认问题` calls the service and updates the UI from the response.

## Self-Review

- This moves beyond local UI state without claiming a full issue management center.
- Existing test asset collection reads remain the source of truth after a server update.
- Invalid status fails explicitly.
