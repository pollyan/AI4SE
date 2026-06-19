# Lisa Test Assets Batch Intent-Tester Import Design

## Goal

Add a manual batch import action in the Lisa test assets modal so reviewed `intentTesterDrafts` can be written to intent-tester together without changing the shared Agent Runtime or intent-tester's main workflow.

## Scope

- Frontend only.
- Reuse the existing `importIntentTesterDraft` service and `/intent-tester/api/testcases` payload contract.
- Keep import user-triggered. Do not automatically write drafts when assets are opened or materialized.
- Skip drafts that have already been imported during the current modal session.

## UI Behavior

When a materialized test asset collection has at least one `intentTesterDrafts` item, the modal shows a batch import button near the coverage summary. Clicking it imports every draft whose `sourceCaseId` is not already present in the current imported case map. On success, the modal displays the number of imported cases and each affected test case card shows the created intent-tester ID.

If no draft remains to import, the modal shows a non-error summary message. If any import request fails, the modal shows the existing error area with a batch import failure message and does not mark unconfirmed cases as imported.

## Testing

Extend `Header.test.tsx` with a two-case collection and assert that clicking the batch import action calls `importIntentTesterDraft` for both drafts and renders the batch success summary plus per-case imported IDs.
