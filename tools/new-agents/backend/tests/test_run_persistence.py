import os
import sys
import tempfile
import threading
import traceback
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

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
    AgentContextSummary,
    AgentMessage,
    AgentRun,
    AgentRunTurnMetric,
    AgentRunTurnRequest,
    db,
)
from run_persistence import (
    TurnPersistenceError,
    TurnPersistenceConflictError,
    TurnRequestIdentityConflictError,
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
        monkeypatch.setattr(
            run_persistence, "create_agent_run", report_unique_create_conflict
        )

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


def test_persistence_adapter_maps_ensure_run_sql_failure_to_safe_error(
    app,
    monkeypatch,
):
    canary = "ENSURE-RUN-SQL-CREDENTIAL-CANARY"
    rollback_calls = []

    with app.app_context():
        original_rollback = db.session.rollback

        def fail_ensure_run(*args, **kwargs):
            raise SQLAlchemyError(canary)

        def track_rollback():
            rollback_calls.append(True)
            original_rollback()

        monkeypatch.setattr(run_persistence, "ensure_agent_run", fail_ensure_run)
        monkeypatch.setattr(db.session, "rollback", track_rollback)

        with pytest.raises(TurnPersistenceError) as captured:
            run_persistence.AgentRunPersistence().ensure_run(
                SimpleNamespace(
                    workflow_id="TEST_DESIGN",
                    stage_id="CLARIFY",
                    run_id=None,
                ),
                model_name="test-model",
            )

    assert str(captured.value) == "Unable to ensure the agent run."
    assert rollback_calls == [True]
    assert captured.value.__cause__ is None
    assert canary not in "".join(traceback.format_exception(captured.value))


def test_persistence_adapter_maps_claim_sql_failure_to_safe_error(
    app,
    monkeypatch,
):
    canary = "CLAIM-TURN-SQL-OWNER-CANARY"
    rollback_calls = []

    with app.app_context():
        original_rollback = db.session.rollback

        def fail_claim(*args, **kwargs):
            raise SQLAlchemyError(canary)

        def track_rollback():
            rollback_calls.append(True)
            original_rollback()

        monkeypatch.setattr(
            run_persistence,
            "claim_agent_run_turn_request",
            fail_claim,
        )
        monkeypatch.setattr(db.session, "rollback", track_rollback)

        with pytest.raises(TurnPersistenceError) as captured:
            run_persistence.AgentRunPersistence().claim_turn_request(
                "run-safe-id",
                SimpleNamespace(
                    request_id="request-safe-id",
                    stage_id="CLARIFY",
                    prompt="safe prompt",
                    system_prompt="safe system prompt",
                ),
                model_name="test-model",
            )

    assert str(captured.value) == "Unable to claim the agent turn request."
    assert rollback_calls == [True]
    assert captured.value.__cause__ is None
    assert canary not in "".join(traceback.format_exception(captured.value))


@pytest.mark.parametrize(
    "semantic_error",
    [
        TurnRequestIdentityConflictError("requestId identity conflict"),
        TurnPersistenceConflictError("turn request conflict"),
        ValueError("invalid request"),
    ],
)
def test_persistence_adapter_preserves_claim_semantic_errors(
    app,
    monkeypatch,
    semantic_error,
):
    with app.app_context():

        def reject_claim(*args, **kwargs):
            raise semantic_error

        monkeypatch.setattr(
            run_persistence,
            "claim_agent_run_turn_request",
            reject_claim,
        )

        with pytest.raises(type(semantic_error)) as captured:
            run_persistence.AgentRunPersistence().claim_turn_request(
                "run-safe-id",
                SimpleNamespace(
                    request_id="request-safe-id",
                    stage_id="CLARIFY",
                    prompt="safe prompt",
                    system_prompt="safe system prompt",
                ),
                model_name="test-model",
            )

    assert captured.value is semantic_error


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
            owner_token=first.owner_token,
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
            stage_id="CLARIFY",
            user_content="请分析登录需求",
        )
        assert duplicate_completed.state == "completed"
        assert duplicate_completed.terminal_event == terminal_event
        assert db.session.get(AgentRun, run.id).current_stage_id == "CLARIFY"
        assert [
            message.role for message in AgentMessage.query.order_by(AgentMessage.id)
        ] == [
            "user",
            "assistant",
        ]


