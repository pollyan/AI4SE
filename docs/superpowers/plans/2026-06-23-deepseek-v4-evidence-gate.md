# DeepSeek V4 Evidence Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a diagnosable DeepSeek V4 structured artifact evidence gate that records readiness, skip reasons, and optional live smoke results without adding a DeepSeek-specific runtime.

**Architecture:** Reuse the existing New Agents backend Agent Runtime, raw JSON streaming config, artifact_data renderer, and artifact contract. Add a small backend evidence helper plus deterministic tests; live DeepSeek calls remain optional and are gated by existing `NEW_AGENTS_SMOKE_*` environment variables.

**Tech Stack:** Python 3.11, pytest, Pydantic models already used by New Agents backend, existing OpenAI-compatible raw JSON streaming client.

---

## File Map

- `tools/new-agents/backend/agent_runtime.py`: expose the artifact_data-enabled stage list as a stable constant used by runtime and evidence helper.
- `tools/new-agents/backend/deepseek_v4_smoke_evidence.py`: new evidence helper and CLI entry.
- `tools/new-agents/backend/tests/test_deepseek_v4_smoke_evidence.py`: deterministic TDD coverage for config diagnosis, readiness evidence, evidence writing, and fake live smoke.
- `docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md`: record this milestone and remaining real-smoke conditions.
- `docs/todos/refactor/README.md`: update active entry wording if the DeepSeek todo becomes evidence-only rather than stage-migration work.

## Task 1: RED - Evidence Config And Readiness Tests

**Files:**
- Create: `tools/new-agents/backend/tests/test_deepseek_v4_smoke_evidence.py`
- Modify later: `tools/new-agents/backend/deepseek_v4_smoke_evidence.py`
- Modify later: `tools/new-agents/backend/agent_runtime.py`

- [ ] Add tests that import the intended API:

```python
from pathlib import Path

from deepseek_v4_smoke_evidence import (
    build_deepseek_v4_readiness_evidence,
    load_deepseek_v4_smoke_config,
    write_deepseek_v4_evidence,
)


def test_config_reports_missing_smoke_environment(tmp_path: Path) -> None:
    config = load_deepseek_v4_smoke_config({}, evidence_dir=tmp_path)

    assert config.ready is False
    assert config.missing_env == (
        "NEW_AGENTS_SMOKE_API_KEY",
        "NEW_AGENTS_SMOKE_BASE_URL",
        "NEW_AGENTS_SMOKE_MODEL",
    )
    assert "NEW_AGENTS_SMOKE_API_KEY" in config.skip_reason
    assert config.evidence_dir == tmp_path


def test_readiness_evidence_summarizes_deepseek_v4_artifact_data_path(tmp_path: Path) -> None:
    env = {
        "NEW_AGENTS_SMOKE_API_KEY": "test-key",
        "NEW_AGENTS_SMOKE_BASE_URL": "https://api.deepseek.com",
        "NEW_AGENTS_SMOKE_MODEL": "deepseek-v4-flash",
    }
    config = load_deepseek_v4_smoke_config(env, evidence_dir=tmp_path)

    evidence = build_deepseek_v4_readiness_evidence(config)

    assert evidence["status"] == "ready"
    assert evidence["model"] == "deepseek-v4-flash"
    assert evidence["capability"]["tier"] == "json_object_only"
    assert evidence["capability"]["response_format"] == {"type": "json_object"}
    assert evidence["model_settings"]["extra_body"] == {"thinking": {"type": "disabled"}}
    assert len(evidence["artifact_data_stages"]) == 17
    assert {"workflow_id": "TEST_DESIGN", "stage_id": "CLARIFY"} in evidence["artifact_data_stages"]
    assert {"workflow_id": "IDEA_BRAINSTORM", "stage_id": "CONCEPT"} in evidence["artifact_data_stages"]


def test_write_evidence_records_skip_reason(tmp_path: Path) -> None:
    config = load_deepseek_v4_smoke_config({}, evidence_dir=tmp_path)
    evidence = build_deepseek_v4_readiness_evidence(config)

    path = write_deepseek_v4_evidence(evidence, tmp_path)

    payload = path.read_text(encoding="utf-8")
    assert '"status": "skipped"' in payload
    assert "NEW_AGENTS_SMOKE_MODEL" in payload
    assert path.name.startswith("deepseek-v4-smoke-")
```

- [ ] Run: `python3 -m pytest tools/new-agents/backend/tests/test_deepseek_v4_smoke_evidence.py -q`
- [ ] Expected: FAIL because `deepseek_v4_smoke_evidence` does not exist.

## Task 2: GREEN - Config, Readiness And Evidence Writer

**Files:**
- Create: `tools/new-agents/backend/deepseek_v4_smoke_evidence.py`
- Modify: `tools/new-agents/backend/agent_runtime.py`

- [ ] In `agent_runtime.py`, extract the inline stage set into `ARTIFACT_DATA_RENDERING_STAGES` and make `supports_artifact_data_rendering()` check the constant.
- [ ] In `deepseek_v4_smoke_evidence.py`, implement:
  - `DeepSeekV4SmokeConfig`
  - `load_deepseek_v4_smoke_config(env=None, evidence_dir=None)`
  - `build_deepseek_v4_readiness_evidence(config)`
  - `write_deepseek_v4_evidence(evidence, evidence_dir)`
