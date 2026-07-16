import json
import re
from typing import Any, Callable, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from agent_contracts import AgentTurnOutput

from artifact_render_plan import (
    ArtifactRenderPlan,
    ArtifactSectionSpec,
    RenderedArtifact,
)

from artifact_data_renderer_base import (
    DocumentInfo,
    StageGateCheck,
    StrictArtifactDataModel,
)
from artifact_data_value_schema import (
    PositioningSummary,
    ValueFlowNode,
    ValueFlowLink,
    ValueFlow,
    TargetScenario,
    PainEvidence,
    Differentiator,
    BusinessFeasibility,
    ValueScore,
    ValueScoreSummary,
    ValueAssumption,
    ValueDiscoveryElevatorArtifactData,
    normalize_value_score_summary,
    validate_blueprint_acceptance_criteria,
    validate_blueprint_handoff_inputs,
    validate_blueprint_main_flow,
    validate_blueprint_requirement_references,
    validate_journey_opportunity_references,
    validate_journey_opportunity_scores,
    validate_journey_pain_priorities,
    validate_journey_stages,
    validate_persona_ids,
    validate_persona_priority_ranking,
    validate_persona_references,
    validate_value_flow_references,
    PersonaSummary,
    PersonaFeature,
    PersonaBehaviorFeature,
    PersonaProfile,
    PersonaBehaviorScenario,
    PersonaDecisionRole,
    PersonaPainEvidence,
    AntiPersona,
    PersonaPriorityRanking,
    ValueDiscoveryPersonaArtifactData,
    JourneySummary,
    JourneyStage,
    JourneyPainPriority,
    JourneyOpportunityScore,
    JourneyEntryStrategy,
    JourneyValidationExperiment,
    ValueDiscoveryJourneyArtifactData,
    BlueprintDocumentInfo,
    BlueprintProductOverview,
    BlueprintTargetUser,
    BlueprintFeatureItem,
    BlueprintFeatureModule,
    BlueprintRequirement,
    BlueprintFlowNode,
    BlueprintFlowLink,
    BlueprintMainFlow,
    BlueprintSuccessMetric,
    BlueprintMvpFeature,
    BlueprintIteration,
    BlueprintMvpPlan,
    BlueprintNonFunctionalRequirement,
    BlueprintAcceptanceCriterion,
    BlueprintRoadmapItem,
    BlueprintRisk,
    BlueprintLisaHandoffInput,
    ValueDiscoveryBlueprintArtifactData,
)


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


ClarificationQuestionStatus = Literal[
    "待确认",
    "已确认",
    "已假设",
    "AI 假设",
]


class ClarificationQuestion(StrictArtifactDataModel):
    question_id: str
    question: str
    priority: str
    blocking: str
    impact: str
    assumption: str
    owner: str
    status: ClarificationQuestionStatus


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


class IdeaProblemStatement(StrictArtifactDataModel):
    target_user: str
    scenario: str
    core_pain: str
    existing_alternative: str
    alternative_gap: str
    consequence: str
    validation_status: str


class IdeaTargetUser(StrictArtifactDataModel):
    dimension: str
    description: str
    evidence_level: str
    validation_status: str


class IdeaSubproblem(StrictArtifactDataModel):
    problem_id: str
    problem: str
    symptoms: list[str] = Field(min_length=1)


class IdeaProblemLandscape(StrictArtifactDataModel):
    root_problem: str
    subproblems: list[IdeaSubproblem] = Field(min_length=1)


class IdeaEvidenceItem(StrictArtifactDataModel):
    evidence_id: str
    related_problem: str
    source: str
    evidence_level: str
    validation_action: str
    owner: str
    validation_status: str


class IdeaProblemUserFit(StrictArtifactDataModel):
    dimension: str
    current_judgement: str
    evidence_or_assumption: str
    evidence_ids: list[str] = Field(min_length=1)
    validation_action: str
    validation_status: str


class IdeaConstraintBoundary(StrictArtifactDataModel):
    boundary_type: str
    content: str
    impact: str
    status: str


class IdeaReverseValidation(StrictArtifactDataModel):
    failure_hypothesis: str
    trigger_signal: str
    validation_action: str
    validation_status: str


class IdeaDefineArtifactData(StrictArtifactDataModel):
    problem_statement: IdeaProblemStatement
    target_users: list[IdeaTargetUser] = Field(min_length=1)
    problem_landscape: IdeaProblemLandscape
    evidence_items: list[IdeaEvidenceItem] = Field(min_length=1)
    problem_user_fit: list[IdeaProblemUserFit] = Field(min_length=1)
    constraints_boundaries: list[IdeaConstraintBoundary] = Field(min_length=1)
    reverse_validation: list[IdeaReverseValidation] = Field(min_length=1)
    stage_gate: list[StageGateCheck] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_idea_define_consistency(self) -> "IdeaDefineArtifactData":
        _validate_idea_define_evidence(self)
        _validate_idea_define_landscape(self)
        _validate_idea_define_fit(self)
        _validate_checked_stage_gate(self)
        return self


class IdeaDivergenceMethod(StrictArtifactDataModel):
    method_name: str
    goal: str
    input_basis: str
    coverage_dimensions: list[str] = Field(min_length=1)
    constraints: str


class IdeaLandscapeGroup(StrictArtifactDataModel):
    group_id: str
    theme: str
    idea_ids: list[str] = Field(min_length=1)


class IdeaDivergeLandscape(StrictArtifactDataModel):
    root_theme: str
    groups: list[IdeaLandscapeGroup] = Field(min_length=1)


class IdeaCard(StrictArtifactDataModel):
    idea_id: str
    title: str
    one_liner: str
    target_user: str
    scenario: str
    value_proposition: str
    key_hypotheses: list[str] = Field(min_length=1)
    novelty_source: str
    evidence_level: str
    validation_action: str
    status: str
    status_reason: str


class IdeaSource(StrictArtifactDataModel):
    source_id: str
    source_type: str
    source: str
    idea_ids: list[str] = Field(min_length=1)
    key_assumption: str
    status_reason: str


class IdeaParkedOrExcludedRecord(StrictArtifactDataModel):
    record_id: str
    idea_or_direction: str
    reason: str
    revisit_condition: str
    status_reason: str


class IdeaDivergeArtifactData(StrictArtifactDataModel):
    divergence_method: IdeaDivergenceMethod
    idea_landscape: IdeaDivergeLandscape
    idea_cards: list[IdeaCard] = Field(min_length=1)
    idea_sources: list[IdeaSource] = Field(min_length=1)
    parked_or_excluded: list[IdeaParkedOrExcludedRecord] = Field(min_length=1)
    stage_gate: list[StageGateCheck] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_idea_diverge_consistency(self) -> "IdeaDivergeArtifactData":
        _validate_idea_cards(self)
        _validate_idea_landscape(self)
        _validate_idea_sources(self)
        _validate_idea_parked(self)
        _validate_checked_stage_gate(self)
        return self


class IdeaDecisionItem(StrictArtifactDataModel):
    idea_id: str
    idea_name: str
    decision: str
    reason: str
    evidence_source: str


class IdeaDecisionMatrix(StrictArtifactDataModel):
    scoring_rubric: str
    recommended_idea_id: str
    recommendation: str
    user_confirmation_status: str
    decision_items: list[IdeaDecisionItem] = Field(min_length=1)


class IdeaIceEvaluation(StrictArtifactDataModel):
    idea_id: str
    idea_name: str
    impact: int = Field(ge=1, le=5)
    confidence: int = Field(ge=1, le=5)
    effort: int = Field(ge=1, le=5)
    ice_score: float | None = None
    rank: int | None = Field(default=None, ge=1)
    conclusion: str
    elimination_reason: str
    evidence_source: str
    next_validation: str


class IdeaResourceConstraint(StrictArtifactDataModel):
    constraint_type: str
    content: str
    impact: str
    handling: str
    status: str


class IdeaSensitivityItem(StrictArtifactDataModel):
    variable: str
    change: str
    impact: str
    signal: str
    next_validation: str


class IdeaValidationExperiment(StrictArtifactDataModel):
    experiment_id: str
    idea_ids: list[str] = Field(min_length=1)
    goal: str
    method: str
    success_metric: str
    owner: str
    next_validation: str
    status: str


class IdeaMergePath(StrictArtifactDataModel):
    path_id: str
    source_idea_ids: list[str] = Field(min_length=1)
    merge_logic: str
    integrated_concept: str
    applicable_condition: str
    risk: str
    user_confirmation_status: str


class IdeaConvergeArtifactData(StrictArtifactDataModel):
    decision_matrix: IdeaDecisionMatrix
    ice_evaluations: list[IdeaIceEvaluation] = Field(min_length=1)
    resource_constraints: list[IdeaResourceConstraint] = Field(min_length=1)
    sensitivity_analysis: list[IdeaSensitivityItem] = Field(min_length=1)
    validation_experiments: list[IdeaValidationExperiment] = Field(min_length=1)
    merge_paths: list[IdeaMergePath] = Field(min_length=1)
    stage_gate: list[StageGateCheck] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_idea_converge_consistency(self) -> "IdeaConvergeArtifactData":
        _normalize_idea_ice(self)
        _validate_idea_decision(self)
        _validate_idea_experiments(self)
        _validate_idea_merge_paths(self)
        _validate_checked_stage_gate(self)
        return self


class IdeaPositioningStatement(StrictArtifactDataModel):
    target_user: str
    user_need: str
    product_name: str
    category: str
    value_proposition: str
    alternative: str
    differentiation: str


class IdeaCoreAssumption(StrictArtifactDataModel):
    assumption_id: str
    assumption: str
    source: str
    importance: str
    validation_action: str
    owner: str
    status: str


class IdeaLeanCanvasCell(StrictArtifactDataModel):
    cell: str
    content: str


class IdeaMvpFeature(StrictArtifactDataModel):
    module: str
    mvp_level: str
    user_value: str
    validation_metric: str
    tradeoff_reason: str
    assumption_ids: list[str] = Field(min_length=1)
    status: str


class IdeaGrowthFunnelStage(StrictArtifactDataModel):
    stage: str
    user_behavior: str
    metric: str
    mvp_implementation: str


class IdeaPremortemRisk(StrictArtifactDataModel):
    risk_id: str
    dimension: str
    failure_reason: str
    likelihood: str
    mitigation: str


class IdeaValidationRoadmapItem(StrictArtifactDataModel):
    validation_id: str
    stage: str
    goal: str
    experiment: str
    success_metric: str
    time_window: str
    owner: str
    status: str
    assumption_ids: list[str] = Field(min_length=1)


class IdeaOutOfScopeItem(StrictArtifactDataModel):
    item: str
    reason: str
    reconsider_condition: str
    status: str


class IdeaDecisionRecord(StrictArtifactDataModel):
    decision: str
    conclusion: str
    basis: str
    decider: str
    date: str
    status: str


class IdeaNextAction(StrictArtifactDataModel):
    action_id: str
    action: str
    related_ids: list[str] = Field(min_length=1)
    owner: str
    due_date: str
    acceptance: str
    status: str


class IdeaConceptArtifactData(StrictArtifactDataModel):
    positioning_statement: IdeaPositioningStatement
    core_assumptions: list[IdeaCoreAssumption] = Field(min_length=1)
    lean_canvas: list[IdeaLeanCanvasCell] = Field(min_length=1)
    mvp_features: list[IdeaMvpFeature] = Field(min_length=1)
    growth_funnel: list[IdeaGrowthFunnelStage] = Field(min_length=1)
    premortem_risks: list[IdeaPremortemRisk] = Field(min_length=1)
    validation_roadmap: list[IdeaValidationRoadmapItem] = Field(min_length=1)
    out_of_scope: list[IdeaOutOfScopeItem] = Field(min_length=1)
    decision_records: list[IdeaDecisionRecord] = Field(min_length=1)
    next_actions: list[IdeaNextAction] = Field(min_length=1)
    stage_gate: list[StageGateCheck] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_idea_concept_consistency(self) -> "IdeaConceptArtifactData":
        _validate_idea_assumptions(self)
        _validate_idea_canvas(self)
        _validate_idea_mvp(self)
        _validate_idea_funnel(self)
        _validate_idea_roadmap(self)
        _validate_idea_next_actions(self)
        _validate_checked_stage_gate(self)
        return self


class IncidentSummary(StrictArtifactDataModel):
    incident_name: str
    severity: str
    detected_at: str
    recovered_at: str
    duration: str
    impact_scope: str
    current_status: str


class IncidentImpactMetric(StrictArtifactDataModel):
    dimension: str
    quantification: str
    confidence: str
    source: str
    status: str


class IncidentFactSource(StrictArtifactDataModel):
    fact_id: str
    fact: str
    source: str
    confidence: str
    status: str


class IncidentTimelineEvent(StrictArtifactDataModel):
    section: str
    occurred_at: str
    event: str
    fact_ids: list[str] = Field(min_length=1)


class IncidentFactSeparationItem(StrictArtifactDataModel):
    item_type: str
    content: str
    handling: str
    blocking: str
    status: str


class IncidentParticipant(StrictArtifactDataModel):
    role: str
    person: str
    action: str
    participated_at: str
    status: str


class IncidentMissingInformation(StrictArtifactDataModel):
    item: str
    reason: str
    supplement_method: str
    blocking: str
    owner: str
    status: str


class IncidentTimelineArtifactData(StrictArtifactDataModel):
    incident_summary: IncidentSummary
    impact_metrics: list[IncidentImpactMetric] = Field(min_length=1)
    fact_sources: list[IncidentFactSource] = Field(min_length=1)
    timeline_events: list[IncidentTimelineEvent] = Field(min_length=1)
    fact_separation: list[IncidentFactSeparationItem] = Field(min_length=1)
    fact_summary: list[str] = Field(min_length=1)
    participants: list[IncidentParticipant] = Field(min_length=1)
    missing_information: list[IncidentMissingInformation] = Field(min_length=1)
    stage_gate: list[StageGateCheck] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_incident_timeline_consistency(
        self,
    ) -> "IncidentTimelineArtifactData":
        _validate_incident_fact_sources(self)
        _validate_incident_timeline_events(self)
        return self


class IncidentRootCauseContext(StrictArtifactDataModel):
    incident_name: str
    scope: str
    upstream_facts: str
    current_judgement: str


class IncidentWhyChainItem(StrictArtifactDataModel):
    level: str
    question: str
    answer: str
    cause_type: str
    evidence: str
    evidence_strength: str
    confidence: str
    actionability: str
    verification_status: str


class IncidentCauseEvidence(StrictArtifactDataModel):
    cause_id: str
    cause: str
    related_level: str
    evidence: str
    evidence_strength: str
    confidence: str
    actionability: str
    verification_status: str


class IncidentFishboneCategory(StrictArtifactDataModel):
    category: str
    causes: list[str] = Field(min_length=1)
    cause_ids: list[str] = Field(min_length=1)


class IncidentRootCauseConclusion(StrictArtifactDataModel):
    conclusion_type: str
    description: str
    category: str
    related_cause_id: str
    evidence_strength: str
    confidence: str
    actionability: str
    verification_status: str


class IncidentExcludedCause(StrictArtifactDataModel):
    exclusion_id: str
    suspected_cause: str
    basis: str
    evidence_strength: str
    still_monitor: str


class IncidentUnverifiedCause(StrictArtifactDataModel):
    cause: str
    reason: str
    possible_impact: str
    verification_action: str
    owner: str
    status: str


class IncidentRootCauseArtifactData(StrictArtifactDataModel):
    analysis_context: IncidentRootCauseContext
    why_chain: list[IncidentWhyChainItem] = Field(min_length=1)
    cause_evidence: list[IncidentCauseEvidence] = Field(min_length=1)
    fishbone_categories: list[IncidentFishboneCategory] = Field(min_length=2)
    root_cause_conclusions: list[IncidentRootCauseConclusion] = Field(min_length=1)
    excluded_causes: list[IncidentExcludedCause] = Field(min_length=1)
    unverified_causes: list[IncidentUnverifiedCause] = Field(min_length=1)
    stage_gate: list[StageGateCheck] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_incident_root_cause_consistency(
        self,
    ) -> "IncidentRootCauseArtifactData":
        _validate_incident_why_chain(self)
        _validate_incident_cause_evidence(self)
        _validate_incident_fishbone(self)
        _validate_incident_conclusions(self)
        _validate_checked_stage_gate(self)
        return self


class IncidentImprovementReportInfo(StrictArtifactDataModel):
    incident_name: str
    severity: str
    version: str
    generated_at: str
    action_count: int | None = Field(default=None, ge=1)
    review_date: str
    closure_status: str


class IncidentImprovementTimelineSummary(StrictArtifactDataModel):
    key_events: list[str] = Field(min_length=1)
    impact_summary: str
    recovery_summary: str


class IncidentImprovementRootCauseSummary(StrictArtifactDataModel):
    direct_cause: str
    root_cause: str
    contributing_factors: list[str] = Field(min_length=1)
    evidence_summary: str


class IncidentImprovementPriorityDistribution(StrictArtifactDataModel):
    urgent_count: int | None = Field(default=None, ge=0)
    important_count: int | None = Field(default=None, ge=0)
    normal_count: int | None = Field(default=None, ge=0)


class IncidentImprovementAction(StrictArtifactDataModel):
    action_id: str
    improvement: str
    action_type: str
    root_cause_id: str
    root_cause_type: str
    owner: str
    deadline: str
    verification_method: str
    acceptance_criteria: str
    priority: str
    status: str
    tracking_method: str


class IncidentRootCauseCoverage(StrictArtifactDataModel):
    cause_id: str
    cause_type: str
    description: str
    action_ids: list[str]
    coverage_status: str
    uncovered_reason: str
    risk_acceptor: str


class IncidentPreventionCheckItem(StrictArtifactDataModel):
    item: str
    related_cause_id: str
    owner: str
    status: str


class IncidentReviewPlanItem(StrictArtifactDataModel):
    review_item: str
    review_date: str
    reviewer: str
    evidence: str
    pass_criteria: str
    status: str


class IncidentResidualRisk(StrictArtifactDataModel):
    risk_id: str
    risk: str
    impact: str
    acceptance_reason: str
    risk_acceptor: str
    review_due_date: str
    status: str


class IncidentLessonLearned(StrictArtifactDataModel):
    lesson_id: str
    lesson: str
    scope: str
    sharing_suggestion: str


class IncidentOrganizationalLearning(StrictArtifactDataModel):
    learning_item: str
    audience: str
    channel: str
    owner: str
    due_date: str
    status: str


class IncidentSignoff(StrictArtifactDataModel):
    role: str
    owner: str
    confirmation: str
    status: str


class IncidentImprovementArtifactData(StrictArtifactDataModel):
    report_info: IncidentImprovementReportInfo
    timeline_summary: IncidentImprovementTimelineSummary
    root_cause_summary: IncidentImprovementRootCauseSummary
    priority_distribution: IncidentImprovementPriorityDistribution | None = None
    improvement_actions: list[IncidentImprovementAction] = Field(min_length=1)
    root_cause_coverage: list[IncidentRootCauseCoverage] = Field(min_length=1)
    prevention_checklist: list[IncidentPreventionCheckItem] = Field(min_length=1)
    review_plan: list[IncidentReviewPlanItem] = Field(min_length=1)
    residual_risks: list[IncidentResidualRisk] = Field(min_length=1)
    lessons_learned: list[IncidentLessonLearned] = Field(min_length=1)
    organizational_learning: list[IncidentOrganizationalLearning] = Field(min_length=1)
    signoffs: list[IncidentSignoff] = Field(min_length=1)
    stage_gate: list[StageGateCheck] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_incident_improvement_consistency(
        self,
    ) -> "IncidentImprovementArtifactData":
        _validate_incident_improvement_report(self)
        _validate_incident_improvement_actions(self)
        _validate_incident_improvement_coverage(self)
        return self


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
    rpn: int | None = Field(default=None, ge=1, le=125)
    mitigation: str
    coverage: str
    status: str

    @model_validator(mode="after")
    def validate_rpn(self) -> "StrategyRisk":
        expected = self.severity * self.occurrence * self.detection
        if self.rpn is None:
            self.rpn = expected
            return self
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


