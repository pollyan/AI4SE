# Story 1.3: Transient State Management & Cleanup

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a User,
I want diff markings to disappear after I proceed to the next round of conversation except for new additions or changes,
so that the interface remains clean and I don't see stale changes from previous turns.

## Acceptance Criteria

1.  **Backend Verification**: In `artifact_patch.py`, `_merge_lists` explicitly clears `_diff` and `_prev` from *original* items at start of processing.
2.  **No `_diff` on Unchanged Items**: If `patch` does not touch an item in a subsequent turn, `_diff` tags are removed from the result.
3.  **Frontend Update**: `StructuredRequirementView` re-renders with clean data when backend response omits `_diff` fields (no red lines/green background).
4.  **Regression**: Existing diff functionality (added/modified) still works for *new* changes in the current turn.

## Tasks / Subtasks

- [x] Task 1: Backend Implementation Verification
  - [x] Review `artifact_patch.py` -> `_merge_lists` logic for clearing `_diff` and `_prev`.
  - [x] Add explicit test case `test_transient_diff_cleanup` in `test_artifact_patch.py` simulating a two-step update (Init -> Mod -> NoChange).
  - [x] Ensure non-list nested structures (if any support diff) also clear tags.

- [x] Task 2: Frontend Verification
  - [x] Add test case in `StructuredRequirementView.test.tsx` simulating a "Turn 2" where an item clearly lacks `_diff`/`_prev` data and renders normally.
  - [x] Verify no lingering CSS classes or stale `oldValue` props.

- [x] Task 3: Regression Testing
  - [x] Run all backend and frontend tests to ensure normal diff functionality is intact.

## Dev Notes

- **Backend Logic**: The `_merge_lists` function already has logic: `item.pop("_diff", None); item.pop("_prev", None)`. This task is primarily about formal verification through tests to prevent regression.
- **Frontend Logic**: Frontend is purely driven by props. If backend sends clean data (no `_diff`/`_prev`), frontend renders clean text. No state retention issue expected unless we introduce local state in `DiffField` (currently it uses `useMemo` dependent on props).

### Project Structure Notes

- Backend: `tools/ai-agents/backend/agents/lisa/artifact_patch.py`
- Frontend: `tools/ai-agents/frontend/src/components/artifact/StructuredRequirementView.tsx`

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.3]
- [Source: _bmad-output/planning-artifacts/architecture.md#Cross-Cutting Concerns]

## Dev Agent Record

### Agent Model Used

Antigravity (simulated)

### Debug Log References

### Completion Notes List

### File List
- tools/ai-agents/backend/tests/test_artifact_patch.py
- tools/ai-agents/frontend/src/components/artifact/__tests__/StructuredRequirementView.test.tsx
- tools/ai-agents/backend/agents/lisa/artifact_patch.py
- tools/ai-agents/frontend/src/components/artifact/StructuredRequirementView.tsx
