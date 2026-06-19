# New Agents Structured Failure Retry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make structured output failures in the left chat pane directly actionable with a visible retry card.

**Architecture:** Keep the existing free-form chat model. Detect known structured failure copy in `ChatPane`, render a lightweight recovery block inside that assistant message, and call the existing `handleRetry` from `useChatService`. Suppress the stage transition confirmation card when the latest assistant message is a structured failure.

**Tech Stack:** React, TypeScript, Zustand store, Vitest, Testing Library.

---

### Task 1: ChatPane Structured Failure Recovery

**Files:**
- Modify: `tools/new-agents/frontend/src/components/ChatPane.tsx`
- Test: `tools/new-agents/frontend/src/components/__tests__/ChatPane.test.tsx`

- [ ] **Step 1: Write failing tests**

Add tests that set an assistant message containing `结构化输出生成失败`, render `ChatPane`, assert that `重试本阶段生成` is visible, click it, and verify mocked `handleRetry` is called. Add a second test with `pendingStageTransition` set and the same failure message, then assert `确认进入 策略制定` is not visible.

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
npm run test -- --run src/components/__tests__/ChatPane.test.tsx
```

Expected: tests fail because ChatPane has no `重试本阶段生成` recovery card and still renders the stage confirmation.

- [ ] **Step 3: Implement minimal UI**

In `ChatPane.tsx`, add a local helper that detects assistant messages whose content includes `结构化输出生成失败`. For those messages, render a bordered recovery panel below the Markdown content with the status copy and a primary `重试本阶段生成` button wired to `handleRetry`.

- [ ] **Step 4: Guard stage confirmation**

Compute whether the latest assistant message is a structured output failure. Add this to the existing stage transition condition so the confirmation card is not shown in that state.

- [ ] **Step 5: Verify**

Run:

```bash
npm run test -- --run src/components/__tests__/ChatPane.test.tsx src/services/__tests__/chatService.test.ts
npm run build
git diff --check
```

Expected: all commands exit 0.

### Task 2: Todo Progress Record

**Files:**
- Modify: `docs/todos/new-agents-ux-professionalization.md`

- [ ] **Step 1: Record P0 progress**

Under `P0 2. 结构化输出失败与重试体验`, add a 2026-06-19 progress record describing the visible retry card, stage confirmation guard, and validation commands.

- [ ] **Step 2: Verify docs patch**

Run:

```bash
git diff --check
```

Expected: command exits 0.
