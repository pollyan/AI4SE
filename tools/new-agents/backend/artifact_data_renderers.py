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


class CaseStatistics(StrictArtifactDataModel):
    total: int = Field(ge=0)
    p0_count: int = Field(ge=0)
    p1_count: int = Field(ge=0)
    p2_count: int = Field(ge=0)


class DesignBasis(StrictArtifactDataModel):
    basis_id: str
    source_type: str
    source_id: str
    basis: str
    case_direction: str


class TestCaseItem(StrictArtifactDataModel):
    case_id: str
    title: str
    priority: str
    dimension: str
    test_point: str
    risk: str
    precondition: str
    steps: str
    test_data: str
    expected_result: str
    assertion: str
    execution_layer: str
    automation_suggestion: str
    status: str


class CaseGroup(StrictArtifactDataModel):
    dimension: str
    cases: list[TestCaseItem] = Field(min_length=1)


class TestDataEnvironment(StrictArtifactDataModel):
    data_id: str
    type: str
    content: str
    preparation: str
    related_cases: str
    status: str


class AutomationCandidate(StrictArtifactDataModel):
    candidate_id: str
    case_id: str
    recommended_layer: str
    value: str
    prerequisite: str
    risk_or_limit: str
    status: str


class CoverageTraceItem(StrictArtifactDataModel):
    test_point: str
    priority: str
    risk: str
    covered_cases: list[str] = Field(min_length=1)
    status: str


class OpenQuestion(StrictArtifactDataModel):
    question_id: str
    question: str
    related: str
    priority: str
    blocking: str
    owner: str
    status: str


class CasesArtifactData(StrictArtifactDataModel):
    document_info: DocumentInfo
    case_statistics: CaseStatistics
    design_bases: list[DesignBasis] = Field(min_length=1)
    case_groups: list[CaseGroup] = Field(min_length=1)
    test_data_environments: list[TestDataEnvironment] = Field(min_length=1)
    automation_candidates: list[AutomationCandidate] = Field(min_length=1)
    coverage_trace: list[CoverageTraceItem] = Field(min_length=1)
    open_questions: list[OpenQuestion] = Field(min_length=1)
    stage_gate: list[StageGateCheck] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_case_consistency(self) -> "CasesArtifactData":
        cases = [case for group in self.case_groups for case in group.cases]
        case_ids = {case.case_id for case in cases}
        if len(case_ids) != len(cases):
            raise ValueError("case_groups contains duplicate case_id")

        priority_counts = {
            "P0": sum(1 for case in cases if case.priority == "P0"),
            "P1": sum(1 for case in cases if case.priority == "P1"),
            "P2": sum(1 for case in cases if case.priority == "P2"),
        }
        if (
            self.case_statistics.total != len(cases)
            or self.case_statistics.p0_count != priority_counts["P0"]
            or self.case_statistics.p1_count != priority_counts["P1"]
            or self.case_statistics.p2_count != priority_counts["P2"]
        ):
            raise ValueError(
                "case_statistics must match case_groups totals and P0/P1/P2 counts"
            )

        unknown_references = sorted(
            {
                case_id
                for trace in self.coverage_trace
                for case_id in trace.covered_cases
                if case_id not in case_ids
            }
        )
        if unknown_references:
            raise ValueError(
                "coverage_trace references unknown case ids: "
                + ", ".join(unknown_references)
            )
        return self


class DeliveryMetrics(StrictArtifactDataModel):
    project_name: str
    version: str
    generated_at: str
    delivery_status: str
    total_cases: int = Field(ge=0)
    high_risk_count: int = Field(ge=0)


class DeliveryExecutiveSummaryItem(StrictArtifactDataModel):
    summary_item: str
    conclusion: str
    evidence_source: str
    status: str


class DeliveryRequirementSummaryItem(StrictArtifactDataModel):
    content_type: str
    reference: str
    conclusion: str
    open_status: str


class DeliveryStrategySummaryItem(StrictArtifactDataModel):
    strategy_item: str
    conclusion: str
    related: str
    coverage_status: str


class DeliveryCaseSummaryItem(StrictArtifactDataModel):
    dimension: str
    case_count: int = Field(ge=0)
    p0_count: int = Field(ge=0)
    p1_count: int = Field(ge=0)
    p2_count: int = Field(ge=0)
    automation_candidates: int = Field(ge=0)
    blocked_or_needs_env: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_priority_counts(self) -> "DeliveryCaseSummaryItem":
        priority_total = self.p0_count + self.p1_count + self.p2_count
        if priority_total != self.case_count:
            raise ValueError("case_count must equal p0_count + p1_count + p2_count")
        return self


class DeliveryCoverageMapItem(StrictArtifactDataModel):
    requirement: str
    risk: str
    test_point: str
    case_ids: list[str] = Field(min_length=1)
    acceptance_status: str


class DeliveryOpenRisk(StrictArtifactDataModel):
    risk_id: str
    risk_type: str
    description: str
    impact: str
    acceptable: str
    owner: str
    next_step: str
    status: str


class DeliverySignoff(StrictArtifactDataModel):
    role: str
    owner: str
    opinion: str
    status: str


class DeliveryChangeLogItem(StrictArtifactDataModel):
    version: str
    date: str
    change: str
    reason: str
    owner: str


class DeliveryArtifactData(StrictArtifactDataModel):
    document_info: DocumentInfo
    delivery_metrics: DeliveryMetrics
    executive_summary: list[DeliveryExecutiveSummaryItem] = Field(min_length=1)
    requirement_summary: list[DeliveryRequirementSummaryItem] = Field(min_length=1)
    strategy_summary_items: list[DeliveryStrategySummaryItem] = Field(min_length=1)
    case_summary_items: list[DeliveryCaseSummaryItem] = Field(min_length=1)
    coverage_map: list[DeliveryCoverageMapItem] = Field(min_length=1)
    open_risks: list[DeliveryOpenRisk] = Field(min_length=1)
    acceptance_checklist: list[StageGateCheck] = Field(min_length=1)
    signoffs: list[DeliverySignoff] = Field(min_length=1)
    change_log: list[DeliveryChangeLogItem] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_delivery_consistency(self) -> "DeliveryArtifactData":
        total_cases = sum(item.case_count for item in self.case_summary_items)
        if self.delivery_metrics.total_cases != total_cases:
            raise ValueError(
                "delivery_metrics.total_cases must match case_summary_items total_cases"
            )

        high_risk_count = sum(
            1
            for item in self.open_risks
            if "风险" in item.risk_type and item.acceptable != "是"
        )
        if self.delivery_metrics.high_risk_count != high_risk_count:
            raise ValueError(
                "delivery_metrics.high_risk_count must match unacceptable open risks"
            )
        return self


class ReqReviewInfo(StrictArtifactDataModel):
    artifact_name: str
    requirement_name: str
    review_date: str
    requirement_summary: str
    conclusion: str


