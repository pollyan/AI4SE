# New Agents Artifact Data Real Streaming Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Emit real, renderer-backed Artifact Markdown deltas before final `agent_turn` when raw JSON streaming has already produced a complete `artifact_data` object.

**Architecture:** Keep the shared `/api/agent/runs/stream` and Agent Runtime path. Add a small JSON value extractor in `agent_runtime.py`, reuse `render_agent_turn_from_artifact_data`, and preserve the existing frontend parser/store protocol.

**Tech Stack:** Python 3.11, Pydantic, pytest, TypeScript/Vitest regression coverage.

---

### Task 1: Backend Red Tests

**Files:**
- Modify: `tools/new-agents/backend/tests/test_agent_runtime.py`

- [ ] **Step 1: Add a CLARIFY red test**

Add a test where the model stream yields three chunks: JSON before `"artifact_data"`, the complete `"artifact_data": {...},` segment, then `"stage_action"` and `"warnings"`. Assert an `AgentTurnDeltaOutput` before final contains Markdown starting with `# 需求分析文档`.

- [ ] **Step 2: Add a STRATEGY red test**

Use `VALID_STRATEGY_ARTIFACT_DATA` with `workflow_id="TEST_DESIGN"` and `current_stage_id="STRATEGY"`. Assert a final-before delta contains `# 风险驱动测试策略蓝图`.

- [ ] **Step 3: Preserve the partial-object boundary**

Change the existing partial artifact-data test so the second chunk contains only part of the object body. Assert no pre-final artifact Markdown is emitted for that incomplete object.

- [ ] **Step 4: Run focused red tests**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_agent_runtime.py -k "artifact_data_before_final_output or partial_artifact_data" -q
```

Expected: the new complete-object streaming tests fail because current `build_partial_agent_delta` does not render `artifact_data` before final.

### Task 2: Shared Runtime Implementation

**Files:**
- Modify: `tools/new-agents/backend/agent_runtime.py`

- [ ] **Step 1: Add JSON object extraction**

Add an extractor near `extract_json_string_prefix`:

```python
def extract_json_object_prefix(text: str, key: str) -> dict[str, Any] | None:
    key_match = re.search(rf'"{re.escape(key)}"\s*:', text)
    if not key_match:
        return None
    index = key_match.end()
    while index < len(text) and text[index].isspace():
        index += 1
    if index >= len(text) or text[index] != "{":
        return None
    try:
        value, _ = json.JSONDecoder().raw_decode(text[index:])
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None
```

- [ ] **Step 2: Render complete partial artifact data**

Extend `build_partial_agent_delta` to accept optional `workflow_id` and `current_stage_id`. Keep legacy `markdown` extraction unchanged. If no `markdown` exists and a complete `artifact_data` object is available, call `render_agent_turn_from_artifact_data` with a minimal payload containing `chat`, `artifact_data`, `stage_action=None`, and `warnings=[]`. Return `artifact_update.replace` from the rendered output.

- [ ] **Step 3: Wire runtime context**

In `_stream_raw_json_turn`, call `build_partial_agent_delta(accumulated, workflow_id=workflow_id, current_stage_id=current_stage_id)` so the extractor has renderer context.

- [ ] **Step 4: Keep invalid partials silent**

Catch `ValueError` and `ValidationError` from partial rendering and return chat-only delta when chat is available. Do not emit a placeholder artifact.

### Task 3: Verify and Record

**Files:**
- Modify if needed: `docs/todos/refactor/2026-06-25-new-agents-artifact-streaming-not-working-p0.md`

- [ ] **Step 1: Run backend focused tests**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_agent_runtime.py -k "artifact_data_before_final_output or partial_artifact_data" -q
```

Expected: all selected tests pass.

- [ ] **Step 2: Run frontend parser regression**

Run:

```bash
cd tools/new-agents/frontend && npm run test -- src/core/__tests__/llm.test.ts
```

Expected: parser tests keep passing because protocol shape is unchanged.

- [ ] **Step 3: Run broad local validation**

Run:

```bash
./scripts/test/test-local.sh all
```

Expected: full local suite passes, or any environment-only blocker is recorded with exact command output and follow-up.

- [ ] **Step 4: Update todo status**

If verification passes, update the P0 todo with completion evidence and leave the position-indicator todo active as the next UX story.
