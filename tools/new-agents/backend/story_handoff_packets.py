import hashlib
import time
from typing import Any

from artifact_data_renderers import UserStoryHandoffArtifactData
from models import (
    AgentArtifact,
    AgentArtifactVersion,
    AgentRun,
    AgentStoryHandoffPacket,
    db,
)


USER_STORY_WORKFLOW_ID = "USER_STORY_BREAKDOWN"
USER_STORY_HANDOFF_STAGE_ID = "HANDOFF"
FORBIDDEN_PACKET_KEYS = {
    "tasks",
    "filePaths",
    "implementationPlan",
    "testCommands",
    "architecturePlan",
}


def list_story_handoff_candidates(
    run_id: str,
    stage_id: str = USER_STORY_HANDOFF_STAGE_ID,
) -> dict[str, Any]:
    source = _get_current_handoff_source(run_id, stage_id)
    artifact_data = _validated_handoff_artifact_data(source["version"])
    return {
        "runId": source["run"].id,
        "workflowId": source["run"].workflow_id,
        "stageId": stage_id,
        "sourceArtifactVersion": source["version"].version_number,
        "sourceArtifactDigest": source["digest"],
        "candidates": [
            {
                "storyId": item.story_id,
                "title": item.title,
                "requirementIds": item.requirement_ids,
                "userValue": item.user_value,
                "readyReason": item.ready_reason,
            }
            for item in artifact_data.ready_story_overview
        ],
    }


def create_story_handoff_packet(
    run_id: str,
    stage_id: str,
    story_id: str,
) -> dict[str, Any]:
    source = _get_current_handoff_source(run_id, stage_id)
    artifact_data = _validated_handoff_artifact_data(source["version"])
    packet_source = next(
        (
            item
            for item in artifact_data.single_story_packets
            if item.story_id == story_id
        ),
        None,
    )
    if packet_source is None:
        raise ValueError(f"未知 ready story: {story_id}")

    created_at_ms = int(time.time() * 1000)
    packet = {
        "sourceRunId": source["run"].id,
        "sourceWorkflowId": source["run"].workflow_id,
        "sourceStageId": stage_id,
        "sourceArtifactVersion": source["version"].version_number,
        "sourceArtifactDigest": source["digest"],
        "createdAt": created_at_ms,
        "storyId": packet_source.story_id,
        "requirementIds": packet_source.requirement_ids,
        "userStory": packet_source.user_story,
        "acceptanceCriteria": packet_source.acceptance_criteria,
        "businessRules": packet_source.business_rules,
        "nonFunctionalNotes": packet_source.non_functional_notes,
        "outOfScope": packet_source.out_of_scope,
        "dependencies": packet_source.dependencies,
        "openQuestions": packet_source.open_questions,
    }
    _assert_no_implementation_fields(packet)

    existing = AgentStoryHandoffPacket.query.filter_by(
        run_id=source["run"].id,
        source_stage_id=stage_id,
        source_artifact_version=source["version"].version_number,
        story_id=packet_source.story_id,
    ).first()
    if existing is None:
        existing = AgentStoryHandoffPacket(
            run_id=source["run"].id,
            source_workflow_id=source["run"].workflow_id,
            source_stage_id=stage_id,
            source_artifact_version=source["version"].version_number,
            source_artifact_digest=source["digest"],
            story_id=packet_source.story_id,
            packet_json=packet,
            created_at_ms=created_at_ms,
        )
        db.session.add(existing)
    else:
        existing.source_artifact_digest = source["digest"]
        existing.packet_json = packet
        existing.created_at_ms = created_at_ms
    db.session.commit()
    return packet


def list_story_handoff_packets(
    run_id: str,
    stage_id: str = USER_STORY_HANDOFF_STAGE_ID,
) -> dict[str, Any]:
    source = _get_current_handoff_source(run_id, stage_id)
    packets = (
        AgentStoryHandoffPacket.query.filter_by(
            run_id=source["run"].id,
            source_stage_id=stage_id,
        )
        .order_by(
            AgentStoryHandoffPacket.created_at_ms.desc(),
            AgentStoryHandoffPacket.id.desc(),
        )
        .all()
    )
    return {
        "runId": source["run"].id,
        "workflowId": source["run"].workflow_id,
        "stageId": stage_id,
        "sourceArtifactVersion": source["version"].version_number,
        "sourceArtifactDigest": source["digest"],
        "packets": [
            _packet_snapshot(packet, source["version"].version_number, source["digest"])
            for packet in packets
        ],
    }


def _packet_snapshot(
    packet: AgentStoryHandoffPacket,
    current_source_artifact_version: int,
    current_source_artifact_digest: str,
) -> dict[str, Any]:
    is_stale = (
        packet.source_artifact_version != current_source_artifact_version
        or packet.source_artifact_digest != current_source_artifact_digest
    )
    return {
        "id": str(packet.id),
        "storyId": packet.story_id,
        "createdAt": packet.created_at_ms,
        "isStale": is_stale,
        "currentSourceArtifactVersion": current_source_artifact_version,
        "currentSourceArtifactDigest": current_source_artifact_digest,
        "packet": packet.packet_json,
    }


def _get_current_handoff_source(run_id: str, stage_id: str) -> dict[str, Any]:
    if stage_id != USER_STORY_HANDOFF_STAGE_ID:
        raise ValueError("只能从 USER_STORY_BREAKDOWN/HANDOFF 生成单故事需求包")

    run = db.session.get(AgentRun, run_id)
    if run is None:
        raise ValueError(f"未知 runId: {run_id}")
    if run.workflow_id != USER_STORY_WORKFLOW_ID:
        raise ValueError("只能从 USER_STORY_BREAKDOWN/HANDOFF 生成单故事需求包")

    artifact = AgentArtifact.query.filter_by(run_id=run_id, stage_id=stage_id).first()
    if artifact is None or artifact.current_version_id is None:
        raise ValueError("当前阶段缺少可生成需求包的产出物")
    version = db.session.get(AgentArtifactVersion, artifact.current_version_id)
    if version is None:
        raise ValueError("当前阶段产出物版本不存在")
    return {
        "run": run,
        "artifact": artifact,
        "version": version,
        "digest": _source_artifact_digest(version.content),
    }


def _validated_handoff_artifact_data(
    version: AgentArtifactVersion,
) -> UserStoryHandoffArtifactData:
    if version.artifact_data is None:
        raise ValueError("缺少结构化 artifact_data，无法生成单故事需求包")
    return UserStoryHandoffArtifactData.model_validate(version.artifact_data)


def _assert_no_implementation_fields(packet: dict[str, Any]) -> None:
    leaked_keys = sorted(FORBIDDEN_PACKET_KEYS.intersection(packet))
    if leaked_keys:
        raise ValueError(
            "单故事需求包不能包含实现计划字段: " + ", ".join(leaked_keys)
        )


def _source_artifact_digest(content: str) -> str:
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"
