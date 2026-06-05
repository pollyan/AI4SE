# Chat Stage Transition Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Move stage-transition confirmation into the chat flow and stop generation until the user confirms.

**Architecture:** Store pending transitions with explicit source/target stage indexes. `chatService` stops consuming the current stream when it sees `NEXT_STAGE`, preventing unconfirmed next-stage artifacts from being written. `ChatPane` renders the confirmation card near the user's focus and triggers the next-stage generation after confirmation.

**Tech Stack:** React 19, Zustand, Vitest, Testing Library, TypeScript.

---

### Task 1: Store Explicit Pending Transition State

**Files:**
- Modify: `tools/new-agents/frontend/src/core/types.ts`
- Modify: `tools/new-agents/frontend/src/store.ts`
- Test: `tools/new-agents/frontend/src/__tests__/p0-fixes.test.ts`

- [x] **Step 1: Write failing store tests**

Add tests proving pending transition target indexes are stored, confirmation advances only to the stored target, and dismiss clears the full pending state.

- [x] **Step 2: Run store tests and verify failure**

Run: `npm test -- src/__tests__/p0-fixes.test.ts`
Expected: FAIL because the store only has a boolean `pendingStageTransition`.

- [x] **Step 3: Implement minimal store changes**

Add `pendingStageTransition: { fromStageIndex: number; toStageIndex: number } | null`, `setPendingStageTransition(pending)`, and `clearPendingStageTransition()`. Update `confirmStageTransition()` to use the stored target.

- [x] **Step 4: Run store tests and verify pass**

Run: `npm test -- src/__tests__/p0-fixes.test.ts`
Expected: PASS.

### Task 2: Stop Current Stream When NEXT_STAGE Appears

**Files:**
- Modify: `tools/new-agents/frontend/src/services/chatService.ts`
- Test: `tools/new-agents/frontend/src/services/__tests__/chatService.test.ts`

- [x] **Step 1: Write failing chat service tests**

Add tests proving `NEXT_STAGE` sets pending state and stops consuming later chunks, so later unconfirmed artifact updates are ignored.

- [x] **Step 2: Run chat service tests and verify failure**

Run: `npm test -- src/services/__tests__/chatService.test.ts`
Expected: FAIL because the service currently continues consuming after `NEXT_STAGE`.

- [x] **Step 3: Implement minimal stream stop**

When `NEXT_STAGE` is observed, set pending transition to `{ fromStageIndex, toStageIndex }`, call `handleStop()` or abort the controller, and break out of the stream loop before handling later chunks.

- [x] **Step 4: Run chat service tests and verify pass**

Run: `npm test -- src/services/__tests__/chatService.test.ts`
Expected: PASS.

### Task 3: Render Confirmation Card In ChatPane And Trigger Next Stage

**Files:**
- Modify: `tools/new-agents/frontend/src/components/ChatPane.tsx`
- Modify: `tools/new-agents/frontend/src/components/Header.tsx`
- Test: `tools/new-agents/frontend/src/components/__tests__/ChatPane.test.tsx`
- Test: `tools/new-agents/frontend/src/components/__tests__/Header.test.tsx`

- [x] **Step 1: Write failing component tests**

Add tests proving the transition confirmation appears in `ChatPane`, the Header banner is absent, "暂不进入" clears pending state, and "确认进入" confirms the stage then invokes next-stage generation.

- [x] **Step 2: Run component tests and verify failure**

Run: `npm test -- src/components/__tests__/ChatPane.test.tsx src/components/__tests__/Header.test.tsx`
Expected: FAIL because the confirmation currently lives in Header.

- [x] **Step 3: Implement chat card**

Move the transition confirmation UI to `ChatPane`. On confirm, call `confirmStageTransition()` and then `handleSend('请继续生成当前阶段产出物')`. Remove Header's confirmation banner.

- [x] **Step 4: Run component tests and verify pass**

Run: `npm test -- src/components/__tests__/ChatPane.test.tsx src/components/__tests__/Header.test.tsx`
Expected: PASS.

### Task 4: Full Verification

**Files:**
- All changed frontend files.

- [x] **Step 1: Run full frontend tests**

Run: `npm test`
Expected: all non-smoke Vitest tests pass.

- [x] **Step 2: Run TypeScript lint**

Run: `npm run lint`
Expected: `tsc --noEmit` exits 0.

- [x] **Step 3: Review diff**

Run: `git diff --stat`
Expected: only the plan and intended frontend files changed.
