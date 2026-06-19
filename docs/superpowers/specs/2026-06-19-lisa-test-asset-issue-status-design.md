# Lisa Test Asset Issue Status Design

## Goal

Add the first issue status flow for Lisa test assets so reviewers can triage exported asset quality issues instead of only reading a static list.

## Scope

This slice is frontend-only. The Lisa test asset modal will let users mark each exported asset issue as:

- `待处理`
- `已确认`
- `忽略`

The status is local to the currently opened modal and resets when test assets are reloaded. This avoids pretending that issue status is persisted while still improving the review workflow. Backend persistence remains a later slice.

## UI Behavior

- Each issue starts as `待处理`.
- The issue counter shows both total issues and pending issues.
- Each issue row shows the current status.
- Each issue row has two actions:
  - `确认问题` sets status to `已确认`.
  - `忽略问题` sets status to `忽略`.
- Once a status is selected, the status label changes immediately and the pending count updates.

## Architecture

- Keep the state in `Header.tsx` because the test asset modal is currently implemented there.
- Derive a stable issue key from issue type, case id, test point, message, and index.
- Store `issueStatuses` as `Record<string, 'pending' | 'confirmed' | 'ignored'>`.
- Reset `issueStatuses` whenever the test asset modal opens and when assets load.

## Testing

Update `tools/new-agents/frontend/src/components/__tests__/Header.test.tsx`:

- Load a collection with one issue.
- Assert the modal shows `1 个问题 · 1 待处理`.
- Click `确认问题`.
- Assert the issue shows `已确认` and the counter shows `1 个问题 · 0 待处理`.
- Click `忽略问题`.
- Assert the issue shows `忽略`.

## Self-Review

- The design does not claim persistence.
- It directly advances the todo item about issue status flow.
- It keeps the change inside the existing modal and test surface.
