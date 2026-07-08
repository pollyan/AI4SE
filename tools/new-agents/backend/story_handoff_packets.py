import hashlib
import time
from typing import Any

from artifact_data_renderers import StoryBreakdownArtifactData
from models import (
    AgentArtifact,
    AgentArtifactVersion,
    AgentRun,
    AgentStoryHandoffPacket,
    db,
)


STORY_BREAKDOWN_WORKFLOW_ID = "STORY_BREAKDOWN"
STORY_BREAKDOWN_PACKET_STAGE_ID = "SPRINT_PLAN"
FORBIDDEN_PACKET_KEYS = {
    "tasks",
    "filePaths",
    "implementationPlan",
    "testCommands",
    "architecturePlan",
}


def list_story_handoff_candidates(
    run_id: str,
    stage_id: str = STORY_BREAKDOWN_PACKET_STAGE_ID,
) -> dict[str, Any]:
    source = _get_current_handoff_source(run_id, stage_id)
    artifact_data = _validated_handoff_artifact_data(source["version"])
    acceptance_by_story = _acceptance_criteria_by_story(artifact_data)
    return {
        "runId": source["run"].id,
        "workflowId": source["run"].workflow_id,
        "stageId": stage_id,
        "sourceArtifactVersion": source["version"].version_number,
        "sourceArtifactDigest": source["digest"],
        "candidates": [
            _candidate_from_story(story, acceptance_by_story)
            for story in artifact_data.user_stories
        ],
    }


def create_story_handoff_packet(
    run_id: str,
    stage_id: str,
    story_id: str,
) -> dict[str, Any]:
    source = _get_current_handoff_source(run_id, stage_id)
    artifact_data = _validated_handoff_artifact_data(source["version"])
    story = next(
        (
            item
            for item in artifact_data.user_stories
            if item.story_id == story_id
        ),
        None,
    )
    if story is None:
        raise ValueError(f"未知 ready story: {story_id}")

    criteria = [
        item
        for item in artifact_data.acceptance_criteria
        if item.story_id == story.story_id
    ]
    related_dependencies = [
        item
        for item in artifact_data.dependencies
        if story.story_id in item.related_story_ids
    ]
    epic = next(
        (item for item in artifact_data.epics if item.epic_id == story.epic_id),
        None,
    )
    created_at_ms = int(time.time() * 1000)
    packet = {
        "sourceRunId": source["run"].id,
        "sourceWorkflowId": source["run"].workflow_id,
        "sourceStageId": stage_id,
        "sourceArtifactVersion": source["version"].version_number,
        "sourceArtifactDigest": source["digest"],
        "createdAt": created_at_ms,
        "storyId": story.story_id,
        "requirementIds": _requirement_ids_for_story(story, criteria),
        "userStory": story.user_story,
        "acceptanceCriteria": [
            criterion.criterion for criterion in criteria
        ],
        "businessRules": _business_rules_for_story(epic),
        "nonFunctionalNotes": _non_functional_notes_for_story(story),
        "outOfScope": list(artifact_data.input_analysis.constraints),
        "dependencies": [
            dependency.description for dependency in related_dependencies
        ],
        "openQuestions": list(artifact_data.input_analysis.open_questions),
    }
    _assert_no_implementation_fields(packet)

    existing = AgentStoryHandoffPacket.query.filter_by(
        run_id=source["run"].id,
        source_stage_id=stage_id,
        source_artifact_version=source["version"].version_number,
        story_id=story.story_id,
    ).first()
    if existing is None:
        existing = AgentStoryHandoffPacket(
            run_id=source["run"].id,
            source_workflow_id=source["run"].workflow_id,
            source_stage_id=stage_id,
            source_artifact_version=source["version"].version_number,
            source_artifact_digest=source["digest"],
            story_id=story.story_id,
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
    stage_id: str = STORY_BREAKDOWN_PACKET_STAGE_ID,
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
    if stage_id != STORY_BREAKDOWN_PACKET_STAGE_ID:
        raise ValueError("只能从 STORY_BREAKDOWN/SPRINT_PLAN 生成单故事需求包")

    run = db.session.get(AgentRun, run_id)
    if run is None:
        raise ValueError(f"未知 runId: {run_id}")
    if run.workflow_id != STORY_BREAKDOWN_WORKFLOW_ID:
        raise ValueError("只能从 STORY_BREAKDOWN/SPRINT_PLAN 生成单故事需求包")

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
) -> StoryBreakdownArtifactData:
    if version.artifact_data is None:
        raise ValueError("缺少结构化 artifact_data，无法生成单故事需求包")
    return StoryBreakdownArtifactData.model_validate(version.artifact_data)


def _acceptance_criteria_by_story(
    artifact_data: StoryBreakdownArtifactData,
) -> dict[str, list[str]]:
    criteria_by_story: dict[str, list[str]] = {}
    for criterion in artifact_data.acceptance_criteria:
        criteria_by_story.setdefault(criterion.story_id, []).append(
            criterion.criterion_id
        )
    return criteria_by_story


def _candidate_from_story(
    story: Any,
    acceptance_by_story: dict[str, list[str]],
) -> dict[str, Any]:
    return {
        "storyId": story.story_id,
        "title": story.title,
        "requirementIds": [
            story.epic_id,
            *acceptance_by_story.get(story.story_id, []),
        ],
        "userValue": story.user_story,
        "readyReason": (
            f"状态：{story.status}；"
            f"可测试性：{story.testability}；"
            f"Sprint：{story.sprint}"
        ),
    }


def _requirement_ids_for_story(story: Any, criteria: list[Any]) -> list[str]:
    return [
        story.epic_id,
        *[criterion.criterion_id for criterion in criteria],
    ]


def _business_rules_for_story(epic: Any | None) -> list[str]:
    if epic is None:
        return []
    return [
        f"Epic：{epic.name}",
        f"价值目标：{epic.value_goal}",
        f"范围：{epic.scope}",
    ]


def _non_functional_notes_for_story(story: Any) -> list[str]:
    return [
        f"优先级：{story.priority}",
        f"故事点：{story.story_points}",
        f"可测试性：{story.testability}",
        f"计划迭代：{story.sprint}",
    ]


def _assert_no_implementation_fields(packet: dict[str, Any]) -> None:
    leaked_keys = sorted(FORBIDDEN_PACKET_KEYS.intersection(packet))
    if leaked_keys:
        raise ValueError(
            "单故事需求包不能包含实现计划字段: " + ", ".join(leaked_keys)
        )


def _source_artifact_digest(content: str) -> str:
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"
