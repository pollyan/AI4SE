import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from api_responses import DEFAULT_LLM_CONFIG_MISSING_CODE
from agent_contracts import WORKFLOW_STAGES
from context_summary_format import (
    CURRENT_ARTIFACT_SUMMARY_TYPE,
    DECISION_SUMMARY_TYPE,
    STAGE_CONCLUSION_SUMMARY_TYPE,
    USER_SUPPLEMENT_SUMMARY_TYPE,
    build_artifact_summary_content,
    build_decision_summary_content,
    build_stage_conclusion_summary_content,
    build_user_supplement_summary_content,
)
from run_collaboration_state import (
    audit_event_snapshot,
    build_collaboration_state_models,
    comment_snapshot,
    section_lock_snapshot,
)
from safe_error_diagnostics import (
    SAFE_RESPONSE_SCHEMA_VALIDATORS,
    project_safe_schema_field_path,
)
from models import (
    AgentArtifact,
    AgentArtifactAuditEvent,
    AgentArtifactComment,
    AgentArtifactSectionLock,
    AgentArtifactVersion,
    AgentContextSummary,
    AgentMessage,
    AgentRun,
    AgentRunTurnRequest,
    AgentRunTurnMetric,
    AgentRuntimeConfigIssue,
    db,
)
from workflow_manifest import get_workflow_agent_id

MESSAGE_ROLES = {"user", "assistant"}
RUN_STATUSES = {"active", "completed", "failed"}
RUN_REUSE_STATUSES = {"ready", "needs_artifact", "failed"}
SUMMARY_SOURCE_ARTIFACT = "artifact"
SUMMARY_SOURCE_USER_INPUT = "user_input"
DEFAULT_RUN_LIST_LIMIT = 20
MAX_RUN_LIST_LIMIT = 100
PROVIDER_ISSUE_ERROR_CODES = {"LLM_ERROR", DEFAULT_LLM_CONFIG_MISSING_CODE}
LOW_OBSERVABILITY_SUCCESS_RATE_THRESHOLD = 80.0
CONTRACT_RETRY_REASON = "STRUCTURED_OUTPUT_CONTRACT_RETRY"
TURN_REQUEST_IDENTITY_KEY = "_requestIdentity"
TURN_REQUEST_OWNER_KEY = "_ownerLease"
TURN_REQUEST_TERMINAL_EVENT_KEY = "terminalEvent"
TURN_REQUEST_ACTIVE_LEASE_SECONDS = 15 * 60
DEFAULT_ERROR_PUBLIC_REASON = "本轮生成失败，右侧产出物已保持不变。"
ERROR_PUBLIC_REASONS = {
    "AGENT_RUNTIME_UNAVAILABLE": "智能体运行时依赖不可用，本轮生成未开始。",
    "CONTRACT_VALIDATION_FAILED": (
        "模型输出未满足当前工作流产物契约，右侧产出物已保持不变。"
    ),
    "PERSISTENCE_CONFLICT": "另一项并发更新已占用当前产出物版本，请重新发起本轮生成。",
    "PERSISTENCE_FAILED": (
        "本轮结果未能安全保存，右侧产出物和历史版本均未作为成功结果提交。"
    ),
    "REQUEST_IN_PROGRESS": "相同请求仍在运行中，请等待其完成或恢复同一请求。",
    "REQUEST_IDENTITY_CONFLICT": "requestId 已绑定到另一个阶段或输入，请使用新的 requestId。",
    "REQUEST_VALIDATION_FAILED": "请求参数未通过校验，本轮生成未开始。",
    "SCHEMA_VALIDATION_FAILED": (
        "模型输出的结构化字段未通过校验，右侧产出物已保持不变。"
    ),
    "VISUAL_VALIDATION_FAILED": (
        "产出物中的可视化内容未通过校验，右侧产出物已保持不变。"
    ),
}
SCHEMA_RETRY_EXHAUSTED_PUBLIC_MESSAGE = (
    "模型连续生成的结构化结果未通过校验。请重试本轮操作；"
    "如果多次失败，请补充更明确的需求或阶段确认信息。"
)
PROVIDER_ERROR_PUBLIC_REASONS = {
    "provider_authentication": (
        "模型供应商鉴权失败，请检查 API Key、Base URL、模型名称和供应商权限。"
    ),
    "provider_connection": (
        "模型供应商连接失败，请检查网络、Base URL 或供应商服务状态。"
    ),
    "provider_error": "模型供应商返回错误，本轮生成未完成，右侧产出物已保持不变。",
    "provider_rate_limit": "模型供应商限流或额度不足，请稍后重试或检查供应商额度。",
}
SAFE_TERMINAL_ERROR_CODES = frozenset(ERROR_PUBLIC_REASONS) | {"LLM_ERROR"}
UNKNOWN_OBSERVABILITY_ERROR_CODE = "UNKNOWN_RUNTIME_ERROR"
SAFE_OBSERVABILITY_ERROR_CODES = SAFE_TERMINAL_ERROR_CODES | {
    DEFAULT_LLM_CONFIG_MISSING_CODE,
    UNKNOWN_OBSERVABILITY_ERROR_CODE,
}
SAFE_PROVIDER_VALIDATORS = frozenset(PROVIDER_ERROR_PUBLIC_REASONS)
SAFE_SCHEMA_VALIDATORS = (
    frozenset(
        {
            "artifact_value",
            "blank_string",
            "bool_type",
            "clarify_question_status_literal",
            "dict_type",
            "delivery_case_count_mismatch",
            "delivery_high_risk_count_mismatch",
            "delivery_total_cases_mismatch",
            "enum",
            "extra_forbidden",
            "float_type",
            "idea_converge_blank_elimination_reason",
            "idea_concept_empty_mvp_feature_assumption_ids",
            "idea_concept_empty_next_action_related_ids",
            "idea_concept_empty_validation_assumption_ids",
            "idea_define_duplicate_evidence_id",
            "idea_define_duplicate_problem_id",
            "idea_define_duplicate_root_problem_id",
            "idea_define_empty_evidence_ids",
            "idea_define_missing_fit_root_evidence_reference",
            "idea_define_missing_root_problem_evidence",
            "idea_define_unknown_problem_reference",
            "idea_define_unknown_evidence_reference",
            "int_type",
            "incident_improvement_blank_risk_acceptor",
            "incident_improvement_action_count_mismatch",
            "incident_improvement_action_group_mismatch",
            "incident_improvement_covered_without_actions",
            "incident_improvement_duplicate_action_id",
            "incident_improvement_duplicate_cause_id",
            "incident_improvement_priority_distribution_mismatch",
            "incident_improvement_unknown_action_reference",
            "incident_improvement_unknown_cause_reference",
            "journey_duplicate_opportunity_id",
            "journey_duplicate_pain_id",
            "journey_duplicate_stage_id",
            "journey_unknown_opportunity_reference",
            "journey_unknown_pain_reference",
            "journey_unknown_stage_reference",
            "list_type",
            "literal_error",
            "missing",
            "pydantic_ai_output_retry",
            "pydantic_validation",
            "stage_gate_unchecked",
            "string_too_short",
            "string_type",
            "structured_output",
            "too_short",
            "union_tag_invalid",
            "union_tag_not_found",
            "value_error",
            "workflow_contract",
        }
    )
    | SAFE_RESPONSE_SCHEMA_VALIDATORS
)


class ArtifactVersionConflictError(ValueError):
    def __init__(self, current_artifact: dict | None):
        super().__init__("产出物已被更新，请刷新后再保存")
        self.current_artifact = current_artifact


class TurnPersistenceError(RuntimeError):
    """A completed turn could not be committed as one durable outcome."""


class TurnPersistenceConflictError(TurnPersistenceError):
    """A concurrent turn wrote the same durable sequence or version slot."""


class UnresolvedTurnHistoryError(TurnPersistenceError):
    """A run has nonterminal history that cannot be copied safely."""


class TurnRequestIdentityConflictError(ValueError):
    """A requestId was reused for a different immutable request identity."""


@dataclass(frozen=True)
class TurnRequestClaim:
    state: str
    terminal_event: dict | None = None
    owner_token: str | None = None
    lease_generation: int | None = None
    user_message_sequence: int | None = None


def _validate_workflow_stage(workflow_id: str, stage_id: str) -> None:
    workflow_stages = WORKFLOW_STAGES.get(workflow_id)
    if workflow_stages is None:
        raise ValueError(f"未知 workflowId: {workflow_id}")
    if stage_id not in workflow_stages:
        raise ValueError(f"workflowId 与 stageId 不匹配: {workflow_id}/{stage_id}")


def _get_run(run_id: str) -> AgentRun:
    run = db.session.get(AgentRun, run_id)
    if run is None:
        raise ValueError(f"未知 runId: {run_id}")
    return run


def _next_message_sequence(run_id: str) -> int:
    current_max = (
        db.session.query(db.func.max(AgentMessage.sequence_index))
        .filter_by(run_id=run_id)
        .scalar()
    )
    return (current_max or 0) + 1


def _last_assistant_sequence(run_id: str) -> int:
    current_max = (
        db.session.query(db.func.max(AgentMessage.sequence_index))
        .filter_by(run_id=run_id, role="assistant")
        .scalar()
    )
    return current_max or 0


def _current_stage_artifact_version(run_id: str, stage_id: str) -> int:
    artifact = AgentArtifact.query.filter_by(
        run_id=run_id,
        stage_id=stage_id,
    ).one_or_none()
    if artifact is None or artifact.current_version_id is None:
        return 0
    version = db.session.get(AgentArtifactVersion, artifact.current_version_id)
    if version is None:
        raise TurnPersistenceConflictError(
            "Current artifact version could not be resolved."
        )
    return version.version_number


def _next_artifact_version(artifact_id: int) -> int:
    current_max = (
        db.session.query(db.func.max(AgentArtifactVersion.version_number))
        .filter_by(artifact_id=artifact_id)
        .scalar()
    )
    return (current_max or 0) + 1


def create_agent_run(
    workflow_id: str,
    agent_id: str,
    current_stage_id: str,
    *,
    model: str | None = None,
    status: str = "active",
    run_id: str | None = None,
    _commit: bool = True,
) -> AgentRun:
    _validate_workflow_stage(workflow_id, current_stage_id)
    if status not in RUN_STATUSES:
        raise ValueError(f"未知 run status: {status}")

    run = AgentRun(
        id=run_id or str(uuid4()),
        workflow_id=workflow_id,
        agent_id=agent_id,
        current_stage_id=current_stage_id,
        status=status,
        model=model,
    )
    db.session.add(run)
    if _commit:
        db.session.commit()
    else:
        db.session.flush()
    return run


def ensure_agent_run(
    workflow_id: str,
    agent_id: str,
    current_stage_id: str,
    *,
    run_id: str | None = None,
    model: str | None = None,
) -> AgentRun:
    _validate_workflow_stage(workflow_id, current_stage_id)
    if run_id is None:
        return create_agent_run(
            workflow_id,
            agent_id,
            current_stage_id,
            model=model,
        )

    run = db.session.get(AgentRun, run_id)
    if run is None:
        try:
            return create_agent_run(
                workflow_id,
                agent_id,
                current_stage_id,
                model=model,
                run_id=run_id,
            )
        except IntegrityError:
            db.session.rollback()
            run = _get_run(run_id)
    if run.workflow_id != workflow_id:
        raise ValueError(f"runId 与 workflowId 不匹配: {run_id}/{workflow_id}")
    if run.agent_id != agent_id:
        raise ValueError(f"runId 与 agentId 不匹配: {run_id}/{agent_id}")

    return run