def _extract_strategy_reference_ids(
    value: str,
    allowed_prefixes: tuple[str, ...],
) -> set[str]:
    candidates = set(re.findall(r"\b(?:QG|R|TS|TP)-[A-Za-z0-9_-]+\b", value))
    return {
        candidate
        for candidate in candidates
        if candidate.split("-", maxsplit=1)[0] in allowed_prefixes
    }


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

    @model_validator(mode="after")
    def validate_strategy_references(self) -> "StrategyArtifactData":
        _validate_strategy_quality_goals(self)
        _validate_strategy_risks(self)
        _validate_strategy_techniques(self)
        _validate_strategy_layers(self)
        _validate_strategy_test_points(self)
        _validate_checked_stage_gate(self)
        return self


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
    dimension: str | None = None
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
    case_statistics: CaseStatistics | None = None
    design_bases: list[DesignBasis] = Field(min_length=1)
    case_groups: list[CaseGroup] = Field(min_length=1)
    test_data_environments: list[TestDataEnvironment] = Field(min_length=1)
    automation_candidates: list[AutomationCandidate] = Field(min_length=1)
    coverage_trace: list[CoverageTraceItem] = Field(min_length=1)
    open_questions: list[OpenQuestion] = Field(min_length=1)
    stage_gate: list[StageGateCheck] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_case_consistency(self) -> "CasesArtifactData":
        _validate_case_groups(self)
        _validate_case_statistics(self)
        _validate_case_automation(self)
        _validate_case_coverage(self)
        _validate_checked_stage_gate(self)
        return self


class DeliveryMetrics(StrictArtifactDataModel):
    project_name: str
    version: str
    generated_at: str
    delivery_status: str
    total_cases: int | None = Field(default=None, ge=0)
    high_risk_count: int | None = Field(default=None, ge=0)


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
    case_count: int | None = Field(default=None, ge=0)
    p0_count: int = Field(ge=0)
    p1_count: int = Field(ge=0)
    p2_count: int = Field(ge=0)
    automation_candidates: int = Field(ge=0)
    blocked_or_needs_env: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_priority_counts(self) -> "DeliveryCaseSummaryItem":
        priority_total = self.p0_count + self.p1_count + self.p2_count
        if self.case_count is None:
            self.case_count = priority_total
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
        _validate_delivery_projection(self)
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
    p0_count: int | None = Field(default=None, ge=0)
    p1_count: int | None = Field(default=None, ge=0)
    p2_count: int | None = Field(default=None, ge=0)
    p0_description: str
    p1_description: str
    p2_description: str


class ReqReviewIssueItem(StrictArtifactDataModel):
    issue_id: str
    dimension: str | None = None
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


def _normalize_req_review_issue_groups(
    issue_groups: list[ReqReviewIssueGroup],
) -> tuple[list[ReqReviewIssueItem], set[str]]:
    for group in issue_groups:
        for issue in group.issues:
            if issue.dimension is None:
                issue.dimension = group.dimension
            elif issue.dimension != group.dimension:
                raise ValueError(
                    "issue_groups[].issues[].dimension must match outer "
                    "issue_groups[].dimension"
                )

    issues = [issue for group in issue_groups for issue in group.issues]
    issue_ids = {issue.issue_id for issue in issues}
    if len(issue_ids) != len(issues):
        raise ValueError("issue_groups contains duplicate issue_id")
    return issues, issue_ids


def _validate_req_review_statistics(
    issue_statistics: ReqReviewIssueStatistics,
    issue_groups: list[ReqReviewIssueGroup],
) -> None:
    issues, _issue_ids = _normalize_req_review_issue_groups(issue_groups)

    priority_counts = {
        "P0": sum(1 for issue in issues if issue.priority == "P0"),
        "P1": sum(1 for issue in issues if issue.priority == "P1"),
        "P2": sum(1 for issue in issues if issue.priority == "P2"),
    }
    if issue_statistics.p0_count is None:
        issue_statistics.p0_count = priority_counts["P0"]
    if issue_statistics.p1_count is None:
        issue_statistics.p1_count = priority_counts["P1"]
    if issue_statistics.p2_count is None:
        issue_statistics.p2_count = priority_counts["P2"]
    if (
        issue_statistics.p0_count != priority_counts["P0"]
        or issue_statistics.p1_count != priority_counts["P1"]
        or issue_statistics.p2_count != priority_counts["P2"]
    ):
        raise ValueError("issue_statistics must match issue_groups priorities")


def _validate_req_review_suggestions(
    issue_groups: list[ReqReviewIssueGroup],
    revision_suggestions: list[ReqReviewRevisionSuggestion],
) -> None:
    _issues, issue_ids = _normalize_req_review_issue_groups(issue_groups)
    unknown_references = sorted(
        {
            issue_id
            for suggestion in revision_suggestions
            for issue_id in suggestion.related_issues
            if issue_id not in issue_ids
        }
    )
    if unknown_references:
        raise ValueError(
            "revision_suggestions references unknown issue ids: "
            + ", ".join(unknown_references)
        )


