# New Agents Strict Structured Failure Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans or execute inline with the current goal-mode TDD discipline. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the raw JSON truncation pseudo-final-output path so partial artifact deltas may stream, but invalid final JSON always ends as a typed error without artifact persistence or stage advancement.

**Architecture:** Keep the existing shared Agent Runtime and typed SSE path. The runtime raises `AgentRuntimeSchemaError` for final JSON decode failure, while `stream_services.py` reuses the existing `SCHEMA_VALIDATION_FAILED` error event, diagnostic, and metric path.

**Tech Stack:** Python 3.11, Pydantic, Flask typed SSE services, pytest.

---

## File Map

- Modify: `tools/new-agents/backend/tests/test_agent_runtime.py`
  Replace the existing `artifact_truncated` success expectation with a failing test that expects schema failure after partial delta.
- Modify: `tools/new-agents/backend/agent_runtime.py`
  Remove the branch that wraps latest partial Markdown into final `AgentTurnOutput(warnings=["artifact_truncated"])`.
- Modify: `tools/new-agents/backend/tests/test_stream_services.py`
  Add a stream service test proving partial delta can be followed by typed error and no persistence success writes occur.
- Modify as needed: `docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md`
  记录第 2 轮执行结果和验证证据。
- Modify only if behavior text must be clarified: `docs/TESTING.md` and `docs/api-contracts.md`.

## Constraints

- Do not add frontend changes unless backend tests reveal a real parser contract gap.
- Do not add workflow-specific logic.
- Do not change successful partial streaming behavior for the 17 existing artifact-data stages.
- Do not persist latest partial artifact as a formal artifact when final JSON is invalid.
- Do not commit or push until focused tests and the agreed batch verification are complete.

---

### Task 1: Runtime Test for Truncated Final JSON

**Files:**
- Modify: `tools/new-agents/backend/tests/test_agent_runtime.py`

- [x] **Step 1: Replace the old pseudo-success test**

Rename `test_runtime_raw_json_stream_turn_keeps_latest_delta_when_final_json_is_truncated` to:

```python
def test_runtime_raw_json_stream_turn_fails_final_json_truncation_after_partial_delta(
    monkeypatch,
):
```

Keep the same chunks that produce a valid partial delta but invalid final JSON:

```python
chunks = [
    '{"chat":"已更新需求文档。",',
    '"artifact_update":{"type":"replace","markdown":"# 需求分析文档\\n\\n'
    "## 1. 被测系统与边界\\n内容",
]
```

Change the assertion to manually consume the generator:

```python
stream = runtime.stream_turn(
    "用户需求",
    workflow_id="TEST_DESIGN",
    current_stage_id="CLARIFY",
)

first_output = next(stream)
assert isinstance(first_output, AgentTurnDeltaOutput)
assert first_output.chat == "已更新需求文档。"
assert first_output.artifact_update is not None
assert first_output.artifact_update.markdown == (
    "# 需求分析文档\n\n## 1. 被测系统与边界\n内容"
)

with pytest.raises(AgentRuntimeSchemaError):
    next(stream)
```

- [x] **Step 2: Run the runtime test and confirm red**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_fails_final_json_truncation_after_partial_delta -q
```

Expected red result: the test fails because the current runtime returns `AgentTurnOutput(warnings=["artifact_truncated"])` instead of raising `AgentRuntimeSchemaError`.

---

### Task 2: Runtime Implementation

**Files:**
- Modify: `tools/new-agents/backend/agent_runtime.py`

- [x] **Step 1: Remove pseudo-final output branch**

In `_stream_raw_json_turn()`, replace this branch:

```python
except json.JSONDecodeError:
    if emitted_any_delta and (latest_chat or latest_markdown):
        yield AgentTurnOutput.model_validate(...)
        return
    raise
```

with:

```python
except json.JSONDecodeError:
    raise
```

After the edit, `emitted_any_delta`, `latest_chat`, and `latest_markdown` remain useful for partial delta emission but no longer affect final failure semantics.

- [x] **Step 2: Run the runtime test and confirm green**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_fails_final_json_truncation_after_partial_delta -q
```

Expected: pass.

---

### Task 3: Stream Service Error Closure Test

**Files:**
- Modify: `tools/new-agents/backend/tests/test_stream_services.py`

