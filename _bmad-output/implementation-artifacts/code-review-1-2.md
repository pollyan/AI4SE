# Code Review Findings: Story 1.2

**Story:** `_bmad-output/implementation-artifacts/1-2-expand-diff-coverage-to-all-artifact-types.md`
**Git vs Story Discrepancies:** 6 found (See Medium Issues)
**Issues Found:** 0 High, 2 Medium, 1 Low

## 🔴 CRITICAL ISSUES
*None. Excellent work on the core backend recursion and frontend integration.*

## 🟡 MEDIUM ISSUES
1.  **Files changed but not documented in story File List**:
    *   The following files were modified/created but are missing from the Story's File List:
        *   `tools/ai-agents/frontend/src/components/common/DiffField.tsx` (New component)
        *   `tools/ai-agents/frontend/src/components/common/__tests__/DiffField.test.tsx` (New tests)
        *   `tools/ai-agents/frontend/src/components/artifact/__tests__/StructuredRequirementView.test.tsx` (New tests)
        *   `tools/ai-agents/frontend/src/types/artifact.ts` (Modified types)
        *   `tools/ai-agents/frontend/index.css` (Added Diff CSS)
        *   `tools/ai-agents/frontend/package.json` (Added `fast-diff`)
    *   *Why this matters*: Future maintainers relying on the story artifact won't know these files were part of this specific feature change.

2.  **Ineffective Code in `StructuredRequirementView.tsx` (Acceptance Criteria)**:
    *   File: `tools/ai-agents/frontend/src/components/artifact/StructuredRequirementView.tsx`
    *   Code: `<DiffField value={ac} />` inside `feature.acceptance.map`
    *   Problem: You are using `DiffField` but NOT passing an `oldValue`. The backend `artifact_patch.py` treats string lists (`acceptance`) as replacements, so `_prev` (if it existed for the array) would be the *entire* old array. There is no logic to correlate "Item 1 in old array" to "Item 1 in new array" for string lists.
    *   Result: `DiffField` is performing unnecessary work (imports, memoization check) to just render plain text. It gives the *illusion* of diff support where none exists.

## 🟢 LOW ISSUES
1.  **Backend `_prev` Granularity**:
    *   In `artifact_patch.py`, `_prev` stores the *entire* old value for a nested field if it changed. While this satisfies the requirement, for large text fields, this might slightly bloat the JSON payload more than necessary (though arguably better than complexity of text diffing in backend).
