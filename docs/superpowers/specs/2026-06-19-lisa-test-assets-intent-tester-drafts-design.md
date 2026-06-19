# Lisa Test Assets Intent Tester Drafts Design

## Current State Gap Analysis

- P1 #7 requires Lisa test assets to support export to intent-tester or other test management tools without changing the intent-tester main path in the short term.
- `test-assets` already exports structured cases, coverage trace, coverage summary, asset issues, source version, and a derived risk matrix.
- There is still no intent-tester-shaped payload that can be reviewed and imported into `/api/testcases`.

## Chosen Design

Add `intentTesterDrafts` to `GET /api/agent/runs/{runId}/test-assets`. Each draft maps one Lisa test case to an intent-tester testcase creation payload:

- `sourceCaseId`
- `name`
- `description`
- `category`
- `priority`
- `tags`
- `steps`
- `draftWarnings`

The draft uses only valid intent-tester step actions. Because Lisa Markdown operation steps are natural language rather than executable MidScene selectors, the draft marks itself with a human-review warning and converts precondition, operation, test data, and expected result into `ai_assert` prompts. This is an import draft, not an automatic write into intent-tester.

## Requirements

- Each Lisa test case produces one draft.
- Priority maps `P0 -> 1`, `P1 -> 2`, `P2 -> 3`, unknown -> 3.
- Draft `category` comes from the Lisa test dimension.
- Draft `tags` include `lisa`, `new-agents`, source case id, priority, and risk when present.
- Draft steps use valid intent-tester action names and include precondition, operation/test data, and expected result prompts.
- No network call or database write to intent-tester happens in this slice.

## Verification

- Service tests assert draft payload shape and priority mapping.
- Endpoint tests assert the response includes the draft.
- Backend full tests and `git diff --check` pass.
