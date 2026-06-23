# DeepSeek V4 Evidence Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a local deterministic and optional real DeepSeek V4 evidence gate for the New Agents structured artifact output path.

**Architecture:** Create one backend evidence module that reuses existing `agent_runtime` helpers, raw JSON streaming, `artifact_data` renderer, and artifact contract. The module returns structured `passed` / `failed` / `skipped` results, exposes a CLI JSON summary, and never treats missing real-model credentials as success. No frontend UI, API path, runtime branch, or renderer fork is added.

**Tech Stack:** Python 3.11, pytest, existing Flask backend test fixtures, Pydantic model validation, current New Agents Agent Runtime.

---

## File Structure

- Create: `tools/new-agents/backend/deepseek_v4_smoke_evidence.py`
  - Responsibility: DeepSeek V4 provider/config evidence, 17-stage artifact_data coverage evidence, local deterministic smoke, optional real smoke, JSON CLI summary.
- Create: `tools/new-agents/backend/tests/test_deepseek_v4_smoke_evidence.py`
  - Responsibility: RED/PASS tests for provider evidence, stage coverage, local smoke request payload, failure semantics, skipped real smoke, CLI summary.
- Modify: `docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md`
  - Responsibility: record evidence gate completion and clarify real smoke conditions.
- Modify: `docs/todos/refactor/README.md`
  - Responsibility: update active refactor todo index for DeepSeek evidence gate state.
- Create: `docs/superpowers/specs/2026-06-24-deepseek-v4-evidence-gate-design.md`
  - Responsibility: Chinese spec with Superpowers brainstorming self-Q&A.
- Create: `docs/superpowers/plans/2026-06-24-deepseek-v4-evidence-gate.md`
  - Responsibility: this implementation plan.

## Commit Boundary

One focused milestone commit:

```bash
git commit -m "feat(new-agents): 增加 DeepSeek V4 证据门禁"
```

The commit includes evidence code, tests, spec, plan, and todo updates because they define one engineering trust loop.

## Task 1: RED Tests

**Files:**
- Create: `tools/new-agents/backend/tests/test_deepseek_v4_smoke_evidence.py`

- [ ] **Step 1: Write import and provider evidence tests**

Create the test file with imports that currently fail because the module does not exist:

```python
import json

from deepseek_v4_smoke_evidence import (
    DEEPSEEK_V4_EXPECTED_ARTIFACT_DATA_STAGES,
    EvidenceStatus,
    collect_deepseek_v4_evidence,
    run_deepseek_v4_provider_evidence,
    run_deepseek_v4_stage_coverage_evidence,
    run_local_deepseek_v4_evidence,
    run_optional_real_deepseek_v4_smoke,
)


def test_provider_evidence_uses_json_object_and_disabled_thinking():
    result = run_deepseek_v4_provider_evidence()

    assert result.status == EvidenceStatus.PASSED
    assert result.details["capability_tier"] == "json_object_only"
    assert result.details["response_format"] == {"type": "json_object"}
    assert result.details["model_settings"] == {
        "extra_body": {"thinking": {"type": "disabled"}}
    }
    assert result.details["agent_retries"] == 3
```

- [ ] **Step 2: Write stage coverage test**

Add:

```python
def test_stage_coverage_evidence_covers_all_deepseek_artifact_data_stages():
    result = run_deepseek_v4_stage_coverage_evidence()

    assert result.status == EvidenceStatus.PASSED
    assert result.details["covered_count"] == 17
    assert set(result.details["covered_stages"]) == {
        f"{workflow}/{stage}"
        for workflow, stage in DEEPSEEK_V4_EXPECTED_ARTIFACT_DATA_STAGES
    }
```

- [ ] **Step 3: Write local smoke passed test**

Add:

```python
from test_agent_runtime import FakeAgent
from test_artifact_data_renderers import VALID_REQ_REVIEW_REPORT_ARTIFACT_DATA


def _valid_req_review_report_json() -> str:
    return json.dumps(
        {
            "chat": "我已整理正式需求评审报告，请确认右侧内容。",
            "artifact_data": VALID_REQ_REVIEW_REPORT_ARTIFACT_DATA,
            "stage_action": None,
            "warnings": [],
        },
        ensure_ascii=False,
    )


def test_local_evidence_uses_json_object_and_renders_artifact(monkeypatch):
    calls = []

    def fake_stream_chat_completion_content(**kwargs):
        calls.append(kwargs)
        yield _valid_req_review_report_json()

    monkeypatch.setattr(
        "agent_runtime.stream_chat_completion_content",
        fake_stream_chat_completion_content,
    )

    result = run_local_deepseek_v4_evidence(agent=FakeAgent({}))

    assert result.status == EvidenceStatus.PASSED
    assert result.details["workflow_id"] == "REQ_REVIEW"
    assert result.details["stage_id"] == "REPORT"
    assert result.details["artifact_title"] == "# 需求评审报告"
    assert calls[0]["response_format"] == {"type": "json_object"}
    assert calls[0]["extra_body"] == {"thinking": {"type": "disabled"}}
    assert "artifact_data" in calls[0]["messages"][0]["content"]
    assert "artifact_update.markdown" not in calls[0]["messages"][0]["content"]
```

