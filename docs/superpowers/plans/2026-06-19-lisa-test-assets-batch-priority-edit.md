# Lisa Test Assets Batch Priority Edit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a batch priority edit control to the Lisa test asset modal.

**Architecture:** Reuse the existing frontend modal and `updateTestAssetCase()` service. The batch action loops through the current collection test cases and replaces local cases with server responses.

**Tech Stack:** React, TypeScript, Vitest, React Testing Library.

---

## File Structure

- Modify `tools/new-agents/frontend/src/components/Header.tsx`: add batch priority state, control, and save handler.
- Modify `tools/new-agents/frontend/src/components/__tests__/Header.test.tsx`: add batch priority test.
- Modify `docs/todos/new-agents-evolution.md`: record progress and remaining asset-center gaps.

## Task 1: Header Test

- [ ] Add a failing test using `TEST_ASSET_COLLECTION_WITH_TWO_DRAFTS`, open test assets, choose `P1`, click “应用优先级”, and assert `updateTestAssetCase` is called for `TC-001` and `TC-002`.
- [ ] Assert the updated priority appears and success text says `已批量更新 2 条用例优先级`。
- [ ] Run `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/Header.test.tsx` and verify RED.

## Task 2: Header Implementation

- [ ] Add `batchPriorityDraft`, `isBatchUpdatingPriority`, and `batchPrioritySummary` state.
- [ ] Reset these states when opening test assets.
- [ ] Add UI controls near existing batch import controls.
- [ ] Implement `handleBatchUpdatePriority()` using existing `updateTestAssetCase()`.
- [ ] Re-run Header test and verify GREEN.

## Task 3: Verification

- [ ] Run `cd tools/new-agents/frontend && npm run test -- --run src/components/__tests__/Header.test.tsx src/services/__tests__/testAssetService.test.ts`。
- [ ] Run `cd tools/new-agents/frontend && npm run lint`。
- [ ] Run `git diff --check`。
- [ ] Update `docs/todos/new-agents-evolution.md`。

## Self-Review

- Spec coverage: Header batch priority action and todo update are covered.
- Placeholder scan: no placeholder implementation steps remain.
- Type consistency: uses existing `TestAssetCase` and `updateTestAssetCase()`.
