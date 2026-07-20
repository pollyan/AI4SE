from collections.abc import Iterable
from dataclasses import dataclass

from context_summary_format import (
    CURRENT_ARTIFACT_SUMMARY_TYPE,
    DECISION_SUMMARY_TYPE,
    STAGE_CONCLUSION_SUMMARY_TYPE,
    USER_SUPPLEMENT_SUMMARY_TYPE,
    build_artifact_summary_content,
)
from run_persistence import get_run_snapshot

DEFAULT_CONTEXT_MAX_CHARS = 12000
CONTEXT_TRUNCATED_WARNING = "context_truncated"
TRUNCATION_NOTICE = "⚠️ [上下文因长度限制已截断，仅保留最近的可用对话。]"
ARTIFACT_SUMMARY_HEADING = "[已保存阶段产物摘要]"
SUMMARY_SOURCE_ARTIFACT = "artifact"
SUMMARY_SOURCE_USER_INPUT = "user_input"
USER_SUPPLEMENT_HEADING = "[已记录用户补充]"
STAGE_CONCLUSION_HEADING = "[已记录阶段结论]"
DECISION_HEADING = "[已记录关键决策]"
LOCKED_ARTIFACT_SECTIONS_HEADING = "[已锁定产物章节]"


@dataclass(frozen=True)
class RunContext:
    prompt: str
    warnings: list[str]


def _is_assistant_control_feedback(role: str, content: str) -> bool:
    return role == "assistant" and (
        content.lstrip().startswith("**Error:**")
        or content.lstrip().startswith("*(已停止生成)*")
        or content.lstrip().startswith("⚠️ **模型配置或供应商异常**")
        or content.lstrip().startswith("⚠️ **模型额度或限流异常**")
        or content.lstrip().startswith("⚠️ **模型调用未完成**")
        or content.lstrip().startswith("⚠️ **本轮生成失败**")
        or content.lstrip().startswith("⚠️ **结构化输出生成失败**")
    )


def _format_message(role: str, content: str) -> str | None:
    if _is_assistant_control_feedback(role, content):
        return None
    role_label = "用户" if role == "user" else "助手"
    return f"[{role_label}]\n{content}"


def _format_artifact_summary(stage_id: str, content: str) -> str | None:
    if not content.strip():
        return None
    return f"[阶段产物: {stage_id}]\n{content}"


def _format_structured_summary(label: str, stage_id: str, content: str) -> str | None:
    if not content.strip():
        return None
    return f"[{label}: {stage_id}]\n{content}"


def _structured_summaries_from_snapshot(
    snapshot: dict,
    *,
    source_type: str,
    summary_type: str,
    label: str,
) -> list[str]:
    return [
        formatted
        for summary in snapshot.get("contextSummaries", [])
        if summary["sourceType"] == source_type
        and summary["summaryType"] == summary_type
        and (
            formatted := _format_structured_summary(
                label,
                summary["sourceStageId"],
                summary["content"],
            )
        )
        is not None
    ]


def _artifact_summaries_from_snapshot(snapshot: dict) -> list[str]:
    persisted_summaries = [
        formatted
        for summary in snapshot.get("contextSummaries", [])
        if summary["sourceType"] == SUMMARY_SOURCE_ARTIFACT
        and summary["summaryType"] == CURRENT_ARTIFACT_SUMMARY_TYPE
        and (
            formatted := _format_artifact_summary(
                summary["sourceStageId"],
                summary["content"],
            )
        )
        is not None
    ]
    if persisted_summaries:
        return persisted_summaries

    return [
        formatted
        for artifact in snapshot["artifacts"]
        if (summary_content := build_artifact_summary_content(artifact["content"]))
        is not None
        and (
            formatted := _format_artifact_summary(
                artifact["stageId"],
                summary_content,
            )
        )
        is not None
    ]


def _locked_sections_from_snapshot(snapshot: dict) -> list[str]:
    return [
        (
            "[锁定章节: "
            f"{lock['stageId']}]\n"
            "以下章节已由用户锁定，后续生成不得修改这些章节原文；"
            "如需调整，请先请用户解锁。\n\n"
            f"{lock['content']}"
        )
        for lock in snapshot.get("artifactSectionLocks", [])
        if lock.get("content", "").strip()
    ]