- [ ] **Step 4: Write local failure and optional real smoke tests**

Add:

```python
def test_local_evidence_reports_contract_failure(monkeypatch):
    def fake_stream_chat_completion_content(**_kwargs):
        yield json.dumps(
            {
                "chat": "缺少右侧产物数据。",
                "artifact_data": {"document_info": {}},
                "stage_action": None,
                "warnings": [],
            },
            ensure_ascii=False,
        )

    monkeypatch.setattr(
        "agent_runtime.stream_chat_completion_content",
        fake_stream_chat_completion_content,
    )

    result = run_local_deepseek_v4_evidence(agent=FakeAgent({}))

    assert result.status == EvidenceStatus.FAILED
    assert result.reason
    assert "artifact_data" in result.reason or "validation" in result.reason.lower()


def test_optional_real_smoke_skips_without_credentials():
    result = run_optional_real_deepseek_v4_smoke(env={})

    assert result.status == EvidenceStatus.SKIPPED
    assert "NEW_AGENTS_DEEPSEEK_V4_SMOKE_API_KEY" in result.reason


def test_optional_real_smoke_rejects_non_deepseek_v4_model():
    result = run_optional_real_deepseek_v4_smoke(
        env={
            "NEW_AGENTS_DEEPSEEK_V4_SMOKE_API_KEY": "test-key",
            "NEW_AGENTS_DEEPSEEK_V4_SMOKE_BASE_URL": "https://api.deepseek.com",
            "NEW_AGENTS_DEEPSEEK_V4_SMOKE_MODEL": "deepseek-chat",
        },
        agent=FakeAgent({}),
    )

    assert result.status == EvidenceStatus.FAILED
    assert "must start with deepseek-v4-" in result.reason
```

- [ ] **Step 5: Write collector test**

Add:

```python
def test_collect_evidence_includes_provider_coverage_local_and_real_smoke(monkeypatch):
    def fake_stream_chat_completion_content(**_kwargs):
        yield _valid_req_review_report_json()

    monkeypatch.setattr(
        "agent_runtime.stream_chat_completion_content",
        fake_stream_chat_completion_content,
    )

    results = collect_deepseek_v4_evidence(env={}, agent=FakeAgent({}))
    by_name = {result.name: result for result in results}

    assert by_name["deepseek-v4-provider-capability"].status == EvidenceStatus.PASSED
    assert by_name["deepseek-v4-artifact-data-stage-coverage"].status == EvidenceStatus.PASSED
    assert by_name["deepseek-v4-local-deterministic-smoke"].status == EvidenceStatus.PASSED
    assert by_name["deepseek-v4-optional-real-smoke"].status == EvidenceStatus.SKIPPED
```

- [ ] **Step 6: Run RED tests**

Run:

```bash
/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest tools/new-agents/backend/tests/test_deepseek_v4_smoke_evidence.py -q
```

Expected: fails with `ModuleNotFoundError: No module named 'deepseek_v4_smoke_evidence'`.

## Task 2: Evidence Module Implementation

**Files:**
- Create: `tools/new-agents/backend/deepseek_v4_smoke_evidence.py`

- [ ] **Step 1: Implement result types and constants**

Create:

```python
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

from agent_contracts import AgentTurnOutput
from agent_runtime import (
    AgentRuntimeDependencyError,
    AgentRuntimeModelError,
    AgentRuntimeSchemaError,
    PydanticAgentRuntime,
    RawStreamingConfig,
    build_agent_retries,
    build_model_settings,
    build_structured_output_instruction,
    resolve_structured_output_capability,
    supports_artifact_data_rendering,
)

class EvidenceStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass(frozen=True)
class EvidenceResult:
    name: str
    status: EvidenceStatus
    reason: str = ""
    details: dict[str, Any] = field(default_factory=dict)
```

Also define `DEEPSEEK_V4_MODEL`, `DEEPSEEK_V4_BASE_URL`, `SMOKE_WORKFLOW_ID`, `SMOKE_STAGE_ID`, `REAL_SMOKE_REQUIRED_ENV`, and `DEEPSEEK_V4_EXPECTED_ARTIFACT_DATA_STAGES`.

- [ ] **Step 2: Implement provider and coverage evidence**

Implement:

```python
def run_deepseek_v4_provider_evidence(model_name: str = DEEPSEEK_V4_MODEL) -> EvidenceResult:
    capability = resolve_structured_output_capability(model_name)
    model_settings = build_model_settings(model_name)
    retries = build_agent_retries(model_name)
    passed = (
        capability.tier == "json_object_only"
        and capability.response_format == {"type": "json_object"}
        and model_settings == {"extra_body": {"thinking": {"type": "disabled"}}}
        and retries == 3
    )
    return EvidenceResult(...PASSED or FAILED...)

def run_deepseek_v4_stage_coverage_evidence() -> EvidenceResult:
    missing = []
    covered = []
    for workflow_id, stage_id in DEEPSEEK_V4_EXPECTED_ARTIFACT_DATA_STAGES:
        if not supports_artifact_data_rendering(workflow_id, stage_id):
            missing.append(f"{workflow_id}/{stage_id}")
            continue
        instruction = build_structured_output_instruction(workflow_id, stage_id)
        if "artifact_data" not in instruction:
            missing.append(f"{workflow_id}/{stage_id}: missing artifact_data instruction")
            continue
        covered.append(f"{workflow_id}/{stage_id}")
    return EvidenceResult(...PASSED if not missing else FAILED...)
```

