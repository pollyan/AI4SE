import re
from collections.abc import Mapping
from typing import Any

from agent_contracts import AgentTurnOutput


STAGE_READINESS_BLOCKED_WARNING = "stage_readiness_blocked"

HIGH_PRIORITY_VALUES = {"P0", "P1"}
BLOCKING_VALUES = {"阻断", "是", "true", "yes"}
CLOSED_CLARIFICATION_STATUSES = {"已确认", "已假设"}

CLARIFICATION_TABLE_PATTERN = re.compile(
    r"^\|\s*(Q-[^|]+)\|\s*([^|]+)\|\s*(P[01])\s*\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]*)\|\s*([^|]+)\|\s*([^|]+)\|",
    re.MULTILINE,
)


def apply_stage_readiness_gate(
    output: AgentTurnOutput,
    *,
    workflow_id: str,
    current_stage_id: str,
) -> AgentTurnOutput:
    if workflow_id != "TEST_DESIGN" or current_stage_id != "CLARIFY":
        return output
    if output.stage_action is None:
        return output
    markdown = output.artifact_update.markdown or ""
    blocking_findings = find_blocking_clarify_questions(
        markdown,
        artifact_data=output.artifact_data,
    )
    if not blocking_findings:
        return output

    warnings = list(output.warnings)
    if STAGE_READINESS_BLOCKED_WARNING not in warnings:
        warnings.append(STAGE_READINESS_BLOCKED_WARNING)

    return output.model_copy(
        update={
            "chat": append_stage_readiness_blocked_message(
                output.chat,
                blocking_findings,
            ),
            "stage_action": None,
            "warnings": warnings,
        }
    )


def find_blocking_clarify_questions(
    markdown: str,
    *,
    artifact_data: Mapping[str, Any] | None = None,
) -> list[str]:
    structured_findings = (
        _find_blocking_structured_clarify_questions(artifact_data)
        if artifact_data is not None
        else None
    )
    if structured_findings is not None:
        return structured_findings

    # Legacy direct AgentTurnOutput values can contain partial metadata rather
    # than a complete clarification list. In that explicit compatibility path,
    # the rendered document remains the available source for the gate.
    findings: list[str] = []
    for match in CLARIFICATION_TABLE_PATTERN.finditer(markdown):
        question_id = _clean_cell(match.group(1))
        question = _clean_cell(match.group(2))
        priority = _clean_cell(match.group(3)).upper()
        blocking = _clean_cell(match.group(4))
        status = _clean_cell(match.group(8))
        finding = _build_blocking_finding(
            question_id=question_id,
            question=question,
            priority=priority,
            blocking=blocking,
            status=status,
        )
        if finding is not None:
            findings.append(finding)
    return findings


def _find_blocking_structured_clarify_questions(
    artifact_data: Mapping[str, Any],
) -> list[str] | None:
    questions = artifact_data.get("clarification_questions")
    if not isinstance(questions, list) or not questions:
        return None

    findings: list[str] = []
    for question_data in questions:
        if not isinstance(question_data, Mapping):
            return None
        question_id = _structured_question_text(question_data, "question_id")
        question = _structured_question_text(question_data, "question")
        priority = _structured_question_text(question_data, "priority")
        blocking = _structured_question_text(question_data, "blocking")
        status = _structured_question_text(question_data, "status")
        if None in (question_id, question, priority, blocking, status):
            return None
        finding = _build_blocking_finding(
            question_id=question_id,
            question=question,
            priority=priority.upper(),
            blocking=blocking,
            status=status,
        )
        if finding is not None:
            findings.append(finding)
    return findings


def _structured_question_text(
    question_data: Mapping[str, Any],
    field_name: str,
) -> str | None:
    value = question_data.get(field_name)
    if not isinstance(value, str) or not value.strip():
        return None
    return _clean_cell(value)


def _build_blocking_finding(
    *,
    question_id: str,
    question: str,
    priority: str,
    blocking: str,
    status: str,
) -> str | None:
    if not (
        priority in HIGH_PRIORITY_VALUES
        and _is_blocking_value(blocking)
        and _is_open_status(status)
    ):
        return None
    return f"{question_id}（{priority} 阻断，状态：{status}）：{question}"


def append_stage_readiness_blocked_message(
    chat: str,
    blocking_findings: list[str],
) -> str:
    if STAGE_READINESS_BLOCKED_WARNING in chat:
        return chat
    finding_lines = "\n".join(f"- {finding}" for finding in blocking_findings)
    return (
        f"{chat.rstrip()}\n\n"
        "阶段成熟度门禁判断：当前还不能进入下一阶段。"
        "以下高优先级阻断问题仍需用户确认或补充后，才能进入策略制定：\n"
        f"{finding_lines}"
    )


def _clean_cell(value: str) -> str:
    return value.strip().strip("`").strip()


def _is_blocking_value(value: str) -> bool:
    normalized = value.strip().lower()
    return value.strip() in BLOCKING_VALUES or normalized in BLOCKING_VALUES


def _is_open_status(value: str) -> bool:
    return _clean_cell(value) not in CLOSED_CLARIFICATION_STATUSES
