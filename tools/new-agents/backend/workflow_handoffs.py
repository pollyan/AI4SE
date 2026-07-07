import hashlib

from agent_contracts import WORKFLOW_STAGES
from context_summary_format import CURRENT_ARTIFACT_SUMMARY_TYPE
from models import AgentArtifact, AgentArtifactVersion, AgentContextSummary, AgentRun, db
from run_persistence import append_run_message, create_agent_run, get_run_snapshot
from workflow_manifest import get_workflow_handoffs


HANDOFF_CONTEXT_MAX_CHARS = 6000
HANDOFF_SUMMARY_MAX_CHARS = 280
HANDOFF_TRUNCATION_NOTICE = "\n\n[源产物内容已截断]"
HANDOFF_PROMPT_TEMPLATES = {
    "source-artifact-handoff": "请基于以下上游产物继续工作。",
}


def export_run_handoffs(run_id: str) -> dict:
    snapshot = get_run_snapshot(run_id)
    run = snapshot["run"]
    handoffs = []

    for handoff in get_workflow_handoffs():
        if handoff["sourceWorkflowId"] != run["workflowId"]:
            continue
        artifact = _source_artifact(snapshot, handoff["sourceStageId"])
        if artifact is None:
            continue
        handoffs.append(_build_handoff(handoff, artifact, source_run_id=run["id"]))

    return {
        "runId": run["id"],
        "sourceWorkflowId": run["workflowId"],
        "handoffs": handoffs,
    }


def start_workflow_handoff(run_id: str, handoff_id: str) -> dict:
    candidates = export_run_handoffs(run_id)
    handoff = next(
        (
            candidate
            for candidate in candidates["handoffs"]
            if candidate["id"] == handoff_id
        ),
        None,
    )
    if handoff is None:
        raise ValueError(f"未知 handoff: {handoff_id}")

    target_run = create_agent_run(
        handoff["targetWorkflowId"],
        handoff["targetAgentId"],
        handoff["targetStageId"],
    )
    append_run_message(target_run.id, "user", handoff["prompt"])
    return {
        **handoff,
        "sourceRunId": run_id,
        "targetRunId": target_run.id,
    }


def export_target_workflow_handoffs(
    target_workflow_id: str,
    target_stage_id: str | None = None,
    *,
    limit: int = 20,
) -> dict:
    _validate_workflow_stage(target_workflow_id, target_stage_id)
    normalized_limit = max(1, min(limit, 100))
    handoffs = []

    for handoff in get_workflow_handoffs():
        if handoff["targetWorkflowId"] != target_workflow_id:
            continue
        if target_stage_id is not None and handoff["targetStageId"] != target_stage_id:
            continue

        source_artifacts = (
            db.session.query(AgentRun, AgentArtifact, AgentArtifactVersion)
            .join(AgentArtifact, AgentArtifact.run_id == AgentRun.id)
            .join(
                AgentArtifactVersion,
                AgentArtifactVersion.id == AgentArtifact.current_version_id,
            )
            .filter(AgentRun.workflow_id == handoff["sourceWorkflowId"])
            .filter(AgentArtifact.stage_id == handoff["sourceStageId"])
            .order_by(
                AgentArtifact.updated_at.desc(),
                AgentRun.updated_at.desc(),
                AgentRun.created_at.desc(),
            )
            .limit(normalized_limit)
            .all()
        )

        for run, artifact, version in source_artifacts:
            artifact_payload = {
                "content": version.content,
                "versionNumber": version.version_number,
                "digest": _source_artifact_digest(version.content),
                "summary": _source_artifact_summary(
                    run.id,
                    artifact.stage_id,
                    version.content,
                ),
            }
            handoffs.append(
                _build_handoff(
                    handoff,
                    artifact_payload,
                    source_run_id=run.id,
                )
            )

    return {
        "targetWorkflowId": target_workflow_id,
        "targetStageId": target_stage_id,
        "handoffs": handoffs,
    }


def _source_artifact(snapshot: dict, source_stage_id: str) -> dict | None:
    return next(
        (
            artifact
            for artifact in snapshot["artifacts"]
            if artifact["stageId"] == source_stage_id
        ),
        None,
    )


