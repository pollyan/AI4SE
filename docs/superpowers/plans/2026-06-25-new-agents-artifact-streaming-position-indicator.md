# New Agents Artifact Streaming Position Indicator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a non-persistent position indicator at the end of the rendered Artifact body while streaming content continues.

**Architecture:** Keep the indicator UI-only inside shared `ArtifactPane`. Do not alter `artifactContent`, SSE events, store state, artifact persistence, exports, or backend contracts.

**Tech Stack:** React, Zustand store selectors, Vitest, Testing Library.

---

### Task 1: Red Tests

**Files:**
- Modify: `tools/new-agents/frontend/src/components/__tests__/ArtifactPane.test.tsx`

- [ ] **Step 1: Add the visible indicator test**

Add a test that sets `artifactContent` to a real Markdown document and `isGenerating` to `true`, renders `ArtifactPane`, and asserts both the existing content and a new body-position indicator are visible.

- [ ] **Step 2: Add the completion cleanup test**

Add a test that sets `artifactContent` and `isGenerating=false`, then asserts the body-position indicator is absent.

- [ ] **Step 3: Add the export pollution test**

Extend the Markdown download test with `isGenerating=true` and assert the downloaded blob text does not include the indicator copy.

- [ ] **Step 4: Run red tests**

Run:

```bash
npm run test -- src/components/__tests__/ArtifactPane.test.tsx
```

Expected: the visible indicator test fails because no body-position indicator exists yet.

### Task 2: UI-only Implementation

**Files:**
- Modify: `tools/new-agents/frontend/src/components/ArtifactPane.tsx`

- [ ] **Step 1: Define display predicate**

Create a boolean near `displayContent`:

```ts
const showArtifactStreamingPositionIndicator = isGenerating && artifactContent.trim().length > 0 && !isEditing;
```

- [ ] **Step 2: Render independent indicator**

Add a small component after the preview/code renderer inside the main artifact body. Use `role="status"` and a stable `data-testid`, for example `artifact-streaming-position-indicator`.

- [ ] **Step 3: Keep content sinks unchanged**

Do not change `handleDownload`, manual edit save, version save, diagnostic input, or any service calls. They must continue to use `artifactContent`.

### Task 3: Verify and Record

**Files:**
- Modify: `docs/todos/refactor/2026-06-24-new-agents-artifact-streaming-position-indicator.md`
- Move to archive if complete.

- [ ] **Step 1: Run focused frontend tests**

Run:

```bash
npm run test -- src/components/__tests__/ArtifactPane.test.tsx
```

- [ ] **Step 2: Run full New Agents frontend tests**

Run:

```bash
npm run test
```

- [ ] **Step 3: Run repository validation**

Run:

```bash
./scripts/test/test-local.sh all
```

If sandbox permissions block port binding or Chromium launch, rerun with elevated permissions and record both results.

- [ ] **Step 4: Archive todo**

If verification passes, move the todo to `docs/todos/archive/` and remove it from `docs/todos/refactor/README.md`.
