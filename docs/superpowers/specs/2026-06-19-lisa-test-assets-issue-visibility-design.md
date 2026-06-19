# Lisa Test Assets Issue Visibility Design

## Goal

Show Lisa test asset quality issues in the existing test assets modal so users can see parser-detected review gaps before editing or importing cases.

## Scope

- Frontend only.
- Read-only issue display. Do not add issue status transitions until backend persistence for reviewed/resolved states is designed.
- Reuse `TestAssetCollection.assetIssues`.

## Behavior

When `assetIssues` is non-empty, the modal shows an `资产问题` section in the side panel with the issue count and each issue message. If an issue includes `caseId` or `testPoint`, those references appear as compact metadata.

When there are no issues, the side panel keeps the existing edit placeholder and does not add extra empty-state text.

## Testing

Add a Header component test with a materialized collection containing an orphan test case issue and assert that `资产问题`, the issue count, message, and case ID are visible.
