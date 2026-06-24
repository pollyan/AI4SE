# New Agents Stage Action Choice Persistence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve user stage-transition confirmations in chat history while keeping the existing shared stage_action and pending transition flow.

**Architecture:** Reuse `chatHistory`, `pendingStageTransition`, `confirmStageTransition`, and shared generation. Do not add workflow-specific rendering or backend APIs. Stage-transition confirmation sends the persisted confirmation text as the generation prompt while suppressing duplicate user-message append.

**Tech Stack:** Zustand store, React ChatPane, chatService, Vitest.

---

### Task 1: Red Tests

**Files:**
- Modify: `tools/new-agents/frontend/src/services/__tests__/chatService.test.ts`
- Modify: `tools/new-agents/frontend/src/components/__tests__/ChatPane.test.tsx`

- [x] **Step 1: Service confirmation event**

Update the service transition confirmation test to expect a `user` chat history item `已确认进入策略制定` before the internal assistant continuation response.

- [x] **Step 2: ChatPane history after click**

Add a component-level test showing that the stage confirmation card can be represented by a persisted user confirmation message in chat history after the pending state is cleared.

### Task 2: Implementation

**Files:**
- Modify: `tools/new-agents/frontend/src/services/chatService.ts`

- [x] **Step 1: Append confirmation message**

In `handleConfirmStageTransition`, derive the target stage name from the current pending transition and append a user message before calling `confirmStageTransition()`.

- [x] **Step 2: Preserve user-visible continuation boundary**

Keep the continuation call using `appendUserMessage: false` and `retryable: false`, so the confirmation event is user-visible once and the assistant continuation follows it.

### Task 3: Verify and Archive

- [x] **Step 1: Run focused tests**

```bash
cd tools/new-agents/frontend && npm run test -- src/services/__tests__/chatService.test.ts src/components/__tests__/ChatPane.test.tsx
```

- [x] **Step 2: Run New Agents frontend tests**

```bash
cd tools/new-agents/frontend && npm run test
```

- [x] **Step 3: Run broad verification**

Run `./scripts/test/test-local.sh all`; if sandbox blocks ports or Chromium, rerun with elevated permissions and record both.

Verification record:
- `./scripts/test/test-local.sh all` with current environment failed only in optional `NEW_AGENTS_E2E_LLM_JUDGE=1` Alex artifact judge because the external judge returned invalid JSON; deterministic suites before that point passed.
- `NEW_AGENTS_E2E_LLM_JUDGE=0 ./scripts/test/test-local.sh all` passed: Browser E2E reported 3 passed / 3 skipped.

- [x] **Step 4: Archive todo**

Move the completed todo to `docs/todos/archive/` and remove it from `docs/todos/refactor/README.md`.