class ReqReviewScopeItem(StrictArtifactDataModel):
    scope_type: str
    content: str
    review_impact: str
    status: str


class ReqReviewQualityOverviewItem(StrictArtifactDataModel):
    dimension: str
    quality_judgement: str
    severity_score: int = Field(ge=1, le=5)
    evidence: str
    testing_risk: str
    status: str


class ReqReviewIssueStatistics(StrictArtifactDataModel):
    p0_count: int = Field(ge=0)
    p1_count: int = Field(ge=0)
    p2_count: int = Field(ge=0)
    p0_description: str
    p1_description: str
    p2_description: str


class ReqReviewIssueItem(StrictArtifactDataModel):
    issue_id: str
    dimension: str
    description: str
    priority: str
    blocking: str
    requirement_section: str
    impact: str
    evidence: str
    suggestion: str
    owner: str
    status: str


class ReqReviewIssueGroup(StrictArtifactDataModel):
    dimension: str
    issues: list[ReqReviewIssueItem] = Field(min_length=1)


class ReqReviewRevisionSuggestion(StrictArtifactDataModel):
    suggestion_id: str
    related_issues: list[str] = Field(min_length=1)
    suggestion: str
    acceptance: str
    owner: str
    status: str


class ReqReviewArtifactData(StrictArtifactDataModel):
    review_info: ReqReviewInfo
    scope_items: list[ReqReviewScopeItem] = Field(min_length=1)
    quality_overview: list[ReqReviewQualityOverviewItem] = Field(min_length=1)
    issue_statistics: ReqReviewIssueStatistics
    issue_groups: list[ReqReviewIssueGroup] = Field(min_length=1)
    revision_suggestions: list[ReqReviewRevisionSuggestion] = Field(min_length=1)
    stage_gate: list[StageGateCheck] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_review_consistency(self) -> "ReqReviewArtifactData":
        issues = [issue for group in self.issue_groups for issue in group.issues]
        issue_ids = {issue.issue_id for issue in issues}
        if len(issue_ids) != len(issues):
            raise ValueError("issue_groups contains duplicate issue_id")

        priority_counts = {
            "P0": sum(1 for issue in issues if issue.priority == "P0"),
            "P1": sum(1 for issue in issues if issue.priority == "P1"),
            "P2": sum(1 for issue in issues if issue.priority == "P2"),
        }
        if (
            self.issue_statistics.p0_count != priority_counts["P0"]
            or self.issue_statistics.p1_count != priority_counts["P1"]
            or self.issue_statistics.p2_count != priority_counts["P2"]
        ):
            raise ValueError("issue_statistics must match issue_groups priorities")

        unknown_references = sorted(
            {
                issue_id
                for suggestion in self.revision_suggestions
                for issue_id in suggestion.related_issues
                if issue_id not in issue_ids
            }
        )
        if unknown_references:
            raise ValueError(
                "revision_suggestions references unknown issue ids: "
                + ", ".join(unknown_references)
            )
        return self


class ReqReviewReportConclusion(StrictArtifactDataModel):
    artifact_name: str
    review_result: str
    reason: str
    development_gate: str
    needs_recheck: str
    summary: str


class ReqReviewReportInfo(StrictArtifactDataModel):
    requirement_name: str
    review_date: str
    review_input: str
    participants: str


class ReqReviewReportIssueStatistics(StrictArtifactDataModel):
    p0_count: int = Field(ge=0)
    p1_count: int = Field(ge=0)
    p2_count: int = Field(ge=0)


class ReqReviewReportIssueClosure(StrictArtifactDataModel):
    issue_id: str
    priority: str
    description: str
    requirement_section: str
    impact: str
    owner: str
    next_step: str
    closure_status: str
    recheck_condition: str


class ReqReviewReportCondition(StrictArtifactDataModel):
    condition_id: str
    condition: str
    related_issues: list[str] = Field(min_length=1)
    verification: str
    owner: str
    status: str


class ReqReviewReportSignoff(StrictArtifactDataModel):
    role: str
    owner: str
    opinion: str
    status: str


class ReqReviewReportChangeLogItem(StrictArtifactDataModel):
    version: str
    date: str
    change: str
    reason: str
    owner: str


class ReqReviewReportArtifactData(StrictArtifactDataModel):
    conclusion: ReqReviewReportConclusion
    review_info: ReqReviewReportInfo
    issue_statistics: ReqReviewReportIssueStatistics
    issue_closures: list[ReqReviewReportIssueClosure] = Field(min_length=1)
    review_conditions: list[ReqReviewReportCondition] = Field(min_length=1)
    signoffs: list[ReqReviewReportSignoff] = Field(min_length=1)
    change_log: list[ReqReviewReportChangeLogItem] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_report_consistency(self) -> "ReqReviewReportArtifactData":
        issue_ids = {item.issue_id for item in self.issue_closures}
        if len(issue_ids) != len(self.issue_closures):
            raise ValueError("issue_closures contains duplicate issue_id")

        priority_counts = {
            "P0": sum(1 for item in self.issue_closures if item.priority == "P0"),
            "P1": sum(1 for item in self.issue_closures if item.priority == "P1"),
            "P2": sum(1 for item in self.issue_closures if item.priority == "P2"),
        }
        if (
            self.issue_statistics.p0_count != priority_counts["P0"]
            or self.issue_statistics.p1_count != priority_counts["P1"]
            or self.issue_statistics.p2_count != priority_counts["P2"]
        ):
            raise ValueError("issue_statistics must match issue_closures priorities")

        unknown_references = sorted(
            {
                issue_id
                for condition in self.review_conditions
                for issue_id in condition.related_issues
                if issue_id not in issue_ids
            }
        )
        if unknown_references:
            raise ValueError(
                "review_conditions references unknown issue ids: "
                + ", ".join(unknown_references)
            )

        has_open_p0 = any(
            item.priority == "P0" and item.closure_status != "已关闭"
            for item in self.issue_closures
        )
        has_open_p1 = any(
            item.priority == "P1" and item.closure_status != "已关闭"
            for item in self.issue_closures
        )
        if self.conclusion.review_result == "通过" and (has_open_p0 or has_open_p1):
            raise ValueError(
                "conclusion.review_result cannot be 通过 when open P0/P1 issues remain"
            )
        return self


class PositioningSummary(StrictArtifactDataModel):
    one_liner: str
    core_user: str
    core_pain: str
    unique_value: str
    current_judgement: str


class ValueFlowNode(StrictArtifactDataModel):
    node_id: str
    label: str
    description: str


class ValueFlowLink(StrictArtifactDataModel):
    from_node: str
    to_node: str
    label: str


class ValueFlow(StrictArtifactDataModel):
    nodes: list[ValueFlowNode] = Field(min_length=1)
    links: list[ValueFlowLink] = Field(min_length=1)


