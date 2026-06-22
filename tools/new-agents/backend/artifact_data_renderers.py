import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from agent_contracts import AgentTurnOutput


class StrictArtifactDataModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator("*", mode="before")
    @classmethod
    def reject_blank_strings(cls, value: Any) -> Any:
        if isinstance(value, str) and not value.strip():
            raise ValueError("string fields cannot be blank")
        return value.strip() if isinstance(value, str) else value


class DocumentInfo(StrictArtifactDataModel):
    artifact_name: str
    workflow: str
    stage: str
    status: str


class RequirementFact(StrictArtifactDataModel):
    fact_id: str
    fact: str
    source: str
    evidence_level: str
    status: str


class SystemBoundary(StrictArtifactDataModel):
    boundary_type: str
    content: str
    testing_meaning: str
    status: str


class BusinessRule(StrictArtifactDataModel):
    rule_id: str
    rule: str
    trigger: str
    state_transition: str
    exception_handling: str
    acceptance: str
    status: str


class FlowLink(StrictArtifactDataModel):
    from_node: str
    to_node: str
    label: str


class ClarificationQuestion(StrictArtifactDataModel):
    question_id: str
    question: str
    priority: str
    blocking: str
    impact: str
    assumption: str
    owner: str
    status: str


class QualityRequirement(StrictArtifactDataModel):
    dimension: str
    requirement_or_assumption: str
    metric: str
    risk: str
    status: str


class DownstreamInput(StrictArtifactDataModel):
    input_type: str
    input_id: str
    content: str
    source: str
    usage: str


class StageGateCheck(StrictArtifactDataModel):
    checked: bool
    item: str


class ClarifyArtifactData(StrictArtifactDataModel):
    document_info: DocumentInfo
    requirement_facts: list[RequirementFact] = Field(min_length=1)
    system_boundaries: list[SystemBoundary] = Field(min_length=1)
    business_rules: list[BusinessRule] = Field(min_length=1)
    flow_links: list[FlowLink] = Field(min_length=1)
    clarification_questions: list[ClarificationQuestion] = Field(min_length=1)
    quality_requirements: list[QualityRequirement] = Field(min_length=1)
    downstream_inputs: list[DownstreamInput] = Field(min_length=1)
    stage_gate: list[StageGateCheck] = Field(min_length=1)


def render_agent_turn_from_artifact_data(
    payload: dict[str, Any],
    *,
    workflow_id: str,
    current_stage_id: str,
) -> AgentTurnOutput | None:
    if "artifact_data" not in payload:
        return None
    if (workflow_id, current_stage_id) != ("TEST_DESIGN", "CLARIFY"):
        raise ValueError(
            f"artifact_data renderer is not configured for {workflow_id}/{current_stage_id}"
        )

    artifact_data = ClarifyArtifactData.model_validate(payload["artifact_data"])
    return AgentTurnOutput.model_validate(
        {
            "chat": payload.get("chat"),
            "artifact_update": {
                "type": "replace",
                "markdown": render_test_design_clarify_markdown(artifact_data),
            },
            "stage_action": payload.get("stage_action"),
            "warnings": payload.get("warnings", []),
        }
    )


def render_test_design_clarify_markdown(data: ClarifyArtifactData) -> str:
    sections = [
        "# 需求分析文档",
        _render_document_info(data.document_info),
        _render_requirement_facts(data.requirement_facts),
        _render_system_boundaries(data.system_boundaries),
        _render_business_rules(data.business_rules),
        _render_flow_links(data.flow_links),
        _render_clarification_questions(data.clarification_questions),
        _render_quality_requirements(data.quality_requirements),
        _render_downstream_inputs(data.downstream_inputs),
        _render_stage_gate(data.stage_gate),
    ]
    return "\n\n".join(sections)


def _render_document_info(info: DocumentInfo) -> str:
    rows = [
        ("Artifact 名称", info.artifact_name),
        ("Workflow", info.workflow),
        ("Stage", info.stage),
        ("状态", info.status),
    ]
    return "## 文档信息\n" + _markdown_table(["字段", "内容"], rows)


