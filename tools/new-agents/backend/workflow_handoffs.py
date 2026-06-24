from run_persistence import append_run_message, create_agent_run, get_run_snapshot
from workflow_manifest import get_workflow_handoffs


HANDOFF_CONTEXT_MAX_CHARS = 6000
HANDOFF_TRUNCATION_NOTICE = "\n\n[源产物内容已截断]"
UNCONFIRMED_MARKERS = ("待确认", "未确认", "待澄清", "未验证", "开放问题")
HANDOFF_PROMPT_TEMPLATES = {
    "source-artifact-handoff": (
        "请基于以下上游产物继续工作。"
        "来源阶段: {sourceWorkflowId}/{sourceStageId}。"
        "目标阶段: {targetWorkflowId}/{targetStageId}。"
    ),
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
    source_summary = _build_source_summary(artifact["content"])
    unconfirmed_items = _extract_unconfirmed_items(artifact["content"])
    target_input_checklist = _build_target_input_checklist(
        handoff,
        artifact["versionNumber"],
        unconfirmed_items,
    )
    return {
        "id": handoff["id"],
        "label": handoff["label"],
        "sourceWorkflowId": handoff["sourceWorkflowId"],
        "sourceStageId": handoff["sourceStageId"],
        "sourceArtifactVersion": artifact["versionNumber"],
        "sourceSummary": source_summary,
        "unconfirmedItems": unconfirmed_items,
        "targetInputChecklist": target_input_checklist,
        "targetWorkflowId": handoff["targetWorkflowId"],
        "targetStageId": handoff["targetStageId"],
        "targetAgentId": handoff["targetAgentId"],
        "prompt": _build_handoff_prompt(
            handoff,
            artifact["content"],
            artifact["versionNumber"],
            source_summary,
            unconfirmed_items,
            target_input_checklist,
        ),
    }


def _build_handoff_prompt(
    handoff: dict,
    source_artifact: str,
    source_artifact_version: int,
    source_summary: str,
    unconfirmed_items: list[str],
    target_input_checklist: list[str],
) -> str:
    bounded_artifact = _bounded_source_artifact(source_artifact)
    template_id = handoff.get("promptTemplateId")
    template = HANDOFF_PROMPT_TEMPLATES.get(template_id)
    if template is None:
        raise ValueError(f"未知 handoff promptTemplateId: {template_id}")
    source_version = (
        f"{handoff['sourceWorkflowId']}/{handoff['sourceStageId']} "
        f"v{source_artifact_version}"
    )
    return "\n\n".join(
        [
            template.format(**handoff),
            f"来源版本: {source_version}",
            "关键摘要:\n" + _format_bullets([source_summary]),
            "未确认项:\n" + _format_bullets(unconfirmed_items or ["无"]),
            "目标工作流输入:\n" + _format_bullets(target_input_checklist),
            "源产物内容:",
            bounded_artifact,
        ]
    )


def _bounded_source_artifact(source_artifact: str) -> str:
    content = source_artifact.strip()
    if len(content) <= HANDOFF_CONTEXT_MAX_CHARS:
        return content
    return content[:HANDOFF_CONTEXT_MAX_CHARS].rstrip() + HANDOFF_TRUNCATION_NOTICE


def _build_source_summary(source_artifact: str) -> str:
    title = _first_markdown_heading(source_artifact)
    body_line = _first_summary_body_line(source_artifact)
    if title and body_line:
        return f"{title}: {body_line}"
    if title:
        return title
    if body_line:
        return body_line
    return "源产物未提供可提取摘要"


def _first_markdown_heading(source_artifact: str) -> str:
    for line in source_artifact.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
    return ""


def _first_summary_body_line(source_artifact: str) -> str:
    in_fence = False
    for line in source_artifact.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or not stripped:
            continue
        if stripped.startswith("#") or stripped.startswith("|"):
            continue
        if stripped.startswith("- ["):
            continue
        if stripped.startswith("- "):
            return stripped[2:].strip()
        return stripped
    return ""


def _extract_unconfirmed_items(source_artifact: str) -> list[str]:
    items = []
    for line in source_artifact.splitlines():
        stripped = line.strip()
        if not stripped or not any(marker in stripped for marker in UNCONFIRMED_MARKERS):
            continue
        if _is_table_separator(stripped) or ("状态" in stripped and "内容" in stripped):
            continue
        item = _format_unconfirmed_item(stripped)
        if item and item not in items:
            items.append(item)
    return items[:5]


def _format_unconfirmed_item(line: str) -> str:
    if line.startswith("|"):
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        cells = [cell for cell in cells if cell]
        if len(cells) >= 3:
            item_type, item_id, content = cells[0], cells[1], cells[2]
            return f"{item_type} {item_id}: {content}"
    return line.lstrip("- ").strip()


def _is_table_separator(line: str) -> bool:
    compact = line.replace("|", "").replace("-", "").replace(":", "").strip()
    return compact == ""


def _build_target_input_checklist(
    handoff: dict,
    source_artifact_version: int,
    unconfirmed_items: list[str],
) -> list[str]:
    source_version = (
        f"{handoff['sourceWorkflowId']}/{handoff['sourceStageId']} "
        f"v{source_artifact_version}"
    )
    target_stage = f"{handoff['targetWorkflowId']}/{handoff['targetStageId']}"
    unconfirmed_step = (
        f"处理 {len(unconfirmed_items)} 个未确认项后再进入目标产物生成"
        if unconfirmed_items
        else "确认没有遗留未确认项后进入目标产物生成"
    )
    return [
        f"复核来源版本 {source_version}",
        f"确认目标阶段 {target_stage} 所需的需求、验收标准和约束均已覆盖",
        unconfirmed_step,
    ]


def _format_bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)