def _resolve_clone_bound_user_message(
    turn_request: AgentRunTurnRequest,
    identity: dict,
) -> AgentMessage:
    source = _get_run(turn_request.run_id)
    workflow_stages = WORKFLOW_STAGES.get(source.workflow_id)
    if (
        turn_request.stage_id != identity["stageId"]
        or workflow_stages is None
        or identity["stageId"] not in workflow_stages
    ):
        raise UnresolvedTurnHistoryError(
            "Unable to clone a run with unresolved turn requests."
        )
    message = AgentMessage.query.filter_by(
        run_id=turn_request.run_id,
        role="user",
        sequence_index=identity["userMessageSequence"],
    ).one_or_none()
    if message is None or identity["promptFingerprint"] != _prompt_fingerprint(
        message.content
    ):
        raise UnresolvedTurnHistoryError(
            "Unable to clone a run with unresolved turn requests."
        )
    return message


def _resolve_failed_turn_assistant_sequence(
    turn_request: AgentRunTurnRequest,
    identity: dict,
    *,
    workflow_id: str,
) -> int:
    expected_content, _diagnostic = _failed_turn_message_projection(
        _sanitize_failed_terminal_event(
            _stored_turn_request_terminal_event(turn_request),
            workflow_id=workflow_id,
            stage_id=turn_request.stage_id,
        )
    )
    assistant_sequence = identity["userMessageSequence"] + 1
    assistant = AgentMessage.query.filter_by(
        run_id=turn_request.run_id,
        role="assistant",
        sequence_index=assistant_sequence,
    ).one_or_none()
    if assistant is None or assistant.content != expected_content:
        raise UnresolvedTurnHistoryError(
            "Unable to clone a run with unresolved turn requests."
        )
    return assistant_sequence


def _resolve_clone_excluded_message_sequences(run_id: str) -> set[int]:
    source = _get_run(run_id)
    nonreusable_requests = (
        AgentRunTurnRequest.query.filter(
            AgentRunTurnRequest.run_id == run_id,
            AgentRunTurnRequest.status.in_(("active", "abandoned", "failed")),
        )
        .with_for_update()
        .all()
    )
    excluded_sequences: set[int] = set()
    for turn_request in nonreusable_requests:
        identity = _stored_turn_request_identity(turn_request)
        if turn_request.status == "active" or identity is None:
            raise UnresolvedTurnHistoryError(
                "Unable to clone a run with unresolved turn requests."
            )
        user_message = _resolve_clone_bound_user_message(turn_request, identity)
        excluded_sequences.add(user_message.sequence_index)
        if turn_request.status == "failed":
            excluded_sequences.add(
                _resolve_failed_turn_assistant_sequence(
                    turn_request,
                    identity,
                    workflow_id=source.workflow_id,
                )
            )
    return excluded_sequences


def _rebuild_clone_user_supplements_for_failed_stage(
    source_run_id: str,
    cloned_run_id: str,
    stage_id: str,
) -> bool:
    failed_request_exists = (
        AgentRunTurnRequest.query.filter_by(
            run_id=source_run_id,
            stage_id=stage_id,
            status="failed",
        ).first()
        is not None
    )
    if not failed_request_exists:
        return False

    completed_messages: list[AgentMessage] = []
    completed_requests = AgentRunTurnRequest.query.filter_by(
        run_id=source_run_id,
        stage_id=stage_id,
        status="completed",
    ).all()
    for turn_request in completed_requests:
        identity = _stored_turn_request_identity(turn_request)
        if identity is None:
            continue
        completed_messages.append(
            _resolve_clone_bound_user_message(turn_request, identity)
        )
    seen_sequences: set[int] = set()
    for message in sorted(
        completed_messages,
        key=lambda candidate: candidate.sequence_index,
    ):
        if message.sequence_index in seen_sequences:
            continue
        seen_sequences.add(message.sequence_index)
        _append_user_supplement_summary(cloned_run_id, stage_id, message.content)
    return True


def clone_agent_run(source_run_id: str) -> AgentRun:
    storage_failed = False
    try:
        transaction = (
            db.session.begin_nested()
            if db.session().in_transaction()
            else db.session.begin()
        )
        with transaction:
            source = _get_run(source_run_id)
            _lock_agent_run_turn_slot(source.id)
            excluded_message_sequences = _resolve_clone_excluded_message_sequences(
                source.id
            )
            cloned = create_agent_run(
                source.workflow_id,
                source.agent_id,
                source.current_stage_id,
                model=source.model,
                status="active",
                _commit=False,
            )
            # Recheck after allocating the clone so any in-transaction interleaving
            # still rolls back without copying an unresolved user message.
            excluded_message_sequences.update(
                _resolve_clone_excluded_message_sequences(source.id)
            )

            source_messages = (
                AgentMessage.query.filter(
                    AgentMessage.run_id == source.id,
                    AgentMessage.sequence_index.notin_(excluded_message_sequences),
                )
                .order_by(AgentMessage.sequence_index.asc())
                .all()
            )
            for message in source_messages:
                db.session.add(
                    AgentMessage(
                        run_id=cloned.id,
                        role=message.role,
                        content=message.content,
                        sequence_index=message.sequence_index,
                    )
                )

            source_artifacts = (
                AgentArtifact.query.filter_by(run_id=source.id)
                .order_by(AgentArtifact.id.asc())
                .all()
            )
            for artifact in source_artifacts:
                artifact_snapshot = _artifact_snapshot(artifact)
                record_artifact_version(
                    cloned.id,
                    artifact_snapshot["stageId"],
                    artifact_snapshot["content"],
                    artifact_data=artifact_snapshot["artifactData"],
                    _commit=False,
                )

            source_summaries = (
                AgentContextSummary.query.filter_by(run_id=source.id)
                .order_by(AgentContextSummary.id.asc())
                .all()
            )
            for summary in source_summaries:
                if (
                    summary.source_type == SUMMARY_SOURCE_USER_INPUT
                    and summary.summary_type == USER_SUPPLEMENT_SUMMARY_TYPE
                    and _rebuild_clone_user_supplements_for_failed_stage(
                        source.id,
                        cloned.id,
                        summary.source_stage_id,
                    )
                ):
                    continue
                _upsert_context_summary(
                    cloned.id,
                    source_type=summary.source_type,
                    source_stage_id=summary.source_stage_id,
                    summary_type=summary.summary_type,
                    content=summary.content,
                )
        if db.session().in_transaction():
            db.session.commit()
        return cloned
    except UnresolvedTurnHistoryError:
        db.session.rollback()
        raise
    except SQLAlchemyError:
        db.session.rollback()
        storage_failed = True
    if storage_failed:
        raise TurnPersistenceError("Unable to clone the agent run.")


class AgentRunPersistence:
    def ensure_run(self, agent_request, *, model_name: str) -> str:
        try:
            agent_id = get_workflow_agent_id(agent_request.workflow_id)
            run = ensure_agent_run(
                agent_request.workflow_id,
                agent_id,
                agent_request.stage_id,
                run_id=agent_request.run_id,
                model=model_name,
            )
            return run.id
        except SQLAlchemyError:
            db.session.rollback()
        raise TurnPersistenceError("Unable to ensure the agent run.") from None

    def claim_turn_request(
        self,
        run_id: str,
        agent_request,
        *,
        model_name: str,
    ) -> TurnRequestClaim:
        try:
            return claim_agent_run_turn_request(
                run_id,
                request_id=agent_request.request_id,
                stage_id=agent_request.stage_id,
                user_content=agent_request.prompt,
                system_prompt=agent_request.system_prompt,
                model_name=model_name,
            )
        except SQLAlchemyError:
            db.session.rollback()
        raise TurnPersistenceError("Unable to claim the agent turn request.") from None

    def fail_turn_request(
        self,
        run_id: str,
        *,
        request_id: str,
        owner_token: str,
        terminal_event: dict,
    ) -> None:
        fail_agent_run_turn_request(
            run_id,
            request_id=request_id,
            owner_token=owner_token,
            terminal_event=terminal_event,
        )

    def abandon_turn_request(
        self,
        run_id: str,
        *,
        request_id: str,
        owner_token: str,
    ) -> None:
        abandon_agent_run_turn_request(
            run_id,
            request_id=request_id,
            owner_token=owner_token,
        )

    def build_runtime_context(
        self,
        run_id: str,
        current_prompt: str,
        *,
        request_id: str,
    ):
        from context_builder import build_run_context

        storage_failed = False
        try:
            excluded_sequences = set()
            context_omitted_requests = AgentRunTurnRequest.query.filter(
                AgentRunTurnRequest.run_id == run_id,
                AgentRunTurnRequest.status.in_(("active", "abandoned", "failed")),
            ).all()
            for turn_request in context_omitted_requests:
                identity = _stored_turn_request_identity(turn_request)
                if identity is None:
                    raise TurnPersistenceError(
                        "Unable to resolve durable runtime context."
                    )
                excluded_sequences.add(identity["userMessageSequence"])
            context = build_run_context(
                run_id,
                current_prompt,
                exclude_message_sequences=excluded_sequences,
            )
            warnings = list(context.warnings)
            return context.prompt, warnings
        except TurnPersistenceError:
            raise
        except (SQLAlchemyError, LookupError, TypeError, ValueError):
            db.session.rollback()
            storage_failed = True
        if storage_failed:
            raise TurnPersistenceError("Unable to build durable runtime context.")

    def complete_agent_run_turn(
        self,
        run_id: str,
        *,
        stage_id: str,
        assistant_content: str,
        artifact_content: str | None,
        artifact_data: dict | None,
        request_id: str | None,
        owner_token: str | None,
        terminal_event: dict | None,
        metric: dict,
    ) -> None:
        complete_agent_run_turn(
            run_id,
            stage_id=stage_id,
            assistant_content=assistant_content,
            artifact_content=artifact_content,
            artifact_data=artifact_data,
            request_id=request_id,
            owner_token=owner_token,
            terminal_event=terminal_event,
            metric=metric,
        )

    def record_turn_metric(self, **kwargs) -> None:
        record_turn_metric(**kwargs)


def append_run_message(
    run_id: str,
    role: str,
    content: str,
    *,
    _commit: bool = True,
    _summarize_user: bool = True,
) -> AgentMessage:
    run = _get_run(run_id)
    if role not in MESSAGE_ROLES:
        raise ValueError(f"未知 message role: {role}")

    message = AgentMessage(
        run_id=run_id,
        role=role,
        content=content,
        sequence_index=_next_message_sequence(run_id),
    )
    db.session.add(message)
    if role == "user" and _summarize_user:
        _append_user_supplement_summary(run_id, run.current_stage_id, content)
    if _commit:
        db.session.commit()
    return message


def _prompt_fingerprint(user_content: str) -> str:
    return "sha256-" + hashlib.sha256(user_content.encode("utf-8")).hexdigest()


def _turn_request_payload(
    *,
    stage_id: str,
    prompt_fingerprint: str,
    system_prompt_fingerprint: str,
    model_name: str,
    user_message_sequence: int,
    baseline_assistant_sequence: int,
    baseline_artifact_version: int,
    owner_token: str,
    lease_generation: int,
    terminal_event: dict | None,
) -> dict:
    return {
        TURN_REQUEST_IDENTITY_KEY: {
            "stageId": stage_id,
            "promptFingerprint": prompt_fingerprint,
            "systemPromptFingerprint": system_prompt_fingerprint,
            "modelName": model_name,
            "userMessageSequence": user_message_sequence,
            "baselineAssistantSequence": baseline_assistant_sequence,
            "baselineArtifactVersion": baseline_artifact_version,
        },
        TURN_REQUEST_OWNER_KEY: {
            "ownerToken": owner_token,
            "generation": lease_generation,
        },
        TURN_REQUEST_TERMINAL_EVENT_KEY: terminal_event,
    }


