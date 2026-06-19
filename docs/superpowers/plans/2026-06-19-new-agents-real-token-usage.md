# New Agents Real Token Usage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Capture provider-reported streaming token usage for raw OpenAI-compatible Agent Runtime turns.

**Architecture:** Extend the existing string streaming helper with an optional usage callback. Store usage on `PydanticAgentRuntime`, then let `stream_services.py` prefer that value when recording turn metrics.

**Tech Stack:** Python 3.11, OpenAI SDK compatible stream chunks, pytest, Markdown docs.

---

### Task 1: LLM Client Usage Callback

**Files:**
- Modify: `tools/new-agents/backend/llm_client.py`
- Modify: `tools/new-agents/backend/tests/test_llm_client.py`

- [x] **Step 1: Write the failing test**

Add a stream chunk fixture with `usage.total_tokens = 42`, call `stream_chat_completion_content(..., on_usage=usage_values.append)`, assert yielded content remains unchanged, assert `usage_values == [42]`, and assert `chat.completions.create` was called with `stream_options={"include_usage": True}`.

- [x] **Step 2: Run RED**

Run: `cd tools/new-agents/backend && python3 -m pytest tests/test_llm_client.py::test_stream_chat_completion_content_reports_usage_when_callback_is_supplied -q`

Expected: FAIL because `on_usage` is not accepted yet.

- [x] **Step 3: Implement optional usage extraction**

Add an optional `on_usage` parameter, set `stream_options` only when callback is supplied, and call the callback when a chunk exposes integer `usage.total_tokens`.

- [x] **Step 4: Run llm client tests**

Run: `cd tools/new-agents/backend && python3 -m pytest tests/test_llm_client.py -q`

Expected: all llm client tests pass.

### Task 2: Runtime And Metric Usage Wiring

**Files:**
- Modify: `tools/new-agents/backend/agent_runtime.py`
- Modify: `tools/new-agents/backend/stream_services.py`
- Modify: `tools/new-agents/backend/tests/test_agent_runtime.py`
- Modify: `tools/new-agents/backend/tests/test_stream_services.py`

- [x] **Step 1: Write failing runtime test**

In the raw streaming runtime test, make the fake `stream_chat_completion_content` call the supplied `on_usage(123)`, then assert `runtime.last_token_usage == 123`.

- [x] **Step 2: Write failing stream metric test**

Add a stream service success metric test where mocked runtime returns a valid final output and has `last_token_usage = 321`; assert recorded metric `estimated_tokens == 321`.

- [x] **Step 3: Run RED tests**

Run: `cd tools/new-agents/backend && python3 -m pytest tests/test_agent_runtime.py::test_raw_streaming_runtime_records_stream_usage tests/test_stream_services.py::test_stream_agent_run_events_records_real_token_usage_when_runtime_exposes_it -q`

Expected: FAIL because runtime usage is not stored and stream metrics still use the character estimate.

- [x] **Step 4: Implement runtime and metric wiring**

Add `last_token_usage` to `PydanticAgentRuntime`, pass `on_usage` in raw streaming, and make stream metric recording prefer non-negative integer usage.

- [x] **Step 5: Run focused backend tests**

Run: `cd tools/new-agents/backend && python3 -m pytest tests/test_llm_client.py tests/test_agent_runtime.py::test_raw_streaming_runtime_records_stream_usage tests/test_stream_services.py::test_stream_agent_run_events_records_real_token_usage_when_runtime_exposes_it tests/test_stream_services.py::test_stream_agent_run_events_records_turn_through_persistence_adapter -q`

Expected: selected tests pass.

### Task 3: Todo Record And Verification

**Files:**
- Modify: `docs/todos/new-agents-evolution.md`
- Modify: `docs/superpowers/plans/2026-06-19-new-agents-real-token-usage.md`

- [x] **Step 1: Update progress**

Record that raw OpenAI-compatible streaming can now capture provider-reported `total_tokens`, while non-usage providers still fall back to estimates.

- [x] **Step 2: Run verification**

Run: `cd tools/new-agents/backend && python3 -m pytest tests/test_llm_client.py tests/test_agent_runtime.py tests/test_stream_services.py tests/test_agent_endpoint.py::test_agent_observability_endpoint_returns_runtime_turn_summary -q`

Expected: backend runtime, stream service, llm client, and observability summary tests pass.

- [x] **Step 3: Run whitespace check**

Run: `git diff --check`

Expected: no whitespace errors.
