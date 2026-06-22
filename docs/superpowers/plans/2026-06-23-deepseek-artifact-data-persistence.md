# DeepSeek Artifact Data Persistence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist validated DeepSeek-compatible `artifact_data` with each generated artifact version and expose it in run snapshots for audit and later quality diagnostics.

**Architecture:** Keep the shared Agent Runtime, typed SSE, artifact contract, and run persistence path. The renderer attaches validated JSON-safe `artifact_data` to `AgentTurnOutput`; stream persistence stores it beside Markdown; snapshot returns it as `artifactData` while old/manual artifact versions return `null`.

**Tech Stack:** Python 3.11, Flask, SQLAlchemy, Pydantic, pytest, existing New Agents backend runtime.

---

### Task 1: RED tests for renderer output metadata

**Files:**
- Modify: `tools/new-agents/backend/tests/test_artifact_data_renderers.py`

- [ ] Add an assertion to the existing clarify renderer test that `first.artifact_data` equals `VALID_CLARIFY_ARTIFACT_DATA`.
- [ ] Run `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_artifact_data_renderers.py::test_render_clarify_artifact_data_is_deterministic_and_contract_valid -q`.
- [ ] Expected RED result before implementation: `AttributeError` or assertion failure because `AgentTurnOutput` has no persisted `artifact_data`.

### Task 2: RED tests for persistence and snapshot

**Files:**
- Modify: `tools/new-agents/backend/tests/test_run_persistence.py`

- [ ] Extend `test_run_snapshot_returns_messages_and_current_artifacts` so the current generated artifact includes `artifactData`.
- [ ] Add a focused test proving a manual artifact version without `artifact_data` returns `artifactData is None`.
- [ ] Run `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_run_persistence.py -q`.
- [ ] Expected RED result before implementation: `record_artifact_version()` rejects `artifact_data` or snapshot omits `artifactData`.

### Task 3: RED tests for stream persistence and endpoint snapshot

**Files:**
- Modify: `tools/new-agents/backend/tests/test_stream_services.py`
- Modify: `tools/new-agents/backend/tests/test_agent_endpoint.py`

- [ ] Update `FakePersistence.record_artifact_version` to accept keyword-only `artifact_data` and record it.
- [ ] Add a stream service assertion that final output `artifact_data` is passed to persistence.
- [ ] Update the persisted endpoint snapshot assertion to include `artifactData`.
- [ ] Run `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_stream_services.py tools/new-agents/backend/tests/test_agent_endpoint.py -q`.
- [ ] Expected RED result before implementation: stream service records no structured data and endpoint snapshot omits it.

### Task 4: Implement output, persistence, snapshot, and migration

**Files:**
- Modify: `tools/new-agents/backend/agent_contracts.py`
- Modify: `tools/new-agents/backend/artifact_data_renderers.py`
- Modify: `tools/new-agents/backend/models.py`
- Modify: `tools/new-agents/backend/run_persistence.py`
- Modify: `tools/new-agents/backend/stream_services.py`
- Modify: `tools/new-agents/backend/app.py`

- [ ] Add optional `artifact_data: dict[str, Any] | None = None` to `AgentTurnOutput`.
- [ ] In `render_agent_turn_from_artifact_data()`, include `artifact_data.model_dump(mode="json")` in the final `AgentTurnOutput`.
- [ ] Add `artifact_data_json = db.Column(db.Text)` to `AgentArtifactVersion`.
- [ ] Serialize `artifact_data` with `json.dumps(..., ensure_ascii=False)` in `record_artifact_version()`.
- [ ] Deserialize `artifact_data_json` in `_artifact_snapshot()` and return it as `artifactData`.
- [ ] Pass `artifact_data=final_output.artifact_data` from `stream_agent_run_events()`.
- [ ] Add `_ensure_agent_artifact_version_columns()` in `app.py` and call it from `init_db()`.

### Task 5: Documentation and verification

**Files:**
- Modify: `docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md`

- [ ] Mark simultaneous `artifact_data` persistence as completed.
- [ ] Keep real DeepSeek smoke as a remaining optional validation topic.
- [ ] Run the combined backend verification command:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_artifact_data_renderers.py tools/new-agents/backend/tests/test_run_persistence.py tools/new-agents/backend/tests/test_stream_services.py tools/new-agents/backend/tests/test_agent_endpoint.py tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_agent_contracts.py -q
```

- [ ] Run `git diff --check`.
- [ ] Commit only this milestone's files.
