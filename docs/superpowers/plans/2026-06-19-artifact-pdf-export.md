# Artifact PDF Export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a minimal valid PDF download option to ArtifactPane.

**Architecture:** Keep export logic local to `ArtifactPane`. Add a small PDF string builder that emits PDF objects, content stream, and xref offsets without adding dependencies.

**Tech Stack:** React, TypeScript, Vitest, Testing Library, browser Blob API.

---

### Task 1: PDF Export Option

**Files:**
- Modify: `tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`
- Modify: `tools/new-agents/frontend/src/components/ArtifactPane.tsx`
- Modify: `docs/todos/new-agents-evolution.md`

- [ ] **Step 1: Write the failing test**

Add a test that opens the export menu, clicks `PDF`, and asserts `test_design_artifact.pdf`, MIME `application/pdf`, `%PDF-1.4`, and UTF-16BE hex for `测试报告`.

- [ ] **Step 2: Run ArtifactPane test to verify it fails**

Run: `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx`

Expected: FAIL because the `PDF` menu item does not exist.

- [ ] **Step 3: Implement minimal PDF builder and menu option**

Add PDF generation in `ArtifactPane.tsx`, extend `handleDownload` to accept `pdf`, and add a `PDF` menu button.

- [ ] **Step 4: Update docs**

Record PDF export as plain text PDF, with rich PDF layout still remaining.

- [ ] **Step 5: Verify**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx src/core/__tests__/artifactDiff.test.ts
cd tools/new-agents/frontend && npm run lint
git diff --check
```
