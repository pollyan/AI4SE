# Artifact Word Export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Word-compatible `.doc` export option to ArtifactPane while preserving the existing Markdown download behavior.

**Architecture:** Keep export fully frontend-only. ArtifactPane creates either a Markdown blob or a simple escaped HTML blob with `application/msword`.

**Tech Stack:** React, TypeScript, Vitest, browser Blob/Object URL APIs.

---

### Task 1: Export Menu and Word Blob

**Files:**
- Modify: `tools/new-agents/frontend/src/components/ArtifactPane.tsx`
- Modify: `tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`

- [ ] **Step 1: Write failing tests**

Add tests for opening the export menu, preserving Markdown export, and exporting Word with `.doc`, `application/msword`, and escaped content.

- [ ] **Step 2: Run tests red**

Run: `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx`

Expected: FAIL because the Word option does not exist.

- [ ] **Step 3: Implement export helpers and menu**

Add `showExportMenu`, `downloadArtifact(format)`, `escapeHtml`, and `buildWordCompatibleHtml`. Replace direct download click with a menu containing Markdown and Word buttons.

- [ ] **Step 4: Run tests green**

Run: `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx`

Expected: PASS.

### Task 2: Documentation and Verification

**Files:**
- Modify: `docs/todos/new-agents-evolution.md`
- Modify: `docs/component-inventory.md` if needed.

- [ ] **Step 1: Update #11 progress**

Record Word-compatible export and explicitly leave PDF/rich DOCX export as remaining work.

- [ ] **Step 2: Run verification**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx
cd tools/new-agents/frontend && npm run lint
git diff --check
```

Expected: all commands pass.