@pytest.mark.parametrize(
    ("target_stage_id", "expected_pending_transition"),
    (
        (
            "STRATEGY",
            {"fromStageId": "CLARIFY", "targetStageId": "STRATEGY"},
        ),
        ("CASES", None),
    ),
)
def test_run_snapshot_projects_only_the_immediate_persisted_stage_transition(
    app,
    target_stage_id,
    expected_pending_transition,
):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")
        claim = claim_agent_run_turn_request(
            run.id,
            request_id="req-snapshot-pending-transition",
            stage_id="CLARIFY",
            user_content="请完成需求澄清",
        )
        complete_agent_run_turn(
            run.id,
            request_id="req-snapshot-pending-transition",
            owner_token=claim.owner_token,
            stage_id="CLARIFY",
            assistant_content="需求澄清完成，请确认进入策略制定。",
            artifact_content="# 需求分析文档\n\n已完成需求澄清。",
            artifact_data={"document": "clarify"},
            terminal_event={
                "type": "agent_turn",
                "output": {
                    "chat": "需求澄清完成，请确认进入策略制定。",
                    "artifact_update": {"type": "replace"},
                    "stage_action": {
                        "type": "request_next_stage",
                        "target_stage_id": target_stage_id,
                    },
                    "warnings": [],
                },
            },
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

        snapshot = get_run_snapshot(run.id)

    assert snapshot["run"]["currentStageId"] == "CLARIFY"
    assert snapshot["pendingStageTransition"] == expected_pending_transition


@pytest.mark.parametrize(
    ("reused_stage_id", "reused_user_content"),
    (
        ("STRATEGY", "请分析登录需求"),
        ("CLARIFY", "请分析另一个需求"),
    ),
)
def test_turn_request_claim_rejects_completed_request_id_reuse_with_different_identity(
    app,
    reused_stage_id,
    reused_user_content,
):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")
        first = claim_agent_run_turn_request(
            run.id,
            request_id="req-bound-identity-001",
            stage_id="CLARIFY",
            user_content="请分析登录需求",
        )
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
            request_id="req-bound-identity-001",
            owner_token=first.owner_token,
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

        with pytest.raises(ValueError, match="requestId identity conflict") as captured:
            claim_agent_run_turn_request(
                run.id,
                request_id="req-bound-identity-001",
                stage_id=reused_stage_id,
                user_content=reused_user_content,
            )

        assert type(captured.value).__name__ == "TurnRequestIdentityConflictError"
        assert AgentMessage.query.filter_by(run_id=run.id).count() == 2
        stored = AgentRunTurnRequest.query.filter_by(
            run_id=run.id,
            request_id="req-bound-identity-001",
        ).one()
        assert stored.status == "completed"
        assert db.session.get(AgentRun, run.id).current_stage_id == "CLARIFY"


def test_abandoned_turn_request_is_reclaimed_only_by_the_same_request_identity(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")
        first = claim_agent_run_turn_request(
            run.id,
            request_id="req-abandoned-retry-001",
            stage_id="CLARIFY",
            user_content="请分析登录需求",
        )
        assert first.state == "new"

        run_persistence.abandon_agent_run_turn_request(
            run.id,
            request_id="req-abandoned-retry-001",
            owner_token=first.owner_token,
        )

        stored = AgentRunTurnRequest.query.filter_by(
            run_id=run.id,
            request_id="req-abandoned-retry-001",
        ).one()
        assert stored.status == "abandoned"

        reclaimed = claim_agent_run_turn_request(
            run.id,
            request_id="req-abandoned-retry-001",
            stage_id="CLARIFY",
            user_content="请分析登录需求",
        )

        assert reclaimed.state == "new"
        assert stored.status == "active"
        assert AgentMessage.query.filter_by(run_id=run.id, role="user").count() == 1

        run_persistence.abandon_agent_run_turn_request(
            run.id,
            request_id="req-abandoned-retry-001",
            owner_token=reclaimed.owner_token,
        )
        with pytest.raises(ValueError, match="requestId identity conflict"):
            claim_agent_run_turn_request(
                run.id,
                request_id="req-abandoned-retry-001",
                stage_id="CLARIFY",
                user_content="请分析另一个需求",
            )
        assert AgentMessage.query.filter_by(run_id=run.id, role="user").count() == 1


def test_abandoned_turn_request_compare_and_set_has_only_one_winner(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")
        first = claim_agent_run_turn_request(
            run.id,
            request_id="req-abandoned-cas-001",
            stage_id="CLARIFY",
            user_content="请分析登录需求",
        )
        run_persistence.abandon_agent_run_turn_request(
            run.id,
            request_id="req-abandoned-cas-001",
            owner_token=first.owner_token,
        )
        stored = AgentRunTurnRequest.query.filter_by(
            run_id=run.id,
            request_id="req-abandoned-cas-001",
        ).one()

        reclaimed_owner = run_persistence._reclaim_abandoned_turn_request(stored)
        assert isinstance(reclaimed_owner, str)
        db.session.commit()
        assert run_persistence._reclaim_abandoned_turn_request(stored) is None
        assert stored.status == "active"


def test_expired_active_turn_request_is_reclaimed_by_exact_identity(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")
        first = claim_agent_run_turn_request(
            run.id,
            request_id="req-expired-lease-001",
            stage_id="CLARIFY",
            user_content="请分析登录需求",
        )
        stored = AgentRunTurnRequest.query.filter_by(
            run_id=run.id,
            request_id="req-expired-lease-001",
        ).one()
        stored.updated_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(
            seconds=run_persistence.TURN_REQUEST_ACTIVE_LEASE_SECONDS + 1
        )
        db.session.commit()

        reclaimed = claim_agent_run_turn_request(
            run.id,
            request_id="req-expired-lease-001",
            stage_id="CLARIFY",
            user_content="请分析登录需求",
        )
        duplicate = claim_agent_run_turn_request(
            run.id,
            request_id="req-expired-lease-001",
            stage_id="CLARIFY",
            user_content="请分析登录需求",
        )

        assert reclaimed.state == "new"
        assert duplicate.state == "active"
        assert AgentMessage.query.filter_by(run_id=run.id, role="user").count() == 1


def test_expired_lease_fences_old_owner_from_terminal_mutations(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")
        first_owner = claim_agent_run_turn_request(
            run.id,
            request_id="req-owner-fence-001",
            stage_id="CLARIFY",
            user_content="请分析登录需求",
        )
        stored = AgentRunTurnRequest.query.filter_by(
            run_id=run.id,
            request_id="req-owner-fence-001",
        ).one()
        stored.updated_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(
            seconds=run_persistence.TURN_REQUEST_ACTIVE_LEASE_SECONDS + 1
        )
        db.session.commit()

        new_owner = claim_agent_run_turn_request(
            run.id,
            request_id="req-owner-fence-001",
            stage_id="CLARIFY",
            user_content="请分析登录需求",
        )

        assert first_owner.owner_token
        assert new_owner.owner_token
        assert new_owner.owner_token != first_owner.owner_token
        assert first_owner.lease_generation == 1
        assert new_owner.lease_generation == 2

        with pytest.raises(TurnPersistenceConflictError):
            fail_agent_run_turn_request(
                run.id,
                request_id="req-owner-fence-001",
                owner_token=first_owner.owner_token,
                terminal_event={"type": "error", "code": "LLM_ERROR"},
            )
        with pytest.raises(TurnPersistenceConflictError):
            run_persistence.abandon_agent_run_turn_request(
                run.id,
                request_id="req-owner-fence-001",
                owner_token=first_owner.owner_token,
            )
        with pytest.raises(TurnPersistenceConflictError):
            complete_agent_run_turn(
                run.id,
                request_id="req-owner-fence-001",
                owner_token=first_owner.owner_token,
                stage_id="CLARIFY",
                assistant_content="旧 worker 结果",
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
                    "output_chars": 8,
                    "estimated_tokens": 4,
                    "contract_retry_count": 0,
                },
            )

        db.session.expire_all()
        still_owned = AgentRunTurnRequest.query.filter_by(
            run_id=run.id,
            request_id="req-owner-fence-001",
        ).one()
        assert still_owned.status == "active"
        assert (
            AgentMessage.query.filter_by(run_id=run.id, role="assistant").count() == 0
        )


def test_different_stage_request_cannot_mutate_run_while_another_turn_is_active(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")
        first = claim_agent_run_turn_request(
            run.id,
            request_id="req-single-active-first",
            stage_id="CLARIFY",
            user_content="第一条需求",
        )

        blocked = claim_agent_run_turn_request(
            run.id,
            request_id="req-single-active-second",
            stage_id="STRATEGY",
            user_content="不应写入的第二条需求",
        )

        assert first.state == "new"
        assert blocked == run_persistence.TurnRequestClaim(state="active")
        assert (
            AgentRunTurnRequest.query.filter_by(
                run_id=run.id,
                request_id="req-single-active-second",
            ).one_or_none()
            is None
        )
        assert [
            (message.role, message.content)
            for message in AgentMessage.query.filter_by(run_id=run.id)
            .order_by(AgentMessage.sequence_index)
            .all()
        ] == [("user", "第一条需求")]
        assert db.session.get(AgentRun, run.id).current_stage_id == "CLARIFY"

        complete_agent_run_turn(
            run.id,
            request_id="req-single-active-first",
            owner_token=first.owner_token,
            stage_id="CLARIFY",
            assistant_content="唯一成功回复",
            artifact_content="# 唯一成功产物",
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
                "input_chars": 6,
                "output_chars": 6,
                "estimated_tokens": 3,
                "contract_retry_count": 0,
            },
        )
        snapshot = get_run_snapshot(run.id)

        assert snapshot["run"]["currentStageId"] == "CLARIFY"
        assert [message["content"] for message in snapshot["messages"]] == [
            "第一条需求",
            "唯一成功回复",
        ]
        assert [artifact["stageId"] for artifact in snapshot["artifacts"]] == [
            "CLARIFY"
        ]


def test_abandoned_request_is_excluded_from_new_request_context(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")
        abandoned = claim_agent_run_turn_request(
            run.id,
            request_id="req-context-abandoned",
            stage_id="CLARIFY",
            user_content="ABANDONED-INPUT-CANARY-001",
        )
        run_persistence.abandon_agent_run_turn_request(
            run.id,
            request_id="req-context-abandoned",
            owner_token=abandoned.owner_token,
        )
        current = claim_agent_run_turn_request(
            run.id,
            request_id="req-context-current",
            stage_id="CLARIFY",
            user_content="CURRENT-INPUT-CANARY-001",
        )

        prompt, _warnings = run_persistence.AgentRunPersistence().build_runtime_context(
            run.id,
            "CURRENT-INPUT-CANARY-001",
            request_id="req-context-current",
        )

        assert current.state == "new"
        assert "ABANDONED-INPUT-CANARY-001" not in prompt
        assert prompt.count("CURRENT-INPUT-CANARY-001") == 1


def test_failed_turn_remains_visible_without_repeating_its_prompt_in_retry_context(
    app,
):
    failed_prompt = "FAILED-PROMPT-CANARY-001"
    public_reason = "模型供应商返回错误，本轮生成未完成，右侧产出物已保持不变。"
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")
        failed_claim = claim_agent_run_turn_request(
            run.id,
            request_id="req-failed-visible-001",
            stage_id="CLARIFY",
            user_content=failed_prompt,
            model_name="test-model",
        )
        fail_agent_run_turn_request(
            run.id,
            request_id="req-failed-visible-001",
            owner_token=failed_claim.owner_token,
            terminal_event={
                "type": "error",
                "code": "LLM_ERROR",
                "message": "unsafe provider details",
                "diagnostic": {
                    "phase": "provider",
                    "workflowId": "TEST_DESIGN",
                    "stageId": "CLARIFY",
                    "fieldPath": "provider",
                    "validator": "provider_error",
                    "retryable": True,
                    "publicReason": "unsafe provider details",
                },
            },
        )

        failed_snapshot = get_run_snapshot(run.id)
        assert failed_snapshot["messages"] == [
            {
                "role": "user",
                "content": failed_prompt,
                "sequenceIndex": 1,
            },
            {
                "role": "assistant",
                "content": f"⚠️ **模型调用未完成**\n\n{public_reason}",
                "sequenceIndex": 2,
                "errorDiagnostic": {
                    "kind": "provider",
                    "summary": "模型调用未完成",
                    "rawMessage": public_reason,
                    "code": "LLM_ERROR",
                    "phase": "provider",
                    "workflowId": "TEST_DESIGN",
                    "stageId": "CLARIFY",
                    "fieldPath": "provider",
                    "validator": "provider_error",
                    "retryable": True,
                },
            },
        ]
        assert failed_snapshot["contextSummaries"] == []

        retry_claim = claim_agent_run_turn_request(
            run.id,
            request_id="req-failed-visible-002",
            stage_id="CLARIFY",
            user_content=failed_prompt,
            model_name="test-model",
        )
        (
            retry_prompt,
            _warnings,
        ) = run_persistence.AgentRunPersistence().build_runtime_context(
            run.id,
            failed_prompt,
            request_id="req-failed-visible-002",
        )

        assert retry_prompt.count(failed_prompt) == 1
        assert "模型调用未完成" not in retry_prompt

        complete_agent_run_turn(
            run.id,
            request_id="req-failed-visible-002",
            owner_token=retry_claim.owner_token,
            stage_id="CLARIFY",
            assistant_content="重试成功。",
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
                "input_chars": len(failed_prompt),
                "output_chars": 5,
                "estimated_tokens": 5,
                "contract_retry_count": 0,
            },
        )
        refreshed_snapshot = get_run_snapshot(run.id)

        assert [
            (message["role"], message["content"])
            for message in refreshed_snapshot["messages"]
        ] == [
            ("user", failed_prompt),
            ("assistant", f"⚠️ **模型调用未完成**\n\n{public_reason}"),
            ("user", failed_prompt),
            ("assistant", "重试成功。"),
        ]


def test_legacy_identityless_failed_turn_fails_closed_before_building_context(app):
    failed_prompt = "LEGACY-FAILED-PROMPT-AND-SUPPLEMENT-CANARY"
    terminal_canary = "LEGACY-FAILED-TERMINAL-SECRET-CANARY"
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")
        append_run_message(run.id, "user", failed_prompt)
        legacy_request = AgentRunTurnRequest(
            run_id=run.id,
            request_id="legacy-identityless-context-failure",
            stage_id="CLARIFY",
            status="failed",
        )
        legacy_request.terminal_event = {
            "type": "error",
            "code": "LLM_ERROR",
            "message": terminal_canary,
        }
        db.session.add(legacy_request)
        db.session.commit()

        with pytest.raises(TurnPersistenceError) as captured:
            run_persistence.AgentRunPersistence().build_runtime_context(
                run.id,
                "CURRENT-SAFE-PROMPT-CANARY",
                request_id="current-safe-request",
            )

    assert str(captured.value) == "Unable to resolve durable runtime context."
    serialized_traceback = "".join(traceback.format_exception(captured.value))
    assert failed_prompt not in serialized_traceback
    assert terminal_canary not in serialized_traceback


def test_abandoned_exact_retry_refreshes_baseline_and_includes_intervening_turn(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")
        first_owner = claim_agent_run_turn_request(
            run.id,
            request_id="req-refresh-abandoned-a",
            stage_id="CLARIFY",
            user_content="A 需求",
        )
        run_persistence.abandon_agent_run_turn_request(
            run.id,
            request_id="req-refresh-abandoned-a",
            owner_token=first_owner.owner_token,
        )
        intervening = claim_agent_run_turn_request(
            run.id,
            request_id="req-refresh-abandoned-b",
            stage_id="CLARIFY",
            user_content="B 需求",
        )
        metric = {
            "workflow_id": "TEST_DESIGN",
            "stage_id": "CLARIFY",
            "model_name": "test-model",
            "provider": "test-provider",
            "status": "success",
            "error_code": None,
            "duration_ms": 1,
            "input_chars": 4,
            "output_chars": 4,
            "estimated_tokens": 2,
            "contract_retry_count": 0,
        }
        complete_agent_run_turn(
            run.id,
            request_id="req-refresh-abandoned-b",
            owner_token=intervening.owner_token,
            stage_id="CLARIFY",
            assistant_content="B 已完成-CANARY",
            artifact_content="# B 产物-CANARY",
            artifact_data=None,
            terminal_event={"type": "agent_turn", "output": {}},
            metric=metric,
        )

        retried = claim_agent_run_turn_request(
            run.id,
            request_id="req-refresh-abandoned-a",
            stage_id="CLARIFY",
            user_content="A 需求",
        )
        prompt, _warnings = run_persistence.AgentRunPersistence().build_runtime_context(
            run.id,
            "A 需求",
            request_id="req-refresh-abandoned-a",
        )
        with pytest.raises(TurnPersistenceConflictError):
            fail_agent_run_turn_request(
                run.id,
                request_id="req-refresh-abandoned-a",
                owner_token=first_owner.owner_token,
                terminal_event={"type": "error", "code": "LLM_ERROR"},
            )
        complete_agent_run_turn(
            run.id,
            request_id="req-refresh-abandoned-a",
            owner_token=retried.owner_token,
            stage_id="CLARIFY",
            assistant_content="A 重试完成",
            artifact_content="# A 重试产物",
            artifact_data=None,
            terminal_event={"type": "agent_turn", "output": {}},
            metric=metric,
        )

        assert retried.state == "new"
        assert retried.owner_token != first_owner.owner_token
        assert "B 已完成-CANARY" in prompt
        assert "# B 产物-CANARY" in prompt
        assert prompt.count("A 需求") == 1
        assert (
            AgentRunTurnRequest.query.filter_by(
                run_id=run.id,
                request_id="req-refresh-abandoned-a",
            )
            .one()
            .status
            == "completed"
        )


def test_new_request_fences_expired_owner_and_exact_retry_refreshes_after_it(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")
        expired_owner = claim_agent_run_turn_request(
            run.id,
            request_id="req-refresh-expired-a",
            stage_id="CLARIFY",
            user_content="过期 A 需求",
        )
        expired = AgentRunTurnRequest.query.filter_by(
            run_id=run.id,
            request_id="req-refresh-expired-a",
        ).one()
        expired.updated_at = datetime.now(timezone.utc).replace(
            tzinfo=None
        ) - timedelta(seconds=run_persistence.TURN_REQUEST_ACTIVE_LEASE_SECONDS + 1)
        db.session.commit()

        intervening = claim_agent_run_turn_request(
            run.id,
            request_id="req-refresh-expired-b",
            stage_id="CLARIFY",
            user_content="B 需求",
        )
        assert intervening.state == "new"
        db.session.refresh(expired)
        assert expired.status == "abandoned"
        with pytest.raises(TurnPersistenceConflictError):
            fail_agent_run_turn_request(
                run.id,
                request_id="req-refresh-expired-a",
                owner_token=expired_owner.owner_token,
                terminal_event={"type": "error", "code": "LLM_ERROR"},
            )

        metric = {
            "workflow_id": "TEST_DESIGN",
            "stage_id": "CLARIFY",
            "model_name": "test-model",
            "provider": "test-provider",
            "status": "success",
            "error_code": None,
            "duration_ms": 1,
            "input_chars": 4,
            "output_chars": 4,
            "estimated_tokens": 2,
            "contract_retry_count": 0,
        }
        complete_agent_run_turn(
            run.id,
            request_id="req-refresh-expired-b",
            owner_token=intervening.owner_token,
            stage_id="CLARIFY",
            assistant_content="B 完成后的新基线",
            artifact_content="# B 新基线产物",
            artifact_data=None,
            terminal_event={"type": "agent_turn", "output": {}},
            metric=metric,
        )

        retried = claim_agent_run_turn_request(
            run.id,
            request_id="req-refresh-expired-a",
            stage_id="CLARIFY",
            user_content="过期 A 需求",
        )
        complete_agent_run_turn(
            run.id,
            request_id="req-refresh-expired-a",
            owner_token=retried.owner_token,
            stage_id="CLARIFY",
            assistant_content="A 重试完成",
            artifact_content=None,
            artifact_data=None,
            terminal_event={"type": "agent_turn", "output": {}},
            metric=metric,
        )

        assert retried.state == "new"
        assert retried.owner_token != expired_owner.owner_token
        assert (
            AgentRunTurnRequest.query.filter_by(
                run_id=run.id,
                request_id="req-refresh-expired-a",
            )
            .one()
            .status
            == "completed"
        )


def test_new_request_fails_closed_on_legacy_expired_ledger_without_deleting_history(
    app,
):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")
        append_run_message(run.id, "user", "LEGACY-COMPLETED-USER-CANARY")
        append_run_message(run.id, "assistant", "LEGACY-COMPLETED-ASSISTANT-CANARY")
        append_run_message(
            run.id,
            "user",
            "LEGACY-EXPIRED-RAW-PROMPT-CANARY",
        )
        legacy_request = AgentRunTurnRequest(
            run_id=run.id,
            request_id="legacy-expired-request",
            stage_id="CLARIFY",
            status="active",
        )
        legacy_request.updated_at = datetime.now(timezone.utc).replace(
            tzinfo=None
        ) - timedelta(seconds=run_persistence.TURN_REQUEST_ACTIVE_LEASE_SECONDS + 1)
        db.session.add(legacy_request)
        db.session.commit()
        summary_before_claim = (
            AgentContextSummary.query.filter_by(
                run_id=run.id,
                source_type=run_persistence.SUMMARY_SOURCE_USER_INPUT,
                summary_type=run_persistence.USER_SUPPLEMENT_SUMMARY_TYPE,
            )
            .one()
            .content
        )

        claim = claim_agent_run_turn_request(
            run.id,
            request_id="request-after-legacy-expiry",
            stage_id="CLARIFY",
            user_content="CURRENT-AFTER-LEGACY-CANARY",
        )
        with pytest.raises(
            run_persistence.TurnPersistenceError,
            match="Unable to resolve durable runtime context",
        ) as captured:
            run_persistence.AgentRunPersistence().build_runtime_context(
                run.id,
                "CURRENT-AFTER-LEGACY-CANARY",
                request_id="request-after-legacy-expiry",
            )

        assert claim.state == "new"
        assert "LEGACY-EXPIRED-RAW-PROMPT-CANARY" not in str(captured.value)
        assert (
            AgentRunTurnRequest.query.filter_by(
                run_id=run.id,
                request_id="legacy-expired-request",
            )
            .one()
            .status
            == "abandoned"
        )
        assert (
            AgentMessage.query.filter_by(
                run_id=run.id,
                content="LEGACY-EXPIRED-RAW-PROMPT-CANARY",
            ).one_or_none()
            is not None
        )
        assert [
            message.content
            for message in AgentMessage.query.filter_by(run_id=run.id)
            .order_by(AgentMessage.sequence_index)
            .all()
        ] == [
            "LEGACY-COMPLETED-USER-CANARY",
            "LEGACY-COMPLETED-ASSISTANT-CANARY",
            "LEGACY-EXPIRED-RAW-PROMPT-CANARY",
            "CURRENT-AFTER-LEGACY-CANARY",
        ]
        assert (
            AgentContextSummary.query.filter_by(
                run_id=run.id,
                source_type=run_persistence.SUMMARY_SOURCE_USER_INPUT,
                summary_type=run_persistence.USER_SUPPLEMENT_SUMMARY_TYPE,
            )
            .one()
            .content
            == summary_before_claim
        )


def test_different_request_message_sequence_integrity_error_is_typed_and_atomic(
    app,
    monkeypatch,
):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")
        append_run_message(run.id, "user", "已由独立 session 占用的序号")
        monkeypatch.setattr(
            run_persistence, "_next_message_sequence", lambda _run_id: 1
        )

        with pytest.raises(TurnPersistenceConflictError):
            claim_agent_run_turn_request(
                run.id,
                request_id="req-sequence-race-other",
                stage_id="STRATEGY",
                user_content="竞争请求",
            )

        assert (
            AgentRunTurnRequest.query.filter_by(
                run_id=run.id,
                request_id="req-sequence-race-other",
            ).one_or_none()
            is None
        )
        assert [message.content for message in AgentMessage.query.all()] == [
            "已由独立 session 占用的序号"
        ]
        assert db.session.get(AgentRun, run.id).current_stage_id == "CLARIFY"


def test_runtime_context_wraps_snapshot_storage_failure(app, monkeypatch):
    import context_builder

    canary = "sk-context-storage-canary"
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")
        claim_agent_run_turn_request(
            run.id,
            request_id="req-context-storage-failure",
            stage_id="CLARIFY",
            user_content="用户需求",
        )

        def fail_snapshot(*args, **kwargs):
            raise SQLAlchemyError(canary)

        monkeypatch.setattr(context_builder, "build_run_context", fail_snapshot)

        with pytest.raises(TurnPersistenceError) as captured:
            run_persistence.AgentRunPersistence().build_runtime_context(
                run.id,
                "用户需求",
                request_id="req-context-storage-failure",
            )

        assert str(captured.value) == "Unable to build durable runtime context."
        assert captured.value.__cause__ is None
        assert captured.value.__context__ is None
        assert canary not in "".join(traceback.format_exception(captured.value))


def test_blocked_overlapping_request_cannot_persist_a_stale_completion(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")
        first = claim_agent_run_turn_request(
            run.id,
            request_id="req-overlap-first",
            stage_id="CLARIFY",
            user_content="第一条并发需求",
        )
        second = claim_agent_run_turn_request(
            run.id,
            request_id="req-overlap-second",
            stage_id="CLARIFY",
            user_content="第二条并发需求",
        )
        assert second == run_persistence.TurnRequestClaim(state="active")
        metric = {
            "workflow_id": "TEST_DESIGN",
            "stage_id": "CLARIFY",
            "model_name": "test-model",
            "provider": "test-provider",
            "status": "success",
            "error_code": None,
            "duration_ms": 1,
            "input_chars": 8,
            "output_chars": 8,
            "estimated_tokens": 4,
            "contract_retry_count": 0,
        }

        complete_agent_run_turn(
            run.id,
            request_id="req-overlap-first",
            owner_token=first.owner_token,
            stage_id="CLARIFY",
            assistant_content="第一条完成",
            artifact_content="# 第一版产物",
            artifact_data=None,
            terminal_event={"type": "agent_turn", "output": {}},
            metric=metric,
        )
        with pytest.raises(TurnPersistenceConflictError):
            complete_agent_run_turn(
                run.id,
                request_id="req-overlap-second",
                owner_token=second.owner_token,
                stage_id="CLARIFY",
                assistant_content="第二条陈旧结果",
                artifact_content="# 第二版陈旧产物",
                artifact_data=None,
                terminal_event={"type": "agent_turn", "output": {}},
                metric=metric,
            )

        artifact = AgentArtifact.query.filter_by(
            run_id=run.id,
            stage_id="CLARIFY",
        ).one()
        assert AgentMessage.query.filter_by(run_id=run.id, role="user").count() == 1
        assert (
            AgentMessage.query.filter_by(run_id=run.id, role="assistant").count() == 1
        )
        assert (
            AgentArtifactVersion.query.filter_by(artifact_id=artifact.id).count() == 1
        )
        assert AgentRunTurnMetric.query.filter_by(run_id=run.id).count() == 1


@pytest.mark.parametrize("terminal_state", ["completed", "failed"])
def test_bound_user_supplement_is_recorded_only_for_completed_turns(
    app,
    terminal_state,
):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")
        claim = claim_agent_run_turn_request(
            run.id,
            request_id=f"req-terminal-supplement-{terminal_state}",
            stage_id="CLARIFY",
            user_content="TERMINAL-SUPPLEMENT-CANARY-001",
        )
        assert AgentContextSummary.query.filter_by(run_id=run.id).count() == 0

        if terminal_state == "completed":
            complete_agent_run_turn(
                run.id,
                request_id=f"req-terminal-supplement-{terminal_state}",
                owner_token=claim.owner_token,
                stage_id="CLARIFY",
                assistant_content="完成",
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
                    "output_chars": 2,
                    "estimated_tokens": 3,
                    "contract_retry_count": 0,
                },
            )
        else:
            fail_agent_run_turn_request(
                run.id,
                request_id=f"req-terminal-supplement-{terminal_state}",
                owner_token=claim.owner_token,
                terminal_event={"type": "error", "code": "LLM_ERROR"},
            )

        summaries = AgentContextSummary.query.filter_by(run_id=run.id).all()
        if terminal_state == "completed":
            assert [summary.content for summary in summaries] == [
                "TERMINAL-SUPPLEMENT-CANARY-001"
            ]
        else:
            assert summaries == []


@pytest.mark.parametrize(
    "terminal_state", ["completed", "failed", "abandoned", "expired"]
)
@pytest.mark.parametrize("mismatch", ["system_prompt", "model_name"])
def test_turn_request_identity_rejects_runtime_input_mismatch_in_every_state(
    app,
    terminal_state,
    mismatch,
):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")
        first = claim_agent_run_turn_request(
            run.id,
            request_id=f"req-runtime-identity-{terminal_state}-{mismatch}",
            stage_id="CLARIFY",
            user_content="请分析登录需求",
            system_prompt="系统提示 A",
            model_name="model-a",
        )
        request_id = f"req-runtime-identity-{terminal_state}-{mismatch}"
        if terminal_state == "completed":
            complete_agent_run_turn(
                run.id,
                request_id=request_id,
                owner_token=first.owner_token,
                stage_id="CLARIFY",
                assistant_content="完成",
                artifact_content=None,
                artifact_data=None,
                terminal_event={"type": "agent_turn", "output": {}},
                metric={
                    "workflow_id": "TEST_DESIGN",
                    "stage_id": "CLARIFY",
                    "model_name": "model-a",
                    "provider": "test-provider",
                    "status": "success",
                    "error_code": None,
                    "duration_ms": 1,
                    "input_chars": 8,
                    "output_chars": 2,
                    "estimated_tokens": 3,
                    "contract_retry_count": 0,
                },
            )
        elif terminal_state == "failed":
            fail_agent_run_turn_request(
                run.id,
                request_id=request_id,
                owner_token=first.owner_token,
                terminal_event={"type": "error", "code": "LLM_ERROR"},
            )
        elif terminal_state == "abandoned":
            run_persistence.abandon_agent_run_turn_request(
                run.id,
                request_id=request_id,
                owner_token=first.owner_token,
            )
        else:
            stored = AgentRunTurnRequest.query.filter_by(
                run_id=run.id,
                request_id=request_id,
            ).one()
            stored.updated_at = datetime.now(timezone.utc).replace(
                tzinfo=None
            ) - timedelta(seconds=run_persistence.TURN_REQUEST_ACTIVE_LEASE_SECONDS + 1)
            db.session.commit()

        with pytest.raises(TurnRequestIdentityConflictError):
            claim_agent_run_turn_request(
                run.id,
                request_id=request_id,
                stage_id="CLARIFY",
                user_content="请分析登录需求",
                system_prompt=(
                    "系统提示 B" if mismatch == "system_prompt" else "系统提示 A"
                ),
                model_name="model-b" if mismatch == "model_name" else "model-a",
            )


def test_complete_turn_rejects_stage_that_differs_from_bound_request(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")
        claim_agent_run_turn_request(
            run.id,
            request_id="req-stage-bound-001",
            stage_id="CLARIFY",
            user_content="请分析登录需求",
        )

        with pytest.raises(
            TurnRequestIdentityConflictError,
            match="requestId identity conflict",
        ):
            complete_agent_run_turn(
                run.id,
                request_id="req-stage-bound-001",
                stage_id="STRATEGY",
                assistant_content="错误阶段结果",
                artifact_content="# 错误阶段产物",
                artifact_data=None,
                terminal_event={"type": "agent_turn", "output": {}},
                metric={
                    "workflow_id": "TEST_DESIGN",
                    "stage_id": "STRATEGY",
                    "model_name": "test-model",
                    "provider": "test-provider",
                    "status": "success",
                    "error_code": None,
                    "duration_ms": 1,
                    "input_chars": 8,
                    "output_chars": 8,
                    "estimated_tokens": 4,
                    "contract_retry_count": 0,
                },
            )

        stored = AgentRunTurnRequest.query.filter_by(
            run_id=run.id,
            request_id="req-stage-bound-001",
        ).one()
        assert stored.status == "active"
        assert (
            AgentMessage.query.filter_by(run_id=run.id, role="assistant").count() == 0
        )
        assert AgentArtifact.query.filter_by(run_id=run.id).count() == 0


def test_turn_request_claim_replays_recorded_failure_without_appending_another_user_message(
    app,
):
    canary = "opaque-legacy-provider-output"
    public_reason = (
        "模型供应商鉴权失败，请检查 API Key、Base URL、模型名称和供应商权限。"
    )
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")
        run_id = run.id
        first = claim_agent_run_turn_request(
            run_id,
            request_id="req-login-failure",
            stage_id="CLARIFY",
            user_content="请分析登录需求",
        )
        terminal_event = {
            "type": "error",
            "code": "LLM_ERROR",
            "message": canary,
            "diagnostic": {
                "phase": "provider",
                "workflowId": "TEST_DESIGN",
                "stageId": "CLARIFY",
                "fieldPath": "provider",
                "validator": "provider_authentication",
                "retryable": True,
                "publicReason": canary,
            },
        }
        fail_agent_run_turn_request(
            run.id,
            request_id="req-login-failure",
            owner_token=first.owner_token,
            terminal_event=terminal_event,
        )

        replay = claim_agent_run_turn_request(
            run.id,
            request_id="req-login-failure",
            stage_id="CLARIFY",
            user_content="请分析登录需求",
        )

        assert replay.state == "failed"
        assert replay.terminal_event == {
            "type": "error",
            "code": "LLM_ERROR",
            "message": public_reason,
            "diagnostic": {
                "phase": "provider",
                "workflowId": "TEST_DESIGN",
                "stageId": "CLARIFY",
                "fieldPath": "provider",
                "validator": "provider_authentication",
                "retryable": False,
                "publicReason": public_reason,
            },
        }
        stored = AgentRunTurnRequest.query.filter_by(
            run_id=run_id,
            request_id="req-login-failure",
        ).one()
        assert canary not in str(stored.terminal_event)
        stored_messages = AgentMessage.query.order_by(AgentMessage.sequence_index).all()
        assert [(message.role, message.content) for message in stored_messages] == [
            ("user", "请分析登录需求"),
            (
                "assistant",
                f"⚠️ **模型调用未完成**\n\n{public_reason}",
            ),
        ]
        assert canary not in str(stored_messages)


def test_turn_request_claim_scrubs_and_rejects_unverifiable_legacy_failure(app):
    canary = "OpaqueLegacyTerminalCanary987"
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")
        request = AgentRunTurnRequest(
            run_id=run.id,
            request_id="req-legacy-failure",
            stage_id="CLARIFY",
            status="failed",
        )
        request.terminal_event = {
            "type": "error",
            "code": ["legacy", canary],
            "message": canary,
            "diagnostic": {
                "validator": {"legacy": canary},
                "publicReason": canary,
            },
        }
        db.session.add(request)
        db.session.commit()

        with pytest.raises(
            TurnRequestIdentityConflictError,
            match="requestId identity conflict",
        ):
            claim_agent_run_turn_request(
                run.id,
                request_id="req-legacy-failure",
                stage_id="CLARIFY",
                user_content="请重新分析登录需求",
            )

        db.session.expire_all()
        stored = AgentRunTurnRequest.query.filter_by(
            run_id=run.id,
            request_id="req-legacy-failure",
        ).one()
        assert stored.status == "failed"
        assert stored.terminal_event["code"] == "LLM_ERROR"
        assert canary not in str(stored.terminal_event)
        assert canary not in stored.terminal_event_json


def test_turn_request_unique_identity_is_enforced_across_independent_db_sessions(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")
        session_factory = sessionmaker(bind=db.engine)
        first_session = session_factory()
        second_session = session_factory()
        try:
            assert (
                first_session.query(AgentRunTurnRequest)
                .filter_by(
                    run_id=run.id,
                    request_id="cross-session-request-001",
                )
                .one_or_none()
                is None
            )
            assert (
                second_session.query(AgentRunTurnRequest)
                .filter_by(
                    run_id=run.id,
                    request_id="cross-session-request-001",
                )
                .one_or_none()
                is None
            )

            first_session.add(
                AgentRunTurnRequest(
                    run_id=run.id,
                    request_id="cross-session-request-001",
                    stage_id="CLARIFY",
                    status="active",
                )
            )
            first_session.commit()

            second_session.add(
                AgentRunTurnRequest(
                    run_id=run.id,
                    request_id="cross-session-request-001",
                    stage_id="CLARIFY",
                    status="active",
                )
            )
            with pytest.raises(IntegrityError):
                second_session.commit()
            second_session.rollback()
        finally:
            first_session.close()
            second_session.close()

        assert (
            AgentRunTurnRequest.query.filter_by(
                run_id=run.id,
                request_id="cross-session-request-001",
            ).count()
            == 1
        )


def test_concurrent_different_request_claims_create_only_one_active_turn(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")
        run_id = run.id
    start = threading.Barrier(2)
    outcomes: dict[str, object] = {}

    def claim_in_separate_session(role: str) -> None:
        with app.app_context():
            try:
                start.wait(timeout=5)
                outcomes[role] = claim_agent_run_turn_request(
                    run_id,
                    request_id=f"concurrent-claim-{role}",
                    stage_id="CLARIFY",
                    user_content=f"{role} 并发请求",
                )
            except (SQLAlchemyError, TurnPersistenceError, ValueError) as error:
                outcomes[role] = error

    first = threading.Thread(
        target=claim_in_separate_session,
        args=("first",),
        name="first-claim",
    )
    second = threading.Thread(
        target=claim_in_separate_session,
        args=("second",),
        name="second-claim",
    )
    first.start()
    second.start()
    first.join(timeout=10)
    second.join(timeout=10)

    assert not first.is_alive()
    assert not second.is_alive()
    assert all(
        isinstance(outcome, run_persistence.TurnRequestClaim)
        for outcome in outcomes.values()
    )
    assert sorted(outcome.state for outcome in outcomes.values()) == ["active", "new"]
    with app.app_context():
        messages = (
            AgentMessage.query.filter_by(run_id=run_id)
            .order_by(AgentMessage.sequence_index)
            .all()
        )
        assert [(message.role, message.sequence_index) for message in messages] == [
            ("user", 1),
        ]
        assert (
            AgentRunTurnRequest.query.filter_by(
                run_id=run_id,
                status="active",
            ).count()
            == 1
        )


def test_blocked_request_cannot_create_a_competing_artifact_version(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")
        run_id = run.id
        record_artifact_version(run_id, "CLARIFY", "# 初始产出物")
        first = claim_agent_run_turn_request(
            run_id,
            request_id="concurrent-version-first",
            stage_id="CLARIFY",
            user_content="第一条版本请求",
        )
        blocked = claim_agent_run_turn_request(
            run_id,
            request_id="concurrent-version-second",
            stage_id="CLARIFY",
            user_content="第二条版本请求",
        )
        metric = {
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
        }
        complete_agent_run_turn(
            run_id,
            request_id="concurrent-version-first",
            owner_token=first.owner_token,
            stage_id="CLARIFY",
            assistant_content="first 完成",
            artifact_content="# first 产出物",
            artifact_data=None,
            terminal_event={"type": "agent_turn", "output": {}},
            metric=metric,
        )
        with pytest.raises(TurnPersistenceConflictError):
            complete_agent_run_turn(
                run_id,
                request_id="concurrent-version-second",
                owner_token=blocked.owner_token,
                stage_id="CLARIFY",
                assistant_content="blocked 完成",
                artifact_content="# blocked 产出物",
                artifact_data=None,
                terminal_event={"type": "agent_turn", "output": {}},
                metric=metric,
            )

        artifact = AgentArtifact.query.filter_by(
            run_id=run_id,
            stage_id="CLARIFY",
        ).one()
        assert (
            AgentArtifactVersion.query.filter_by(artifact_id=artifact.id).count() == 2
        )
        assert (
            AgentMessage.query.filter_by(run_id=run_id, role="assistant").count() == 1
        )


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
        assert (
            AgentArtifactVersion.query.filter_by(artifact_id=artifact.id).count() == 2
        )


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


def test_clone_fails_closed_on_unresolved_turn_history_without_creating_run(app):
    with app.app_context():
        source = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")
        append_run_message(source.id, "user", "SAFE-COMPLETED-USER-CANARY")
        append_run_message(source.id, "assistant", "SAFE-COMPLETED-ASSISTANT-CANARY")
        append_run_message(source.id, "user", "LEGACY-UNBOUND-RAW-PROMPT-CANARY")
        db.session.add(
            AgentRunTurnRequest(
                run_id=source.id,
                request_id="legacy-unbound-clone-request",
                stage_id="CLARIFY",
                status="abandoned",
            )
        )
        db.session.commit()
        source_snapshot = get_run_snapshot(source.id)
        run_count = AgentRun.query.count()

        with pytest.raises(
            TurnPersistenceError,
            match="Unable to clone a run with unresolved turn requests",
        ) as captured:
            clone_agent_run(source.id)

        assert "LEGACY-UNBOUND-RAW-PROMPT-CANARY" not in str(captured.value)
        assert AgentRun.query.count() == run_count
        assert get_run_snapshot(source.id) == source_snapshot


def test_clone_rechecks_unresolved_history_inside_atomic_copy(app, monkeypatch):
    with app.app_context():
        source = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")
        append_run_message(source.id, "user", "SAFE-COMPLETED-USER-CANARY")
        append_run_message(source.id, "assistant", "SAFE-COMPLETED-ASSISTANT-CANARY")
        source_snapshot = get_run_snapshot(source.id)
        run_count = AgentRun.query.count()
        original_create_agent_run = run_persistence.create_agent_run

        def inject_unresolved_turn_before_clone_copy(*args, **kwargs):
            append_run_message(
                source.id,
                "user",
                "INTERLEAVED-RAW-PROMPT-CANARY",
                _commit=False,
                _summarize_user=False,
            )
            db.session.add(
                AgentRunTurnRequest(
                    run_id=source.id,
                    request_id="interleaved-clone-request",
                    stage_id="CLARIFY",
                    status="active",
                )
            )
            db.session.flush()
            return original_create_agent_run(*args, **kwargs)

        monkeypatch.setattr(
            run_persistence,
            "create_agent_run",
            inject_unresolved_turn_before_clone_copy,
        )

        with pytest.raises(
            TurnPersistenceError,
            match="Unable to clone a run with unresolved turn requests",
        ):
            clone_agent_run(source.id)

        assert AgentRun.query.count() == run_count
        assert get_run_snapshot(source.id) == source_snapshot
        assert (
            AgentMessage.query.filter_by(
                run_id=source.id,
                content="INTERLEAVED-RAW-PROMPT-CANARY",
            ).one_or_none()
            is None
        )


def test_clone_excludes_bound_abandoned_user_message_without_blocking_run(app):
    with app.app_context():
        source = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")
        append_run_message(source.id, "user", "SAFE-COMPLETED-USER-CANARY")
        append_run_message(source.id, "assistant", "SAFE-COMPLETED-ASSISTANT-CANARY")
        abandoned = claim_agent_run_turn_request(
            source.id,
            request_id="bound-abandoned-clone-request",
            stage_id="CLARIFY",
            user_content="BOUND-ABANDONED-RAW-PROMPT-CANARY",
        )
        run_persistence.abandon_agent_run_turn_request(
            source.id,
            request_id="bound-abandoned-clone-request",
            owner_token=abandoned.owner_token,
        )

        cloned = clone_agent_run(source.id)
        cloned_snapshot = get_run_snapshot(cloned.id)
        source_snapshot = get_run_snapshot(source.id)

        assert [message["content"] for message in cloned_snapshot["messages"]] == [
            "SAFE-COMPLETED-USER-CANARY",
            "SAFE-COMPLETED-ASSISTANT-CANARY",
        ]
        assert "BOUND-ABANDONED-RAW-PROMPT-CANARY" in [
            message["content"] for message in source_snapshot["messages"]
        ]
        assert "BOUND-ABANDONED-RAW-PROMPT-CANARY" not in str(
            cloned_snapshot["contextSummaries"]
        )
        assert "SAFE-COMPLETED-USER-CANARY" in str(cloned_snapshot["contextSummaries"])


def test_clone_excludes_failed_turn_and_rebuilds_only_completed_user_supplements(app):
    completed_prompt = "COMPLETED-CLONE-CONTEXT-CANARY"
    failed_prompt = "FAILED-CLONE-PROMPT-AND-SUPPLEMENT-CANARY"
    current_prompt = "CURRENT-CLONE-PROMPT-CANARY"
    with app.app_context():
        source = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")
        completed = claim_agent_run_turn_request(
            source.id,
            request_id="completed-before-failed-clone",
            stage_id="CLARIFY",
            user_content=completed_prompt,
            model_name="test-model",
        )
        complete_agent_run_turn(
            source.id,
            request_id="completed-before-failed-clone",
            owner_token=completed.owner_token,
            stage_id="CLARIFY",
            assistant_content="COMPLETED-CLONE-ASSISTANT-CANARY",
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
                "input_chars": len(completed_prompt),
                "output_chars": 1,
                "estimated_tokens": 1,
                "contract_retry_count": 0,
            },
        )
        failed = claim_agent_run_turn_request(
            source.id,
            request_id="failed-before-clone",
            stage_id="CLARIFY",
            user_content=failed_prompt,
            model_name="test-model",
        )
        fail_agent_run_turn_request(
            source.id,
            request_id="failed-before-clone",
            owner_token=failed.owner_token,
            terminal_event={"type": "error", "code": "LLM_ERROR"},
        )
        # Simulate a pre-fix source that summarized the failed prompt at claim time.
        run_persistence._append_user_supplement_summary(
            source.id,
            "CLARIFY",
            failed_prompt,
        )
        db.session.commit()

        cloned = clone_agent_run(source.id)
        cloned_snapshot = get_run_snapshot(cloned.id)
        cloned_claim = claim_agent_run_turn_request(
            cloned.id,
            request_id="current-clone-request",
            stage_id="CLARIFY",
            user_content=current_prompt,
            model_name="test-model",
        )
        (
            context,
            _warnings,
        ) = run_persistence.AgentRunPersistence().build_runtime_context(
            cloned.id,
            current_prompt,
            request_id="current-clone-request",
        )

        assert cloned_claim.state == "new"
        assert [
            (message["role"], message["content"])
            for message in cloned_snapshot["messages"]
        ] == [
            ("user", completed_prompt),
            ("assistant", "COMPLETED-CLONE-ASSISTANT-CANARY"),
        ]
        assert completed_prompt in str(cloned_snapshot["contextSummaries"])
        assert failed_prompt not in str(cloned_snapshot["contextSummaries"])
        assert completed_prompt in context
        assert failed_prompt not in context
        assert "模型调用未完成" not in context
        assert context.count(current_prompt) == 1


def test_clone_fails_closed_when_failed_assistant_cannot_be_safely_associated(app):
    with app.app_context():
        source = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")
        failed = claim_agent_run_turn_request(
            source.id,
            request_id="failed-with-invalid-assistant",
            stage_id="CLARIFY",
            user_content="FAILED-ASSOCIATION-PROMPT-CANARY",
        )
        fail_agent_run_turn_request(
            source.id,
            request_id="failed-with-invalid-assistant",
            owner_token=failed.owner_token,
            terminal_event={"type": "error", "code": "LLM_ERROR"},
        )
        assistant = AgentMessage.query.filter_by(
            run_id=source.id,
            role="assistant",
        ).one()
        assistant.content = "UNRELATED-ASSISTANT-CANARY"
        db.session.commit()
        source_snapshot = get_run_snapshot(source.id)
        run_count = AgentRun.query.count()

        with pytest.raises(
            TurnPersistenceError,
            match="Unable to clone a run with unresolved turn requests",
        ):
            clone_agent_run(source.id)

        assert AgentRun.query.count() == run_count
        assert get_run_snapshot(source.id) == source_snapshot


def test_clone_storage_failure_has_no_raw_exception_chain_and_is_atomic(
    app,
    monkeypatch,
):
    with app.app_context():
        source = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")
        append_run_message(source.id, "user", "SAFE-COMPLETED-USER-CANARY")
        append_run_message(source.id, "assistant", "SAFE-COMPLETED-ASSISTANT-CANARY")
        record_artifact_version(source.id, "CLARIFY", "# 安全产物\n\n## 业务内容\n完成")
        source_snapshot = get_run_snapshot(source.id)
        run_count = AgentRun.query.count()
        canary = "SQL-OWNER-TOKEN-PARAMETER-CANARY"
        original_artifact_snapshot = run_persistence._artifact_snapshot

        def fail_artifact_snapshot(_artifact):
            raise SQLAlchemyError(canary)

        monkeypatch.setattr(
            run_persistence,
            "_artifact_snapshot",
            fail_artifact_snapshot,
        )

        with pytest.raises(TurnPersistenceError) as captured:
            clone_agent_run(source.id)

        assert str(captured.value) == "Unable to clone the agent run."
        assert captured.value.__cause__ is None
        assert captured.value.__context__ is None
        assert canary not in "".join(traceback.format_exception(captured.value))
        assert AgentRun.query.count() == run_count
        monkeypatch.setattr(
            run_persistence,
            "_artifact_snapshot",
            original_artifact_snapshot,
        )
        assert get_run_snapshot(source.id) == source_snapshot


def test_clone_and_new_claim_share_the_source_run_mutex(app, monkeypatch):
    with app.app_context():
        source = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")
        append_run_message(source.id, "user", "SAFE-COMPLETED-USER-CANARY")
        append_run_message(source.id, "assistant", "SAFE-COMPLETED-ASSISTANT-CANARY")
        source_run_id = source.id

    original_lock = run_persistence._lock_agent_run_turn_slot
    clone_locked = threading.Event()
    claim_entered_lock = threading.Event()
    release_clone = threading.Event()
    outcomes: dict[str, object] = {}

    def coordinated_lock(run_id: str) -> None:
        thread_name = threading.current_thread().name
        if thread_name == "clone-run":
            original_lock(run_id)
            clone_locked.set()
            if not release_clone.wait(timeout=5):
                raise RuntimeError("clone mutex test timed out")
            return
        if thread_name == "claim-run":
            claim_entered_lock.set()
        original_lock(run_id)

    monkeypatch.setattr(
        run_persistence,
        "_lock_agent_run_turn_slot",
        coordinated_lock,
    )

    def clone_in_separate_session() -> None:
        with app.app_context():
            try:
                outcomes["clone"] = clone_agent_run(source_run_id).id
            except (SQLAlchemyError, TurnPersistenceError, ValueError) as error:
                outcomes["clone"] = error

    def claim_in_separate_session() -> None:
        with app.app_context():
            try:
                outcomes["claim"] = claim_agent_run_turn_request(
                    source_run_id,
                    request_id="claim-after-clone-lock",
                    stage_id="CLARIFY",
                    user_content="CLAIM-AFTER-CLONE-RAW-PROMPT-CANARY",
                )
            except (SQLAlchemyError, TurnPersistenceError, ValueError) as error:
                outcomes["claim"] = error

    clone_thread = threading.Thread(target=clone_in_separate_session, name="clone-run")
    claim_thread = threading.Thread(target=claim_in_separate_session, name="claim-run")
    clone_thread.start()
    assert clone_locked.wait(timeout=5)
    claim_thread.start()
    assert claim_entered_lock.wait(timeout=5)
    release_clone.set()
    clone_thread.join(timeout=10)
    claim_thread.join(timeout=10)

    assert not clone_thread.is_alive()
    assert not claim_thread.is_alive()
    assert isinstance(outcomes["clone"], str)
    assert isinstance(outcomes["claim"], run_persistence.TurnRequestClaim)
    assert outcomes["claim"].state == "new"
    with app.app_context():
        cloned_snapshot = get_run_snapshot(outcomes["clone"])
        source_snapshot = get_run_snapshot(source_run_id)
    assert "CLAIM-AFTER-CLONE-RAW-PROMPT-CANARY" not in str(cloned_snapshot["messages"])
    assert "CLAIM-AFTER-CLONE-RAW-PROMPT-CANARY" in str(source_snapshot["messages"])


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

    assert [event["eventType"] for event in snapshot["artifactAuditEvents"]] == [
        "artifact_saved",
        "collaboration_updated",
    ]
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
        "workflowId": "TEST_DESIGN",
        "stageId": "CLARIFY",
        "fieldPath": "artifact_data",
        "validator": "string_too_short",
        "publicReason": "模型输出的结构化字段未通过校验，右侧产出物已保持不变。",
        "retryable": True,
    }


@pytest.mark.parametrize(
    ("stage_id", "validator", "expected_field_path"),
    [
        (
            "DELIVERY",
            "delivery_total_cases_mismatch",
            "artifact_data.delivery_metrics.total_cases",
        ),
        (
            "DELIVERY",
            "delivery_high_risk_count_mismatch",
            "artifact_data.delivery_metrics.high_risk_count",
        ),
        (
            "CLARIFY",
            "clarify_question_status_literal",
            "artifact_data.clarification_questions[].status",
        ),
    ],
)
def test_observability_preserves_safe_schema_projection(
    app,
    stage_id,
    validator,
    expected_field_path,
):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", stage_id)
        record_turn_metric(
            run_id=run.id,
            workflow_id="TEST_DESIGN",
            stage_id=stage_id,
            model_name="deepseek-v4-flash",
            provider="deepseek",
            status="error",
            error_code="SCHEMA_VALIDATION_FAILED",
            duration_ms=1200,
            input_chars=80,
            output_chars=0,
            estimated_tokens=20,
            contract_retry_count=1,
            diagnostic={
                "phase": "structured_output",
                "fieldPath": "artifact_data.delivery_metrics",
                "validator": validator,
                "publicReason": "模型输出的结构化字段未通过校验，右侧产出物已保持不变。",
                "retryable": True,
            },
        )

        summary = get_runtime_observability_summary(limit=5)

    assert summary["recentTurns"][0]["diagnostic"]["validator"] == validator
    assert summary["recentTurns"][0]["diagnostic"]["fieldPath"] == (expected_field_path)


def test_record_turn_metric_rolls_back_and_raises_fixed_persistence_error(
    app,
    monkeypatch,
):
    canary = "opaque-metric-database-failure-canary"
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")
        original_commit = db.session.commit
        original_rollback = db.session.rollback
        rollback_calls = []

        def fail_commit():
            raise SQLAlchemyError(canary)

        def track_rollback():
            rollback_calls.append(True)
            original_rollback()

        monkeypatch.setattr(db.session, "commit", fail_commit)
        monkeypatch.setattr(db.session, "rollback", track_rollback)

        with pytest.raises(run_persistence.TurnPersistenceError) as captured:
            record_turn_metric(
                run_id=run.id,
                workflow_id="TEST_DESIGN",
                stage_id="CLARIFY",
                model_name="deepseek-chat",
                provider="deepseek",
                status="error",
                error_code="LLM_ERROR",
                duration_ms=100,
                input_chars=10,
                output_chars=0,
                estimated_tokens=3,
                contract_retry_count=0,
            )

        monkeypatch.setattr(db.session, "commit", original_commit)

        assert str(captured.value) == "Unable to persist the agent turn metric."
        assert captured.value.__cause__ is None
        assert captured.value.__context__ is None
        assert canary not in str(captured.value)
        assert rollback_calls == [True]
        assert AgentRunTurnMetric.query.count() == 0


def test_observability_sanitizes_legacy_metric_diagnostic_at_read_boundary(app):
    canary = "sk-legacy-provider-output-canary"
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")
        metric = record_turn_metric(
            run_id=run.id,
            workflow_id="TEST_DESIGN",
            stage_id="CLARIFY",
            model_name="deepseek-chat",
            provider="deepseek",
            status="error",
            error_code="LLM_ERROR",
            duration_ms=1200,
            input_chars=80,
            output_chars=0,
            estimated_tokens=20,
            contract_retry_count=0,
        )
        metric.diagnostic = {
            "phase": "provider",
            "workflowId": "TEST_DESIGN",
            "stageId": "CLARIFY",
            "fieldPath": f"provider raw response {canary}",
            "validator": "provider_error",
            "publicReason": f"provider/model raw text: {canary}",
            "retryable": True,
            "providerResponse": f"upstream response {canary}",
            "modelOutput": f"model output {canary}",
        }
        db.session.commit()

        summary = get_runtime_observability_summary(limit=5)

    diagnostic = summary["recentTurns"][0]["diagnostic"]
    assert diagnostic == {
        "phase": "provider",
        "workflowId": "TEST_DESIGN",
        "stageId": "CLARIFY",
        "fieldPath": "provider",
        "validator": "provider_error",
        "publicReason": "模型供应商返回错误，本轮生成未完成，右侧产出物已保持不变。",
        "retryable": True,
    }
    assert canary not in str(diagnostic)


def test_observability_projects_unknown_legacy_error_code(app):
    canary = "sk-legacy-error-code-canary"
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")
        metric = record_turn_metric(
            run_id=run.id,
            workflow_id="TEST_DESIGN",
            stage_id="CLARIFY",
            model_name="deepseek-chat",
            provider="deepseek",
            status="error",
            error_code="LLM_ERROR",
            duration_ms=1200,
            input_chars=80,
            output_chars=0,
            estimated_tokens=20,
            contract_retry_count=0,
        )
        metric.error_code = canary
        db.session.commit()

        summary = get_runtime_observability_summary(limit=5)

    safe_code = "UNKNOWN_RUNTIME_ERROR"
    assert summary["byStage"][0]["errorCodes"] == {safe_code: 1}
    assert summary["byProvider"][0]["errorCodes"] == {safe_code: 1}
    assert summary["recentTurns"][0]["errorCode"] == safe_code
    assert canary not in str(summary)


def test_observability_scrubs_opaque_legacy_extra_field_at_rest(app):
    canary = "OpaqueLegacyField987654"
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")
        metric = record_turn_metric(
            run_id=run.id,
            workflow_id="TEST_DESIGN",
            stage_id="CLARIFY",
            model_name="deepseek-chat",
            provider="deepseek",
            status="error",
            error_code="SCHEMA_VALIDATION_FAILED",
            duration_ms=100,
            input_chars=10,
            output_chars=0,
            estimated_tokens=3,
            contract_retry_count=1,
        )
        metric.diagnostic = {
            "phase": "structured_output",
            "workflowId": "TEST_DESIGN",
            "stageId": "CLARIFY",
            "fieldPath": f"artifact_data.{canary}",
            "validator": "extra_forbidden",
            "publicReason": canary,
            "retryable": True,
        }
        db.session.commit()

        summary = get_runtime_observability_summary(limit=5)

        db.session.expire_all()
        stored = db.session.get(type(metric), metric.id)
        diagnostic = summary["recentTurns"][0]["diagnostic"]
        assert diagnostic["fieldPath"] == "artifact_data.extra_field"
        assert canary not in str(diagnostic)
        assert canary not in stored.diagnostic_json


def test_record_artifact_version_persists_current_artifact_summary(app):
    with app.app_context():
        run = create_agent_run("TEST_DESIGN", "lisa", "CLARIFY")

        record_artifact_version(run.id, "CLARIFY", "# 结论\n\n- 目标：提升转化")
        snapshot = get_run_snapshot(run.id)

    summaries = {
        summary["summaryType"]: summary for summary in snapshot["contextSummaries"]
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
        "- 决定优先自动化登录回归\n" "- P0 风险先覆盖第三方回调失败"
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
