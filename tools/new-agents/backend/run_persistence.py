import time
from uuid import uuid4

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
from models import (
    AgentArtifact,
    AgentArtifactAuditEvent,
    AgentArtifactComment,
    AgentArtifactSectionLock,
    AgentArtifactVersion,
    AgentContextSummary,
    AgentMessage,
    AgentRun,
    AgentRunTurnMetric,
    AgentRuntimeConfigIssue,
    db,
)
from workflow_manifest import get_workflow_agent_id


MESSAGE_ROLES = {"user", "assistant"}
RUN_STATUSES = {"active", "completed", "failed"}
SUMMARY_SOURCE_ARTIFACT = "artifact"
SUMMARY_SOURCE_USER_INPUT = "user_input"
DEFAULT_RUN_LIST_LIMIT = 20
MAX_RUN_LIST_LIMIT = 100
PROVIDER_ISSUE_ERROR_CODES = {"LLM_ERROR", DEFAULT_LLM_CONFIG_MISSING_CODE}


class ArtifactVersionConflictError(ValueError):
    def __init__(self, current_artifact: dict | None):
        super().__init__("产出物已被更新，请刷新后再保存")
        self.current_artifact = current_artifact


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
) -> AgentRun:
    _validate_workflow_stage(workflow_id, current_stage_id)
    if status not in RUN_STATUSES:
        raise ValueError(f"未知 run status: {status}")

    run = AgentRun(
        id=str(uuid4()),
        workflow_id=workflow_id,
        agent_id=agent_id,
        current_stage_id=current_stage_id,
        status=status,
        model=model,
    )
    db.session.add(run)
    db.session.commit()
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

    run = _get_run(run_id)
    if run.workflow_id != workflow_id:
        raise ValueError(f"runId 与 workflowId 不匹配: {run_id}/{workflow_id}")
    if run.agent_id != agent_id:
        raise ValueError(f"runId 与 agentId 不匹配: {run_id}/{agent_id}")

    run.current_stage_id = current_stage_id
    if model is not None:
        run.model = model
    db.session.commit()
    return run


class AgentRunPersistence:
    def ensure_run(self, agent_request, *, model_name: str) -> str:
        agent_id = get_workflow_agent_id(agent_request.workflow_id)
        run = ensure_agent_run(
            agent_request.workflow_id,
            agent_id,
            agent_request.stage_id,
            run_id=agent_request.run_id,
            model=model_name,
        )
        return run.id

    def append_user_message(self, run_id: str, content: str) -> None:
        append_run_message(run_id, "user", content)

    def build_runtime_prompt(self, run_id: str, current_prompt: str) -> str:
        from context_builder import build_run_context_prompt

        return build_run_context_prompt(run_id, current_prompt)

    def build_runtime_context(self, run_id: str, current_prompt: str):
        from context_builder import build_run_context

        context = build_run_context(run_id, current_prompt)
        return context.prompt, context.warnings

    def append_assistant_message(self, run_id: str, content: str) -> None:
        append_run_message(run_id, "assistant", content)

    def record_artifact_version(
        self,
        run_id: str,
        stage_id: str,
        content: str,
    ) -> None:
        record_artifact_version(run_id, stage_id, content)

    def record_turn_metric(self, **kwargs) -> None:
        record_turn_metric(**kwargs)


def append_run_message(run_id: str, role: str, content: str) -> AgentMessage:
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
    if role == "user":
        _append_user_supplement_summary(run_id, run.current_stage_id, content)
    db.session.commit()
    return message


def record_artifact_version(
    run_id: str,
    stage_id: str,
    content: str,
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
    )
    db.session.add(version)
    db.session.flush()
    artifact.current_version_id = version.id
    _upsert_artifact_context_summaries(run_id, stage_id, content)
    db.session.commit()
    return version


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
            "未知上下文摘要: "
            f"{source_type}/{source_stage_id}/{summary_type}"
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
    _require_collaboration_artifacts(
        run_id,
        {
            item.stage_id
            for item in [
                *collaboration_state.comments,
                *collaboration_state.section_locks,
            ]
        },
    )

    AgentArtifactComment.query.filter_by(run_id=run_id).delete()
    AgentArtifactSectionLock.query.filter_by(run_id=run_id).delete()
    db.session.add_all(collaboration_state.comments)
    db.session.add_all(collaboration_state.section_locks)
    db.session.add(collaboration_state.audit_event)
    db.session.commit()
    return {
        "artifactComments": [
            comment_snapshot(comment)
            for comment in collaboration_state.comments
        ],
        "artifactSectionLocks": [
            section_lock_snapshot(lock)
            for lock in collaboration_state.section_locks
        ],
    }


