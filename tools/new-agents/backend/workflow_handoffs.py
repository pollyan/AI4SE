from run_persistence import append_run_message, create_agent_run, get_run_snapshot
from workflow_manifest import get_workflow_handoffs


HANDOFF_CONTEXT_MAX_CHARS = 6000
HANDOFF_TRUNCATION_NOTICE = "\n\n[源产物内容已截断]"


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
        handoffs.append(_build_handoff(handoff, artifact))

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


def _source_artifact(snapshot: dict, source_stage_id: str) -> dict | None:
    return next(
        (
            artifact
            for artifact in snapshot["artifacts"]
            if artifact["stageId"] == source_stage_id
        ),
        None,
    )


def _build_handoff(handoff: dict, artifact: dict) -> dict:
    return {
        "id": handoff["id"],
        "label": handoff["label"],
        "sourceWorkflowId": handoff["sourceWorkflowId"],
        "sourceStageId": handoff["sourceStageId"],
        "sourceArtifactVersion": artifact["versionNumber"],
        "targetWorkflowId": handoff["targetWorkflowId"],
        "targetStageId": handoff["targetStageId"],
        "targetAgentId": handoff["targetAgentId"],
        "prompt": _build_handoff_prompt(handoff, artifact["content"]),
    }


def _build_handoff_prompt(handoff: dict, source_artifact: str) -> str:
    bounded_artifact = _bounded_source_artifact(source_artifact)
    return "\n\n".join(
        [
            (
                "请基于以下 Alex 产出的需求蓝图继续工作。"
                f"来源阶段: {handoff['sourceWorkflowId']}/{handoff['sourceStageId']}。"
                f"目标阶段: {handoff['targetWorkflowId']}/{handoff['targetStageId']}。"
            ),
            bounded_artifact,
        ]
    )


def _bounded_source_artifact(source_artifact: str) -> str:
    content = source_artifact.strip()
    if len(content) <= HANDOFF_CONTEXT_MAX_CHARS:
        return content
    return content[:HANDOFF_CONTEXT_MAX_CHARS].rstrip() + HANDOFF_TRUNCATION_NOTICE