class TargetScenario(StrictArtifactDataModel):
    dimension: str
    description: str
    evidence_level: str
    status: str


class PainEvidence(StrictArtifactDataModel):
    pain_id: str
    description: str
    scene: str
    impact: str
    evidence_level: str
    validation_action: str
    status: str


class Differentiator(StrictArtifactDataModel):
    dimension: str
    our_value: str
    existing_solution: str
    evidence: str
    status: str


class BusinessFeasibility(StrictArtifactDataModel):
    dimension: str
    judgement: str
    basis: str
    validation_action: str
    status: str


class ValueScore(StrictArtifactDataModel):
    dimension: str
    score: int = Field(ge=1, le=5)
    basis: str
    next_validation: str


class ValueScoreSummary(StrictArtifactDataModel):
    total_score: int = Field(ge=1)
    average_score: float = Field(ge=1, le=5)
    judgement: str


class ValueAssumption(StrictArtifactDataModel):
    assumption_id: str
    content: str
    impact: str
    validation_action: str
    owner: str
    status: str


class ValueDiscoveryElevatorArtifactData(StrictArtifactDataModel):
    document_info: DocumentInfo
    positioning_summary: PositioningSummary
    value_flow: ValueFlow
    target_scenarios: list[TargetScenario] = Field(min_length=1)
    pain_evidence: list[PainEvidence] = Field(min_length=1)
    differentiators: list[Differentiator] = Field(min_length=1)
    business_feasibility: list[BusinessFeasibility] = Field(min_length=1)
    score_matrix: list[ValueScore] = Field(min_length=1)
    score_summary: ValueScoreSummary
    assumptions: list[ValueAssumption] = Field(min_length=1)
    elevator_pitch: str
    stage_gate: list[StageGateCheck] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_value_consistency(self) -> "ValueDiscoveryElevatorArtifactData":
        node_ids = {node.node_id for node in self.value_flow.nodes}
        if len(node_ids) != len(self.value_flow.nodes):
            raise ValueError("value_flow.nodes contains duplicate node_id")

        unknown_references = sorted(
            {
                reference
                for link in self.value_flow.links
                for reference in (link.from_node, link.to_node)
                if reference not in node_ids
            }
        )
        if unknown_references:
            raise ValueError(
                "value_flow.links references unknown node ids: "
                + ", ".join(unknown_references)
            )

        total_score = sum(item.score for item in self.score_matrix)
        if self.score_summary.total_score != total_score:
            raise ValueError(
                "score_summary.total_score must equal score_matrix score sum"
            )

        expected_average = round(total_score / len(self.score_matrix), 2)
        if abs(self.score_summary.average_score - expected_average) > 0.001:
            raise ValueError(
                "score_summary.average_score must equal score_matrix average score "
                f"({expected_average})"
            )
        return self


class PersonaSummary(StrictArtifactDataModel):
    artifact_name: str
    core_user_judgement: str
    primary_pain: str
    validation_status: str
    journey_readiness: str


class PersonaFeature(StrictArtifactDataModel):
    dimension: str
    description: str
    evidence_level: str
    validation_status: str


class PersonaBehaviorFeature(StrictArtifactDataModel):
    dimension: str
    description: str
    trigger: str
    evidence_level: str
    validation_status: str


class PersonaProfile(StrictArtifactDataModel):
    persona_id: str
    name: str
    priority: str
    summary: str
    basic_features: list[PersonaFeature] = Field(min_length=1)
    behavior_features: list[PersonaBehaviorFeature] = Field(min_length=1)


class PersonaBehaviorScenario(StrictArtifactDataModel):
    scenario_id: str
    persona_id: str
    scenario: str
    trigger: str
    user_goal: str
    current_solution: str
    status: str


class PersonaDecisionRole(StrictArtifactDataModel):
    role: str
    persona_id: str
    concern: str
    influence: str
    payment_relation: str
    evidence_level: str
    validation_status: str


class PersonaPainEvidence(StrictArtifactDataModel):
    pain_id: str
    persona_id: str
    pain: str
    frequency: str
    impact: str
    existing_solution_gap: str
    evidence_level: str
    validation_status: str


class AntiPersona(StrictArtifactDataModel):
    name: str
    reason: str
    boundary: str
    risk: str
    status: str


class PersonaPriorityRanking(StrictArtifactDataModel):
    priority: str
    persona_id: str
    reason: str
    related_pain: str
    evidence_level: str
    validation_status: str


class ValueDiscoveryPersonaArtifactData(StrictArtifactDataModel):
    document_info: DocumentInfo
    persona_summary: PersonaSummary
    personas: list[PersonaProfile] = Field(min_length=1)
    behavior_scenarios: list[PersonaBehaviorScenario] = Field(min_length=1)
    decision_chain: list[PersonaDecisionRole] = Field(min_length=1)
    pain_evidence: list[PersonaPainEvidence] = Field(min_length=1)
    anti_personas: list[AntiPersona] = Field(min_length=1)
    priority_ranking: list[PersonaPriorityRanking] = Field(min_length=1)
    stage_gate: list[StageGateCheck] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_persona_consistency(self) -> "ValueDiscoveryPersonaArtifactData":
        persona_ids = {persona.persona_id for persona in self.personas}
        if len(persona_ids) != len(self.personas):
            raise ValueError("personas contains duplicate persona_id")

        references = [
            *(item.persona_id for item in self.behavior_scenarios),
            *(item.persona_id for item in self.decision_chain),
            *(item.persona_id for item in self.pain_evidence),
            *(item.persona_id for item in self.priority_ranking),
        ]
        unknown = sorted(
            {persona_id for persona_id in references if persona_id not in persona_ids}
        )
        if unknown:
            raise ValueError(
                "persona references unknown persona ids: " + ", ".join(unknown)
            )

        ranked_ids = [item.persona_id for item in self.priority_ranking]
        if len(set(ranked_ids)) != len(ranked_ids):
            raise ValueError("priority_ranking contains duplicate persona_id")
        return self


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
    elif (workflow_id, current_stage_id) == ("TEST_DESIGN", "CASES"):
        artifact_data = CasesArtifactData.model_validate(payload["artifact_data"])
        markdown = render_test_design_cases_markdown(artifact_data)
    elif (workflow_id, current_stage_id) == ("TEST_DESIGN", "DELIVERY"):
        artifact_data = DeliveryArtifactData.model_validate(payload["artifact_data"])
        markdown = render_test_design_delivery_markdown(artifact_data)
    elif (workflow_id, current_stage_id) == ("REQ_REVIEW", "REVIEW"):
        artifact_data = ReqReviewArtifactData.model_validate(payload["artifact_data"])
        markdown = render_req_review_review_markdown(artifact_data)
    elif (workflow_id, current_stage_id) == ("REQ_REVIEW", "REPORT"):
        artifact_data = ReqReviewReportArtifactData.model_validate(
            payload["artifact_data"]
        )
        markdown = render_req_review_report_markdown(artifact_data)
    elif (workflow_id, current_stage_id) == ("VALUE_DISCOVERY", "ELEVATOR"):
        artifact_data = ValueDiscoveryElevatorArtifactData.model_validate(
            payload["artifact_data"]
        )
        markdown = render_value_discovery_elevator_markdown(artifact_data)
    elif (workflow_id, current_stage_id) == ("VALUE_DISCOVERY", "PERSONA"):
        artifact_data = ValueDiscoveryPersonaArtifactData.model_validate(
            payload["artifact_data"]
        )
        markdown = render_value_discovery_persona_markdown(artifact_data)
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