def _stored_turn_request_identity(turn_request: AgentRunTurnRequest) -> dict | None:
    payload = turn_request.terminal_event
    if not isinstance(payload, dict):
        return None
    identity = payload.get(TURN_REQUEST_IDENTITY_KEY)
    if not isinstance(identity, dict):
        return None
    stage_id = identity.get("stageId")
    prompt_fingerprint = identity.get("promptFingerprint")
    system_prompt_fingerprint = identity.get("systemPromptFingerprint")
    model_name = identity.get("modelName")
    user_message_sequence = identity.get("userMessageSequence")
    baseline_assistant_sequence = identity.get("baselineAssistantSequence")
    baseline_artifact_version = identity.get("baselineArtifactVersion")
    if (
        not isinstance(stage_id, str)
        or not isinstance(prompt_fingerprint, str)
        or not isinstance(system_prompt_fingerprint, str)
        or not isinstance(model_name, str)
        or not isinstance(user_message_sequence, int)
        or isinstance(user_message_sequence, bool)
        or user_message_sequence < 1
        or not isinstance(baseline_assistant_sequence, int)
        or isinstance(baseline_assistant_sequence, bool)
        or baseline_assistant_sequence < 0
        or not isinstance(baseline_artifact_version, int)
        or isinstance(baseline_artifact_version, bool)
        or baseline_artifact_version < 0
    ):
        return None
    return {
        "stageId": stage_id,
        "promptFingerprint": prompt_fingerprint,
        "systemPromptFingerprint": system_prompt_fingerprint,
        "modelName": model_name,
        "userMessageSequence": user_message_sequence,
        "baselineAssistantSequence": baseline_assistant_sequence,
        "baselineArtifactVersion": baseline_artifact_version,
    }


def _stored_turn_request_owner(turn_request: AgentRunTurnRequest) -> dict | None:
    payload = turn_request.terminal_event
    if not isinstance(payload, dict):
        return None
    owner = payload.get(TURN_REQUEST_OWNER_KEY)
    if not isinstance(owner, dict):
        return None
    owner_token = owner.get("ownerToken")
    generation = owner.get("generation")
    if (
        not isinstance(owner_token, str)
        or not owner_token
        or not isinstance(generation, int)
        or isinstance(generation, bool)
        or generation < 1
    ):
        return None
    return {"ownerToken": owner_token, "generation": generation}


def _stored_turn_request_terminal_event(
    turn_request: AgentRunTurnRequest,
) -> dict | None:
    payload = turn_request.terminal_event
    if _stored_turn_request_identity(turn_request) is None:
        return payload if isinstance(payload, dict) else None
    terminal_event = payload.get(TURN_REQUEST_TERMINAL_EVENT_KEY)
    return terminal_event if isinstance(terminal_event, dict) else None


def _snapshot_pending_stage_transition(run: AgentRun) -> dict[str, str] | None:
    """Project only the durable, immediate transition requested by the latest turn."""
    stages = WORKFLOW_STAGES.get(run.workflow_id)
    if stages is None or run.current_stage_id not in stages:
        return None
    stage_index = stages.index(run.current_stage_id)
    if stage_index + 1 >= len(stages):
        return None

    latest_request = (
        AgentRunTurnRequest.query.filter_by(
            run_id=run.id,
            stage_id=run.current_stage_id,
        )
        .order_by(AgentRunTurnRequest.id.desc())
        .first()
    )
    if latest_request is None or latest_request.status != "completed":
        return None
    terminal_event = _stored_turn_request_terminal_event(latest_request)
    output = terminal_event.get("output") if isinstance(terminal_event, dict) else None
    stage_action = output.get("stage_action") if isinstance(output, dict) else None
    target_stage_id = (
        stage_action.get("target_stage_id")
        if isinstance(stage_action, dict)
        and stage_action.get("type") == "request_next_stage"
        else None
    )
    expected_target_stage_id = stages[stage_index + 1]
    if target_stage_id != expected_target_stage_id:
        return None
    return {
        "fromStageId": run.current_stage_id,
        "targetStageId": target_stage_id,
    }


def _bind_turn_request_identity(
    turn_request: AgentRunTurnRequest,
    *,
    stage_id: str,
    user_content: str,
    system_prompt: str,
    model_name: str,
    user_message_sequence: int,
    baseline_assistant_sequence: int,
    baseline_artifact_version: int,
    terminal_event: dict | None = None,
) -> str:
    owner_token = str(uuid4())
    turn_request.terminal_event = _turn_request_payload(
        stage_id=stage_id,
        prompt_fingerprint=_prompt_fingerprint(user_content),
        system_prompt_fingerprint=_prompt_fingerprint(system_prompt),
        model_name=model_name,
        user_message_sequence=user_message_sequence,
        baseline_assistant_sequence=baseline_assistant_sequence,
        baseline_artifact_version=baseline_artifact_version,
        owner_token=owner_token,
        lease_generation=1,
        terminal_event=terminal_event,
    )
    return owner_token


def _replace_turn_request_terminal_event(
    turn_request: AgentRunTurnRequest,
    terminal_event: dict | None,
) -> None:
    identity = _stored_turn_request_identity(turn_request)
    owner = _stored_turn_request_owner(turn_request)
    if identity is None or owner is None:
        raise TurnRequestIdentityConflictError("requestId identity conflict")
    turn_request.terminal_event = _turn_request_payload(
        stage_id=identity["stageId"],
        prompt_fingerprint=identity["promptFingerprint"],
        system_prompt_fingerprint=identity["systemPromptFingerprint"],
        model_name=identity["modelName"],
        user_message_sequence=identity["userMessageSequence"],
        baseline_assistant_sequence=identity["baselineAssistantSequence"],
        baseline_artifact_version=identity["baselineArtifactVersion"],
        owner_token=owner["ownerToken"],
        lease_generation=owner["generation"],
        terminal_event=terminal_event,
    )


def _transition_owned_turn_request(
    turn_request: AgentRunTurnRequest,
    *,
    owner_token: str,
    next_status: str,
    terminal_event: dict | None,
) -> None:
    identity = _stored_turn_request_identity(turn_request)
    owner = _stored_turn_request_owner(turn_request)
    if (
        turn_request.status != "active"
        or identity is None
        or owner is None
        or not isinstance(owner_token, str)
        or not hmac.compare_digest(owner["ownerToken"], owner_token)
    ):
        raise TurnPersistenceConflictError("Turn request ownership was superseded.")
    expected_payload = turn_request.terminal_event_json
    next_payload = json.dumps(
        _turn_request_payload(
            stage_id=identity["stageId"],
            prompt_fingerprint=identity["promptFingerprint"],
            system_prompt_fingerprint=identity["systemPromptFingerprint"],
            model_name=identity["modelName"],
            user_message_sequence=identity["userMessageSequence"],
            baseline_assistant_sequence=identity["baselineAssistantSequence"],
            baseline_artifact_version=identity["baselineArtifactVersion"],
            owner_token=owner["ownerToken"],
            lease_generation=owner["generation"],
            terminal_event=terminal_event,
        ),
        ensure_ascii=False,
    )
    updated = (
        db.session.query(AgentRunTurnRequest)
        .filter(
            AgentRunTurnRequest.id == turn_request.id,
            AgentRunTurnRequest.status == "active",
            AgentRunTurnRequest.terminal_event_json == expected_payload,
        )
        .update(
            {
                AgentRunTurnRequest.status: next_status,
                AgentRunTurnRequest.terminal_event_json: next_payload,
                AgentRunTurnRequest.updated_at: _utcnow_naive(),
            },
            synchronize_session=False,
        )
    )
    if updated != 1:
        db.session.expire(turn_request)
        raise TurnPersistenceConflictError("Turn request ownership was superseded.")
    db.session.expire(turn_request)


def _rotated_turn_request_owner_payload(
    turn_request: AgentRunTurnRequest,
) -> tuple[str, str]:
    identity = _stored_turn_request_identity(turn_request)
    owner = _stored_turn_request_owner(turn_request)
    if identity is None or owner is None:
        raise TurnRequestIdentityConflictError("requestId identity conflict")
    owner_token = str(uuid4())
    baseline_assistant_sequence = _last_assistant_sequence(turn_request.run_id)
    baseline_artifact_version = _current_stage_artifact_version(
        turn_request.run_id,
        identity["stageId"],
    )
    terminal_event_json = json.dumps(
        _turn_request_payload(
            stage_id=identity["stageId"],
            prompt_fingerprint=identity["promptFingerprint"],
            system_prompt_fingerprint=identity["systemPromptFingerprint"],
            model_name=identity["modelName"],
            user_message_sequence=identity["userMessageSequence"],
            baseline_assistant_sequence=baseline_assistant_sequence,
            baseline_artifact_version=baseline_artifact_version,
            owner_token=owner_token,
            lease_generation=owner["generation"] + 1,
            terminal_event=None,
        ),
        ensure_ascii=False,
    )
    return owner_token, terminal_event_json


def _reclaim_abandoned_turn_request(
    turn_request: AgentRunTurnRequest,
) -> str | None:
    """Atomically grant one retry ownership of an abandoned request."""
    owner_token, terminal_event_json = _rotated_turn_request_owner_payload(turn_request)
    updated = (
        db.session.query(AgentRunTurnRequest)
        .filter(
            AgentRunTurnRequest.id == turn_request.id,
            AgentRunTurnRequest.status == "abandoned",
        )
        .update(
            {
                AgentRunTurnRequest.status: "active",
                AgentRunTurnRequest.terminal_event_json: terminal_event_json,
                AgentRunTurnRequest.updated_at: _utcnow_naive(),
            },
            synchronize_session=False,
        )
    )
    if updated == 1:
        db.session.expire(turn_request)
        return owner_token
    return None


def _utcnow_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _abandon_expired_active_turn_requests(
    run_id: str,
    *,
    exclude_request_id: str,
) -> int:
    """Fence expired owners before another request competes for the run slot."""
    now = _utcnow_naive()
    cutoff = now - timedelta(seconds=TURN_REQUEST_ACTIVE_LEASE_SECONDS)
    lease_timestamp = db.func.coalesce(
        AgentRunTurnRequest.updated_at,
        AgentRunTurnRequest.created_at,
    )
    return (
        db.session.query(AgentRunTurnRequest)
        .filter(
            AgentRunTurnRequest.run_id == run_id,
            AgentRunTurnRequest.request_id != exclude_request_id,
            AgentRunTurnRequest.status == "active",
            or_(lease_timestamp <= cutoff, lease_timestamp.is_(None)),
        )
        .update(
            {
                AgentRunTurnRequest.status: "abandoned",
                AgentRunTurnRequest.updated_at: now,
            },
            synchronize_session=False,
        )
    )


def _lock_agent_run_turn_slot(run_id: str) -> None:
    """Acquire the shared source-row mutex used by claims and run cloning."""
    updated = (
        db.session.query(AgentRun)
        .filter(AgentRun.id == run_id)
        .update(
            {AgentRun.updated_at: _utcnow_naive()},
            synchronize_session=False,
        )
    )
    if updated != 1:
        raise TurnPersistenceError("Unable to lock the agent run turn slot.")
    db.session.flush()