- [x] **Step 1: Add a test for partial delta followed by schema error**

Add this test near the existing `AgentRuntimeSchemaError` tests:

```python
@patch("stream_services.build_pydantic_agent_runtime")
def test_stream_agent_run_events_errors_after_partial_delta_without_persisting_artifact(
    mock_build_runtime: MagicMock,
) -> None:
    runtime = MagicMock()

    def broken_stream_turn(*args, **kwargs):
        yield AgentTurnDeltaOutput.model_validate({
            "chat": "已更新需求文档。",
            "artifact_update": {
                "type": "replace",
                "markdown": "# 需求分析文档\n\n## 1. 被测系统与边界\n内容",
            },
            "stage_action": None,
            "warnings": [],
        })
        raise AgentRuntimeSchemaError("Unterminated string in raw JSON stream")

    runtime.stream_turn.side_effect = broken_stream_turn
    mock_build_runtime.return_value = runtime
    persistence = FakePersistence()

    events = list(stream_agent_run_events(
        _request(),
        api_key="test-api-key",
        base_url="https://api.deepseek.com/v1",
        model_name="deepseek-chat",
        persistence=persistence,
    ))

    assert isinstance(events[0], RunStartedEvent)
    assert isinstance(events[1], AgentTurnDeltaEvent)
    assert isinstance(events[2], ErrorEvent)
    assert len(events) == 3
    assert events[2].code == "SCHEMA_VALIDATION_FAILED"
    assert events[2].diagnostic is not None
    assert events[2].diagnostic.phase == "structured_output"

    call_names = [call[0] for call in persistence.calls]
    assert "append_assistant_message" not in call_names
    assert "record_artifact_version" not in call_names
    metric = persistence.calls[-1][1]
    assert persistence.calls[-1][0] == "record_turn_metric"
    assert metric["status"] == "error"
    assert metric["error_code"] == "SCHEMA_VALIDATION_FAILED"
```

- [x] **Step 2: Run the stream service test**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_stream_services.py::test_stream_agent_run_events_errors_after_partial_delta_without_persisting_artifact -q
```

Expected: pass with current stream service after Task 2, because it already maps runtime schema errors to typed error events.

---

### Task 4: Focused Regression

**Files:**
- No implementation files unless failures identify real regressions.

- [x] **Step 1: Run runtime and stream focused tests**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_fails_final_json_truncation_after_partial_delta tools/new-agents/backend/tests/test_stream_services.py::test_stream_agent_run_events_errors_after_partial_delta_without_persisting_artifact -q
```

Expected: pass.

- [x] **Step 2: Run existing raw JSON streaming matrix**

Run the matrix command from `docs/TESTING.md` for 17 stages, or run the broader file if command length becomes unwieldy:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py -q
```

Expected: pass; successful partial streaming stages still produce final `AgentTurnOutput`.

- [x] **Step 3: Run shared backend regression**

Run:

```bash
.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_stream_services.py tools/new-agents/backend/tests/test_workflow_contract_sync.py tools/new-agents/backend/tests/test_agent_contracts.py -q
```

Expected: pass.

---

### Task 5: Todo Record and Batch Verification

**Files:**
- Modify: `docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md`
- Modify only if necessary: `docs/TESTING.md`, `docs/api-contracts.md`

- [x] **Step 1: Re-read the latest todo before editing**

Run:

```bash
sed -n '1,260p' docs/todos/2026-07-08-new-agents-structured-artifact-failure-reduction.md
```

- [x] **Step 2: Update 第 2 轮 execution record**

Record:

- `artifact_truncated` pseudo-final output removed.
- partial delta can still appear before final error.
- no `agent_turn`, no artifact persistence, no stage advancement on invalid final JSON.
- verification commands and results.

- [x] **Step 3: Run batch verification before commit / push decision**

Run:

```bash
./scripts/test/test-local.sh new-agents
```

Expected: New Agents backend and frontend suites pass. If this is too broad or blocked by existing unrelated environment issues, record exact failure and run the closest CI-equivalent focused suite.

- [ ] **Step 4: Commit and push boundary**

After verification passes and only intended files are staged, create a focused commit for this independent engineering trust closure. Push to GitHub when the branch remote and permissions are available. If push is temporarily unsafe because current worktree contains unrelated dirty files or verification is incomplete, record the exact reason in the final status.