def _render_requirement_facts(facts: list[RequirementFact]) -> str:
    rows = [
        (item.fact_id, item.fact, item.source, item.evidence_level, item.status)
        for item in facts
    ]
    return "## 1. 需求事实清单\n" + _markdown_table(
        ["事实 ID", "需求事实", "来源", "证据等级", "状态"],
        rows,
    )


def _render_system_boundaries(boundaries: list[SystemBoundary]) -> str:
    rows = [
        (item.boundary_type, item.content, item.testing_meaning, item.status)
        for item in boundaries
    ]
    return "## 2. 被测系统与边界\n" + _markdown_table(
        ["类型", "具体内容", "测试含义", "状态"],
        rows,
    )


def _render_business_rules(rules: list[BusinessRule]) -> str:
    rows = [
        (
            item.rule_id,
            item.rule,
            item.trigger,
            item.state_transition,
            item.exception_handling,
            item.acceptance,
            item.status,
        )
        for item in rules
    ]
    return "## 3. 业务规则与数据状态\n" + _markdown_table(
        [
            "规则 ID",
            "业务规则",
            "触发条件",
            "边界值/状态流转",
            "异常处理",
            "验收口径",
            "状态",
        ],
        rows,
    )


def _render_flow_links(links: list[FlowLink]) -> str:
    node_ids: dict[str, str] = {}
    lines = ["```mermaid", "flowchart TD"]
    for link in links:
        from_id = _node_id(link.from_node, node_ids)
        to_id = _node_id(link.to_node, node_ids)
        lines.append(
            f'    {from_id}["{_escape_mermaid_label(link.from_node)}"] '
            f'-->|"{_escape_mermaid_label(link.label)}"| '
            f'{to_id}["{_escape_mermaid_label(link.to_node)}"]'
        )
    lines.append("```")
    return "## 4. 核心链路与异常链路\n" + "\n".join(lines)


def _render_clarification_questions(
    questions: list[ClarificationQuestion],
) -> str:
    rows = [
        (
            item.question_id,
            item.question,
            item.priority,
            item.blocking,
            item.impact,
            item.assumption,
            item.owner,
            item.status,
        )
        for item in questions
    ]
    return "## 5. 待澄清问题\n" + _markdown_table(
        [
            "问题 ID",
            "问题描述",
            "优先级",
            "阻断性",
            "影响范围",
            "当前假设",
            "责任方",
            "状态",
        ],
        rows,
    )


def _render_quality_requirements(
    requirements: list[QualityRequirement],
) -> str:
    rows = [
        (
            item.dimension,
            item.requirement_or_assumption,
            item.metric,
            item.risk,
            item.status,
        )
        for item in requirements
    ]
    return "## 6. 隐式质量需求\n" + _markdown_table(
        ["质量维度", "需求或假设", "可验证指标", "风险", "状态"],
        rows,
    )


def _render_downstream_inputs(inputs: list[DownstreamInput]) -> str:
    rows = [
        (item.input_type, item.input_id, item.content, item.source, item.usage)
        for item in inputs
    ]
    return "## 7. 后续测试设计输入\n" + _markdown_table(
        ["输入类型", "ID", "内容", "来源", "后续用途"],
        rows,
    )


def _render_stage_gate(checks: list[StageGateCheck]) -> str:
    lines = [f"- [{'x' if item.checked else ' '}] {item.item}" for item in checks]
    return "## 8. 阶段门禁\n" + "\n".join(lines)


def _markdown_table(headers: list[str], rows: list[tuple[str, ...]]) -> str:
    header = "| " + " | ".join(headers) + " |"
    separator = "| " + " | ".join("---" for _ in headers) + " |"
    body = [
        "| " + " | ".join(_escape_table_cell(cell) for cell in row) + " |"
        for row in rows
    ]
    return "\n".join([header, separator, *body])


def _escape_table_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", "<br>")


def _node_id(label: str, existing: dict[str, str]) -> str:
    if label in existing:
        return existing[label]
    base = re.sub(r"[^0-9A-Za-z_]+", "_", label).strip("_")
    if not base or base[0].isdigit():
        base = f"N_{base}" if base else "N"
    candidate = base
    suffix = 2
    while candidate in existing.values():
        candidate = f"{base}_{suffix}"
        suffix += 1
    existing[label] = candidate
    return candidate


def _escape_mermaid_label(value: str) -> str:
    return value.replace('"', "'")
