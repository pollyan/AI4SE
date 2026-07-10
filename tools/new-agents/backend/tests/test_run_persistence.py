import os
import sys
import tempfile
import threading

import pytest
import run_persistence
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ["FLASK_TESTING"] = "1"

from app import create_app
from models import (
    AgentArtifact,
    AgentArtifactVersion,
    AgentMessage,
    AgentRun,
    AgentRunTurnRequest,
    db,
)
from run_persistence import (
    append_run_message,
    claim_agent_run_turn_request,
    clone_agent_run,
    complete_agent_run_turn,
    create_agent_run,
    fail_agent_run_turn_request,
    ensure_agent_run,
    get_runtime_observability_summary,
    get_run_snapshot,
    list_agent_runs,
    record_artifact_version,
    record_turn_metric,
    replace_artifact_collaboration_state,
    update_context_summary,
    update_run_artifact,
    upsert_manual_decision_summary,
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

        fetched = db.session.get(AgentRun, run.id)
        assert fetched is not None
        assert fetched.workflow_id == "TEST_DESIGN"
        assert fetched.agent_id == "lisa"
        assert fetched.current_stage_id == "CLARIFY"
        assert fetched.status == "active"
        assert fetched.model == "gpt-test"


def test_ensure_agent_run_reuses_existing_run_without_mutating_replay_state(app):
    with app.app_context():
        run = create_agent_run(
            workflow_id="TEST_DESIGN",
            agent_id="lisa",
            current_stage_id="CLARIFY",
            model="gpt-old",
        )

        reused = ensure_agent_run(
            "TEST_DESIGN",
            "lisa",
            "STRATEGY",
            run_id=run.id,
            model="gpt-new",
        )

        assert reused.id == run.id
        assert AgentRun.query.count() == 1
    assert reused.current_stage_id == "CLARIFY"
    assert reused.model == "gpt-old"


def test_ensure_agent_run_recovers_a_concurrent_first_run_create_conflict(
    app,
    monkeypatch,
):
    with app.app_context():
        concurrent_run = create_agent_run(
            "TEST_DESIGN",
            "lisa",
            "CLARIFY",
            model="gpt-concurrent",
        )
        original_get = db.session.get
        first_lookup = True

        def return_stale_absence(model, identifier, *args, **kwargs):
            nonlocal first_lookup
            if model is AgentRun and identifier == concurrent_run.id and first_lookup:
                first_lookup = False
                return None
            return original_get(model, identifier, *args, **kwargs)

        def report_unique_create_conflict(*args, **kwargs):
            raise IntegrityError("insert", {}, RuntimeError("duplicate run id"))

        monkeypatch.setattr(db.session, "get", return_stale_absence)
        monkeypatch.setattr(run_persistence, "create_agent_run", report_unique_create_conflict)

        reused = ensure_agent_run(
            "TEST_DESIGN",
            "lisa",
            "STRATEGY",
            run_id=concurrent_run.id,
            model="gpt-new",
        )

        assert reused.id == concurrent_run.id
        assert reused.current_stage_id == "CLARIFY"
        assert reused.model == "gpt-concurrent"


def test_messages_are_appended_with_stable_sequence(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")

        first = append_run_message(run.id, "user", "请分析这个需求")
        second = append_run_message(run.id, "assistant", "我会先做需求澄清")

        assert first.sequence_index == 1
        assert second.sequence_index == 2
        assert [
            message.content
            for message in AgentMessage.query.order_by(AgentMessage.sequence_index)
        ] == [
            "请分析这个需求",
            "我会先做需求澄清",
        ]


def test_complete_agent_run_turn_rolls_back_every_success_record_when_metric_write_fails(
    app,
    monkeypatch,
):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")
        append_run_message(run.id, "user", "请分析登录需求")

        def fail_metric_write(*args, **kwargs):
            raise SQLAlchemyError("metric storage unavailable")

        monkeypatch.setattr(run_persistence, "_stage_turn_metric", fail_metric_write)

        with pytest.raises(run_persistence.TurnPersistenceError):
            complete_agent_run_turn(
                run.id,
                stage_id="CLARIFY",
                assistant_content="已完成登录需求分析。",
                artifact_content="# 需求分析文档\n\n登录功能",
                artifact_data={"document_info": {"artifact_name": "登录需求"}},
                metric={
                    "workflow_id": "TEST_DESIGN",
                    "stage_id": "CLARIFY",
                    "model_name": "test-model",
                    "provider": "test-provider",
                    "status": "success",
                    "error_code": None,
                    "duration_ms": 1,
                    "input_chars": 8,
                    "output_chars": 20,
                    "estimated_tokens": 7,
                    "contract_retry_count": 0,
                },
            )

        assert [message.role for message in AgentMessage.query.all()] == ["user"]
        assert AgentArtifact.query.filter_by(run_id=run.id).count() == 0
        assert run.turn_metrics == []


def test_complete_agent_run_turn_reports_concurrent_unique_slot_conflict_without_partial_success(
    app,
    monkeypatch,
):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")
        append_run_message(run.id, "user", "请分析登录需求")

        def fail_metric_write(*args, **kwargs):
            raise IntegrityError("insert", {}, RuntimeError("unique slot"))

        monkeypatch.setattr(run_persistence, "_stage_turn_metric", fail_metric_write)

        with pytest.raises(run_persistence.TurnPersistenceConflictError):
            complete_agent_run_turn(
                run.id,
                stage_id="CLARIFY",
                assistant_content="已完成登录需求分析。",
                artifact_content="# 需求分析文档\n\n登录功能",
                artifact_data=None,
                metric={
                    "workflow_id": "TEST_DESIGN",
                    "stage_id": "CLARIFY",
                    "model_name": "test-model",
                    "provider": "test-provider",
                    "status": "success",
                    "error_code": None,
                    "duration_ms": 1,
                    "input_chars": 8,
                    "output_chars": 20,
                    "estimated_tokens": 7,
                    "contract_retry_count": 0,
                },
            )

        assert [message.role for message in AgentMessage.query.all()] == ["user"]
        assert AgentArtifact.query.filter_by(run_id=run.id).count() == 0


def test_turn_request_claim_is_idempotent_and_replays_completed_terminal_outcome(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")
        first = claim_agent_run_turn_request(
            run.id,
            request_id="req-login-001",
            stage_id="CLARIFY",
            user_content="请分析登录需求",
        )

        assert first.state == "new"
        assert [message.role for message in AgentMessage.query.all()] == ["user"]

        duplicate_active = claim_agent_run_turn_request(
            run.id,
            request_id="req-login-001",
            stage_id="CLARIFY",
            user_content="请分析登录需求",
        )
        assert duplicate_active.state == "active"
        assert AgentMessage.query.count() == 1

        terminal_event = {
            "type": "agent_turn",
            "output": {
                "chat": "已完成登录需求分析。",
                "artifact_update": {"type": "none"},
                "stage_action": None,
                "warnings": [],
            },
        }
        complete_agent_run_turn(
            run.id,
            request_id="req-login-001",
            stage_id="CLARIFY",
            assistant_content="已完成登录需求分析。",
            artifact_content=None,
            artifact_data=None,
            terminal_event=terminal_event,
            metric={
                "workflow_id": "TEST_DESIGN",
                "stage_id": "CLARIFY",
                "model_name": "test-model",
                "provider": "test-provider",
                "status": "success",
                "error_code": None,
                "duration_ms": 1,
                "input_chars": 8,
                "output_chars": 12,
                "estimated_tokens": 5,
                "contract_retry_count": 0,
            },
        )

        duplicate_completed = claim_agent_run_turn_request(
            run.id,
            request_id="req-login-001",
            stage_id="STRATEGY",
            user_content="请分析登录需求",
        )
        assert duplicate_completed.state == "completed"
        assert duplicate_completed.terminal_event == terminal_event
        assert db.session.get(AgentRun, run.id).current_stage_id == "CLARIFY"
        assert [message.role for message in AgentMessage.query.order_by(AgentMessage.id)] == [
            "user",
            "assistant",
        ]


def test_turn_request_claim_replays_recorded_failure_without_appending_another_user_message(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")
        run_id = run.id
        claim_agent_run_turn_request(
            run_id,
            request_id="req-login-failure",
            stage_id="CLARIFY",
            user_content="请分析登录需求",
        )
        terminal_event = {
            "type": "error",
            "code": "LLM_ERROR",
            "message": "provider API failed",
        }
        fail_agent_run_turn_request(
            run.id,
            request_id="req-login-failure",
            terminal_event=terminal_event,
        )

        replay = claim_agent_run_turn_request(
            run.id,
            request_id="req-login-failure",
            stage_id="CLARIFY",
            user_content="请分析登录需求",
        )

        assert replay.state == "failed"
        assert replay.terminal_event == terminal_event
        assert AgentMessage.query.count() == 1


def test_turn_request_unique_identity_is_enforced_across_independent_db_sessions(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")
        session_factory = sessionmaker(bind=db.engine)
        first_session = session_factory()
        second_session = session_factory()
        try:
            assert first_session.query(AgentRunTurnRequest).filter_by(
                run_id=run.id,
                request_id="cross-session-request-001",
            ).one_or_none() is None
            assert second_session.query(AgentRunTurnRequest).filter_by(
                run_id=run.id,
                request_id="cross-session-request-001",
            ).one_or_none() is None

            first_session.add(AgentRunTurnRequest(
                run_id=run.id,
                request_id="cross-session-request-001",
                stage_id="CLARIFY",
                status="active",
            ))
            first_session.commit()

            second_session.add(AgentRunTurnRequest(
                run_id=run.id,
                request_id="cross-session-request-001",
                stage_id="CLARIFY",
                status="active",
            ))
            with pytest.raises(IntegrityError):
                second_session.commit()
            second_session.rollback()
        finally:
            first_session.close()
            second_session.close()

        assert AgentRunTurnRequest.query.filter_by(
            run_id=run.id,
            request_id="cross-session-request-001",
        ).count() == 1


def test_concurrent_turn_completion_returns_one_conflict_without_partial_history(
    app,
    monkeypatch,
):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")
        run_id = run.id
        claim_agent_run_turn_request(
            run_id,
            request_id="concurrent-complete-first",
            stage_id="CLARIFY",
            user_content="第一条并发请求",
        )
        claim_agent_run_turn_request(
            run_id,
            request_id="concurrent-complete-second",
            stage_id="CLARIFY",
            user_content="第二条并发请求",
        )

    second_has_read_sequence = threading.Event()
    first_finished = threading.Event()

    def return_same_stale_sequence(_run_id: str) -> int:
        if threading.current_thread().name == "first-completion":
            second_has_read_sequence.wait(timeout=5)
            return 3
        second_has_read_sequence.set()
        first_finished.wait(timeout=5)
        return 3

    monkeypatch.setattr(
        run_persistence,
        "_next_message_sequence",
        return_same_stale_sequence,
    )
    outcomes: dict[str, str] = {}

    def complete_in_separate_session(role: str, request_id: str) -> None:
        with app.app_context():
            try:
                complete_agent_run_turn(
                    run_id,
                    request_id=request_id,
                    stage_id="CLARIFY",
                    assistant_content=f"{role} 完成",
                    artifact_content=None,
                    artifact_data=None,
                    terminal_event={"type": "agent_turn", "output": {}},
                    metric={
                        "workflow_id": "TEST_DESIGN",
                        "stage_id": "CLARIFY",
                        "model_name": "test-model",
                        "provider": "test-provider",
                        "status": "success",
                        "error_code": None,
                        "duration_ms": 1,
                        "input_chars": 8,
                        "output_chars": 12,
                        "estimated_tokens": 5,
                        "contract_retry_count": 0,
                    },
                )
                outcomes[role] = "success"
            except run_persistence.TurnPersistenceConflictError:
                outcomes[role] = "conflict"
            finally:
                if role == "first":
                    first_finished.set()

    first = threading.Thread(
        target=complete_in_separate_session,
        args=("first", "concurrent-complete-first"),
        name="first-completion",
    )
    second = threading.Thread(
        target=complete_in_separate_session,
        args=("second", "concurrent-complete-second"),
        name="second-completion",
    )
    first.start()
    second.start()
    first.join(timeout=10)
    second.join(timeout=10)

    assert not first.is_alive()
    assert not second.is_alive()
    assert sorted(outcomes.values()) == ["conflict", "success"]
    with app.app_context():
        messages = AgentMessage.query.filter_by(run_id=run_id).order_by(
            AgentMessage.sequence_index
        ).all()
        assert [(message.role, message.sequence_index) for message in messages] == [
            ("user", 1),
            ("user", 2),
            ("assistant", 3),
        ]


def test_concurrent_turn_completion_returns_one_artifact_version_conflict(
    app,
    monkeypatch,
):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")
        run_id = run.id
        record_artifact_version(run_id, "CLARIFY", "# 初始产出物")
        for request_id, content in (
            ("concurrent-version-first", "第一条版本请求"),
            ("concurrent-version-second", "第二条版本请求"),
        ):
            claim_agent_run_turn_request(
                run_id,
                request_id=request_id,
                stage_id="CLARIFY",
                user_content=content,
            )

    second_has_read_version = threading.Event()
    first_finished = threading.Event()

    def distinct_message_sequences(_run_id: str) -> int:
        return 3 if threading.current_thread().name == "first-version" else 4

    def return_same_stale_version(_artifact_id: int) -> int:
        if threading.current_thread().name == "first-version":
            second_has_read_version.wait(timeout=5)
            return 2
        second_has_read_version.set()
        first_finished.wait(timeout=5)
        return 2

    monkeypatch.setattr(run_persistence, "_next_message_sequence", distinct_message_sequences)
    monkeypatch.setattr(run_persistence, "_next_artifact_version", return_same_stale_version)
    outcomes: dict[str, str] = {}

    def complete_in_separate_session(role: str, request_id: str) -> None:
        with app.app_context():
            try:
                complete_agent_run_turn(
                    run_id,
                    request_id=request_id,
                    stage_id="CLARIFY",
                    assistant_content=f"{role} 完成",
                    artifact_content=f"# {role} 产出物",
                    artifact_data=None,
                    terminal_event={"type": "agent_turn", "output": {}},
                    metric={
                        "workflow_id": "TEST_DESIGN",
                        "stage_id": "CLARIFY",
                        "model_name": "test-model",
                        "provider": "test-provider",
                        "status": "success",
                        "error_code": None,
                        "duration_ms": 1,
                        "input_chars": 8,
                        "output_chars": 12,
                        "estimated_tokens": 5,
                        "contract_retry_count": 0,
                    },
                )
                outcomes[role] = "success"
            except run_persistence.TurnPersistenceConflictError:
                outcomes[role] = "conflict"
            finally:
                if role == "first":
                    first_finished.set()

    first = threading.Thread(
        target=complete_in_separate_session,
        args=("first", "concurrent-version-first"),
        name="first-version",
    )
    second = threading.Thread(
        target=complete_in_separate_session,
        args=("second", "concurrent-version-second"),
        name="second-version",
    )
    first.start()
    second.start()
    first.join(timeout=10)
    second.join(timeout=10)

    assert not first.is_alive()
    assert not second.is_alive()
    assert sorted(outcomes.values()) == ["conflict", "success"]
    with app.app_context():
        artifact = AgentArtifact.query.filter_by(
            run_id=run_id,
            stage_id="CLARIFY",
        ).one()
        assert AgentArtifactVersion.query.filter_by(artifact_id=artifact.id).count() == 2
        assert AgentMessage.query.filter_by(run_id=run_id, role="assistant").count() == 1


def test_artifact_versions_increment_per_run_stage(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")

        first = record_artifact_version(run.id, "CLARIFY", "# 需求分析文档\n初版")
        second = record_artifact_version(run.id, "CLARIFY", "# 需求分析文档\n二版")

        artifact = AgentArtifact.query.filter_by(
            run_id=run.id,
            stage_id="CLARIFY",
        ).one()
        assert first.version_number == 1
        assert second.version_number == 2
        assert artifact.current_version_id == second.id
        assert AgentArtifactVersion.query.filter_by(artifact_id=artifact.id).count() == 2


def test_record_artifact_version_persists_artifact_data_in_current_snapshot(app):
    with app.app_context():
        run = create_agent_run("STORY_BREAKDOWN", "alex", "STORY_BACKLOG")
        artifact_data = {
            "document_info": {
                "artifact_name": "用户故事卡片",
                "workflow": "STORY_BREAKDOWN",
                "stage": "STORY_BACKLOG",
            },
            "story_cards": [
                {
                    "storyId": "US-001",
                    "title": "短信验证码登录",
                }
            ],
        }

        version = record_artifact_version(
            run.id,
            "STORY_BACKLOG",
            "# 用户故事卡片\n\nUS-001",
            artifact_data=artifact_data,
        )

        assert version.artifact_data == artifact_data
        snapshot = get_run_snapshot(run.id)

    assert snapshot["artifacts"] == [
        {
            "stageId": "STORY_BACKLOG",
            "content": "# 用户故事卡片\n\nUS-001",
            "versionNumber": 1,
            "artifactData": artifact_data,
        }
    ]


def test_run_snapshot_returns_messages_and_current_artifacts(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY", model="gpt-test")
        append_run_message(run.id, "user", "输入")
        append_run_message(run.id, "assistant", "回复")
        record_artifact_version(run.id, "CLARIFY", "初版")
        record_artifact_version(
            run.id,
            "CLARIFY",
            "二版",
            artifact_data={
                "document_info": {
                    "artifact_name": "测试需求分析与澄清基线",
                },
                "stage_gate": {
                    "status": "需要用户补充",
                    "blocking": True,
                },
            },
        )

        snapshot = get_run_snapshot(run.id)

    assert snapshot["run"]["id"] == run.id
    assert snapshot["run"]["workflowId"] == "TEST_DESIGN"
    assert snapshot["run"]["agentId"] == "lisa"
    assert snapshot["run"]["currentStageId"] == "CLARIFY"
    assert snapshot["run"]["status"] == "active"
    assert snapshot["run"]["model"] == "gpt-test"
    assert [message["role"] for message in snapshot["messages"]] == [
        "user",
        "assistant",
    ]
    assert [message["sequenceIndex"] for message in snapshot["messages"]] == [1, 2]
    assert snapshot["artifacts"] == [
        {
            "stageId": "CLARIFY",
            "content": "二版",
            "versionNumber": 2,
            "artifactData": {
                "document_info": {
                    "artifact_name": "测试需求分析与澄清基线",
                },
                "stage_gate": {
                    "status": "需要用户补充",
                    "blocking": True,
                },
            },
        }
    ]
    assert snapshot["artifactComments"] == []
    assert snapshot["artifactSectionLocks"] == []


def test_run_snapshot_returns_null_artifact_data_for_manual_versions(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY", model="gpt-test")
        record_artifact_version(run.id, "CLARIFY", "手工编辑版本")

        snapshot = get_run_snapshot(run.id)

    assert snapshot["artifacts"] == [
        {
            "stageId": "CLARIFY",
            "content": "手工编辑版本",
            "versionNumber": 1,
            "artifactData": None,
        }
    ]


def test_run_snapshot_returns_artifact_collaboration_state(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY", model="gpt-test")
        record_artifact_version(run.id, "CLARIFY", "# 需求分析文档\n\n登录边界")

        saved = replace_artifact_collaboration_state(
            run.id,
            {
                "comments": [
                    {
                        "id": "comment-1",
                        "stageId": "CLARIFY",
                        "content": "这里需要业务确认登录边界。",
                        "artifactExcerpt": "登录边界",
                        "anchorText": "登录边界",
                        "createdAt": 1710000000000,
                        "status": "resolved",
                        "resolvedAt": 1710000000300,
                        "replies": [
                            {
                                "id": "reply-1",
                                "content": "已补充登录异常边界。",
                                "createdAt": 1710000000200,
                            }
                        ],
                    }
                ],
                "sectionLocks": [
                    {
                        "id": "lock-1",
                        "stageId": "CLARIFY",
                        "heading": "## 业务规则",
                        "sectionAnchor": "h2:业务规则:1",
                        "content": "## 业务规则\n\n已确认登录规则。",
                        "createdAt": 1710000000100,
                    }
                ],
            },
        )
        snapshot = get_run_snapshot(run.id)

    assert saved == {
        "artifactComments": [
            {
                "id": "comment-1",
                "stageId": "CLARIFY",
                "content": "这里需要业务确认登录边界。",
                "artifactExcerpt": "登录边界",
                "anchorText": "登录边界",
                "createdAt": 1710000000000,
                "status": "resolved",
                "resolvedAt": 1710000000300,
                "replies": [
                    {
                        "id": "reply-1",
                        "content": "已补充登录异常边界。",
                        "createdAt": 1710000000200,
                    }
                ],
            }
        ],
        "artifactSectionLocks": [
            {
                "id": "lock-1",
                "stageId": "CLARIFY",
                "heading": "## 业务规则",
                "sectionAnchor": "h2:业务规则:1",
                "content": "## 业务规则\n\n已确认登录规则。",
                "createdAt": 1710000000100,
            }
        ],
    }
    assert snapshot["artifactComments"] == saved["artifactComments"]
    assert snapshot["artifactSectionLocks"] == saved["artifactSectionLocks"]


def test_clone_agent_run_copies_reusable_context_without_mutating_source(app):
    with app.app_context():
        source = create_agent_run("TEST_DESIGN", "lisa", "STRATEGY", model="gpt-test")
        append_run_message(source.id, "user", "请评估登录需求")
        append_run_message(source.id, "assistant", "已形成测试策略")
        record_artifact_version(source.id, "CLARIFY", "# 需求分析文档\n\n登录边界")
        record_artifact_version(source.id, "STRATEGY", "# 测试策略蓝图\n\n覆盖登录风险")
        replace_artifact_collaboration_state(
            source.id,
            {
                "comments": [
                    {
                        "id": "comment-source",
                        "stageId": "STRATEGY",
                        "content": "源 run 的审阅意见",
                        "artifactExcerpt": "登录风险",
                        "anchorText": "登录风险",
                        "createdAt": 1710000000000,
                        "status": "open",
                        "resolvedAt": None,
                        "replies": [],
                    }
                ],
                "sectionLocks": [
                    {
                        "id": "lock-source",
                        "stageId": "STRATEGY",
                        "heading": "## 风险范围",
                        "sectionAnchor": "h2:风险范围:1",
                        "content": "## 风险范围\n\n源 run 锁定内容",
                        "createdAt": 1710000000100,
                    }
                ],
            },
        )

        cloned = clone_agent_run(source.id)
        source_snapshot = get_run_snapshot(source.id)
        cloned_snapshot = get_run_snapshot(cloned.id)

    assert cloned.id != source.id
    assert cloned.workflow_id == "TEST_DESIGN"
    assert cloned.agent_id == "lisa"
    assert cloned.current_stage_id == "STRATEGY"
    assert cloned.status == "active"
    assert cloned.model == "gpt-test"
    assert [message["content"] for message in cloned_snapshot["messages"]] == [
        "请评估登录需求",
        "已形成测试策略",
    ]
    assert cloned_snapshot["artifacts"] == [
        {
            "stageId": "CLARIFY",
            "content": "# 需求分析文档\n\n登录边界",
            "versionNumber": 1,
            "artifactData": None,
        },
        {
            "stageId": "STRATEGY",
            "content": "# 测试策略蓝图\n\n覆盖登录风险",
            "versionNumber": 1,
            "artifactData": None,
        },
    ]
    assert cloned_snapshot["contextSummaries"] == source_snapshot["contextSummaries"]
    assert cloned_snapshot["artifactComments"] == []
    assert cloned_snapshot["artifactSectionLocks"] == []
    assert source_snapshot["artifactComments"][0]["id"] == "comment-source"
    assert source_snapshot["artifactSectionLocks"][0]["id"] == "lock-source"


def test_list_agent_runs_filters_by_reuse_status(app):
    with app.app_context():
        ready_run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")
        record_artifact_version(ready_run.id, "CLARIFY", "# 需求分析文档\n\n可复用")
        draft_run = create_agent_run("TEST_DESIGN", "lisa", "STRATEGY")
        failed_run = create_agent_run("TEST_DESIGN", "lisa", "CASES", status="failed")

        ready_result = list_agent_runs(reuse_status="ready")
        draft_result = list_agent_runs(reuse_status="needs_artifact")
        failed_result = list_agent_runs(reuse_status="failed")

    assert [run["id"] for run in ready_result["runs"]] == [ready_run.id]
    assert ready_result["runs"][0]["reuseStatus"] == "ready"
    assert [run["id"] for run in draft_result["runs"]] == [draft_run.id]
    assert draft_result["runs"][0]["reuseStatus"] == "needs_artifact"
    assert [run["id"] for run in failed_result["runs"]] == [failed_run.id]
    assert failed_result["runs"][0]["reuseStatus"] == "failed"


def test_run_snapshot_returns_artifact_audit_events(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY", model="gpt-test")

        update_run_artifact(
            run.id,
            {
                "stageId": "CLARIFY",
                "content": "# 需求分析文档\n\n人工校准后的边界。",
            },
        )
        replace_artifact_collaboration_state(
            run.id,
            {
                "comments": [
                    {
                        "id": "comment-1",
                        "stageId": "CLARIFY",
                        "content": "这里需要业务确认登录边界。",
                        "artifactExcerpt": "登录边界",
                        "anchorText": "登录边界",
                        "createdAt": 1710000000000,
                        "status": "open",
                        "resolvedAt": None,
                        "replies": [],
                    }
                ],
                "sectionLocks": [],
            },
        )
        snapshot = get_run_snapshot(run.id)

    assert [
        event["eventType"]
        for event in snapshot["artifactAuditEvents"]
    ] == ["artifact_saved", "collaboration_updated"]
    assert snapshot["artifactAuditEvents"][0] == {
        "stageId": "CLARIFY",
        "eventType": "artifact_saved",
        "summary": "保存了 CLARIFY 阶段产出物 v1",
        "createdAt": snapshot["artifactAuditEvents"][0]["createdAt"],
    }
    assert snapshot["artifactAuditEvents"][1] == {
        "stageId": "CLARIFY",
        "eventType": "collaboration_updated",
        "summary": "更新了 CLARIFY 阶段协作状态：1 条批注，0 个章节锁",
        "createdAt": snapshot["artifactAuditEvents"][1]["createdAt"],
    }


def test_observability_recent_turns_include_sanitized_error_diagnostic(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")
        record_turn_metric(
            run_id=run.id,
            workflow_id="TEST_DESIGN",
            stage_id="CLARIFY",
            model_name="deepseek-chat",
            provider="deepseek",
            status="error",
            error_code="SCHEMA_VALIDATION_FAILED",
            duration_ms=1200,
            input_chars=80,
            output_chars=0,
            estimated_tokens=20,
            contract_retry_count=2,
            diagnostic={
                "phase": "structured_output",
                "fieldPath": "artifact_data.requirement_facts.0.fact",
                "validator": "string_too_short",
                "publicReason": "模型输出的结构化字段未通过校验，右侧产出物已保持不变。",
                "retryable": True,
            },
        )

        summary = get_runtime_observability_summary(limit=5)

    turn = summary["recentTurns"][0]
    assert turn["diagnostic"] == {
        "phase": "structured_output",
        "fieldPath": "artifact_data.requirement_facts.0.fact",
        "validator": "string_too_short",
        "publicReason": "模型输出的结构化字段未通过校验，右侧产出物已保持不变。",
        "retryable": True,
    }


def test_record_artifact_version_persists_current_artifact_summary(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")

        record_artifact_version(run.id, "CLARIFY", "# 结论\n\n- 目标：提升转化")
        snapshot = get_run_snapshot(run.id)

    summaries = {
        summary["summaryType"]: summary
        for summary in snapshot["contextSummaries"]
    }
    assert summaries["current_artifact"] == {
        "sourceType": "artifact",
        "sourceStageId": "CLARIFY",
        "summaryType": "current_artifact",
        "content": "# 结论\n- 目标：提升转化",
    }
    assert summaries["stage_conclusion"] == {
        "sourceType": "artifact",
        "sourceStageId": "CLARIFY",
        "summaryType": "stage_conclusion",
        "content": "# 结论\n- 目标：提升转化",
    }


def test_record_artifact_version_updates_existing_current_artifact_summary(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")

        record_artifact_version(run.id, "CLARIFY", "# 结论\n初版")
        record_artifact_version(run.id, "CLARIFY", "# 结论\n二版")
        snapshot = get_run_snapshot(run.id)

    summaries = {
        summary["summaryType"]: summary["content"]
        for summary in snapshot["contextSummaries"]
    }
    assert summaries["current_artifact"] == "# 结论\n二版"
    assert summaries["stage_conclusion"] == "# 结论\n二版"


def test_append_user_message_persists_stage_user_supplement_summary(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")

        append_run_message(run.id, "user", "补充：必须覆盖短信验证码")
        append_run_message(run.id, "assistant", "已收到")
        append_run_message(run.id, "user", "补充：弱网下也要验证")
        snapshot = get_run_snapshot(run.id)

    summaries = [
        summary
        for summary in snapshot["contextSummaries"]
        if summary["summaryType"] == "user_supplement"
    ]
    assert summaries == [
        {
            "sourceType": "user_input",
            "sourceStageId": "CLARIFY",
            "summaryType": "user_supplement",
            "content": "补充：必须覆盖短信验证码\n\n补充：弱网下也要验证",
        }
    ]


def test_record_artifact_version_persists_decision_summary(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "STRATEGY")

        record_artifact_version(
            run.id,
            "STRATEGY",
            "# 测试策略蓝图\n\n"
            "## 阶段结论\n"
            "- 覆盖登录主链路和异常链路\n\n"
            "## 关键决策\n"
            "- 决定优先自动化登录回归\n"
            "- P0 风险先覆盖第三方回调失败",
        )
        snapshot = get_run_snapshot(run.id)

    summaries = {
        summary["summaryType"]: summary["content"]
        for summary in snapshot["contextSummaries"]
    }
    assert "覆盖登录主链路和异常链路" in summaries["stage_conclusion"]
    assert summaries["decision"] == (
        "- 决定优先自动化登录回归\n"
        "- P0 风险先覆盖第三方回调失败"
    )


def test_update_context_summary_persists_calibrated_content(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "STRATEGY")
        record_artifact_version(run.id, "STRATEGY", "# 阶段结论\n\n初始摘要")

        updated = update_context_summary(
            run.id,
            {
                "sourceType": "artifact",
                "sourceStageId": "STRATEGY",
                "summaryType": "stage_conclusion",
                "content": "人工校准后的阶段结论",
            },
        )
        snapshot = get_run_snapshot(run.id)

    assert updated == {
        "sourceType": "artifact",
        "sourceStageId": "STRATEGY",
        "summaryType": "stage_conclusion",
        "content": "人工校准后的阶段结论",
    }
    summaries = {
        summary["summaryType"]: summary["content"]
        for summary in snapshot["contextSummaries"]
    }
    assert summaries["stage_conclusion"] == "人工校准后的阶段结论"


def test_update_context_summary_rejects_missing_summary(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "STRATEGY")

        with pytest.raises(
            ValueError,
            match="未知上下文摘要: artifact/STRATEGY/stage_conclusion",
        ):
            update_context_summary(
                run.id,
                {
                    "sourceType": "artifact",
                    "sourceStageId": "STRATEGY",
                    "summaryType": "stage_conclusion",
                    "content": "人工校准后的阶段结论",
                },
            )


def test_update_context_summary_rejects_blank_content(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "STRATEGY")
        record_artifact_version(run.id, "STRATEGY", "# 阶段结论\n\n初始摘要")

        with pytest.raises(ValueError, match="content 不能为空"):
            update_context_summary(
                run.id,
                {
                    "sourceType": "artifact",
                    "sourceStageId": "STRATEGY",
                    "summaryType": "stage_conclusion",
                    "content": "   ",
                },
            )


def test_upsert_manual_decision_summary_creates_decision(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "STRATEGY")

        decision = upsert_manual_decision_summary(
            run.id,
            {
                "stageId": "STRATEGY",
                "content": "决定优先覆盖第三方登录回调失败",
            },
        )
        snapshot = get_run_snapshot(run.id)

    assert decision == {
        "sourceType": "artifact",
        "sourceStageId": "STRATEGY",
        "summaryType": "decision",
        "content": "决定优先覆盖第三方登录回调失败",
    }
    assert decision in snapshot["contextSummaries"]


def test_upsert_manual_decision_summary_updates_existing_decision(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "STRATEGY")

        upsert_manual_decision_summary(
            run.id,
            {
                "stageId": "STRATEGY",
                "content": "旧决策",
            },
        )
        upsert_manual_decision_summary(
            run.id,
            {
                "stageId": "STRATEGY",
                "content": "新决策",
            },
        )
        snapshot = get_run_snapshot(run.id)

    decisions = [
        summary
        for summary in snapshot["contextSummaries"]
        if summary["summaryType"] == "decision"
    ]
    assert decisions == [
        {
            "sourceType": "artifact",
            "sourceStageId": "STRATEGY",
            "summaryType": "decision",
            "content": "新决策",
        }
    ]


def test_upsert_manual_decision_summary_rejects_stage_outside_workflow(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "STRATEGY")

        with pytest.raises(
            ValueError,
            match="workflowId 与 stageId 不匹配: TEST_DESIGN/REPORT",
        ):
            upsert_manual_decision_summary(
                run.id,
                {
                    "stageId": "REPORT",
                    "content": "跨工作流决策",
                },
            )


@pytest.mark.parametrize(
    ("workflow_id", "stage_id", "message"),
    [
        ("UNKNOWN", "CLARIFY", "未知 workflowId: UNKNOWN"),
        (
            "TEST_DESIGN",
            "UNKNOWN",
            "workflowId 与 stageId 不匹配: TEST_DESIGN/UNKNOWN",
        ),
    ],
)
def test_create_run_rejects_unknown_workflow_stage(
    app,
    workflow_id,
    stage_id,
    message,
):
    with app.app_context(), pytest.raises(ValueError, match=message):
        create_agent_run(workflow_id, "lisa", stage_id)


def test_record_artifact_rejects_stage_outside_run_workflow(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")

        with pytest.raises(
            ValueError,
            match="workflowId 与 stageId 不匹配: TEST_DESIGN/REPORT",
        ):
            record_artifact_version(run.id, "REPORT", "wrong stage")


def test_ensure_agent_run_rejects_workflow_mismatch(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")

        with pytest.raises(
            ValueError,
            match=f"runId 与 workflowId 不匹配: {run.id}/VALUE_DISCOVERY",
        ):
            ensure_agent_run(
                "VALUE_DISCOVERY",
                "alex",
                "ELEVATOR",
                run_id=run.id,
            )


def test_append_message_rejects_unknown_role(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")

        with pytest.raises(ValueError, match="未知 message role: system"):
            append_run_message(run.id, "system", "hidden")