def _claim_run_turn_slot(run_id: str, *, request_id: str) -> bool:
    """Atomically reserve the single active turn slot for one run."""
    _lock_agent_run_turn_slot(run_id)
    _abandon_expired_active_turn_requests(
        run_id,
        exclude_request_id=request_id,
    )
    active_other_request = (
        AgentRunTurnRequest.query.filter(
            AgentRunTurnRequest.run_id == run_id,
            AgentRunTurnRequest.request_id != request_id,
            AgentRunTurnRequest.status == "active",
        )
        .with_for_update()
        .first()
    )
    return active_other_request is None


def _turn_request_lease_expired(
    turn_request: AgentRunTurnRequest,
    *,
    now: datetime | None = None,
) -> bool:
    timestamp = turn_request.updated_at or turn_request.created_at
    if timestamp is None:
        return True
    if timestamp.tzinfo is not None:
        timestamp = timestamp.astimezone(timezone.utc).replace(tzinfo=None)
    current = now or _utcnow_naive()
    return timestamp <= current - timedelta(seconds=TURN_REQUEST_ACTIVE_LEASE_SECONDS)


def _reclaim_expired_active_turn_request(
    turn_request: AgentRunTurnRequest,
) -> str | None:
    """Atomically renew one expired active request lease for an exact retry."""
    now = _utcnow_naive()
    if not _turn_request_lease_expired(turn_request, now=now):
        return None
    owner_token, terminal_event_json = _rotated_turn_request_owner_payload(turn_request)
    cutoff = now - timedelta(seconds=TURN_REQUEST_ACTIVE_LEASE_SECONDS)
    lease_timestamp = db.func.coalesce(
        AgentRunTurnRequest.updated_at,
        AgentRunTurnRequest.created_at,
    )
    updated = (
        db.session.query(AgentRunTurnRequest)
        .filter(
            AgentRunTurnRequest.id == turn_request.id,
            AgentRunTurnRequest.status == "active",
            or_(lease_timestamp <= cutoff, lease_timestamp.is_(None)),
        )
        .update(
            {
                AgentRunTurnRequest.terminal_event_json: terminal_event_json,
                AgentRunTurnRequest.updated_at: now,
            },
            synchronize_session=False,
        )
    )
    if updated == 1:
        db.session.expire(turn_request)
        return owner_token
    return None


def _validate_turn_request_identity(
    turn_request: AgentRunTurnRequest,
    *,
    stage_id: str,
    user_content: str,
    system_prompt: str,
    model_name: str,
) -> None:
    identity = _stored_turn_request_identity(turn_request)
    if identity is None:
        raise TurnRequestIdentityConflictError("requestId identity conflict")
    if (
        identity["stageId"] != stage_id
        or not hmac.compare_digest(
            identity["promptFingerprint"],
            _prompt_fingerprint(user_content),
        )
        or not hmac.compare_digest(
            identity["systemPromptFingerprint"],
            _prompt_fingerprint(system_prompt),
        )
        or not hmac.compare_digest(identity["modelName"], model_name)
    ):
        raise TurnRequestIdentityConflictError("requestId identity conflict")


def _turn_request_claim(turn_request: AgentRunTurnRequest) -> TurnRequestClaim:
    identity = _stored_turn_request_identity(turn_request)
    return TurnRequestClaim(
        state=turn_request.status,
        terminal_event=_stored_turn_request_terminal_event(turn_request),
        user_message_sequence=(
            identity["userMessageSequence"] if identity is not None else None
        ),
    )


def _owned_turn_request_claim(
    turn_request: AgentRunTurnRequest,
    owner_token: str,
) -> TurnRequestClaim:
    identity = _stored_turn_request_identity(turn_request)
    owner = _stored_turn_request_owner(turn_request)
    if (
        identity is None
        or owner is None
        or not hmac.compare_digest(owner["ownerToken"], owner_token)
    ):
        raise TurnRequestIdentityConflictError("requestId identity conflict")
    return TurnRequestClaim(
        state="new",
        owner_token=owner_token,
        lease_generation=owner["generation"],
        user_message_sequence=identity["userMessageSequence"],
    )


def _sanitize_failed_terminal_event(
    value: object,
    *,
    workflow_id: str,
    stage_id: str,
) -> dict:
    stored_code = value.get("code") if isinstance(value, dict) else None
    code = (
        stored_code
        if isinstance(stored_code, str) and stored_code in SAFE_TERMINAL_ERROR_CODES
        else "LLM_ERROR"
    )
    stored_diagnostic = value.get("diagnostic") if isinstance(value, dict) else None
    if code == "LLM_ERROR":
        stored_validator = (
            stored_diagnostic.get("validator")
            if isinstance(stored_diagnostic, dict)
            else None
        )
        validator = (
            stored_validator
            if isinstance(stored_validator, str)
            and stored_validator in SAFE_PROVIDER_VALIDATORS
            else "provider_error"
        )
        public_reason = PROVIDER_ERROR_PUBLIC_REASONS[validator]
        phase = "provider"
        field_path = "provider"
        retryable = validator != "provider_authentication"
    else:
        public_reason = ERROR_PUBLIC_REASONS[code]
        profiles = {
            "AGENT_RUNTIME_UNAVAILABLE": (
                "runtime",
                "runtime",
                "runtime_dependency",
                False,
            ),
            "CONTRACT_VALIDATION_FAILED": (
                "contract_validation",
                "artifact_contract",
                "workflow_contract",
                False,
            ),
            "PERSISTENCE_CONFLICT": (
                "persistence",
                "run_outcome",
                "unique_sequence_or_version",
                True,
            ),
            "PERSISTENCE_FAILED": (
                "persistence",
                "run_outcome",
                "atomic_commit",
                True,
            ),
            "REQUEST_IN_PROGRESS": (
                "persistence",
                "request_id",
                "idempotency_lease",
                True,
            ),
            "REQUEST_IDENTITY_CONFLICT": (
                "persistence",
                "request_id",
                "immutable_request_identity",
                False,
            ),
            "REQUEST_VALIDATION_FAILED": (
                "request_validation",
                "request",
                "request_schema",
                False,
            ),
            "SCHEMA_VALIDATION_FAILED": (
                "structured_output",
                "artifact_data",
                "structured_output",
                True,
            ),
            "VISUAL_VALIDATION_FAILED": (
                "visual_validation",
                "artifact_update.markdown",
                "artifact_visual",
                False,
            ),
        }
        phase, field_path, validator, retryable = profiles[code]
    if code == "SCHEMA_VALIDATION_FAILED":
        stored_validator = (
            stored_diagnostic.get("validator")
            if isinstance(stored_diagnostic, dict)
            else None
        )
        validator = (
            stored_validator
            if isinstance(stored_validator, str)
            and stored_validator in SAFE_SCHEMA_VALIDATORS
            else "structured_output"
        )
        field_path = project_safe_schema_field_path(validator)

    stored_message = value.get("message") if isinstance(value, dict) else None
    if (
        code == "SCHEMA_VALIDATION_FAILED"
        and stored_message == SCHEMA_RETRY_EXHAUSTED_PUBLIC_MESSAGE
        and validator == "pydantic_ai_output_retry"
    ):
        message = SCHEMA_RETRY_EXHAUSTED_PUBLIC_MESSAGE
    else:
        message = public_reason

    diagnostic = {
        "phase": phase,
        "workflowId": workflow_id,
        "stageId": stage_id,
        "fieldPath": field_path,
        "validator": validator,
        "retryable": retryable,
        "publicReason": public_reason,
    }
    return {
        "type": "error",
        "code": code,
        "message": message,
        "diagnostic": diagnostic,
    }


def _failed_turn_message_projection(terminal_event: dict) -> tuple[str, dict]:
    code = terminal_event["code"]
    diagnostic = terminal_event["diagnostic"]
    if code == "LLM_ERROR":
        kind = "provider"
        summary = "模型调用未完成"
    elif code in {
        "CONTRACT_VALIDATION_FAILED",
        "SCHEMA_VALIDATION_FAILED",
        "VISUAL_VALIDATION_FAILED",
    }:
        kind = "structured"
        summary = "结构化输出生成失败"
    else:
        kind = "generic"
        summary = "本轮生成失败"

    content = f"⚠️ **{summary}**\n\n{diagnostic['publicReason']}"
    error_diagnostic = {
        "kind": kind,
        "summary": summary,
        "rawMessage": terminal_event["message"],
        "code": code,
        "phase": diagnostic["phase"],
        "workflowId": diagnostic["workflowId"],
        "stageId": diagnostic["stageId"],
        "fieldPath": diagnostic["fieldPath"],
        "validator": diagnostic["validator"],
        "retryable": diagnostic["retryable"],
    }
    return content, error_diagnostic


