import re

from run_persistence import append_run_message, create_agent_run, get_run_snapshot
from workflow_manifest import get_workflow_handoffs


HANDOFF_CONTEXT_MAX_CHARS = 6000
HANDOFF_SUMMARY_MAX_CHARS = 180
HANDOFF_UNRESOLVED_ITEM_LIMIT = 5
HANDOFF_UNRESOLVED_ITEM_MAX_CHARS = 140
HANDOFF_TRUNCATION_NOTICE = "\n\n[源产物内容已截断]"
HANDOFF_PROMPT_TEMPLATES = {
    "source-artifact-handoff": (
        "请基于以下上游产物继续工作。\n"
        "来源版本: {sourceWorkflowId}/{sourceStageId} v{sourceArtifactVersion}\n"
        "目标阶段: {targetWorkflowId}/{targetStageId}\n"
        "关键摘要: {sourceArtifactSummary}\n"
        "目标用途: {targetInputSummary}\n"
        "未确认项:\n{unresolvedItemsText}"
    ),
}
CONFIRMED_STATUS_VALUES = ("已确认", "已补充", "已解决", "已处置", "可用", "完成")
UNRESOLVED_SECTION_TERMS = ("待确认", "待澄清", "未确认", "待补充", "开放问题", "缺失信息")
RISK_SECTION_TERMS = ("风险", "依赖")


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
    source_artifact_summary = _build_source_artifact_summary(artifact["content"])
    unresolved_items = _extract_unresolved_items(artifact["content"])
    target_input_summary = _build_target_input_summary(
        handoff,
        artifact["versionNumber"],
    )
    return {
        "id": handoff["id"],
        "label": handoff["label"],
        "sourceWorkflowId": handoff["sourceWorkflowId"],
        "sourceStageId": handoff["sourceStageId"],
        "sourceArtifactVersion": artifact["versionNumber"],
        "sourceArtifactSummary": source_artifact_summary,
        "unresolvedItems": unresolved_items,
        "targetInputSummary": target_input_summary,
        "targetWorkflowId": handoff["targetWorkflowId"],
        "targetStageId": handoff["targetStageId"],
        "targetAgentId": handoff["targetAgentId"],
        "prompt": _build_handoff_prompt(
            handoff,
            artifact["content"],
            artifact["versionNumber"],
            source_artifact_summary,
            unresolved_items,
            target_input_summary,
        ),
    }


def _build_handoff_prompt(
    handoff: dict,
    source_artifact: str,
    source_artifact_version: int,
    source_artifact_summary: str,
    unresolved_items: list[str],
    target_input_summary: str,
) -> str:
    bounded_artifact = _bounded_source_artifact(source_artifact)
    template_id = handoff.get("promptTemplateId")
    template = HANDOFF_PROMPT_TEMPLATES.get(template_id)
    if template is None:
        raise ValueError(f"未知 handoff promptTemplateId: {template_id}")
    unresolved_items_text = (
        "\n".join(f"- {item}" for item in unresolved_items)
        if unresolved_items
        else "- 暂未发现待确认项。"
    )
    return "\n\n".join(
        [
            template.format(
                **handoff,
                sourceArtifactVersion=source_artifact_version,
                sourceArtifactSummary=source_artifact_summary,
                targetInputSummary=target_input_summary,
                unresolvedItemsText=unresolved_items_text,
            ),
            bounded_artifact,
        ]
    )


def _bounded_source_artifact(source_artifact: str) -> str:
    content = source_artifact.strip()
    if len(content) <= HANDOFF_CONTEXT_MAX_CHARS:
        return content
    return content[:HANDOFF_CONTEXT_MAX_CHARS].rstrip() + HANDOFF_TRUNCATION_NOTICE


