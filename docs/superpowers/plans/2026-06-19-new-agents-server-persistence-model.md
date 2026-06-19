# New Agents Server Persistence Model Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the first backend persistence layer for New Agents runs, messages, artifacts, and artifact versions.

**Architecture:** Extend the existing Flask-SQLAlchemy model module with generic run/session tables and add a small repository module that validates workflow/stage IDs against `agent_contracts.WORKFLOW_STAGES`. This slice is deliberately backend-only so later API/SSE work can reuse the repository without changing the typed runtime contract.

**Tech Stack:** Python 3.11, Flask-SQLAlchemy, SQLite-backed pytest fixtures.

---

## File Structure

- Create: `tools/new-agents/backend/tests/test_run_persistence.py`
  - Covers repository behavior using the same temporary SQLite pattern as existing backend tests.
- Modify: `tools/new-agents/backend/models.py`
  - Adds `AgentRun`, `AgentMessage`, `AgentArtifact`, and `AgentArtifactVersion`.
- Create: `tools/new-agents/backend/run_persistence.py`
  - Provides validated create/append/version/snapshot functions.
- Modify: `docs/todos/new-agents-evolution.md`
  - Records the completed first slice and verification evidence.

## Task 1: Repository Contract Tests

**Files:**
- Create: `tools/new-agents/backend/tests/test_run_persistence.py`

- [ ] **Step 1: Write the failing repository tests**

```python
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ["FLASK_TESTING"] = "1"

from app import create_app
from models import AgentArtifact, AgentArtifactVersion, AgentMessage, AgentRun, db
from run_persistence import (
    append_run_message,
    create_agent_run,
    get_run_snapshot,
    record_artifact_version,
)


@pytest.fixture
def app():
    db_fd, db_path = tempfile.mkstemp()
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        }
    )
    with app.app_context():
        db.create_all()
        yield app
    os.close(db_fd)
    os.unlink(db_path)


def test_create_run_persists_generic_workflow_metadata(app):
    with app.app_context():
        run = create_agent_run(
            workflow_id="TEST_DESIGN",
            agent_id="lisa",
            current_stage_id="CLARIFY",
            model="gpt-test",
        )

        fetched = AgentRun.query.get(run.id)
        assert fetched is not None
        assert fetched.workflow_id == "TEST_DESIGN"
        assert fetched.agent_id == "lisa"
        assert fetched.current_stage_id == "CLARIFY"
        assert fetched.status == "active"
        assert fetched.model == "gpt-test"


def test_messages_are_appended_with_stable_sequence(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")

        first = append_run_message(run.id, "user", "请分析这个需求")
        second = append_run_message(run.id, "assistant", "我会先做需求澄清")

        assert first.sequence_index == 1
        assert second.sequence_index == 2
        assert [message.content for message in AgentMessage.query.order_by(AgentMessage.sequence_index)] == [
            "请分析这个需求",
            "我会先做需求澄清",
        ]


def test_artifact_versions_increment_per_run_stage(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")

        first = record_artifact_version(run.id, "CLARIFY", "# 需求分析文档\n初版")
        second = record_artifact_version(run.id, "CLARIFY", "# 需求分析文档\n二版")

        artifact = AgentArtifact.query.filter_by(run_id=run.id, stage_id="CLARIFY").one()
        assert first.version_number == 1
        assert second.version_number == 2
        assert artifact.current_version_id == second.id
        assert AgentArtifactVersion.query.filter_by(artifact_id=artifact.id).count() == 2


def test_run_snapshot_returns_messages_and_current_artifacts(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY", model="gpt-test")
        append_run_message(run.id, "user", "输入")
        append_run_message(run.id, "assistant", "回复")
        record_artifact_version(run.id, "CLARIFY", "初版")
        record_artifact_version(run.id, "CLARIFY", "二版")

        snapshot = get_run_snapshot(run.id)

    assert snapshot["run"]["id"] == run.id
    assert snapshot["run"]["workflowId"] == "TEST_DESIGN"
    assert snapshot["run"]["agentId"] == "lisa"
    assert snapshot["run"]["currentStageId"] == "CLARIFY"
    assert snapshot["run"]["status"] == "active"
    assert snapshot["run"]["model"] == "gpt-test"
    assert [message["role"] for message in snapshot["messages"]] == ["user", "assistant"]
    assert [message["sequenceIndex"] for message in snapshot["messages"]] == [1, 2]
    assert snapshot["artifacts"] == [
        {
            "stageId": "CLARIFY",
            "content": "二版",
            "versionNumber": 2,
        }
    ]


@pytest.mark.parametrize(
    ("workflow_id", "stage_id", "message"),
    [
        ("UNKNOWN", "CLARIFY", "未知 workflowId: UNKNOWN"),
        ("TEST_DESIGN", "UNKNOWN", "workflowId 与 stageId 不匹配: TEST_DESIGN/UNKNOWN"),
    ],
)
def test_create_run_rejects_unknown_workflow_stage(app, workflow_id, stage_id, message):
    with app.app_context(), pytest.raises(ValueError, match=message):
        create_agent_run(workflow_id, "lisa", stage_id)


def test_record_artifact_rejects_stage_outside_run_workflow(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")

        with pytest.raises(ValueError, match="workflowId 与 stageId 不匹配: TEST_DESIGN/REPORT"):
            record_artifact_version(run.id, "REPORT", "wrong stage")


def test_append_message_rejects_unknown_role(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")

        with pytest.raises(ValueError, match="未知 message role: system"):
            append_run_message(run.id, "system", "hidden")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd tools/new-agents/backend && python3 -m pytest tests/test_run_persistence.py -q`
Expected: FAIL because `AgentRun` and `run_persistence` do not exist yet.

## Task 2: Minimal Models And Repository

**Files:**
- Modify: `tools/new-agents/backend/models.py`
- Create: `tools/new-agents/backend/run_persistence.py`

- [ ] **Step 1: Add SQLAlchemy models**

Add generic run, message, artifact, and version tables in `models.py`, using the existing `db.Model` style.

- [ ] **Step 2: Add repository functions**

Add `create_agent_run`, `append_run_message`, `record_artifact_version`, and `get_run_snapshot` in `run_persistence.py`. Validate workflow/stage IDs with `WORKFLOW_STAGES`, validate message roles as `user` or `assistant`, and raise `ValueError` with explicit messages for invalid inputs.

- [ ] **Step 3: Run test to verify it passes**

Run: `cd tools/new-agents/backend && python3 -m pytest tests/test_run_persistence.py -q`
Expected: PASS.

## Task 3: Existing Backend Regression Check

**Files:**
- Test: `tools/new-agents/backend/tests/test_models.py`
- Test: `tools/new-agents/backend/tests/test_config_service.py`
- Test: `tools/new-agents/backend/tests/test_run_persistence.py`

- [ ] **Step 1: Run focused backend regression**

Run: `cd tools/new-agents/backend && python3 -m pytest tests/test_models.py tests/test_config_service.py tests/test_run_persistence.py -q`
Expected: PASS.

- [ ] **Step 2: Run diff whitespace check**

Run: `git diff --check`
Expected: no output and exit code 0.

## Task 4: Todo Progress Record

**Files:**
- Modify: `docs/todos/new-agents-evolution.md`

- [ ] **Step 1: Record first persistence slice**

Append progress under P1 #5 noting that the backend model/repository slice is complete, API/SSE/frontend integration remains future work, and include exact verification commands.