def claim_agent_run_turn_request(
    run_id: str,
    *,
    request_id: str,
    stage_id: str,
    user_content: str,
    system_prompt: str = "",
    model_name: str | None = None,
) -> TurnRequestClaim:
    if not request_id.strip():
        raise ValueError("requestId 不能为空")
    if not user_content.strip():
        raise ValueError("user content 不能为空")

    try:
        transaction = (
            db.session.begin_nested()
            if db.session().in_transaction()
            else db.session.begin()
        )
        canonical_model_name = model_name or ""
        existing_claim: TurnRequestClaim | None = None
        new_claim: TurnRequestClaim | None = None
        identity_conflict = False
        with transaction:
            run = _get_run(run_id)
            _validate_workflow_stage(run.workflow_id, stage_id)
            existing = AgentRunTurnRequest.query.filter_by(
                run_id=run_id,
                request_id=request_id,
            ).one_or_none()
            if existing is not None:
                if _stored_turn_request_identity(existing) is None:
                    if existing.status == "failed":
                        existing.terminal_event = _sanitize_failed_terminal_event(
                            _stored_turn_request_terminal_event(existing),
                            workflow_id=run.workflow_id,
                            stage_id=existing.stage_id,
                        )
                    identity_conflict = True
                else:
                    _validate_turn_request_identity(
                        existing,
                        stage_id=stage_id,
                        user_content=user_content,
                        system_prompt=system_prompt,
                        model_name=canonical_model_name,
                    )
                    if existing.status == "abandoned":
                        if not _claim_run_turn_slot(
                            run_id,
                            request_id=request_id,
                        ):
                            existing_claim = TurnRequestClaim(state="active")
                        else:
                            owner_token = _reclaim_abandoned_turn_request(existing)
                            if owner_token is not None:
                                run.current_stage_id = stage_id
                                if model_name is not None:
                                    run.model = model_name
                                existing_claim = _owned_turn_request_claim(
                                    existing,
                                    owner_token,
                                )
                            else:
                                db.session.expire(existing)
                                db.session.refresh(existing)
                                _validate_turn_request_identity(
                                    existing,
                                    stage_id=stage_id,
                                    user_content=user_content,
                                    system_prompt=system_prompt,
                                    model_name=canonical_model_name,
                                )
                                existing_claim = _turn_request_claim(existing)
                    elif existing.status == "active" and _turn_request_lease_expired(
                        existing
                    ):
                        if not _claim_run_turn_slot(
                            run_id,
                            request_id=request_id,
                        ):
                            existing_claim = TurnRequestClaim(state="active")
                        else:
                            owner_token = _reclaim_expired_active_turn_request(existing)
                            if owner_token is not None:
                                run.current_stage_id = stage_id
                                if model_name is not None:
                                    run.model = model_name
                                existing_claim = _owned_turn_request_claim(
                                    existing,
                                    owner_token,
                                )
                            else:
                                db.session.expire(existing)
                                db.session.refresh(existing)
                                _validate_turn_request_identity(
                                    existing,
                                    stage_id=stage_id,
                                    user_content=user_content,
                                    system_prompt=system_prompt,
                                    model_name=canonical_model_name,
                                )
                                existing_claim = _turn_request_claim(existing)
                    elif existing.status == "failed":
                        _replace_turn_request_terminal_event(
                            existing,
                            _sanitize_failed_terminal_event(
                                _stored_turn_request_terminal_event(existing),
                                workflow_id=run.workflow_id,
                                stage_id=existing.stage_id,
                            ),
                        )
                        existing_claim = _turn_request_claim(existing)
                    else:
                        existing_claim = _turn_request_claim(existing)
            else:
                if not _claim_run_turn_slot(
                    run_id,
                    request_id=request_id,
                ):
                    existing_claim = TurnRequestClaim(state="active")
                else:
                    turn_request = AgentRunTurnRequest(
                        run_id=run_id,
                        request_id=request_id,
                        stage_id=stage_id,
                        status="new",
                    )
                    db.session.add(turn_request)
                    run.current_stage_id = stage_id
                    if model_name is not None:
                        run.model = model_name
                    baseline_assistant_sequence = _last_assistant_sequence(run_id)
                    baseline_artifact_version = _current_stage_artifact_version(
                        run_id,
                        stage_id,
                    )
                    user_message = append_run_message(
                        run_id,
                        "user",
                        user_content,
                        _commit=False,
                        _summarize_user=False,
                    )
                    owner_token = _bind_turn_request_identity(
                        turn_request,
                        stage_id=stage_id,
                        user_content=user_content,
                        system_prompt=system_prompt,
                        model_name=canonical_model_name,
                        user_message_sequence=user_message.sequence_index,
                        baseline_assistant_sequence=baseline_assistant_sequence,
                        baseline_artifact_version=baseline_artifact_version,
                    )
                    turn_request.status = "active"
                    new_claim = _owned_turn_request_claim(turn_request, owner_token)
        if db.session().in_transaction():
            db.session.commit()
        if identity_conflict:
            raise TurnRequestIdentityConflictError("requestId identity conflict")
        if existing_claim is not None:
            return existing_claim
        if new_claim is None:
            raise TurnPersistenceError("Unable to establish turn request ownership.")
        return new_claim
    except IntegrityError as error:
        db.session.rollback()
        existing = AgentRunTurnRequest.query.filter_by(
            run_id=run_id,
            request_id=request_id,
        ).one_or_none()
        if existing is None:
            raise TurnPersistenceConflictError(
                "A concurrent turn request claim conflicted."
            ) from error
        run = _get_run(run_id)
        canonical_model_name = model_name or ""
        _validate_turn_request_identity(
            existing,
            stage_id=stage_id,
            user_content=user_content,
            system_prompt=system_prompt,
            model_name=canonical_model_name,
        )
        if existing.status == "abandoned":
            if not _claim_run_turn_slot(run_id, request_id=request_id):
                db.session.commit()
                return TurnRequestClaim(state="active")
            owner_token = _reclaim_abandoned_turn_request(existing)
            if owner_token is not None:
                run.current_stage_id = stage_id
                if model_name is not None:
                    run.model = model_name
                db.session.commit()
                return _owned_turn_request_claim(existing, owner_token)
            db.session.expire(existing)
            db.session.refresh(existing)
            _validate_turn_request_identity(
                existing,
                stage_id=stage_id,
                user_content=user_content,
                system_prompt=system_prompt,
                model_name=canonical_model_name,
            )
        if existing.status == "active" and _turn_request_lease_expired(existing):
            if not _claim_run_turn_slot(run_id, request_id=request_id):
                db.session.commit()
                return TurnRequestClaim(state="active")
            owner_token = _reclaim_expired_active_turn_request(existing)
            if owner_token is not None:
                run.current_stage_id = stage_id
                if model_name is not None:
                    run.model = model_name
                db.session.commit()
                return _owned_turn_request_claim(existing, owner_token)
            db.session.expire(existing)
            db.session.refresh(existing)
            _validate_turn_request_identity(
                existing,
                stage_id=stage_id,
                user_content=user_content,
                system_prompt=system_prompt,
                model_name=canonical_model_name,
            )
        if existing.status == "failed":
            _replace_turn_request_terminal_event(
                existing,
                _sanitize_failed_terminal_event(
                    _stored_turn_request_terminal_event(existing),
                    workflow_id=run.workflow_id,
                    stage_id=existing.stage_id,
                ),
            )
            db.session.commit()
        return _turn_request_claim(existing)


def abandon_agent_run_turn_request(
    run_id: str,
    *,
    request_id: str,
    owner_token: str,
) -> None:
    """Release an owned active request after its stream consumer disconnects."""
    try:
        transaction = (
            db.session.begin_nested()
            if db.session().in_transaction()
            else db.session.begin()
        )
        with transaction:
            turn_request = AgentRunTurnRequest.query.filter_by(
                run_id=run_id,
                request_id=request_id,
            ).one_or_none()
            if turn_request is None:
                raise TurnPersistenceConflictError(
                    "Turn request ownership was superseded."
                )
            _transition_owned_turn_request(
                turn_request,
                owner_token=owner_token,
                next_status="abandoned",
                terminal_event=None,
            )
        if db.session().in_transaction():
            db.session.commit()
    except SQLAlchemyError as error:
        db.session.rollback()
        raise TurnPersistenceError(
            "Unable to release the abandoned agent turn."
        ) from error


def fail_agent_run_turn_request(
    run_id: str,
    *,
    request_id: str,
    owner_token: str,
    terminal_event: dict,
) -> None:
    try:
        transaction = (
            db.session.begin_nested()
            if db.session().in_transaction()
            else db.session.begin()
        )
        with transaction:
            turn_request = AgentRunTurnRequest.query.filter_by(
                run_id=run_id,
                request_id=request_id,
            ).one_or_none()
            if turn_request is None:
                raise TurnPersistenceConflictError(
                    "Turn request ownership was superseded."
                )
            run = _get_run(run_id)
            sanitized_terminal_event = _sanitize_failed_terminal_event(
                terminal_event,
                workflow_id=run.workflow_id,
                stage_id=turn_request.stage_id,
            )
            _transition_owned_turn_request(
                turn_request,
                owner_token=owner_token,
                next_status="failed",
                terminal_event=sanitized_terminal_event,
            )
            failed_assistant_content, _error_diagnostic = (
                _failed_turn_message_projection(sanitized_terminal_event)
            )
            append_run_message(
                run_id,
                "assistant",
                failed_assistant_content,
                _commit=False,
            )
        if db.session().in_transaction():
            db.session.commit()
    except SQLAlchemyError as error:
        db.session.rollback()
        raise TurnPersistenceError(
            "Unable to persist the failed agent turn."
        ) from error


def record_artifact_version(
    run_id: str,
    stage_id: str,
    content: str,
    *,
    artifact_data: dict | None = None,
    _commit: bool = True,
) -> AgentArtifactVersion:
    run = _get_run(run_id)
    _validate_workflow_stage(run.workflow_id, stage_id)

    artifact = AgentArtifact.query.filter_by(
        run_id=run_id,
        stage_id=stage_id,
    ).first()
    if artifact is None:
        artifact = AgentArtifact(run_id=run_id, stage_id=stage_id)
        db.session.add(artifact)
        db.session.flush()

    version = AgentArtifactVersion(
        artifact_id=artifact.id,
        version_number=_next_artifact_version(artifact.id),
        content=content,
        artifact_data_json=(
            json.dumps(artifact_data, ensure_ascii=False)
            if artifact_data is not None
            else None
        ),
    )
    db.session.add(version)
    db.session.flush()
    artifact.current_version_id = version.id
    _upsert_artifact_context_summaries(run_id, stage_id, content)
    if _commit:
        db.session.commit()
    return version


def _stage_turn_metric(
    *,
    run_id: str,
    workflow_id: str,
    stage_id: str,
    model_name: str,
    provider: str,
    status: str,
    error_code: str | None,
    duration_ms: int,
    input_chars: int,
    output_chars: int,
    estimated_tokens: int,
    contract_retry_count: int,
    diagnostic: dict | None = None,
) -> AgentRunTurnMetric:
    _get_run(run_id)
    metric = AgentRunTurnMetric(
        run_id=run_id,
        workflow_id=workflow_id,
        stage_id=stage_id,
        model=model_name,
        provider=provider or "unknown",
        status=status,
        error_code=error_code,
        duration_ms=max(0, duration_ms),
        input_chars=max(0, input_chars),
        output_chars=max(0, output_chars),
        estimated_tokens=max(0, estimated_tokens),
        contract_retry_count=max(0, contract_retry_count),
        diagnostic=_sanitize_error_diagnostic(
            diagnostic,
            error_code=error_code,
            workflow_id=workflow_id,
            stage_id=stage_id,
        ),
    )
    db.session.add(metric)
    return metric


def complete_agent_run_turn(
    run_id: str,
    *,
    request_id: str | None = None,
    owner_token: str | None = None,
    stage_id: str,
    assistant_content: str,
    artifact_content: str | None,
    artifact_data: dict | None,
    terminal_event: dict | None = None,
    metric: dict,
) -> None:
    """Persist a successful assistant turn as one atomic outcome."""
    try:
        transaction = (
            db.session.begin_nested()
            if db.session().in_transaction()
            else db.session.begin()
        )
        with transaction:
            if request_id is not None:
                turn_request = AgentRunTurnRequest.query.filter_by(
                    run_id=run_id,
                    request_id=request_id,
                ).one_or_none()
                if turn_request is None:
                    raise TurnPersistenceConflictError(
                        "Turn request ownership was superseded."
                    )
                identity = _stored_turn_request_identity(turn_request)
                if (
                    identity is None
                    or turn_request.stage_id != stage_id
                    or identity["stageId"] != stage_id
                ):
                    raise TurnRequestIdentityConflictError(
                        "requestId identity conflict"
                    )
                if (
                    _last_assistant_sequence(run_id)
                    != identity["baselineAssistantSequence"]
                    or _current_stage_artifact_version(run_id, stage_id)
                    != identity["baselineArtifactVersion"]
                ):
                    raise TurnPersistenceConflictError(
                        "Turn request baseline was superseded."
                    )
                _transition_owned_turn_request(
                    turn_request,
                    owner_token=owner_token,
                    next_status="completed",
                    terminal_event=terminal_event,
                )
                _append_turn_request_user_supplement(turn_request)
            append_run_message(
                run_id,
                "assistant",
                assistant_content,
                _commit=False,
            )
            if artifact_content is not None:
                record_artifact_version(
                    run_id,
                    stage_id,
                    artifact_content,
                    artifact_data=artifact_data,
                    _commit=False,
                )
            _stage_turn_metric(run_id=run_id, **metric)
        if db.session().in_transaction():
            db.session.commit()
    except IntegrityError as error:
        db.session.rollback()
        raise TurnPersistenceConflictError(
            "A concurrent turn updated the durable run state."
        ) from error
    except SQLAlchemyError as error:
        db.session.rollback()
        raise TurnPersistenceError(
            "Unable to persist the completed agent turn."
        ) from error


