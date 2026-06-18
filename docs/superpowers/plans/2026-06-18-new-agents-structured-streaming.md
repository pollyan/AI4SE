# New Agents Structured Streaming Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore real streaming UI feedback for New Agents while keeping final PydanticAI structured output stable and contract-validated.

**Architecture:** Add typed draft SSE events before the final `agent_turn`. Backend emits `run_started`, `agent_delta`, final `agent_turn`, and `error`; frontend treats draft events as UI-only cumulative frames and keeps final persistence on the existing final chunk path.

**Tech Stack:** Flask, Pydantic, PydanticAI, typed SSE, React 19, Zustand, Vitest, pytest.

---

## File Structure

- Modify `tools/new-agents/backend/sse_schemas.py`: add `RunStartedEvent` and `AgentTurnDeltaEvent`.
- Modify `tools/new-agents/backend/agent_runtime.py`: add streaming runtime method and partial-output normalization.
- Modify `tools/new-agents/backend/stream_services.py`: yield start and delta events, then final event.
- Modify `tools/new-agents/backend/tests/test_stream_services.py`: cover event sequence and fallback/error behavior.
- Modify `tools/new-agents/backend/tests/test_agent_endpoint.py`: cover endpoint SSE payload sequence.
- Modify `tools/new-agents/frontend/src/core/llm.ts`: parse start/delta events and map them into stream chunks.
- Modify `tools/new-agents/frontend/src/core/__tests__/llm.test.ts`: cover start/delta/final parsing.
- Modify `tools/new-agents/frontend/src/services/__tests__/chatService.test.ts`: cover progressive UI state before generator completion.

## Task 1: Backend SSE Event Contract

**Files:**
- Modify: `tools/new-agents/backend/sse_schemas.py`
- Test: `tools/new-agents/backend/tests/test_stream_services.py`

- [ ] **Step 1: Write failing backend service test**

Add a test that uses a runtime double with `stream_turn()` returning one partial output and one final output:

```python
def test_stream_agent_run_events_yields_started_delta_and_final_events(mock_build_runtime):
    partial = AgentTurnOutput.model_validate({
        "chat": "正在梳理需求。",
        "artifact_update": {"type": "replace", "markdown": VALID_CLARIFY_ARTIFACT},
        "stage_action": None,
        "warnings": [],
    })
    final = AgentTurnOutput.model_validate({
        "chat": "已更新右侧需求分析文档，请确认。",
        "artifact_update": {"type": "replace", "markdown": VALID_CLARIFY_ARTIFACT},
        "stage_action": None,
        "warnings": [],
    })
    runtime = MagicMock()
    runtime.stream_turn.return_value = iter([partial, final])
    mock_build_runtime.return_value = runtime

    events = list(stream_agent_run_events(request, api_key="test-api-key", base_url="https://api.test.com/v1", model_name="test-model"))

    assert [event.type for event in events] == ["run_started", "agent_delta", "agent_turn"]
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest tools/new-agents/backend/tests/test_stream_services.py::test_stream_agent_run_events_yields_started_delta_and_final_events -q
```

Expected: FAIL because the event models and `stream_turn()` path do not exist.

- [ ] **Step 3: Add event models**

Add `RunStartedEvent` and `AgentTurnDeltaEvent` to `sse_schemas.py`:

```python
class RunStartedEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["run_started"] = "run_started"


class AgentTurnDeltaEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["agent_delta"] = "agent_delta"
    output: AgentTurnOutput
```

Update `SseEvent` to include both.

- [ ] **Step 4: Implement service event sequence**

In `stream_agent_run_events()`, call `runtime.stream_turn(...)`, yield `RunStartedEvent()`, yield `AgentTurnDeltaEvent` for all but the last streamed output, and yield `AgentTurnEvent` for the final output.

- [ ] **Step 5: Run backend targeted tests**

Run:

```bash
/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest tools/new-agents/backend/tests/test_stream_services.py -q
```

Expected: all stream service tests pass.

## Task 2: Backend Runtime Streaming Boundary

**Files:**
- Modify: `tools/new-agents/backend/agent_runtime.py`
- Test: `tools/new-agents/backend/tests/test_stream_services.py`, `tools/new-agents/backend/tests/test_agent_endpoint.py`

- [ ] **Step 1: Write failing endpoint test**

