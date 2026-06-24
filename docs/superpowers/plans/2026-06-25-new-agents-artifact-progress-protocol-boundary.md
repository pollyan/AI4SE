# New Agents Artifact Progress Protocol Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent artifact progress/debug placeholders from entering New Agents right-side formal artifact rendering.

**Architecture:** Keep the shared Agent Runtime and typed SSE path. Backend partial streaming emits chat and formal artifact markdown only; partial `artifact_data` does not synthesize artifact markdown. Frontend keeps a defensive filter for legacy or malformed `agent_delta` payloads.

**Tech Stack:** Python 3.11, pytest, Flask/PydanticAI backend, TypeScript, React, Vitest, pnpm.

**Execution Status:** Completed on 2026-06-25.

---

## File Structure

- Modify: `tools/new-agents/backend/tests/test_agent_runtime.py`
  - Rewrite the current progress-placeholder test into a protocol guard test.
- Modify: `tools/new-agents/backend/agent_runtime.py`
  - Remove partial `artifact_data` progress Markdown generation from `build_partial_agent_delta()`.
- Modify: `tools/new-agents/frontend/src/core/llm.ts`
  - Keep `hasRenderableArtifactDelta()` as a defensive boundary in the shared stream parser.
- Modify: `tools/new-agents/frontend/src/core/__tests__/llm.test.ts`
  - Keep regression coverage for legacy progress-placeholder delta.
- Modify: `docs/api-contracts.md`
  - Document that `artifact_update.replace` carries only formal artifact Markdown.
- Modify: `docs/TESTING.md`
  - Document backend and frontend regression responsibilities for this protocol boundary.
- Modify: `docs/todos/refactor/2026-06-24-new-agents-artifact-streaming-position-indicator.md`
  - Record that protocol cleanup is a prerequisite consumed by this milestone.

### Task 1: Backend RED Test

**Files:**
- Modify: `tools/new-agents/backend/tests/test_agent_runtime.py`

- [x] **Step 1: Rewrite the failing backend test**

Change `test_runtime_raw_json_stream_turn_streams_artifact_progress_for_artifact_data` to:

```python
def test_runtime_raw_json_stream_turn_does_not_emit_progress_artifact_for_partial_artifact_data(
    monkeypatch,
):
    final_json = json.dumps(
        {
            "chat": "正在生成结构化产物。",
            "artifact_data": VALID_CLARIFY_ARTIFACT_DATA,
            "stage_action": None,
            "warnings": [],
        },
        ensure_ascii=False,
    )
    chunks = [
        final_json[: final_json.index('"artifact_data"')],
        final_json[
            final_json.index('"artifact_data"') : final_json.index('"stage_action"')
        ],
        final_json[final_json.index('"stage_action"') :],
    ]

    def fake_stream_chat_completion_content(**kwargs):
        yield from chunks

    monkeypatch.setattr(
        "agent_runtime.stream_chat_completion_content",
        fake_stream_chat_completion_content,
    )
    runtime = PydanticAgentRuntime(
        FakeAgent({}),
        raw_streaming_config=RawStreamingConfig(
            api_key="test-api-key",
            base_url="https://api.test.com/v1",
            model_name="test-model",
            system_prompt="system prompt",
        ),
    )

    outputs = list(
        runtime.stream_turn(
            "用户需求",
            workflow_id="TEST_DESIGN",
            current_stage_id="CLARIFY",
        )
    )

    partial_markdowns = [
        output.artifact_update.markdown
        for output in outputs[:-1]
        if isinstance(output, AgentTurnDeltaOutput)
        and output.artifact_update is not None
        and output.artifact_update.type == "replace"
        and output.artifact_update.markdown is not None
    ]

    assert partial_markdowns == []
    assert outputs[-1].artifact_update.markdown.startswith("# 需求分析文档")
```

- [x] **Step 2: Run the targeted test and verify RED**

Run from `tools/new-agents/backend`:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_does_not_emit_progress_artifact_for_partial_artifact_data -q
```

Expected: FAIL because current backend emits `# 产出物生成中` as `artifact_update.replace`.

### Task 2: Backend GREEN Implementation

