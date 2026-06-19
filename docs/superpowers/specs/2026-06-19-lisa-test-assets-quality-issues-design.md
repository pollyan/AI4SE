# Lisa Test Assets Quality Issues Design

## Current State Gap Analysis

- Lisa test assets export already returns structured test cases, coverage trace, source version, and coverage summary.
- The export still treats internally inconsistent assets as if they were clean. For example, coverage trace may reference a missing test case ID, or a test case may not be referenced by any test point.
- Full asset editing and version management remain later work, but surfacing quality issues now makes the exported assets more auditable.

## Chosen Design

Add `assetIssues` to the export payload. It is a deterministic list of warning objects:

- `unknown_coverage_case`: coverage trace references a test case ID that is not present in `testCases`.
- `orphan_test_case`: a test case exists but no coverage trace row references it.

These are non-fatal quality issues. The endpoint still returns 200 when parsing succeeds.

## Requirements

- `assetIssues` must be present even when empty.
- Unknown referenced case IDs must include the affected test point and missing ID.
- Orphan test cases must include the orphan case ID.
- Existing fail-fast behavior for missing CASES artifact and malformed tables remains unchanged.

## Verification

- Service tests cover clean assets and assets with both issue types.
- Endpoint test covers `assetIssues` in the response.
- Backend full tests and `git diff --check` pass.