def _build_target_input_summary(handoff: dict, source_artifact_version: int) -> str:
    return (
        f"将 {handoff['sourceWorkflowId']}/{handoff['sourceStageId']} "
        f"v{source_artifact_version} 作为 "
        f"{handoff['targetWorkflowId']}/{handoff['targetStageId']} 的启动输入，"
        "重点用于 Lisa 继续测试设计或需求评审。"
    )


def _build_source_artifact_summary(source_artifact: str) -> str:
    title = ""
    first_body_line = ""
    in_fence = False

    for raw_line in source_artifact.splitlines():
        line = raw_line.strip()
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or not line:
            continue
        if not title and line.startswith("#"):
            title = _clean_markdown_text(line.lstrip("#").strip())
            continue
        if (
            not first_body_line
            and not line.startswith("#")
            and not line.startswith("|")
            and not line.startswith("-")
            and not line.startswith("*")
        ):
            first_body_line = _clean_markdown_text(line)
        if title and first_body_line:
            break

    summary_parts = [part for part in (title, first_body_line) if part]
    if not summary_parts:
        return "来源产物已生成，可作为下游工作流输入。"
    return _truncate_text("；".join(summary_parts), HANDOFF_SUMMARY_MAX_CHARS)


def _extract_unresolved_items(source_artifact: str) -> list[str]:
    items: list[str] = []
    current_heading = ""
    in_fence = False
    current_table_header: list[str] | None = None

    for raw_line in source_artifact.splitlines():
        line = raw_line.strip()
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        heading_match = re.match(r"^#{1,6}\s+(.+)$", line)
        if heading_match:
            current_heading = _clean_markdown_text(heading_match.group(1))
            current_table_header = None
            continue
        if not line:
            current_table_header = None
            continue

        if line.startswith("|") and line.endswith("|"):
            cells = _parse_markdown_table_row(line)
            if _is_markdown_separator_row(cells):
                continue
            if current_table_header is None:
                current_table_header = cells
                continue
            item = _extract_unresolved_table_item(
                current_heading,
                current_table_header,
                cells,
            )
            if item:
                _append_unique_item(items, item)
            continue

        current_table_header = None
        if line.startswith(("- ", "* ", "+ ")):
            if _is_unresolved_section(current_heading):
                _append_unique_item(items, line[2:].strip())

    return items[:HANDOFF_UNRESOLVED_ITEM_LIMIT]


def _extract_unresolved_table_item(
    heading: str,
    headers: list[str],
    cells: list[str],
) -> str | None:
    if not _is_unresolved_section(heading) and not _is_risk_section(heading):
        return None
    row = dict(zip(headers, cells, strict=False))
    status = _find_first_value(row, ("状态", "处理状态", "确认状态"))
    if status and any(value in status for value in CONFIRMED_STATUS_VALUES):
        return None
    if _is_risk_section(heading):
        value = _find_first_value(row, ("风险", "风险描述", "问题", "内容", "待确认事项"))
    else:
        value = _find_first_value(row, ("待确认事项", "待澄清问题", "问题", "内容", "风险描述", "风险"))
    return value


def _is_unresolved_section(heading: str) -> bool:
    return any(term in heading for term in UNRESOLVED_SECTION_TERMS)


def _is_risk_section(heading: str) -> bool:
    return any(term in heading for term in RISK_SECTION_TERMS)


def _find_first_value(row: dict[str, str], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = row.get(key)
        if value:
            return value
    return None


def _append_unique_item(items: list[str], item: str) -> None:
    cleaned = _truncate_text(_clean_markdown_text(item), HANDOFF_UNRESOLVED_ITEM_MAX_CHARS)
    if cleaned and cleaned not in items:
        items.append(cleaned)


def _parse_markdown_table_row(line: str) -> list[str]:
    return [_clean_markdown_text(cell.strip()) for cell in line.strip("|").split("|")]


def _is_markdown_separator_row(cells: list[str]) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in cells)


def _clean_markdown_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("**", "").replace("`", "")).strip()


def _truncate_text(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"