def _upsert_artifact_context_summaries(
    run_id: str,
    stage_id: str,
    content: str,
) -> None:
    _upsert_context_summary(
        run_id,
        source_type=SUMMARY_SOURCE_ARTIFACT,
        source_stage_id=stage_id,
        summary_type=CURRENT_ARTIFACT_SUMMARY_TYPE,
        content=build_artifact_summary_content(content),
    )
    _upsert_context_summary(
        run_id,
        source_type=SUMMARY_SOURCE_ARTIFACT,
        source_stage_id=stage_id,
        summary_type=STAGE_CONCLUSION_SUMMARY_TYPE,
        content=build_stage_conclusion_summary_content(content),
    )
    _upsert_context_summary(
        run_id,
        source_type=SUMMARY_SOURCE_ARTIFACT,
        source_stage_id=stage_id,
        summary_type=DECISION_SUMMARY_TYPE,
        content=build_decision_summary_content(content),
    )


def _append_user_supplement_summary(
    run_id: str,
    stage_id: str,
    content: str,
) -> None:
    supplement = build_user_supplement_summary_content(content)
    if supplement is None:
        return

    summary = AgentContextSummary.query.filter_by(
        run_id=run_id,
        source_type=SUMMARY_SOURCE_USER_INPUT,
        source_stage_id=stage_id,
        summary_type=USER_SUPPLEMENT_SUMMARY_TYPE,
    ).first()
    if summary is None:
        db.session.add(
            AgentContextSummary(
                run_id=run_id,
                source_type=SUMMARY_SOURCE_USER_INPUT,
                source_stage_id=stage_id,
                summary_type=USER_SUPPLEMENT_SUMMARY_TYPE,
                content=supplement,
            )
        )
        return

    combined = build_user_supplement_summary_content(
        f"{summary.content}\n\n{supplement}"
    )
    if combined is not None:
        summary.content = combined


def _append_turn_request_user_supplement(
    turn_request: AgentRunTurnRequest,
) -> None:
    identity = _stored_turn_request_identity(turn_request)
    if identity is None:
        raise TurnRequestIdentityConflictError("requestId identity conflict")
    message = AgentMessage.query.filter_by(
        run_id=turn_request.run_id,
        role="user",
        sequence_index=identity["userMessageSequence"],
    ).one_or_none()
    if message is None:
        raise TurnPersistenceConflictError("Bound user message could not be resolved.")
    _append_user_supplement_summary(
        turn_request.run_id,
        identity["stageId"],
        message.content,
    )


def _upsert_context_summary(
    run_id: str,
    *,
    source_type: str,
    source_stage_id: str,
    summary_type: str,
    content: str | None,
) -> None:
    if content is None:
        return

    summary = AgentContextSummary.query.filter_by(
        run_id=run_id,
        source_type=source_type,
        source_stage_id=source_stage_id,
        summary_type=summary_type,
    ).first()
    if summary is None:
        db.session.add(
            AgentContextSummary(
                run_id=run_id,
                source_type=source_type,
                source_stage_id=source_stage_id,
                summary_type=summary_type,
                content=content,
            )
        )
    else:
        summary.content = content


def _read_summary_patch_string(
    patch: dict,
    field_name: str,
) -> str:
    value = patch.get(field_name)
    if not isinstance(value, str):
        raise ValueError(f"{field_name} 必须是字符串")
    return value


def _read_optional_patch_integer(patch: dict, field_name: str) -> int | None:
    if field_name not in patch:
        return None
    value = patch.get(field_name)
    if not isinstance(value, int):
        raise ValueError(f"{field_name} 必须是整数")
    return value


def update_context_summary(run_id: str, patch: dict) -> dict:
    if not isinstance(patch, dict):
        raise ValueError("请求体必须是对象")

    allowed_fields = {"sourceType", "sourceStageId", "summaryType", "content"}
    unexpected_fields = set(patch.keys()) - allowed_fields
    if unexpected_fields:
        raise ValueError(f"不支持的字段: {', '.join(sorted(unexpected_fields))}")

    missing_fields = allowed_fields - set(patch.keys())
    if missing_fields:
        raise ValueError(f"缺少字段: {', '.join(sorted(missing_fields))}")

    source_type = _read_summary_patch_string(patch, "sourceType")
    source_stage_id = _read_summary_patch_string(patch, "sourceStageId")
    summary_type = _read_summary_patch_string(patch, "summaryType")
    content = _read_summary_patch_string(patch, "content")
    if not content.strip():
        raise ValueError("content 不能为空")

    _get_run(run_id)
    summary = AgentContextSummary.query.filter_by(
        run_id=run_id,
        source_type=source_type,
        source_stage_id=source_stage_id,
        summary_type=summary_type,
    ).first()
    if summary is None:
        raise ValueError(
            "未知上下文摘要: " f"{source_type}/{source_stage_id}/{summary_type}"
        )

    summary.content = content
    db.session.commit()
    return {
        "sourceType": summary.source_type,
        "sourceStageId": summary.source_stage_id,
        "summaryType": summary.summary_type,
        "content": summary.content,
    }


def update_run_artifact(run_id: str, patch: dict) -> dict:
    if not isinstance(patch, dict):
        raise ValueError("请求体必须是对象")

    allowed_fields = {"stageId", "content", "expectedVersionNumber"}
    unexpected_fields = set(patch.keys()) - allowed_fields
    if unexpected_fields:
        raise ValueError(f"不支持的字段: {', '.join(sorted(unexpected_fields))}")

    required_fields = {"stageId", "content"}
    missing_fields = required_fields - set(patch.keys())
    if missing_fields:
        raise ValueError(f"缺少字段: {', '.join(sorted(missing_fields))}")

    stage_id = _read_summary_patch_string(patch, "stageId")
    content = _read_summary_patch_string(patch, "content")
    expected_version_number = _read_optional_patch_integer(
        patch,
        "expectedVersionNumber",
    )
    if not content.strip():
        raise ValueError("content 不能为空")

    run = _get_run(run_id)
    _validate_workflow_stage(run.workflow_id, stage_id)
    if expected_version_number is not None:
        artifact = AgentArtifact.query.filter_by(
            run_id=run_id,
            stage_id=stage_id,
        ).first()
        current_artifact = (
            _artifact_snapshot(artifact)
            if artifact is not None and artifact.current_version_id is not None
            else None
        )
        current_version_number = (
            current_artifact["versionNumber"] if current_artifact is not None else 0
        )
        if current_version_number != expected_version_number:
            raise ArtifactVersionConflictError(current_artifact)

    version = record_artifact_version(run_id, stage_id, content)
    _record_artifact_audit_event(
        run_id,
        stage_id,
        "artifact_saved",
        f"保存了 {stage_id} 阶段产出物 v{version.version_number}",
    )
    return {
        "stageId": stage_id,
        "content": version.content,
        "versionNumber": version.version_number,
    }


def _record_artifact_audit_event(
    run_id: str,
    stage_id: str,
    event_type: str,
    summary: str,
) -> AgentArtifactAuditEvent:
    event = AgentArtifactAuditEvent(
        run_id=run_id,
        stage_id=stage_id,
        event_type=event_type,
        summary=summary,
        created_at_ms=int(time.time() * 1000),
    )
    db.session.add(event)
    db.session.commit()
    return event


def replace_artifact_collaboration_state(run_id: str, patch: dict) -> dict:
    run = _get_run(run_id)
    collaboration_state = build_collaboration_state_models(
        run_id=run_id,
        workflow_id=run.workflow_id,
        current_stage_id=run.current_stage_id,
        patch=patch,
        created_at_ms=int(time.time() * 1000),
    )

    AgentArtifactComment.query.filter_by(run_id=run_id).delete()
    AgentArtifactSectionLock.query.filter_by(run_id=run_id).delete()
    db.session.add_all(collaboration_state.comments)
    db.session.add_all(collaboration_state.section_locks)
    db.session.add(collaboration_state.audit_event)
    db.session.commit()
    return {
        "artifactComments": [
            comment_snapshot(comment) for comment in collaboration_state.comments
        ],
        "artifactSectionLocks": [
            section_lock_snapshot(lock) for lock in collaboration_state.section_locks
        ],
    }


def upsert_manual_decision_summary(run_id: str, patch: dict) -> dict:
    if not isinstance(patch, dict):
        raise ValueError("请求体必须是对象")

    allowed_fields = {"stageId", "content"}
    unexpected_fields = set(patch.keys()) - allowed_fields
    if unexpected_fields:
        raise ValueError(f"不支持的字段: {', '.join(sorted(unexpected_fields))}")

    missing_fields = allowed_fields - set(patch.keys())
    if missing_fields:
        raise ValueError(f"缺少字段: {', '.join(sorted(missing_fields))}")

    stage_id = _read_summary_patch_string(patch, "stageId")
    content = _read_summary_patch_string(patch, "content")
    if not content.strip():
        raise ValueError("content 不能为空")

    run = _get_run(run_id)
    _validate_workflow_stage(run.workflow_id, stage_id)
    _upsert_context_summary(
        run_id,
        source_type=SUMMARY_SOURCE_ARTIFACT,
        source_stage_id=stage_id,
        summary_type=DECISION_SUMMARY_TYPE,
        content=content,
    )
    db.session.commit()
    return {
        "sourceType": SUMMARY_SOURCE_ARTIFACT,
        "sourceStageId": stage_id,
        "summaryType": DECISION_SUMMARY_TYPE,
        "content": content,
    }


def get_run_snapshot(run_id: str) -> dict:
    run = _get_run(run_id)
    messages = (
        AgentMessage.query.filter_by(run_id=run_id)
        .order_by(AgentMessage.sequence_index)
        .all()
    )
    failed_turn_requests = AgentRunTurnRequest.query.filter_by(
        run_id=run_id,
        status="failed",
    ).all()
    failed_message_projections: dict[int, tuple[str, dict]] = {}
    for turn_request in failed_turn_requests:
        identity = _stored_turn_request_identity(turn_request)
        if identity is None:
            continue
        terminal_event = _sanitize_failed_terminal_event(
            _stored_turn_request_terminal_event(turn_request),
            workflow_id=run.workflow_id,
            stage_id=turn_request.stage_id,
        )
        failed_message_projections[identity["userMessageSequence"] + 1] = (
            _failed_turn_message_projection(terminal_event)
        )
    artifacts = AgentArtifact.query.filter_by(run_id=run_id).order_by(
        AgentArtifact.stage_id,
    )
    context_summaries = AgentContextSummary.query.filter_by(run_id=run_id).order_by(
        AgentContextSummary.source_type,
        AgentContextSummary.source_stage_id,
        AgentContextSummary.summary_type,
    )
    artifact_comments = AgentArtifactComment.query.filter_by(run_id=run_id).order_by(
        AgentArtifactComment.created_at_ms,
    )
    artifact_section_locks = AgentArtifactSectionLock.query.filter_by(
        run_id=run_id,
    ).order_by(
        AgentArtifactSectionLock.created_at_ms,
    )
    artifact_audit_events = AgentArtifactAuditEvent.query.filter_by(
        run_id=run_id,
    ).order_by(
        AgentArtifactAuditEvent.created_at_ms,
        AgentArtifactAuditEvent.id,
    )

    return {
        "run": {
            "id": run.id,
            "workflowId": run.workflow_id,
            "agentId": run.agent_id,
            "currentStageId": run.current_stage_id,
            "status": run.status,
            "model": run.model,
        },
        "pendingStageTransition": _snapshot_pending_stage_transition(run),
        "messages": [
            {
                "role": message.role,
                "content": message.content,
                "sequenceIndex": message.sequence_index,
                **(
                    {
                        "errorDiagnostic": failed_message_projections[
                            message.sequence_index
                        ][1]
                    }
                    if message.role == "assistant"
                    and message.sequence_index in failed_message_projections
                    and message.content
                    == failed_message_projections[message.sequence_index][0]
                    else {}
                ),
            }
            for message in messages
        ],
        "artifacts": [
            _artifact_snapshot(artifact)
            for artifact in artifacts
            if artifact.current_version_id is not None
        ],
        "contextSummaries": [
            {
                "sourceType": summary.source_type,
                "sourceStageId": summary.source_stage_id,
                "summaryType": summary.summary_type,
                "content": summary.content,
            }
            for summary in context_summaries
        ],
        "artifactComments": [
            comment_snapshot(comment) for comment in artifact_comments
        ],
        "artifactSectionLocks": [
            section_lock_snapshot(lock) for lock in artifact_section_locks
        ],
        "artifactAuditEvents": [
            audit_event_snapshot(event) for event in artifact_audit_events
        ],
    }


