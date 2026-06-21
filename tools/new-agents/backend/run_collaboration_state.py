import json
from dataclasses import dataclass

from agent_contracts import WORKFLOW_STAGES
from models import (
    AgentArtifactAuditEvent,
    AgentArtifactComment,
    AgentArtifactSectionLock,
)


COMMENT_STATUSES = {"open", "resolved"}


@dataclass
class CollaborationStateModels:
    comments: list[AgentArtifactComment]
    section_locks: list[AgentArtifactSectionLock]
    audit_event: AgentArtifactAuditEvent


def _validate_workflow_stage(workflow_id: str, stage_id: str) -> None:
    workflow_stages = WORKFLOW_STAGES.get(workflow_id)
    if workflow_stages is None:
        raise ValueError(f"未知 workflowId: {workflow_id}")
    if stage_id not in workflow_stages:
        raise ValueError(f"workflowId 与 stageId 不匹配: {workflow_id}/{stage_id}")


def _read_collaboration_list(patch: dict, field_name: str) -> list:
    value = patch.get(field_name)
    if not isinstance(value, list):
        raise ValueError(f"{field_name} 必须是数组")
    return value


def _read_collaboration_string(item: dict, field_name: str) -> str:
    value = item.get(field_name)
    if not isinstance(value, str):
        raise ValueError(f"{field_name} 必须是字符串")
    value = value.strip()
    if not value:
        raise ValueError(f"{field_name} 不能为空")
    return value


def _read_collaboration_integer(item: dict, field_name: str) -> int:
    value = item.get(field_name)
    if not isinstance(value, int):
        raise ValueError(f"{field_name} 必须是整数")
    return value


def _read_optional_collaboration_string(item: dict, field_name: str) -> str | None:
    value = item.get(field_name)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field_name} 必须是字符串")
    value = value.strip()
    return value or None


def _read_optional_collaboration_integer(item: dict, field_name: str) -> int | None:
    value = item.get(field_name)
    if value is None:
        return None
    if not isinstance(value, int):
        raise ValueError(f"{field_name} 必须是整数")
    return value


def _read_comment_status(item: dict) -> str:
    value = item.get("status", "open")
    if not isinstance(value, str) or value not in COMMENT_STATUSES:
        raise ValueError("status 必须是 open 或 resolved")
    return value


def _read_comment_replies(item: dict) -> list[dict]:
    value = item.get("replies", [])
    if not isinstance(value, list):
        raise ValueError("replies 必须是数组")

    replies: list[dict] = []
    for reply in value:
        if not isinstance(reply, dict):
            raise ValueError("replies 条目必须是对象")
        replies.append(
            {
                "id": _read_collaboration_string(reply, "id"),
                "content": _read_collaboration_string(reply, "content"),
                "createdAt": _read_collaboration_integer(reply, "createdAt"),
            }
        )
    return replies


def build_collaboration_state_models(
    *,
    run_id: str,
    workflow_id: str,
    current_stage_id: str,
    patch: dict,
    created_at_ms: int,
) -> CollaborationStateModels:
    if not isinstance(patch, dict):
        raise ValueError("请求体必须是对象")

    allowed_fields = {"comments", "sectionLocks"}
    unexpected_fields = set(patch.keys()) - allowed_fields
    if unexpected_fields:
        raise ValueError(f"不支持的字段: {', '.join(sorted(unexpected_fields))}")

    missing_fields = allowed_fields - set(patch.keys())
    if missing_fields:
        raise ValueError(f"缺少字段: {', '.join(sorted(missing_fields))}")

    comments_payload = _read_collaboration_list(patch, "comments")
    locks_payload = _read_collaboration_list(patch, "sectionLocks")

    comments: list[AgentArtifactComment] = []
    for item in comments_payload:
        if not isinstance(item, dict):
            raise ValueError("comments 条目必须是对象")
        stage_id = _read_collaboration_string(item, "stageId")
        _validate_workflow_stage(workflow_id, stage_id)
        replies = _read_comment_replies(item)
        comments.append(
            AgentArtifactComment(
                run_id=run_id,
                client_id=_read_collaboration_string(item, "id"),
                stage_id=stage_id,
                content=_read_collaboration_string(item, "content"),
                artifact_excerpt=_read_collaboration_string(item, "artifactExcerpt"),
                anchor_text=_read_optional_collaboration_string(item, "anchorText"),
                created_at_ms=_read_collaboration_integer(item, "createdAt"),
                status=_read_comment_status(item),
                resolved_at_ms=_read_optional_collaboration_integer(item, "resolvedAt"),
                replies_json=json.dumps(replies, ensure_ascii=False),
            )
        )

    section_locks: list[AgentArtifactSectionLock] = []
    for item in locks_payload:
        if not isinstance(item, dict):
            raise ValueError("sectionLocks 条目必须是对象")
        stage_id = _read_collaboration_string(item, "stageId")
        _validate_workflow_stage(workflow_id, stage_id)
        section_locks.append(
            AgentArtifactSectionLock(
                run_id=run_id,
                client_id=_read_collaboration_string(item, "id"),
                stage_id=stage_id,
                heading=_read_collaboration_string(item, "heading"),
                section_anchor=_read_optional_collaboration_string(item, "sectionAnchor"),
                content=_read_collaboration_string(item, "content"),
                created_at_ms=_read_collaboration_integer(item, "createdAt"),
            )
        )

    audit_event = AgentArtifactAuditEvent(
        run_id=run_id,
        stage_id=current_stage_id,
        event_type="collaboration_updated",
        summary=(
            f"更新了 {current_stage_id} 阶段协作状态："
            f"{len(comments_payload)} 条批注，{len(locks_payload)} 个章节锁"
        ),
        created_at_ms=created_at_ms,
    )
    return CollaborationStateModels(
        comments=comments,
        section_locks=section_locks,
        audit_event=audit_event,
    )


def comment_snapshot(comment: AgentArtifactComment) -> dict:
    try:
        replies = json.loads(comment.replies_json or "[]")
    except json.JSONDecodeError:
        replies = []
    return {
        "id": comment.client_id,
        "stageId": comment.stage_id,
        "content": comment.content,
        "artifactExcerpt": comment.artifact_excerpt,
        "anchorText": comment.anchor_text,
        "createdAt": comment.created_at_ms,
        "status": comment.status,
        "resolvedAt": comment.resolved_at_ms,
        "replies": replies if isinstance(replies, list) else [],
    }


def section_lock_snapshot(lock: AgentArtifactSectionLock) -> dict:
    return {
        "id": lock.client_id,
        "stageId": lock.stage_id,
        "heading": lock.heading,
        "sectionAnchor": lock.section_anchor,
        "content": lock.content,
        "createdAt": lock.created_at_ms,
    }


def audit_event_snapshot(event: AgentArtifactAuditEvent) -> dict:
    return {
        "stageId": event.stage_id,
        "eventType": event.event_type,
        "summary": event.summary,
        "createdAt": event.created_at_ms,
    }
