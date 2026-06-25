# New Agents Artifact Section Memo Rendering Implementation Plan

> **For agentic workers:** Use executing-plans and keep checkboxes current.

**Goal:** Make ArtifactPane main preview render unchanged markdown sections through memoized section blocks instead of one full-document ReactMarkdown render.

## Task 1: Red Test

Files:
- `tools/new-agents/frontend/src/components/__tests__/ArtifactPane.incrementalRender.test.tsx`

- [x] Mock `react-markdown` and record render counts by markdown section content.
- [x] Render ArtifactPane with two sections, update only the second section, assert the first section render count stays at 1.
- [x] Run the focused test and confirm it fails on the current full-document renderer.

## Task 2: Section Renderer

Files:
- `tools/new-agents/frontend/src/components/ArtifactPane.tsx`

- [x] Add markdown render block builder using shared section extraction.
- [x] Add block-level Mermaid / structured visual offset counting.
- [x] Add memoized section renderer for the main preview path.
- [x] Keep history preview and code view unchanged.

## Task 3: Verification and Todo Update

Files:
- `docs/todos/2026-06-25-new-agents-artifact-incremental-rendering.md`

- [x] Run focused incremental render test.
- [x] Run ArtifactPane tests, frontend lint, and frontend full test suite.
- [x] Update active todo with scope and verification evidence.
- [x] Diff check, stage only this slice, commit.
