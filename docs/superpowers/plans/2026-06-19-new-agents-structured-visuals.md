# New Agents Structured Visuals Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the first shared `ai4se-visual` artifact Markdown protocol and render traceability matrices through frontend components.

**Architecture:** Keep parsing in a React-free core module, rendering in a focused component, and Markdown language dispatch in the existing shared code renderer. ArtifactPane remains the integration surface for live and history previews.

**Tech Stack:** React, TypeScript, Vitest, Testing Library, ReactMarkdown.

---

### Task 1: Structured Visual Parser

**Files:**
- Create: `tools/new-agents/frontend/src/core/structuredVisuals.ts`
- Test: `tools/new-agents/frontend/src/core/__tests__/structuredVisuals.test.ts`

- [x] **Step 1: Write the failing parser tests**

Create tests that import `parseStructuredVisual` and assert that a valid `traceability-matrix` JSON block returns typed columns and rows, invalid JSON returns an invalid result with a message, and unsupported `type` returns an invalid result.

- [x] **Step 2: Run parser tests to verify RED**

Run: `cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/structuredVisuals.test.ts`

Expected: fail because `structuredVisuals.ts` does not exist yet.

- [x] **Step 3: Implement the parser**

Create `structuredVisuals.ts` with `StructuredVisualResult`, `TraceabilityMatrixVisual`, and `parseStructuredVisual(source: string)` using `JSON.parse` plus explicit schema checks.

- [x] **Step 4: Run parser tests to verify GREEN**

Run: `cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/structuredVisuals.test.ts`

Expected: all parser tests pass.

### Task 2: Structured Visual Component

**Files:**
- Create: `tools/new-agents/frontend/src/components/StructuredVisual.tsx`
- Test: `tools/new-agents/frontend/src/components/__tests__/StructuredVisual.test.tsx`

- [x] **Step 1: Write the failing component tests**

Create tests that render `StructuredVisual` with a valid matrix and expect an accessible table labeled by the title. Add an invalid JSON test that expects `结构化可视化格式错误`.

- [x] **Step 2: Run component tests to verify RED**

Run: `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/StructuredVisual.test.tsx`

Expected: fail because `StructuredVisual.tsx` does not exist yet.

- [x] **Step 3: Implement the component**

Render valid matrices as a compact table with the existing dark artifact visual style. Render invalid blocks as a bordered error panel with the parser message.

- [x] **Step 4: Run component tests to verify GREEN**

Run: `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/StructuredVisual.test.tsx`

Expected: all component tests pass.

### Task 3: Artifact Markdown Integration

**Files:**
- Modify: `tools/new-agents/frontend/src/components/markdownCodeRenderer.tsx`
- Modify: `tools/new-agents/frontend/src/components/ArtifactPane.tsx`
- Test: `tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`

- [x] **Step 1: Write the failing ArtifactPane test**

Add an ArtifactPane test with a fenced `ai4se-visual` block and assert that preview mode renders a table with `aria-label="需求-风险-用例追溯矩阵"`.

- [x] **Step 2: Run ArtifactPane test to verify RED**

Run: `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx`

Expected: fail because `ai4se-visual` still renders as a generic code block.

- [x] **Step 3: Add structured visual dispatch**

Extend `createMarkdownCodeRenderer` with optional `renderStructuredVisual`. In `ArtifactPane`, pass a renderer that returns `<StructuredVisual source={String(children).replace(/\n$/, '')} />` when language is `ai4se-visual`.

- [x] **Step 4: Run ArtifactPane test to verify GREEN**

Run: `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/ArtifactPane.test.tsx`

Expected: all ArtifactPane tests pass.

### Task 4: Record Todo Progress And Verify

**Files:**
- Modify: `docs/todos/new-agents-evolution.md`

- [x] **Step 1: Update todo progress**

Append a dated note under P0 #3 describing the new `ai4se-visual` protocol, traceability matrix renderer, and remaining backend contract work.

- [x] **Step 2: Run focused frontend tests**

Run: `cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/structuredVisuals.test.ts src/components/__tests__/StructuredVisual.test.tsx src/components/__tests__/ArtifactPane.test.tsx src/components/__tests__/markdownCodeRenderer.test.tsx`

Expected: all selected tests pass.

- [x] **Step 3: Run diff whitespace verification**

Run: `git diff --check`

Expected: no whitespace errors.
