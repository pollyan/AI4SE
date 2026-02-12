# Story 1.2: Expand Diff Coverage to All Artifact Types

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a Product Owner,
I want inline diff support for all text fields across Features, Assumptions, and Scoping sections,
So that I have a consistent review experience regardless of which part of the document changed.

## Acceptance Criteria

1. **Backend `_prev` Generation**: The backend correctly generates `_prev` values for all modified text fields within nested structures for `Features` (`name`, `desc`, `priority`) and `Assumptions` (`question`, `note`, `priority`).
2. **Frontend `DiffField` Integration**: The Frontend renders `DiffField` components for all corresponding UI elements in `StructuredRequirementView.tsx`.
3. **Graceful Fallback**: Unsupported fields (like Mermaid diagrams) continue to render the current value without crashing or attempting to render text diffs.
4. **Added Item Highlighting**: `added` items (newly created entries) are highlighted with a green background (`.diff-inserted` block style) via the global CSS classes.
5. **Scope/OutScope Handling**: For `scope` and `out_of_scope` lists (string arrays), if schema migration is not performed, ensure they at least display the new values correctly. If schema allows, support added/modified highlighting (See Dev Notes).

## Tasks / Subtasks

- [x] Task 1: Backend Support for Nested Types
  - [x] Verify `artifact_patch.py` -> `_merge_lists` correctly recurses and generates `_prev` for `FeatureItem` and `AssumptionItem` structures.
  - [x] Add unit tests in `test_artifact_patch.py` to cover nested updates in Features and Assumptions.
  - [x] Investigate `scope` list handling: If primitives cannot be tracked for diffs, log decision and ensure partial updates don't break.

- [x] Task 2: Frontend Integration for Features
  - [x] Update `StructuredRequirementView.tsx` to use `DiffField` for `FeatureItem.name`
  - [x] Update `StructuredRequirementView.tsx` to use `DiffField` for `FeatureItem.priority`
  - [x] Update `StructuredRequirementView.tsx` to use `DiffField` for `FeatureItem.acceptance` (List of strings? Might need `DiffField` loop or just block diff)

- [x] Task 3: Frontend Integration for Assumptions
  - [x] Update `StructuredRequirementView.tsx` to use `DiffField` for `AssumptionItem.question`
  - [x] Update `StructuredRequirementView.tsx` to use `DiffField` for `AssumptionItem.note`
  - [x] Update `StructuredRequirementView.tsx` to use `DiffField` for `AssumptionItem.priority`

- [x] Task 4: Frontend Scope Handling
  - [x] Review `scope` rendering. Since it is a string list `scope: string[]`, we cannot easily attach `_prev` to individual strings without object wrappers.
  - [x] Implement decision: Either wrap scope items in objects (schema change) or accept that Scale/Scope only shows current state for now. (Recommended: Keep simple for this story, maybe just highlight if *list* length changes? Or skip specific scope diffs).

- [x] Task 5: Verification
  - [x] Verify `flow_mermaid` and other non-text fields are untouched/safe.
  - [x] Run backend tests.
  - [x] Run frontend component tests.

## Dev Notes

- **DiffField Usage**: `<DiffField value={item.field} oldValue={item._prev?.field} />`
- **Scope List Complexity**: `scope` is `string[]`. `_merge_lists` in backend treats primitive lists as "replace". To get diffs, we'd need `id`s. For now, accepting that `scope` might not have fine-grained inline diffs is acceptable for MVP unless we refactor schema to `ScopeItem { id, text }`. **Decision**: Do not change schema in this story. Skip inline diffs for `scope` items, only full list replacement behavior is expected.
- **Feature Acceptance Criteria**: `acceptance` is `string[]`. Same issue as scope. Stick to rendering list as-is or investigate if we can diff the *whole list text*.
- **Priority Fields**: `priority` is P0/P1. `DiffField` works on strings, so it's fine.

### Project Structure Notes

- Backend: `tools/ai-agents/backend/agents/lisa/artifact_patch.py`
- Frontend: `tools/ai-agents/frontend/src/components/artifact/StructuredRequirementView.tsx`

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic 1: Complete Inline Diff Implementation (End-to-End)]
- [Source: _bmad-output/planning-artifacts/architecture.md#Architecture Decision Document]

## Dev Agent Record

### Agent Model Used

Antigravity (simulated)

### Debug Log References

### Completion Notes List

- Backend Support for Nested Types verified with new tests. `artifact_patch.py` handles recursive updates correctly.
- Created tests: `test_nested_feature_update_prev`, `test_nested_assumption_update_prev`.
- Frontend Integration for Features and Assumptions complete. `StructuredRequirementView` uses `DiffField` for relevant fields.
- Verified with new frontend tests: `renders inline diff for Feature fields` and `renders inline diff for Assumption fields`.
- Task 4 (Scope Handling) completed: Verified that `scope` and `out_of_scope` lists render correctly. No inline diffs implemented for primitive string lists as per decision to maintain schema stability. Added regression test `renders scope and out_of_scope correctly`.
- Final Verification complete:
  - Backend tests passed: 13 passed in `test_artifact_patch.py`.
  - Frontend `DiffField` tests passed: 7 passed.
  - Frontend `StructuredRequirementView` tests passed: 8 passed.
  - `flow_mermaid` rendering verified safe (no diff logic applied).

### File List

- tools/ai-agents/backend/agents/lisa/artifact_patch.py
- tools/ai-agents/backend/tests/test_artifact_patch.py
- tools/ai-agents/frontend/src/components/artifact/StructuredRequirementView.tsx
- tools/ai-agents/frontend/src/components/common/DiffField.tsx
- tools/ai-agents/frontend/src/components/common/__tests__/DiffField.test.tsx
- tools/ai-agents/frontend/src/components/artifact/__tests__/StructuredRequirementView.test.tsx
- tools/ai-agents/frontend/src/types/artifact.ts
- tools/ai-agents/frontend/index.css
- tools/ai-agents/frontend/package.json