def build_run_context(
    run_id: str,
    current_prompt: str,
    *,
    max_chars: int = DEFAULT_CONTEXT_MAX_CHARS,
    exclude_message_sequence: int | None = None,
    exclude_message_sequences: Iterable[int] = (),
) -> RunContext:
    snapshot = get_run_snapshot(run_id)
    excluded_message_sequences = set(exclude_message_sequences)
    if exclude_message_sequence is not None:
        excluded_message_sequences.add(exclude_message_sequence)
    user_supplements = _structured_summaries_from_snapshot(
        snapshot,
        source_type=SUMMARY_SOURCE_USER_INPUT,
        summary_type=USER_SUPPLEMENT_SUMMARY_TYPE,
        label="用户补充",
    )
    stage_conclusions = _structured_summaries_from_snapshot(
        snapshot,
        source_type=SUMMARY_SOURCE_ARTIFACT,
        summary_type=STAGE_CONCLUSION_SUMMARY_TYPE,
        label="阶段结论",
    )
    decisions = _structured_summaries_from_snapshot(
        snapshot,
        source_type=SUMMARY_SOURCE_ARTIFACT,
        summary_type=DECISION_SUMMARY_TYPE,
        label="关键决策",
    )
    artifact_summaries = _artifact_summaries_from_snapshot(snapshot)
    locked_sections = _locked_sections_from_snapshot(snapshot)
    context_blocks = []
    priority_context_blocks = []
    if user_supplements:
        user_supplement_block = "\n\n".join(
            [USER_SUPPLEMENT_HEADING, *user_supplements]
        )
        context_blocks.append(user_supplement_block)
        if excluded_message_sequences:
            priority_context_blocks.append(user_supplement_block)
    if stage_conclusions:
        context_blocks.append(
            "\n\n".join([STAGE_CONCLUSION_HEADING, *stage_conclusions])
        )
    if decisions:
        context_blocks.append("\n\n".join([DECISION_HEADING, *decisions]))
    if artifact_summaries:
        context_blocks.append(
            "\n\n".join([ARTIFACT_SUMMARY_HEADING, *artifact_summaries])
        )
    if locked_sections:
        context_blocks.append(
            "\n\n".join([LOCKED_ARTIFACT_SECTIONS_HEADING, *locked_sections])
        )
    prior_messages = [
        formatted
        for message in snapshot["messages"]
        if message["sequenceIndex"] not in excluded_message_sequences
        if (formatted := _format_message(message["role"], message["content"]))
        is not None
    ]
    current_message = f"[用户]\n{current_prompt}"
    if not context_blocks and not prior_messages:
        return RunContext(prompt=current_prompt, warnings=[])

    blocks = [*context_blocks, *prior_messages, current_message]
    prompt = "\n\n".join(blocks)
    if len(prompt) <= max_chars:
        return RunContext(prompt=prompt, warnings=[])

    kept = [current_message]
    used_chars = len(current_message) + len(TRUNCATION_NOTICE) + 4
    for block in priority_context_blocks:
        next_used_chars = used_chars + len(block) + 2
        if next_used_chars <= max_chars:
            kept.insert(0, block)
            used_chars = next_used_chars
    remaining_blocks = [
        block
        for block in [*context_blocks, *prior_messages]
        if block not in priority_context_blocks
    ]
    for block in reversed(remaining_blocks):
        next_used_chars = used_chars + len(block) + 2
        if next_used_chars > max_chars:
            break
        kept.insert(0, block)
        used_chars = next_used_chars

    return RunContext(
        prompt="\n\n".join([TRUNCATION_NOTICE, *kept]),
        warnings=[CONTEXT_TRUNCATED_WARNING],
    )


def build_run_context_prompt(
    run_id: str,
    current_prompt: str,
    *,
    max_chars: int = DEFAULT_CONTEXT_MAX_CHARS,
    exclude_message_sequence: int | None = None,
    exclude_message_sequences: Iterable[int] = (),
) -> str:
    return build_run_context(
        run_id,
        current_prompt,
        max_chars=max_chars,
        exclude_message_sequence=exclude_message_sequence,
        exclude_message_sequences=exclude_message_sequences,
    ).prompt
