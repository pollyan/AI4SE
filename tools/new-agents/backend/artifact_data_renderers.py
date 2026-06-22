import json
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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


class StrategySummary(StrictArtifactDataModel):
    conclusion: str
    basis: str
    case_stage_readiness: str


class QualityGoal(StrictArtifactDataModel):
    goal_id: str
    goal: str
    metric: str
    source: str
    priority: str
    status: str


class StrategyRisk(StrictArtifactDataModel):
    risk_id: str
    name: str
    failure_mode: str
    impact: str
    source: str
    severity: int = Field(ge=1, le=5)
    occurrence: int = Field(ge=1, le=5)
    detection: int = Field(ge=1, le=5)
    rpn: int = Field(ge=1, le=125)
    mitigation: str
    coverage: str
    status: str

    @model_validator(mode="after")
    def validate_rpn(self) -> "StrategyRisk":
        expected = self.severity * self.occurrence * self.detection
        if self.rpn != expected:
            raise ValueError(
                "rpn must equal severity * occurrence * detection " f"({expected})"
            )
        return self


class TestTechnique(StrictArtifactDataModel):
    technique_id: str
    target: str
    category: str
    technique: str
    reason: str
    applies_to: str


class TestLayer(StrictArtifactDataModel):
    layer: str
    ratio: str
    scope: str
    related: str
    tools: str
    entry_condition: str


class TestPoint(StrictArtifactDataModel):
    point_id: str
    point: str
    priority: str
    quality_goal: str
    risk: str
    technique: str
    layer: str
    estimated_cases: int = Field(ge=0)
    coverage: str
    status: str


class Tradeoff(StrictArtifactDataModel):
    item: str
    decision: str
    impact: str
    owner: str
    status: str


class StrategyArtifactData(StrictArtifactDataModel):
    document_info: DocumentInfo
    strategy_summary: StrategySummary
    quality_goals: list[QualityGoal] = Field(min_length=1)
    risks: list[StrategyRisk] = Field(min_length=1)
    test_techniques: list[TestTechnique] = Field(min_length=1)
    test_layers: list[TestLayer] = Field(min_length=1)
    test_points: list[TestPoint] = Field(min_length=1)
    tradeoffs: list[Tradeoff] = Field(min_length=1)
    stage_gate: list[StageGateCheck] = Field(min_length=1)