**Files:**
- Modify: `tools/new-agents/backend/agent_runtime.py`

- [x] **Step 1: Remove progress placeholder synthesis**

Change `build_partial_agent_delta()` to:

```python
def build_partial_agent_delta(text: str) -> AgentTurnDeltaOutput | None:
    chat = extract_json_string_prefix(text, "chat")
    markdown = extract_json_string_prefix(text, "markdown")
    if not chat and not markdown:
        return None
    return AgentTurnDeltaOutput(
        chat=chat,
        artifact_update=(
            {"type": "replace", "markdown": markdown} if markdown else None
        ),
    )
```

Delete `build_artifact_data_progress_markdown()`.

- [x] **Step 2: Run targeted backend test and verify GREEN**

Run from `tools/new-agents/backend`:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider tests/test_agent_runtime.py::test_runtime_raw_json_stream_turn_does_not_emit_progress_artifact_for_partial_artifact_data -q
```

Expected: PASS.

### Task 3: Frontend Defensive Boundary

**Files:**
- Modify: `tools/new-agents/frontend/src/core/llm.ts`
- Modify: `tools/new-agents/frontend/src/core/__tests__/llm.test.ts`

- [x] **Step 1: Keep shared parser guard**

Confirm `mapAgentDeltaToStreamChunks()` only treats a delta as renderable when `hasRenderableArtifactDelta(output)` is true, and that `# 产出物生成中` is filtered.

- [x] **Step 2: Run frontend stream parser tests**

Run from repository root:

```bash
corepack pnpm --dir tools/new-agents/frontend exec vitest run src/core/__tests__/llm.test.ts --pool=forks --maxWorkers=1
```

Expected: PASS.

### Task 4: Contract Documentation

**Files:**
- Modify: `docs/api-contracts.md`
- Modify: `docs/TESTING.md`
- Modify: `docs/todos/refactor/2026-06-24-new-agents-artifact-streaming-position-indicator.md`

- [x] **Step 1: Update API contract**

Add that `artifact_update.type="replace"` must contain formal artifact Markdown only and must not contain progress/debug placeholders.

- [x] **Step 2: Update testing guidance**

Add backend runtime and frontend stream parser expectations for rejecting or ignoring progress/debug placeholders.

- [x] **Step 3: Update active todo**

Record that this milestone consumes the protocol cleanup prerequisite, while the chapter-position indicator remains active.

### Task 5: Verification and Commit

**Files:**
- All files listed above.

- [x] **Step 1: Run focused backend test file**

Run from `tools/new-agents/backend`:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -p no:cacheprovider tests/test_agent_runtime.py -q
```

Expected: PASS.

- [x] **Step 2: Run frontend tests and lint**

Run from repository root:

```bash
corepack pnpm --dir tools/new-agents/frontend exec vitest run src/core/__tests__/llm.test.ts --pool=forks --maxWorkers=1
corepack pnpm --dir tools/new-agents/frontend run lint
```

Expected: PASS.

- [x] **Step 3: Check diff hygiene**

Run:

```bash
git diff --check
git status --short
```

Expected: no whitespace errors; unrelated dirty files remain unstaged.

- [x] **Step 4: Commit focused milestone**

Stage only this milestone:

```bash
git add docs/superpowers/specs/2026-06-25-new-agents-artifact-progress-protocol-boundary-design.md docs/superpowers/plans/2026-06-25-new-agents-artifact-progress-protocol-boundary.md docs/api-contracts.md docs/TESTING.md docs/todos/refactor/2026-06-24-new-agents-artifact-streaming-position-indicator.md tools/new-agents/backend/agent_runtime.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/frontend/src/core/llm.ts tools/new-agents/frontend/src/core/__tests__/llm.test.ts
git commit -m "fix(new-agents): 收束 artifact 进度占位协议边界"
```

Expected: focused commit created.

## Self-Review

- Spec coverage: plan covers backend protocol, frontend defensive boundary, docs, todo, and verification.
- Placeholder scan: no `TBD` / `TODO` placeholders.
- Type consistency: all changed names match existing Python and TypeScript modules.