def _require_collaboration_artifacts(run_id: str, stage_ids: set[str]) -> None:
    if not stage_ids:
        return

    existing_stage_ids = {
        stage_id
        for (stage_id,) in (
            db.session.query(AgentArtifact.stage_id)
            .filter(
                AgentArtifact.run_id == run_id,
                AgentArtifact.stage_id.in_(stage_ids),
                AgentArtifact.current_version_id.isnot(None),
            )
            .all()
        )
    }
    missing_stage_ids = sorted(stage_ids - existing_stage_ids)
    if missing_stage_ids:
        if len(missing_stage_ids) == 1:
            raise ValueError(
                f"{missing_stage_ids[0]} 阶段产出物不存在，无法保存协作状态"
            )
        raise ValueError(
            "以下阶段产出物不存在，无法保存协作状态: "
            + ", ".join(missing_stage_ids)
        )


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
    messages = AgentMessage.query.filter_by(run_id=run_id).order_by(
        AgentMessage.sequence_index,
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
        "messages": [
            {
                "role": message.role,
                "content": message.content,
                "sequenceIndex": message.sequence_index,
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
            comment_snapshot(comment)
            for comment in artifact_comments
        ],
        "artifactSectionLocks": [
            section_lock_snapshot(lock)
            for lock in artifact_section_locks
        ],
        "artifactAuditEvents": [
            audit_event_snapshot(event)
            for event in artifact_audit_events
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
    )
    db.session.add(metric)
    db.session.commit()
    return metric


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
    failed_turns = (
        sum(1 for metric in metrics if metric.status != "success")
        + len(config_issues)
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
        "recentTurns": [
            _turn_metric_snapshot(metric)
            for metric in metrics[:limit]
        ],
    }


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
    failed_turns = (
        sum(1 for metric in metrics if metric.status != "success")
        + len(config_issues)
    )
    error_codes: dict[str, int] = {}
    for metric in metrics:
        if metric.error_code:
            error_codes[metric.error_code] = error_codes.get(metric.error_code, 0) + 1
    for issue in config_issues:
        error_codes[issue.error_code] = error_codes.get(issue.error_code, 0) + 1
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
        if metric.error_code:
            error_codes[metric.error_code] = error_codes.get(metric.error_code, 0) + 1
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
    return {
        "id": metric.id,
        "runId": metric.run_id,
        "workflowId": metric.workflow_id,
        "stageId": metric.stage_id,
        "model": metric.model,
        "provider": metric.provider,
        "status": metric.status,
        "errorCode": metric.error_code,
        "durationMs": metric.duration_ms,
        "inputChars": metric.input_chars,
        "outputChars": metric.output_chars,
        "estimatedTokens": metric.estimated_tokens,
        "contractRetryCount": metric.contract_retry_count,
        "createdAt": _format_datetime(metric.created_at),
    }


def list_agent_runs(
    *,
    workflow_id: str | None = None,
    limit: int = DEFAULT_RUN_LIST_LIMIT,
    offset: int = 0,
    query_text: str | None = None,
) -> dict:
    if workflow_id is not None and workflow_id not in WORKFLOW_STAGES:
        raise ValueError(f"未知 workflowId: {workflow_id}")
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


def _run_list_item(run: AgentRun) -> dict:
    return {
        "id": run.id,
        "workflowId": run.workflow_id,
        "agentId": run.agent_id,
        "currentStageId": run.current_stage_id,
        "status": run.status,
        "model": run.model,
        "createdAt": _format_datetime(run.created_at),
        "updatedAt": _format_datetime(run.updated_at),
        "lastMessage": _last_message_snapshot(run.id),
        "currentArtifact": _current_artifact_summary(run.id),
    }


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
    }