def render_agent_turn_from_artifact_data(
    payload: dict[str, Any],
    *,
    workflow_id: str,
    current_stage_id: str,
) -> AgentTurnOutput | None:
    if "artifact_data" not in payload:
        return None
    if (workflow_id, current_stage_id) == ("TEST_DESIGN", "CLARIFY"):
        artifact_data = ClarifyArtifactData.model_validate(payload["artifact_data"])
        markdown = render_test_design_clarify_markdown(artifact_data)
    elif (workflow_id, current_stage_id) == ("TEST_DESIGN", "STRATEGY"):
        artifact_data = StrategyArtifactData.model_validate(payload["artifact_data"])
        markdown = render_test_design_strategy_markdown(artifact_data)
    else:
        raise ValueError(
            f"artifact_data renderer is not configured for {workflow_id}/{current_stage_id}"
        )

    return AgentTurnOutput.model_validate(
        {
            "chat": payload.get("chat"),
            "artifact_update": {
                "type": "replace",
                "markdown": markdown,
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


def render_test_design_strategy_markdown(data: StrategyArtifactData) -> str:
    sections = [
        "# 测试策略蓝图",
        _render_strategy_summary(data.strategy_summary),
        _render_quality_goals(data.quality_goals),
        _render_strategy_risks(data.risks),
        _render_test_techniques(data.test_techniques),
        _render_test_layers(data.test_layers),
        _render_test_points(data.test_points),
        _render_tradeoffs(data.tradeoffs),
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


def _render_strategy_summary(summary: StrategySummary) -> str:
    rows = [
        ("策略结论", summary.conclusion),
        ("策略依据", summary.basis),
        ("进入用例阶段判断", summary.case_stage_readiness),
    ]
    return "## 1. 策略摘要\n" + _markdown_table(["字段", "内容"], rows)


def _render_quality_goals(goals: list[QualityGoal]) -> str:
    rows = [
        (
            item.goal_id,
            item.goal,
            item.metric,
            item.source,
            item.priority,
            item.status,
        )
        for item in goals
    ]
    return "## 2. 质量目标\n" + _markdown_table(
        ["目标 ID", "质量目标", "可验证指标", "来源", "优先级", "状态"],
        rows,
    )


def _render_strategy_risks(risks: list[StrategyRisk]) -> str:
    return (
        "## 3. 风险识别与 FMEA\n\n"
        "### 3.1 风险矩阵\n"
        + _render_risk_quadrant_chart(risks)
        + "\n\n"
        + "### 3.2 风险明细\n"
        + _render_risk_detail_table(risks)
        + "\n\n"
        + _render_risk_board_visual(risks)
        + "\n\n"
        + "> RPN = S × O × D，RPN >= 60 为高风险，需优先覆盖。"
    )


def _render_risk_quadrant_chart(risks: list[StrategyRisk]) -> str:
    lines = [
        "```mermaid",
        "quadrantChart",
        "    title 风险优先级矩阵",
        '    x-axis "低发生度" --> "高发生度"',
        '    y-axis "低严重度" --> "高严重度"',
        '    quadrant-1 "紧急处理"',
        '    quadrant-2 "重点关注"',
        '    quadrant-3 "观察监控"',
        '    quadrant-4 "常规覆盖"',
    ]
    for risk in risks:
        x_value = risk.occurrence / 5
        y_value = risk.severity / 5
        lines.append(
            f'    "{_escape_mermaid_label(risk.name)}": '
            f"[{x_value:.2f}, {y_value:.2f}]"
        )
    lines.append("```")
    return "\n".join(lines)


def _render_risk_detail_table(risks: list[StrategyRisk]) -> str:
    rows = [
        (
            item.risk_id,
            item.name,
            item.failure_mode,
            item.impact,
            item.source,
            item.severity,
            item.occurrence,
            item.detection,
            item.rpn,
            item.mitigation,
            item.coverage,
            item.status,
        )
        for item in risks
    ]
    return _markdown_table(
        [
            "风险 ID",
            "风险名称",
            "失效模式",
            "影响",
            "来源",
            "严重度 S(1-5)",
            "发生度 O(1-5)",
            "检出度 D(1-5)",
            "RPN(SxOxD)",
            "缓解策略",
            "覆盖建议",
            "状态",
        ],
        rows,
    )


def _render_risk_board_visual(risks: list[StrategyRisk]) -> str:
    visual = {
        "type": "risk-board",
        "title": "FMEA 风险处置看板",
        "columns": ["风险", "S", "O", "D", "RPN", "缓解策略", "覆盖建议"],
        "rows": [
            {
                "风险": item.name,
                "S": item.severity,
                "O": item.occurrence,
                "D": item.detection,
                "RPN": item.rpn,
                "缓解策略": item.mitigation,
                "覆盖建议": item.coverage,
            }
            for item in risks
        ],
    }
    return (
        "```ai4se-visual\n" + json.dumps(visual, ensure_ascii=False, indent=2) + "\n```"
    )


def _render_test_techniques(techniques: list[TestTechnique]) -> str:
    rows = [
        (
            item.technique_id,
            item.target,
            item.category,
            item.technique,
            item.reason,
            item.applies_to,
        )
        for item in techniques
    ]
    return "## 4. 测试技术选型\n" + _markdown_table(
        ["技术 ID", "针对目标", "技术类别", "选用技术", "选择理由", "适用风险/测试点"],
        rows,
    )


def _render_test_layers(layers: list[TestLayer]) -> str:
    rows = [
        (
            item.layer,
            item.ratio,
            item.scope,
            item.related,
            item.tools,
            item.entry_condition,
        )
        for item in layers
    ]
    return "## 5. 测试分层策略\n\n" "### 5.1 测试金字塔\n" + _render_test_pyramid(
        layers
    ) + "\n\n" + "### 5.2 分层明细\n" + _markdown_table(
        ["层级", "占比", "覆盖范围", "关联风险/测试点", "推荐工具", "进入条件"],
        rows,
    )


def _render_test_pyramid(layers: list[TestLayer]) -> str:
    node_ids: dict[str, str] = {}
    lines = ["```mermaid", "block-beta", "    columns 1"]
    for layer in reversed(layers):
        node_id = _node_id(layer.layer, node_ids)
        label = f"{layer.layer} ({layer.ratio}) - {layer.scope}"
        lines.append(f'    {node_id}["{_escape_mermaid_label(label)}"]')
    lines.append("```")
    return "\n".join(lines)


def _render_test_points(points: list[TestPoint]) -> str:
    rows = [
        (
            item.point_id,
            item.point,
            item.priority,
            item.quality_goal,
            item.risk,
            item.technique,
            item.layer,
            item.estimated_cases,
            item.coverage,
            item.status,
        )
        for item in points
    ]
    p0_count = sum(1 for item in points if item.priority == "P0")
    p1_count = sum(1 for item in points if item.priority == "P1")
    p2_count = sum(1 for item in points if item.priority == "P2")
    estimated_total = sum(item.estimated_cases for item in points)
    return (
        "## 6. 测试点拓扑\n"
        + _markdown_table(
            [
                "测试点 ID",
                "测试点",
                "优先级",
                "关联质量目标",
                "关联风险",
                "测试技术",
                "测试层级",
                "预估用例数",
                "覆盖建议",
                "状态",
            ],
            rows,
        )
        + "\n\n"
        + f"> **覆盖统计**：共 {len(points)} 个测试点，P0: {p0_count} 个 | "
        + f"P1: {p1_count} 个 | P2: {p2_count} 个，"
        + f"预估总用例 {estimated_total} 条"
    )


def _render_tradeoffs(tradeoffs: list[Tradeoff]) -> str:
    rows = [
        (item.item, item.decision, item.impact, item.owner, item.status)
        for item in tradeoffs
    ]
    return "## 7. 资源与取舍\n" + _markdown_table(
        ["取舍项", "决策", "影响", "需要确认人", "状态"],
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


def _markdown_table(headers: list[str], rows: list[tuple[Any, ...]]) -> str:
    header = "| " + " | ".join(headers) + " |"
    separator = "| " + " | ".join("---" for _ in headers) + " |"
    body = [
        "| " + " | ".join(_escape_table_cell(cell) for cell in row) + " |"
        for row in rows
    ]
    return "\n".join([header, separator, *body])


def _escape_table_cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", "<br>")


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
