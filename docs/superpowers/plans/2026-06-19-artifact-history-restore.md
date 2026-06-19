# Artifact History Restore Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a restore action in the artifact history modal so users can roll the current artifact back to a selected historical version.

**Architecture:** Reuse existing Zustand artifact actions. `ArtifactPane` will call `addArtifactVersion()` to preserve the current artifact, then `setArtifactContent()` to restore the selected version content.

**Tech Stack:** React, Zustand, Vitest, Testing Library.

---

### Task 1: ArtifactPane Restore Action

**Files:**
- Modify: `tools/new-agents/frontend/src/components/ArtifactPane.tsx`
- Modify: `tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`

- [ ] **Step 1: Write failing component test**

Add a test that opens history, clicks “恢复此版本”, and asserts `artifactContent` becomes the selected history content while the previous current content is added to `artifactHistory`.

- [ ] **Step 2: Run test red**

Run: `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx`

Expected: FAIL because the restore button does not exist.

- [ ] **Step 3: Implement restore action**

Read `setArtifactContent` and `addArtifactVersion` from the store. Add a restore button in the history modal header when `selectedVersion` exists. On click, add the current content as a new history version with the current stage id, then restore selected content and close the modal.

- [ ] **Step 4: Run test green**

Run: `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx`

Expected: PASS.

### Task 2: Documentation and Verification

**Files:**
- Modify: `docs/todos/new-agents-evolution.md`
- Modify: `docs/component-inventory.md` if needed.

- [ ] **Step 1: Update #11 progress**

Record the restore action, local persistence boundary, remaining accept/reject/batch collaboration gaps, and verification commands.

- [ ] **Step 2: Run verification**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx src/core/__tests__/artifactDiff.test.ts
cd tools/new-agents/frontend && npm run lint
git diff --check
```

Expected: all commands pass.