def _build_handoff(
    handoff: dict,
    artifact: dict,
    *,
    source_run_id: str | None = None,
) -> dict:
    source_artifact_digest = artifact.get("digest") or _source_artifact_digest(
        artifact["content"]
    )
    payload = {
        "id": handoff["id"],
        "label": handoff["label"],
        "sourceWorkflowId": handoff["sourceWorkflowId"],
        "sourceStageId": handoff["sourceStageId"],
        "sourceArtifactVersion": artifact["versionNumber"],
        "sourceArtifactDigest": source_artifact_digest,
        "targetWorkflowId": handoff["targetWorkflowId"],
        "targetStageId": handoff["targetStageId"],
        "targetAgentId": handoff["targetAgentId"],
        "prompt": _build_handoff_prompt(
            handoff,
            artifact["content"],
            source_run_id=source_run_id,
            source_artifact_version=artifact["versionNumber"],
            source_artifact_digest=source_artifact_digest,
        ),
    }
    if source_run_id is not None:
        payload["sourceRunId"] = source_run_id
    summary = artifact.get("summary")
    if isinstance(summary, str) and summary.strip():
        payload["sourceArtifactSummary"] = summary.strip()
    return payload


def _build_handoff_prompt(
    handoff: dict,
    source_artifact: str,
    *,
    source_run_id: str | None = None,
    source_artifact_version: int | None = None,
    source_artifact_digest: str | None = None,
) -> str:
    bounded_artifact = _bounded_source_artifact(source_artifact)
    template_id = handoff.get("promptTemplateId")
    template = HANDOFF_PROMPT_TEMPLATES.get(template_id)
    if template is None:
        raise ValueError(f"未知 handoff promptTemplateId: {template_id}")
    trace_lines = [
        f"来源阶段: {handoff['sourceWorkflowId']}/{handoff['sourceStageId']}",
        f"目标阶段: {handoff['targetWorkflowId']}/{handoff['targetStageId']}",
    ]
    if source_run_id is not None:
        trace_lines.append(f"源 run: {source_run_id}")
    if source_artifact_version is not None:
        trace_lines.append(f"源 artifact version: {source_artifact_version}")
    if source_artifact_digest is not None:
        trace_lines.append(f"源 artifact digest: {source_artifact_digest}")
    return "\n\n".join(
        [
            template.format(**handoff),
            "Handoff 追溯:\n" + "\n".join(f"- {line}" for line in trace_lines),
            bounded_artifact,
        ]
    )


def _bounded_source_artifact(source_artifact: str) -> str:
    content = source_artifact.strip()
    if len(content) <= HANDOFF_CONTEXT_MAX_CHARS:
        return content
    return content[:HANDOFF_CONTEXT_MAX_CHARS].rstrip() + HANDOFF_TRUNCATION_NOTICE


def _validate_workflow_stage(
    workflow_id: str,
    stage_id: str | None = None,
) -> None:
    if workflow_id not in WORKFLOW_STAGES:
        raise ValueError(f"未知 workflowId: {workflow_id}")
    if stage_id is not None and stage_id not in WORKFLOW_STAGES[workflow_id]:
        raise ValueError(f"workflowId 与 stageId 不匹配: {workflow_id}/{stage_id}")


def _source_artifact_digest(content: str) -> str:
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _source_artifact_summary(
    run_id: str,
    stage_id: str,
    content: str,
) -> str:
    summary = AgentContextSummary.query.filter_by(
        run_id=run_id,
        source_type="artifact",
        source_stage_id=stage_id,
        summary_type=CURRENT_ARTIFACT_SUMMARY_TYPE,
    ).first()
    if summary is not None and summary.content.strip():
        return _bounded_source_summary(summary.content)
    return _bounded_source_summary(content)


def _bounded_source_summary(content: str) -> str:
    summary = " ".join(line.strip() for line in content.splitlines() if line.strip())
    if len(summary) <= HANDOFF_SUMMARY_MAX_CHARS:
        return summary
    return summary[:HANDOFF_SUMMARY_MAX_CHARS].rstrip() + "..."