def render_test_design_cases_markdown(data: CasesArtifactData) -> str:
    sections = [
        "# 测试用例集",
        _render_case_statistics(data.case_statistics),
        _render_design_bases(data.design_bases),
        _render_case_groups(data.case_groups),
        _render_test_data_environments(data.test_data_environments),
        _render_automation_candidates(data.automation_candidates),
        _render_coverage_trace(data.coverage_trace),
        _render_open_questions(data.open_questions),
        _render_stage_gate(data.stage_gate),
    ]
    return "\n\n".join(sections)


def render_test_design_delivery_markdown(data: DeliveryArtifactData) -> str:
    sections = [
        "# 测试设计文档",
        _render_delivery_document_info(data.document_info, data.delivery_metrics),
        _render_delivery_executive_summary(data.executive_summary),
        _render_delivery_requirement_summary(data.requirement_summary),
        _render_delivery_strategy_summary(data.strategy_summary_items),
        _render_delivery_case_summary(data.case_summary_items),
        _render_delivery_coverage_map(data.coverage_map),
        _render_delivery_open_risks(data.open_risks),
        _render_delivery_acceptance_checklist(data.acceptance_checklist),
        _render_delivery_signoffs(data.signoffs),
        _render_delivery_change_log(data.change_log),
    ]
    return "\n\n".join(sections)


def render_req_review_review_markdown(data: ReqReviewArtifactData) -> str:
    sections = [
        "# 需求评审问题清单",
        _render_req_review_info(data.review_info),
        _render_req_review_scope(data.scope_items),
        _render_req_review_quality_overview(data.quality_overview),
        _render_req_review_quality_flowchart(),
        _render_req_review_issue_statistics(
            data.issue_statistics, data.quality_overview
        ),
        _render_req_review_issue_groups(data.issue_groups),
        _render_req_review_revision_suggestions(data.revision_suggestions),
        _render_req_review_stage_gate(data.stage_gate),
    ]
    return "\n\n".join(sections)


def render_req_review_report_markdown(data: ReqReviewReportArtifactData) -> str:
    sections = [
        "# 需求评审报告",
        _render_req_review_report_conclusion(data.conclusion),
        _render_req_review_report_info(data.review_info),
        _render_req_review_report_statistics(data.issue_statistics),
        _render_req_review_report_priority_board(data.issue_closures),
        _render_req_review_report_issue_closures(data.issue_closures),
        _render_req_review_report_conditions(data.review_conditions),
        _render_req_review_report_signoffs(data.signoffs),
        _render_req_review_report_change_log(data.change_log),
    ]
    return "\n\n".join(sections)


def render_value_discovery_elevator_markdown(
    data: ValueDiscoveryElevatorArtifactData,
) -> str:
    sections = [
        "# 价值定位分析",
        _render_value_positioning_summary(data.positioning_summary),
        _render_value_flow(data.value_flow),
        _render_target_scenarios(data.target_scenarios),
        _render_pain_evidence(data.pain_evidence),
        _render_differentiators(data.differentiators),
        _render_business_feasibility(data.business_feasibility),
        _render_value_score_matrix(data.score_matrix, data.score_summary),
        _render_value_assumptions(data.assumptions),
        _render_elevator_pitch(data.elevator_pitch),
        _render_value_stage_gate(data.stage_gate),
    ]
    return "\n\n".join(sections)


