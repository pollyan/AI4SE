# Lisa Test Assets Test Point Coverage Visibility Design

## Goal

Expose Lisa test point coverage details in the test assets modal so users can see which test points are covered, partially covered, or uncovered.

## Scope

- Frontend only.
- Read-only display of `TestAssetCollection.testPoints`.
- No independent test point library, editing, or status workflow in this slice.

## Behavior

When a materialized test asset collection contains `testPoints`, the right side panel shows a `测试点覆盖` section. Each row displays the test point, status, priority, risk, and covered case IDs. The section is hidden when no test point entries exist.

## Testing

Add a Header component test with one uncovered test point and assert that `测试点覆盖`, the test point, status, priority, risk, and covered case placeholder are visible.
