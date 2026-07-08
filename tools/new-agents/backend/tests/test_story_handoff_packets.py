import copy
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ["FLASK_TESTING"] = "1"

from app import create_app
from models import db
from run_persistence import create_agent_run, record_artifact_version
from story_handoff_packets import (
    create_story_handoff_packet,
    list_story_handoff_candidates,
    list_story_handoff_packets,
)
from test_artifact_data_renderers import VALID_STORY_BREAKDOWN_ARTIFACT_DATA


SPRINT_PLAN_MARKDOWN = """# 用户故事拆解包

## User Story Backlog

| Story ID | 标题 | 来源需求 |
| --- | --- | --- |
| US-001 | 需求澄清基线 | EPIC-001 |

## Sprint 切片建议
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


@pytest.fixture
def client(app):
    return app.test_client()


def _create_story_breakdown_run(artifact_data=None, content=SPRINT_PLAN_MARKDOWN):
    run = create_agent_run("STORY_BREAKDOWN", "alex", "SPRINT_PLAN")
    record_artifact_version(
        run.id,
        "SPRINT_PLAN",
        content,
        artifact_data=(
            copy.deepcopy(VALID_STORY_BREAKDOWN_ARTIFACT_DATA)
            if artifact_data is None
            else artifact_data
        ),
    )
    return run


def test_story_handoff_candidates_return_ready_stories_from_artifact_data(app):
    with app.app_context():
        run = _create_story_breakdown_run()

        result = list_story_handoff_candidates(run.id, "SPRINT_PLAN")

    assert result["runId"] == run.id
    assert result["workflowId"] == "STORY_BREAKDOWN"
    assert result["stageId"] == "SPRINT_PLAN"
    assert result["sourceArtifactVersion"] == 1
    assert result["sourceArtifactDigest"].startswith("sha256:")
    assert result["candidates"] == [
        {
            "storyId": "US-001",
            "title": "需求澄清基线",
            "requirementIds": ["EPIC-001", "AC-001"],
            "userValue": "作为测试负责人，我想把需求输入转成澄清清单，以便在开发前发现遗漏。",
            "readyReason": "状态：待评审；可测试性：高；Sprint：Sprint 1",
        },
        {
            "storyId": "US-002",
            "title": "测试策略生成",
            "requirementIds": ["EPIC-001"],
            "userValue": "作为测试负责人，我想自动获得风险、测试点和测试层级建议，以便快速组织评审。",
            "readyReason": "状态：待评审；可测试性：高；Sprint：Sprint 1",
        },
    ]


def test_create_story_handoff_packet_persists_requirement_only_payload(app):
    with app.app_context():
        run = _create_story_breakdown_run()

        packet = create_story_handoff_packet(run.id, "SPRINT_PLAN", "US-001")
        result = list_story_handoff_packets(run.id, "SPRINT_PLAN")

    assert packet["storyId"] == "US-001"
    assert packet["sourceRunId"] == run.id
    assert packet["sourceWorkflowId"] == "STORY_BREAKDOWN"
    assert packet["sourceStageId"] == "SPRINT_PLAN"
    assert packet["sourceArtifactVersion"] == 1
    assert packet["sourceArtifactDigest"].startswith("sha256:")
    assert packet["requirementIds"] == ["EPIC-001", "AC-001"]
    assert packet["acceptanceCriteria"] == [
        "输入需求后生成事实、边界、业务规则和待澄清问题。",
    ]
    forbidden_keys = {
        "tasks",
        "filePaths",
        "implementationPlan",
        "testCommands",
        "architecturePlan",
    }
    assert forbidden_keys.isdisjoint(packet)
    assert result["packets"][0]["packet"] == packet
    assert result["packets"][0]["isStale"] is False


def test_story_handoff_packets_mark_stale_after_source_artifact_changes(app):
    with app.app_context():
        run = _create_story_breakdown_run()
        create_story_handoff_packet(run.id, "SPRINT_PLAN", "US-001")
        record_artifact_version(
            run.id,
            "SPRINT_PLAN",
            SPRINT_PLAN_MARKDOWN + "\n\n## 更新后的故事清单\n",
            artifact_data=copy.deepcopy(VALID_STORY_BREAKDOWN_ARTIFACT_DATA),
        )

        result = list_story_handoff_packets(run.id, "SPRINT_PLAN")

    assert result["sourceArtifactVersion"] == 2
    assert result["packets"][0]["isStale"] is True
    assert result["packets"][0]["currentSourceArtifactVersion"] == 2
    assert result["packets"][0]["packet"]["sourceArtifactVersion"] == 1


def test_create_story_handoff_packet_rejects_missing_artifact_data(app):
    with app.app_context():
        run = create_agent_run("STORY_BREAKDOWN", "alex", "SPRINT_PLAN")
        record_artifact_version(run.id, "SPRINT_PLAN", SPRINT_PLAN_MARKDOWN)

        with pytest.raises(ValueError, match="缺少结构化 artifact_data"):
            create_story_handoff_packet(run.id, "SPRINT_PLAN", "US-001")


def test_create_story_handoff_packet_rejects_unknown_story_id(app):
    with app.app_context():
        run = _create_story_breakdown_run()

        with pytest.raises(ValueError, match="未知 ready story"):
            create_story_handoff_packet(run.id, "SPRINT_PLAN", "US-404")


def test_story_handoff_candidates_reject_invalid_stage(app):
    with app.app_context():
        run = _create_story_breakdown_run()

        with pytest.raises(ValueError, match="只能从 STORY_BREAKDOWN/SPRINT_PLAN"):
            list_story_handoff_candidates(run.id, "STORY_BACKLOG")


def test_story_handoff_packet_routes_create_and_read_packet(client, app):
    with app.app_context():
        run = _create_story_breakdown_run()
        run_id = run.id

    candidates_response = client.get(
        f"/api/agent/runs/{run_id}/story-handoff-candidates?stageId=SPRINT_PLAN"
    )
    assert candidates_response.status_code == 200
    assert candidates_response.get_json()["candidates"][0]["storyId"] == "US-001"

    create_response = client.post(
        f"/api/agent/runs/{run_id}/story-handoff-packets",
        json={"stageId": "SPRINT_PLAN", "storyId": "US-001"},
    )
    assert create_response.status_code == 200
    assert create_response.get_json()["storyId"] == "US-001"

    list_response = client.get(
        f"/api/agent/runs/{run_id}/story-handoff-packets?stageId=SPRINT_PLAN"
    )
    assert list_response.status_code == 200
    payload = list_response.get_json()
    assert payload["packets"][0]["packet"]["storyId"] == "US-001"
