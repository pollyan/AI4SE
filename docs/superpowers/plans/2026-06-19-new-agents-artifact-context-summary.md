# New Agents Artifact Context Summary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Include persisted current artifact summaries in the backend runtime context so later turns can use prior stage outputs without frontend prompt stitching.

**Architecture:** Extend the existing backend `context_builder.py` only. It will read artifacts already returned by `get_run_snapshot`, format bounded deterministic summaries, and include them in the same prompt budget and truncation warning path used for persisted messages.

**Tech Stack:** Python 3.11, Flask-SQLAlchemy, pytest.

---

## File Structure

- Modify: `tools/new-agents/backend/context_builder.py`
  - Add deterministic artifact summary formatting and include artifact summary blocks in the bounded prompt.
- Modify: `tools/new-agents/backend/tests/test_context_builder.py`
  - Add RED tests for artifact summary inclusion, no-artifact compatibility, artifact-level truncation, and total prompt budget truncation behavior.
- Modify docs:
  - `docs/ARCHITECTURE.md`
  - `docs/TESTING.md`
  - `docs/todos/new-agents-evolution.md`

## Task 1: RED Context Builder Artifact Tests

- [ ] **Step 1: Write failing tests**

Add tests like:

```python
def test_build_run_context_prompt_includes_current_artifact_summaries(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "STRATEGY")
        record_artifact_version(run.id, "CLARIFY", "# 澄清结论\n- 核心目标：提升登录转化")
        append_run_message(run.id, "user", "上一轮输入")

        prompt = build_run_context_prompt(run.id, "继续设计策略")

    assert "已保存阶段产物摘要" in prompt
    assert "[阶段产物: CLARIFY]" in prompt
    assert "核心目标：提升登录转化" in prompt
    assert prompt.endswith("[用户]\n继续设计策略")
```

Add a second test that records a very long artifact and asserts the summary contains an artifact-level truncation notice while keeping the current user prompt.

- [ ] **Step 2: Run test to verify failure**

Run: `cd tools/new-agents/backend && python3 -m pytest tests/test_context_builder.py -q`

Expected: FAIL because current `context_builder.py` ignores snapshot artifacts.

## Task 2: GREEN Artifact Summary Formatting

- [ ] **Step 1: Implement deterministic formatting**

In `context_builder.py`, add constants and helpers:

```python
ARTIFACT_SUMMARY_HEADING = "[已保存阶段产物摘要]"
ARTIFACT_MAX_CHARS = 1200
ARTIFACT_TRUNCATION_NOTICE = "\n[该阶段产物摘要已截断]"

def _normalize_artifact_content(content: str) -> str:
    return "\n".join(line.rstrip() for line in content.strip().splitlines() if line.strip())

def _format_artifact_summary(artifact: dict) -> str | None:
    content = _normalize_artifact_content(artifact["content"])
    if not content:
        return None
    if len(content) > ARTIFACT_MAX_CHARS:
        content = content[:ARTIFACT_MAX_CHARS].rstrip() + ARTIFACT_TRUNCATION_NOTICE
    return f"[阶段产物: {artifact['stageId']}]\n{content}"
```

- [ ] **Step 2: Include summaries in prompt blocks**

Build an optional artifact summary block before messages:

```python
artifact_summaries = [
    formatted
    for artifact in snapshot["artifacts"]
    if (formatted := _format_artifact_summary(artifact)) is not None
]
context_blocks = []
if artifact_summaries:
    context_blocks.append("\n\n".join([ARTIFACT_SUMMARY_HEADING, *artifact_summaries]))
blocks = [*context_blocks, *prior_messages, current_message]
```

- [ ] **Step 3: Run focused test**

Run: `cd tools/new-agents/backend && python3 -m pytest tests/test_context_builder.py -q`

Expected: PASS.

## Task 3: Budget Behavior And Regression Verification

- [ ] **Step 1: Add/update budget test**

Add a test where artifact + old message exceeds `max_chars`, then assert:

```python
context = build_run_context(run.id, "当前输入", max_chars=80)
assert context.prompt.endswith("[用户]\n当前输入")
assert context.warnings == ["context_truncated"]
```

- [ ] **Step 2: Run backend focused tests**

Run: `cd tools/new-agents/backend && python3 -m pytest tests/test_context_builder.py tests/test_stream_services.py tests/test_sse_encoder.py -q`

Expected: PASS.

- [ ] **Step 3: Run backend full tests**

Run: `cd tools/new-agents/backend && python3 -m pytest -q`

Expected: PASS with one existing skipped test.

## Task 4: Docs And Final Checks

- [ ] **Step 1: Update docs**

Record that service-side context now includes bounded artifact summaries:

- `docs/ARCHITECTURE.md`: context builder bullet.
- `docs/TESTING.md`: context builder testing bullets.
- `docs/todos/new-agents-evolution.md`: P1 #6 progress and remaining work.

- [ ] **Step 2: Run whitespace check**

Run: `git diff --check`

Expected: no output and exit code 0.