def render_value_discovery_persona_markdown(
    data: ValueDiscoveryPersonaArtifactData,
) -> str:
    sections = [
        "# 用户画像分析",
        _render_persona_summary(data.persona_summary),
        _render_persona_profiles(data.personas),
        _render_persona_behavior_scenarios(data.behavior_scenarios, data.personas),
        _render_persona_decision_chain(data.decision_chain, data.personas),
        _render_persona_pain_evidence(data.pain_evidence, data.personas),
        _render_anti_personas(data.anti_personas),
        _render_persona_priority_ranking(data.priority_ranking, data.personas),
        _render_value_stage_gate(data.stage_gate),
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


def _render_case_statistics(statistics: CaseStatistics) -> str:
    rows = [
        ("用例总数", statistics.total),
        ("P0 用例数", statistics.p0_count),
        ("P1 用例数", statistics.p1_count),
        ("P2 用例数", statistics.p2_count),
    ]
    return (
        "## 1. 用例统计\n"
        + _markdown_table(["指标", "数量"], rows)
        + "\n\n"
        + f"**统计摘要**：共 {statistics.total} 条用例，"
        + f"P0: {statistics.p0_count} 条 | "
        + f"P1: {statistics.p1_count} 条 | "
        + f"P2: {statistics.p2_count} 条"
    )


def _render_design_bases(bases: list[DesignBasis]) -> str:
    rows = [
        (
            item.basis_id,
            item.source_type,
            item.source_id,
            item.basis,
            item.case_direction,
        )
        for item in bases
    ]
    return "## 2. 用例设计依据\n" + _markdown_table(
        ["依据 ID", "来源类型", "来源 ID", "设计依据", "派生用例方向"],
        rows,
    )


def _render_case_groups(groups: list[CaseGroup]) -> str:
    sections = ["## 3. 按维度分组的用例清单"]
    headers = [
        "ID",
        "用例标题",
        "优先级",
        "测试维度",
        "关联测试点",
        "关联风险",
        "前置条件",
        "操作步骤",
        "测试数据",
        "预期结果",
        "断言",
        "执行层级",
        "自动化建议",
        "状态",
    ]
    for index, group in enumerate(groups, start=1):
        rows = [
            (
                item.case_id,
                item.title,
                item.priority,
                item.dimension,
                item.test_point,
                item.risk,
                item.precondition,
                item.steps,
                item.test_data,
                item.expected_result,
                item.assertion,
                item.execution_layer,
                item.automation_suggestion,
                item.status,
            )
            for item in group.cases
        ]
        sections.append(
            f"### 3.{index} {group.dimension}\n" + _markdown_table(headers, rows)
        )
    return "\n\n".join(sections)


def _render_test_data_environments(items: list[TestDataEnvironment]) -> str:
    rows = [
        (
            item.data_id,
            item.type,
            item.content,
            item.preparation,
            item.related_cases,
            item.status,
        )
        for item in items
    ]
    return "## 4. 测试数据与环境\n" + _markdown_table(
        ["数据/环境 ID", "类型", "内容", "准备方式", "关联用例", "状态"],
        rows,
    )


def _render_automation_candidates(items: list[AutomationCandidate]) -> str:
    rows = [
        (
            item.candidate_id,
            item.case_id,
            item.recommended_layer,
            item.value,
            item.prerequisite,
            item.risk_or_limit,
            item.status,
        )
        for item in items
    ]
    return "## 5. 自动化候选\n" + _markdown_table(
        [
            "候选 ID",
            "用例 ID",
            "推荐自动化层级",
            "自动化价值",
            "前置条件",
            "风险或限制",
            "状态",
        ],
        rows,
    )


def _render_coverage_trace(items: list[CoverageTraceItem]) -> str:
    rows = [
        (
            item.test_point,
            item.priority,
            item.risk,
            ", ".join(item.covered_cases),
            item.status,
        )
        for item in items
    ]
    total = len(items)
    covered = sum(1 for item in items if item.status == "已覆盖")
    coverage_rate = (covered / total * 100) if total else 0.0
    return (
        "## 6. 测试点覆盖追溯\n"
        + _markdown_table(
            ["测试点", "优先级", "关联风险", "覆盖用例", "覆盖状态"],
            rows,
        )
        + "\n\n"
        + _render_traceability_matrix_visual(items)
        + "\n\n"
        + f"> **覆盖率**：总覆盖率 {coverage_rate:.1f}%"
    )


def _render_traceability_matrix_visual(items: list[CoverageTraceItem]) -> str:
    visual = {
        "type": "traceability-matrix",
        "title": "测试点-用例覆盖追溯矩阵",
        "columns": ["测试点", "优先级", "关联风险", "覆盖用例", "覆盖状态"],
        "rows": [
            {
                "测试点": item.test_point,
                "优先级": item.priority,
                "关联风险": item.risk,
                "覆盖用例": ", ".join(item.covered_cases),
                "覆盖状态": item.status,
            }
            for item in items
        ],
    }
    return (
        "```ai4se-visual\n" + json.dumps(visual, ensure_ascii=False, indent=2) + "\n```"
    )


def _render_open_questions(items: list[OpenQuestion]) -> str:
    rows = [
        (
            item.question_id,
            item.question,
            item.related,
            item.priority,
            item.blocking,
            item.owner,
            item.status,
        )
        for item in items
    ]
    return "## 7. 开放问题\n" + _markdown_table(
        [
            "问题 ID",
            "问题描述",
            "关联用例/测试点",
            "优先级",
            "阻断性",
            "责任方",
            "状态",
        ],
        rows,
    )


def _render_delivery_document_info(
    info: DocumentInfo,
    metrics: DeliveryMetrics,
) -> str:
    rows = [
        ("Artifact 名称", info.artifact_name),
        ("项目/需求名称", metrics.project_name),
        ("版本", metrics.version),
        ("生成时间", metrics.generated_at),
        ("Workflow", info.workflow),
        ("Stage", info.stage),
        ("交付状态", metrics.delivery_status),
        ("总用例数", metrics.total_cases),
        ("高风险项", metrics.high_risk_count),
        ("状态", info.status),
    ]
    return "## 1. 文档信息\n" + _markdown_table(["字段", "内容"], rows)


def _render_delivery_executive_summary(
    items: list[DeliveryExecutiveSummaryItem],
) -> str:
    rows = [
        (item.summary_item, item.conclusion, item.evidence_source, item.status)
        for item in items
    ]
    return "## 2. 执行摘要\n" + _markdown_table(
        ["摘要项", "结论", "证据来源", "状态"],
        rows,
    )


def _render_delivery_requirement_summary(
    items: list[DeliveryRequirementSummaryItem],
) -> str:
    rows = [
        (item.content_type, item.reference, item.conclusion, item.open_status)
        for item in items
    ]
    return "## 3. 需求分析摘要\n" + _markdown_table(
        ["内容类型", "ID/范围", "核心结论", "开放状态"],
        rows,
    )


def _render_delivery_strategy_summary(
    items: list[DeliveryStrategySummaryItem],
) -> str:
    rows = [
        (item.strategy_item, item.conclusion, item.related, item.coverage_status)
        for item in items
    ]
    return "## 4. 测试策略摘要\n" + _markdown_table(
        ["策略项", "结论", "关联风险/目标", "覆盖状态"],
        rows,
    )


def _render_delivery_case_summary(items: list[DeliveryCaseSummaryItem]) -> str:
    rows = [
        (
            item.dimension,
            item.case_count,
            item.p0_count,
            item.p1_count,
            item.p2_count,
            item.automation_candidates,
            item.blocked_or_needs_env,
        )
        for item in items
    ]
    return "## 5. 测试用例摘要\n" + _markdown_table(
        ["维度", "用例数", "P0", "P1", "P2", "自动化候选", "不可执行/需补环境"],
        rows,
    )


def _render_delivery_coverage_map(items: list[DeliveryCoverageMapItem]) -> str:
    rows = [
        (
            item.requirement,
            item.risk,
            item.test_point,
            ", ".join(item.case_ids),
            item.acceptance_status,
        )
        for item in items
    ]
    return (
        "## 6. 覆盖地图\n"
        + _markdown_table(
            ["需求", "风险", "测试点", "用例", "验收状态"],
            rows,
        )
        + "\n\n"
        + _render_coverage_map_visual(items)
    )


def _render_coverage_map_visual(items: list[DeliveryCoverageMapItem]) -> str:
    visual = {
        "type": "coverage-map",
        "title": "测试交付覆盖地图",
        "columns": ["需求", "风险", "测试点", "用例", "验收状态"],
        "rows": [
            {
                "需求": item.requirement,
                "风险": item.risk,
                "测试点": item.test_point,
                "用例": ", ".join(item.case_ids),
                "验收状态": item.acceptance_status,
            }
            for item in items
        ],
    }
    return (
        "```ai4se-visual\n" + json.dumps(visual, ensure_ascii=False, indent=2) + "\n```"
    )


def _render_delivery_open_risks(items: list[DeliveryOpenRisk]) -> str:
    rows = [
        (
            item.risk_id,
            item.risk_type,
            item.description,
            item.impact,
            item.acceptable,
            item.owner,
            item.next_step,
            item.status,
        )
        for item in items
    ]
    return "## 7. 开放风险\n" + _markdown_table(
        [
            "风险/问题 ID",
            "类型",
            "描述",
            "影响",
            "是否可接受",
            "责任方",
            "后续处理",
            "状态",
        ],
        rows,
    )


def _render_delivery_acceptance_checklist(checks: list[StageGateCheck]) -> str:
    lines = [f"- [{'x' if item.checked else ' '}] {item.item}" for item in checks]
    return "## 8. 交付验收清单\n" + "\n".join(lines)


def _render_delivery_signoffs(items: list[DeliverySignoff]) -> str:
    rows = [(item.role, item.owner, item.opinion, item.status) for item in items]
    return "## 9. 签署确认\n" + _markdown_table(
        ["角色", "姓名/责任方", "签署意见", "状态"],
        rows,
    )


def _render_delivery_change_log(items: list[DeliveryChangeLogItem]) -> str:
    rows = [
        (item.version, item.date, item.change, item.reason, item.owner)
        for item in items
    ]
    return "## 10. 变更记录\n" + _markdown_table(
        ["版本", "日期", "变更内容", "变更原因", "责任方"],
        rows,
    )


def _render_req_review_info(info: ReqReviewInfo) -> str:
    rows = [
        ("Artifact 名称", info.artifact_name),
        ("被评审需求", info.requirement_name),
        ("评审时间", info.review_date),
        ("需求概述", info.requirement_summary),
        ("评审结论倾向", info.conclusion),
    ]
    return "## 评审信息\n" + _markdown_table(["字段", "内容"], rows)


def _render_req_review_scope(items: list[ReqReviewScopeItem]) -> str:
    rows = [
        (item.scope_type, item.content, item.review_impact, item.status)
        for item in items
    ]
    return "## 评审范围与不评审范围\n" + _markdown_table(
        ["类型", "内容", "评审影响", "状态"],
        rows,
    )


def _render_req_review_quality_overview(
    items: list[ReqReviewQualityOverviewItem],
) -> str:
    rows = [
        (
            item.dimension,
            item.quality_judgement,
            item.severity_score,
            item.evidence,
            item.testing_risk,
            item.status,
        )
        for item in items
    ]
    return "## 需求质量总览\n" + _markdown_table(
        ["评审维度", "质量判断", "严重度评分(1-5)", "主要证据", "测试风险", "状态"],
        rows,
    )


def _render_req_review_quality_flowchart() -> str:
    return """## 需求质量结构图
```mermaid
flowchart TD
    Req["需求文档输入"] --> Scope["评审范围确认"]
    Scope --> Quality["质量维度扫描"]
    Quality --> Testability["可测试性"]
    Quality --> Completeness["功能完整性"]
    Quality --> Rules["边界与规则"]
    Quality --> Exception["异常闭环"]
    Quality --> NonFunctional["非功能需求"]
    Testability --> Issues["问题分级 P0/P1/P2"]
    Completeness --> Issues
    Rules --> Issues
    Exception --> Issues
    NonFunctional --> Issues
    Issues --> Fix["修订建议与责任方"]
    Fix --> Report["评审报告与复审条件"]
```"""


def _render_req_review_issue_statistics(
    statistics: ReqReviewIssueStatistics,
    quality_overview: list[ReqReviewQualityOverviewItem],
) -> str:
    rows = [
        ("P0 (阻塞)", statistics.p0_count, statistics.p0_description),
        ("P1 (重要)", statistics.p1_count, statistics.p1_description),
        ("P2 (建议)", statistics.p2_count, statistics.p2_description),
    ]
    return (
        "## 问题统计\n"
        + _markdown_table(["优先级", "数量", "说明"], rows)
        + "\n\n"
        + _render_req_review_score_matrix(quality_overview)
    )


def _render_req_review_score_matrix(
    items: list[ReqReviewQualityOverviewItem],
) -> str:
    visual = {
        "type": "score-matrix",
        "title": "需求质量评审维度评分矩阵",
        "columns": ["评审维度", "严重度评分", "主要证据", "测试风险"],
        "rows": [
            {
                "评审维度": item.dimension,
                "严重度评分": item.severity_score,
                "主要证据": item.evidence,
                "测试风险": item.testing_risk,
            }
            for item in items
        ],
    }
    return (
        "```ai4se-visual\n" + json.dumps(visual, ensure_ascii=False, indent=2) + "\n```"
    )


def _render_req_review_issue_groups(groups: list[ReqReviewIssueGroup]) -> str:
    sections = ["## 按维度问题清单"]
    headers = [
        "ID",
        "评审维度",
        "问题描述",
        "优先级",
        "阻断性",
        "所属需求章节",
        "影响范围",
        "证据/依据",
        "建议",
        "责任方/确认人",
        "状态",
    ]
    for index, group in enumerate(groups, start=1):
        rows = [
            (
                item.issue_id,
                item.dimension,
                item.description,
                item.priority,
                item.blocking,
                item.requirement_section,
                item.impact,
                item.evidence,
                item.suggestion,
                item.owner,
                item.status,
            )
            for item in group.issues
        ]
        sections.append(
            f"### {index}. {group.dimension}\n" + _markdown_table(headers, rows)
        )
    return "\n\n".join(sections)


def _render_req_review_revision_suggestions(
    items: list[ReqReviewRevisionSuggestion],
) -> str:
    rows = [
        (
            item.suggestion_id,
            ", ".join(item.related_issues),
            item.suggestion,
            item.acceptance,
            item.owner,
            item.status,
        )
        for item in items
    ]
    return "## 修订建议\n" + _markdown_table(
        ["建议 ID", "关联问题", "修订建议", "验收口径", "责任方/确认人", "状态"],
        rows,
    )


def _render_req_review_stage_gate(checks: list[StageGateCheck]) -> str:
    lines = [f"- [{'x' if item.checked else ' '}] {item.item}" for item in checks]
    return "## 阶段门禁\n" + "\n".join(lines)


def _render_req_review_report_conclusion(
    conclusion: ReqReviewReportConclusion,
) -> str:
    rows = [
        ("Artifact 名称", conclusion.artifact_name),
        ("评审结果", conclusion.review_result),
        ("结论理由", conclusion.reason),
        ("是否允许进入开发/测试设计", conclusion.development_gate),
        ("需要复审", conclusion.needs_recheck),
    ]
    return (
        "## 评审结论\n"
        + _markdown_table(["字段", "内容"], rows)
        + "\n\n"
        + f"> {conclusion.summary}"
        + "\n\n"
        + "### 判定标准\n"
        + "- **通过**：无 P0 问题，且 P1 问题均已有明确处理方案\n"
        + "- **有条件通过**：无 P0 问题，但存在未解决的 P1 问题，需在开发阶段同步明确\n"
        + "- **不通过**：存在 P0 阻塞性问题，必须修订需求后重新评审"
    )


def _render_req_review_report_info(info: ReqReviewReportInfo) -> str:
    rows = [
        ("被评审需求", info.requirement_name),
        ("评审时间", info.review_date),
        ("评审输入", info.review_input),
        ("评审参与方", info.participants),
    ]
    return "## 评审信息\n" + _markdown_table(["字段", "内容"], rows)


def _render_req_review_report_statistics(
    statistics: ReqReviewReportIssueStatistics,
) -> str:
    total = statistics.p0_count + statistics.p1_count + statistics.p2_count
    return (
        "## 问题统计\n"
        + "```mermaid\n"
        + "pie title 评审问题优先级分布\n"
        + f'    "P0 (阻塞)" : {statistics.p0_count}\n'
        + f'    "P1 (重要)" : {statistics.p1_count}\n'
        + f'    "P2 (建议)" : {statistics.p2_count}\n'
        + "```\n\n"
        + f"**统计摘要**：共 {total} 个问题，P0: {statistics.p0_count} 个 | "
        + f"P1: {statistics.p1_count} 个 | P2: {statistics.p2_count} 个"
    )


def _render_req_review_report_priority_board(
    items: list[ReqReviewReportIssueClosure],
) -> str:
    visual = {
        "type": "priority-board",
        "title": "评审问题优先级看板",
        "columns": ["问题", "优先级", "影响范围", "责任方", "下一步", "关闭状态"],
        "rows": [
            {
                "问题": item.description,
                "优先级": item.priority,
                "影响范围": item.impact,
                "责任方": item.owner,
                "下一步": item.next_step,
                "关闭状态": item.closure_status,
            }
            for item in items
        ],
    }
    return (
        "## 优先级看板\n"
        + "```ai4se-visual\n"
        + json.dumps(visual, ensure_ascii=False, indent=2)
        + "\n```"
    )


def _render_req_review_report_issue_closures(
    items: list[ReqReviewReportIssueClosure],
) -> str:
    sections = ["## 问题关闭清单"]
    sections.append(
        _render_req_review_report_issue_closure_group(
            "### P0 阻塞性问题",
            [item for item in items if item.priority == "P0"],
            include_impact=True,
            include_recheck=True,
        )
    )
    sections.append(
        _render_req_review_report_issue_closure_group(
            "### P1 重要问题",
            [item for item in items if item.priority == "P1"],
            include_impact=True,
            include_recheck=True,
        )
    )
    sections.append(
        _render_req_review_report_issue_closure_group(
            "### P2 优化建议",
            [item for item in items if item.priority == "P2"],
            include_impact=False,
            include_recheck=False,
        )
    )
    return "\n\n".join(sections)


def _render_req_review_report_issue_closure_group(
    title: str,
    items: list[ReqReviewReportIssueClosure],
    *,
    include_impact: bool,
    include_recheck: bool,
) -> str:
    if include_impact and include_recheck:
        rows = [
            (
                item.issue_id,
                item.description,
                item.requirement_section,
                item.impact,
                item.owner,
                item.next_step,
                item.closure_status,
                item.recheck_condition,
            )
            for item in items
        ]
        return (
            title
            + "\n"
            + _markdown_table(
                [
                    "ID",
                    "问题描述",
                    "所属需求章节",
                    "影响范围",
                    "责任方",
                    "下一步",
                    "关闭状态",
                    "复审条件",
                ],
                rows,
            )
        )

    rows = [
        (
            item.issue_id,
            item.description,
            item.requirement_section,
            item.owner,
            item.next_step,
            item.closure_status,
        )
        for item in items
    ]
    return (
        title
        + "\n"
        + _markdown_table(
            ["ID", "问题描述", "所属需求章节", "责任方", "下一步", "关闭状态"],
            rows,
        )
    )


def _render_req_review_report_conditions(
    items: list[ReqReviewReportCondition],
) -> str:
    rows = [
        (
            item.condition_id,
            item.condition,
            ", ".join(item.related_issues),
            item.verification,
            item.owner,
            item.status,
        )
        for item in items
    ]
    return "## 复审条件\n" + _markdown_table(
        ["条件 ID", "复审条件", "关联问题", "验证方式", "责任方", "状态"],
        rows,
    )


def _render_req_review_report_signoffs(items: list[ReqReviewReportSignoff]) -> str:
    rows = [(item.role, item.owner, item.opinion, item.status) for item in items]
    return "## 签署确认\n" + _markdown_table(
        ["角色", "姓名/责任方", "签署意见", "签署状态"],
        rows,
    )


def _render_req_review_report_change_log(
    items: list[ReqReviewReportChangeLogItem],
) -> str:
    rows = [
        (item.version, item.date, item.change, item.reason, item.owner)
        for item in items
    ]
    return "## 变更记录\n" + _markdown_table(
        ["版本", "日期", "变更内容", "变更原因", "责任方"],
        rows,
    )


def _render_value_positioning_summary(summary: PositioningSummary) -> str:
    rows = [
        ("Artifact 名称", "价值定位诊断报告"),
        ("一句话定位", summary.one_liner),
        ("核心用户", summary.core_user),
        ("核心痛点", summary.core_pain),
        ("独特价值", summary.unique_value),
        ("当前判断", summary.current_judgement),
    ]
    return "## 定位摘要\n" + _markdown_table(["字段", "内容"], rows)


def _render_value_flow(flow: ValueFlow) -> str:
    node_lookup = {node.node_id: node for node in flow.nodes}
    safe_ids: dict[str, str] = {}
    rendered_ids = {
        node.node_id: _node_id(node.node_id, safe_ids) for node in flow.nodes
    }
    lines = ["```mermaid", "flowchart TD"]
    for node in flow.nodes:
        lines.append(
            f'    {rendered_ids[node.node_id]}["{_escape_mermaid_label(node.label)}<br/>'
            f'{_escape_mermaid_label(node.description)}"]'
        )
    for link in flow.links:
        lines.append(
            f"    {rendered_ids[link.from_node]} -->|"
            f'"{_escape_mermaid_label(link.label)}"| '
            f"{rendered_ids[link.to_node]}"
        )
    lines.append("```")

    rows = [
        (node.node_id, node.label, node.description) for node in node_lookup.values()
    ]
    return (
        "## 价值结构图\n"
        + "\n".join(lines)
        + "\n\n"
        + _markdown_table(["节点 ID", "节点", "说明"], rows)
    )


def _render_target_scenarios(items: list[TargetScenario]) -> str:
    rows = [
        (item.dimension, item.description, item.evidence_level, item.status)
        for item in items
    ]
    return "## 目标用户与场景\n" + _markdown_table(
        ["维度", "描述", "证据等级", "状态"],
        rows,
    )


def _render_pain_evidence(items: list[PainEvidence]) -> str:
    rows = [
        (
            item.pain_id,
            item.description,
            item.scene,
            item.impact,
            item.evidence_level,
            item.validation_action,
            item.status,
        )
        for item in items
    ]
    return "## 痛点证据\n" + _markdown_table(
        ["痛点 ID", "痛点描述", "发生场景", "影响程度", "证据等级", "验证动作", "状态"],
        rows,
    )


def _render_differentiators(items: list[Differentiator]) -> str:
    rows = [
        (
            item.dimension,
            item.our_value,
            item.existing_solution,
            item.evidence,
            item.status,
        )
        for item in items
    ]
    return "## 差异化价值\n" + _markdown_table(
        ["维度", "我们", "现有方案/竞品", "差异化证据", "状态"],
        rows,
    )


def _render_business_feasibility(items: list[BusinessFeasibility]) -> str:
    rows = [
        (
            item.dimension,
            item.judgement,
            item.basis,
            item.validation_action,
            item.status,
        )
        for item in items
    ]
    return "## 商业可行性\n" + _markdown_table(
        ["维度", "判断", "依据", "验证动作", "状态"],
        rows,
    )


def _render_value_score_matrix(
    items: list[ValueScore],
    summary: ValueScoreSummary,
) -> str:
    rows = [
        (item.dimension, item.score, item.basis, item.next_validation) for item in items
    ]
    visual = {
        "type": "score-matrix",
        "title": "价值主张初筛评分矩阵",
        "columns": ["评估维度", "评分", "依据", "下一步验证"],
        "rows": [
            {
                "评估维度": item.dimension,
                "评分": item.score,
                "依据": item.basis,
                "下一步验证": item.next_validation,
            }
            for item in items
        ],
    }
    return (
        "## 价值主张评分\n"
        + _markdown_table(["评估维度", "评分", "依据", "下一步验证"], rows)
        + "\n\n"
        + "```ai4se-visual\n"
        + json.dumps(visual, ensure_ascii=False, indent=2)
        + "\n```"
        + "\n\n"
        + f"> **评分结论**：总分 {summary.total_score}，平均分 "
        + f"{summary.average_score:.2f}。{summary.judgement}"
    )


def _render_value_assumptions(items: list[ValueAssumption]) -> str:
    rows = [
        (
            item.assumption_id,
            item.content,
            item.impact,
            item.validation_action,
            item.owner,
            item.status,
        )
        for item in items
    ]
    return "## 未验证假设\n" + _markdown_table(
        ["假设 ID", "假设内容", "影响范围", "验证动作", "责任方/验证人", "状态"],
        rows,
    )


def _render_elevator_pitch(pitch: str) -> str:
    return "## 60 秒电梯演讲\n\n> " + pitch


def _render_value_stage_gate(checks: list[StageGateCheck]) -> str:
    lines = [f"- [{'x' if item.checked else ' '}] {item.item}" for item in checks]
    return "## 阶段门禁\n" + "\n".join(lines)


def _persona_names(personas: list[PersonaProfile]) -> dict[str, str]:
    return {persona.persona_id: persona.name for persona in personas}


def _render_persona_summary(summary: PersonaSummary) -> str:
    rows = [
        ("Artifact 名称", summary.artifact_name),
        ("核心用户判断", summary.core_user_judgement),
        ("主要痛点", summary.primary_pain),
        ("验证状态", summary.validation_status),
        ("进入旅程阶段判断", summary.journey_readiness),
    ]
    return "## 画像摘要\n" + _markdown_table(["字段", "内容"], rows)


def _render_persona_profiles(personas: list[PersonaProfile]) -> str:
    sections = ["## 主要用户画像"]
    for index, persona in enumerate(personas, start=1):
        basic_rows = [
            (
                item.dimension,
                item.description,
                item.evidence_level,
                item.validation_status,
            )
            for item in persona.basic_features
        ]
        behavior_rows = [
            (
                item.dimension,
                item.description,
                item.trigger,
                item.evidence_level,
                item.validation_status,
            )
            for item in persona.behavior_features
        ]
        sections.append(
            f"### 画像 {index}\n\n"
            f"**用户类型名称**：{persona.name}（{persona.priority}）\n\n"
            f"> {persona.summary}\n\n"
            "#### 基础特征\n"
            + _markdown_table(
                ["维度", "描述", "证据等级", "验证状态"],
                basic_rows,
            )
            + "\n\n"
            + "#### 行为特征\n"
            + _markdown_table(
                ["维度", "描述", "场景触发", "证据等级", "验证状态"],
                behavior_rows,
            )
        )
    return "\n\n".join(sections)


def _render_persona_behavior_scenarios(
    items: list[PersonaBehaviorScenario],
    personas: list[PersonaProfile],
) -> str:
    persona_names = _persona_names(personas)
    rows = [
        (
            item.scenario_id,
            persona_names[item.persona_id],
            item.scenario,
            item.trigger,
            item.user_goal,
            item.current_solution,
            item.status,
        )
        for item in items
    ]
    return "## 行为与场景\n" + _markdown_table(
        ["场景 ID", "用户类型", "场景描述", "触发条件", "用户目标", "当前做法", "状态"],
        rows,
    )


def _render_persona_decision_chain(
    items: list[PersonaDecisionRole],
    personas: list[PersonaProfile],
) -> str:
    persona_names = _persona_names(personas)
    rows = [
        (
            item.role,
            persona_names[item.persona_id],
            item.concern,
            item.influence,
            item.payment_relation,
            item.evidence_level,
            item.validation_status,
        )
        for item in items
    ]
    return "## 决策链\n" + _markdown_table(
        [
            "决策角色",
            "用户类型/岗位",
            "关注点",
            "影响力",
            "付费/采购关系",
            "证据等级",
            "验证状态",
        ],
        rows,
    )


def _render_persona_pain_evidence(
    items: list[PersonaPainEvidence],
    personas: list[PersonaProfile],
) -> str:
    persona_names = _persona_names(personas)
    rows = [
        (
            item.pain_id,
            persona_names[item.persona_id],
            item.pain,
            item.frequency,
            item.impact,
            item.existing_solution_gap,
            item.evidence_level,
            item.validation_status,
        )
        for item in items
    ]
    return "## 痛点证据\n" + _markdown_table(
        [
            "痛点 ID",
            "用户类型",
            "痛点",
            "频率",
            "影响程度",
            "现有方案不足",
            "证据等级",
            "验证状态",
        ],
        rows,
    )


def _render_anti_personas(items: list[AntiPersona]) -> str:
    rows = [
        (item.name, item.reason, item.boundary, item.risk, item.status)
        for item in items
    ]
    return "## 反画像\n" + _markdown_table(
        ["非目标用户", "为什么不是当前核心用户", "不服务的边界", "风险", "状态"],
        rows,
    )


def _render_persona_priority_ranking(
    items: list[PersonaPriorityRanking],
    personas: list[PersonaProfile],
) -> str:
    persona_names = _persona_names(personas)
    rows = [
        (
            item.priority,
            persona_names[item.persona_id],
            item.reason,
            item.related_pain,
            item.evidence_level,
            item.validation_status,
        )
        for item in items
    ]
    return "## 用户优先级排序\n" + _markdown_table(
        ["优先级", "用户类型", "理由", "关联痛点", "证据等级", "验证状态"],
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