def record_turn_metric(
    *,
    run_id: str,
    workflow_id: str,
    stage_id: str,
    model_name: str,
    provider: str,
    status: str,
    error_code: str | None,
    duration_ms: int,
    input_chars: int,
    output_chars: int,
    estimated_tokens: int,
    contract_retry_count: int,
    diagnostic: dict | None = None,
) -> AgentRunTurnMetric:
    try:
        metric = _stage_turn_metric(
            run_id=run_id,
            workflow_id=workflow_id,
            stage_id=stage_id,
            model_name=model_name,
            provider=provider,
            status=status,
            error_code=error_code,
            duration_ms=duration_ms,
            input_chars=input_chars,
            output_chars=output_chars,
            estimated_tokens=estimated_tokens,
            contract_retry_count=contract_retry_count,
            diagnostic=diagnostic,
        )
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
    else:
        return metric
    raise TurnPersistenceError("Unable to persist the agent turn metric.") from None


def record_runtime_config_issue(
    *,
    workflow_id: str,
    stage_id: str,
    error_code: str,
    issue_scope: str,
    route: str,
    request_id: str,
) -> AgentRuntimeConfigIssue:
    _validate_workflow_stage(workflow_id, stage_id)
    issue = AgentRuntimeConfigIssue(
        workflow_id=workflow_id,
        stage_id=stage_id,
        error_code=error_code,
        issue_scope=issue_scope,
        route=route,
        request_id=request_id,
    )
    db.session.add(issue)
    db.session.commit()
    return issue


def get_runtime_observability_summary(
    *,
    limit: int = 20,
    workflow_id: str | None = None,
    stage_id: str | None = None,
) -> dict:
    if limit < 1:
        limit = 20
    if limit > 100:
        limit = 100
    if stage_id is not None and workflow_id is None:
        raise ValueError("stageId 需要与 workflowId 一起使用")
    if workflow_id is not None:
        if workflow_id not in WORKFLOW_STAGES:
            raise ValueError(f"未知 workflowId: {workflow_id}")
        if stage_id is not None:
            _validate_workflow_stage(workflow_id, stage_id)

    query = AgentRunTurnMetric.query
    if workflow_id is not None:
        query = query.filter(AgentRunTurnMetric.workflow_id == workflow_id)
    if stage_id is not None:
        query = query.filter(AgentRunTurnMetric.stage_id == stage_id)

    metrics = query.order_by(
        AgentRunTurnMetric.created_at.desc(),
        AgentRunTurnMetric.id.desc(),
    ).all()
    _scrub_legacy_metric_diagnostics(metrics)

    config_issue_query = AgentRuntimeConfigIssue.query
    if workflow_id is not None:
        config_issue_query = config_issue_query.filter(
            AgentRuntimeConfigIssue.workflow_id == workflow_id
        )
    if stage_id is not None:
        config_issue_query = config_issue_query.filter(
            AgentRuntimeConfigIssue.stage_id == stage_id
        )
    config_issues = config_issue_query.order_by(
        AgentRuntimeConfigIssue.created_at.desc(),
        AgentRuntimeConfigIssue.id.desc(),
    ).all()

    total_turns = len(metrics) + len(config_issues)
    failed_turns = sum(1 for metric in metrics if metric.status != "success") + len(
        config_issues
    )
    provider_issue_codes = _merge_error_codes(
        _provider_issue_codes(metrics),
        _config_issue_provider_codes(config_issues),
    )

    stage_config_issue_index: dict[tuple[str, str], list[AgentRuntimeConfigIssue]] = {}
    stage_index: dict[tuple[str, str], list[AgentRunTurnMetric]] = {}
    provider_index: dict[str, list[AgentRunTurnMetric]] = {}
    for metric in metrics:
        stage_index.setdefault((metric.workflow_id, metric.stage_id), []).append(metric)
        provider_index.setdefault(metric.provider, []).append(metric)
    for issue in config_issues:
        stage_config_issue_index.setdefault(
            (issue.workflow_id, issue.stage_id),
            [],
        ).append(issue)
    stage_keys = sorted(set(stage_index) | set(stage_config_issue_index))

    contract_retry_reasons = _contract_retry_reasons(metrics)
    diagnostics = _runtime_diagnostics(
        total_turns=total_turns,
        failed_turns=failed_turns,
        success_rate=_success_rate(total_turns, failed_turns),
        provider_issue_codes=provider_issue_codes,
        metrics=metrics,
        config_issues=config_issues,
        stage_items=[
            _stage_observability_item(
                workflow_id,
                stage_id,
                stage_index.get((workflow_id, stage_id), []),
                stage_config_issue_index.get((workflow_id, stage_id), []),
            )
            for workflow_id, stage_id in stage_keys
        ],
        contract_retry_reasons=contract_retry_reasons,
    )

    return {
        "totals": {
            "turns": total_turns,
            "failedTurns": failed_turns,
            "successRate": _success_rate(total_turns, failed_turns),
            "avgDurationMs": _avg_duration(
                metrics,
                zero_duration_count=len(config_issues),
            ),
            "estimatedTokens": sum(metric.estimated_tokens for metric in metrics),
            "providerIssueCount": sum(provider_issue_codes.values()),
            "providerIssueCodes": provider_issue_codes,
        },
        "byStage": [
            _stage_observability_item(
                workflow_id,
                stage_id,
                stage_index.get((workflow_id, stage_id), []),
                stage_config_issue_index.get((workflow_id, stage_id), []),
            )
            for workflow_id, stage_id in stage_keys
        ],
        "byProvider": [
            _provider_observability_item(provider, provider_metrics)
            for provider, provider_metrics in sorted(provider_index.items())
        ],
        "recentTurns": [_turn_metric_snapshot(metric) for metric in metrics[:limit]],
        "contractRetryReasons": contract_retry_reasons,
        "diagnostics": diagnostics,
    }


def _contract_retry_reasons(metrics: list[AgentRunTurnMetric]) -> dict[str, int]:
    retry_count = sum(metric.contract_retry_count for metric in metrics)
    if retry_count <= 0:
        return {}
    return {CONTRACT_RETRY_REASON: retry_count}


def _top_contract_retry_stage(
    metrics: list[AgentRunTurnMetric],
) -> tuple[str, str, int] | None:
    retry_by_stage: dict[tuple[str, str], int] = {}
    for metric in metrics:
        if metric.contract_retry_count <= 0:
            continue
        key = (metric.workflow_id, metric.stage_id)
        retry_by_stage[key] = retry_by_stage.get(key, 0) + metric.contract_retry_count
    if not retry_by_stage:
        return None
    (workflow_id, stage_id), retry_count = sorted(
        retry_by_stage.items(),
        key=lambda item: (-item[1], item[0][0], item[0][1]),
    )[0]
    return workflow_id, stage_id, retry_count


def _runtime_diagnostics(
    *,
    total_turns: int,
    failed_turns: int,
    success_rate: float,
    provider_issue_codes: dict[str, int],
    metrics: list[AgentRunTurnMetric],
    config_issues: list[AgentRuntimeConfigIssue],
    stage_items: list[dict],
    contract_retry_reasons: dict[str, int],
) -> list[dict]:
    diagnostics: list[dict] = []
    provider_issue_count = sum(provider_issue_codes.values())
    if provider_issue_count > 0:
        top_issue_code = sorted(
            provider_issue_codes.items(),
            key=lambda item: (-item[1], item[0]),
        )[0][0]
        diagnostics.append(
            {
                "id": "provider-config",
                "severity": "critical" if config_issues else "warning",
                "title": "模型/供应商配置异常",
                "detail": (
                    f"最近运行中有 {provider_issue_count} 轮与模型配置、"
                    f"供应商额度、鉴权或网络有关；最高频错误为 {top_issue_code}。"
                ),
                "action": "打开模型设置并检测连接，确认 API Key、Base URL、模型名和额度状态。",
            }
        )

    if failed_turns > 0 and success_rate < LOW_OBSERVABILITY_SUCCESS_RATE_THRESHOLD:
        diagnostics.append(
            {
                "id": "runtime-failures",
                "severity": "warning",
                "title": "运行失败率偏高",
                "detail": (
                    f"最近 {total_turns} 轮中有 {failed_turns} 轮失败，"
                    f"成功率 {success_rate}%。"
                ),
                "action": "优先查看失败集中的 workflow/stage 和最近运行错误码，再重试修复后的阶段。",
            }
        )

    risky_stage = sorted(
        (
            stage
            for stage in stage_items
            if stage["failedTurns"] > 0
            and stage["successRate"] < LOW_OBSERVABILITY_SUCCESS_RATE_THRESHOLD
        ),
        key=lambda stage: (
            stage["successRate"],
            -stage["failedTurns"],
            stage["workflowId"],
            stage["stageId"],
        ),
    )
    if risky_stage:
        stage = risky_stage[0]
        diagnostics.append(
            {
                "id": "stage-failures",
                "severity": "warning",
                "title": "阶段失败集中",
                "detail": (
                    f"{stage['workflowId']} / {stage['stageId']} 成功率 "
                    f"{stage['successRate']}%，失败 {stage['failedTurns']}/{stage['turns']} 轮。"
                ),
                "action": "检查该阶段输入上下文、stage prompt、artifact contract 和重试后的错误码。",
            }
        )

    retry_count = contract_retry_reasons.get(CONTRACT_RETRY_REASON, 0)
    if retry_count > 0:
        top_stage = _top_contract_retry_stage(metrics)
        stage_detail = ""
        if top_stage:
            workflow_id, stage_id, stage_retry_count = top_stage
            stage_detail = (
                f"，集中在 {workflow_id} / {stage_id}（{stage_retry_count} 次）"
            )
        diagnostics.append(
            {
                "id": "contract-retry",
                "severity": "warning",
                "title": "结构化输出重试偏高",
                "detail": f"最近运行中有 {retry_count} 次 contract retry{stage_detail}。",
                "action": "检查该阶段 prompt、artifact contract 和 renderer 输出是否同步。",
            }
        )

    return diagnostics


def _success_rate(total_turns: int, failed_turns: int) -> float:
    if total_turns == 0:
        return 0.0
    return round(((total_turns - failed_turns) / total_turns) * 100, 2)


def _avg_duration(
    metrics: list[AgentRunTurnMetric],
    *,
    zero_duration_count: int = 0,
) -> float:
    total_count = len(metrics) + zero_duration_count
    if total_count == 0:
        return 0.0
    return round(
        sum(metric.duration_ms for metric in metrics) / total_count,
        2,
    )