- [ ] **Step 3: Implement local and optional real smoke**

Implement `_build_runtime()`, `_run_runtime_evidence()`, `run_local_deepseek_v4_evidence()`, and `run_optional_real_deepseek_v4_smoke()`. Use `REQ_REVIEW/REPORT` as representative stage and assert final artifact title is `# 需求评审报告`.

- [ ] **Step 4: Implement collector and CLI**

Implement:

```python
def collect_deepseek_v4_evidence(*, env=None, agent=None) -> list[EvidenceResult]:
    return [
        run_deepseek_v4_provider_evidence(),
        run_deepseek_v4_stage_coverage_evidence(),
        run_local_deepseek_v4_evidence(agent=agent or _NoopAgent()),
        run_optional_real_deepseek_v4_smoke(env=env, agent=agent),
    ]
```

Add JSON serialization and `main()` that exits `1` if any result status is `FAILED`, otherwise `0`.

- [ ] **Step 5: Run GREEN tests**

Run:

```bash
/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest tools/new-agents/backend/tests/test_deepseek_v4_smoke_evidence.py -q
```

Expected: all selected evidence tests pass.

## Task 3: Todo Records

**Files:**
- Modify: `docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md`
- Modify: `docs/todos/refactor/README.md`

- [ ] **Step 1: Update DeepSeek todo current progress**

Add a current progress bullet:

```markdown
- 2026-06-24 已完成 DeepSeek V4 结构化输出证据门禁：新增本地 deterministic evidence、17 stage coverage evidence、provider capability evidence 和可选真实 smoke skipped/failed/passed 结果；真实 DeepSeek V4 Flash smoke 仍需要显式凭证、网络和额度。
```

- [ ] **Step 2: Update validation commands**

Add:

```markdown
- `.venv/bin/python -m pytest tools/new-agents/backend/tests/test_deepseek_v4_smoke_evidence.py -q`
- `.venv/bin/python tools/new-agents/backend/deepseek_v4_smoke_evidence.py`
```

- [ ] **Step 3: Update README current entry**

Clarify the DeepSeek todo now tracks optional real smoke and future confidence/persistence work, not stage migration.

## Task 4: Verification and Commit

**Files:**
- All touched files.

- [ ] **Step 1: Run CI-equivalent verification**

Run:

```bash
/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest tools/new-agents/backend/tests/test_deepseek_v4_smoke_evidence.py -q
/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m pytest tools/new-agents/backend/tests/test_agent_runtime.py tools/new-agents/backend/tests/test_agent_contracts.py -q
/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python -m py_compile tools/new-agents/backend/deepseek_v4_smoke_evidence.py tools/new-agents/backend/agent_runtime.py
/Users/anhui/Documents/myProgram/AI4SE/.venv/bin/python tools/new-agents/backend/deepseek_v4_smoke_evidence.py
git diff --check
```

Expected: pytest and py_compile pass; CLI exits 0 with provider/stage/local passed and optional real smoke skipped when credentials are absent; diff check produces no output.

- [ ] **Step 2: Inspect scope**

Run:

```bash
git status --short
git diff --stat
```

Expected: only evidence module/tests/spec/plan/todo files changed.

- [ ] **Step 3: Commit**

Stage and commit:

```bash
git add docs/superpowers/specs/2026-06-24-deepseek-v4-evidence-gate-design.md docs/superpowers/plans/2026-06-24-deepseek-v4-evidence-gate.md docs/todos/refactor/2026-06-23-deepseek-v4-structured-artifact-data.md docs/todos/refactor/README.md tools/new-agents/backend/deepseek_v4_smoke_evidence.py tools/new-agents/backend/tests/test_deepseek_v4_smoke_evidence.py
git commit -m "feat(new-agents): 增加 DeepSeek V4 证据门禁"
```

## Plan Self-Review

- Spec coverage: tasks cover provider evidence, 17-stage coverage, local deterministic smoke, optional real smoke skip/fail, CLI JSON summary, todo updates, and verification.
- Placeholder scan: no placeholder-only instructions remain; every step has exact files, code shape, commands, and expected output.
- Type consistency: field and function names are consistent across spec, tests, module, and plan: `EvidenceStatus`, `EvidenceResult`, `run_deepseek_v4_provider_evidence`, `run_deepseek_v4_stage_coverage_evidence`, `run_local_deepseek_v4_evidence`, `run_optional_real_deepseek_v4_smoke`, `collect_deepseek_v4_evidence`.
