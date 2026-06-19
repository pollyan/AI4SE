# New Agents Server Context Builder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move persisted-run conversation history assembly from the frontend into a backend context builder for requests with `runId`.

**Architecture:** Add a backend context builder that reads persisted run snapshots through `run_persistence`, composes a bounded prompt, and is invoked through the existing stream persistence adapter. The frontend keeps first-turn and attachment behavior unchanged, but stops adding local chat history when `currentRunId` is available.

**Tech Stack:** Python 3.11, Flask-SQLAlchemy, pytest, React/TypeScript, Vitest.

---

## File Structure

- Create: `tools/new-agents/backend/context_builder.py`
  - Builds bounded runtime prompt from persisted snapshot messages.
- Create: `tools/new-agents/backend/tests/test_context_builder.py`
  - Unit tests ordering, filtering, truncation, and no-history behavior.
- Modify: `tools/new-agents/backend/run_persistence.py`
  - Add `AgentRunPersistence.build_runtime_prompt`.
- Modify: `tools/new-agents/backend/stream_services.py`
  - Use persistence-provided runtime prompt after run is ensured.
- Modify: `tools/new-agents/backend/tests/test_stream_services.py`
  - Assert runtime gets persisted context prompt.
- Modify: `tools/new-agents/frontend/src/core/llm.ts`
  - Do not include local chat history when `currentRunId` exists.
- Modify: `tools/new-agents/frontend/src/core/__tests__/llm.test.ts`
  - Assert `runId` requests send only current user content plus attachments.
- Modify docs:
  - `docs/todos/new-agents-evolution.md`
  - `docs/ARCHITECTURE.md`
  - `docs/TESTING.md`

## Task 1: Backend Context Builder Tests

- [ ] **Step 1: Write failing tests**

Create tests for no prior history, ordered persisted messages, assistant control filtering, and truncation notice.

- [ ] **Step 2: Run tests to verify failure**

Run: `cd tools/new-agents/backend && python3 -m pytest tests/test_context_builder.py -q`
Expected: FAIL because `context_builder.py` does not exist.

## Task 2: Stream Service Integration Tests

- [ ] **Step 1: Add failing stream test**

Extend fake persistence with `build_runtime_prompt`, then assert `runtime.stream_turn` receives the server-built prompt when persistence is supplied.

- [ ] **Step 2: Run stream tests**

Run: `cd tools/new-agents/backend && python3 -m pytest tests/test_stream_services.py -q`
Expected: FAIL because `stream_agent_run_events` still passes `agent_request.prompt` directly.

## Task 3: Frontend Prompt Boundary Tests

- [ ] **Step 1: Add failing llm test**

Set `currentRunId`, include previous local chat history, call `generateResponseStream`, and assert request body `prompt` contains only current user text, not local history.

- [ ] **Step 2: Run frontend llm tests**

Run: `cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/llm.test.ts`
Expected: FAIL because `llm.ts` still calls `buildRuntimePrompt` with chat history when `currentRunId` exists.

## Task 4: Implementation

- [ ] **Step 1: Implement `context_builder.py`**

Add `build_run_context_prompt(run_id, current_prompt, max_chars=12000)`.

- [ ] **Step 2: Wire persistence adapter**

Add `build_runtime_prompt` to `AgentRunPersistence` and the stream persistence protocol.

- [ ] **Step 3: Wire stream service**

Use the server-built prompt for `runtime.stream_turn` after `ensure_run`.

- [ ] **Step 4: Wire frontend prompt boundary**

When `currentRunId` exists, call `buildContentWithAttachments` for the current user input instead of `buildRuntimePrompt`.

## Task 5: Verification And Docs

- [ ] **Step 1: Run backend focused tests**

Run: `cd tools/new-agents/backend && python3 -m pytest tests/test_context_builder.py tests/test_stream_services.py tests/test_agent_endpoint.py tests/test_run_persistence.py -q`
Expected: PASS.

- [ ] **Step 2: Run frontend focused tests**

Run: `cd tools/new-agents/frontend && npm run test -- --run src/core/__tests__/llm.test.ts src/__tests__/store.test.ts`
Expected: PASS.

- [ ] **Step 3: Run lint/checks**

Run: `cd tools/new-agents/frontend && npm run lint`
Expected: PASS.

Run: `git diff --check`
Expected: no output and exit code 0.

- [ ] **Step 4: Update docs and todo**

Record the P1 #6 first slice and remaining context builder work.
