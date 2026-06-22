# DeepSeek V4 Real Smoke Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Align the optional real DeepSeek V4 smoke test with the current `artifact_data -> deterministic renderer -> artifact contract` architecture.

**Architecture:** Keep the shared Agent Runtime and raw JSON streaming path. The smoke test builds a `PydanticAgentRuntime` with `RawStreamingConfig`, instructs the model to return `artifact_data`, then verifies the backend renderer produced the final Markdown artifact.

**Tech Stack:** Python 3.11, pytest, Flask/PydanticAI backend test utilities, existing New Agents runtime.

---

### Task 1: RED test for smoke env loading

**Files:**
- Modify: `tools/new-agents/backend/tests/test_agent_real_smoke.py`

- [ ] Add local tests proving `DEEPSEEK_V4_SMOKE_*` values override `NEW_AGENTS_SMOKE_*`, and missing env raises `pytest.skip.Exception`.
- [ ] Run `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_agent_real_smoke.py::test_deepseek_smoke_env_prefers_deepseek_specific_values tools/new-agents/backend/tests/test_agent_real_smoke.py::test_deepseek_smoke_env_skips_when_required_values_are_missing -q`.
- [ ] Expected RED: tests fail because DeepSeek-specific env helper does not exist.

### Task 2: RED test for artifact_data-oriented smoke contract

**Files:**
- Modify: `tools/new-agents/backend/tests/test_agent_real_smoke.py`

- [ ] Add a local assertion that `SMOKE_SYSTEM_PROMPT` names `artifact_data`, rejects direct Markdown, and does not require `artifact_update.markdown`.
- [ ] Run the focused test.
- [ ] Expected RED: existing prompt still requires direct Markdown artifact output.

### Task 3: Implement smoke gate alignment

**Files:**
- Modify: `tools/new-agents/backend/tests/test_agent_real_smoke.py`

- [ ] Replace direct Markdown smoke prompt with artifact_data prompt.
- [ ] Use `RawStreamingConfig` + `PydanticAgentRuntime` so smoke exercises raw JSON streaming.
- [ ] Keep final output assertions on rendered Markdown headings, Mermaid, chat cleanliness, and no stage action.
- [ ] Keep default skip behavior without env.

### Task 4: Update DeepSeek todo and verify

**Files:**
- Modify: `docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md`

- [ ] Record that the real smoke gate is optional and now aligned with `artifact_data`.
- [ ] Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest -p no:cacheprovider tools/new-agents/backend/tests/test_agent_real_smoke.py tools/new-agents/backend/tests/test_agent_runtime.py -q
```

- [ ] Run `git diff --check`.
- [ ] Commit the focused change.
