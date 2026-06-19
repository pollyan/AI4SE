# New Agents Persistent Artifact Summary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist deterministic current artifact summaries in a server-side context summary table and have the context builder consume them.

**Architecture:** Add an `AgentContextSummary` SQLAlchemy model and repository upsert path inside `record_artifact_version`. Extract deterministic artifact summary formatting to a backend helper shared by persistence and context builder. Snapshot responses expose summaries, and context builder prefers persisted summaries with fallback to current artifacts for old data.

**Tech Stack:** Python 3.11, Flask-SQLAlchemy, pytest.

---

## File Structure

- Create: `tools/new-agents/backend/context_summary_format.py`
  - Owns deterministic artifact content normalization and truncation.
- Modify: `tools/new-agents/backend/models.py`
  - Add `AgentContextSummary` model and `AgentRun.context_summaries` relationship.
- Modify: `tools/new-agents/backend/run_persistence.py`
  - Upsert current artifact summary on `record_artifact_version`.
  - Include `contextSummaries` in `get_run_snapshot`.
- Modify: `tools/new-agents/backend/context_builder.py`
  - Use persisted `contextSummaries` first, fallback to artifact current content.
- Modify: `tools/new-agents/backend/tests/test_run_persistence.py`
  - Add summary persistence tests.
- Modify: `tools/new-agents/backend/tests/test_context_builder.py`
  - Add persisted summary preference test.
- Modify docs:
  - `docs/ARCHITECTURE.md`
  - `docs/TESTING.md`
  - `docs/todos/new-agents-evolution.md`

## Task 1: RED Persistence Tests

- [ ] **Step 1: Write failing tests**

In `test_run_persistence.py`, add:

```python
def test_record_artifact_version_persists_current_artifact_summary(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")

        record_artifact_version(run.id, "CLARIFY", "# 结论\n- 目标：提升转化")
        snapshot = get_run_snapshot(run.id)

    assert snapshot["contextSummaries"] == [
        {
            "sourceType": "artifact",
            "sourceStageId": "CLARIFY",
            "summaryType": "current_artifact",
            "content": "# 结论\n- 目标：提升转化",
        }
    ]
```

Add a second test recording the same run/stage twice and assert only one summary exists with the second content.

- [ ] **Step 2: Run RED**

Run: `cd tools/new-agents/backend && python3 -m pytest tests/test_run_persistence.py -q`

Expected: FAIL because `contextSummaries` and `AgentContextSummary` do not exist yet.

## Task 2: GREEN Model And Repository

- [ ] **Step 1: Add model**

Add `AgentContextSummary` with a unique constraint on `run_id`, `source_type`, `source_stage_id`, `summary_type`.

- [ ] **Step 2: Add shared formatter**

Create `context_summary_format.py` with:

```python
ARTIFACT_MAX_CHARS = 1200
ARTIFACT_TRUNCATION_NOTICE = "\n[该阶段产物摘要已截断]"
CURRENT_ARTIFACT_SUMMARY_TYPE = "current_artifact"

def normalize_artifact_content(content: str) -> str:
    return "\n".join(line.rstrip() for line in content.strip().splitlines() if line.strip())

def build_artifact_summary_content(content: str) -> str | None:
    summary = normalize_artifact_content(content)
    if not summary:
        return None
    if len(summary) > ARTIFACT_MAX_CHARS:
        summary = summary[:ARTIFACT_MAX_CHARS].rstrip() + ARTIFACT_TRUNCATION_NOTICE
    return summary
```

- [ ] **Step 3: Upsert summary**

In `record_artifact_version`, after the artifact version is flushed, build summary content and upsert the `AgentContextSummary` row for the run/stage.

- [ ] **Step 4: Include summaries in snapshot**

Return `contextSummaries` from `get_run_snapshot`.

- [ ] **Step 5: Run persistence tests**

Run: `cd tools/new-agents/backend && python3 -m pytest tests/test_run_persistence.py -q`

Expected: PASS.

## Task 3: Context Builder Uses Persisted Summaries

- [ ] **Step 1: Add failing preference test**

In `test_context_builder.py`, record a long artifact, then mutate the persisted summary content through the model and assert the prompt uses the persisted summary value instead of recalculating from raw artifact content.

- [ ] **Step 2: Implement preference**

In `context_builder.py`, import the shared formatter and build artifact blocks from `snapshot["contextSummaries"]` where `sourceType == "artifact"` and `summaryType == "current_artifact"`. If no such summaries exist, fallback to `snapshot["artifacts"]`.

- [ ] **Step 3: Run context tests**

Run: `cd tools/new-agents/backend && python3 -m pytest tests/test_context_builder.py -q`

Expected: PASS.

## Task 4: Verification And Docs

- [ ] **Step 1: Run focused backend tests**

Run: `cd tools/new-agents/backend && python3 -m pytest tests/test_run_persistence.py tests/test_context_builder.py tests/test_stream_services.py tests/test_agent_endpoint.py -q`

Expected: PASS.

- [ ] **Step 2: Run backend full tests**

Run: `cd tools/new-agents/backend && python3 -m pytest -q`

Expected: PASS with one existing skipped test.

- [ ] **Step 3: Update docs and todo**

Record `agent_context_summaries`, snapshot summaries, and remaining P1 #6 gaps.

- [ ] **Step 4: Run whitespace check**

Run: `git diff --check`

Expected: no output and exit code 0.