Add endpoint coverage that a fake runtime with `stream_turn()` produces JSON payloads with `run_started`, `agent_delta`, and `agent_turn`.

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_endpoint.py::test_agent_runs_stream_returns_started_delta_and_final_sse_events -q
```

Expected: FAIL before endpoint fake/runtime path is updated.

- [ ] **Step 3: Implement `PydanticAgentRuntime.stream_turn()`**

Add a generator method that:

- Uses PydanticAI streaming APIs when available.
- Yields validated-looking partial `AgentTurnOutput` values without business-contract enforcement.
- Validates and yields the final `AgentTurnOutput` with `validate_agent_turn(...)`.
- Falls back to `run_turn()` when the installed runtime/test double has no streaming API.

- [ ] **Step 4: Update test fakes**

Give existing `FakeRuntime` and `FailingRuntime` in endpoint tests `stream_turn()` methods so tests exercise the streaming service path.

- [ ] **Step 5: Run backend endpoint and service tests**

Run:

```bash
/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest tools/new-agents/backend/tests/test_stream_services.py tools/new-agents/backend/tests/test_agent_endpoint.py -q
```

Expected: all selected backend tests pass.

## Task 3: Frontend SSE Parser and Chunk Mapping

**Files:**
- Modify: `tools/new-agents/frontend/src/core/llm.ts`
- Test: `tools/new-agents/frontend/src/core/__tests__/llm.test.ts`

- [ ] **Step 1: Write failing parser test**

Add a Vitest case whose SSE body contains:

```text
data: {"type":"run_started"}
data: {"type":"agent_delta","output":{"chat":"正在梳理需求。","artifact_update":{"type":"none"},"stage_action":null,"warnings":[]}}
data: {"type":"agent_delta","output":{"chat":"正在梳理需求。\n\n已生成初稿。","artifact_update":{"type":"replace","markdown":"# 需求分析文档\n\n## 1. 被测系统与边界\n登录功能"},"stage_action":null,"warnings":[]}}
data: {"type":"agent_turn","output":{"chat":"正在梳理需求。\n\n已生成初稿。","artifact_update":{"type":"replace","markdown":"# 需求分析文档\n\n## 1. 被测系统与边界\n登录功能\n\n## 2. 系统交互与核心链路\n待补充\n\n## 3. 待澄清与阻断性问题\n需要确认验证码策略\n\n## 4. 隐式需求与非功能性考量\n覆盖安全和审计要求"},"stage_action":null,"warnings":[]}}
data: [DONE]
```

Assert the collected chunks include an immediate first chunk, draft chat/artifact chunks, and the final complete chunk.

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
npm run test -- --run src/core/__tests__/llm.test.ts
```

Expected: FAIL because `run_started` and `agent_delta` are rejected.

- [ ] **Step 3: Extend event parsing**

Update `AgentRuntimeEvent` and `parseAgentRuntimeEvent()` to accept:

```ts
| { type: 'run_started' }
| { type: 'agent_delta'; output: AgentTurnOutput }
```

Delta output validation accepts empty/missing artifact updates only through the existing `none` shape; final `agent_turn` keeps strict non-empty final validation.

- [ ] **Step 4: Map events to stream chunks**

In `processSsePayload()`:

- `run_started` yields `{ chatResponse: '正在生成...', newArtifact: currentArtifact, action: '', hasArtifactUpdate: false }`.
- `agent_delta` yields cumulative draft chunks without synthetic splitting.
- `agent_turn` keeps the existing final synthetic splitting behavior.

- [ ] **Step 5: Run frontend parser tests**

Run:

```bash
npm run test -- --run src/core/__tests__/llm.test.ts
```

Expected: all parser tests pass.

## Task 4: Chat Service Progressive Rendering

**Files:**
- Modify: `tools/new-agents/frontend/src/services/__tests__/chatService.test.ts`
- Modify if needed: `tools/new-agents/frontend/src/services/chatService.ts`

- [ ] **Step 1: Write failing service test**

Add a test where mocked `generateResponseStream()` yields one chunk, waits on a promise, then yields a second chunk. Assert before resolving the promise that `chatHistory[1].content` and `artifactContent` already reflect the first chunk.

- [ ] **Step 2: Run test to verify it fails or confirms current behavior**

Run:

```bash
npm run test -- --run src/services/__tests__/chatService.test.ts
```

Expected: if current service already updates per chunk, PASS; otherwise FAIL and fix `chatService.ts` to update state inside the `for await` loop.

- [ ] **Step 3: Fix only if needed**

Keep the state update order inside the existing stream loop:

1. Add/update assistant message from the current chunk.
2. Apply draft artifact content from the current chunk.
3. Stop only after applying the final transition chunk.

- [ ] **Step 4: Run combined frontend tests**

Run:

```bash
npm run test -- --run src/core/__tests__/llm.test.ts src/services/__tests__/chatService.test.ts
```

Expected: both files pass.

## Task 5: Full Targeted Verification and Merge Prep

**Files:**
- All touched files.

- [ ] **Step 1: Run backend verification**

```bash
/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest tools/new-agents/backend/tests/test_stream_services.py tools/new-agents/backend/tests/test_agent_endpoint.py -q
```

- [ ] **Step 2: Run frontend verification**

```bash
npm run test -- --run src/core/__tests__/llm.test.ts src/services/__tests__/chatService.test.ts
```

- [ ] **Step 3: Inspect git diff**

```bash
git diff --stat
git diff --check
```

- [ ] **Step 4: Commit implementation**

```bash
git add docs/superpowers/plans/2026-06-18-new-agents-structured-streaming.md tools/new-agents/backend tools/new-agents/frontend/src/core tools/new-agents/frontend/src/services
git commit -m "feat(new-agents): 恢复结构化流式渲染"
```
