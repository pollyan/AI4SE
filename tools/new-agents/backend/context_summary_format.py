ARTIFACT_MAX_CHARS = 1200
ARTIFACT_TRUNCATION_NOTICE = "\n[该阶段产物摘要已截断]"
CURRENT_ARTIFACT_SUMMARY_TYPE = "current_artifact"
USER_SUPPLEMENT_SUMMARY_TYPE = "user_supplement"
STAGE_CONCLUSION_SUMMARY_TYPE = "stage_conclusion"
DECISION_SUMMARY_TYPE = "decision"
SUMMARY_TRUNCATION_NOTICE = "\n[该结构化摘要已截断]"


def normalize_artifact_content(content: str) -> str:
    return "\n".join(
        line.rstrip()
        for line in content.strip().splitlines()
        if line.strip()
    )


def build_artifact_summary_content(content: str) -> str | None:
    summary = normalize_artifact_content(content)
    if not summary:
        return None
    if len(summary) > ARTIFACT_MAX_CHARS:
        summary = summary[:ARTIFACT_MAX_CHARS].rstrip()
        summary = f"{summary}{ARTIFACT_TRUNCATION_NOTICE}"
    return summary


def _truncate_summary(content: str) -> str | None:
    summary = normalize_artifact_content(content)
    if not summary:
        return None
    if len(summary) > ARTIFACT_MAX_CHARS:
        summary = summary[:ARTIFACT_MAX_CHARS].rstrip()
        summary = f"{summary}{SUMMARY_TRUNCATION_NOTICE}"
    return summary


def _extract_markdown_sections(
    content: str,
    keywords: tuple[str, ...],
    *,
    include_heading: bool,
) -> str | None:
    lines = normalize_artifact_content(content).splitlines()
    sections: list[str] = []
    current: list[str] = []
    capturing = False

    for line in lines:
        is_heading = line.lstrip().startswith("#")
        if is_heading:
            if current:
                sections.append("\n".join(current).strip())
            capturing = any(keyword in line for keyword in keywords)
            current = [line] if capturing and include_heading else []
            continue
        if capturing:
            current.append(line)

    if current:
        sections.append("\n".join(current).strip())
    if not sections:
        return None
    return _truncate_summary("\n\n".join(section for section in sections if section))


def build_user_supplement_summary_content(content: str) -> str | None:
    summary = "\n".join(line.rstrip() for line in content.strip().splitlines()).strip()
    while "\n\n\n" in summary:
        summary = summary.replace("\n\n\n", "\n\n")
    if not summary:
        return None
    if len(summary) > ARTIFACT_MAX_CHARS:
        summary = summary[:ARTIFACT_MAX_CHARS].rstrip()
        summary = f"{summary}{SUMMARY_TRUNCATION_NOTICE}"
    return summary


def build_stage_conclusion_summary_content(content: str) -> str | None:
    extracted = _extract_markdown_sections(
        content,
        ("阶段结论", "结论", "摘要", "核心", "概述"),
        include_heading=True,
    )
    if extracted is not None:
        return extracted
    return build_artifact_summary_content(content)


def build_decision_summary_content(content: str) -> str | None:
    return _extract_markdown_sections(
        content,
        ("关键决策", "决策", "决定", "取舍", "约定"),
        include_heading=False,
    )
