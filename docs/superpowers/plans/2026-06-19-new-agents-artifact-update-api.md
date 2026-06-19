# New Agents Artifact Update API Plan

## Scope

Persist manual artifact edits as first-class artifact versions in the existing shared run snapshot model.

## Steps

1. Add failing backend endpoint tests for artifact update persistence, invalid stage, and blank content.
2. Add failing frontend service tests for `updateRunArtifact` request/response parsing.
3. Implement a workflow-neutral persistence helper and Flask route.
4. Implement the frontend service wrapper.
5. Run targeted backend/frontend tests, build, and `git diff --check`.
6. Update `docs/todos/new-agents-ux-professionalization.md` with progress and remaining UI wiring work.
