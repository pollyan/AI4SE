# New Agents Artifact Conflict Detection Plan

## Scope

Add optimistic conflict detection to manual artifact saves.

## Steps

1. Add failing backend tests for `expectedVersionNumber` conflict and successful guarded update.
2. Add failing frontend service tests for sending `expectedVersionNumber` and raising a conflict error on HTTP 409.
3. Add failing `ArtifactPane` test proving conflicts keep the draft open and leave artifact state unchanged.
4. Implement backend validation and conflict response.
5. Implement frontend service conflict parsing and ArtifactPane base-version inference.
6. Run targeted backend/frontend tests, build, and `git diff --check`.