def _merge_error_codes(*code_groups: dict[str, int]) -> dict[str, int]:
    merged: dict[str, int] = {}
    for codes in code_groups:
        for code, count in codes.items():
            merged[code] = merged.get(code, 0) + count
    return dict(sorted(merged.items()))


def _project_observability_error_code(error_code: str | None) -> str | None:
    if error_code is None:
        return None
    if error_code in SAFE_OBSERVABILITY_ERROR_CODES:
        return error_code
    return UNKNOWN_OBSERVABILITY_ERROR_CODE


def _provider_issue_codes(metrics: list[AgentRunTurnMetric]) -> dict[str, int]:
    issue_codes: dict[str, int] = {}
    for metric in metrics:
        if metric.error_code in PROVIDER_ISSUE_ERROR_CODES:
            issue_codes[metric.error_code] = issue_codes.get(metric.error_code, 0) + 1
    return dict(sorted(issue_codes.items()))


def _config_issue_provider_codes(
    config_issues: list[AgentRuntimeConfigIssue],
) -> dict[str, int]:
    issue_codes: dict[str, int] = {}
    for issue in config_issues:
        if issue.error_code in PROVIDER_ISSUE_ERROR_CODES:
            issue_codes[issue.error_code] = issue_codes.get(issue.error_code, 0) + 1
    return dict(sorted(issue_codes.items()))


def _stage_observability_item(
    workflow_id: str,
    stage_id: str,
    metrics: list[AgentRunTurnMetric],
    config_issues: list[AgentRuntimeConfigIssue] | None = None,
) -> dict:
    config_issues = config_issues or []
    total_turns = len(metrics) + len(config_issues)
    failed_turns = sum(1 for metric in metrics if metric.status != "success") + len(
        config_issues
    )
    error_codes: dict[str, int] = {}
    for metric in metrics:
        error_code = _project_observability_error_code(metric.error_code)
        if error_code:
            error_codes[error_code] = error_codes.get(error_code, 0) + 1
    for issue in config_issues:
        error_code = _project_observability_error_code(issue.error_code)
        if error_code:
            error_codes[error_code] = error_codes.get(error_code, 0) + 1
    provider_issue_codes = _merge_error_codes(
        _provider_issue_codes(metrics),
        _config_issue_provider_codes(config_issues),
    )

    return {
        "workflowId": workflow_id,
        "stageId": stage_id,
        "turns": total_turns,
        "failedTurns": failed_turns,
        "successRate": _success_rate(total_turns, failed_turns),
        "avgDurationMs": _avg_duration(
            metrics,
            zero_duration_count=len(config_issues),
        ),
        "estimatedTokens": sum(metric.estimated_tokens for metric in metrics),
        "errorCodes": dict(sorted(error_codes.items())),
        "providerIssueCount": sum(provider_issue_codes.values()),
        "providerIssueCodes": provider_issue_codes,
    }


def _provider_observability_item(
    provider: str,
    metrics: list[AgentRunTurnMetric],
) -> dict:
    failed_turns = sum(1 for metric in metrics if metric.status != "success")
    error_codes: dict[str, int] = {}
    for metric in metrics:
        error_code = _project_observability_error_code(metric.error_code)
        if error_code:
            error_codes[error_code] = error_codes.get(error_code, 0) + 1
    provider_issue_codes = _provider_issue_codes(metrics)

    return {
        "provider": provider,
        "turns": len(metrics),
        "failedTurns": failed_turns,
        "successRate": _success_rate(len(metrics), failed_turns),
        "avgDurationMs": _avg_duration(metrics),
        "estimatedTokens": sum(metric.estimated_tokens for metric in metrics),
        "errorCodes": dict(sorted(error_codes.items())),
        "providerIssueCount": sum(provider_issue_codes.values()),
        "providerIssueCodes": provider_issue_codes,
    }


def _turn_metric_snapshot(metric: AgentRunTurnMetric) -> dict:
    error_code = _project_observability_error_code(metric.error_code)
    snapshot = {
        "id": metric.id,
        "runId": metric.run_id,
        "workflowId": metric.workflow_id,
        "stageId": metric.stage_id,
        "model": metric.model,
        "provider": metric.provider,
        "status": metric.status,
        "errorCode": error_code,
        "durationMs": metric.duration_ms,
        "inputChars": metric.input_chars,
        "outputChars": metric.output_chars,
        "estimatedTokens": metric.estimated_tokens,
        "contractRetryCount": metric.contract_retry_count,
        "createdAt": _format_datetime(metric.created_at),
    }
    diagnostic = _sanitize_error_diagnostic(
        metric.diagnostic,
        error_code=error_code,
        workflow_id=metric.workflow_id,
        stage_id=metric.stage_id,
    )
    if diagnostic is not None:
        snapshot["diagnostic"] = diagnostic
    return snapshot


def _sanitize_error_diagnostic(
    value: dict | None,
    *,
    error_code: str | None,
    workflow_id: str,
    stage_id: str,
) -> dict | None:
    if not isinstance(value, dict):
        return None
    safe_event = _sanitize_failed_terminal_event(
        {"code": error_code, "diagnostic": value},
        workflow_id=workflow_id,
        stage_id=stage_id,
    )
    sanitized = dict(safe_event["diagnostic"])
    if error_code == "SCHEMA_VALIDATION_FAILED":
        stored_validator = value.get("validator")
        validator = (
            stored_validator
            if isinstance(stored_validator, str)
            and stored_validator in SAFE_SCHEMA_VALIDATORS
            else "structured_output"
        )
        sanitized["validator"] = validator
        sanitized["fieldPath"] = project_safe_schema_field_path(validator)
    return sanitized


def _scrub_legacy_metric_diagnostics(
    metrics: list[AgentRunTurnMetric],
) -> None:
    changed = False
    for metric in metrics:
        sanitized = _sanitize_error_diagnostic(
            metric.diagnostic,
            error_code=metric.error_code,
            workflow_id=metric.workflow_id,
            stage_id=metric.stage_id,
        )
        if metric.diagnostic != sanitized:
            metric.diagnostic = sanitized
            changed = True
    if changed:
        db.session.commit()


def list_agent_runs(
    *,
    workflow_id: str | None = None,
    reuse_status: str | None = None,
    limit: int = DEFAULT_RUN_LIST_LIMIT,
    offset: int = 0,
    query_text: str | None = None,
) -> dict:
    if workflow_id is not None and workflow_id not in WORKFLOW_STAGES:
        raise ValueError(f"未知 workflowId: {workflow_id}")
    if reuse_status is not None and reuse_status not in RUN_REUSE_STATUSES:
        raise ValueError(f"未知 reuseStatus: {reuse_status}")
    if limit < 1:
        limit = DEFAULT_RUN_LIST_LIMIT
    if limit > MAX_RUN_LIST_LIMIT:
        limit = MAX_RUN_LIST_LIMIT
    if offset < 0:
        offset = 0
    normalized_query = query_text.strip() if query_text is not None else ""

    query = AgentRun.query
    if workflow_id is not None:
        query = query.filter_by(workflow_id=workflow_id)
    if reuse_status is not None:
        query = _apply_run_reuse_status_filter(query, reuse_status)
    if normalized_query:
        query = _apply_run_search_filter(query, normalized_query)

    total = query.count()
    runs = (
        query.order_by(AgentRun.updated_at.desc(), AgentRun.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    has_more = offset + len(runs) < total

    return {
        "limit": limit,
        "offset": offset,
        "total": total,
        "hasMore": has_more,
        "nextOffset": offset + len(runs) if has_more else None,
        "query": normalized_query or None,
        "runs": [_run_list_item(run) for run in runs],
    }


def _apply_run_search_filter(query, query_text: str):
    pattern = f"%{query_text}%"
    message_match = (
        db.session.query(AgentMessage.id)
        .filter(
            AgentMessage.run_id == AgentRun.id,
            AgentMessage.content.ilike(pattern),
        )
        .exists()
    )
    summary_match = (
        db.session.query(AgentContextSummary.id)
        .filter(
            AgentContextSummary.run_id == AgentRun.id,
            AgentContextSummary.content.ilike(pattern),
        )
        .exists()
    )
    return query.filter(
        db.or_(
            AgentRun.id.ilike(pattern),
            AgentRun.workflow_id.ilike(pattern),
            AgentRun.agent_id.ilike(pattern),
            AgentRun.current_stage_id.ilike(pattern),
            AgentRun.status.ilike(pattern),
            AgentRun.model.ilike(pattern),
            message_match,
            summary_match,
        )
    )


def _apply_run_reuse_status_filter(query, reuse_status: str):
    artifact_summary_exists = (
        db.session.query(AgentContextSummary.id)
        .filter(
            AgentContextSummary.run_id == AgentRun.id,
            AgentContextSummary.source_type == SUMMARY_SOURCE_ARTIFACT,
            AgentContextSummary.summary_type == CURRENT_ARTIFACT_SUMMARY_TYPE,
        )
        .exists()
    )
    if reuse_status == "failed":
        return query.filter(AgentRun.status == "failed")
    if reuse_status == "ready":
        return query.filter(AgentRun.status != "failed", artifact_summary_exists)
    return query.filter(AgentRun.status != "failed", ~artifact_summary_exists)


def _run_list_item(run: AgentRun) -> dict:
    return {
        "id": run.id,
        "workflowId": run.workflow_id,
        "agentId": run.agent_id,
        "currentStageId": run.current_stage_id,
        "status": run.status,
        "reuseStatus": _run_reuse_status(run),
        "model": run.model,
        "createdAt": _format_datetime(run.created_at),
        "updatedAt": _format_datetime(run.updated_at),
        "lastMessage": _last_message_snapshot(run.id),
        "currentArtifact": _current_artifact_summary(run.id),
    }


def _run_reuse_status(run: AgentRun) -> str:
    if run.status == "failed":
        return "failed"
    return (
        "ready" if _current_artifact_summary(run.id) is not None else "needs_artifact"
    )


def _format_datetime(value) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _last_message_snapshot(run_id: str) -> dict | None:
    message = (
        AgentMessage.query.filter_by(run_id=run_id)
        .order_by(AgentMessage.sequence_index.desc())
        .first()
    )
    if message is None:
        return None
    return {
        "role": message.role,
        "content": message.content,
        "sequenceIndex": message.sequence_index,
    }


def _current_artifact_summary(run_id: str) -> dict | None:
    summary = (
        AgentContextSummary.query.filter_by(
            run_id=run_id,
            source_type=SUMMARY_SOURCE_ARTIFACT,
            summary_type=CURRENT_ARTIFACT_SUMMARY_TYPE,
        )
        .order_by(AgentContextSummary.updated_at.desc())
        .first()
    )
    if summary is None:
        return None

    artifact = AgentArtifact.query.filter_by(
        run_id=run_id,
        stage_id=summary.source_stage_id,
    ).first()
    version_number = None
    if artifact is not None and artifact.current_version_id is not None:
        version = db.session.get(AgentArtifactVersion, artifact.current_version_id)
        if version is not None:
            version_number = version.version_number

    return {
        "stageId": summary.source_stage_id,
        "versionNumber": version_number,
        "summary": summary.content,
    }


def _artifact_snapshot(artifact: AgentArtifact) -> dict:
    version = db.session.get(AgentArtifactVersion, artifact.current_version_id)
    if version is None:
        raise ValueError(f"artifact 当前版本不存在: {artifact.id}")
    return {
        "stageId": artifact.stage_id,
        "content": version.content,
        "versionNumber": version.version_number,
        "artifactData": (
            json.loads(version.artifact_data_json)
            if version.artifact_data_json
            else None
        ),
    }
