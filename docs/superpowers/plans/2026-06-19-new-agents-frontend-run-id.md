# New Agents Frontend Run ID Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the frontend remember the backend `runId` returned by typed SSE and reuse it on later turns in the same workspace.

**Architecture:** Store `currentRunId` in the existing Zustand persisted workspace state. `llm.ts` reads it when building the Agent Runtime request and writes it back when parsing `run_started.runId`.

**Tech Stack:** React 19, Zustand 5, TypeScript 5.8, Vitest.

---

## File Structure

- Modify: `tools/new-agents/frontend/src/core/types.ts`
  - Add `currentRunId` and `setCurrentRunId`.
- Modify: `tools/new-agents/frontend/src/store.ts`
  - Initialize, sanitize, persist, clear, and reset `currentRunId`.
- Modify: `tools/new-agents/frontend/src/core/llm.ts`
  - Parse optional `run_started.runId`, store it, and include `runId` in later requests.
- Modify tests:
  - `tools/new-agents/frontend/src/__tests__/store.test.ts`
  - `tools/new-agents/frontend/src/core/__tests__/llm.test.ts`

## Task 1: Store Tests

- [ ] **Step 1: Add failing store tests**

Cover `setCurrentRunId`, `clearHistory`, `setWorkflow`, and persisted merge sanitization.

- [ ] **Step 2: Run store tests**

Run: `cd tools/new-agents/frontend && npm run test -- --run src/__tests__/store.test.ts`
Expected: FAIL because `currentRunId` is not in state yet.

## Task 2: LLM Tests

- [ ] **Step 1: Add failing llm tests**

Cover omission of `runId` on first request, inclusion on subsequent request, and storing `run_started.runId`.

- [ ] **Step 2: Run llm tests**

Run: `cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/llm.test.ts`
Expected: FAIL because `llm.ts` ignores `run_started.runId` and request bodies do not include `runId`.

## Task 3: Implementation

- [ ] **Step 1: Update types and store**

Add `currentRunId`, `setCurrentRunId`, persisted sanitization, and reset behavior.

- [ ] **Step 2: Update Agent Runtime stream handling**

Add optional `runId` to the runtime event type, include current run ID in fetch body, and set store state on `run_started.runId`.

## Task 4: Verification And Docs

- [ ] **Step 1: Run focused frontend tests**

Run: `cd tools/new-agents/frontend && npm run test -- --run src/__tests__/store.test.ts src/core/__tests__/llm.test.ts`
Expected: PASS.

- [ ] **Step 2: Run frontend lint**

Run: `cd tools/new-agents/frontend && npm run lint`
Expected: PASS.

- [ ] **Step 3: Run diff whitespace check**

Run: `git diff --check`
Expected: no output and exit code 0.

- [ ] **Step 4: Update docs and todo**

Record frontend runId reuse in `docs/todos/new-agents-evolution.md`, `docs/ARCHITECTURE.md`, and `docs/TESTING.md`.