def _validate_req_review_issue_consistency(
    issue_statistics: ReqReviewIssueStatistics,
    issue_groups: list[ReqReviewIssueGroup],
    revision_suggestions: list[ReqReviewRevisionSuggestion],
) -> None:
    _validate_req_review_statistics(issue_statistics, issue_groups)
    _validate_req_review_suggestions(issue_groups, revision_suggestions)


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
        _validate_req_review_issue_consistency(
            self.issue_statistics,
            self.issue_groups,
            self.revision_suggestions,
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
    p0_count: int | None = Field(default=None, ge=0)
    p1_count: int | None = Field(default=None, ge=0)
    p2_count: int | None = Field(default=None, ge=0)


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
    issue_statistics: ReqReviewReportIssueStatistics | None = None
    issue_closures: list[ReqReviewReportIssueClosure] = Field(min_length=1)
    review_conditions: list[ReqReviewReportCondition] = Field(min_length=1)
    signoffs: list[ReqReviewReportSignoff] = Field(min_length=1)
    change_log: list[ReqReviewReportChangeLogItem] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_report_consistency(self) -> "ReqReviewReportArtifactData":
        _validate_req_report_closures(self)
        _validate_req_report_statistics_projection(self)
        _validate_req_report_conditions(self)
        _validate_req_report_conclusion(self)
        return self


class PrdInventoryItem(StrictArtifactDataModel):
    item_id: str
    category: str
    content: str
    source: str
    evidence_level: str
    status: str


class PrdQualityFinding(StrictArtifactDataModel):
    finding_id: str
    dimension: str
    problem: str
    severity: str
    blocking: str
    evidence: str
    impact: str
    recommendation: str
    status: str


class PrdCompletionAction(StrictArtifactDataModel):
    action_id: str
    finding_ids: list[str] = Field(min_length=1)
    action: str
    priority: str
    owner: str
    verification_method: str
    review_condition: str
    status: str


class PrdRevisionSection(StrictArtifactDataModel):
    section_id: str
    title: str
    rewrite_goal: str
    recommended_content: str
    acceptance_note: str
    status: str


class PrdAcceptanceCriterion(StrictArtifactDataModel):
    criterion_id: str
    related_section_ids: list[str] = Field(min_length=1)
    scenario: str
    given: str
    when: str
    then: str
    testability_level: str
    status: str


class PrdHandoffInput(StrictArtifactDataModel):
    input_id: str
    related_section_ids: list[str] = Field(min_length=1)
    target_workflow: str
    content: str
    risk: str
    status: str


class PrdReviewArtifactData(StrictArtifactDataModel):
    document_info: DocumentInfo
    prd_inventory: list[PrdInventoryItem] = Field(min_length=1)
    quality_findings: list[PrdQualityFinding] = Field(min_length=1)
    completion_actions: list[PrdCompletionAction] = Field(min_length=1)
    revision_sections: list[PrdRevisionSection] = Field(min_length=1)
    acceptance_criteria: list[PrdAcceptanceCriterion] = Field(min_length=1)
    handoff_inputs: list[PrdHandoffInput] = Field(min_length=1)
    stage_gate: list[StageGateCheck] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_prd_review_consistency(self) -> "PrdReviewArtifactData":
        _validate_prd_findings(self)
        _validate_prd_actions(self)
        _prd_section_ids(self)
        _validate_prd_acceptance(self)
        _validate_prd_handoff(self)
        _validate_checked_stage_gate(self)
        return self


class StoryBreakdownInputAnalysis(StrictArtifactDataModel):
    source_type: str
    product_goal: str
    target_users: list[str] = Field(min_length=1)
    constraints: list[str] = Field(min_length=1)
    open_questions: list[str] = Field(min_length=1)


class StoryBreakdownEpic(StrictArtifactDataModel):
    epic_id: str
    name: str
    value_goal: str
    scope: str
    priority: str
    dependencies: list[str] = Field(min_length=1)


class StoryBreakdownUserStory(StrictArtifactDataModel):
    story_id: str
    epic_id: str
    title: str
    user_story: str
    priority: str
    sprint: str | None = None
    story_points: int = Field(ge=1)
    testability: str
    status: str


class StoryBreakdownAcceptanceCriterion(StrictArtifactDataModel):
    criterion_id: str
    story_id: str
    criterion: str
    verification_method: str
    status: str


class StoryBreakdownDependency(StrictArtifactDataModel):
    dependency_id: str
    related_story_ids: list[str] = Field(min_length=1)
    description: str
    risk: str
    mitigation: str
    owner: str
    status: str


class StoryBreakdownSprintSlice(StrictArtifactDataModel):
    sprint_id: str
    goal: str
    story_ids: list[str] = Field(min_length=1)
    deliverable: str
    acceptance_focus: str


class StoryBreakdownLisaHandoffInput(StrictArtifactDataModel):
    input_type: str
    reference_id: str
    content: str
    usage: str
    status: str


class StoryBreakdownArtifactData(StrictArtifactDataModel):
    document_info: DocumentInfo
    input_analysis: StoryBreakdownInputAnalysis
    epics: list[StoryBreakdownEpic] = Field(min_length=1)
    user_stories: list[StoryBreakdownUserStory] = Field(min_length=1)
    acceptance_criteria: list[StoryBreakdownAcceptanceCriterion] = Field(min_length=1)
    dependencies: list[StoryBreakdownDependency] = Field(min_length=1)
    sprint_slices: list[StoryBreakdownSprintSlice] = Field(min_length=1)
    lisa_handoff_inputs: list[StoryBreakdownLisaHandoffInput] = Field(min_length=1)
    stage_gate: list[StageGateCheck] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_story_breakdown_consistency(self) -> "StoryBreakdownArtifactData":
        _validate_story_epics(self)
        _validate_story_backlog(self)
        _validate_story_acceptance_criteria(self)
        _validate_story_dependencies(self)
        _validate_story_sprint_slices(self)
        _validate_story_handoff(self)
        _validate_checked_stage_gate(self)
        return self


def render_agent_turn_from_artifact_data(
    payload: dict[str, Any],
    *,
    workflow_id: str,
    current_stage_id: str,
) -> AgentTurnOutput | None:
    if "artifact_data" not in payload:
        return None
    rendered = render_complete_artifact_data(
        payload["artifact_data"],
        workflow_id=workflow_id,
        current_stage_id=current_stage_id,
    )

    return AgentTurnOutput.model_validate(
        {
            "chat": payload.get("chat"),
            "artifact_update": {
                "type": "replace",
                "markdown": rendered.markdown,
            },
            "artifact_data": rendered.normalized_artifact_data,
            "stage_action": payload.get("stage_action"),
            "warnings": payload.get("warnings", []),
        }
    )


def render_test_design_clarify_markdown(data: ClarifyArtifactData) -> str:
    return render_complete_artifact_data(
        data.model_dump(mode="json"),
        workflow_id="TEST_DESIGN",
        current_stage_id="CLARIFY",
    ).markdown


def render_complete_artifact_data(
    artifact_data: dict[str, Any],
    *,
    workflow_id: str,
    current_stage_id: str,
) -> RenderedArtifact:
    stage_key = (workflow_id, current_stage_id)
    plan = ARTIFACT_DATA_RENDERERS.get(stage_key)
    if plan is None:
        raise ValueError(
            f"artifact_data renderer is not configured for "
            f"{workflow_id}/{current_stage_id}"
        )
    return plan.render_complete(artifact_data)


def render_available_artifact_data(
    artifact_data: dict[str, Any],
    *,
    workflow_id: str,
    current_stage_id: str,
) -> RenderedArtifact | None:
    plan = ARTIFACT_DATA_RENDERERS.get((workflow_id, current_stage_id))
    if plan is None:
        raise ValueError(
            f"artifact_data renderer is not configured for "
            f"{workflow_id}/{current_stage_id}"
        )
    return plan.render_available(artifact_data)


def render_partial_artifact_data_markdown(
    artifact_data: dict[str, Any],
    *,
    workflow_id: str,
    current_stage_id: str,
) -> str | None:
    rendered = render_available_artifact_data(
        artifact_data,
        workflow_id=workflow_id,
        current_stage_id=current_stage_id,
    )
    return rendered.markdown if rendered is not None else None


def render_idea_brainstorm_define_markdown(data: IdeaDefineArtifactData) -> str:
    return render_complete_artifact_data(
        data.model_dump(mode="json"),
        workflow_id="IDEA_BRAINSTORM",
        current_stage_id="DEFINE",
    ).markdown


def render_idea_brainstorm_diverge_markdown(data: IdeaDivergeArtifactData) -> str:
    return render_complete_artifact_data(
        data.model_dump(mode="json"),
        workflow_id="IDEA_BRAINSTORM",
        current_stage_id="DIVERGE",
    ).markdown


def render_idea_brainstorm_converge_markdown(data: IdeaConvergeArtifactData) -> str:
    return render_complete_artifact_data(
        data.model_dump(mode="json"),
        workflow_id="IDEA_BRAINSTORM",
        current_stage_id="CONVERGE",
    ).markdown


def render_idea_brainstorm_concept_markdown(data: IdeaConceptArtifactData) -> str:
    return render_complete_artifact_data(
        data.model_dump(mode="json"),
        workflow_id="IDEA_BRAINSTORM",
        current_stage_id="CONCEPT",
    ).markdown


def render_incident_review_timeline_markdown(
    data: IncidentTimelineArtifactData,
) -> str:
    return render_complete_artifact_data(
        data.model_dump(mode="json"),
        workflow_id="INCIDENT_REVIEW",
        current_stage_id="TIMELINE",
    ).markdown


def render_incident_review_root_cause_markdown(
    data: IncidentRootCauseArtifactData,
) -> str:
    return render_complete_artifact_data(
        data.model_dump(mode="json"),
        workflow_id="INCIDENT_REVIEW",
        current_stage_id="ROOT_CAUSE",
    ).markdown


def render_incident_review_improvement_markdown(
    data: IncidentImprovementArtifactData,
) -> str:
    return render_complete_artifact_data(
        data.model_dump(mode="json"),
        workflow_id="INCIDENT_REVIEW",
        current_stage_id="IMPROVEMENT",
    ).markdown


def render_test_design_strategy_markdown(data: StrategyArtifactData) -> str:
    return render_complete_artifact_data(
        data.model_dump(mode="json"),
        workflow_id="TEST_DESIGN",
        current_stage_id="STRATEGY",
    ).markdown


def render_test_design_cases_markdown(data: CasesArtifactData) -> str:
    return render_complete_artifact_data(
        data.model_dump(mode="json"),
        workflow_id="TEST_DESIGN",
        current_stage_id="CASES",
    ).markdown


def render_test_design_delivery_markdown(data: DeliveryArtifactData) -> str:
    return render_complete_artifact_data(
        data.model_dump(mode="json"),
        workflow_id="TEST_DESIGN",
        current_stage_id="DELIVERY",
    ).markdown


def render_req_review_review_markdown(data: ReqReviewArtifactData) -> str:
    return (
        ARTIFACT_DATA_RENDERERS[("REQ_REVIEW", "REVIEW")]
        .render_complete(data.model_dump(mode="json"))
        .markdown
    )


def render_req_review_report_markdown(data: ReqReviewReportArtifactData) -> str:
    return render_complete_artifact_data(
        data.model_dump(mode="json"),
        workflow_id="REQ_REVIEW",
        current_stage_id="REPORT",
    ).markdown


def render_value_discovery_elevator_markdown(
    data: ValueDiscoveryElevatorArtifactData,
) -> str:
    return render_complete_artifact_data(
        data.model_dump(mode="json"),
        workflow_id="VALUE_DISCOVERY",
        current_stage_id="ELEVATOR",
    ).markdown


def render_value_discovery_persona_markdown(
    data: ValueDiscoveryPersonaArtifactData,
) -> str:
    return render_complete_artifact_data(
        data.model_dump(mode="json"),
        workflow_id="VALUE_DISCOVERY",
        current_stage_id="PERSONA",
    ).markdown


def render_value_discovery_journey_markdown(
    data: ValueDiscoveryJourneyArtifactData,
) -> str:
    return render_complete_artifact_data(
        data.model_dump(mode="json"),
        workflow_id="VALUE_DISCOVERY",
        current_stage_id="JOURNEY",
    ).markdown


def render_value_discovery_blueprint_markdown(
    data: ValueDiscoveryBlueprintArtifactData,
) -> str:
    return render_complete_artifact_data(
        data.model_dump(mode="json"),
        workflow_id="VALUE_DISCOVERY",
        current_stage_id="BLUEPRINT",
    ).markdown


def render_prd_review_markdown(data: PrdReviewArtifactData, stage_id: str) -> str:
    return render_complete_artifact_data(
        data.model_dump(mode="json"),
        workflow_id="PRD_REVIEW",
        current_stage_id=stage_id,
    ).markdown


def render_story_breakdown_markdown(data: StoryBreakdownArtifactData) -> str:
    return render_complete_artifact_data(
        data.model_dump(mode="json"),
        workflow_id="STORY_BREAKDOWN",
        current_stage_id="INPUT_ANALYSIS",
    ).markdown


def _render_story_input_analysis(data: StoryBreakdownInputAnalysis) -> str:
    rows = [
        ("输入类型", data.source_type),
        ("产品目标", data.product_goal),
        ("目标用户", "、".join(data.target_users)),
        ("关键约束", "；".join(data.constraints)),
        ("待澄清问题", "；".join(data.open_questions)),
    ]
    return "## 输入分析\n" + _markdown_table(["维度", "内容"], rows)


def _render_story_epic_map(
    epics: list[StoryBreakdownEpic],
    *,
    product_goal: str,
) -> str:
    node_ids = {epic.epic_id for epic in epics}
    nodes = [
        {
            "id": "Goal",
            "label": "Goal",
            "title": product_goal,
            "description": "产品目标",
            "category": "目标",
            "status": "已确认",
        }
    ]
    edges = []
    for epic in epics:
        nodes.append(
            {
                "id": epic.epic_id,
                "label": epic.epic_id,
                "title": epic.name,
                "description": epic.value_goal,
                "category": "Epic",
                "status": epic.priority,
            }
        )
        edges.append(
            {
                "source": "Goal",
                "target": epic.epic_id,
                "label": "拆解为",
            }
        )
        for dependency in epic.dependencies:
            if dependency in node_ids and dependency != epic.epic_id:
                edges.append(
                    {
                        "source": dependency,
                        "target": epic.epic_id,
                        "label": "依赖",
                    }
                )
    flow_map = {
        "type": "flow-map",
        "title": "Epic 流程图",
        "nodes": nodes,
        "edges": edges,
    }
    rows = [
        (
            item.epic_id,
            item.name,
            item.value_goal,
            item.scope,
            item.priority,
            "、".join(item.dependencies),
        )
        for item in epics
    ]
    return "\n".join(
        [
            "## Epic Map",
            "```ai4se-visual",
            json.dumps(flow_map, ensure_ascii=False, indent=2),
            "```",
            "",
            _markdown_table(
                ["Epic ID", "名称", "价值目标", "范围边界", "优先级", "依赖"],
                rows,
            ),
        ]
    )


def _render_story_backlog(stories: list[StoryBreakdownUserStory]) -> str:
    rows = [
        (
            item.story_id,
            item.epic_id,
            item.title,
            item.user_story,
            item.priority,
            item.sprint,
            item.story_points,
            item.testability,
            item.status,
        )
        for item in stories
    ]
    visual_rows = [
        {
            "Epic": item.epic_id,
            "Story": f"{item.story_id} {item.title}",
            "优先级": item.priority,
            "Sprint": item.sprint,
            "依赖": "",
            "可测试性": item.testability,
        }
        for item in stories
    ]
    story_map = {
        "type": "story-map",
        "title": "用户故事地图",
        "columns": ["Epic", "Story", "优先级", "Sprint", "依赖", "可测试性"],
        "rows": visual_rows,
    }
    return "\n".join(
        [
            "## User Story Backlog",
            _markdown_table(
                [
                    "Story ID",
                    "Epic ID",
                    "标题",
                    "用户故事",
                    "优先级",
                    "Sprint",
                    "点数",
                    "可测试性",
                    "状态",
                ],
                rows,
            ),
            "",
            "```ai4se-visual",
            json.dumps(story_map, ensure_ascii=False, indent=2),
            "```",
        ]
    )


def _render_story_acceptance_criteria(
    criteria: list[StoryBreakdownAcceptanceCriterion],
) -> str:
    rows = [
        (
            item.criterion_id,
            item.story_id,
            item.criterion,
            item.verification_method,
            item.status,
        )
        for item in criteria
    ]
    return "## 验收标准\n" + _markdown_table(
        ["AC ID", "Story ID", "验收标准", "验证方式", "状态"],
        rows,
    )


def _render_story_dependencies(
    dependencies: list[StoryBreakdownDependency],
) -> str:
    rows = [
        (
            item.dependency_id,
            "、".join(item.related_story_ids),
            item.description,
            item.risk,
            item.mitigation,
            item.owner,
            item.status,
        )
        for item in dependencies
    ]
    return "## 依赖与风险\n" + _markdown_table(
        ["依赖 ID", "关联 Story", "依赖描述", "风险", "缓解策略", "owner", "状态"],
        rows,
    )


def _render_story_sprint_slices(
    sprints: list[StoryBreakdownSprintSlice],
) -> str:
    rows = [
        (
            item.sprint_id,
            item.goal,
            "、".join(item.story_ids),
            item.deliverable,
            item.acceptance_focus,
        )
        for item in sprints
    ]
    return "## Sprint 切片建议\n" + _markdown_table(
        ["Sprint", "目标", "Story", "交付物", "验收重点"],
        rows,
    )


def _render_story_lisa_handoff_inputs(
    inputs: list[StoryBreakdownLisaHandoffInput],
) -> str:
    rows = [
        (item.input_type, item.reference_id, item.content, item.usage, item.status)
        for item in inputs
    ]
    return "## Lisa Handoff 输入\n" + _markdown_table(
        ["输入类型", "ID", "内容", "给 Lisa 的用途", "状态"],
        rows,
    )


def _render_story_stage_gate(checks: list[StageGateCheck]) -> str:
    lines = [f"- [{'x' if item.checked else ' '}] {item.item}" for item in checks]
    return "## 阶段门禁\n" + "\n".join(lines)


def _render_document_info(info: DocumentInfo) -> str:
    rows = [
        ("Artifact 名称", info.artifact_name),
        ("Workflow", info.workflow),
        ("Stage", info.stage),
        ("状态", info.status),
    ]
    return "## 文档信息\n" + _markdown_table(["字段", "内容"], rows)


def _render_incident_summary(summary: IncidentSummary) -> str:
    rows = [
        ("故障名称", summary.incident_name),
        ("严重等级", summary.severity),
        ("发现时间", summary.detected_at),
        ("恢复时间", summary.recovered_at),
        ("持续时长", summary.duration),
        ("影响范围", summary.impact_scope),
        ("当前状态", summary.current_status),
    ]
    return "## 1. 事件概要\n" + _markdown_table(["属性", "详情"], rows)


def _render_idea_problem_statement(statement: IdeaProblemStatement) -> str:
    paragraph = (
        f"我们相信 {statement.target_user} 在 {statement.scenario} 下面临"
        f" {statement.core_pain} 的问题。目前他们通过 "
        f"{statement.existing_alternative} 来应对，但 "
        f"{statement.alternative_gap}。如果该问题得不到有效解决，将导致 "
        f"{statement.consequence}。"
    )
    rows = [
        ("目标用户", statement.target_user),
        ("具体场景", statement.scenario),
        ("核心痛点", statement.core_pain),
        ("现有替代方案", statement.existing_alternative),
        ("现有方案不足", statement.alternative_gap),
        ("不解决的后果", statement.consequence),
        ("验证状态", statement.validation_status),
    ]
    return (
        "## 问题假设陈述\n"
        + paragraph
        + "\n\n"
        + _markdown_table(["字段", "内容"], rows)
    )


def _render_idea_target_users(items: list[IdeaTargetUser]) -> str:
    rows = [
        (
            item.dimension,
            item.description,
            item.evidence_level,
            item.validation_status,
        )
        for item in items
    ]
    return "## 目标用户画像\n" + _markdown_table(
        ["维度", "描述", "证据等级", "验证状态"],
        rows,
    )


def _render_idea_problem_landscape(landscape: IdeaProblemLandscape) -> str:
    lines = [
        "```mermaid",
        "mindmap",
        f'  root(("{_escape_mermaid_mindmap_text(landscape.root_problem)}"))',
    ]
    for item in landscape.subproblems:
        lines.append(f"    {_escape_mermaid_mindmap_text(item.problem)}")
        for symptom in item.symptoms:
            lines.append(f"      {_escape_mermaid_mindmap_text(symptom)}")
    lines.append("```")
    rows = [
        (item.problem_id, item.problem, "、".join(item.symptoms))
        for item in landscape.subproblems
    ]
    return (
        "## 问题域全景\n"
        + "\n".join(lines)
        + "\n\n"
        + _markdown_table(["问题 ID", "子问题", "表现"], rows)
    )


def _render_idea_evidence_items(items: list[IdeaEvidenceItem]) -> str:
    rows = [
        (
            item.evidence_id,
            item.related_problem,
            item.source,
            item.evidence_level,
            item.validation_action,
            item.owner,
            item.validation_status,
        )
        for item in items
    ]
    return "## 证据与验证状态\n" + _markdown_table(
        [
            "证据 ID",
            "关联问题",
            "证据来源",
            "证据等级",
            "验证动作",
            "owner",
            "验证状态",
        ],
        rows,
    )


def _render_idea_problem_user_fit(items: list[IdeaProblemUserFit]) -> str:
    rows = [
        (
            item.dimension,
            item.current_judgement,
            item.evidence_or_assumption,
            ", ".join(item.evidence_ids),
            item.validation_action,
            item.validation_status,
        )
        for item in items
    ]
    return "## 问题-用户-场景匹配\n" + _markdown_table(
        [
            "检验维度",
            "当前判断",
            "证据/假设",
            "关联证据",
            "验证动作",
            "验证状态",
        ],
        rows,
    )


def _render_idea_constraints_boundaries(
    items: list[IdeaConstraintBoundary],
) -> str:
    rows = [
        (item.boundary_type, item.content, item.impact, item.status) for item in items
    ]
    return "## 约束与边界\n" + _markdown_table(
        ["类型", "内容", "影响", "状态"],
        rows,
    )


def _render_idea_reverse_validation(items: list[IdeaReverseValidation]) -> str:
    rows = [
        (
            item.failure_hypothesis,
            item.trigger_signal,
            item.validation_action,
            item.validation_status,
        )
        for item in items
    ]
    return "## 反向验证（风险思考）\n" + _markdown_table(
        ["失败假设", "触发信号", "验证动作", "验证状态"],
        rows,
    )


def _render_idea_stage_gate(checks: list[StageGateCheck]) -> str:
    lines = [f"- [{'x' if item.checked else ' '}] {item.item}" for item in checks]
    return "## 阶段门禁\n" + "\n".join(lines)


def _render_idea_divergence_method(method: IdeaDivergenceMethod) -> str:
    rows = [
        ("发散方法", method.method_name),
        ("发散目标", method.goal),
        ("输入依据", method.input_basis),
        ("覆盖维度", "、".join(method.coverage_dimensions)),
        ("发散约束", method.constraints),
    ]
    return "## 发散方法说明\n" + _markdown_table(["字段", "内容"], rows)


def _render_idea_diverge_landscape(
    landscape: IdeaDivergeLandscape,
    idea_cards: list[IdeaCard],
) -> str:
    idea_titles = {item.idea_id: item.title for item in idea_cards}
    lines = [
        "```mermaid",
        "mindmap",
        f'  root(("{_escape_mermaid_mindmap_text(landscape.root_theme)}"))',
    ]
    for group in landscape.groups:
        lines.append(f"    {_escape_mermaid_mindmap_text(group.theme)}")
        for idea_id in group.idea_ids:
            title = idea_titles[idea_id]
            lines.append("      " + _escape_mermaid_mindmap_text(f"{idea_id} {title}"))
    lines.append("```")
    rows = [
        (
            group.group_id,
            group.theme,
            ", ".join(group.idea_ids),
        )
        for group in landscape.groups
    ]
    return (
        "## 发散全景图\n"
        + "\n".join(lines)
        + "\n\n"
        + _markdown_table(["分组 ID", "主题", "创意 ID"], rows)
    )


def _render_idea_cards(items: list[IdeaCard]) -> str:
    rows = [
        (
            item.idea_id,
            item.title,
            item.one_liner,
            item.target_user,
            item.scenario,
            item.value_proposition,
            "；".join(item.key_hypotheses),
            item.novelty_source,
            item.evidence_level,
            item.validation_action,
            item.status,
            item.status_reason,
        )
        for item in items
    ]
    return "## 创意卡片库\n" + _markdown_table(
        [
            "创意 ID",
            "创意名称",
            "一句话说明",
            "目标用户",
            "使用场景",
            "价值主张",
            "关键假设",
            "创新来源",
            "证据等级",
            "验证动作",
            "状态",
            "状态理由",
        ],
        rows,
    )


def _render_idea_sources(items: list[IdeaSource]) -> str:
    rows = [
        (
            item.source_id,
            item.source_type,
            item.source,
            ", ".join(item.idea_ids),
            item.key_assumption,
            item.status_reason,
        )
        for item in items
    ]
    return "## 创意来源与假设\n" + _markdown_table(
        ["来源 ID", "来源类型", "来源内容", "关联创意", "关键假设", "状态理由"],
        rows,
    )


def _render_idea_parked_or_excluded(
    items: list[IdeaParkedOrExcludedRecord],
) -> str:
    rows = [
        (
            item.record_id,
            item.idea_or_direction,
            item.reason,
            item.revisit_condition,
            item.status_reason,
        )
        for item in items
    ]
    return "## 搁置/排除记录\n" + _markdown_table(
        ["记录 ID", "创意或方向", "搁置/排除原因", "重新考虑条件", "状态理由"],
        rows,
    )


def _render_idea_converge_decision_matrix(
    matrix: IdeaDecisionMatrix,
    evaluations: list[IdeaIceEvaluation],
) -> str:
    summary_rows = [
        ("评分口径", matrix.scoring_rubric),
        ("推荐方案", f"{matrix.recommended_idea_id} {matrix.recommendation}"),
        ("用户确认状态", matrix.user_confirmation_status),
    ]
    decision_rows = [
        (
            item.idea_id,
            item.idea_name,
            item.decision,
            item.reason,
            item.evidence_source,
        )
        for item in matrix.decision_items
    ]
    return (
        "## 决策矩阵\n"
        + _render_idea_converge_quadrant_chart(evaluations)
        + "\n\n"
        + _markdown_table(["字段", "内容"], summary_rows)
        + "\n\n"
        + _markdown_table(
            ["创意 ID", "创意名称", "决策", "理由", "证据来源"],
            decision_rows,
        )
    )


def _render_idea_converge_quadrant_chart(
    evaluations: list[IdeaIceEvaluation],
) -> str:
    lines = [
        "```mermaid",
        "quadrantChart",
        "    title 创意收敛决策矩阵",
        '    x-axis "低信心" --> "高信心"',
        '    y-axis "低影响力" --> "高影响力"',
        '    quadrant-1 "优先验证"',
        '    quadrant-2 "潜力观察"',
        '    quadrant-3 "暂缓"',
        '    quadrant-4 "低成本尝试"',
    ]
    for item in evaluations:
        x_value = _format_mermaid_quadrant_coordinate(item.confidence / 5)
        y_value = _format_mermaid_quadrant_coordinate(item.impact / 5)
        lines.append(
            f'    "{_escape_mermaid_label(item.idea_name)}": ' f"[{x_value}, {y_value}]"
        )
    lines.append("```")
    return "\n".join(lines)


def _render_idea_ice_evaluations(items: list[IdeaIceEvaluation]) -> str:
    rows = [
        (
            item.idea_id,
            item.idea_name,
            item.impact,
            item.confidence,
            item.effort,
            f"{item.ice_score:.2f}",
            item.rank,
            item.conclusion,
            item.elimination_reason,
            item.evidence_source,
            item.next_validation,
        )
        for item in sorted(items, key=lambda evaluation: evaluation.rank)
    ]
    return "## ICE 评估表\n" + _markdown_table(
        [
            "创意 ID",
            "创意名称",
            "影响力",
            "信心",
            "实现难度",
            "ICE得分",
            "排名",
            "结论",
            "淘汰理由",
            "证据来源",
            "下一步验证",
        ],
        rows,
    )


def _render_idea_resource_constraints(
    items: list[IdeaResourceConstraint],
) -> str:
    rows = [
        (
            item.constraint_type,
            item.content,
            item.impact,
            item.handling,
            item.status,
        )
        for item in items
    ]
    return "## 资源约束\n" + _markdown_table(
        ["约束类型", "内容", "影响", "处理方式", "状态"],
        rows,
    )


def _render_idea_sensitivity_analysis(items: list[IdeaSensitivityItem]) -> str:
    rows = [
        (
            item.variable,
            item.change,
            item.impact,
            item.signal,
            item.next_validation,
        )
        for item in items
    ]
    return "## 敏感性分析\n" + _markdown_table(
        ["敏感变量", "变化方向", "影响", "观察信号", "下一步验证"],
        rows,
    )


def _render_idea_validation_experiments(
    items: list[IdeaValidationExperiment],
) -> str:
    rows = [
        (
            item.experiment_id,
            ", ".join(item.idea_ids),
            item.goal,
            item.method,
            item.success_metric,
            item.owner,
            item.next_validation,
            item.status,
        )
        for item in items
    ]
    return "## 验证实验\n" + _markdown_table(
        [
            "实验 ID",
            "关联创意",
            "实验目标",
            "方法",
            "成功指标",
            "owner",
            "下一步验证",
            "状态",
        ],
        rows,
    )


def _render_idea_merge_paths(items: list[IdeaMergePath]) -> str:
    rows = [
        (
            item.path_id,
            ", ".join(item.source_idea_ids),
            item.merge_logic,
            item.integrated_concept,
            item.applicable_condition,
            item.risk,
            item.user_confirmation_status,
        )
        for item in items
    ]
    return "## 整合演进路径（如果触发合并）\n" + _markdown_table(
        [
            "路径 ID",
            "来源创意",
            "合并逻辑",
            "整合方案",
            "适用条件",
            "风险",
            "用户确认状态",
        ],
        rows,
    )


def _render_idea_concept_positioning(statement: IdeaPositioningStatement) -> str:
    lines = [
        "## 定位声明",
        f"**For** {statement.target_user}",
        f"**who** {statement.user_need},",
        f"**the** {statement.product_name} **is a** {statement.category}",
        f"**that** {statement.value_proposition}.",
        f"**Unlike** {statement.alternative},",
        f"**our product** {statement.differentiation}.",
    ]
    return "\n".join(lines)


def _render_idea_concept_core_assumptions(
    items: list[IdeaCoreAssumption],
) -> str:
    rows = [
        (
            item.assumption_id,
            item.assumption,
            item.source,
            item.importance,
            item.validation_action,
            item.owner,
            item.status,
        )
        for item in items
    ]
    return "## 核心假设\n" + _markdown_table(
        ["假设 ID", "假设内容", "关联来源", "重要性", "验证动作", "owner", "状态"],
        rows,
    )


def _render_idea_concept_lean_canvas(items: list[IdeaLeanCanvasCell]) -> str:
    order = [
        "问题",
        "用户群体",
        "独特价值主张",
        "解决方案",
        "渠道",
        "收入来源",
        "成本结构",
        "关键指标",
        "竞争壁垒",
    ]
    cells_by_name = {item.cell: item.content for item in items}
    rows = [(cell, cells_by_name[cell]) for cell in order if cell in cells_by_name]
    return "## Lean Canvas 产品画布\n" + _markdown_table(["格子", "内容"], rows)


def _render_idea_concept_mvp_features(items: list[IdeaMvpFeature]) -> str:
    level_counts: dict[str, int] = {}
    for item in items:
        level_counts[item.mvp_level] = level_counts.get(item.mvp_level, 0) + 1
    pie_lines = [
        "```mermaid",
        "pie title MVP 功能组成",
        *[
            f'    "{_escape_mermaid_label(level)}" : {count}'
            for level, count in sorted(level_counts.items())
        ],
        "```",
    ]
    rows = [
        (
            item.module,
            item.mvp_level,
            item.user_value,
            item.validation_metric,
            item.tradeoff_reason,
            ", ".join(item.assumption_ids),
            item.status,
        )
        for item in items
    ]
    visual = {
        "type": "mvp-map",
        "title": "MVP 功能地图",
        "columns": ["模块", "MVP层级", "用户价值", "验证指标", "取舍理由"],
        "rows": [
            {
                "模块": item.module,
                "MVP层级": item.mvp_level,
                "用户价值": item.user_value,
                "验证指标": item.validation_metric,
                "取舍理由": item.tradeoff_reason,
            }
            for item in items
        ],
    }
    return (
        "## MVP 功能分布\n"
        + "\n".join(pie_lines)
        + "\n\n"
        + _markdown_table(
            [
                "模块",
                "MVP层级",
                "用户价值",
                "验证指标",
                "取舍理由",
                "关联假设",
                "状态",
            ],
            rows,
        )
        + "\n\n```ai4se-visual\n"
        + json.dumps(visual, ensure_ascii=False, indent=2)
        + "\n```"
    )


def _render_idea_concept_growth_funnel(
    items: list[IdeaGrowthFunnelStage],
) -> str:
    order = ["Acquisition", "Activation", "Retention", "Revenue", "Referral"]
    labels = {
        "Acquisition": "Acquisition 获客",
        "Activation": "Activation 激活",
        "Retention": "Retention 留存",
        "Revenue": "Revenue 变现",
        "Referral": "Referral 传播",
    }
    items_by_stage = {item.stage: item for item in items}
    flow_lines = [
        "```mermaid",
        "flowchart TD",
        '    A["Acquisition 获客"] --> B["Activation 激活"]',
        '    B --> C["Retention 留存"]',
        '    C --> D["Revenue 变现"]',
        '    D --> E["Referral 传播"]',
        "```",
    ]
    rows = [
        (
            labels[stage],
            items_by_stage[stage].user_behavior,
            items_by_stage[stage].metric,
            items_by_stage[stage].mvp_implementation,
        )
        for stage in order
        if stage in items_by_stage
    ]
    return (
        "## 核心增长漏斗\n"
        + "\n".join(flow_lines)
        + "\n\n"
        + _markdown_table(
            ["漏斗阶段", "用户行为", "核心指标", "MVP 中如何实现"],
            rows,
        )
    )


def _render_idea_concept_premortem_risks(
    items: list[IdeaPremortemRisk],
) -> str:
    rows = [
        (
            item.risk_id,
            item.dimension,
            item.failure_reason,
            item.likelihood,
            item.mitigation,
        )
        for item in items
    ]
    return "## Pre-mortem 风险分析\n" + _markdown_table(
        ["风险 ID", "风险维度", "失败原因", "可能性", "缓解措施"],
        rows,
    )


def _render_idea_concept_validation_roadmap(
    items: list[IdeaValidationRoadmapItem],
) -> str:
    rows = [
        (
            item.validation_id,
            item.stage,
            item.goal,
            item.experiment,
            item.success_metric,
            item.time_window,
            item.owner,
            item.status,
            ", ".join(item.assumption_ids),
        )
        for item in items
    ]
    return "## 验证路线\n" + _markdown_table(
        [
            "验证 ID",
            "阶段",
            "验证目标",
            "实验方式",
            "成功指标",
            "时间窗口",
            "owner",
            "状态",
            "关联假设",
        ],
        rows,
    )


def _render_idea_concept_out_of_scope(items: list[IdeaOutOfScopeItem]) -> str:
    rows = [
        (item.item, item.reason, item.reconsider_condition, item.status)
        for item in items
    ]
    return "## 不可做范围\n" + _markdown_table(
        ["不做项", "原因", "重新考虑条件", "状态"],
        rows,
    )


def _render_idea_concept_decision_records(
    items: list[IdeaDecisionRecord],
) -> str:
    rows = [
        (
            item.decision,
            item.conclusion,
            item.basis,
            item.decider,
            item.date,
            item.status,
        )
        for item in items
    ]
    return "## 决策记录\n" + _markdown_table(
        ["决策项", "结论", "依据", "决策人/角色", "日期", "状态"],
        rows,
    )


def _render_idea_concept_next_actions(items: list[IdeaNextAction]) -> str:
    rows = [
        (
            item.action_id,
            item.action,
            ", ".join(item.related_ids),
            item.owner,
            item.due_date,
            item.acceptance,
            item.status,
        )
        for item in items
    ]
    return "## 下一步行动\n" + _markdown_table(
        ["行动 ID", "行动", "关联假设/风险", "owner", "截止时间", "验收标准", "状态"],
        rows,
    )


def _render_incident_impact_metrics(
    items: list[IncidentImpactMetric],
) -> str:
    rows = [
        (
            item.dimension,
            item.quantification,
            item.confidence,
            item.source,
            item.status,
        )
        for item in items
    ]
    return "## 2. 影响量化\n" + _markdown_table(
        ["影响维度", "量化结果", "可信度", "来源", "状态"],
        rows,
    )


def _render_incident_fact_sources(items: list[IncidentFactSource]) -> str:
    rows = [
        (item.fact_id, item.fact, item.source, item.confidence, item.status)
        for item in items
    ]
    return "## 3. 事实来源\n" + _markdown_table(
        ["事实 ID", "事实描述", "来源", "可信度", "状态"],
        rows,
    )


def _render_incident_timeline(
    summary: IncidentSummary,
    events: list[IncidentTimelineEvent],
) -> str:
    rows = [
        (
            item.section,
            item.occurred_at,
            item.event,
            ", ".join(item.fact_ids),
        )
        for item in events
    ]
    return (
        "## 4. 事件时间线\n"
        + _render_timeline_map_visual(summary, events)
        + "\n\n"
        + _markdown_table(["阶段", "时间点", "事件描述", "关联事实"], rows)
    )


def _render_timeline_map_visual(
    summary: IncidentSummary,
    events: list[IncidentTimelineEvent],
) -> str:
    visual = {
        "type": "timeline-map",
        "title": f"{summary.incident_name} 事件时间线",
        "events": [
            {
                "id": f"TL-{index:03d}",
                "time": item.occurred_at,
                "title": item.event,
                "description": f"阶段：{item.section}；关联事实：{', '.join(item.fact_ids)}",
                "factIds": item.fact_ids,
            }
            for index, item in enumerate(events, start=1)
        ],
    }
    return (
        "```ai4se-visual\n" + json.dumps(visual, ensure_ascii=False, indent=2) + "\n```"
    )


def _render_incident_fact_separation(
    items: list[IncidentFactSeparationItem],
) -> str:
    rows = [
        (item.item_type, item.content, item.handling, item.blocking, item.status)
        for item in items
    ]
    return "## 5. 事实/推测隔离\n" + _markdown_table(
        ["类型", "内容", "处理方式", "阻断性", "状态"],
        rows,
    )


def _render_incident_fact_summary(items: list[str]) -> str:
    lines = [f"{index}. {item}" for index, item in enumerate(items, start=1)]
    return "## 6. 事实摘要\n" + "\n".join(lines)


def _render_incident_participants(items: list[IncidentParticipant]) -> str:
    rows = [
        (item.role, item.person, item.action, item.participated_at, item.status)
        for item in items
    ]
    return "## 7. 参与人员\n" + _markdown_table(
        ["角色", "人员", "主要行动", "参与时间", "状态"],
        rows,
    )


def _render_incident_missing_information(
    items: list[IncidentMissingInformation],
) -> str:
    rows = [
        (
            item.item,
            item.reason,
            item.supplement_method,
            item.blocking,
            item.owner,
            item.status,
        )
        for item in items
    ]
    return "## 8. 待补充信息\n" + _markdown_table(
        ["信息项", "为什么需要", "补充方式", "阻断性", "owner", "状态"],
        rows,
    )


def _render_incident_stage_gate(checks: list[StageGateCheck]) -> str:
    lines = [f"- [{'x' if item.checked else ' '}] {item.item}" for item in checks]
    return "## 9. 阶段门禁\n" + "\n".join(lines)


def _render_incident_root_cause_context(context: IncidentRootCauseContext) -> str:
    rows = [
        ("故障名称", context.incident_name),
        ("分析范围", context.scope),
        ("上游事实摘要", context.upstream_facts),
        ("当前判断", context.current_judgement),
    ]
    return "## 6. 根因分析\n" + _markdown_table(["字段", "内容"], rows)


def _render_incident_why_chain(items: list[IncidentWhyChainItem]) -> str:
    rows = [
        (
            item.level,
            item.question,
            item.answer,
            item.cause_type,
            item.evidence,
            item.evidence_strength,
            item.confidence,
            item.actionability,
            item.verification_status,
        )
        for item in items
    ]
    visual = {
        "type": "cause-map",
        "title": "5-Why 根因链路图",
        "nodes": [
            {
                "id": item.level,
                "label": item.level,
                "title": item.answer,
                "description": item.question,
                "category": item.cause_type,
                "evidence": item.evidence,
                "confidence": item.confidence,
                "status": item.verification_status,
            }
            for item in items
        ],
        "edges": [
            {
                "source": items[index].level,
                "target": items[index + 1].level,
                "label": "继续追问",
            }
            for index in range(len(items) - 1)
        ],
    }
    return (
        "### 6.1 5-Why 分析链\n"
        + _markdown_table(
            [
                "层级",
                "问题",
                "回答",
                "原因类型",
                "证据",
                "证据强度",
                "置信度",
                "可行动性",
                "验证状态",
            ],
            rows,
        )
        + "\n\n```ai4se-visual\n"
        + json.dumps(visual, ensure_ascii=False, indent=2)
        + "\n```"
    )


def _render_incident_cause_evidence(items: list[IncidentCauseEvidence]) -> str:
    rows = [
        (
            item.cause_id,
            item.cause,
            item.related_level,
            item.evidence,
            item.evidence_strength,
            item.confidence,
            item.actionability,
            item.verification_status,
        )
        for item in items
    ]
    return "### 6.2 根因证据表\n" + _markdown_table(
        [
            "原因 ID",
            "原因描述",
            "关联层级",
            "证据",
            "证据强度",
            "置信度",
            "可行动性",
            "验证状态",
        ],
        rows,
    )


def _render_incident_fishbone(
    context: IncidentRootCauseContext,
    categories: list[IncidentFishboneCategory],
) -> str:
    lines = [
        "```mermaid",
        "mindmap",
        f'  root(("{_escape_mermaid_mindmap_text(context.incident_name)}"))',
    ]
    for item in categories:
        lines.append(f"    {_escape_mermaid_mindmap_text(item.category)}")
        for cause in item.causes:
            lines.append(f"      {_escape_mermaid_mindmap_text(cause)}")
    lines.append("```")
    rows = [
        (item.category, "、".join(item.causes), ", ".join(item.cause_ids))
        for item in categories
    ]
    return (
        "### 6.3 原因鱼骨图\n"
        + "\n".join(lines)
        + "\n\n"
        + _markdown_table(["分类", "原因项", "关联原因 ID"], rows)
    )


def _render_incident_root_cause_conclusions(
    items: list[IncidentRootCauseConclusion],
) -> str:
    rows = [
        (
            item.conclusion_type,
            item.description,
            item.category,
            item.related_cause_id,
            item.evidence_strength,
            item.confidence,
            item.actionability,
            item.verification_status,
        )
        for item in items
    ]
    return "### 6.4 根因结论\n" + _markdown_table(
        [
            "类型",
            "描述",
            "归类",
            "关联原因",
            "证据强度",
            "置信度",
            "可行动性",
            "验证状态",
        ],
        rows,
    )


def _render_incident_excluded_causes(items: list[IncidentExcludedCause]) -> str:
    rows = [
        (
            item.exclusion_id,
            item.suspected_cause,
            item.basis,
            item.evidence_strength,
            item.still_monitor,
        )
        for item in items
    ]
    return "### 6.5 排除项\n" + _markdown_table(
        ["排除项", "曾经怀疑原因", "排除依据", "证据强度", "仍需关注"],
        rows,
    )


def _render_incident_unverified_causes(
    items: list[IncidentUnverifiedCause],
) -> str:
    rows = [
        (
            item.cause,
            item.reason,
            item.possible_impact,
            item.verification_action,
            item.owner,
            item.status,
        )
        for item in items
    ]
    return "### 6.6 未验证原因\n" + _markdown_table(
        ["原因", "为什么未验证", "可能影响", "后续验证动作", "owner", "状态"],
        rows,
    )


def _render_incident_root_cause_stage_gate(
    checks: list[StageGateCheck],
) -> str:
    lines = [f"- [{'x' if item.checked else ' '}] {item.item}" for item in checks]
    return "### 6.7 阶段门禁\n" + "\n".join(lines)


def _render_incident_improvement_report_info(
    info: IncidentImprovementReportInfo,
) -> str:
    rows = [
        ("故障名称", info.incident_name),
        ("严重等级", info.severity),
        ("报告版本", info.version),
        ("生成时间", info.generated_at),
        ("改进行动总数", info.action_count),
        ("复查日期", info.review_date),
        ("关闭状态", info.closure_status),
    ]
    return "## 报告信息\n" + _markdown_table(["字段", "内容"], rows)


def _render_incident_improvement_timeline_summary(
    summary: IncidentImprovementTimelineSummary,
) -> str:
    rows = [
        ("关键事件", "<br>".join(summary.key_events)),
        ("影响摘要", summary.impact_summary),
        ("恢复摘要", summary.recovery_summary),
    ]
    return "## 第一部分：事件还原\n" + _markdown_table(["字段", "内容"], rows)


def _render_incident_improvement_root_cause_summary(
    summary: IncidentImprovementRootCauseSummary,
) -> str:
    rows = [
        ("直接原因", summary.direct_cause),
        ("根本原因", summary.root_cause),
        ("促成因素", "<br>".join(summary.contributing_factors)),
        ("证据摘要", summary.evidence_summary),
    ]
    return "## 第二部分：根因分析\n" + _markdown_table(["字段", "内容"], rows)


def _render_incident_improvement_priority_distribution(
    distribution: IncidentImprovementPriorityDistribution,
) -> str:
    lines = [
        "```mermaid",
        "pie title 改进措施优先级分布",
        f'    "紧急" : {distribution.urgent_count}',
        f'    "重要" : {distribution.important_count}',
        f'    "常规" : {distribution.normal_count}',
        "```",
    ]
    rows = [
        ("紧急", distribution.urgent_count),
        ("重要", distribution.important_count),
        ("常规", distribution.normal_count),
    ]
    return (
        "#### 7.1 改进优先级分布\n"
        + "\n".join(lines)
        + "\n\n"
        + _markdown_table(["优先级", "数量"], rows)
    )


def _render_incident_improvement_actions(
    items: list[IncidentImprovementAction],
) -> str:
    rows = [
        (
            item.action_id,
            item.improvement,
            item.action_type,
            item.root_cause_id,
            item.root_cause_type,
            item.owner,
            item.deadline,
            item.verification_method,
            item.acceptance_criteria,
            item.priority,
            item.status,
            item.tracking_method,
        )
        for item in items
    ]
    visual = {
        "type": "action-board",
        "title": "故障改进行动看板",
        "columns": [
            "ID",
            "改进措施",
            "类型",
            "对应根因",
            "建议负责人",
            "完成期限",
            "验证方式",
            "验收标准",
            "优先级",
            "当前状态",
            "追踪机制",
        ],
        "rows": [
            {
                "ID": item.action_id,
                "改进措施": item.improvement,
                "类型": item.action_type,
                "对应根因": item.root_cause_id,
                "建议负责人": item.owner,
                "完成期限": item.deadline,
                "验证方式": item.verification_method,
                "验收标准": item.acceptance_criteria,
                "优先级": item.priority,
                "当前状态": item.status,
                "追踪机制": item.tracking_method,
            }
            for item in items
        ],
    }
    return (
        "#### 7.2 改进行动清单\n"
        + _markdown_table(
            [
                "ID",
                "改进措施",
                "类型",
                "对应根因",
                "根因类型",
                "建议负责人",
                "完成期限",
                "验证方式",
                "验收标准",
                "优先级",
                "当前状态",
                "追踪机制",
            ],
            rows,
        )
        + "\n\n```ai4se-visual\n"
        + json.dumps(visual, ensure_ascii=False, indent=2)
        + "\n```"
    )


def _render_incident_improvement_root_cause_coverage(
    items: list[IncidentRootCauseCoverage],
) -> str:
    rows = [
        (
            item.cause_id,
            item.cause_type,
            item.description,
            ", ".join(item.action_ids),
            item.coverage_status,
            item.uncovered_reason,
            item.risk_acceptor,
        )
        for item in items
    ]
    return "#### 7.3 根因覆盖检查\n" + _markdown_table(
        [
            "根因 ID",
            "类型",
            "根因说明",
            "覆盖行动",
            "覆盖状态",
            "未覆盖原因",
            "风险接受人",
        ],
        rows,
    )


def _render_incident_improvement_prevention_checklist(
    items: list[IncidentPreventionCheckItem],
) -> str:
    rows = [
        (item.item, item.related_cause_id, item.owner, item.status) for item in items
    ]
    return "### 8. 防复发检查清单\n" + _markdown_table(
        ["检查项", "对应根因", "建议负责人", "当前状态"],
        rows,
    )


def _render_incident_improvement_review_plan(
    items: list[IncidentReviewPlanItem],
) -> str:
    rows = [
        (
            item.review_item,
            item.review_date,
            item.reviewer,
            item.evidence,
            item.pass_criteria,
            item.status,
        )
        for item in items
    ]
    return "### 9. 复查计划\n" + _markdown_table(
        ["复查项", "复查日期", "复查人", "证据", "通过标准", "当前状态"],
        rows,
    )


def _render_incident_improvement_residual_risks(
    items: list[IncidentResidualRisk],
) -> str:
    rows = [
        (
            item.risk_id,
            item.risk,
            item.impact,
            item.acceptance_reason,
            item.risk_acceptor,
            item.review_due_date,
            item.status,
        )
        for item in items
    ]
    return "### 10. 遗留风险与风险接受\n" + _markdown_table(
        [
            "风险 ID",
            "风险",
            "影响",
            "接受理由",
            "风险接受人",
            "复查日期",
            "当前状态",
        ],
        rows,
    )


def _render_incident_improvement_lessons(
    items: list[IncidentLessonLearned],
) -> str:
    rows = [
        (item.lesson_id, item.lesson, item.scope, item.sharing_suggestion)
        for item in items
    ]
    return "### 11. 经验教训\n" + _markdown_table(
        ["经验 ID", "经验教训", "适用范围", "传播建议"],
        rows,
    )


def _render_incident_improvement_organizational_learning(
    items: list[IncidentOrganizationalLearning],
) -> str:
    rows = [
        (
            item.learning_item,
            item.audience,
            item.channel,
            item.owner,
            item.due_date,
            item.status,
        )
        for item in items
    ]
    return "### 12. 组织学习\n" + _markdown_table(
        ["学习项", "受众", "渠道", "建议负责人", "完成期限", "当前状态"],
        rows,
    )


def _render_incident_improvement_signoffs(items: list[IncidentSignoff]) -> str:
    rows = [(item.role, item.owner, item.confirmation, item.status) for item in items]
    return "## 签署确认\n" + _markdown_table(
        ["角色", "签署人", "确认项", "当前状态"],
        rows,
    )


def _render_incident_improvement_stage_gate(
    checks: list[StageGateCheck],
) -> str:
    lines = [f"- [{'x' if item.checked else ' '}] {item.item}" for item in checks]
    return "### 13. 阶段门禁\n" + "\n".join(lines)


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
        x_value = _format_mermaid_quadrant_coordinate(risk.occurrence / 5)
        y_value = _format_mermaid_quadrant_coordinate(risk.severity / 5)
        lines.append(
            f'    "{_escape_mermaid_label(risk.name)}": ' f"[{x_value}, {y_value}]"
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


def _render_prd_document_info(info: DocumentInfo) -> str:
    rows = [
        ("Artifact 名称", info.artifact_name),
        ("Workflow", info.workflow),
        ("阶段", info.stage),
        ("状态", info.status),
    ]
    return "## 文档信息\n" + _markdown_table(["字段", "内容"], rows)


def _render_prd_goal_scope(items: list[PrdInventoryItem]) -> str:
    rows = [
        (item.category, item.content, item.source, item.evidence_level, item.status)
        for item in items[:5]
    ]
    return "## PRD 目标与范围\n" + _markdown_table(
        ["类别", "内容", "来源", "证据等级", "状态"],
        rows,
    )


def _render_prd_inventory(items: list[PrdInventoryItem]) -> str:
    rows = [
        (
            item.item_id,
            item.category,
            item.content,
            item.source,
            item.evidence_level,
            item.status,
        )
        for item in items
    ]
    return "## 输入事实清单\n" + _markdown_table(
        ["ID", "类别", "内容", "来源", "证据等级", "状态"],
        rows,
    )


def _render_prd_inventory_mindmap(items: list[PrdInventoryItem]) -> str:
    grouped: dict[str, list[PrdInventoryItem]] = {}
    for item in items:
        grouped.setdefault(item.category, []).append(item)

    lines = [
        "```mermaid",
        "mindmap",
        '  root(("PRD 输入盘点"))',
    ]
    for category, category_items in grouped.items():
        lines.append(f"    {_escape_mermaid_mindmap_text(category)}")
        for item in category_items[:4]:
            lines.append(
                "      " + _escape_mermaid_mindmap_text(f"{item.item_id} {item.status}")
            )
    lines.append("```")
    return "## PRD 输入结构图\n" + "\n".join(lines)


def _render_prd_users_and_scenarios(items: list[PrdInventoryItem]) -> str:
    rows = [
        (item.category, item.content, item.status)
        for item in items
        if item.category in {"目标用户", "用户场景", "业务场景", "使用场景"}
    ] or [(items[0].category, items[0].content, items[0].status)]
    return "## 用户与场景\n" + _markdown_table(
        ["类别", "内容", "状态"],
        rows,
    )


def _render_prd_existing_acceptance(
    criteria: list[PrdAcceptanceCriterion],
) -> str:
    rows = [
        (
            item.criterion_id,
            item.scenario,
            item.given,
            item.when,
            item.then,
            item.testability_level,
            item.status,
        )
        for item in criteria
    ]
    return "## 现有验收材料\n" + _markdown_table(
        ["ID", "场景", "Given", "When", "Then", "可测试性等级", "状态"],
        rows,
    )


def _render_prd_missing_information(
    findings: list[PrdQualityFinding],
) -> str:
    rows = [
        (
            item.finding_id,
            item.dimension,
            item.problem,
            item.blocking,
            item.recommendation,
            item.status,
        )
        for item in findings
    ]
    return "## 缺失信息清单\n" + _markdown_table(
        ["ID", "维度", "缺失或问题", "阻断性", "建议", "状态"],
        rows,
    )


def _render_prd_quality_summary(findings: list[PrdQualityFinding]) -> str:
    p0_count = sum(1 for item in findings if item.severity == "P0")
    p1_count = sum(1 for item in findings if item.severity == "P1")
    blocking_count = sum(1 for item in findings if item.blocking == "阻断")
    rows = [
        ("问题总数", len(findings)),
        ("P0 问题", p0_count),
        ("P1 问题", p1_count),
        ("阻断问题", blocking_count),
        ("当前建议", "先关闭 P0/P1 阻断问题，再进入 Lisa 后续 workflow"),
    ]
    return "## 质量评审摘要\n" + _markdown_table(["指标", "内容"], rows)


def _render_prd_quality_score_matrix(findings: list[PrdQualityFinding]) -> str:
    rows = [
        (item.dimension, item.severity, item.evidence, item.impact) for item in findings
    ]
    visual = {
        "type": "score-matrix",
        "title": "PRD 质量评分矩阵",
        "columns": ["维度", "评分", "依据", "风险"],
        "rows": [
            {
                "维度": item.dimension,
                "评分": item.severity,
                "依据": item.evidence,
                "风险": item.impact,
            }
            for item in findings
        ],
    }
    return (
        "## 质量评分矩阵\n"
        + _markdown_table(["评审维度", "严重级别", "证据", "风险"], rows)
        + "\n\n```ai4se-visual\n"
        + json.dumps(visual, ensure_ascii=False, indent=2)
        + "\n```"
    )


def _render_prd_findings(findings: list[PrdQualityFinding]) -> str:
    rows = [
        (
            item.finding_id,
            item.dimension,
            item.problem,
            item.severity,
            item.blocking,
            item.evidence,
            item.recommendation,
            item.status,
        )
        for item in findings
    ]
    return "## 问题清单\n" + _markdown_table(
        ["ID", "评审维度", "问题", "严重级别", "阻断性", "证据", "建议", "状态"],
        rows,
    )


def _render_prd_risk_impact(findings: list[PrdQualityFinding]) -> str:
    rows = [(item.finding_id, item.impact, item.recommendation) for item in findings]
    return "## 风险影响\n" + _markdown_table(
        ["问题 ID", "影响范围", "缓解建议"],
        rows,
    )


def _render_prd_completion_actions(actions: list[PrdCompletionAction]) -> str:
    rows = [
        (
            item.action_id,
            ", ".join(item.finding_ids),
            item.action,
            item.priority,
            item.owner,
            item.verification_method,
            item.review_condition,
            item.status,
        )
        for item in actions
    ]
    visual = {
        "type": "action-board",
        "title": "PRD 补全任务清单",
        "columns": ["行动", "对应根因", "负责人", "期限", "状态", "验证方式"],
        "rows": [
            {
                "行动": item.action,
                "对应根因": ", ".join(item.finding_ids),
                "负责人": item.owner,
                "期限": "进入下一阶段前",
                "状态": item.status,
                "验证方式": item.verification_method,
            }
            for item in actions
        ],
    }
    return (
        "## 补全任务清单\n"
        + _markdown_table(
            [
                "ID",
                "关联问题",
                "补全动作",
                "优先级",
                "负责人",
                "验证方式",
                "复审条件",
                "状态",
            ],
            rows,
        )
        + "\n\n```ai4se-visual\n"
        + json.dumps(visual, ensure_ascii=False, indent=2)
        + "\n```"
    )


def _render_prd_revision_structure(sections: list[PrdRevisionSection]) -> str:
    rows = [
        (
            item.section_id,
            item.title,
            item.rewrite_goal,
            item.acceptance_note,
            item.status,
        )
        for item in sections
    ]
    visual = {
        "type": "roadmap",
        "title": "PRD 修订路线",
        "columns": ["版本", "时间", "核心功能", "目标", "成功指标"],
        "rows": [
            {
                "版本": item.section_id,
                "时间": "本次修订",
                "核心功能": item.title,
                "目标": item.rewrite_goal,
                "成功指标": item.acceptance_note,
            }
            for item in sections
        ],
    }
    return (
        "## 推荐 PRD 结构\n"
        + _markdown_table(["章节 ID", "章节", "改写目标", "验收说明", "状态"], rows)
        + "\n\n```ai4se-visual\n"
        + json.dumps(visual, ensure_ascii=False, indent=2)
        + "\n```"
    )


def _render_prd_verification_and_review(actions: list[PrdCompletionAction]) -> str:
    rows = [
        (item.action_id, item.verification_method, item.review_condition, item.status)
        for item in actions
    ]
    return "## 验证方式与复审条件\n" + _markdown_table(
        ["动作 ID", "验证方式", "复审条件", "状态"],
        rows,
    )


def _render_prd_core_rewrites(sections: list[PrdRevisionSection]) -> str:
    rows = [
        (item.section_id, item.title, item.recommended_content, item.acceptance_note)
        for item in sections
    ]
    return "## 核心需求改写\n" + _markdown_table(
        ["章节 ID", "章节", "推荐内容", "验收说明"],
        rows,
    )


def _render_prd_acceptance_criteria(
    criteria: list[PrdAcceptanceCriterion],
) -> str:
    rows = [
        (
            item.criterion_id,
            ", ".join(item.related_section_ids),
            item.scenario,
            item.given,
            item.when,
            item.then,
            item.testability_level,
            item.status,
        )
        for item in criteria
    ]
    return "## 验收标准与可测试性\n" + _markdown_table(
        ["ID", "关联章节", "场景", "Given", "When", "Then", "可测试性等级", "状态"],
        rows,
    )


def _render_prd_handoff_inputs(items: list[PrdHandoffInput]) -> str:
    rows = [
        (
            item.input_id,
            ", ".join(item.related_section_ids),
            item.target_workflow,
            item.content,
            item.risk,
            item.status,
        )
        for item in items
    ]
    return "## Lisa Handoff 输入\n" + _markdown_table(
        ["ID", "关联章节", "目标 Workflow", "内容", "风险", "状态"],
        rows,
    )


def _render_prd_review_conditions(actions: list[PrdCompletionAction]) -> str:
    rows = [
        (item.action_id, item.review_condition, item.owner, item.status)
        for item in actions
    ]
    return "## 复审条件\n" + _markdown_table(
        ["动作 ID", "复审条件", "责任方", "状态"],
        rows,
    )


def _render_prd_stage_gate(checks: list[StageGateCheck]) -> str:
    lines = [f"- [{'x' if item.checked else ' '}] {item.item}" for item in checks]
    return "## 阶段门禁\n" + "\n".join(lines)


def _escape_mermaid_label(value: str) -> str:
    return value.replace('"', "'")


def _format_mermaid_quadrant_coordinate(value: float) -> str:
    """Format endpoint coordinates in Mermaid quadrantChart's accepted grammar."""
    if value.is_integer():
        return str(int(value))
    return f"{value:.2f}"


from artifact_data_renderer_value import (
    _render_value_positioning_summary,
    _render_value_flow,
    _render_target_scenarios,
    _render_pain_evidence,
    _render_differentiators,
    _render_business_feasibility,
    _render_value_score_matrix,
    _render_value_assumptions,
    _render_elevator_pitch,
    _render_value_stage_gate,
    _persona_names,
    _render_persona_summary,
    _render_persona_profiles,
    _render_persona_behavior_scenarios,
    _render_persona_decision_chain,
    _render_persona_pain_evidence,
    _render_anti_personas,
    _render_persona_priority_ranking,
    _render_journey_map,
    _render_journey_map_visual,
    _render_journey_stage_details,
    _render_journey_pain_priorities,
    _render_journey_opportunity_scores,
    _render_journey_entry_strategy,
    _render_journey_validation_experiments,
    _render_journey_summary,
    _escape_journey_text,
    _escape_mermaid_time,
    _escape_mermaid_timeline_text,
    _escape_mermaid_mindmap_text,
    _render_blueprint_document_info,
    _render_blueprint_product_overview,
    _render_blueprint_target_users,
    _render_blueprint_requirements,
    _render_blueprint_feature_mindmap,
    _render_blueprint_main_flow,
    _render_blueprint_success_metrics,
    _render_blueprint_mvp_plan,
    _render_blueprint_non_functional_requirements,
    _render_blueprint_acceptance_criteria,
    _render_blueprint_roadmap,
    _render_blueprint_risks,
    _render_blueprint_lisa_handoff_inputs,
    _render_blueprint_stage_gate,
)


def _section(
    section_id: str,
    dependencies: tuple[str, ...],
    render: Callable[[Any], str],
    *,
    validate_projection: Callable[[Any], None] | None = None,
    role: str = "business",
) -> ArtifactSectionSpec:
    return ArtifactSectionSpec(
        section_id=section_id,
        dependencies=dependencies,
        render=render,
        validate_projection=validate_projection,
        role=role,
    )


def _join_rendered_sections(*sections: str) -> str:
    return "\n\n".join(sections)


def _plan_business_section_ids(plan: ArtifactRenderPlan) -> tuple[str, ...]:
    return tuple(
        section.section_id for section in plan.sections if section.role == "business"
    )


def _validate_unique_ids(items: list[Any], attribute: str, label: str) -> set[str]:
    values = [getattr(item, attribute) for item in items]
    if len(values) != len(set(values)):
        raise ValueError(f"{label} contains duplicate {attribute}")
    return set(values)


def _validate_checked_stage_gate(data: Any) -> None:
    if not any(item.checked for item in data.stage_gate):
        raise ValueError("stage_gate must include at least one checked item")


def _validate_strategy_quality_goals(data: Any) -> None:
    _validate_unique_ids(data.quality_goals, "goal_id", "quality_goals")


def _validate_strategy_risks(data: Any) -> None:
    _validate_unique_ids(data.risks, "risk_id", "risks")


def _validate_strategy_techniques(data: Any) -> None:
    goal_ids = _validate_unique_ids(data.quality_goals, "goal_id", "quality_goals")
    risk_ids = _validate_unique_ids(data.risks, "risk_id", "risks")
    point_ids = _validate_unique_ids(data.test_points, "point_id", "test_points")
    _validate_unique_ids(data.test_techniques, "technique_id", "test_techniques")
    unknown: set[str] = set()
    for item in data.test_techniques:
        for value in (item.target, item.applies_to):
            unknown.update(_extract_strategy_reference_ids(value, ("QG",)) - goal_ids)
            unknown.update(_extract_strategy_reference_ids(value, ("R",)) - risk_ids)
            unknown.update(_extract_strategy_reference_ids(value, ("TP",)) - point_ids)
    if unknown:
        raise ValueError(
            "test_techniques references unknown ids: " + ", ".join(sorted(unknown))
        )


def _validate_strategy_layers(data: Any) -> None:
    goal_ids = _validate_unique_ids(data.quality_goals, "goal_id", "quality_goals")
    risk_ids = _validate_unique_ids(data.risks, "risk_id", "risks")
    point_ids = _validate_unique_ids(data.test_points, "point_id", "test_points")
    unknown: set[str] = set()
    for item in data.test_layers:
        unknown.update(
            _extract_strategy_reference_ids(item.related, ("QG",)) - goal_ids
        )
        unknown.update(_extract_strategy_reference_ids(item.related, ("R",)) - risk_ids)
        unknown.update(
            _extract_strategy_reference_ids(item.related, ("TP",)) - point_ids
        )
    if unknown:
        raise ValueError(
            "test_layers references unknown ids: " + ", ".join(sorted(unknown))
        )


def _validate_strategy_test_points(data: Any) -> None:
    goal_ids = _validate_unique_ids(data.quality_goals, "goal_id", "quality_goals")
    risk_ids = _validate_unique_ids(data.risks, "risk_id", "risks")
    technique_ids = _validate_unique_ids(
        data.test_techniques, "technique_id", "test_techniques"
    )
    _validate_unique_ids(data.test_points, "point_id", "test_points")
    unknown: set[str] = set()
    for item in data.test_points:
        unknown.update(
            _extract_strategy_reference_ids(item.quality_goal, ("QG",)) - goal_ids
        )
        unknown.update(_extract_strategy_reference_ids(item.risk, ("R",)) - risk_ids)
        unknown.update(
            _extract_strategy_reference_ids(item.technique, ("TS",)) - technique_ids
        )
    if unknown:
        raise ValueError(
            "test_points references unknown ids: " + ", ".join(sorted(unknown))
        )


def _normalize_case_groups(data: Any) -> tuple[list[Any], set[str]]:
    cases: list[Any] = []
    for group in data.case_groups:
        for case in group.cases:
            if case.dimension is None:
                case.dimension = group.dimension
            elif case.dimension != group.dimension:
                raise ValueError(
                    "case_groups[].cases[].dimension must match outer "
                    "case_groups[].dimension"
                )
            cases.append(case)
    case_ids = _validate_unique_ids(cases, "case_id", "case_groups")
    return cases, case_ids


def _validate_case_groups(data: Any) -> None:
    _normalize_case_groups(data)


def _validate_case_statistics(data: Any) -> None:
    cases, _case_ids = _normalize_case_groups(data)
    expected = CaseStatistics(
        total=len(cases),
        p0_count=sum(1 for case in cases if case.priority == "P0"),
        p1_count=sum(1 for case in cases if case.priority == "P1"),
        p2_count=sum(1 for case in cases if case.priority == "P2"),
    )
    if data.case_statistics is None:
        data.case_statistics = expected
    if data.case_statistics != expected:
        raise ValueError(
            "case_statistics must match case_groups totals and P0/P1/P2 counts"
        )


def _validate_case_automation(data: Any) -> None:
    _cases, case_ids = _normalize_case_groups(data)
    unknown = sorted(
        candidate.case_id
        for candidate in data.automation_candidates
        if candidate.case_id not in case_ids
    )
    if unknown:
        raise ValueError(
            "automation_candidates references unknown case ids: " + ", ".join(unknown)
        )


def _validate_case_coverage(data: Any) -> None:
    _cases, case_ids = _normalize_case_groups(data)
    unknown = sorted(
        case_id
        for trace in data.coverage_trace
        for case_id in trace.covered_cases
        if case_id not in case_ids
    )
    if unknown:
        raise ValueError(
            "coverage_trace references unknown case ids: " + ", ".join(unknown)
        )


def _validate_incident_why_chain(data: Any) -> None:
    levels = [item.level for item in data.why_chain]
    if len(levels) != len(set(levels)):
        raise ValueError("why_chain contains duplicate level")
    if len([item for item in data.why_chain if item.level.startswith("Why-")]) < 3:
        raise ValueError("why_chain must include at least 3 Why rows")


def _validate_incident_cause_evidence(data: Any) -> None:
    why_levels = {item.level for item in data.why_chain}
    cause_ids = [item.cause_id for item in data.cause_evidence]
    if len(cause_ids) != len(set(cause_ids)):
        raise ValueError("cause_evidence contains duplicate cause_id")
    unknown_related_levels = sorted(
        {
            item.related_level
            for item in data.cause_evidence
            if item.related_level not in why_levels
        }
    )
    if unknown_related_levels:
        raise ValueError(
            "cause_evidence references unknown why levels: "
            + ", ".join(unknown_related_levels)
        )


def _validate_story_backlog(data: Any) -> None:
    epic_ids = {item.epic_id for item in data.epics}
    story_ids = [item.story_id for item in data.user_stories]
    if len(story_ids) != len(set(story_ids)):
        raise ValueError("user_stories contains duplicate story_id")
    unknown_epic_ids = sorted(
        {item.epic_id for item in data.user_stories if item.epic_id not in epic_ids}
    )
    if unknown_epic_ids:
        raise ValueError(
            "user_stories references unknown epic ids: " + ", ".join(unknown_epic_ids)
        )


def _validate_story_epics(data: Any) -> None:
    epic_ids = [item.epic_id for item in data.epics]
    if len(epic_ids) != len(set(epic_ids)):
        raise ValueError("epics contains duplicate epic_id")


def _story_ids(data: Any) -> set[str]:
    _validate_story_backlog(data)
    return {item.story_id for item in data.user_stories}


def _validate_story_acceptance_criteria(data: Any) -> None:
    story_ids = _story_ids(data)
    criterion_ids = [item.criterion_id for item in data.acceptance_criteria]
    if len(criterion_ids) != len(set(criterion_ids)):
        raise ValueError("acceptance_criteria contains duplicate criterion_id")
    unknown = sorted(
        item.story_id
        for item in data.acceptance_criteria
        if item.story_id not in story_ids
    )
    if unknown:
        raise ValueError(
            "acceptance_criteria references unknown story ids: " + ", ".join(unknown)
        )


def _validate_story_dependencies(data: Any) -> None:
    story_ids = _story_ids(data)
    dependency_ids = [item.dependency_id for item in data.dependencies]
    if len(dependency_ids) != len(set(dependency_ids)):
        raise ValueError("dependencies contains duplicate dependency_id")
    unknown = sorted(
        story_id
        for item in data.dependencies
        for story_id in item.related_story_ids
        if story_id not in story_ids
    )
    if unknown:
        raise ValueError(
            "dependencies references unknown story ids: " + ", ".join(unknown)
        )


def _validate_story_sprint_slices(data: Any) -> None:
    story_ids = _story_ids(data)
    sprint_ids = [item.sprint_id for item in data.sprint_slices]
    if len(sprint_ids) != len(set(sprint_ids)):
        raise ValueError("sprint_slices contains duplicate sprint_id")
    sprint_by_story_id: dict[str, str] = {}
    duplicate_assignments: set[str] = set()
    for sprint in data.sprint_slices:
        for story_id in sprint.story_ids:
            if story_id not in story_ids:
                raise ValueError(
                    "sprint_slices references unknown story ids: " + story_id
                )
            if story_id in sprint_by_story_id:
                duplicate_assignments.add(story_id)
            else:
                sprint_by_story_id[story_id] = sprint.sprint_id
    if duplicate_assignments:
        raise ValueError(
            "sprint_slices contains duplicate story assignments: "
            + ", ".join(sorted(duplicate_assignments))
        )
    missing = sorted(story_ids - set(sprint_by_story_id))
    if missing:
        raise ValueError(
            "sprint_slices must include every user_stories story_id: "
            + ", ".join(missing)
        )
    mismatched: list[str] = []
    for story in data.user_stories:
        expected_sprint = sprint_by_story_id[story.story_id]
        if story.sprint is None:
            story.sprint = expected_sprint
        elif story.sprint != expected_sprint:
            mismatched.append(story.story_id)
    if mismatched:
        raise ValueError(
            "user_stories.sprint must match sprint_slices.story_ids: "
            + ", ".join(mismatched)
        )


def _validate_story_handoff(data: Any) -> None:
    story_ids = _story_ids(data)
    _validate_story_acceptance_criteria(data)
    criterion_ids = {item.criterion_id for item in data.acceptance_criteria}
    unknown = sorted(
        item.reference_id
        for item in data.lisa_handoff_inputs
        if (item.input_type == "用户故事" and item.reference_id not in story_ids)
        or (item.input_type == "验收标准" and item.reference_id not in criterion_ids)
    )
    if unknown:
        raise ValueError(
            "lisa_handoff_inputs references unknown ids: " + ", ".join(unknown)
        )


def _validate_value_flow_projection(data: Any) -> None:
    validate_value_flow_references(data.value_flow)


def _validate_value_score_projection(data: Any) -> None:
    normalize_value_score_summary(data.score_matrix, data.score_summary)


def _validate_personas_projection(data: Any) -> None:
    validate_persona_ids(data.personas)


def _validate_persona_behavior_projection(data: Any) -> None:
    validate_persona_references(
        data.personas, [item.persona_id for item in data.behavior_scenarios]
    )


def _validate_persona_decision_projection(data: Any) -> None:
    validate_persona_references(
        data.personas, [item.persona_id for item in data.decision_chain]
    )


def _validate_persona_pain_projection(data: Any) -> None:
    validate_persona_references(
        data.personas, [item.persona_id for item in data.pain_evidence]
    )


def _validate_persona_priority_projection(data: Any) -> None:
    validate_persona_priority_ranking(data.personas, data.priority_ranking)


def _validate_journey_stages_projection(data: Any) -> None:
    validate_journey_stages(data.journey_stages)


def _validate_journey_pain_projection(data: Any) -> None:
    validate_journey_pain_priorities(data.journey_stages, data.pain_priorities)


def _validate_journey_opportunity_projection(data: Any) -> None:
    validate_journey_opportunity_scores(data.journey_stages, data.opportunity_scores)


def _validate_journey_entry_projection(data: Any) -> None:
    validate_journey_opportunity_references(
        data.journey_stages,
        [item.related_opportunity for item in data.entry_strategy],
    )


def _validate_journey_experiment_projection(data: Any) -> None:
    validate_journey_opportunity_references(
        data.journey_stages,
        [item.opportunity_id for item in data.validation_experiments],
    )


def _validate_blueprint_requirements_projection(data: Any) -> None:
    validate_blueprint_requirement_references(
        data.requirements,
        [
            feature.requirement_id
            for module in data.feature_modules
            for feature in module.features
            if feature.requirement_id is not None
        ],
    )


def _validate_blueprint_mvp_projection(data: Any) -> None:
    validate_blueprint_requirement_references(
        data.requirements,
        [item.requirement_id for item in data.mvp_plan.included_features],
    )


def _validate_blueprint_acceptance_projection(data: Any) -> None:
    validate_blueprint_acceptance_criteria(data.requirements, data.acceptance_criteria)


def _validate_blueprint_handoff_projection(data: Any) -> None:
    validate_blueprint_handoff_inputs(
        data.requirements,
        data.acceptance_criteria,
        data.lisa_handoff_inputs,
    )


def _validate_blueprint_flow_projection(data: Any) -> None:
    validate_blueprint_main_flow(data.main_flow)


def _validate_idea_define_evidence(data: Any) -> None:
    evidence_ids = [item.evidence_id for item in data.evidence_items]
    if len(evidence_ids) != len(set(evidence_ids)):
        raise ValueError("evidence_items contains duplicate evidence_id")


def _validate_idea_define_landscape(data: Any) -> None:
    problem_ids = [item.problem_id for item in data.problem_landscape.subproblems]
    if len(problem_ids) != len(set(problem_ids)):
        raise ValueError("problem_landscape contains duplicate problem_id")


def _validate_idea_define_fit(data: Any) -> None:
    _validate_idea_define_evidence(data)
    _validate_idea_define_landscape(data)
    evidence_ids = {item.evidence_id for item in data.evidence_items}
    unknown = sorted(
        evidence_id
        for item in data.problem_user_fit
        for evidence_id in item.evidence_ids
        if evidence_id not in evidence_ids
    )
    if unknown:
        raise ValueError(
            "problem_user_fit references unknown evidence ids: " + ", ".join(unknown)
        )
    root_problem = data.problem_landscape.root_problem
    if not (
        any(root_problem in item.related_problem for item in data.evidence_items)
        or any(
            root_problem in item.evidence_or_assumption
            for item in data.problem_user_fit
        )
    ):
        raise ValueError(
            "problem_landscape.root_problem must be covered by evidence_items "
            "or problem_user_fit"
        )


def _validate_idea_cards(data: Any) -> None:
    idea_ids = [item.idea_id for item in data.idea_cards]
    if len(idea_ids) != len(set(idea_ids)):
        raise ValueError("idea_cards contains duplicate idea_id")


def _validate_idea_landscape(data: Any) -> None:
    _validate_idea_cards(data)
    idea_ids = {item.idea_id for item in data.idea_cards}
    unknown = sorted(
        idea_id
        for group in data.idea_landscape.groups
        for idea_id in group.idea_ids
        if idea_id not in idea_ids
    )
    if unknown:
        raise ValueError(
            "idea_landscape references unknown idea ids: " + ", ".join(unknown)
        )


def _validate_idea_sources(data: Any) -> None:
    _validate_idea_cards(data)
    source_ids = [item.source_id for item in data.idea_sources]
    if len(source_ids) != len(set(source_ids)):
        raise ValueError("idea_sources contains duplicate source_id")
    idea_ids = {item.idea_id for item in data.idea_cards}
    unknown = sorted(
        idea_id
        for source in data.idea_sources
        for idea_id in source.idea_ids
        if idea_id not in idea_ids
    )
    if unknown:
        raise ValueError(
            "idea_sources references unknown idea ids: " + ", ".join(unknown)
        )


def _validate_idea_parked(data: Any) -> None:
    record_ids = [item.record_id for item in data.parked_or_excluded]
    if len(record_ids) != len(set(record_ids)):
        raise ValueError("parked_or_excluded contains duplicate record_id")


def _normalize_idea_ice(data: Any) -> None:
    idea_ids = [item.idea_id for item in data.ice_evaluations]
    if len(idea_ids) != len(set(idea_ids)):
        raise ValueError("ice_evaluations contains duplicate idea_id")
    provided_ranks = [
        item.rank for item in data.ice_evaluations if item.rank is not None
    ]
    if len(provided_ranks) != len(set(provided_ranks)):
        raise ValueError("ice_evaluations contains duplicate rank")
    for item in data.ice_evaluations:
        expected_score = item.impact * item.confidence / item.effort
        if item.ice_score is None:
            item.ice_score = expected_score
        elif abs(item.ice_score - expected_score) > 0.01:
            raise ValueError(
                f"ice_evaluations.{item.idea_id}.ice_score must equal "
                "impact * confidence / effort"
            )
    ranked_items = sorted(
        enumerate(data.ice_evaluations),
        key=lambda indexed_item: (-(indexed_item[1].ice_score or 0), indexed_item[0]),
    )
    expected_ranks = {
        id(item): rank for rank, (_index, item) in enumerate(ranked_items, start=1)
    }
    for item in data.ice_evaluations:
        expected_rank = expected_ranks[id(item)]
        if item.rank is None:
            item.rank = expected_rank
        elif item.rank != expected_rank:
            raise ValueError(
                f"ice_evaluations.{item.idea_id}.rank must match "
                "descending ice_score order"
            )


def _validate_idea_decision(data: Any) -> None:
    _normalize_idea_ice(data)
    idea_ids = {item.idea_id for item in data.ice_evaluations}
    recommended_id = data.decision_matrix.recommended_idea_id
    if recommended_id not in idea_ids:
        raise ValueError("decision_matrix.recommended_idea_id is unknown")
    decision_ids = {item.idea_id for item in data.decision_matrix.decision_items}
    unknown = sorted(decision_ids - idea_ids)
    if unknown:
        raise ValueError(
            "decision_matrix references unknown idea ids: " + ", ".join(unknown)
        )
    recommended_evaluation = next(
        item for item in data.ice_evaluations if item.idea_id == recommended_id
    )
    recommended_decision = next(
        (
            item
            for item in data.decision_matrix.decision_items
            if item.idea_id == recommended_id
        ),
        None,
    )
    if (
        "推荐" not in recommended_evaluation.conclusion
        or recommended_decision is None
        or "推荐" not in recommended_decision.decision
    ):
        raise ValueError(
            "recommended idea must match a recommended ICE evaluation "
            "and decision item"
        )


def _validate_idea_experiments(data: Any) -> None:
    _normalize_idea_ice(data)
    idea_ids = {item.idea_id for item in data.ice_evaluations}
    unknown = sorted(
        idea_id
        for experiment in data.validation_experiments
        for idea_id in experiment.idea_ids
        if idea_id not in idea_ids
    )
    if unknown:
        raise ValueError(
            "validation_experiments references unknown idea ids: " + ", ".join(unknown)
        )


def _validate_idea_merge_paths(data: Any) -> None:
    _normalize_idea_ice(data)
    idea_ids = {item.idea_id for item in data.ice_evaluations}
    unknown = sorted(
        idea_id
        for path in data.merge_paths
        for idea_id in path.source_idea_ids
        if idea_id not in idea_ids
    )
    if unknown:
        raise ValueError(
            "merge_paths references unknown idea ids: " + ", ".join(unknown)
        )


def _validate_idea_assumptions(data: Any) -> None:
    ids = [item.assumption_id for item in data.core_assumptions]
    if len(ids) != len(set(ids)):
        raise ValueError("core_assumptions contains duplicate assumption_id")


def _validate_idea_canvas(data: Any) -> None:
    required = {
        "问题",
        "用户群体",
        "独特价值主张",
        "解决方案",
        "渠道",
        "收入来源",
        "成本结构",
        "关键指标",
        "竞争壁垒",
    }
    missing = sorted(required - {item.cell for item in data.lean_canvas})
    if missing:
        raise ValueError("lean_canvas missing required cells: " + ", ".join(missing))


def _validate_idea_funnel(data: Any) -> None:
    required = {"Acquisition", "Activation", "Retention", "Revenue", "Referral"}
    missing = sorted(required - {item.stage for item in data.growth_funnel})
    if missing:
        raise ValueError("growth_funnel missing required stages: " + ", ".join(missing))


def _validate_idea_mvp(data: Any) -> None:
    _validate_idea_assumptions(data)
    assumption_ids = {item.assumption_id for item in data.core_assumptions}
    unknown = sorted(
        assumption_id
        for feature in data.mvp_features
        for assumption_id in feature.assumption_ids
        if assumption_id not in assumption_ids
    )
    if unknown:
        raise ValueError(
            "mvp_features references unknown assumption ids: " + ", ".join(unknown)
        )


def _validate_idea_roadmap(data: Any) -> None:
    _validate_idea_assumptions(data)
    validation_ids = [item.validation_id for item in data.validation_roadmap]
    if len(validation_ids) != len(set(validation_ids)):
        raise ValueError("validation_roadmap contains duplicate validation_id")
    assumption_ids = {item.assumption_id for item in data.core_assumptions}
    unknown = sorted(
        assumption_id
        for item in data.validation_roadmap
        for assumption_id in item.assumption_ids
        if assumption_id not in assumption_ids
    )
    if unknown:
        raise ValueError(
            "validation_roadmap references unknown assumption ids: "
            + ", ".join(unknown)
        )


def _validate_idea_next_actions(data: Any) -> None:
    _validate_idea_assumptions(data)
    _validate_idea_roadmap(data)
    action_ids = [item.action_id for item in data.next_actions]
    if len(action_ids) != len(set(action_ids)):
        raise ValueError("next_actions contains duplicate action_id")
    allowed = (
        {item.assumption_id for item in data.core_assumptions}
        | {item.validation_id for item in data.validation_roadmap}
        | {item.risk_id for item in data.premortem_risks}
    )
    unknown = sorted(
        related_id
        for item in data.next_actions
        for related_id in item.related_ids
        if related_id not in allowed
    )
    if unknown:
        raise ValueError("next_actions references unknown ids: " + ", ".join(unknown))


def _validate_incident_fact_sources(data: Any) -> None:
    fact_ids = [item.fact_id for item in data.fact_sources]
    if len(fact_ids) != len(set(fact_ids)):
        raise ValueError("fact_sources contains duplicate fact_id")


def _validate_incident_timeline_events(data: Any) -> None:
    _validate_incident_fact_sources(data)
    fact_ids = {item.fact_id for item in data.fact_sources}
    unknown = sorted(
        fact_id
        for item in data.timeline_events
        for fact_id in item.fact_ids
        if fact_id not in fact_ids
    )
    if unknown:
        raise ValueError(
            "timeline_events references unknown fact ids: " + ", ".join(unknown)
        )


def _incident_cause_ids(data: Any) -> set[str]:
    cause_ids = [item.cause_id for item in data.cause_evidence]
    if len(cause_ids) != len(set(cause_ids)):
        raise ValueError("cause_evidence contains duplicate cause_id")
    return set(cause_ids)


def _validate_incident_fishbone(data: Any) -> None:
    cause_ids = _incident_cause_ids(data)
    unknown = sorted(
        cause_id
        for item in data.fishbone_categories
        for cause_id in item.cause_ids
        if cause_id not in cause_ids
    )
    if unknown:
        raise ValueError(
            "fishbone_categories references unknown cause ids: " + ", ".join(unknown)
        )


def _validate_incident_conclusions(data: Any) -> None:
    cause_ids = _incident_cause_ids(data)
    unknown = sorted(
        item.related_cause_id
        for item in data.root_cause_conclusions
        if item.related_cause_id not in cause_ids
    )
    if unknown:
        raise ValueError(
            "root_cause_conclusions references unknown cause ids: " + ", ".join(unknown)
        )
    if not any(
        item.conclusion_type == "根本原因" for item in data.root_cause_conclusions
    ):
        raise ValueError("root_cause_conclusions must include root cause conclusion")


def _validate_incident_improvement_action_ids(data: Any) -> set[str]:
    action_ids = [item.action_id for item in data.improvement_actions]
    if len(action_ids) != len(set(action_ids)):
        raise ValueError("improvement_actions contains duplicate action_id")
    return set(action_ids)


def _validate_incident_improvement_report(data: Any) -> None:
    _validate_incident_improvement_action_ids(data)
    expected = len(data.improvement_actions)
    if data.report_info.action_count is None:
        data.report_info.action_count = expected
    elif data.report_info.action_count != expected:
        raise ValueError(
            "report_info.action_count must match improvement_actions length"
        )


def _validate_incident_improvement_coverage(data: Any) -> None:
    action_ids = _validate_incident_improvement_action_ids(data)
    coverage_ids = [item.cause_id for item in data.root_cause_coverage]
    if len(coverage_ids) != len(set(coverage_ids)):
        raise ValueError("root_cause_coverage contains duplicate cause_id")
    coverage_id_set = set(coverage_ids)
    unknown_action_ids = sorted(
        action_id
        for item in data.root_cause_coverage
        for action_id in item.action_ids
        if action_id not in action_ids
    )
    if unknown_action_ids:
        raise ValueError(
            "root_cause_coverage references unknown action ids: "
            + ", ".join(unknown_action_ids)
        )
    unknown_causes = sorted(
        item.root_cause_id
        for item in data.improvement_actions
        if item.root_cause_id not in coverage_id_set
    )
    if unknown_causes:
        raise ValueError(
            "improvement_actions.root_cause_id references unknown coverage cause ids: "
            + ", ".join(unknown_causes)
        )
    uncovered = sorted(
        item.cause_id
        for item in data.root_cause_coverage
        if item.coverage_status == "已覆盖" and not item.action_ids
    )
    if uncovered:
        raise ValueError(
            "root_cause_coverage.coverage_status 已覆盖 requires action_ids: "
            + ", ".join(uncovered)
        )
    grouped: dict[str, set[str]] = {cause_id: set() for cause_id in coverage_id_set}
    for action in data.improvement_actions:
        grouped.setdefault(action.root_cause_id, set()).add(action.action_id)
    mismatched = sorted(
        item.cause_id
        for item in data.root_cause_coverage
        if set(item.action_ids) != grouped.get(item.cause_id, set())
    )
    if mismatched:
        raise ValueError(
            "root_cause_coverage.action_ids must match improvement_actions grouped "
            "by root_cause_id: " + ", ".join(mismatched)
        )


def _validate_delivery_projection(data: Any) -> None:
    total_cases = sum(item.case_count for item in data.case_summary_items)
    if data.delivery_metrics.total_cases is None:
        data.delivery_metrics.total_cases = total_cases
    elif data.delivery_metrics.total_cases != total_cases:
        raise ValueError(
            "delivery_metrics.total_cases must match case_summary_items total_cases"
        )
    high_risk_count = sum(
        1
        for item in data.open_risks
        if "风险" in item.risk_type and item.acceptable != "是"
    )
    if data.delivery_metrics.high_risk_count is None:
        data.delivery_metrics.high_risk_count = high_risk_count
    elif data.delivery_metrics.high_risk_count != high_risk_count:
        raise ValueError(
            "delivery_metrics.high_risk_count must match unacceptable open risks"
        )


def _validate_req_report_closures(data: Any) -> set[str]:
    issue_ids = [item.issue_id for item in data.issue_closures]
    if len(issue_ids) != len(set(issue_ids)):
        raise ValueError("issue_closures contains duplicate issue_id")
    return set(issue_ids)


def _validate_req_report_conditions(data: Any) -> None:
    issue_ids = _validate_req_report_closures(data)
    unknown = sorted(
        issue_id
        for condition in data.review_conditions
        for issue_id in condition.related_issues
        if issue_id not in issue_ids
    )
    if unknown:
        raise ValueError(
            "review_conditions references unknown issue ids: " + ", ".join(unknown)
        )


def _validate_req_report_conclusion(data: Any) -> None:
    _validate_req_report_closures(data)
    has_open_high = any(
        item.priority in {"P0", "P1"} and item.closure_status != "已关闭"
        for item in data.issue_closures
    )
    if data.conclusion.review_result == "通过" and has_open_high:
        raise ValueError(
            "conclusion.review_result cannot be 通过 when open P0/P1 issues remain"
        )


def _validate_prd_findings(data: Any) -> set[str]:
    ids = [item.finding_id for item in data.quality_findings]
    if len(ids) != len(set(ids)):
        raise ValueError("quality_findings contains duplicate finding_id")
    return set(ids)


def _validate_prd_actions(data: Any) -> None:
    finding_ids = _validate_prd_findings(data)
    action_ids = [item.action_id for item in data.completion_actions]
    if len(action_ids) != len(set(action_ids)):
        raise ValueError("completion_actions contains duplicate action_id")
    unknown = sorted(
        finding_id
        for action in data.completion_actions
        for finding_id in action.finding_ids
        if finding_id not in finding_ids
    )
    if unknown:
        raise ValueError(
            "completion_actions references unknown finding ids: " + ", ".join(unknown)
        )


def _prd_section_ids(data: Any) -> set[str]:
    ids = [item.section_id for item in data.revision_sections]
    if len(ids) != len(set(ids)):
        raise ValueError("revision_sections contains duplicate section_id")
    return set(ids)


def _validate_prd_acceptance(data: Any) -> None:
    section_ids = _prd_section_ids(data)
    unknown = sorted(
        section_id
        for criterion in data.acceptance_criteria
        for section_id in criterion.related_section_ids
        if section_id not in section_ids
    )
    if unknown:
        raise ValueError(
            "acceptance_criteria references unknown section ids: " + ", ".join(unknown)
        )


def _validate_prd_handoff(data: Any) -> None:
    section_ids = _prd_section_ids(data)
    unknown = sorted(
        section_id
        for handoff in data.handoff_inputs
        for section_id in handoff.related_section_ids
        if section_id not in section_ids
    )
    if unknown:
        raise ValueError(
            "handoff_inputs references unknown section ids: " + ", ".join(unknown)
        )


def _validate_incident_improvement_actions(data: Any) -> None:
    _validate_incident_improvement_action_ids(data)
    actual_distribution = {
        priority: sum(
            1 for item in data.improvement_actions if item.priority == priority
        )
        for priority in ("紧急", "重要", "常规")
    }
    if data.priority_distribution is None:
        data.priority_distribution = IncidentImprovementPriorityDistribution(
            urgent_count=actual_distribution["紧急"],
            important_count=actual_distribution["重要"],
            normal_count=actual_distribution["常规"],
        )
    for field_name, priority in (
        ("urgent_count", "紧急"),
        ("important_count", "重要"),
        ("normal_count", "常规"),
    ):
        current = getattr(data.priority_distribution, field_name)
        if current is None:
            setattr(
                data.priority_distribution, field_name, actual_distribution[priority]
            )
        elif current != actual_distribution[priority]:
            raise ValueError(
                "priority_distribution must match improvement_actions priorities"
            )


def _validate_req_review_issue_groups(data: Any) -> None:
    _normalize_req_review_issue_groups(data.issue_groups)


def _validate_req_review_statistics_projection(data: Any) -> None:
    _validate_req_review_statistics(data.issue_statistics, data.issue_groups)


def _validate_req_review_suggestions_projection(data: Any) -> None:
    _validate_req_review_suggestions(data.issue_groups, data.revision_suggestions)


def _validate_req_report_statistics_projection(data: Any) -> None:
    counts = {
        "P0": sum(1 for item in data.issue_closures if item.priority == "P0"),
        "P1": sum(1 for item in data.issue_closures if item.priority == "P1"),
        "P2": sum(1 for item in data.issue_closures if item.priority == "P2"),
    }
    if data.issue_statistics is None:
        data.issue_statistics = ReqReviewReportIssueStatistics(
            p0_count=counts["P0"],
            p1_count=counts["P1"],
            p2_count=counts["P2"],
        )
    for priority, field_name in (
        ("P0", "p0_count"),
        ("P1", "p1_count"),
        ("P2", "p2_count"),
    ):
        value = getattr(data.issue_statistics, field_name)
        if value is None:
            setattr(data.issue_statistics, field_name, counts[priority])
        elif value != counts[priority]:
            raise ValueError("issue_statistics must match issue_closures priorities")


CLARIFY_RENDER_PLAN = ArtifactRenderPlan(
    model=ClarifyArtifactData,
    title=lambda _data: "# 需求分析文档",
    title_dependencies=(),
    sections=(
        _section(
            "document-info",
            ("document_info",),
            lambda data: _render_document_info(data.document_info),
            role="metadata",
        ),
        _section(
            "requirement-facts",
            ("requirement_facts",),
            lambda data: _render_requirement_facts(data.requirement_facts),
        ),
        _section(
            "system-boundaries",
            ("system_boundaries",),
            lambda data: _render_system_boundaries(data.system_boundaries),
        ),
        _section(
            "business-rules",
            ("business_rules",),
            lambda data: _render_business_rules(data.business_rules),
        ),
        _section(
            "flow-links",
            ("flow_links",),
            lambda data: _render_flow_links(data.flow_links),
        ),
        _section(
            "clarification-questions",
            ("clarification_questions",),
            lambda data: _render_clarification_questions(data.clarification_questions),
        ),
        _section(
            "quality-requirements",
            ("quality_requirements",),
            lambda data: _render_quality_requirements(data.quality_requirements),
        ),
        _section(
            "downstream-inputs",
            ("downstream_inputs",),
            lambda data: _render_downstream_inputs(data.downstream_inputs),
        ),
        _section(
            "stage-gate",
            ("stage_gate",),
            lambda data: _render_stage_gate(data.stage_gate),
        ),
    ),
)

STRATEGY_RENDER_PLAN = ArtifactRenderPlan(
    model=StrategyArtifactData,
    title=lambda _data: "# 测试策略蓝图",
    title_dependencies=(),
    sections=(
        _section(
            "strategy-summary",
            ("strategy_summary",),
            lambda data: _render_strategy_summary(data.strategy_summary),
        ),
        _section(
            "quality-goals",
            ("quality_goals",),
            lambda data: _render_quality_goals(data.quality_goals),
            validate_projection=_validate_strategy_quality_goals,
        ),
        _section(
            "risks",
            ("risks",),
            lambda data: _render_strategy_risks(data.risks),
            validate_projection=_validate_strategy_risks,
        ),
        _section(
            "test-techniques",
            ("quality_goals", "risks", "test_points", "test_techniques"),
            lambda data: _render_test_techniques(data.test_techniques),
            validate_projection=_validate_strategy_techniques,
        ),
        _section(
            "test-layers",
            ("quality_goals", "risks", "test_points", "test_layers"),
            lambda data: _render_test_layers(data.test_layers),
            validate_projection=_validate_strategy_layers,
        ),
        _section(
            "test-points",
            ("quality_goals", "risks", "test_techniques", "test_points"),
            lambda data: _render_test_points(data.test_points),
            validate_projection=_validate_strategy_test_points,
        ),
        _section(
            "tradeoffs", ("tradeoffs",), lambda data: _render_tradeoffs(data.tradeoffs)
        ),
        _section(
            "stage-gate",
            ("stage_gate",),
            lambda data: _render_stage_gate(data.stage_gate),
            validate_projection=_validate_checked_stage_gate,
        ),
    ),
)

CASES_RENDER_PLAN = ArtifactRenderPlan(
    model=CasesArtifactData,
    title=lambda _data: "# 测试用例集",
    title_dependencies=(),
    sections=(
        _section(
            "case-statistics",
            ("case_statistics", "case_groups"),
            lambda data: _render_case_statistics(data.case_statistics),
            validate_projection=_validate_case_statistics,
        ),
        _section(
            "design-bases",
            ("design_bases",),
            lambda data: _render_design_bases(data.design_bases),
        ),
        _section(
            "case-groups",
            ("case_groups",),
            lambda data: _render_case_groups(data.case_groups),
            validate_projection=_validate_case_groups,
        ),
        _section(
            "test-data-environments",
            ("test_data_environments",),
            lambda data: _render_test_data_environments(data.test_data_environments),
        ),
        _section(
            "automation-candidates",
            ("case_groups", "automation_candidates"),
            lambda data: _render_automation_candidates(data.automation_candidates),
            validate_projection=_validate_case_automation,
        ),
        _section(
            "coverage-trace",
            ("case_groups", "coverage_trace"),
            lambda data: _render_coverage_trace(data.coverage_trace),
            validate_projection=_validate_case_coverage,
        ),
        _section(
            "open-questions",
            ("open_questions",),
            lambda data: _render_open_questions(data.open_questions),
        ),
        _section(
            "stage-gate",
            ("stage_gate",),
            lambda data: _render_stage_gate(data.stage_gate),
            validate_projection=_validate_checked_stage_gate,
        ),
    ),
)

DELIVERY_RENDER_PLAN = ArtifactRenderPlan(
    model=DeliveryArtifactData,
    title=lambda _data: "# 测试设计文档",
    title_dependencies=(),
    sections=(
        _section(
            "document-info",
            (
                "document_info",
                "delivery_metrics",
                "case_summary_items",
                "open_risks",
            ),
            lambda data: _render_delivery_document_info(
                data.document_info, data.delivery_metrics
            ),
            validate_projection=_validate_delivery_projection,
            role="metadata",
        ),
        _section(
            "executive-summary",
            ("executive_summary",),
            lambda data: _render_delivery_executive_summary(data.executive_summary),
        ),
        _section(
            "requirement-summary",
            ("requirement_summary",),
            lambda data: _render_delivery_requirement_summary(data.requirement_summary),
        ),
        _section(
            "strategy-summary",
            ("strategy_summary_items",),
            lambda data: _render_delivery_strategy_summary(data.strategy_summary_items),
        ),
        _section(
            "case-summary",
            ("case_summary_items",),
            lambda data: _render_delivery_case_summary(data.case_summary_items),
        ),
        _section(
            "coverage-map",
            ("coverage_map",),
            lambda data: _render_delivery_coverage_map(data.coverage_map),
        ),
        _section(
            "open-risks",
            ("open_risks",),
            lambda data: _render_delivery_open_risks(data.open_risks),
        ),
        _section(
            "acceptance-checklist",
            ("acceptance_checklist",),
            lambda data: _render_delivery_acceptance_checklist(
                data.acceptance_checklist
            ),
        ),
        _section(
            "signoffs",
            ("signoffs",),
            lambda data: _render_delivery_signoffs(data.signoffs),
        ),
        _section(
            "change-log",
            ("change_log",),
            lambda data: _render_delivery_change_log(data.change_log),
        ),
    ),
)

REQ_REVIEW_REVIEW_RENDER_PLAN = ArtifactRenderPlan(
    model=ReqReviewArtifactData,
    title=lambda _data: "# 需求评审问题清单",
    title_dependencies=(),
    sections=(
        _section(
            "review-info",
            ("review_info",),
            lambda data: _render_req_review_info(data.review_info),
            role="metadata",
        ),
        _section(
            "review-scope",
            ("scope_items",),
            lambda data: _render_req_review_scope(data.scope_items),
        ),
        _section(
            "quality-overview",
            ("quality_overview",),
            lambda data: _join_rendered_sections(
                _render_req_review_quality_overview(data.quality_overview),
                _render_req_review_quality_flowchart(),
            ),
        ),
        _section(
            "issue-statistics",
            ("quality_overview", "issue_statistics", "issue_groups"),
            lambda data: _render_req_review_issue_statistics(
                data.issue_statistics,
                data.quality_overview,
            ),
            validate_projection=_validate_req_review_statistics_projection,
        ),
        _section(
            "issue-groups",
            ("issue_groups",),
            lambda data: _render_req_review_issue_groups(data.issue_groups),
            validate_projection=_validate_req_review_issue_groups,
        ),
        _section(
            "revision-suggestions",
            ("issue_groups", "revision_suggestions"),
            lambda data: _render_req_review_revision_suggestions(
                data.revision_suggestions
            ),
            validate_projection=_validate_req_review_suggestions_projection,
        ),
        _section(
            "stage-gate",
            ("stage_gate",),
            lambda data: _render_req_review_stage_gate(data.stage_gate),
        ),
    ),
)

REQ_REVIEW_REPORT_RENDER_PLAN = ArtifactRenderPlan(
    model=ReqReviewReportArtifactData,
    title=lambda _data: "# 需求评审报告",
    title_dependencies=(),
    sections=(
        _section(
            "conclusion",
            ("conclusion", "issue_closures"),
            lambda data: _render_req_review_report_conclusion(data.conclusion),
            validate_projection=_validate_req_report_conclusion,
        ),
        _section(
            "review-info",
            ("review_info",),
            lambda data: _render_req_review_report_info(data.review_info),
            role="metadata",
        ),
        _section(
            "issue-statistics",
            ("issue_statistics", "issue_closures"),
            lambda data: _render_req_review_report_statistics(data.issue_statistics),
            validate_projection=_validate_req_report_statistics_projection,
        ),
        _section(
            "priority-board",
            ("issue_closures",),
            lambda data: _render_req_review_report_priority_board(data.issue_closures),
            validate_projection=_validate_req_report_closures,
        ),
        _section(
            "issue-closures",
            ("issue_closures",),
            lambda data: _render_req_review_report_issue_closures(data.issue_closures),
            validate_projection=_validate_req_report_closures,
        ),
        _section(
            "review-conditions",
            ("issue_closures", "review_conditions"),
            lambda data: _render_req_review_report_conditions(data.review_conditions),
            validate_projection=_validate_req_report_conditions,
        ),
        _section(
            "signoffs",
            ("signoffs",),
            lambda data: _render_req_review_report_signoffs(data.signoffs),
        ),
        _section(
            "change-log",
            ("change_log",),
            lambda data: _render_req_review_report_change_log(data.change_log),
        ),
    ),
)

INCIDENT_TIMELINE_RENDER_PLAN = ArtifactRenderPlan(
    model=IncidentTimelineArtifactData,
    title=lambda _data: "# 故障复盘报告",
    title_dependencies=(),
    sections=(
        _section(
            "incident-summary",
            ("incident_summary",),
            lambda data: _render_incident_summary(data.incident_summary),
        ),
        _section(
            "impact-metrics",
            ("impact_metrics",),
            lambda data: _render_incident_impact_metrics(data.impact_metrics),
        ),
        _section(
            "fact-sources",
            ("fact_sources",),
            lambda data: _render_incident_fact_sources(data.fact_sources),
            validate_projection=_validate_incident_fact_sources,
        ),
        _section(
            "timeline",
            ("incident_summary", "fact_sources", "timeline_events"),
            lambda data: _render_incident_timeline(
                data.incident_summary, data.timeline_events
            ),
            validate_projection=_validate_incident_timeline_events,
        ),
        _section(
            "fact-separation",
            ("fact_separation",),
            lambda data: _render_incident_fact_separation(data.fact_separation),
        ),
        _section(
            "fact-summary",
            ("fact_summary",),
            lambda data: _render_incident_fact_summary(data.fact_summary),
        ),
        _section(
            "participants",
            ("participants",),
            lambda data: _render_incident_participants(data.participants),
        ),
        _section(
            "missing-information",
            ("missing_information",),
            lambda data: _render_incident_missing_information(data.missing_information),
        ),
        _section(
            "stage-gate",
            ("stage_gate",),
            lambda data: _render_incident_stage_gate(data.stage_gate),
        ),
    ),
)

INCIDENT_ROOT_CAUSE_RENDER_PLAN = ArtifactRenderPlan(
    model=IncidentRootCauseArtifactData,
    title=lambda _data: "# 故障复盘报告",
    title_dependencies=(),
    sections=(
        _section(
            "analysis-context",
            ("analysis_context",),
            lambda data: _render_incident_root_cause_context(data.analysis_context),
        ),
        _section(
            "why-chain",
            ("why_chain",),
            lambda data: _render_incident_why_chain(data.why_chain),
            validate_projection=_validate_incident_why_chain,
        ),
        _section(
            "cause-evidence",
            ("why_chain", "cause_evidence"),
            lambda data: _render_incident_cause_evidence(data.cause_evidence),
            validate_projection=_validate_incident_cause_evidence,
        ),
        _section(
            "fishbone",
            ("analysis_context", "cause_evidence", "fishbone_categories"),
            lambda data: _render_incident_fishbone(
                data.analysis_context, data.fishbone_categories
            ),
            validate_projection=_validate_incident_fishbone,
        ),
        _section(
            "root-cause-conclusions",
            ("cause_evidence", "root_cause_conclusions"),
            lambda data: _render_incident_root_cause_conclusions(
                data.root_cause_conclusions
            ),
            validate_projection=_validate_incident_conclusions,
        ),
        _section(
            "excluded-causes",
            ("excluded_causes",),
            lambda data: _render_incident_excluded_causes(data.excluded_causes),
        ),
        _section(
            "unverified-causes",
            ("unverified_causes",),
            lambda data: _render_incident_unverified_causes(data.unverified_causes),
        ),
        _section(
            "stage-gate",
            ("stage_gate",),
            lambda data: _render_incident_root_cause_stage_gate(data.stage_gate),
            validate_projection=_validate_checked_stage_gate,
        ),
    ),
)

INCIDENT_IMPROVEMENT_RENDER_PLAN = ArtifactRenderPlan(
    model=IncidentImprovementArtifactData,
    title=lambda _data: "# 故障复盘报告",
    title_dependencies=(),
    sections=(
        _section(
            "report-info",
            ("report_info", "improvement_actions"),
            lambda data: _render_incident_improvement_report_info(data.report_info),
            validate_projection=_validate_incident_improvement_report,
            role="metadata",
        ),
        _section(
            "timeline-summary",
            ("timeline_summary",),
            lambda data: _render_incident_improvement_timeline_summary(
                data.timeline_summary
            ),
        ),
        _section(
            "root-cause-summary",
            ("root_cause_summary",),
            lambda data: _render_incident_improvement_root_cause_summary(
                data.root_cause_summary
            ),
        ),
        _section(
            "improvement-actions",
            ("priority_distribution", "improvement_actions"),
            lambda data: _join_rendered_sections(
                "## 第三部分：改进措施",
                "### 7. 改进措施",
                _render_incident_improvement_priority_distribution(
                    data.priority_distribution
                ),
                _render_incident_improvement_actions(data.improvement_actions),
            ),
            validate_projection=_validate_incident_improvement_actions,
        ),
        _section(
            "root-cause-coverage",
            ("improvement_actions", "root_cause_coverage"),
            lambda data: _render_incident_improvement_root_cause_coverage(
                data.root_cause_coverage
            ),
            validate_projection=_validate_incident_improvement_coverage,
        ),
        _section(
            "prevention-checklist",
            ("prevention_checklist",),
            lambda data: _render_incident_improvement_prevention_checklist(
                data.prevention_checklist
            ),
        ),
        _section(
            "review-plan",
            ("review_plan",),
            lambda data: _render_incident_improvement_review_plan(data.review_plan),
        ),
        _section(
            "residual-risks",
            ("residual_risks",),
            lambda data: _render_incident_improvement_residual_risks(
                data.residual_risks
            ),
        ),
        _section(
            "lessons-learned",
            ("lessons_learned",),
            lambda data: _render_incident_improvement_lessons(data.lessons_learned),
        ),
        _section(
            "organizational-learning",
            ("organizational_learning",),
            lambda data: _render_incident_improvement_organizational_learning(
                data.organizational_learning
            ),
        ),
        _section(
            "signoffs",
            ("signoffs",),
            lambda data: _render_incident_improvement_signoffs(data.signoffs),
        ),
        _section(
            "stage-gate",
            ("stage_gate",),
            lambda data: _render_incident_improvement_stage_gate(data.stage_gate),
        ),
    ),
)

IDEA_DEFINE_RENDER_PLAN = ArtifactRenderPlan(
    model=IdeaDefineArtifactData,
    title=lambda _data: "# 问题域分析",
    title_dependencies=(),
    sections=(
        _section(
            "problem-statement",
            ("problem_statement",),
            lambda data: _render_idea_problem_statement(data.problem_statement),
        ),
        _section(
            "target-users",
            ("target_users",),
            lambda data: _render_idea_target_users(data.target_users),
        ),
        _section(
            "problem-landscape",
            ("problem_landscape",),
            lambda data: _render_idea_problem_landscape(data.problem_landscape),
            validate_projection=_validate_idea_define_landscape,
        ),
        _section(
            "evidence-items",
            ("evidence_items",),
            lambda data: _render_idea_evidence_items(data.evidence_items),
            validate_projection=_validate_idea_define_evidence,
        ),
        _section(
            "problem-user-fit",
            ("problem_landscape", "evidence_items", "problem_user_fit"),
            lambda data: _render_idea_problem_user_fit(data.problem_user_fit),
            validate_projection=_validate_idea_define_fit,
        ),
        _section(
            "constraints-boundaries",
            ("constraints_boundaries",),
            lambda data: _render_idea_constraints_boundaries(
                data.constraints_boundaries
            ),
        ),
        _section(
            "reverse-validation",
            ("reverse_validation",),
            lambda data: _render_idea_reverse_validation(data.reverse_validation),
        ),
        _section(
            "stage-gate",
            ("stage_gate",),
            lambda data: _render_idea_stage_gate(data.stage_gate),
            validate_projection=_validate_checked_stage_gate,
        ),
    ),
)

IDEA_DIVERGE_RENDER_PLAN = ArtifactRenderPlan(
    model=IdeaDivergeArtifactData,
    title=lambda _data: "# 创意发散",
    title_dependencies=(),
    sections=(
        _section(
            "divergence-method",
            ("divergence_method",),
            lambda data: _render_idea_divergence_method(data.divergence_method),
        ),
        _section(
            "idea-landscape",
            ("idea_landscape", "idea_cards"),
            lambda data: _render_idea_diverge_landscape(
                data.idea_landscape, data.idea_cards
            ),
            validate_projection=_validate_idea_landscape,
        ),
        _section(
            "idea-cards",
            ("idea_cards",),
            lambda data: _render_idea_cards(data.idea_cards),
            validate_projection=_validate_idea_cards,
        ),
        _section(
            "idea-sources",
            ("idea_cards", "idea_sources"),
            lambda data: _render_idea_sources(data.idea_sources),
            validate_projection=_validate_idea_sources,
        ),
        _section(
            "parked-or-excluded",
            ("parked_or_excluded",),
            lambda data: _render_idea_parked_or_excluded(data.parked_or_excluded),
            validate_projection=_validate_idea_parked,
        ),
        _section(
            "stage-gate",
            ("stage_gate",),
            lambda data: _render_idea_stage_gate(data.stage_gate),
            validate_projection=_validate_checked_stage_gate,
        ),
    ),
)

IDEA_CONVERGE_RENDER_PLAN = ArtifactRenderPlan(
    model=IdeaConvergeArtifactData,
    title=lambda _data: "# 收敛聚焦",
    title_dependencies=(),
    sections=(
        _section(
            "decision-matrix",
            ("decision_matrix", "ice_evaluations"),
            lambda data: _render_idea_converge_decision_matrix(
                data.decision_matrix, data.ice_evaluations
            ),
            validate_projection=_validate_idea_decision,
        ),
        _section(
            "ice-evaluations",
            ("ice_evaluations",),
            lambda data: _render_idea_ice_evaluations(data.ice_evaluations),
            validate_projection=_normalize_idea_ice,
        ),
        _section(
            "resource-constraints",
            ("resource_constraints",),
            lambda data: _render_idea_resource_constraints(data.resource_constraints),
        ),
        _section(
            "sensitivity-analysis",
            ("sensitivity_analysis",),
            lambda data: _render_idea_sensitivity_analysis(data.sensitivity_analysis),
        ),
        _section(
            "validation-experiments",
            ("ice_evaluations", "validation_experiments"),
            lambda data: _render_idea_validation_experiments(
                data.validation_experiments
            ),
            validate_projection=_validate_idea_experiments,
        ),
        _section(
            "merge-paths",
            ("ice_evaluations", "merge_paths"),
            lambda data: _render_idea_merge_paths(data.merge_paths),
            validate_projection=_validate_idea_merge_paths,
        ),
        _section(
            "stage-gate",
            ("stage_gate",),
            lambda data: _render_idea_stage_gate(data.stage_gate),
            validate_projection=_validate_checked_stage_gate,
        ),
    ),
)

IDEA_CONCEPT_RENDER_PLAN = ArtifactRenderPlan(
    model=IdeaConceptArtifactData,
    title=lambda _data: "# 产品概念简报",
    title_dependencies=(),
    sections=(
        _section(
            "positioning-statement",
            ("positioning_statement",),
            lambda data: _render_idea_concept_positioning(data.positioning_statement),
        ),
        _section(
            "core-assumptions",
            ("core_assumptions",),
            lambda data: _render_idea_concept_core_assumptions(data.core_assumptions),
            validate_projection=_validate_idea_assumptions,
        ),
        _section(
            "lean-canvas",
            ("lean_canvas",),
            lambda data: _render_idea_concept_lean_canvas(data.lean_canvas),
            validate_projection=_validate_idea_canvas,
        ),
        _section(
            "mvp-features",
            ("core_assumptions", "mvp_features"),
            lambda data: _render_idea_concept_mvp_features(data.mvp_features),
            validate_projection=_validate_idea_mvp,
        ),
        _section(
            "growth-funnel",
            ("growth_funnel",),
            lambda data: _render_idea_concept_growth_funnel(data.growth_funnel),
            validate_projection=_validate_idea_funnel,
        ),
        _section(
            "premortem-risks",
            ("premortem_risks",),
            lambda data: _render_idea_concept_premortem_risks(data.premortem_risks),
        ),
        _section(
            "validation-roadmap",
            ("core_assumptions", "validation_roadmap"),
            lambda data: _render_idea_concept_validation_roadmap(
                data.validation_roadmap
            ),
            validate_projection=_validate_idea_roadmap,
        ),
        _section(
            "out-of-scope",
            ("out_of_scope",),
            lambda data: _render_idea_concept_out_of_scope(data.out_of_scope),
        ),
        _section(
            "decision-records",
            ("decision_records",),
            lambda data: _render_idea_concept_decision_records(data.decision_records),
        ),
        _section(
            "next-actions",
            (
                "core_assumptions",
                "premortem_risks",
                "validation_roadmap",
                "next_actions",
            ),
            lambda data: _render_idea_concept_next_actions(data.next_actions),
            validate_projection=_validate_idea_next_actions,
        ),
        _section(
            "stage-gate",
            ("stage_gate",),
            lambda data: _render_idea_stage_gate(data.stage_gate),
            validate_projection=_validate_checked_stage_gate,
        ),
    ),
)

VALUE_ELEVATOR_RENDER_PLAN = ArtifactRenderPlan(
    model=ValueDiscoveryElevatorArtifactData,
    title=lambda _data: "# 价值定位分析",
    title_dependencies=(),
    sections=(
        _section(
            "positioning-summary",
            ("positioning_summary",),
            lambda data: _render_value_positioning_summary(data.positioning_summary),
        ),
        _section(
            "value-flow",
            ("value_flow",),
            lambda data: _render_value_flow(data.value_flow),
            validate_projection=_validate_value_flow_projection,
        ),
        _section(
            "target-scenarios",
            ("target_scenarios",),
            lambda data: _render_target_scenarios(data.target_scenarios),
        ),
        _section(
            "pain-evidence",
            ("pain_evidence",),
            lambda data: _render_pain_evidence(data.pain_evidence),
        ),
        _section(
            "differentiators",
            ("differentiators",),
            lambda data: _render_differentiators(data.differentiators),
        ),
        _section(
            "business-feasibility",
            ("business_feasibility",),
            lambda data: _render_business_feasibility(data.business_feasibility),
        ),
        _section(
            "score-matrix",
            ("score_matrix", "score_summary"),
            lambda data: _render_value_score_matrix(
                data.score_matrix, data.score_summary
            ),
            validate_projection=_validate_value_score_projection,
        ),
        _section(
            "assumptions",
            ("assumptions",),
            lambda data: _render_value_assumptions(data.assumptions),
        ),
        _section(
            "elevator-pitch",
            ("elevator_pitch",),
            lambda data: _render_elevator_pitch(data.elevator_pitch),
        ),
        _section(
            "stage-gate",
            ("stage_gate",),
            lambda data: _render_value_stage_gate(data.stage_gate),
        ),
    ),
)

VALUE_PERSONA_RENDER_PLAN = ArtifactRenderPlan(
    model=ValueDiscoveryPersonaArtifactData,
    title=lambda _data: "# 用户画像分析",
    title_dependencies=(),
    sections=(
        _section(
            "persona-summary",
            ("persona_summary",),
            lambda data: _render_persona_summary(data.persona_summary),
        ),
        _section(
            "persona-profiles",
            ("personas",),
            lambda data: _render_persona_profiles(data.personas),
            validate_projection=_validate_personas_projection,
        ),
        _section(
            "behavior-scenarios",
            ("behavior_scenarios", "personas"),
            lambda data: _render_persona_behavior_scenarios(
                data.behavior_scenarios, data.personas
            ),
            validate_projection=_validate_persona_behavior_projection,
        ),
        _section(
            "decision-chain",
            ("decision_chain", "personas"),
            lambda data: _render_persona_decision_chain(
                data.decision_chain, data.personas
            ),
            validate_projection=_validate_persona_decision_projection,
        ),
        _section(
            "pain-evidence",
            ("pain_evidence", "personas"),
            lambda data: _render_persona_pain_evidence(
                data.pain_evidence, data.personas
            ),
            validate_projection=_validate_persona_pain_projection,
        ),
        _section(
            "anti-personas",
            ("anti_personas",),
            lambda data: _render_anti_personas(data.anti_personas),
        ),
        _section(
            "priority-ranking",
            ("priority_ranking", "personas"),
            lambda data: _render_persona_priority_ranking(
                data.priority_ranking, data.personas
            ),
            validate_projection=_validate_persona_priority_projection,
        ),
        _section(
            "stage-gate",
            ("stage_gate",),
            lambda data: _render_value_stage_gate(data.stage_gate),
        ),
    ),
)

VALUE_JOURNEY_RENDER_PLAN = ArtifactRenderPlan(
    model=ValueDiscoveryJourneyArtifactData,
    title=lambda _data: "# 用户旅程分析",
    title_dependencies=(),
    sections=(
        _section(
            "journey-map",
            ("journey_stages",),
            lambda data: _render_journey_map(data.journey_stages),
            validate_projection=_validate_journey_stages_projection,
        ),
        _section(
            "journey-map-visual",
            ("journey_stages",),
            lambda data: _render_journey_map_visual(data.journey_stages),
            validate_projection=_validate_journey_stages_projection,
        ),
        _section(
            "journey-stage-details",
            ("journey_stages",),
            lambda data: _render_journey_stage_details(data.journey_stages),
            validate_projection=_validate_journey_stages_projection,
        ),
        _section(
            "pain-priorities",
            ("pain_priorities", "journey_stages"),
            lambda data: _render_journey_pain_priorities(
                data.pain_priorities, data.journey_stages
            ),
            validate_projection=_validate_journey_pain_projection,
        ),
        _section(
            "opportunity-scores",
            ("journey_stages", "opportunity_scores"),
            lambda data: _render_journey_opportunity_scores(data.opportunity_scores),
            validate_projection=_validate_journey_opportunity_projection,
        ),
        _section(
            "entry-strategy",
            ("journey_stages", "entry_strategy"),
            lambda data: _render_journey_entry_strategy(data.entry_strategy),
            validate_projection=_validate_journey_entry_projection,
        ),
        _section(
            "validation-experiments",
            ("journey_stages", "validation_experiments"),
            lambda data: _render_journey_validation_experiments(
                data.validation_experiments
            ),
            validate_projection=_validate_journey_experiment_projection,
        ),
        _section(
            "journey-summary",
            ("journey_summary",),
            lambda data: _render_journey_summary(data.journey_summary),
        ),
        _section(
            "stage-gate",
            ("stage_gate",),
            lambda data: _render_value_stage_gate(data.stage_gate),
        ),
    ),
)

VALUE_BLUEPRINT_RENDER_PLAN = ArtifactRenderPlan(
    model=ValueDiscoveryBlueprintArtifactData,
    title=lambda data: f"# {data.document_info.product_name} 需求蓝图",
    title_dependencies=("document_info",),
    sections=(
        _section(
            "document-info",
            ("document_info",),
            lambda data: _render_blueprint_document_info(data.document_info),
            role="metadata",
        ),
        _section(
            "product-overview",
            ("product_overview",),
            lambda data: _render_blueprint_product_overview(data.product_overview),
        ),
        _section(
            "target-users",
            ("target_users",),
            lambda data: _render_blueprint_target_users(data.target_users),
        ),
        _section(
            "requirements",
            ("feature_modules", "requirements"),
            lambda data: _render_blueprint_requirements(
                data.feature_modules, data.requirements
            ),
            validate_projection=_validate_blueprint_requirements_projection,
        ),
        _section(
            "main-flow",
            ("main_flow",),
            lambda data: _render_blueprint_main_flow(data.main_flow),
            validate_projection=_validate_blueprint_flow_projection,
        ),
        _section(
            "success-metrics",
            ("success_metrics",),
            lambda data: _render_blueprint_success_metrics(data.success_metrics),
        ),
        _section(
            "mvp-plan",
            ("requirements", "mvp_plan"),
            lambda data: _render_blueprint_mvp_plan(data.mvp_plan),
            validate_projection=_validate_blueprint_mvp_projection,
        ),
        _section(
            "non-functional-requirements",
            ("non_functional_requirements",),
            lambda data: _render_blueprint_non_functional_requirements(
                data.non_functional_requirements
            ),
        ),
        _section(
            "acceptance-criteria",
            ("requirements", "acceptance_criteria"),
            lambda data: _render_blueprint_acceptance_criteria(
                data.acceptance_criteria
            ),
            validate_projection=_validate_blueprint_acceptance_projection,
        ),
        _section(
            "roadmap",
            ("roadmap",),
            lambda data: _render_blueprint_roadmap(data.roadmap),
        ),
        _section("risks", ("risks",), lambda data: _render_blueprint_risks(data.risks)),
        _section(
            "lisa-handoff-inputs",
            ("requirements", "acceptance_criteria", "lisa_handoff_inputs"),
            lambda data: _render_blueprint_lisa_handoff_inputs(
                data.lisa_handoff_inputs
            ),
            validate_projection=_validate_blueprint_handoff_projection,
        ),
        _section(
            "stage-gate",
            ("stage_gate",),
            lambda data: _render_blueprint_stage_gate(data.stage_gate),
        ),
    ),
)

STORY_BREAKDOWN_RENDER_PLAN = ArtifactRenderPlan(
    model=StoryBreakdownArtifactData,
    title=lambda _data: "# 用户故事拆解包",
    title_dependencies=(),
    sections=(
        _section(
            "input-analysis",
            ("input_analysis",),
            lambda data: _render_story_input_analysis(data.input_analysis),
        ),
        _section(
            "epic-map",
            ("input_analysis", "epics"),
            lambda data: _render_story_epic_map(
                data.epics, product_goal=data.input_analysis.product_goal
            ),
            validate_projection=_validate_story_epics,
        ),
        _section(
            "story-backlog",
            ("epics", "user_stories", "sprint_slices"),
            lambda data: _render_story_backlog(data.user_stories),
            validate_projection=_validate_story_sprint_slices,
        ),
        _section(
            "acceptance-criteria",
            ("epics", "user_stories", "acceptance_criteria"),
            lambda data: _render_story_acceptance_criteria(data.acceptance_criteria),
            validate_projection=_validate_story_acceptance_criteria,
        ),
        _section(
            "dependencies",
            ("epics", "user_stories", "dependencies"),
            lambda data: _render_story_dependencies(data.dependencies),
            validate_projection=_validate_story_dependencies,
        ),
        _section(
            "sprint-slices",
            ("epics", "user_stories", "sprint_slices"),
            lambda data: _render_story_sprint_slices(data.sprint_slices),
            validate_projection=_validate_story_sprint_slices,
        ),
        _section(
            "lisa-handoff-inputs",
            (
                "epics",
                "user_stories",
                "acceptance_criteria",
                "lisa_handoff_inputs",
            ),
            lambda data: _render_story_lisa_handoff_inputs(data.lisa_handoff_inputs),
            validate_projection=_validate_story_handoff,
        ),
        _section(
            "stage-gate",
            ("stage_gate",),
            lambda data: _render_story_stage_gate(data.stage_gate),
            validate_projection=_validate_checked_stage_gate,
        ),
    ),
)


def _prd_common_sections() -> tuple[ArtifactSectionSpec, ...]:
    return (
        _section(
            "document-info",
            ("document_info",),
            lambda data: _render_prd_document_info(data.document_info),
            role="metadata",
        ),
        _section(
            "goal-scope",
            ("prd_inventory",),
            lambda data: _render_prd_goal_scope(data.prd_inventory),
        ),
    )


PRD_INVENTORY_RENDER_PLAN = ArtifactRenderPlan(
    model=PrdReviewArtifactData,
    title=lambda _data: "# PRD 输入盘点",
    title_dependencies=(),
    sections=(
        *_prd_common_sections(),
        _section(
            "inventory",
            ("prd_inventory",),
            lambda data: _join_rendered_sections(
                _render_prd_inventory(data.prd_inventory),
                _render_prd_inventory_mindmap(data.prd_inventory),
                _render_prd_users_and_scenarios(data.prd_inventory),
            ),
        ),
        _section(
            "existing-acceptance",
            ("revision_sections", "acceptance_criteria"),
            lambda data: _render_prd_existing_acceptance(data.acceptance_criteria),
            validate_projection=_validate_prd_acceptance,
        ),
        _section(
            "missing-information",
            ("quality_findings",),
            lambda data: _render_prd_missing_information(data.quality_findings),
            validate_projection=_validate_prd_findings,
        ),
        _section(
            "stage-gate",
            ("stage_gate",),
            lambda data: _render_prd_stage_gate(data.stage_gate),
            validate_projection=_validate_checked_stage_gate,
        ),
    ),
)

PRD_QUALITY_AUDIT_RENDER_PLAN = ArtifactRenderPlan(
    model=PrdReviewArtifactData,
    title=lambda _data: "# PRD 质量评审",
    title_dependencies=(),
    sections=(
        *_prd_common_sections(),
        _section(
            "quality-summary",
            ("quality_findings",),
            lambda data: _render_prd_quality_summary(data.quality_findings),
            validate_projection=_validate_prd_findings,
        ),
        _section(
            "quality-score-matrix",
            ("quality_findings",),
            lambda data: _render_prd_quality_score_matrix(data.quality_findings),
            validate_projection=_validate_prd_findings,
        ),
        _section(
            "findings",
            ("quality_findings",),
            lambda data: _render_prd_findings(data.quality_findings),
            validate_projection=_validate_prd_findings,
        ),
        _section(
            "risk-impact",
            ("quality_findings",),
            lambda data: _render_prd_risk_impact(data.quality_findings),
            validate_projection=_validate_prd_findings,
        ),
        _section(
            "stage-gate",
            ("stage_gate",),
            lambda data: _render_prd_stage_gate(data.stage_gate),
            validate_projection=_validate_checked_stage_gate,
        ),
    ),
)

PRD_COMPLETION_PLAN_RENDER_PLAN = ArtifactRenderPlan(
    model=PrdReviewArtifactData,
    title=lambda _data: "# PRD 补全建议",
    title_dependencies=(),
    sections=(
        *_prd_common_sections(),
        _section(
            "quality-summary",
            ("quality_findings",),
            lambda data: _render_prd_quality_summary(data.quality_findings),
            validate_projection=_validate_prd_findings,
        ),
        _section(
            "completion-actions",
            ("quality_findings", "completion_actions"),
            lambda data: _render_prd_completion_actions(data.completion_actions),
            validate_projection=_validate_prd_actions,
        ),
        _section(
            "revision-structure",
            ("revision_sections",),
            lambda data: _render_prd_revision_structure(data.revision_sections),
            validate_projection=_prd_section_ids,
        ),
        _section(
            "verification-review",
            ("quality_findings", "completion_actions"),
            lambda data: _render_prd_verification_and_review(data.completion_actions),
            validate_projection=_validate_prd_actions,
        ),
        _section(
            "stage-gate",
            ("stage_gate",),
            lambda data: _render_prd_stage_gate(data.stage_gate),
            validate_projection=_validate_checked_stage_gate,
        ),
    ),
)

PRD_REVISION_BLUEPRINT_RENDER_PLAN = ArtifactRenderPlan(
    model=PrdReviewArtifactData,
    title=lambda _data: "# PRD 修订蓝图",
    title_dependencies=(),
    sections=(
        *_prd_common_sections(),
        _section(
            "quality-summary",
            ("quality_findings",),
            lambda data: _render_prd_quality_summary(data.quality_findings),
            validate_projection=_validate_prd_findings,
        ),
        _section(
            "completion-actions",
            ("quality_findings", "completion_actions"),
            lambda data: _render_prd_completion_actions(data.completion_actions),
            validate_projection=_validate_prd_actions,
        ),
        _section(
            "revision-structure",
            ("revision_sections",),
            lambda data: _render_prd_revision_structure(data.revision_sections),
            validate_projection=_prd_section_ids,
        ),
        _section(
            "core-rewrites",
            ("revision_sections",),
            lambda data: _render_prd_core_rewrites(data.revision_sections),
            validate_projection=_prd_section_ids,
        ),
        _section(
            "acceptance-criteria",
            ("revision_sections", "acceptance_criteria"),
            lambda data: _render_prd_acceptance_criteria(data.acceptance_criteria),
            validate_projection=_validate_prd_acceptance,
        ),
        _section(
            "handoff-inputs",
            ("revision_sections", "handoff_inputs"),
            lambda data: _render_prd_handoff_inputs(data.handoff_inputs),
            validate_projection=_validate_prd_handoff,
        ),
        _section(
            "review-conditions",
            ("quality_findings", "completion_actions"),
            lambda data: _render_prd_review_conditions(data.completion_actions),
            validate_projection=_validate_prd_actions,
        ),
        _section(
            "stage-gate",
            ("stage_gate",),
            lambda data: _render_prd_stage_gate(data.stage_gate),
            validate_projection=_validate_checked_stage_gate,
        ),
    ),
)


ARTIFACT_DATA_RENDERERS: dict[tuple[str, str], ArtifactRenderPlan] = {
    ("TEST_DESIGN", "CLARIFY"): CLARIFY_RENDER_PLAN,
    ("TEST_DESIGN", "STRATEGY"): STRATEGY_RENDER_PLAN,
    ("TEST_DESIGN", "CASES"): CASES_RENDER_PLAN,
    ("TEST_DESIGN", "DELIVERY"): DELIVERY_RENDER_PLAN,
    ("REQ_REVIEW", "REVIEW"): REQ_REVIEW_REVIEW_RENDER_PLAN,
    ("REQ_REVIEW", "REPORT"): REQ_REVIEW_REPORT_RENDER_PLAN,
    ("INCIDENT_REVIEW", "TIMELINE"): INCIDENT_TIMELINE_RENDER_PLAN,
    ("INCIDENT_REVIEW", "ROOT_CAUSE"): INCIDENT_ROOT_CAUSE_RENDER_PLAN,
    ("INCIDENT_REVIEW", "IMPROVEMENT"): INCIDENT_IMPROVEMENT_RENDER_PLAN,
    ("IDEA_BRAINSTORM", "DEFINE"): IDEA_DEFINE_RENDER_PLAN,
    ("IDEA_BRAINSTORM", "DIVERGE"): IDEA_DIVERGE_RENDER_PLAN,
    ("IDEA_BRAINSTORM", "CONVERGE"): IDEA_CONVERGE_RENDER_PLAN,
    ("IDEA_BRAINSTORM", "CONCEPT"): IDEA_CONCEPT_RENDER_PLAN,
    ("VALUE_DISCOVERY", "ELEVATOR"): VALUE_ELEVATOR_RENDER_PLAN,
    ("VALUE_DISCOVERY", "PERSONA"): VALUE_PERSONA_RENDER_PLAN,
    ("VALUE_DISCOVERY", "JOURNEY"): VALUE_JOURNEY_RENDER_PLAN,
    ("VALUE_DISCOVERY", "BLUEPRINT"): VALUE_BLUEPRINT_RENDER_PLAN,
    ("STORY_BREAKDOWN", "INPUT_ANALYSIS"): STORY_BREAKDOWN_RENDER_PLAN,
    ("STORY_BREAKDOWN", "EPIC_MAPPING"): STORY_BREAKDOWN_RENDER_PLAN,
    ("STORY_BREAKDOWN", "STORY_BACKLOG"): STORY_BREAKDOWN_RENDER_PLAN,
    ("STORY_BREAKDOWN", "SPRINT_PLAN"): STORY_BREAKDOWN_RENDER_PLAN,
    ("PRD_REVIEW", "INVENTORY"): PRD_INVENTORY_RENDER_PLAN,
    ("PRD_REVIEW", "QUALITY_AUDIT"): PRD_QUALITY_AUDIT_RENDER_PLAN,
    ("PRD_REVIEW", "COMPLETION_PLAN"): PRD_COMPLETION_PLAN_RENDER_PLAN,
    ("PRD_REVIEW", "REVISION_BLUEPRINT"): PRD_REVISION_BLUEPRINT_RENDER_PLAN,
}


def get_artifact_render_plan_stage_keys() -> tuple[tuple[str, str], ...]:
    return tuple(sorted(ARTIFACT_DATA_RENDERERS))


def get_artifact_render_plan_business_section_ids(
    workflow_id: str,
    stage_id: str,
) -> tuple[str, ...]:
    plan = ARTIFACT_DATA_RENDERERS.get((workflow_id, stage_id))
    if plan is None:
        raise ValueError(
            "Unsupported artifact_data render contract: "
            f"workflow={workflow_id}, stage={stage_id}"
        )
    return _plan_business_section_ids(plan)


def get_artifact_data_renderer_stage_keys() -> tuple[tuple[str, str], ...]:
    return get_artifact_render_plan_stage_keys()
