# New Agents Context Truncation Warning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Surface server-side context truncation as a visible left-chat warning.

**Architecture:** Extend backend context building to return warning codes, pass them through `run_started`, and map them to an initial frontend stream chunk. Keep artifact truncation and context truncation separate.

**Tech Stack:** Python 3.11, Pydantic, pytest, TypeScript, Vitest.

---

## File Structure

- Modify: `tools/new-agents/backend/context_builder.py`
  - Add context result object with `prompt` and `warnings`.
- Modify: `tools/new-agents/backend/stream_services.py`
  - Emit context warnings on `RunStartedEvent`.
- Modify: `tools/new-agents/backend/sse_schemas.py`
  - Add optional `warnings` to `RunStartedEvent`.
- Modify tests:
  - `tools/new-agents/backend/tests/test_context_builder.py`
  - `tools/new-agents/backend/tests/test_stream_services.py`
  - `tools/new-agents/frontend/src/core/__tests__/llm.test.ts`
- Modify: `tools/new-agents/frontend/src/core/llm.ts`
  - Parse run-start warnings and show a visible first chunk.

## Task 1: RED Tests

- [ ] **Step 1: Add backend failing tests**

Assert truncated context returns `context_truncated` and stream emits `RunStartedEvent(warnings=["context_truncated"])`.

- [ ] **Step 2: Add frontend failing test**

Assert `run_started.warnings=["context_truncated"]` maps to an initial chunk containing a truncation warning.

- [ ] **Step 3: Run focused tests**

Run backend and frontend focused tests; expected failure because warnings are not implemented.

## Task 2: Implementation

- [ ] **Step 1: Implement context result**

Return `{prompt, warnings}` while keeping `build_run_context_prompt` compatibility.

- [ ] **Step 2: Wire stream warnings**

Pass context warnings through `RunStartedEvent`.

- [ ] **Step 3: Wire frontend visible message**

Map `context_truncated` to a concise visible chat message.

## Task 3: Verification And Docs

- [ ] **Step 1: Run focused tests**

Backend context/stream tests and frontend llm tests must pass.

- [ ] **Step 2: Run lint/check**

Run frontend lint and `git diff --check`.

- [ ] **Step 3: Update todo/docs**

Record the visible context truncation warning slice and remaining summary work.