- [ ] Run: `python3 -m pytest tools/new-agents/backend/tests/test_deepseek_v4_smoke_evidence.py -q`
- [ ] Expected: PASS for the three tests from Task 1.

## Task 3: RED/GREEN - Fake Live Smoke Evidence

**Files:**
- Modify: `tools/new-agents/backend/tests/test_deepseek_v4_smoke_evidence.py`
- Modify: `tools/new-agents/backend/deepseek_v4_smoke_evidence.py`

- [ ] Add a fake runtime test:

```python
class FakeRuntime:
    last_token_usage = 321

    def stream_turn(self, prompt: str, *, workflow_id: str, current_stage_id: str):
        from agent_runtime import parse_agent_turn_output_text
        from test_artifact_data_renderers import VALID_CLARIFY_ARTIFACT_DATA
        import json

        yield parse_agent_turn_output_text(
            json.dumps(
                {
                    "chat": "我已整理需求澄清基线。",
                    "artifact_data": VALID_CLARIFY_ARTIFACT_DATA,
                    "stage_action": None,
                    "warnings": [],
                },
                ensure_ascii=False,
            ),
            workflow_id=workflow_id,
            current_stage_id=current_stage_id,
        )


def test_live_smoke_evidence_uses_runtime_and_records_artifact_summary(tmp_path: Path) -> None:
    env = {
        "NEW_AGENTS_SMOKE_API_KEY": "test-key",
        "NEW_AGENTS_SMOKE_BASE_URL": "https://api.deepseek.com",
        "NEW_AGENTS_SMOKE_MODEL": "deepseek-v4-flash",
    }
    config = load_deepseek_v4_smoke_config(env, evidence_dir=tmp_path)

    evidence = run_deepseek_v4_structured_smoke(
        config,
        runtime_factory=lambda *_args, **_kwargs: FakeRuntime(),
    )

    assert evidence["status"] == "passed"
    assert evidence["workflow_id"] == "TEST_DESIGN"
    assert evidence["stage_id"] == "CLARIFY"
    assert evidence["token_usage"] == 321
    assert evidence["artifact"]["has_markdown"] is True
    assert "# 需求分析文档" in evidence["artifact"]["headings"]
```

- [ ] Run the new test and confirm FAIL because `run_deepseek_v4_structured_smoke` is missing.
- [ ] Implement `run_deepseek_v4_structured_smoke(config, runtime_factory=build_pydantic_agent_runtime)` using `stream_turn()` for `TEST_DESIGN/CLARIFY`.
- [ ] Run: `python3 -m pytest tools/new-agents/backend/tests/test_deepseek_v4_smoke_evidence.py -q`
- [ ] Expected: PASS.

## Task 4: CLI Entry And Optional Real Smoke

**Files:**
- Modify: `tools/new-agents/backend/deepseek_v4_smoke_evidence.py`
- Modify: `tools/new-agents/backend/tests/test_deepseek_v4_smoke_evidence.py`

- [ ] Add a `main()` that:
  - loads env config,
  - writes readiness evidence when config is not ready,
  - runs live smoke and writes passed/failed evidence when config is ready,
  - prints the evidence path,
  - exits `0` for skipped or passed, `1` for live smoke failure.
- [ ] Add deterministic tests for model mismatch and CLI skip output if needed.
- [ ] Run: `python3 -m pytest tools/new-agents/backend/tests/test_deepseek_v4_smoke_evidence.py -q`

## Task 5: Documentation And Todo Update

**Files:**
- Modify: `docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md`
- Modify: `docs/todos/refactor/README.md`

- [ ] Record this evidence gate milestone as completed.
- [ ] Clarify that 17 stage migrations are complete and future work should be capability-package level, not stage-by-stage Superpowers slices.
- [ ] Record the optional real command:

```bash
NEW_AGENTS_SMOKE_API_KEY=... \
NEW_AGENTS_SMOKE_BASE_URL=https://api.deepseek.com \
NEW_AGENTS_SMOKE_MODEL=deepseek-v4-flash \
python3 tools/new-agents/backend/deepseek_v4_smoke_evidence.py
```

## Task 6: Verification And Commit

**Files:**
- All touched files.

- [ ] Run: `python3 -m pytest tools/new-agents/backend/tests/test_deepseek_v4_smoke_evidence.py -q`
- [ ] Run: `python3 -m pytest tools/new-agents/backend/tests/test_agent_runtime.py -q`
- [ ] Run: `python3 -m py_compile tools/new-agents/backend/deepseek_v4_smoke_evidence.py tools/new-agents/backend/agent_runtime.py`
- [ ] Run: `git diff --check`
- [ ] If `NEW_AGENTS_SMOKE_*` are not set, do not run live DeepSeek smoke; report the skipped command and missing env.
- [ ] Stage only this milestone's files.
- [ ] Commit with message: `feat(new-agents): 增加 DeepSeek V4 证据门禁`
