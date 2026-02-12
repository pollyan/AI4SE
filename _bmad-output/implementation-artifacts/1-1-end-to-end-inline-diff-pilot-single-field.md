# Story 1.1: End-to-End Inline Diff Pilot (Single Field)

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a Product Owner reviewing AI updates,
I want to see character-level inline diffs (red strikethrough/green highlight) for the `desc` field of Rules,
so that I can precisely identify minor wording changes without reading the old and new text separately.

## Acceptance Criteria

1. **Given** an existing Rule with `desc: "User must login."`
   **When** the AI updates the rule to `desc: "User must login via SSO."`
   **Then** the backend response includes `_prev: { desc: "User must login." }` for that rule

2. **And** the Frontend `StructuredRequirementView` renders the `desc` field as: `User must login <ins>via SSO</ins>.` (using `fast-diff` logic)

3. **And** unchanged parts of the text have no styling

4. **And** `fast-diff` is installed as a project dependency

## Tasks / Subtasks

- [x] Task 1: Frontend Dependency Setup
  - [x] Install `fast-diff` in `tools/ai-agents/frontend`
  - [x] Add global CSS styles for `.diff-inserted` (green bg) and `.diff-deleted` (red strikethrough) in `tools/ai-agents/frontend/index.css`

- [x] Task 2: Backend `_prev` Injection Logic
  - [x] Modify `tools/ai-agents/backend/agents/lisa/artifact_patch.py` -> `_merge_lists`
  - [x] Implement logic to detect field changes and store old value in `_prev` dict
  - [x] Ensure `_prev` is only added when actual content changes
  - [x] Add unit tests in `test_artifact_patch.py` covering nested dict updates

- [x] Task 3: `DiffField` Component Implementation
  - [x] Create `tools/ai-agents/frontend/src/components/common/DiffField.tsx`
  - [x] Implement `fast-diff` usage: map diff tuples to HTML spans
  - [x] Handle error cases (defensive programming)
  - [x] Add unit tests `DiffField.test.tsx`

- [x] Task 4: Integration
  - [x] Update `StructuredRequirementView.tsx` to pass `_prev.desc` to `DiffField` for Rule items
  - [x] Verify end-to-end rendering with mock data

## Dev Notes

- **Backend Logic**:
  - `_merge_lists` currently handles `_diff` status. You need to extend it to compare `old_item` and `new_item` fields.
  - If `new_item[field] != old_item[field]`, set `new_item.setdefault("_prev", {})[field] = old_item[field]`.

- **Frontend Logic**:
  - `fast-diff` returns arrays like `[[0, "Unchanged"], [-1, "Deleted"], [1, "Inserted"]]`.
  - -1 -> `<span class="diff-deleted">Deleted</span>`
  - 1 -> `<span class="diff-inserted">Inserted</span>`
  - 0 -> `<span>Unchanged</span>`
  - **Security**: Be careful with `dangerouslySetInnerHTML` if you use it. For MVP, rendering plain text diffs is fine, but if input is trusted (it comes from our backend), basic sanitization is recommended.

### Project Structure Notes

- **Backend**: `tools/ai-agents/backend/agents/lisa/`
- **Frontend**: `tools/ai-agents/frontend/src/components/`

### References

- [Architecture: Core Decisions](_bmad-output/planning-artifacts/architecture.md#core-architectural-decisions)
- [Architecture: Implementation Patterns](_bmad-output/planning-artifacts/architecture.md#implementation-patterns-consistency-rules)

## Dev Agent Record

### Agent Model Used

Antigravity (simulating Dev Agent Context preparation)

### Debug Log References

- None

### Completion Notes List

- Ready for implementation.
- implemented `_prev` logic in `artifact_patch.py` with tests.
- Created `DiffField` component with tests.
- Updated `StructuredRequirementView` to use `DiffField` for rules.
- Added `_prev` to artifact types.
- Verified all tests pass.

### File List
- tools/ai-agents/backend/agents/lisa/artifact_patch.py
- tools/ai-agents/backend/tests/test_artifact_patch.py
- tools/ai-agents/frontend/package.json
- tools/ai-agents/frontend/index.css
- tools/ai-agents/frontend/src/components/common/DiffField.tsx
- tools/ai-agents/frontend/src/components/common/__tests__/DiffField.test.tsx
- tools/ai-agents/frontend/src/components/artifact/StructuredRequirementView.tsx
- tools/ai-agents/frontend/src/components/artifact/__tests__/StructuredRequirementView.test.tsx
- tools/ai-agents/frontend/src/types/artifact.ts
