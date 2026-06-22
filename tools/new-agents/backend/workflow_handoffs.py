from run_persistence import append_run_message, create_agent_run, get_run_snapshot
from workflow_manifest import get_workflow_handoffs

HANDOFF_CONTEXT_MAX_CHARS = 6000
HANDOFF_TRUNCATION_NOTICE = "\n\n[源产物内容已截断]"
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
    context = _build_handoff_context(handoff, artifact)
    return {
        "id": handoff["id"],
        "label": handoff["label"],
        "sourceWorkflowId": handoff["sourceWorkflowId"],
        "sourceStageId": handoff["sourceStageId"],
        "sourceArtifactVersion": artifact["versionNumber"],
        "targetWorkflowId": handoff["targetWorkflowId"],
        "targetStageId": handoff["targetStageId"],
        "targetAgentId": handoff["targetAgentId"],
        "context": context,
        "prompt": _build_handoff_prompt(handoff, artifact, context),
    }


def _build_handoff_prompt(handoff: dict, artifact: dict, context: dict) -> str:
    bounded_artifact = _bounded_source_artifact(artifact["content"])
    template_id = handoff.get("promptTemplateId")
    template = HANDOFF_PROMPT_TEMPLATES.get(template_id)
    if template is None:
        raise ValueError(f"未知 handoff promptTemplateId: {template_id}")
    return "\n\n".join(
        [
            template.format(**handoff),
            _format_handoff_context(handoff, artifact, context),
            bounded_artifact,
        ]
    )


def _bounded_source_artifact(source_artifact: str) -> str:
    content = source_artifact.strip()
    if len(content) <= HANDOFF_CONTEXT_MAX_CHARS:
        return content
    return content[:HANDOFF_CONTEXT_MAX_CHARS].rstrip() + HANDOFF_TRUNCATION_NOTICE


def _build_handoff_context(handoff: dict, artifact: dict) -> dict:
    content = artifact["content"]
    title = _extract_title(content)
    handoff_inputs = _extract_lisa_handoff_inputs(content)
    item_labels = [f"{item['inputType']} {item['id']}" for item in handoff_inputs]
    unconfirmed_items = [
        f"{item['inputType']} {item['id']}: {item['content']}"
        for item in handoff_inputs
        if _is_unconfirmed_status(item["status"])
    ]
    target = f"{handoff['targetWorkflowId']}/{handoff['targetStageId']}"
    target_items = (
        "、".join(item_labels) if item_labels else "未识别到 Lisa handoff 输入"
    )

    return {
        "sourceArtifactTitle": title,
        "sourceArtifactSummary": f"{title}；Lisa handoff 输入 {len(handoff_inputs)} 项",
        "targetInputSummary": f"交给 {target} 使用：{target_items}",
        "unconfirmedItems": unconfirmed_items,
    }


def _format_handoff_context(handoff: dict, artifact: dict, context: dict) -> str:
    lines = [
        "## 接力上下文",
        f"- 来源阶段: {handoff['sourceWorkflowId']}/{handoff['sourceStageId']}",
        f"- 来源版本: v{artifact['versionNumber']}",
        f"- 目标阶段: {handoff['targetWorkflowId']}/{handoff['targetStageId']}",
        f"- 来源摘要: {context['sourceArtifactSummary']}",
        f"- 目标输入: {context['targetInputSummary']}",
        "- 未确认项:",
    ]
    if context["unconfirmedItems"]:
        lines.extend(f"  - {item}" for item in context["unconfirmedItems"])
    else:
        lines.append("  - 无")
    return "\n".join(lines)


def _extract_title(content: str) -> str:
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped.removeprefix("# ").strip()
    return "未命名来源产物"


def _extract_lisa_handoff_inputs(content: str) -> list[dict]:
    lines = content.splitlines()
    section_start = next(
        (
            index
            for index, line in enumerate(lines)
            if line.strip().lstrip("#").strip() == "11. Lisa Handoff 输入"
            or line.strip().lstrip("#").strip() == "Lisa Handoff 输入"
        ),
        None,
    )
    if section_start is None:
        return []

    table_lines = []
    for line in lines[section_start + 1 :]:
        stripped = line.strip()
        if stripped.startswith("#"):
            break
        if stripped.startswith("|") and stripped.endswith("|"):
            table_lines.append(stripped)

    rows = [_parse_markdown_table_row(line) for line in table_lines]
    data_rows = [
        row
        for row in rows[2:]
        if len(row) >= 6 and any(cell.strip("- ") for cell in row)
    ]
    return [
        {
            "inputType": row[0],
            "id": row[1],
            "content": row[2],
            "status": row[5],
        }
        for row in data_rows
    ]


def _parse_markdown_table_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _is_unconfirmed_status(status: str) -> bool:
    return any(keyword in status for keyword in ("待确认", "未确认", "假设"))
