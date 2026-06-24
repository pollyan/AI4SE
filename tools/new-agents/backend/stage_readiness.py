import re

from agent_contracts import AgentTurnOutput


STAGE_READINESS_BLOCKED_WARNING = "stage_readiness_blocked"

HIGH_PRIORITY_VALUES = {"P0", "P1"}
BLOCKING_VALUES = {"阻断", "是", "true", "yes"}
OPEN_STATUS_KEYWORDS = (
    "待确认",
    "未确认",
    "需确认",
    "需补充",
    "待补充",
    "AI 假设",
    "假设",
)

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
    blocking_findings = find_blocking_clarify_questions(markdown)
    if not blocking_findings:
        return output

    warnings = list(output.warnings)
    if STAGE_READINESS_BLOCKED_WARNING not in warnings:
        warnings.append(STAGE_READINESS_BLOCKED_WARNING)

    return AgentTurnOutput.model_validate({
        "chat": append_stage_readiness_blocked_message(
            output.chat,
            blocking_findings,
        ),
        "artifact_update": output.artifact_update.model_dump(mode="json"),
        "stage_action": None,
        "warnings": warnings,
    })


def find_blocking_clarify_questions(markdown: str) -> list[str]:
    findings: list[str] = []
    for match in CLARIFICATION_TABLE_PATTERN.finditer(markdown):
        question_id = _clean_cell(match.group(1))
        question = _clean_cell(match.group(2))
        priority = _clean_cell(match.group(3)).upper()
        blocking = _clean_cell(match.group(4))
        status = _clean_cell(match.group(8))
        if (
            priority in HIGH_PRIORITY_VALUES
            and _is_blocking_value(blocking)
            and _is_open_status(status)
        ):
            findings.append(
                f"{question_id}（{priority} 阻断，状态：{status}）：{question}"
            )
    return findings


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
    return any(keyword in value for keyword in OPEN_STATUS_KEYWORDS)
