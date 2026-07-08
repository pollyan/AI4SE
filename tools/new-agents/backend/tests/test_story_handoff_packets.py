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
from test_artifact_data_renderers import VALID_USER_STORY_HANDOFF_ARTIFACT_DATA


HANDOFF_MARKDOWN = """# 单故事 Handoff 清单

## 1. Ready Stories

| Story ID | 标题 | 来源需求 |
| --- | --- | --- |
| US-001 | 生成澄清问题 | REQ-001 |

## 2. 单故事需求包

```json
{"storyId":"US-001"}
```
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


def _create_user_story_run(artifact_data=None, content=HANDOFF_MARKDOWN):
    run = create_agent_run("USER_STORY_BREAKDOWN", "alex", "HANDOFF")
    record_artifact_version(
        run.id,
        "HANDOFF",
        content,
        artifact_data=(
            copy.deepcopy(VALID_USER_STORY_HANDOFF_ARTIFACT_DATA)
            if artifact_data is None
            else artifact_data
        ),
    )
    return run


def test_story_handoff_candidates_return_ready_stories_from_artifact_data(app):
    with app.app_context():
        run = _create_user_story_run()

        result = list_story_handoff_candidates(run.id, "HANDOFF")

    assert result["runId"] == run.id
    assert result["workflowId"] == "USER_STORY_BREAKDOWN"
    assert result["stageId"] == "HANDOFF"
    assert result["sourceArtifactVersion"] == 1
    assert result["sourceArtifactDigest"].startswith("sha256:")
    assert result["candidates"] == [
        {
            "storyId": "US-001",
            "title": "生成澄清问题",
            "requirementIds": ["REQ-001"],
            "userValue": "测试负责人能在设计前发现缺失业务规则",
            "readyReason": "验收标准和业务规则已明确",
        },
        {
            "storyId": "US-002",
            "title": "生成测试策略",
            "requirementIds": ["REQ-002"],
            "userValue": "测试负责人能快速形成可评审测试方案",
            "readyReason": "输入、输出和准出条件明确",
        },
    ]


def test_create_story_handoff_packet_persists_requirement_only_payload(app):
    with app.app_context():
        run = _create_user_story_run()

        packet = create_story_handoff_packet(run.id, "HANDOFF", "US-001")
        result = list_story_handoff_packets(run.id, "HANDOFF")

    assert packet["storyId"] == "US-001"
    assert packet["sourceRunId"] == run.id
    assert packet["sourceWorkflowId"] == "USER_STORY_BREAKDOWN"
    assert packet["sourceStageId"] == "HANDOFF"
    assert packet["sourceArtifactVersion"] == 1
    assert packet["sourceArtifactDigest"].startswith("sha256:")
    assert packet["requirementIds"] == ["REQ-001"]
    assert packet["acceptanceCriteria"] == [
        "输出需求事实清单",
        "输出阻断性待澄清问题",
        "输出 P0 风险线索",
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
        run = _create_user_story_run()
        create_story_handoff_packet(run.id, "HANDOFF", "US-001")
        record_artifact_version(
            run.id,
            "HANDOFF",
            HANDOFF_MARKDOWN + "\n\n## 更新后的故事清单\n",
            artifact_data=copy.deepcopy(VALID_USER_STORY_HANDOFF_ARTIFACT_DATA),
        )

        result = list_story_handoff_packets(run.id, "HANDOFF")

    assert result["sourceArtifactVersion"] == 2
    assert result["packets"][0]["isStale"] is True
    assert result["packets"][0]["currentSourceArtifactVersion"] == 2
    assert result["packets"][0]["packet"]["sourceArtifactVersion"] == 1


def test_create_story_handoff_packet_rejects_missing_artifact_data(app):
    with app.app_context():
        run = create_agent_run("USER_STORY_BREAKDOWN", "alex", "HANDOFF")
        record_artifact_version(run.id, "HANDOFF", HANDOFF_MARKDOWN)

        with pytest.raises(ValueError, match="缺少结构化 artifact_data"):
            create_story_handoff_packet(run.id, "HANDOFF", "US-001")


def test_create_story_handoff_packet_rejects_unknown_story_id(app):
    with app.app_context():
        run = _create_user_story_run()

        with pytest.raises(ValueError, match="未知 ready story"):
            create_story_handoff_packet(run.id, "HANDOFF", "US-404")


def test_story_handoff_candidates_reject_invalid_stage(app):
    with app.app_context():
        run = _create_user_story_run()

        with pytest.raises(ValueError, match="只能从 USER_STORY_BREAKDOWN/HANDOFF"):
            list_story_handoff_candidates(run.id, "STORIES")


def test_story_handoff_packet_routes_create_and_read_packet(client, app):
    with app.app_context():
        run = _create_user_story_run()
        run_id = run.id

    candidates_response = client.get(
        f"/api/agent/runs/{run_id}/story-handoff-candidates?stageId=HANDOFF"
    )
    assert candidates_response.status_code == 200
    assert candidates_response.get_json()["candidates"][0]["storyId"] == "US-001"

    create_response = client.post(
        f"/api/agent/runs/{run_id}/story-handoff-packets",
        json={"stageId": "HANDOFF", "storyId": "US-001"},
    )
    assert create_response.status_code == 200
    assert create_response.get_json()["storyId"] == "US-001"

    list_response = client.get(
        f"/api/agent/runs/{run_id}/story-handoff-packets?stageId=HANDOFF"
    )
    assert list_response.status_code == 200
    payload = list_response.get_json()
    assert payload["packets"][0]["packet"]["storyId"] == "US-001"
