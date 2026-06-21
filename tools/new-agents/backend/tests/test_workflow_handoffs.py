import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ["FLASK_TESTING"] = "1"

from app import create_app
from models import db
from run_persistence import create_agent_run, get_run_snapshot, record_artifact_version
from workflow_handoffs import export_run_handoffs, start_workflow_handoff


BLUEPRINT_MARKDOWN = """需求蓝图

## 1. 产品概述
AI 测试资产管理平台。

## 3. 核心需求
自动生成测试策略和用例。
"""


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


def test_export_run_handoffs_returns_configured_lisa_targets(app):
    with app.app_context():
        run = create_agent_run("VALUE_DISCOVERY", "alex", "BLUEPRINT")
        record_artifact_version(run.id, "BLUEPRINT", BLUEPRINT_MARKDOWN)

        result = export_run_handoffs(run.id)

    assert result["runId"] == run.id
    assert result["sourceWorkflowId"] == "VALUE_DISCOVERY"
    assert [
        (handoff["targetWorkflowId"], handoff["targetStageId"], handoff["targetAgentId"])
        for handoff in result["handoffs"]
    ] == [
        ("TEST_DESIGN", "CLARIFY", "lisa"),
        ("REQ_REVIEW", "REVIEW", "lisa"),
    ]
    first = result["handoffs"][0]
    assert first["sourceStageId"] == "BLUEPRINT"
    assert first["sourceArtifactVersion"] == 1
    assert "VALUE_DISCOVERY/BLUEPRINT" in first["prompt"]
    assert "TEST_DESIGN/CLARIFY" in first["prompt"]
    assert "AI 测试资产管理平台" in first["prompt"]
    assert "Alex 产出的需求蓝图" not in first["prompt"]


def test_export_run_handoffs_returns_empty_without_required_artifact(app):
    with app.app_context():
        run = create_agent_run("VALUE_DISCOVERY", "alex", "JOURNEY")

        result = export_run_handoffs(run.id)

    assert result["handoffs"] == []


def test_export_run_handoffs_returns_empty_for_non_source_workflow(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")

        result = export_run_handoffs(run.id)

    assert result["handoffs"] == []


def test_start_workflow_handoff_creates_target_run_with_handoff_prompt(app):
    with app.app_context():
        source_run = create_agent_run("VALUE_DISCOVERY", "alex", "BLUEPRINT")
        record_artifact_version(source_run.id, "BLUEPRINT", BLUEPRINT_MARKDOWN)
        source_run_id = source_run.id

        result = start_workflow_handoff(
            source_run.id,
            "value-discovery-blueprint-to-test-design",
        )
        target_snapshot = get_run_snapshot(result["targetRunId"])

    assert result["sourceRunId"] == source_run_id
    assert result["targetRunId"]
    assert result["targetWorkflowId"] == "TEST_DESIGN"
    assert result["targetStageId"] == "CLARIFY"
    assert result["targetAgentId"] == "lisa"
    assert target_snapshot["run"]["workflowId"] == "TEST_DESIGN"
    assert target_snapshot["run"]["agentId"] == "lisa"
    assert target_snapshot["run"]["currentStageId"] == "CLARIFY"
    assert target_snapshot["messages"] == [
        {
            "role": "user",
            "content": result["prompt"],
            "sequenceIndex": 1,
        }
    ]


def test_start_workflow_handoff_rejects_unknown_candidate(app):
    with app.app_context():
        source_run = create_agent_run("VALUE_DISCOVERY", "alex", "BLUEPRINT")
        record_artifact_version(source_run.id, "BLUEPRINT", BLUEPRINT_MARKDOWN)

        with pytest.raises(ValueError, match="未知 handoff"):
            start_workflow_handoff(source_run.id, "missing-handoff")
