# Lisa Test Assets Risk Matrix Visibility Design

## Goal

Expose the existing Lisa `riskMatrix` data in the test assets modal so users can inspect which risks are covered by which test cases and test points before importing or editing cases.

## Scope

- Frontend only.
- Read-only display of `TestAssetCollection.riskMatrix`.
- No independent risk library, risk lifecycle editing, or persistence changes in this slice.

## Behavior

When a materialized test asset collection contains `riskMatrix` entries, the right side panel shows a `风险矩阵` section. Each risk entry displays the risk ID/name, associated test cases, test points, priorities, and coverage statuses. The section is hidden when no risk matrix entries exist.

## Testing

Add a Header component test with one risk matrix entry and assert that the modal renders `风险矩阵`, the risk, associated case, test point, priority, and coverage status.
