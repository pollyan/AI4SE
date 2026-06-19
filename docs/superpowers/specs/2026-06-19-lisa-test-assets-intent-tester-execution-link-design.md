# Lisa Test Assets Intent-Tester Execution Link Design

## Goal

After a Lisa test asset draft is imported into intent-tester, expose a clear handoff from New Agents to the intent-tester execution page for that created test case.

## Scope

- Frontend only.
- Do not call the execution API from New Agents.
- Link to the existing intent-tester execution UI at `/intent-tester/execution?testcase_id=<id>`, which already reads the query parameter and preselects the test case.

## Behavior

For any test case imported during the current test assets modal session, the card continues to show `已导入 intent-tester #<id>` and also shows a `去执行 #<id>` link. The link opens in a new tab and uses `rel="noreferrer"` so New Agents does not retain cross-app window access.

## Testing

Extend the existing Header import test to assert that the execution handoff link appears with the expected href after a successful import.
