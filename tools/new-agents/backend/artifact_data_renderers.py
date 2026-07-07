import json
import re
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

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
        evidence_ids = {item.evidence_id for item in self.evidence_items}
        if len(evidence_ids) != len(self.evidence_items):
            raise ValueError("evidence_items contains duplicate evidence_id")

        problem_ids = {item.problem_id for item in self.problem_landscape.subproblems}
        if len(problem_ids) != len(self.problem_landscape.subproblems):
            raise ValueError("problem_landscape contains duplicate problem_id")

        unknown_fit_evidence_ids = sorted(
            {
                evidence_id
                for item in self.problem_user_fit
                for evidence_id in item.evidence_ids
                if evidence_id not in evidence_ids
            }
        )
        if unknown_fit_evidence_ids:
            raise ValueError(
                "problem_user_fit references unknown evidence ids: "
                + ", ".join(unknown_fit_evidence_ids)
            )

        root_problem = self.problem_landscape.root_problem
        root_problem_covered = any(
            root_problem in item.related_problem for item in self.evidence_items
        ) or any(
            root_problem in item.evidence_or_assumption
            for item in self.problem_user_fit
        )
        if not root_problem_covered:
            raise ValueError(
                "problem_landscape.root_problem must be covered by evidence_items "
                "or problem_user_fit"
            )

        if not any(item.checked for item in self.stage_gate):
            raise ValueError("stage_gate must include at least one checked item")

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
        idea_ids = {item.idea_id for item in self.idea_cards}
        if len(idea_ids) != len(self.idea_cards):
            raise ValueError("idea_cards contains duplicate idea_id")

        source_ids = {item.source_id for item in self.idea_sources}
        if len(source_ids) != len(self.idea_sources):
            raise ValueError("idea_sources contains duplicate source_id")

        record_ids = {item.record_id for item in self.parked_or_excluded}
        if len(record_ids) != len(self.parked_or_excluded):
            raise ValueError("parked_or_excluded contains duplicate record_id")

        unknown_landscape_idea_ids = sorted(
            {
                idea_id
                for group in self.idea_landscape.groups
                for idea_id in group.idea_ids
                if idea_id not in idea_ids
            }
        )
        if unknown_landscape_idea_ids:
            raise ValueError(
                "idea_landscape references unknown idea ids: "
                + ", ".join(unknown_landscape_idea_ids)
            )

        unknown_source_idea_ids = sorted(
            {
                idea_id
                for source in self.idea_sources
                for idea_id in source.idea_ids
                if idea_id not in idea_ids
            }
        )
        if unknown_source_idea_ids:
            raise ValueError(
                "idea_sources references unknown idea ids: "
                + ", ".join(unknown_source_idea_ids)
            )

        if not any(item.checked for item in self.stage_gate):
            raise ValueError("stage_gate must include at least one checked item")

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
    ice_score: float
    rank: int = Field(ge=1)
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
        idea_ids = {item.idea_id for item in self.ice_evaluations}
        if len(idea_ids) != len(self.ice_evaluations):
            raise ValueError("ice_evaluations contains duplicate idea_id")

        ranks = {item.rank for item in self.ice_evaluations}
        if len(ranks) != len(self.ice_evaluations):
            raise ValueError("ice_evaluations contains duplicate rank")

        for item in self.ice_evaluations:
            expected_score = item.impact * item.confidence / item.effort
            if abs(item.ice_score - expected_score) > 0.01:
                raise ValueError(
                    f"ice_evaluations.{item.idea_id}.ice_score must equal "
                    "impact * confidence / effort"
                )

        recommended_idea_id = self.decision_matrix.recommended_idea_id
        if recommended_idea_id not in idea_ids:
            raise ValueError("decision_matrix.recommended_idea_id is unknown")

        decision_idea_ids = {
            item.idea_id for item in self.decision_matrix.decision_items
        }
        unknown_decision_idea_ids = sorted(decision_idea_ids - idea_ids)
        if unknown_decision_idea_ids:
            raise ValueError(
                "decision_matrix references unknown idea ids: "
                + ", ".join(unknown_decision_idea_ids)
            )

        recommended_evaluation = next(
            item for item in self.ice_evaluations if item.idea_id == recommended_idea_id
        )
        recommended_decision = next(
            (
                item
                for item in self.decision_matrix.decision_items
                if item.idea_id == recommended_idea_id
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

        unknown_experiment_idea_ids = sorted(
            {
                idea_id
                for experiment in self.validation_experiments
                for idea_id in experiment.idea_ids
                if idea_id not in idea_ids
            }
        )
        if unknown_experiment_idea_ids:
            raise ValueError(
                "validation_experiments references unknown idea ids: "
                + ", ".join(unknown_experiment_idea_ids)
            )

        unknown_merge_idea_ids = sorted(
            {
                idea_id
                for path in self.merge_paths
                for idea_id in path.source_idea_ids
                if idea_id not in idea_ids
            }
        )
        if unknown_merge_idea_ids:
            raise ValueError(
                "merge_paths references unknown idea ids: "
                + ", ".join(unknown_merge_idea_ids)
            )

        if not any(item.checked for item in self.stage_gate):
            raise ValueError("stage_gate must include at least one checked item")

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
        assumption_ids = {item.assumption_id for item in self.core_assumptions}
        if len(assumption_ids) != len(self.core_assumptions):
            raise ValueError("core_assumptions contains duplicate assumption_id")

        validation_ids = {item.validation_id for item in self.validation_roadmap}
        if len(validation_ids) != len(self.validation_roadmap):
            raise ValueError("validation_roadmap contains duplicate validation_id")

        action_ids = {item.action_id for item in self.next_actions}
        if len(action_ids) != len(self.next_actions):
            raise ValueError("next_actions contains duplicate action_id")

        required_canvas_cells = {
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
        canvas_cells = {item.cell for item in self.lean_canvas}
        missing_canvas_cells = sorted(required_canvas_cells - canvas_cells)
        if missing_canvas_cells:
            raise ValueError(
                "lean_canvas missing required cells: " + ", ".join(missing_canvas_cells)
            )

        required_funnel_stages = {
            "Acquisition",
            "Activation",
            "Retention",
            "Revenue",
            "Referral",
        }
        funnel_stages = {item.stage for item in self.growth_funnel}
        missing_funnel_stages = sorted(required_funnel_stages - funnel_stages)
        if missing_funnel_stages:
            raise ValueError(
                "growth_funnel missing required stages: "
                + ", ".join(missing_funnel_stages)
            )

        unknown_mvp_assumption_ids = sorted(
            {
                assumption_id
                for feature in self.mvp_features
                for assumption_id in feature.assumption_ids
                if assumption_id not in assumption_ids
            }
        )
        if unknown_mvp_assumption_ids:
            raise ValueError(
                "mvp_features references unknown assumption ids: "
                + ", ".join(unknown_mvp_assumption_ids)
            )

        unknown_validation_assumption_ids = sorted(
            {
                assumption_id
                for item in self.validation_roadmap
                for assumption_id in item.assumption_ids
                if assumption_id not in assumption_ids
            }
        )
        if unknown_validation_assumption_ids:
            raise ValueError(
                "validation_roadmap references unknown assumption ids: "
                + ", ".join(unknown_validation_assumption_ids)
            )

        risk_ids = {item.risk_id for item in self.premortem_risks}
        allowed_next_action_refs = assumption_ids | validation_ids | risk_ids
        unknown_next_action_refs = sorted(
            {
                related_id
                for item in self.next_actions
                for related_id in item.related_ids
                if related_id not in allowed_next_action_refs
            }
        )
        if unknown_next_action_refs:
            raise ValueError(
                "next_actions references unknown ids: "
                + ", ".join(unknown_next_action_refs)
            )

        if not any(item.checked for item in self.stage_gate):
            raise ValueError("stage_gate must include at least one checked item")

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
        fact_ids = {item.fact_id for item in self.fact_sources}
        if len(fact_ids) != len(self.fact_sources):
            raise ValueError("fact_sources contains duplicate fact_id")

        referenced_fact_ids = [
            fact_id for item in self.timeline_events for fact_id in item.fact_ids
        ]
        unknown_fact_ids = sorted(
            {fact_id for fact_id in referenced_fact_ids if fact_id not in fact_ids}
        )
        if unknown_fact_ids:
            raise ValueError(
                "timeline_events references unknown fact ids: "
                + ", ".join(unknown_fact_ids)
            )
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
        why_levels = {item.level for item in self.why_chain}
        why_rows = [item for item in self.why_chain if item.level.startswith("Why-")]
        if len(why_rows) < 3:
            raise ValueError("why_chain must include at least 3 Why rows")

        cause_ids = {item.cause_id for item in self.cause_evidence}
        if len(cause_ids) != len(self.cause_evidence):
            raise ValueError("cause_evidence contains duplicate cause_id")

        unknown_related_levels = sorted(
            {
                item.related_level
                for item in self.cause_evidence
                if item.related_level not in why_levels
            }
        )
        if unknown_related_levels:
            raise ValueError(
                "cause_evidence references unknown why levels: "
                + ", ".join(unknown_related_levels)
            )

        unknown_fishbone_cause_ids = sorted(
            {
                cause_id
                for item in self.fishbone_categories
                for cause_id in item.cause_ids
                if cause_id not in cause_ids
            }
        )
        if unknown_fishbone_cause_ids:
            raise ValueError(
                "fishbone_categories references unknown cause ids: "
                + ", ".join(unknown_fishbone_cause_ids)
            )

        unknown_conclusion_cause_ids = sorted(
            {
                item.related_cause_id
                for item in self.root_cause_conclusions
                if item.related_cause_id not in cause_ids
            }
        )
        if unknown_conclusion_cause_ids:
            raise ValueError(
                "root_cause_conclusions references unknown cause ids: "
                + ", ".join(unknown_conclusion_cause_ids)
            )

        if not any(
            item.conclusion_type == "根本原因" for item in self.root_cause_conclusions
        ):
            raise ValueError(
                "root_cause_conclusions must include root cause conclusion"
            )
        return self


class IncidentImprovementReportInfo(StrictArtifactDataModel):
    incident_name: str
    severity: str
    version: str
    generated_at: str
    action_count: int = Field(ge=1)
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
    urgent_count: int = Field(ge=0)
    important_count: int = Field(ge=0)
    normal_count: int = Field(ge=0)


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
    priority_distribution: IncidentImprovementPriorityDistribution
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
        action_ids = {item.action_id for item in self.improvement_actions}
        if len(action_ids) != len(self.improvement_actions):
            raise ValueError("improvement_actions contains duplicate action_id")

        if self.report_info.action_count != len(self.improvement_actions):
            raise ValueError(
                "report_info.action_count must match improvement_actions length"
            )

        expected_distribution = {
            "紧急": self.priority_distribution.urgent_count,
            "重要": self.priority_distribution.important_count,
            "常规": self.priority_distribution.normal_count,
        }
        actual_distribution = {
            priority: sum(
                1 for item in self.improvement_actions if item.priority == priority
            )
            for priority in expected_distribution
        }
        if actual_distribution != expected_distribution:
            raise ValueError(
                "priority_distribution must match improvement_actions priorities"
            )

        coverage_cause_ids = {item.cause_id for item in self.root_cause_coverage}
        if len(coverage_cause_ids) != len(self.root_cause_coverage):
            raise ValueError("root_cause_coverage contains duplicate cause_id")

        unknown_coverage_action_ids = sorted(
            {
                action_id
                for item in self.root_cause_coverage
                for action_id in item.action_ids
                if action_id not in action_ids
            }
        )
        if unknown_coverage_action_ids:
            raise ValueError(
                "root_cause_coverage references unknown action ids: "
                + ", ".join(unknown_coverage_action_ids)
            )

        unknown_action_root_causes = sorted(
            {
                item.root_cause_id
                for item in self.improvement_actions
                if item.root_cause_id not in coverage_cause_ids
            }
        )
        if unknown_action_root_causes:
            raise ValueError(
                "improvement_actions.root_cause_id references unknown coverage "
                "cause ids: " + ", ".join(unknown_action_root_causes)
            )

        uncovered_completed_causes = [
            item.cause_id
            for item in self.root_cause_coverage
            if item.coverage_status == "已覆盖" and not item.action_ids
        ]
        if uncovered_completed_causes:
            raise ValueError(
                "root_cause_coverage.coverage_status 已覆盖 requires action_ids: "
                + ", ".join(uncovered_completed_causes)
            )

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
        elif self.rpn != expected:
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


class JourneySummary(StrictArtifactDataModel):
    core_persona: str
    core_pain: str
    entry_strategy: str
    blueprint_readiness: str


class JourneyStage(StrictArtifactDataModel):
    stage_id: str
    stage_name: str
    user_task: str
    touchpoint: str
    user_goal: str
    user_behavior: str
    emotion_score: int = Field(ge=1, le=5)
    emotion_reason: str
    pain_id: str
    key_pain: str
    existing_solution_gap: str
    opportunity_id: str
    opportunity_hypothesis: str
    success_metric: str
    validation_status: str


class JourneyPainPriority(StrictArtifactDataModel):
    priority_level: str
    pain_id: str
    pain: str
    stage_id: str
    impact: str
    frequency: str
    existing_solution_gap: str


class JourneyOpportunityScore(StrictArtifactDataModel):
    opportunity_id: str
    opportunity: str
    pain_id: str
    value_potential: str
    competition_strength: str
    feasibility: str
    success_metric: str
    validation_status: str


class JourneyEntryStrategy(StrictArtifactDataModel):
    strategy_item: str
    content: str
    related_opportunity: str
    tradeoff_reason: str
    status: str


class JourneyValidationExperiment(StrictArtifactDataModel):
    experiment_id: str
    hypothesis: str
    opportunity_id: str
    method: str
    success_metric: str
    owner: str
    status: str


class ValueDiscoveryJourneyArtifactData(StrictArtifactDataModel):
    document_info: DocumentInfo
    journey_summary: JourneySummary
    journey_stages: list[JourneyStage] = Field(min_length=1)
    pain_priorities: list[JourneyPainPriority] = Field(min_length=1)
    opportunity_scores: list[JourneyOpportunityScore] = Field(min_length=1)
    entry_strategy: list[JourneyEntryStrategy] = Field(min_length=1)
    validation_experiments: list[JourneyValidationExperiment] = Field(min_length=1)
    stage_gate: list[StageGateCheck] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_journey_consistency(self) -> "ValueDiscoveryJourneyArtifactData":
        stage_ids = {item.stage_id for item in self.journey_stages}
        if len(stage_ids) != len(self.journey_stages):
            raise ValueError("journey_stages contains duplicate stage_id")

        pain_ids = {item.pain_id for item in self.journey_stages}
        if len(pain_ids) != len(self.journey_stages):
            raise ValueError("journey_stages contains duplicate pain_id")

        opportunity_ids = {item.opportunity_id for item in self.journey_stages}
        if len(opportunity_ids) != len(self.journey_stages):
            raise ValueError("journey_stages contains duplicate opportunity_id")

        unknown_stage_ids = sorted(
            {
                item.stage_id
                for item in self.pain_priorities
                if item.stage_id not in stage_ids
            }
        )
        if unknown_stage_ids:
            raise ValueError(
                "pain_priorities references unknown stage ids: "
                + ", ".join(unknown_stage_ids)
            )

        referenced_pain_ids = [
            *(item.pain_id for item in self.pain_priorities),
            *(item.pain_id for item in self.opportunity_scores),
        ]
        unknown_pain_ids = sorted(
            {pain_id for pain_id in referenced_pain_ids if pain_id not in pain_ids}
        )
        if unknown_pain_ids:
            raise ValueError(
                "journey references unknown pain ids: " + ", ".join(unknown_pain_ids)
            )

        referenced_opportunity_ids = [
            *(item.opportunity_id for item in self.opportunity_scores),
            *(item.related_opportunity for item in self.entry_strategy),
            *(item.opportunity_id for item in self.validation_experiments),
        ]
        unknown_opportunity_ids = sorted(
            {
                opportunity_id
                for opportunity_id in referenced_opportunity_ids
                if opportunity_id not in opportunity_ids
            }
        )
        if unknown_opportunity_ids:
            raise ValueError(
                "journey references unknown opportunity ids: "
                + ", ".join(unknown_opportunity_ids)
            )

        return self


class BlueprintDocumentInfo(StrictArtifactDataModel):
    product_name: str
    version: str
    created_at: str
    product_direction: str
    artifact_name: str
    blueprint_status: str


class BlueprintProductOverview(StrictArtifactDataModel):
    vision: str
    positioning_for: str
    positioning_who: str
    positioning_product: str
    positioning_category: str
    positioning_value: str
    positioning_unlike: str
    positioning_differentiator: str
    user_value: str
    business_value: str
    business_model: str


class BlueprintTargetUser(StrictArtifactDataModel):
    user_type: str
    core_pain: str
    priority: str


class BlueprintFeatureItem(StrictArtifactDataModel):
    feature_id: str
    feature_name: str
    requirement_id: str | None = None


class BlueprintFeatureModule(StrictArtifactDataModel):
    module_id: str
    module_name: str
    features: list[BlueprintFeatureItem] = Field(min_length=1)


class BlueprintRequirement(StrictArtifactDataModel):
    requirement_id: str
    priority: str
    name: str
    user_story: str
    related_pain: str
    scope: str
    dependency: str
    acceptance: str
    testability_level: str
    owner: str
    status: str


class BlueprintFlowNode(StrictArtifactDataModel):
    node_id: str
    label: str


class BlueprintFlowLink(StrictArtifactDataModel):
    from_node: str
    to_node: str
    label: str


class BlueprintMainFlow(StrictArtifactDataModel):
    nodes: list[BlueprintFlowNode] = Field(min_length=1)
    links: list[BlueprintFlowLink] = Field(min_length=1)


class BlueprintSuccessMetric(StrictArtifactDataModel):
    metric_type: str
    metric_name: str
    target: str
    measurement: str


class BlueprintMvpFeature(StrictArtifactDataModel):
    requirement_id: str
    feature_name: str
    included: bool
    release: str


class BlueprintIteration(StrictArtifactDataModel):
    version: str
    time: str
    core_features: str
    goal: str


class BlueprintMvpPlan(StrictArtifactDataModel):
    included_features: list[BlueprintMvpFeature] = Field(min_length=1)
    iterations: list[BlueprintIteration] = Field(min_length=1)


class BlueprintNonFunctionalRequirement(StrictArtifactDataModel):
    type: str
    description: str
    metric_or_constraint: str
    verification: str
    owner: str
    status: str


class BlueprintAcceptanceCriterion(StrictArtifactDataModel):
    acceptance_id: str
    requirement_id: str
    criterion: str
    verification: str
    testability_level: str
    owner: str
    status: str


class BlueprintRoadmapItem(StrictArtifactDataModel):
    version: str
    time: str
    core_features: str
    goal: str
    success_metric: str


class BlueprintRisk(StrictArtifactDataModel):
    risk_type: str
    description: str
    probability: str
    impact: str
    mitigation: str
    owner: str
    status: str


class BlueprintLisaHandoffInput(StrictArtifactDataModel):
    input_type: str
    reference_id: str
    content: str
    source: str
    usage: str
    status: str


class ValueDiscoveryBlueprintArtifactData(StrictArtifactDataModel):
    document_info: BlueprintDocumentInfo
    product_overview: BlueprintProductOverview
    target_users: list[BlueprintTargetUser] = Field(min_length=1)
    feature_modules: list[BlueprintFeatureModule] = Field(min_length=1)
    requirements: list[BlueprintRequirement] = Field(min_length=1)
    main_flow: BlueprintMainFlow
    success_metrics: list[BlueprintSuccessMetric] = Field(min_length=1)
    mvp_plan: BlueprintMvpPlan
    non_functional_requirements: list[BlueprintNonFunctionalRequirement] = Field(
        min_length=1
    )
    acceptance_criteria: list[BlueprintAcceptanceCriterion] = Field(min_length=1)
    roadmap: list[BlueprintRoadmapItem] = Field(min_length=1)
    risks: list[BlueprintRisk] = Field(min_length=1)
    lisa_handoff_inputs: list[BlueprintLisaHandoffInput] = Field(min_length=1)
    stage_gate: list[StageGateCheck] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_blueprint_consistency(self) -> "ValueDiscoveryBlueprintArtifactData":
        requirement_ids = {item.requirement_id for item in self.requirements}
        if len(requirement_ids) != len(self.requirements):
            raise ValueError("requirements contains duplicate requirement_id")

        acceptance_ids = {item.acceptance_id for item in self.acceptance_criteria}
        if len(acceptance_ids) != len(self.acceptance_criteria):
            raise ValueError("acceptance_criteria contains duplicate acceptance_id")

        feature_requirement_ids = [
            feature.requirement_id
            for module in self.feature_modules
            for feature in module.features
            if feature.requirement_id is not None
        ]
        referenced_requirement_ids = [
            *feature_requirement_ids,
            *(item.requirement_id for item in self.mvp_plan.included_features),
            *(item.requirement_id for item in self.acceptance_criteria),
            *(
                item.reference_id
                for item in self.lisa_handoff_inputs
                if item.input_type == "需求"
            ),
        ]
        unknown_requirement_ids = sorted(
            {
                requirement_id
                for requirement_id in referenced_requirement_ids
                if requirement_id not in requirement_ids
            }
        )
        if unknown_requirement_ids:
            raise ValueError(
                "blueprint references unknown requirement ids: "
                + ", ".join(unknown_requirement_ids)
            )

        unknown_acceptance_ids = sorted(
            {
                item.reference_id
                for item in self.lisa_handoff_inputs
                if item.input_type == "验收标准"
                and item.reference_id not in acceptance_ids
            }
        )
        if unknown_acceptance_ids:
            raise ValueError(
                "blueprint references unknown acceptance ids: "
                + ", ".join(unknown_acceptance_ids)
            )

        flow_node_ids = {item.node_id for item in self.main_flow.nodes}
        if len(flow_node_ids) != len(self.main_flow.nodes):
            raise ValueError("main_flow.nodes contains duplicate node_id")
        unknown_flow_nodes = sorted(
            {
                node_id
                for link in self.main_flow.links
                for node_id in (link.from_node, link.to_node)
                if node_id not in flow_node_ids
            }
        )
        if unknown_flow_nodes:
            raise ValueError(
                "main_flow.links references unknown node ids: "
                + ", ".join(unknown_flow_nodes)
            )

        return self


class UserStoryRequirementRef(StrictArtifactDataModel):
    requirement_id: str
    name: str
    priority: str
    status: str


class UserStoryScopeRequirement(StrictArtifactDataModel):
    requirement_id: str
    name: str
    user_value: str
    priority: str
    split_decision: str
    status: str


class UserStoryScopeTrace(StrictArtifactDataModel):
    requirement_id: str
    source: str
    target_user: str
    scenario: str
    acceptance_hint: str
    status: str


class UserStoryOutOfScopeItem(StrictArtifactDataModel):
    requirement_id: str
    item: str
    reason: str
    reentry_condition: str
    status: str


class UserStoryBlockingQuestion(StrictArtifactDataModel):
    question_id: str
    requirement_id: str
    question: str
    impact: str
    owner: str
    status: str


class UserStoryScopeArtifactData(StrictArtifactDataModel):
    document_info: DocumentInfo
    in_scope_requirements: list[UserStoryScopeRequirement] = Field(min_length=1)
    traceability_index: list[UserStoryScopeTrace] = Field(min_length=1)
    out_of_scope_items: list[UserStoryOutOfScopeItem] = Field(min_length=1)
    blocking_questions: list[UserStoryBlockingQuestion] = Field(min_length=1)
    stage_gate: list[StageGateCheck] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_scope_consistency(self) -> "UserStoryScopeArtifactData":
        in_scope_ids = _unique_ids(
            [item.requirement_id for item in self.in_scope_requirements],
            "in_scope_requirements",
            "requirement_id",
        )
        out_scope_ids = _unique_ids(
            [item.requirement_id for item in self.out_of_scope_items],
            "out_of_scope_items",
            "requirement_id",
        )
        trace_ids = _unique_ids(
            [item.requirement_id for item in self.traceability_index],
            "traceability_index",
            "requirement_id",
        )
        unknown_trace_ids = sorted(trace_ids - in_scope_ids)
        if unknown_trace_ids:
            raise ValueError(
                "traceability_index references unknown requirement ids: "
                + ", ".join(unknown_trace_ids)
            )
        known_requirement_ids = in_scope_ids | out_scope_ids
        unknown_question_ids = sorted(
            {
                item.requirement_id
                for item in self.blocking_questions
                if item.requirement_id not in known_requirement_ids
            }
        )
        if unknown_question_ids:
            raise ValueError(
                "blocking_questions references unknown requirement ids: "
                + ", ".join(unknown_question_ids)
            )
        _unique_ids(
            [item.question_id for item in self.blocking_questions],
            "blocking_questions",
            "question_id",
        )
        return self


class UserStoryActivity(StrictArtifactDataModel):
    activity_id: str
    activity: str
    user_goal: str
    requirement_ids: list[str] = Field(min_length=1)
    priority: str


class UserStoryTask(StrictArtifactDataModel):
    task_id: str
    activity_id: str
    task: str
    success_result: str
    requirement_ids: list[str] = Field(min_length=1)
    status: str


class UserStoryMapItem(StrictArtifactDataModel):
    story_id: str
    activity_id: str
    task_id: str
    title: str
    requirement_ids: list[str] = Field(min_length=1)
    slice_id: str
    status: str


class UserStoryMvpSlice(StrictArtifactDataModel):
    slice_id: str
    story_ids: list[str] = Field(min_length=1)
    business_outcome: str
    excluded_items: list[str] = Field(min_length=1)
    acceptance: str


class UserStoryReleaseSlice(StrictArtifactDataModel):
    slice_id: str
    story_ids: list[str] = Field(min_length=1)
    release_goal: str
    dependencies: list[str] = Field(min_length=1)
    status: str


class UserStoryMapArtifactData(StrictArtifactDataModel):
    document_info: DocumentInfo
    requirements: list[UserStoryRequirementRef] = Field(min_length=1)
    activities: list[UserStoryActivity] = Field(min_length=1)
    tasks: list[UserStoryTask] = Field(min_length=1)
    story_map_items: list[UserStoryMapItem] = Field(min_length=1)
    mvp_slices: list[UserStoryMvpSlice] = Field(min_length=1)
    release_slices: list[UserStoryReleaseSlice] = Field(min_length=1)
    stage_gate: list[StageGateCheck] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_story_map_consistency(self) -> "UserStoryMapArtifactData":
        requirement_ids = _unique_ids(
            [item.requirement_id for item in self.requirements],
            "requirements",
            "requirement_id",
        )
        activity_ids = _unique_ids(
            [item.activity_id for item in self.activities],
            "activities",
            "activity_id",
        )
        task_ids = _unique_ids(
            [item.task_id for item in self.tasks],
            "tasks",
            "task_id",
        )
        story_ids = _unique_ids(
            [item.story_id for item in self.story_map_items],
            "story_map_items",
            "story_id",
        )
        slice_ids = _unique_ids(
            [item.slice_id for item in self.mvp_slices + self.release_slices],
            "slices",
            "slice_id",
        )
        _validate_known_ids(
            {
                requirement_id
                for item in self.activities
                for requirement_id in item.requirement_ids
            },
            requirement_ids,
            "activities references unknown requirement ids",
        )
        _validate_known_ids(
            {item.activity_id for item in self.tasks},
            activity_ids,
            "tasks references unknown activity ids",
        )
        _validate_known_ids(
            {
                requirement_id
                for item in self.tasks
                for requirement_id in item.requirement_ids
            },
            requirement_ids,
            "tasks references unknown requirement ids",
        )
        _validate_known_ids(
            {item.activity_id for item in self.story_map_items},
            activity_ids,
            "story_map_items references unknown activity ids",
        )
        _validate_known_ids(
            {item.task_id for item in self.story_map_items},
            task_ids,
            "story_map_items references unknown task ids",
        )
        _validate_known_ids(
            {
                requirement_id
                for item in self.story_map_items
                for requirement_id in item.requirement_ids
            },
            requirement_ids,
            "story_map_items references unknown requirement ids",
        )
        _validate_known_ids(
            {item.slice_id for item in self.story_map_items},
            slice_ids,
            "story_map_items references unknown slice ids",
        )
        _validate_known_ids(
            {
                story_id
                for item in self.mvp_slices + self.release_slices
                for story_id in item.story_ids
            },
            story_ids,
            "slices reference unknown story ids",
        )
        return self


class UserStorySplitPrinciple(StrictArtifactDataModel):
    principle: str
    applied: str
    anti_pattern: str


class UserStoryCard(StrictArtifactDataModel):
    story_id: str
    title: str
    user_role: str
    user_goal: str
    benefit: str
    requirement_ids: list[str] = Field(min_length=1)
    activity_id: str
    task_id: str
    business_rules: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    non_functional_notes: list[str] = Field(default_factory=list)
    out_of_scope: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    status: Literal["ready", "not_ready"]
    blocker_reason: str | None = None


class UserStoryReadySummary(StrictArtifactDataModel):
    story_id: str
    ready_reason: str
    handoff_summary: str
    acceptance_criteria_count: int = Field(ge=1)
    concerns: str


class UserStoryNotReadySummary(StrictArtifactDataModel):
    story_id: str
    requirement_ids: list[str] = Field(min_length=1)
    blocker_reason: str
    questions: list[str] = Field(min_length=1)
    suggested_next_step: str
    status: Literal["not_ready"]


class UserStoryOpenQuestion(StrictArtifactDataModel):
    question_id: str
    story_id: str
    question: str
    decision_impact: str
    owner: str
    status: str


class UserStoriesArtifactData(StrictArtifactDataModel):
    document_info: DocumentInfo
    requirements: list[UserStoryRequirementRef] = Field(min_length=1)
    split_principles: list[UserStorySplitPrinciple] = Field(min_length=1)
    story_cards: list[UserStoryCard] = Field(min_length=1)
    ready_story_summaries: list[UserStoryReadySummary] = Field(min_length=1)
    not_ready_stories: list[UserStoryNotReadySummary] = Field(min_length=1)
    open_questions: list[UserStoryOpenQuestion] = Field(min_length=1)
    stage_gate: list[StageGateCheck] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_story_cards_consistency(self) -> "UserStoriesArtifactData":
        requirement_ids = _unique_ids(
            [item.requirement_id for item in self.requirements],
            "requirements",
            "requirement_id",
        )
        story_ids = _unique_ids(
            [item.story_id for item in self.story_cards],
            "story_cards",
            "story_id",
        )
        story_by_id = {item.story_id: item for item in self.story_cards}
        _validate_known_ids(
            {
                requirement_id
                for item in self.story_cards
                for requirement_id in item.requirement_ids
            },
            requirement_ids,
            "story_cards references unknown requirement ids",
        )

        for story in self.story_cards:
            if story.status == "ready":
                if not story.acceptance_criteria:
                    raise ValueError(
                        f"ready story {story.story_id} must include acceptance criteria"
                    )
                if not story.business_rules:
                    raise ValueError(
                        f"ready story {story.story_id} must include business rules or N/A"
                    )
                if not story.out_of_scope:
                    raise ValueError(
                        f"ready story {story.story_id} must include out of scope"
                    )
                if not story.dependencies:
                    raise ValueError(
                        f"ready story {story.story_id} must include dependencies"
                    )
            else:
                if not story.blocker_reason:
                    raise ValueError(
                        f"not_ready story {story.story_id} must include blocker reason"
                    )
                if not story.open_questions:
                    raise ValueError(
                        f"not_ready story {story.story_id} must include questions"
                    )

        ready_summary_ids = _unique_ids(
            [item.story_id for item in self.ready_story_summaries],
            "ready_story_summaries",
            "story_id",
        )
        _validate_known_ids(
            ready_summary_ids,
            story_ids,
            "ready_story_summaries references unknown story ids",
        )
        not_ready_summary_ids = _unique_ids(
            [item.story_id for item in self.not_ready_stories],
            "not_ready_stories",
            "story_id",
        )
        _validate_known_ids(
            not_ready_summary_ids,
            story_ids,
            "not_ready_stories references unknown story ids",
        )
        for story_id in ready_summary_ids:
            if story_by_id[story_id].status != "ready":
                raise ValueError(
                    "ready_story_summaries can only reference ready stories: "
                    + story_id
                )
        for item in self.ready_story_summaries:
            if item.acceptance_criteria_count != len(
                story_by_id[item.story_id].acceptance_criteria
            ):
                raise ValueError(
                    "ready_story_summaries acceptance_criteria_count mismatch: "
                    + item.story_id
                )
        for story_id in not_ready_summary_ids:
            if story_by_id[story_id].status != "not_ready":
                raise ValueError(
                    "not_ready_stories can only reference not_ready stories: "
                    + story_id
                )
        _validate_known_ids(
            {item.story_id for item in self.open_questions},
            story_ids,
            "open_questions references unknown story ids",
        )
        _unique_ids(
            [item.question_id for item in self.open_questions],
            "open_questions",
            "question_id",
        )
        return self


class UserStoryReadyOverview(StrictArtifactDataModel):
    story_id: str
    title: str
    requirement_ids: list[str] = Field(min_length=1)
    user_value: str
    ready_reason: str
    status: Literal["ready"]


class UserStoryPacket(StrictArtifactDataModel):
    story_id: str
    requirement_ids: list[str] = Field(min_length=1)
    user_story: str
    acceptance_criteria: list[str] = Field(min_length=1)
    business_rules: list[str] = Field(min_length=1)
    non_functional_notes: list[str] = Field(min_length=1)
    out_of_scope: list[str] = Field(min_length=1)
    dependencies: list[str] = Field(min_length=1)
    open_questions: list[str] = Field(min_length=1)


class UserStoryUpstreamTrace(StrictArtifactDataModel):
    story_id: str
    source_workflow: str
    source_stage: str
    source_requirements: list[str] = Field(min_length=1)
    source_slice: str
    trace_note: str


class UserStoryNotReadyBlocker(StrictArtifactDataModel):
    story_id: str
    requirement_ids: list[str] = Field(min_length=1)
    blocker_reason: str
    questions: list[str] = Field(min_length=1)
    suggested_next_step: str


class AiCodingInputBoundary(StrictArtifactDataModel):
    allowed: list[str] = Field(min_length=1)
    forbidden: list[str] = Field(min_length=1)


class UserStoryHandoffArtifactData(StrictArtifactDataModel):
    document_info: DocumentInfo
    requirements: list[UserStoryRequirementRef] = Field(min_length=1)
    ready_story_overview: list[UserStoryReadyOverview] = Field(min_length=1)
    single_story_packets: list[UserStoryPacket] = Field(min_length=1)
    upstream_traceability: list[UserStoryUpstreamTrace] = Field(min_length=1)
    not_ready_blockers: list[UserStoryNotReadyBlocker] = Field(min_length=1)
    ai_coding_input_boundary: AiCodingInputBoundary
    stage_gate: list[StageGateCheck] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_handoff_consistency(self) -> "UserStoryHandoffArtifactData":
        requirement_ids = _unique_ids(
            [item.requirement_id for item in self.requirements],
            "requirements",
            "requirement_id",
        )
        ready_story_ids = _unique_ids(
            [item.story_id for item in self.ready_story_overview],
            "ready_story_overview",
            "story_id",
        )
        packet_story_ids = _unique_ids(
            [item.story_id for item in self.single_story_packets],
            "single_story_packets",
            "story_id",
        )
        _validate_known_ids(
            packet_story_ids,
            ready_story_ids,
            "single_story_packets references non-ready story ids",
        )
        _validate_known_ids(
            {
                requirement_id
                for item in self.ready_story_overview
                for requirement_id in item.requirement_ids
            },
            requirement_ids,
            "ready_story_overview references unknown requirement ids",
        )
        _validate_known_ids(
            {
                requirement_id
                for item in self.single_story_packets
                for requirement_id in item.requirement_ids
            },
            requirement_ids,
            "single_story_packets references unknown requirement ids",
        )
        _validate_known_ids(
            {item.story_id for item in self.upstream_traceability},
            ready_story_ids,
            "upstream_traceability references unknown ready story ids",
        )
        _validate_known_ids(
            {
                requirement_id
                for item in self.upstream_traceability
                for requirement_id in item.source_requirements
            },
            requirement_ids,
            "upstream_traceability references unknown requirement ids",
        )
        _validate_known_ids(
            {
                requirement_id
                for item in self.not_ready_blockers
                for requirement_id in item.requirement_ids
            },
            requirement_ids,
            "not_ready_blockers references unknown requirement ids",
        )
        return self


def _unique_ids(values: list[str], collection: str, field_name: str) -> set[str]:
    unique = set(values)
    if len(unique) != len(values):
        raise ValueError(f"{collection} contains duplicate {field_name}")
    return unique


def _validate_known_ids(
    referenced_ids: set[str],
    known_ids: set[str],
    message: str,
) -> None:
    unknown_ids = sorted(referenced_ids - known_ids)
    if unknown_ids:
        raise ValueError(f"{message}: " + ", ".join(unknown_ids))


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
    elif (workflow_id, current_stage_id) == ("IDEA_BRAINSTORM", "DEFINE"):
        artifact_data = IdeaDefineArtifactData.model_validate(payload["artifact_data"])
        markdown = render_idea_brainstorm_define_markdown(artifact_data)
    elif (workflow_id, current_stage_id) == ("IDEA_BRAINSTORM", "DIVERGE"):
        artifact_data = IdeaDivergeArtifactData.model_validate(payload["artifact_data"])
        markdown = render_idea_brainstorm_diverge_markdown(artifact_data)
    elif (workflow_id, current_stage_id) == ("IDEA_BRAINSTORM", "CONVERGE"):
        artifact_data = IdeaConvergeArtifactData.model_validate(
            payload["artifact_data"]
        )
        markdown = render_idea_brainstorm_converge_markdown(artifact_data)
    elif (workflow_id, current_stage_id) == ("IDEA_BRAINSTORM", "CONCEPT"):
        artifact_data = IdeaConceptArtifactData.model_validate(payload["artifact_data"])
        markdown = render_idea_brainstorm_concept_markdown(artifact_data)
    elif (workflow_id, current_stage_id) == ("INCIDENT_REVIEW", "TIMELINE"):
        artifact_data = IncidentTimelineArtifactData.model_validate(
            payload["artifact_data"]
        )
        markdown = render_incident_review_timeline_markdown(artifact_data)
    elif (workflow_id, current_stage_id) == ("INCIDENT_REVIEW", "ROOT_CAUSE"):
        artifact_data = IncidentRootCauseArtifactData.model_validate(
            payload["artifact_data"]
        )
        markdown = render_incident_review_root_cause_markdown(artifact_data)
    elif (workflow_id, current_stage_id) == ("INCIDENT_REVIEW", "IMPROVEMENT"):
        artifact_data = IncidentImprovementArtifactData.model_validate(
            payload["artifact_data"]
        )
        markdown = render_incident_review_improvement_markdown(artifact_data)
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
    elif (workflow_id, current_stage_id) == ("VALUE_DISCOVERY", "JOURNEY"):
        artifact_data = ValueDiscoveryJourneyArtifactData.model_validate(
            payload["artifact_data"]
        )
        markdown = render_value_discovery_journey_markdown(artifact_data)
    elif (workflow_id, current_stage_id) == ("VALUE_DISCOVERY", "BLUEPRINT"):
        artifact_data = ValueDiscoveryBlueprintArtifactData.model_validate(
            payload["artifact_data"]
        )
        markdown = render_value_discovery_blueprint_markdown(artifact_data)
    elif (workflow_id, current_stage_id) == ("USER_STORY_BREAKDOWN", "SCOPE"):
        artifact_data = UserStoryScopeArtifactData.model_validate(
            payload["artifact_data"]
        )
        markdown = render_user_story_scope_markdown(artifact_data)
    elif (workflow_id, current_stage_id) == ("USER_STORY_BREAKDOWN", "STORY_MAP"):
        artifact_data = UserStoryMapArtifactData.model_validate(
            payload["artifact_data"]
        )
        markdown = render_user_story_map_markdown(artifact_data)
    elif (workflow_id, current_stage_id) == ("USER_STORY_BREAKDOWN", "STORIES"):
        artifact_data = UserStoriesArtifactData.model_validate(
            payload["artifact_data"]
        )
        markdown = render_user_stories_markdown(artifact_data)
    elif (workflow_id, current_stage_id) == ("USER_STORY_BREAKDOWN", "HANDOFF"):
        artifact_data = UserStoryHandoffArtifactData.model_validate(
            payload["artifact_data"]
        )
        markdown = render_user_story_handoff_markdown(artifact_data)
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
            "artifact_data": artifact_data.model_dump(mode="json", exclude_none=True),
            "stage_action": payload.get("stage_action"),
            "warnings": payload.get("warnings", []),
        }
    )


def render_partial_agent_turn_from_artifact_data(
    payload: dict[str, Any],
    *,
    workflow_id: str,
    current_stage_id: str,
) -> AgentTurnOutput | None:
    if "artifact_data" not in payload:
        return None
    if (workflow_id, current_stage_id) == ("TEST_DESIGN", "CLARIFY"):
        field_order = [
            "requirement_facts",
            "system_boundaries",
            "business_rules",
            "flow_links",
            "clarification_questions",
            "quality_requirements",
            "downstream_inputs",
            "stage_gate",
        ]
        renderer = render_partial_test_design_clarify_markdown
        markdown = render_partial_test_design_clarify_markdown(
            payload["artifact_data"]
        )
    elif (workflow_id, current_stage_id) == ("TEST_DESIGN", "STRATEGY"):
        field_order = [
            "strategy_summary",
            "quality_goals",
            "risks",
            "test_techniques",
            "test_layers",
            "test_points",
            "tradeoffs",
            "stage_gate",
        ]
        renderer = render_partial_test_design_strategy_markdown
        markdown = render_partial_test_design_strategy_markdown(payload["artifact_data"])
    elif (workflow_id, current_stage_id) == ("TEST_DESIGN", "CASES"):
        field_order = [
            "case_statistics",
            "design_bases",
            "case_groups",
            "test_data_environments",
            "automation_candidates",
            "coverage_trace",
            "open_questions",
            "stage_gate",
        ]
        renderer = render_partial_test_design_cases_markdown
        markdown = render_partial_test_design_cases_markdown(payload["artifact_data"])
    elif (workflow_id, current_stage_id) == ("TEST_DESIGN", "DELIVERY"):
        field_order = [
            "executive_summary",
            "requirement_summary",
            "strategy_summary_items",
            "case_summary_items",
            "coverage_map",
            "open_risks",
            "acceptance_checklist",
            "signoffs",
            "change_log",
        ]
        renderer = render_partial_test_design_delivery_markdown
        markdown = render_partial_test_design_delivery_markdown(
            payload["artifact_data"]
        )
    elif (workflow_id, current_stage_id) == ("REQ_REVIEW", "REVIEW"):
        field_order = [
            "scope_items",
            "quality_overview",
            "issue_statistics",
            "issue_groups",
            "revision_suggestions",
            "stage_gate",
        ]
        renderer = render_partial_req_review_review_markdown
        markdown = render_partial_req_review_review_markdown(payload["artifact_data"])
    elif (workflow_id, current_stage_id) == ("REQ_REVIEW", "REPORT"):
        field_order = [
            "conclusion",
            "review_info",
            "issue_statistics",
            "issue_closures",
            "review_conditions",
            "signoffs",
            "change_log",
        ]
        renderer = render_partial_req_review_report_markdown
        markdown = render_partial_req_review_report_markdown(payload["artifact_data"])
    elif (workflow_id, current_stage_id) == ("INCIDENT_REVIEW", "TIMELINE"):
        field_order = [
            "incident_summary",
            "impact_metrics",
            "fact_sources",
            "timeline_events",
            "fact_separation",
            "fact_summary",
            "participants",
            "missing_information",
            "stage_gate",
        ]
        renderer = render_partial_incident_review_timeline_markdown
        markdown = render_partial_incident_review_timeline_markdown(
            payload["artifact_data"]
        )
    elif (workflow_id, current_stage_id) == ("INCIDENT_REVIEW", "ROOT_CAUSE"):
        field_order = [
            "analysis_context",
            "why_chain",
            "cause_evidence",
            "fishbone_categories",
            "root_cause_conclusions",
            "excluded_causes",
            "unverified_causes",
            "stage_gate",
        ]
        renderer = render_partial_incident_review_root_cause_markdown
        markdown = render_partial_incident_review_root_cause_markdown(
            payload["artifact_data"]
        )
    elif (workflow_id, current_stage_id) == ("INCIDENT_REVIEW", "IMPROVEMENT"):
        field_order = [
            "report_info",
            "timeline_summary",
            "root_cause_summary",
            "priority_distribution",
            "improvement_actions",
            "root_cause_coverage",
            "prevention_checklist",
            "review_plan",
            "residual_risks",
            "lessons_learned",
            "organizational_learning",
            "signoffs",
            "stage_gate",
        ]
        renderer = render_partial_incident_review_improvement_markdown
        markdown = render_partial_incident_review_improvement_markdown(
            payload["artifact_data"]
        )
    elif (workflow_id, current_stage_id) == ("IDEA_BRAINSTORM", "DEFINE"):
        field_order = [
            "problem_statement",
            "target_users",
            "problem_landscape",
            "evidence_items",
            "problem_user_fit",
            "constraints_boundaries",
            "reverse_validation",
            "stage_gate",
        ]
        renderer = render_partial_idea_brainstorm_define_markdown
        markdown = render_partial_idea_brainstorm_define_markdown(
            payload["artifact_data"]
        )
    elif (workflow_id, current_stage_id) == ("IDEA_BRAINSTORM", "DIVERGE"):
        field_order = [
            "divergence_method",
            "idea_landscape",
            "idea_cards",
            "idea_sources",
            "parked_or_excluded",
            "stage_gate",
        ]
        renderer = render_partial_idea_brainstorm_diverge_markdown
        markdown = render_partial_idea_brainstorm_diverge_markdown(
            payload["artifact_data"]
        )
    elif (workflow_id, current_stage_id) == ("IDEA_BRAINSTORM", "CONVERGE"):
        field_order = [
            "decision_matrix",
            "ice_evaluations",
            "resource_constraints",
            "sensitivity_analysis",
            "validation_experiments",
            "merge_paths",
            "stage_gate",
        ]
        renderer = render_partial_idea_brainstorm_converge_markdown
        markdown = render_partial_idea_brainstorm_converge_markdown(
            payload["artifact_data"]
        )
    elif (workflow_id, current_stage_id) == ("IDEA_BRAINSTORM", "CONCEPT"):
        field_order = [
            "positioning_statement",
            "core_assumptions",
            "lean_canvas",
            "mvp_features",
            "growth_funnel",
            "premortem_risks",
            "validation_roadmap",
            "out_of_scope",
            "decision_records",
            "next_actions",
            "stage_gate",
        ]
        renderer = render_partial_idea_brainstorm_concept_markdown
        markdown = render_partial_idea_brainstorm_concept_markdown(
            payload["artifact_data"]
        )
    elif (workflow_id, current_stage_id) == ("VALUE_DISCOVERY", "ELEVATOR"):
        field_order = [
            "document_info",
            "positioning_summary",
            "value_flow",
            "target_scenarios",
            "pain_evidence",
            "differentiators",
            "business_feasibility",
            "score_matrix",
            "score_summary",
            "assumptions",
            "elevator_pitch",
            "stage_gate",
        ]
        renderer = render_partial_value_discovery_elevator_markdown
        markdown = render_partial_value_discovery_elevator_markdown(
            payload["artifact_data"]
        )
    elif (workflow_id, current_stage_id) == ("VALUE_DISCOVERY", "PERSONA"):
        field_order = [
            "document_info",
            "persona_summary",
            "personas",
            "behavior_scenarios",
            "decision_chain",
            "pain_evidence",
            "anti_personas",
            "priority_ranking",
            "stage_gate",
        ]
        renderer = render_partial_value_discovery_persona_markdown
        markdown = render_partial_value_discovery_persona_markdown(
            payload["artifact_data"]
        )
    elif (workflow_id, current_stage_id) == ("VALUE_DISCOVERY", "JOURNEY"):
        field_order = [
            "document_info",
            "journey_summary",
            "journey_stages",
            "pain_priorities",
            "opportunity_scores",
            "entry_strategy",
            "validation_experiments",
            "stage_gate",
        ]
        renderer = render_partial_value_discovery_journey_markdown
        markdown = render_partial_value_discovery_journey_markdown(
            payload["artifact_data"]
        )
    elif (workflow_id, current_stage_id) == ("VALUE_DISCOVERY", "BLUEPRINT"):
        field_order = [
            "document_info",
            "product_overview",
            "target_users",
            "feature_modules",
            "requirements",
            "main_flow",
            "success_metrics",
            "mvp_plan",
            "non_functional_requirements",
            "acceptance_criteria",
            "roadmap",
            "risks",
            "lisa_handoff_inputs",
            "stage_gate",
        ]
        renderer = render_partial_value_discovery_blueprint_markdown
        markdown = render_partial_value_discovery_blueprint_markdown(
            payload["artifact_data"]
        )
    elif (workflow_id, current_stage_id) == ("USER_STORY_BREAKDOWN", "SCOPE"):
        field_order = [
            "document_info",
            "in_scope_requirements",
            "traceability_index",
            "out_of_scope_items",
            "blocking_questions",
            "stage_gate",
        ]
        renderer = render_partial_user_story_scope_markdown
        markdown = render_partial_user_story_scope_markdown(payload["artifact_data"])
    elif (workflow_id, current_stage_id) == ("USER_STORY_BREAKDOWN", "STORY_MAP"):
        field_order = [
            "document_info",
            "requirements",
            "activities",
            "tasks",
            "story_map_items",
            "mvp_slices",
            "release_slices",
            "stage_gate",
        ]
        renderer = render_partial_user_story_map_markdown
        markdown = render_partial_user_story_map_markdown(payload["artifact_data"])
    elif (workflow_id, current_stage_id) == ("USER_STORY_BREAKDOWN", "STORIES"):
        field_order = [
            "document_info",
            "requirements",
            "split_principles",
            "story_cards",
            "ready_story_summaries",
            "not_ready_stories",
            "open_questions",
            "stage_gate",
        ]
        renderer = render_partial_user_stories_markdown
        markdown = render_partial_user_stories_markdown(payload["artifact_data"])
    elif (workflow_id, current_stage_id) == ("USER_STORY_BREAKDOWN", "HANDOFF"):
        field_order = [
            "document_info",
            "requirements",
            "ready_story_overview",
            "single_story_packets",
            "upstream_traceability",
            "not_ready_blockers",
            "ai_coding_input_boundary",
            "stage_gate",
        ]
        renderer = render_partial_user_story_handoff_markdown
        markdown = render_partial_user_story_handoff_markdown(payload["artifact_data"])
    else:
        return None
    if markdown is None:
        return None
    artifact_patch = _build_partial_add_after_patch(
        payload["artifact_data"],
        markdown,
        field_order=field_order,
        renderer=renderer,
    )
    return AgentTurnOutput.model_validate(
        {
            "chat": payload.get("chat") or "正在生成右侧产出物。",
            "artifact_update": {
                "type": "replace",
                "markdown": markdown,
            },
            "artifact_patch": artifact_patch,
            "stage_action": payload.get("stage_action"),
            "warnings": payload.get("warnings", []),
        }
    )


def _validate_partial_list(value: Any, model_type: type[StrictArtifactDataModel]):
    if not isinstance(value, list) or len(value) == 0:
        raise ValueError("partial artifact list must be non-empty")
    return [model_type.model_validate(item) for item in value]


def _validate_partial_string_list(value: Any) -> list[str]:
    if not isinstance(value, list) or len(value) == 0:
        raise ValueError("partial artifact string list must be non-empty")
    if not all(isinstance(item, str) and item.strip() for item in value):
        raise ValueError("partial artifact string list must contain non-empty strings")
    return value


def _join_partial_sections(sections: list[str]) -> str | None:
    return "\n\n".join(sections) if len(sections) > 1 else None


_ARTIFACT_HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


def _extract_artifact_sections(markdown: str) -> list[dict[str, Any]]:
    lines = markdown.replace("\r\n", "\n").split("\n")
    raw_sections: list[dict[str, Any]] = []
    in_fence = False
    current_start = -1
    current_level = 0
    current_heading = ""
    current_title = ""

    for index, line in enumerate(lines):
        if re.match(r"^\s*```", line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = _ARTIFACT_HEADING_PATTERN.match(line)
        if not match:
            continue
        if current_start >= 0:
            raw_sections.append({
                "level": current_level,
                "heading": current_heading,
                "title": current_title,
                "content": "\n".join(lines[current_start:index]).strip(),
            })
        current_start = index
        current_level = len(match.group(1))
        current_heading = line.strip()
        current_title = match.group(2).strip()

    if current_start >= 0:
        raw_sections.append({
            "level": current_level,
            "heading": current_heading,
            "title": current_title,
            "content": "\n".join(lines[current_start:]).strip(),
        })

    duplicate_counts: dict[str, int] = {}
    for section in raw_sections:
        title = section["title"]
        duplicate_counts[title] = duplicate_counts.get(title, 0) + 1

    occurrence_counts: dict[str, int] = {}
    sections: list[dict[str, Any]] = []
    for section in raw_sections:
        title = section["title"]
        occurrence = occurrence_counts.get(title, 0) + 1
        occurrence_counts[title] = occurrence
        sections.append({
            **section,
            "anchor": f"h{section['level']}:{title}:{occurrence}",
        })
    return sections


def _build_partial_add_after_patch(
    data: Any,
    markdown: str,
    *,
    field_order: list[str],
    renderer: Any,
) -> dict[str, str] | None:
    if not isinstance(data, dict):
        return None
    completed_fields = [field for field in field_order if field in data]
    if len(completed_fields) < 2:
        return None

    previous_data = dict(data)
    previous_data.pop(completed_fields[-1], None)
    previous_markdown = renderer(previous_data)
    if not previous_markdown:
        return None
    if not markdown.startswith(f"{previous_markdown}\n\n"):
        return None

    previous_sections = _extract_artifact_sections(previous_markdown)
    current_sections = _extract_artifact_sections(markdown)
    if (
        not previous_sections
        or len(current_sections) != len(previous_sections) + 1
    ):
        return None

    added_section = current_sections[-1]
    replacement_markdown = markdown[len(previous_markdown) + 2 :].strip()
    if replacement_markdown != added_section["content"]:
        return None

    return {
        "operation": "add_after",
        "sectionAnchor": added_section["anchor"],
        "afterSectionAnchor": previous_sections[-1]["anchor"],
        "replacementMarkdown": replacement_markdown,
        "baseContent": previous_markdown,
    }


def render_partial_test_design_cases_markdown(data: Any) -> str | None:
    if not isinstance(data, dict) or "document_info" not in data:
        return None
    try:
        DocumentInfo.model_validate(data["document_info"])
    except (TypeError, ValueError, ValidationError):
        return None

    sections = ["# 测试用例集"]
    try:
        if "case_statistics" not in data:
            return None
        sections.append(
            _render_case_statistics(
                CaseStatistics.model_validate(data["case_statistics"])
            )
        )

        if "design_bases" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_design_bases(
                _validate_partial_list(data["design_bases"], DesignBasis)
            )
        )

        if "case_groups" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_case_groups(_validate_partial_list(data["case_groups"], CaseGroup))
        )

        if "test_data_environments" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_test_data_environments(
                _validate_partial_list(
                    data["test_data_environments"],
                    TestDataEnvironment,
                )
            )
        )

        if "automation_candidates" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_automation_candidates(
                _validate_partial_list(
                    data["automation_candidates"],
                    AutomationCandidate,
                )
            )
        )

        if "coverage_trace" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_coverage_trace(
                _validate_partial_list(data["coverage_trace"], CoverageTraceItem)
            )
        )

        if "open_questions" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_open_questions(
                _validate_partial_list(data["open_questions"], OpenQuestion)
            )
        )

        if "stage_gate" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_stage_gate(
                _validate_partial_list(data["stage_gate"], StageGateCheck)
            )
        )
    except (TypeError, ValueError, ValidationError):
        return _join_partial_sections(sections)

    return _join_partial_sections(sections)


def render_partial_test_design_delivery_markdown(data: Any) -> str | None:
    if not isinstance(data, dict) or "document_info" not in data:
        return None
    try:
        document_info = DocumentInfo.model_validate(data["document_info"])
    except (TypeError, ValueError, ValidationError):
        return None

    sections = ["# 测试设计文档"]
    try:
        if "executive_summary" not in data:
            return None
        sections.append(
            _render_delivery_executive_summary(
                _validate_partial_list(
                    data["executive_summary"],
                    DeliveryExecutiveSummaryItem,
                )
            )
        )

        if "requirement_summary" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_delivery_requirement_summary(
                _validate_partial_list(
                    data["requirement_summary"],
                    DeliveryRequirementSummaryItem,
                )
            )
        )

        if "strategy_summary_items" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_delivery_strategy_summary(
                _validate_partial_list(
                    data["strategy_summary_items"],
                    DeliveryStrategySummaryItem,
                )
            )
        )

        if "case_summary_items" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_delivery_case_summary(
                _validate_partial_list(
                    data["case_summary_items"],
                    DeliveryCaseSummaryItem,
                )
            )
        )

        if "coverage_map" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_delivery_coverage_map(
                _validate_partial_list(
                    data["coverage_map"],
                    DeliveryCoverageMapItem,
                )
            )
        )

        if "open_risks" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_delivery_open_risks(
                _validate_partial_list(data["open_risks"], DeliveryOpenRisk)
            )
        )

        if "acceptance_checklist" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_delivery_acceptance_checklist(
                _validate_partial_list(data["acceptance_checklist"], StageGateCheck)
            )
        )

        if "signoffs" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_delivery_signoffs(
                _validate_partial_list(data["signoffs"], DeliverySignoff)
            )
        )

        if "change_log" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_delivery_change_log(
                _validate_partial_list(data["change_log"], DeliveryChangeLogItem)
            )
        )

        if "delivery_metrics" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_delivery_document_info(
                document_info,
                DeliveryMetrics.model_validate(data["delivery_metrics"]),
            )
        )
    except (TypeError, ValueError, ValidationError):
        return _join_partial_sections(sections)

    return _join_partial_sections(sections)


def render_partial_req_review_review_markdown(data: Any) -> str | None:
    if not isinstance(data, dict) or "review_info" not in data:
        return None
    try:
        review_info = ReqReviewInfo.model_validate(data["review_info"])
    except (TypeError, ValueError, ValidationError):
        return None

    sections = ["# 需求评审问题清单"]
    try:
        if "scope_items" not in data:
            return None
        sections.append(
            _render_req_review_scope(
                _validate_partial_list(data["scope_items"], ReqReviewScopeItem)
            )
        )

        if "quality_overview" not in data:
            return _join_partial_sections(sections)
        quality_overview = _validate_partial_list(
            data["quality_overview"],
            ReqReviewQualityOverviewItem,
        )
        sections.append(_render_req_review_quality_overview(quality_overview))
        sections.append(_render_req_review_quality_flowchart())

        if "issue_statistics" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_req_review_issue_statistics(
                ReqReviewIssueStatistics.model_validate(data["issue_statistics"]),
                quality_overview,
            )
        )

        if "issue_groups" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_req_review_issue_groups(
                _validate_partial_list(data["issue_groups"], ReqReviewIssueGroup)
            )
        )

        if "revision_suggestions" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_req_review_revision_suggestions(
                _validate_partial_list(
                    data["revision_suggestions"],
                    ReqReviewRevisionSuggestion,
                )
            )
        )

        if "stage_gate" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_req_review_stage_gate(
                _validate_partial_list(data["stage_gate"], StageGateCheck)
            )
        )
        sections.append(_render_req_review_info(review_info))
    except (TypeError, ValueError, ValidationError):
        return _join_partial_sections(sections)

    return _join_partial_sections(sections)


def render_partial_req_review_report_markdown(data: Any) -> str | None:
    if not isinstance(data, dict):
        return None

    sections = ["# 需求评审报告"]
    try:
        if "conclusion" not in data:
            return None
        sections.append(
            _render_req_review_report_conclusion(
                ReqReviewReportConclusion.model_validate(data["conclusion"])
            )
        )

        if "review_info" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_req_review_report_info(
                ReqReviewReportInfo.model_validate(data["review_info"])
            )
        )

        if "issue_statistics" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_req_review_report_statistics(
                ReqReviewReportIssueStatistics.model_validate(
                    data["issue_statistics"]
                )
            )
        )

        if "issue_closures" not in data:
            return _join_partial_sections(sections)
        issue_closures = _validate_partial_list(
            data["issue_closures"],
            ReqReviewReportIssueClosure,
        )
        sections.append(_render_req_review_report_priority_board(issue_closures))
        sections.append(_render_req_review_report_issue_closures(issue_closures))

        if "review_conditions" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_req_review_report_conditions(
                _validate_partial_list(
                    data["review_conditions"],
                    ReqReviewReportCondition,
                )
            )
        )

        if "signoffs" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_req_review_report_signoffs(
                _validate_partial_list(data["signoffs"], ReqReviewReportSignoff)
            )
        )

        if "change_log" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_req_review_report_change_log(
                _validate_partial_list(
                    data["change_log"],
                    ReqReviewReportChangeLogItem,
                )
            )
        )
    except (TypeError, ValueError, ValidationError):
        return _join_partial_sections(sections)

    return _join_partial_sections(sections)


def render_partial_incident_review_timeline_markdown(data: Any) -> str | None:
    if not isinstance(data, dict) or "incident_summary" not in data:
        return None
    try:
        incident_summary = IncidentSummary.model_validate(data["incident_summary"])
    except (TypeError, ValueError, ValidationError):
        return None

    sections = ["# 故障复盘报告"]
    try:
        sections.append(_render_incident_summary(incident_summary))

        if "impact_metrics" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_incident_impact_metrics(
                _validate_partial_list(
                    data["impact_metrics"],
                    IncidentImpactMetric,
                )
            )
        )

        if "fact_sources" not in data:
            return _join_partial_sections(sections)
        _validate_partial_list(data["fact_sources"], IncidentFactSource)
        sections.append(
            _render_incident_fact_sources(
                _validate_partial_list(data["fact_sources"], IncidentFactSource)
            )
        )

        if "timeline_events" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_incident_timeline(
                incident_summary,
                _validate_partial_list(
                    data["timeline_events"],
                    IncidentTimelineEvent,
                ),
            )
        )

        if "fact_separation" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_incident_fact_separation(
                _validate_partial_list(
                    data["fact_separation"],
                    IncidentFactSeparationItem,
                )
            )
        )

        if "fact_summary" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_incident_fact_summary(
                _validate_partial_string_list(data["fact_summary"])
            )
        )

        if "participants" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_incident_participants(
                _validate_partial_list(data["participants"], IncidentParticipant)
            )
        )

        if "missing_information" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_incident_missing_information(
                _validate_partial_list(
                    data["missing_information"],
                    IncidentMissingInformation,
                )
            )
        )

        if "stage_gate" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_incident_stage_gate(
                _validate_partial_list(data["stage_gate"], StageGateCheck)
            )
        )
    except (TypeError, ValueError, ValidationError):
        return _join_partial_sections(sections)

    return _join_partial_sections(sections)


def render_partial_incident_review_root_cause_markdown(data: Any) -> str | None:
    if not isinstance(data, dict) or "analysis_context" not in data:
        return None
    try:
        analysis_context = IncidentRootCauseContext.model_validate(
            data["analysis_context"]
        )
    except (TypeError, ValueError, ValidationError):
        return None

    sections = ["# 故障复盘报告"]
    try:
        sections.append(_render_incident_root_cause_context(analysis_context))

        if "why_chain" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_incident_why_chain(
                _validate_partial_list(data["why_chain"], IncidentWhyChainItem)
            )
        )

        if "cause_evidence" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_incident_cause_evidence(
                _validate_partial_list(data["cause_evidence"], IncidentCauseEvidence)
            )
        )

        if "fishbone_categories" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_incident_fishbone(
                analysis_context,
                _validate_partial_list(
                    data["fishbone_categories"],
                    IncidentFishboneCategory,
                ),
            )
        )

        if "root_cause_conclusions" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_incident_root_cause_conclusions(
                _validate_partial_list(
                    data["root_cause_conclusions"],
                    IncidentRootCauseConclusion,
                )
            )
        )

        if "excluded_causes" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_incident_excluded_causes(
                _validate_partial_list(data["excluded_causes"], IncidentExcludedCause)
            )
        )

        if "unverified_causes" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_incident_unverified_causes(
                _validate_partial_list(
                    data["unverified_causes"],
                    IncidentUnverifiedCause,
                )
            )
        )

        if "stage_gate" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_incident_root_cause_stage_gate(
                _validate_partial_list(data["stage_gate"], StageGateCheck)
            )
        )
    except (TypeError, ValueError, ValidationError):
        return _join_partial_sections(sections)

    return _join_partial_sections(sections)


def render_partial_incident_review_improvement_markdown(data: Any) -> str | None:
    if not isinstance(data, dict) or "report_info" not in data:
        return None
    try:
        IncidentImprovementReportInfo.model_validate(data["report_info"])
    except (TypeError, ValueError, ValidationError):
        return None

    sections = ["# 故障复盘报告"]
    try:
        sections.append(
            _render_incident_improvement_report_info(
                IncidentImprovementReportInfo.model_validate(data["report_info"])
            )
        )

        if "timeline_summary" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_incident_improvement_timeline_summary(
                IncidentImprovementTimelineSummary.model_validate(
                    data["timeline_summary"]
                )
            )
        )

        if "root_cause_summary" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_incident_improvement_root_cause_summary(
                IncidentImprovementRootCauseSummary.model_validate(
                    data["root_cause_summary"]
                )
            )
        )

        if (
            "priority_distribution" not in data
            and "improvement_actions" not in data
        ):
            return _join_partial_sections(sections)
        sections.append("## 第三部分：改进措施")
        sections.append("### 7. 改进措施")

        if "priority_distribution" in data:
            sections.append(
                _render_incident_improvement_priority_distribution(
                    IncidentImprovementPriorityDistribution.model_validate(
                        data["priority_distribution"]
                    )
                )
            )

        if "improvement_actions" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_incident_improvement_actions(
                _validate_partial_list(
                    data["improvement_actions"],
                    IncidentImprovementAction,
                )
            )
        )

        if "root_cause_coverage" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_incident_improvement_root_cause_coverage(
                _validate_partial_list(
                    data["root_cause_coverage"],
                    IncidentRootCauseCoverage,
                )
            )
        )

        if "prevention_checklist" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_incident_improvement_prevention_checklist(
                _validate_partial_list(
                    data["prevention_checklist"],
                    IncidentPreventionCheckItem,
                )
            )
        )

        if "review_plan" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_incident_improvement_review_plan(
                _validate_partial_list(data["review_plan"], IncidentReviewPlanItem)
            )
        )

        if "residual_risks" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_incident_improvement_residual_risks(
                _validate_partial_list(data["residual_risks"], IncidentResidualRisk)
            )
        )

        if "lessons_learned" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_incident_improvement_lessons(
                _validate_partial_list(data["lessons_learned"], IncidentLessonLearned)
            )
        )

        if "organizational_learning" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_incident_improvement_organizational_learning(
                _validate_partial_list(
                    data["organizational_learning"],
                    IncidentOrganizationalLearning,
                )
            )
        )

        if "signoffs" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_incident_improvement_signoffs(
                _validate_partial_list(data["signoffs"], IncidentSignoff)
            )
        )

        if "stage_gate" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_incident_improvement_stage_gate(
                _validate_partial_list(data["stage_gate"], StageGateCheck)
            )
        )
    except (TypeError, ValueError, ValidationError):
        return _join_partial_sections(sections)

    return _join_partial_sections(sections)


def render_partial_idea_brainstorm_define_markdown(data: Any) -> str | None:
    if not isinstance(data, dict) or "problem_statement" not in data:
        return None
    try:
        problem_statement = IdeaProblemStatement.model_validate(
            data["problem_statement"]
        )
    except (TypeError, ValueError, ValidationError):
        return None

    sections = ["# 问题域分析"]
    try:
        sections.append(_render_idea_problem_statement(problem_statement))

        if "target_users" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_idea_target_users(
                _validate_partial_list(data["target_users"], IdeaTargetUser)
            )
        )

        if "problem_landscape" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_idea_problem_landscape(
                IdeaProblemLandscape.model_validate(data["problem_landscape"])
            )
        )

        if "evidence_items" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_idea_evidence_items(
                _validate_partial_list(data["evidence_items"], IdeaEvidenceItem)
            )
        )

        if "problem_user_fit" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_idea_problem_user_fit(
                _validate_partial_list(
                    data["problem_user_fit"],
                    IdeaProblemUserFit,
                )
            )
        )

        if "constraints_boundaries" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_idea_constraints_boundaries(
                _validate_partial_list(
                    data["constraints_boundaries"],
                    IdeaConstraintBoundary,
                )
            )
        )

        if "reverse_validation" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_idea_reverse_validation(
                _validate_partial_list(
                    data["reverse_validation"],
                    IdeaReverseValidation,
                )
            )
        )

        if "stage_gate" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_idea_stage_gate(
                _validate_partial_list(data["stage_gate"], StageGateCheck)
            )
        )
    except (TypeError, ValueError, ValidationError):
        return _join_partial_sections(sections)

    return _join_partial_sections(sections)


def render_partial_idea_brainstorm_diverge_markdown(data: Any) -> str | None:
    if not isinstance(data, dict) or "divergence_method" not in data:
        return None
    try:
        divergence_method = IdeaDivergenceMethod.model_validate(
            data["divergence_method"]
        )
    except (TypeError, ValueError, ValidationError):
        return None

    sections = ["# 创意发散"]
    try:
        sections.append(_render_idea_divergence_method(divergence_method))

        if "idea_landscape" not in data or "idea_cards" not in data:
            return _join_partial_sections(sections)
        idea_cards = _validate_partial_list(data["idea_cards"], IdeaCard)
        sections.append(
            _render_idea_diverge_landscape(
                IdeaDivergeLandscape.model_validate(data["idea_landscape"]),
                idea_cards,
            )
        )
        sections.append(_render_idea_cards(idea_cards))

        if "idea_sources" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_idea_sources(
                _validate_partial_list(data["idea_sources"], IdeaSource)
            )
        )

        if "parked_or_excluded" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_idea_parked_or_excluded(
                _validate_partial_list(
                    data["parked_or_excluded"],
                    IdeaParkedOrExcludedRecord,
                )
            )
        )

        if "stage_gate" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_idea_stage_gate(
                _validate_partial_list(data["stage_gate"], StageGateCheck)
            )
        )
    except (TypeError, ValueError, ValidationError, KeyError):
        return _join_partial_sections(sections)

    return _join_partial_sections(sections)


def render_partial_idea_brainstorm_converge_markdown(data: Any) -> str | None:
    if (
        not isinstance(data, dict)
        or "decision_matrix" not in data
        or "ice_evaluations" not in data
    ):
        return None
    try:
        decision_matrix = IdeaDecisionMatrix.model_validate(data["decision_matrix"])
        ice_evaluations = _validate_partial_list(
            data["ice_evaluations"],
            IdeaIceEvaluation,
        )
    except (TypeError, ValueError, ValidationError):
        return None

    sections = ["# 收敛聚焦"]
    try:
        sections.append(
            _render_idea_converge_decision_matrix(
                decision_matrix,
                ice_evaluations,
            )
        )
        sections.append(_render_idea_ice_evaluations(ice_evaluations))

        if "resource_constraints" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_idea_resource_constraints(
                _validate_partial_list(
                    data["resource_constraints"],
                    IdeaResourceConstraint,
                )
            )
        )

        if "sensitivity_analysis" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_idea_sensitivity_analysis(
                _validate_partial_list(
                    data["sensitivity_analysis"],
                    IdeaSensitivityItem,
                )
            )
        )

        if "validation_experiments" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_idea_validation_experiments(
                _validate_partial_list(
                    data["validation_experiments"],
                    IdeaValidationExperiment,
                )
            )
        )

        if "merge_paths" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_idea_merge_paths(
                _validate_partial_list(data["merge_paths"], IdeaMergePath)
            )
        )

        if "stage_gate" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_idea_stage_gate(
                _validate_partial_list(data["stage_gate"], StageGateCheck)
            )
        )
    except (TypeError, ValueError, ValidationError):
        return _join_partial_sections(sections)

    return _join_partial_sections(sections)


def render_partial_idea_brainstorm_concept_markdown(data: Any) -> str | None:
    if not isinstance(data, dict) or "positioning_statement" not in data:
        return None
    try:
        positioning_statement = IdeaPositioningStatement.model_validate(
            data["positioning_statement"]
        )
    except (TypeError, ValueError, ValidationError):
        return None

    sections = ["# 产品概念简报"]
    try:
        sections.append(_render_idea_concept_positioning(positioning_statement))

        if "core_assumptions" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_idea_concept_core_assumptions(
                _validate_partial_list(
                    data["core_assumptions"],
                    IdeaCoreAssumption,
                )
            )
        )

        if "lean_canvas" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_idea_concept_lean_canvas(
                _validate_partial_list(data["lean_canvas"], IdeaLeanCanvasCell)
            )
        )

        if "mvp_features" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_idea_concept_mvp_features(
                _validate_partial_list(data["mvp_features"], IdeaMvpFeature)
            )
        )

        if "growth_funnel" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_idea_concept_growth_funnel(
                _validate_partial_list(
                    data["growth_funnel"],
                    IdeaGrowthFunnelStage,
                )
            )
        )

        if "premortem_risks" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_idea_concept_premortem_risks(
                _validate_partial_list(
                    data["premortem_risks"],
                    IdeaPremortemRisk,
                )
            )
        )

        if "validation_roadmap" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_idea_concept_validation_roadmap(
                _validate_partial_list(
                    data["validation_roadmap"],
                    IdeaValidationRoadmapItem,
                )
            )
        )

        if "out_of_scope" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_idea_concept_out_of_scope(
                _validate_partial_list(data["out_of_scope"], IdeaOutOfScopeItem)
            )
        )

        if "decision_records" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_idea_concept_decision_records(
                _validate_partial_list(
                    data["decision_records"],
                    IdeaDecisionRecord,
                )
            )
        )

        if "next_actions" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_idea_concept_next_actions(
                _validate_partial_list(data["next_actions"], IdeaNextAction)
            )
        )

        if "stage_gate" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_idea_stage_gate(
                _validate_partial_list(data["stage_gate"], StageGateCheck)
            )
        )
    except (TypeError, ValueError, ValidationError):
        return _join_partial_sections(sections)

    return _join_partial_sections(sections)


def render_partial_value_discovery_elevator_markdown(data: Any) -> str | None:
    if not isinstance(data, dict) or "positioning_summary" not in data:
        return None
    try:
        if "document_info" in data:
            DocumentInfo.model_validate(data["document_info"])
        positioning_summary = PositioningSummary.model_validate(
            data["positioning_summary"]
        )
    except (TypeError, ValueError, ValidationError):
        return None

    sections = ["# 价值定位分析"]
    try:
        sections.append(_render_value_positioning_summary(positioning_summary))

        if "value_flow" not in data:
            return _join_partial_sections(sections)
        sections.append(_render_value_flow(ValueFlow.model_validate(data["value_flow"])))

        if "target_scenarios" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_target_scenarios(
                _validate_partial_list(data["target_scenarios"], TargetScenario)
            )
        )

        if "pain_evidence" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_pain_evidence(
                _validate_partial_list(data["pain_evidence"], PainEvidence)
            )
        )

        if "differentiators" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_differentiators(
                _validate_partial_list(data["differentiators"], Differentiator)
            )
        )

        if "business_feasibility" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_business_feasibility(
                _validate_partial_list(
                    data["business_feasibility"],
                    BusinessFeasibility,
                )
            )
        )

        if "score_matrix" not in data or "score_summary" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_value_score_matrix(
                _validate_partial_list(data["score_matrix"], ValueScore),
                ValueScoreSummary.model_validate(data["score_summary"]),
            )
        )

        if "assumptions" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_value_assumptions(
                _validate_partial_list(data["assumptions"], ValueAssumption)
            )
        )

        if "elevator_pitch" not in data:
            return _join_partial_sections(sections)
        if not isinstance(data["elevator_pitch"], str) or not data[
            "elevator_pitch"
        ].strip():
            raise ValueError("elevator_pitch must be a non-empty string")
        sections.append(_render_elevator_pitch(data["elevator_pitch"]))

        if "stage_gate" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_value_stage_gate(
                _validate_partial_list(data["stage_gate"], StageGateCheck)
            )
        )
    except (TypeError, ValueError, ValidationError, KeyError):
        return _join_partial_sections(sections)

    return _join_partial_sections(sections)


def render_partial_value_discovery_persona_markdown(data: Any) -> str | None:
    if not isinstance(data, dict) or "persona_summary" not in data:
        return None
    try:
        if "document_info" in data:
            DocumentInfo.model_validate(data["document_info"])
        persona_summary = PersonaSummary.model_validate(data["persona_summary"])
    except (TypeError, ValueError, ValidationError):
        return None

    sections = ["# 用户画像分析"]
    try:
        sections.append(_render_persona_summary(persona_summary))

        if "personas" not in data:
            return _join_partial_sections(sections)
        personas = _validate_partial_list(data["personas"], PersonaProfile)
        sections.append(_render_persona_profiles(personas))

        if "behavior_scenarios" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_persona_behavior_scenarios(
                _validate_partial_list(
                    data["behavior_scenarios"],
                    PersonaBehaviorScenario,
                ),
                personas,
            )
        )

        if "decision_chain" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_persona_decision_chain(
                _validate_partial_list(data["decision_chain"], PersonaDecisionRole),
                personas,
            )
        )

        if "pain_evidence" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_persona_pain_evidence(
                _validate_partial_list(data["pain_evidence"], PersonaPainEvidence),
                personas,
            )
        )

        if "anti_personas" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_anti_personas(
                _validate_partial_list(data["anti_personas"], AntiPersona)
            )
        )

        if "priority_ranking" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_persona_priority_ranking(
                _validate_partial_list(
                    data["priority_ranking"],
                    PersonaPriorityRanking,
                ),
                personas,
            )
        )

        if "stage_gate" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_value_stage_gate(
                _validate_partial_list(data["stage_gate"], StageGateCheck)
            )
        )
    except (TypeError, ValueError, ValidationError, KeyError):
        return _join_partial_sections(sections)

    return _join_partial_sections(sections)


def render_partial_value_discovery_journey_markdown(data: Any) -> str | None:
    if not isinstance(data, dict) or "journey_stages" not in data:
        return None
    try:
        if "document_info" in data:
            DocumentInfo.model_validate(data["document_info"])
        journey_stages = _validate_partial_list(data["journey_stages"], JourneyStage)
    except (TypeError, ValueError, ValidationError):
        return None

    sections = ["# 用户旅程分析"]
    try:
        sections.append(_render_journey_map(journey_stages))
        sections.append(_render_journey_map_visual(journey_stages))
        sections.append(_render_journey_stage_details(journey_stages))

        if "pain_priorities" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_journey_pain_priorities(
                _validate_partial_list(
                    data["pain_priorities"],
                    JourneyPainPriority,
                ),
                journey_stages,
            )
        )

        if "opportunity_scores" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_journey_opportunity_scores(
                _validate_partial_list(
                    data["opportunity_scores"],
                    JourneyOpportunityScore,
                )
            )
        )

        if "entry_strategy" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_journey_entry_strategy(
                _validate_partial_list(data["entry_strategy"], JourneyEntryStrategy)
            )
        )

        if "validation_experiments" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_journey_validation_experiments(
                _validate_partial_list(
                    data["validation_experiments"],
                    JourneyValidationExperiment,
                )
            )
        )

        if "journey_summary" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_journey_summary(
                JourneySummary.model_validate(data["journey_summary"])
            )
        )

        if "stage_gate" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_value_stage_gate(
                _validate_partial_list(data["stage_gate"], StageGateCheck)
            )
        )
    except (TypeError, ValueError, ValidationError, KeyError):
        return _join_partial_sections(sections)

    return _join_partial_sections(sections)


def render_partial_value_discovery_blueprint_markdown(data: Any) -> str | None:
    if (
        not isinstance(data, dict)
        or "document_info" not in data
        or "product_overview" not in data
    ):
        return None
    try:
        document_info = BlueprintDocumentInfo.model_validate(data["document_info"])
        product_overview = BlueprintProductOverview.model_validate(
            data["product_overview"]
        )
    except (TypeError, ValueError, ValidationError):
        return None

    sections = [f"# {document_info.product_name} 需求蓝图"]
    try:
        sections.append(_render_blueprint_product_overview(product_overview))

        if "target_users" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_blueprint_target_users(
                _validate_partial_list(data["target_users"], BlueprintTargetUser)
            )
        )

        if "feature_modules" not in data or "requirements" not in data:
            return _join_partial_sections(sections)
        feature_modules = _validate_partial_list(
            data["feature_modules"],
            BlueprintFeatureModule,
        )
        requirements = _validate_partial_list(
            data["requirements"],
            BlueprintRequirement,
        )
        sections.append(_render_blueprint_requirements(feature_modules, requirements))

        if "main_flow" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_blueprint_main_flow(
                BlueprintMainFlow.model_validate(data["main_flow"])
            )
        )

        if "success_metrics" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_blueprint_success_metrics(
                _validate_partial_list(
                    data["success_metrics"],
                    BlueprintSuccessMetric,
                )
            )
        )

        if "mvp_plan" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_blueprint_mvp_plan(
                BlueprintMvpPlan.model_validate(data["mvp_plan"])
            )
        )

        if "non_functional_requirements" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_blueprint_non_functional_requirements(
                _validate_partial_list(
                    data["non_functional_requirements"],
                    BlueprintNonFunctionalRequirement,
                )
            )
        )

        if "acceptance_criteria" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_blueprint_acceptance_criteria(
                _validate_partial_list(
                    data["acceptance_criteria"],
                    BlueprintAcceptanceCriterion,
                )
            )
        )

        if "roadmap" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_blueprint_roadmap(
                _validate_partial_list(data["roadmap"], BlueprintRoadmapItem)
            )
        )

        if "risks" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_blueprint_risks(
                _validate_partial_list(data["risks"], BlueprintRisk)
            )
        )

        if "lisa_handoff_inputs" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_blueprint_lisa_handoff_inputs(
                _validate_partial_list(
                    data["lisa_handoff_inputs"],
                    BlueprintLisaHandoffInput,
                )
            )
        )

        if "stage_gate" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_blueprint_stage_gate(
                _validate_partial_list(data["stage_gate"], StageGateCheck)
            )
        )
        sections.append(_render_blueprint_document_info(document_info))
    except (TypeError, ValueError, ValidationError, KeyError):
        return _join_partial_sections(sections)

    return _join_partial_sections(sections)


def render_partial_user_story_scope_markdown(data: Any) -> str | None:
    if not isinstance(data, dict) or "document_info" not in data:
        return None
    try:
        DocumentInfo.model_validate(data["document_info"])
    except (TypeError, ValueError, ValidationError):
        return None
    sections = ["# 用户故事拆解文档"]
    try:
        if "in_scope_requirements" not in data:
            return None
        sections.append(
            _render_user_story_scope_requirements(
                _validate_partial_list(
                    data["in_scope_requirements"],
                    UserStoryScopeRequirement,
                )
            )
        )
        if "traceability_index" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_user_story_traceability_index(
                _validate_partial_list(
                    data["traceability_index"],
                    UserStoryScopeTrace,
                )
            )
        )
        if "out_of_scope_items" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_user_story_out_of_scope(
                _validate_partial_list(
                    data["out_of_scope_items"],
                    UserStoryOutOfScopeItem,
                )
            )
        )
        if "blocking_questions" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_user_story_blocking_questions(
                _validate_partial_list(
                    data["blocking_questions"],
                    UserStoryBlockingQuestion,
                )
            )
        )
        if "stage_gate" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_user_story_stage_gate(
                _validate_partial_list(data["stage_gate"], StageGateCheck),
                heading_number=5,
            )
        )
    except (TypeError, ValueError, ValidationError):
        return _join_partial_sections(sections)
    return _join_partial_sections(sections)


def render_partial_user_story_map_markdown(data: Any) -> str | None:
    if not isinstance(data, dict) or "document_info" not in data:
        return None
    try:
        DocumentInfo.model_validate(data["document_info"])
    except (TypeError, ValueError, ValidationError):
        return None
    sections = ["# 用户故事拆解文档"]
    try:
        if "activities" not in data:
            return None
        activities = _validate_partial_list(data["activities"], UserStoryActivity)
        sections.append(_render_user_story_activities(activities))
        if "tasks" not in data:
            return _join_partial_sections(sections)
        tasks = _validate_partial_list(data["tasks"], UserStoryTask)
        sections.append(_render_user_story_tasks(tasks))
        if "story_map_items" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_user_story_map(
                _validate_partial_list(
                    data["story_map_items"],
                    UserStoryMapItem,
                ),
                activities,
                tasks,
            )
        )
        if "mvp_slices" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_user_story_mvp_slices(
                _validate_partial_list(data["mvp_slices"], UserStoryMvpSlice)
            )
        )
        if "release_slices" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_user_story_release_slices(
                _validate_partial_list(
                    data["release_slices"],
                    UserStoryReleaseSlice,
                )
            )
        )
        if "stage_gate" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_user_story_stage_gate(
                _validate_partial_list(data["stage_gate"], StageGateCheck),
                heading_number=6,
            )
        )
    except (TypeError, ValueError, ValidationError, KeyError):
        return _join_partial_sections(sections)
    return _join_partial_sections(sections)


def render_partial_user_stories_markdown(data: Any) -> str | None:
    if not isinstance(data, dict) or "document_info" not in data:
        return None
    try:
        DocumentInfo.model_validate(data["document_info"])
    except (TypeError, ValueError, ValidationError):
        return None
    sections = ["# 用户故事拆解文档"]
    try:
        if "split_principles" not in data:
            return None
        sections.append(
            _render_user_story_split_principles(
                _validate_partial_list(
                    data["split_principles"],
                    UserStorySplitPrinciple,
                )
            )
        )
        if "story_cards" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_user_story_cards(
                _validate_partial_list(data["story_cards"], UserStoryCard)
            )
        )
        if "ready_story_summaries" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_user_story_ready_summaries(
                _validate_partial_list(
                    data["ready_story_summaries"],
                    UserStoryReadySummary,
                )
            )
        )
        if "not_ready_stories" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_user_story_not_ready(
                _validate_partial_list(
                    data["not_ready_stories"],
                    UserStoryNotReadySummary,
                )
            )
        )
        if "open_questions" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_user_story_open_questions(
                _validate_partial_list(
                    data["open_questions"],
                    UserStoryOpenQuestion,
                )
            )
        )
        if "stage_gate" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_user_story_stage_gate(
                _validate_partial_list(data["stage_gate"], StageGateCheck),
                heading_number=6,
            )
        )
    except (TypeError, ValueError, ValidationError):
        return _join_partial_sections(sections)
    return _join_partial_sections(sections)


def render_partial_user_story_handoff_markdown(data: Any) -> str | None:
    if not isinstance(data, dict) or "document_info" not in data:
        return None
    try:
        DocumentInfo.model_validate(data["document_info"])
    except (TypeError, ValueError, ValidationError):
        return None
    sections = ["# 单故事 Handoff 清单"]
    try:
        if "ready_story_overview" not in data:
            return None
        sections.append(
            _render_user_story_ready_overview(
                _validate_partial_list(
                    data["ready_story_overview"],
                    UserStoryReadyOverview,
                )
            )
        )
        if "single_story_packets" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_user_story_packets(
                _validate_partial_list(
                    data["single_story_packets"],
                    UserStoryPacket,
                )
            )
        )
        if "upstream_traceability" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_user_story_upstream_traceability(
                _validate_partial_list(
                    data["upstream_traceability"],
                    UserStoryUpstreamTrace,
                )
            )
        )
        if "not_ready_blockers" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_user_story_not_ready_blockers(
                _validate_partial_list(
                    data["not_ready_blockers"],
                    UserStoryNotReadyBlocker,
                )
            )
        )
        if "ai_coding_input_boundary" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_user_story_ai_coding_boundary(
                AiCodingInputBoundary.model_validate(
                    data["ai_coding_input_boundary"]
                )
            )
        )
        if "stage_gate" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_user_story_stage_gate(
                _validate_partial_list(data["stage_gate"], StageGateCheck),
                heading_number=6,
            )
        )
    except (TypeError, ValueError, ValidationError):
        return _join_partial_sections(sections)
    return _join_partial_sections(sections)


def render_partial_test_design_clarify_markdown(data: Any) -> str | None:
    if not isinstance(data, dict) or "document_info" not in data:
        return None
    try:
        document_info = DocumentInfo.model_validate(data["document_info"])
    except (TypeError, ValueError, ValidationError):
        return None

    sections = ["# 需求分析文档"]
    try:
        if "requirement_facts" not in data:
            return None
        sections.append(
            _render_requirement_facts(
                _validate_partial_list(data["requirement_facts"], RequirementFact)
            )
        )

        if "system_boundaries" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_system_boundaries(
                _validate_partial_list(data["system_boundaries"], SystemBoundary)
            )
        )

        if "business_rules" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_business_rules(
                _validate_partial_list(data["business_rules"], BusinessRule)
            )
        )

        if "flow_links" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_flow_links(
                _validate_partial_list(data["flow_links"], FlowLink)
            )
        )

        if "clarification_questions" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_clarification_questions(
                _validate_partial_list(
                    data["clarification_questions"],
                    ClarificationQuestion,
                )
            )
        )

        if "quality_requirements" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_quality_requirements(
                _validate_partial_list(
                    data["quality_requirements"],
                    QualityRequirement,
                )
            )
        )

        if "downstream_inputs" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_downstream_inputs(
                _validate_partial_list(data["downstream_inputs"], DownstreamInput)
            )
        )

        if "stage_gate" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_stage_gate(
                _validate_partial_list(data["stage_gate"], StageGateCheck)
            )
        )
        sections.append(_render_document_info(document_info))
    except (TypeError, ValueError, ValidationError):
        return _join_partial_sections(sections)

    return _join_partial_sections(sections)


def render_partial_test_design_strategy_markdown(data: Any) -> str | None:
    if not isinstance(data, dict) or "document_info" not in data:
        return None
    try:
        DocumentInfo.model_validate(data["document_info"])
    except (TypeError, ValueError, ValidationError):
        return None

    sections = ["# 测试策略蓝图"]
    try:
        if "strategy_summary" not in data:
            return None
        sections.append(
            _render_strategy_summary(
                StrategySummary.model_validate(data["strategy_summary"])
            )
        )

        if "quality_goals" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_quality_goals(
                _validate_partial_list(data["quality_goals"], QualityGoal)
            )
        )

        if "risks" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_strategy_risks(
                _validate_partial_list(data["risks"], StrategyRisk)
            )
        )

        if "test_techniques" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_test_techniques(
                _validate_partial_list(data["test_techniques"], TestTechnique)
            )
        )

        if "test_layers" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_test_layers(
                _validate_partial_list(data["test_layers"], TestLayer)
            )
        )

        if "test_points" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_test_points(
                _validate_partial_list(data["test_points"], TestPoint)
            )
        )

        if "tradeoffs" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_tradeoffs(
                _validate_partial_list(data["tradeoffs"], Tradeoff)
            )
        )

        if "stage_gate" not in data:
            return _join_partial_sections(sections)
        sections.append(
            _render_stage_gate(
                _validate_partial_list(data["stage_gate"], StageGateCheck)
            )
        )
    except (TypeError, ValueError, ValidationError):
        return _join_partial_sections(sections)

    return _join_partial_sections(sections)


def render_test_design_clarify_markdown(data: ClarifyArtifactData) -> str:
    sections = [
        "# 需求分析文档",
        _render_requirement_facts(data.requirement_facts),
        _render_system_boundaries(data.system_boundaries),
        _render_business_rules(data.business_rules),
        _render_flow_links(data.flow_links),
        _render_clarification_questions(data.clarification_questions),
        _render_quality_requirements(data.quality_requirements),
        _render_downstream_inputs(data.downstream_inputs),
        _render_stage_gate(data.stage_gate),
        _render_document_info(data.document_info),
    ]
    return "\n\n".join(sections)


def render_idea_brainstorm_define_markdown(data: IdeaDefineArtifactData) -> str:
    sections = [
        "# 问题域分析",
        _render_idea_problem_statement(data.problem_statement),
        _render_idea_target_users(data.target_users),
        _render_idea_problem_landscape(data.problem_landscape),
        _render_idea_evidence_items(data.evidence_items),
        _render_idea_problem_user_fit(data.problem_user_fit),
        _render_idea_constraints_boundaries(data.constraints_boundaries),
        _render_idea_reverse_validation(data.reverse_validation),
        _render_idea_stage_gate(data.stage_gate),
    ]
    return "\n\n".join(sections)


def render_idea_brainstorm_diverge_markdown(data: IdeaDivergeArtifactData) -> str:
    sections = [
        "# 创意发散",
        _render_idea_divergence_method(data.divergence_method),
        _render_idea_diverge_landscape(data.idea_landscape, data.idea_cards),
        _render_idea_cards(data.idea_cards),
        _render_idea_sources(data.idea_sources),
        _render_idea_parked_or_excluded(data.parked_or_excluded),
        _render_idea_stage_gate(data.stage_gate),
    ]
    return "\n\n".join(sections)


def render_idea_brainstorm_converge_markdown(data: IdeaConvergeArtifactData) -> str:
    sections = [
        "# 收敛聚焦",
        _render_idea_converge_decision_matrix(
            data.decision_matrix,
            data.ice_evaluations,
        ),
        _render_idea_ice_evaluations(data.ice_evaluations),
        _render_idea_resource_constraints(data.resource_constraints),
        _render_idea_sensitivity_analysis(data.sensitivity_analysis),
        _render_idea_validation_experiments(data.validation_experiments),
        _render_idea_merge_paths(data.merge_paths),
        _render_idea_stage_gate(data.stage_gate),
    ]
    return "\n\n".join(sections)


def render_idea_brainstorm_concept_markdown(data: IdeaConceptArtifactData) -> str:
    sections = [
        "# 产品概念简报",
        _render_idea_concept_positioning(data.positioning_statement),
        _render_idea_concept_core_assumptions(data.core_assumptions),
        _render_idea_concept_lean_canvas(data.lean_canvas),
        _render_idea_concept_mvp_features(data.mvp_features),
        _render_idea_concept_growth_funnel(data.growth_funnel),
        _render_idea_concept_premortem_risks(data.premortem_risks),
        _render_idea_concept_validation_roadmap(data.validation_roadmap),
        _render_idea_concept_out_of_scope(data.out_of_scope),
        _render_idea_concept_decision_records(data.decision_records),
        _render_idea_concept_next_actions(data.next_actions),
        _render_idea_stage_gate(data.stage_gate),
    ]
    return "\n\n".join(sections)


def render_incident_review_timeline_markdown(
    data: IncidentTimelineArtifactData,
) -> str:
    sections = [
        "# 故障复盘报告",
        _render_incident_summary(data.incident_summary),
        _render_incident_impact_metrics(data.impact_metrics),
        _render_incident_fact_sources(data.fact_sources),
        _render_incident_timeline(data.incident_summary, data.timeline_events),
        _render_incident_fact_separation(data.fact_separation),
        _render_incident_fact_summary(data.fact_summary),
        _render_incident_participants(data.participants),
        _render_incident_missing_information(data.missing_information),
        _render_incident_stage_gate(data.stage_gate),
    ]
    return "\n\n".join(sections)


def render_incident_review_root_cause_markdown(
    data: IncidentRootCauseArtifactData,
) -> str:
    sections = [
        "# 故障复盘报告",
        _render_incident_root_cause_context(data.analysis_context),
        _render_incident_why_chain(data.why_chain),
        _render_incident_cause_evidence(data.cause_evidence),
        _render_incident_fishbone(data.analysis_context, data.fishbone_categories),
        _render_incident_root_cause_conclusions(data.root_cause_conclusions),
        _render_incident_excluded_causes(data.excluded_causes),
        _render_incident_unverified_causes(data.unverified_causes),
        _render_incident_root_cause_stage_gate(data.stage_gate),
    ]
    return "\n\n".join(sections)


def render_incident_review_improvement_markdown(
    data: IncidentImprovementArtifactData,
) -> str:
    sections = [
        "# 故障复盘报告",
        _render_incident_improvement_report_info(data.report_info),
        _render_incident_improvement_timeline_summary(data.timeline_summary),
        _render_incident_improvement_root_cause_summary(data.root_cause_summary),
        "## 第三部分：改进措施",
        "### 7. 改进措施",
        _render_incident_improvement_priority_distribution(data.priority_distribution),
        _render_incident_improvement_actions(data.improvement_actions),
        _render_incident_improvement_root_cause_coverage(data.root_cause_coverage),
        _render_incident_improvement_prevention_checklist(data.prevention_checklist),
        _render_incident_improvement_review_plan(data.review_plan),
        _render_incident_improvement_residual_risks(data.residual_risks),
        _render_incident_improvement_lessons(data.lessons_learned),
        _render_incident_improvement_organizational_learning(
            data.organizational_learning
        ),
        _render_incident_improvement_signoffs(data.signoffs),
        _render_incident_improvement_stage_gate(data.stage_gate),
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
        _render_delivery_executive_summary(data.executive_summary),
        _render_delivery_requirement_summary(data.requirement_summary),
        _render_delivery_strategy_summary(data.strategy_summary_items),
        _render_delivery_case_summary(data.case_summary_items),
        _render_delivery_coverage_map(data.coverage_map),
        _render_delivery_open_risks(data.open_risks),
        _render_delivery_acceptance_checklist(data.acceptance_checklist),
        _render_delivery_signoffs(data.signoffs),
        _render_delivery_change_log(data.change_log),
        _render_delivery_document_info(data.document_info, data.delivery_metrics),
    ]
    return "\n\n".join(sections)


def render_req_review_review_markdown(data: ReqReviewArtifactData) -> str:
    sections = [
        "# 需求评审问题清单",
        _render_req_review_scope(data.scope_items),
        _render_req_review_quality_overview(data.quality_overview),
        _render_req_review_quality_flowchart(),
        _render_req_review_issue_statistics(
            data.issue_statistics, data.quality_overview
        ),
        _render_req_review_issue_groups(data.issue_groups),
        _render_req_review_revision_suggestions(data.revision_suggestions),
        _render_req_review_stage_gate(data.stage_gate),
        _render_req_review_info(data.review_info),
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


def render_value_discovery_journey_markdown(
    data: ValueDiscoveryJourneyArtifactData,
) -> str:
    sections = [
        "# 用户旅程分析",
        _render_journey_map(data.journey_stages),
        _render_journey_map_visual(data.journey_stages),
        _render_journey_stage_details(data.journey_stages),
        _render_journey_pain_priorities(data.pain_priorities, data.journey_stages),
        _render_journey_opportunity_scores(data.opportunity_scores),
        _render_journey_entry_strategy(data.entry_strategy),
        _render_journey_validation_experiments(data.validation_experiments),
        _render_journey_summary(data.journey_summary),
        _render_value_stage_gate(data.stage_gate),
    ]
    return "\n\n".join(sections)


def render_value_discovery_blueprint_markdown(
    data: ValueDiscoveryBlueprintArtifactData,
) -> str:
    sections = [
        f"# {data.document_info.product_name} 需求蓝图",
        _render_blueprint_product_overview(data.product_overview),
        _render_blueprint_target_users(data.target_users),
        _render_blueprint_requirements(data.feature_modules, data.requirements),
        _render_blueprint_main_flow(data.main_flow),
        _render_blueprint_success_metrics(data.success_metrics),
        _render_blueprint_mvp_plan(data.mvp_plan),
        _render_blueprint_non_functional_requirements(data.non_functional_requirements),
        _render_blueprint_acceptance_criteria(data.acceptance_criteria),
        _render_blueprint_roadmap(data.roadmap),
        _render_blueprint_risks(data.risks),
        _render_blueprint_lisa_handoff_inputs(data.lisa_handoff_inputs),
        _render_blueprint_stage_gate(data.stage_gate),
        _render_blueprint_document_info(data.document_info),
    ]
    return "\n\n".join(sections)


def render_user_story_scope_markdown(data: UserStoryScopeArtifactData) -> str:
    sections = [
        "# 用户故事拆解文档",
        _render_user_story_scope_requirements(data.in_scope_requirements),
        _render_user_story_traceability_index(data.traceability_index),
        _render_user_story_out_of_scope(data.out_of_scope_items),
        _render_user_story_blocking_questions(data.blocking_questions),
        _render_user_story_stage_gate(data.stage_gate, heading_number=5),
    ]
    return "\n\n".join(sections)


def render_user_story_map_markdown(data: UserStoryMapArtifactData) -> str:
    sections = [
        "# 用户故事拆解文档",
        _render_user_story_activities(data.activities),
        _render_user_story_tasks(data.tasks),
        _render_user_story_map(data.story_map_items, data.activities, data.tasks),
        _render_user_story_mvp_slices(data.mvp_slices),
        _render_user_story_release_slices(data.release_slices),
        _render_user_story_stage_gate(data.stage_gate, heading_number=6),
    ]
    return "\n\n".join(sections)


def render_user_stories_markdown(data: UserStoriesArtifactData) -> str:
    sections = [
        "# 用户故事拆解文档",
        _render_user_story_split_principles(data.split_principles),
        _render_user_story_cards(data.story_cards),
        _render_user_story_ready_summaries(data.ready_story_summaries),
        _render_user_story_not_ready(data.not_ready_stories),
        _render_user_story_open_questions(data.open_questions),
        _render_user_story_stage_gate(data.stage_gate, heading_number=6),
    ]
    return "\n\n".join(sections)


def render_user_story_handoff_markdown(
    data: UserStoryHandoffArtifactData,
) -> str:
    sections = [
        "# 单故事 Handoff 清单",
        _render_user_story_ready_overview(data.ready_story_overview),
        _render_user_story_packets(data.single_story_packets),
        _render_user_story_upstream_traceability(data.upstream_traceability),
        _render_user_story_not_ready_blockers(data.not_ready_blockers),
        _render_user_story_ai_coding_boundary(data.ai_coding_input_boundary),
        _render_user_story_stage_gate(data.stage_gate, heading_number=6),
    ]
    return "\n\n".join(sections)


def _render_user_story_scope_requirements(
    items: list[UserStoryScopeRequirement],
) -> str:
    rows = [
        (
            item.requirement_id,
            item.name,
            item.user_value,
            item.priority,
            item.split_decision,
            item.status,
        )
        for item in items
    ]
    return "## 1. 拆分范围\n" + _markdown_table(
        ["需求 ID", "需求名称", "用户价值", "优先级", "是否进入拆分", "状态"],
        rows,
    )


def _render_user_story_traceability_index(
    items: list[UserStoryScopeTrace],
) -> str:
    rows = [
        (
            item.requirement_id,
            item.source,
            item.target_user,
            item.scenario,
            item.acceptance_hint,
            item.status,
        )
        for item in items
    ]
    return (
        "## 2. 需求追溯索引\n"
        + _markdown_table(
            ["需求 ID", "来源章节 / 上游依据", "目标用户", "关键场景", "验收线索", "状态"],
            rows,
        )
        + "\n\n"
        + _render_user_story_scope_flowchart(items)
    )


def _render_user_story_scope_flowchart(items: list[UserStoryScopeTrace]) -> str:
    lines = [
        "```mermaid",
        "flowchart TD",
        '    Blueprint["需求蓝图"] --> InScope["进入拆分范围"]',
    ]
    for item in items:
        label = _escape_mermaid_label(f"{item.requirement_id} {item.scenario}")
        lines.append(f'    InScope --> {item.requirement_id.replace("-", "")}["{label}"]')
    lines.append("```")
    return "\n".join(lines)


def _render_user_story_out_of_scope(
    items: list[UserStoryOutOfScopeItem],
) -> str:
    rows = [
        (
            item.requirement_id,
            item.item,
            item.reason,
            item.reentry_condition,
            item.status,
        )
        for item in items
    ]
    return "## 3. 不拆范围\n" + _markdown_table(
        ["需求 ID", "范围项", "不拆原因", "重新进入条件", "状态"],
        rows,
    )


def _render_user_story_blocking_questions(
    items: list[UserStoryBlockingQuestion],
) -> str:
    rows = [
        (
            item.question_id,
            item.requirement_id,
            item.question,
            item.impact,
            item.owner,
            item.status,
        )
        for item in items
    ]
    return "## 4. 阻塞问题\n" + _markdown_table(
        ["问题 ID", "关联需求 ID", "问题", "对拆分的影响", "需要谁确认", "状态"],
        rows,
    )


def _render_user_story_activities(items: list[UserStoryActivity]) -> str:
    rows = [
        (
            item.activity_id,
            item.activity,
            item.user_goal,
            _join_inline(item.requirement_ids),
            item.priority,
        )
        for item in items
    ]
    return "## 1. 用户活动主干\n" + _markdown_table(
        ["活动 ID", "用户活动", "用户目标", "关联需求 ID", "优先级"],
        rows,
    )


def _render_user_story_tasks(items: list[UserStoryTask]) -> str:
    rows = [
        (
            item.task_id,
            item.activity_id,
            item.task,
            item.success_result,
            _join_inline(item.requirement_ids),
            item.status,
        )
        for item in items
    ]
    return "## 2. 用户任务流\n" + _markdown_table(
        ["任务 ID", "活动 ID", "用户任务", "成功结果", "关联需求 ID", "状态"],
        rows,
    )


def _render_user_story_map(
    items: list[UserStoryMapItem],
    activities: list[UserStoryActivity],
    tasks: list[UserStoryTask],
) -> str:
    rows = [
        (
            item.story_id,
            item.activity_id,
            item.task_id,
            item.title,
            _join_inline(item.requirement_ids),
            item.slice_id,
            item.status,
        )
        for item in items
    ]
    return (
        "## 3. 用户故事地图\n"
        + _render_user_story_map_flowchart(items, activities, tasks)
        + "\n\n"
        + _markdown_table(
            ["Story ID", "活动 ID", "任务 ID", "故事标题", "来源需求", "Slice", "状态"],
            rows,
        )
    )


def _render_user_story_map_flowchart(
    items: list[UserStoryMapItem],
    activities: list[UserStoryActivity],
    tasks: list[UserStoryTask],
) -> str:
    activity_lookup = {item.activity_id: item for item in activities}
    task_lookup = {item.task_id: item for item in tasks}
    lines = ["```mermaid", "flowchart TD"]
    for item in items:
        activity = activity_lookup[item.activity_id]
        task = task_lookup[item.task_id]
        activity_node = _safe_mermaid_node_id(activity.activity_id)
        task_node = _safe_mermaid_node_id(task.task_id)
        story_node = _safe_mermaid_node_id(item.story_id)
        slice_node = _safe_mermaid_node_id(item.slice_id)
        lines.extend([
            f'    {activity_node}["{_escape_mermaid_label(activity.activity_id + " " + activity.activity)}"] --> {task_node}["{_escape_mermaid_label(task.task_id + " " + task.task)}"]',
            f'    {task_node} --> {story_node}["{_escape_mermaid_label(item.story_id + " " + item.title)}"]',
            f'    {story_node} --> {slice_node}["{_escape_mermaid_label(item.slice_id)}"]',
        ])
    lines.append("```")
    return "\n".join(lines)


def _render_user_story_mvp_slices(items: list[UserStoryMvpSlice]) -> str:
    rows = [
        (
            item.slice_id,
            _join_inline(item.story_ids),
            item.business_outcome,
            _join_inline(item.excluded_items),
            item.acceptance,
        )
        for item in items
    ]
    return "## 4. MVP Slice\n" + _markdown_table(
        ["Slice ID", "包含 Story ID", "可验证业务闭环", "排除项", "验收口径"],
        rows,
    )


def _render_user_story_release_slices(items: list[UserStoryReleaseSlice]) -> str:
    rows = [
        (
            item.slice_id,
            _join_inline(item.story_ids),
            item.release_goal,
            _join_inline(item.dependencies),
            item.status,
        )
        for item in items
    ]
    return "## 5. Release Slice\n" + _markdown_table(
        ["Slice ID", "包含 Story ID", "发布目标", "依赖", "状态"],
        rows,
    )


def _render_user_story_split_principles(
    items: list[UserStorySplitPrinciple],
) -> str:
    rows = [
        (item.principle, item.applied, item.anti_pattern)
        for item in items
    ]
    return "## 1. 故事拆分原则\n" + _markdown_table(
        ["原则", "本轮采用方式", "反例拦截"],
        rows,
    )


def _render_user_story_cards(items: list[UserStoryCard]) -> str:
    rows = [
        (
            item.story_id,
            item.title,
            item.user_role,
            item.user_goal,
            item.benefit,
            _join_inline(item.requirement_ids),
            f"{item.activity_id} / {item.task_id}",
            _join_inline(item.business_rules),
            _join_inline(item.acceptance_criteria),
            _join_inline(item.out_of_scope),
            _join_inline(item.dependencies),
            item.status,
        )
        for item in items
    ]
    return "## 2. 用户故事卡片\n" + _markdown_table(
        [
            "Story ID",
            "标题",
            "作为",
            "我想要",
            "以便",
            "来源需求",
            "用户活动 / 任务",
            "业务规则",
            "验收标准",
            "不包含范围",
            "依赖",
            "状态",
        ],
        rows,
    )


def _render_user_story_ready_summaries(
    items: list[UserStoryReadySummary],
) -> str:
    rows = [
        (
            item.story_id,
            item.ready_reason,
            item.handoff_summary,
            item.acceptance_criteria_count,
            item.concerns,
        )
        for item in items
    ]
    return "## 3. Ready Stories\n" + _markdown_table(
        ["Story ID", "Ready 理由", "可交接需求摘要", "验收标准数量", "仍需关注"],
        rows,
    )


def _render_user_story_not_ready(items: list[UserStoryNotReadySummary]) -> str:
    rows = [
        (
            item.story_id,
            _join_inline(item.requirement_ids),
            item.blocker_reason,
            _join_inline(item.questions),
            item.suggested_next_step,
            item.status,
        )
        for item in items
    ]
    return "## 4. Not Ready Stories\n" + _markdown_table(
        ["Story ID", "来源需求", "阻塞原因", "需要补充的问题", "建议下一步", "状态"],
        rows,
    )


def _render_user_story_open_questions(items: list[UserStoryOpenQuestion]) -> str:
    rows = [
        (
            item.question_id,
            item.story_id,
            item.question,
            item.decision_impact,
            item.owner,
            item.status,
        )
        for item in items
    ]
    return "## 5. 开放问题\n" + _markdown_table(
        ["问题 ID", "关联 Story ID", "问题", "决策影响", "责任方", "状态"],
        rows,
    )


def _render_user_story_ready_overview(
    items: list[UserStoryReadyOverview],
) -> str:
    rows = [
        (
            item.story_id,
            item.title,
            _join_inline(item.requirement_ids),
            item.user_value,
            item.ready_reason,
            item.status,
        )
        for item in items
    ]
    return "## 1. Ready Story 总览\n" + _markdown_table(
        ["storyId", "标题", "requirementId", "用户价值", "Ready 理由", "状态"],
        rows,
    )


def _render_user_story_packets(items: list[UserStoryPacket]) -> str:
    sections = ["## 2. 单故事需求包"]
    for item in items:
        rows = [
            ("storyId", item.story_id),
            ("requirementId", _join_inline(item.requirement_ids)),
            ("userStory", item.user_story),
            ("acceptanceCriteria", _join_inline(item.acceptance_criteria)),
            ("businessRules", _join_inline(item.business_rules)),
            ("nonFunctionalNotes", _join_inline(item.non_functional_notes)),
            ("outOfScope", _join_inline(item.out_of_scope)),
            ("dependencies", _join_inline(item.dependencies)),
            ("openQuestions", _join_inline(item.open_questions)),
        ]
        sections.append(
            f"### {item.story_id}\n" + _markdown_table(["字段", "内容"], rows)
        )
    return "\n\n".join(sections)


def _render_user_story_upstream_traceability(
    items: list[UserStoryUpstreamTrace],
) -> str:
    rows = [
        (
            item.story_id,
            item.source_workflow,
            item.source_stage,
            _join_inline(item.source_requirements),
            item.source_slice,
            item.trace_note,
        )
        for item in items
    ]
    return "## 3. 上游追溯\n" + _markdown_table(
        ["storyId", "sourceWorkflow", "sourceStage", "sourceRequirement", "sourceSlice", "追溯说明"],
        rows,
    )


def _render_user_story_not_ready_blockers(
    items: list[UserStoryNotReadyBlocker],
) -> str:
    rows = [
        (
            item.story_id,
            _join_inline(item.requirement_ids),
            item.blocker_reason,
            _join_inline(item.questions),
            item.suggested_next_step,
        )
        for item in items
    ]
    return "## 4. Not Ready 阻塞项\n" + _markdown_table(
        ["storyId", "requirementId", "阻塞原因", "需要补充的问题", "建议处理"],
        rows,
    )


def _render_user_story_ai_coding_boundary(boundary: AiCodingInputBoundary) -> str:
    rows = [(_join_inline(boundary.allowed), _join_inline(boundary.forbidden))]
    return "## 5. AI Coding 输入边界\n" + _markdown_table(
        ["可以交接", "不在本清单中交接"],
        rows,
    )


def _render_user_story_stage_gate(
    checks: list[StageGateCheck],
    *,
    heading_number: int,
) -> str:
    lines = [f"- [{'x' if item.checked else ' '}] {item.item}" for item in checks]
    return f"## {heading_number}. 阶段门禁\n" + "\n".join(lines)


def _join_inline(items: list[str]) -> str:
    return "；".join(items) if items else "无"


def _safe_mermaid_node_id(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "", value) or "Node"


def _render_document_info(info: DocumentInfo) -> str:
    rows = [
        ("Artifact 名称", info.artifact_name),
        ("Workflow", info.workflow),
        ("Stage", info.stage),
        ("状态", info.status),
    ]
    return "## 附录：文档信息\n" + _markdown_table(["字段", "内容"], rows)


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
        x_value = item.confidence / 5
        y_value = item.impact / 5
        lines.append(
            f'    "{_escape_mermaid_label(item.idea_name)}": '
            f"[{x_value:.2f}, {y_value:.2f}]"
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
    lines = [
        "```mermaid",
        "timeline",
        f"    title {_escape_mermaid_timeline_text(summary.incident_name)} 事件时间线",
    ]
    current_section = None
    for item in events:
        if item.section != current_section:
            current_section = item.section
            lines.append(f"    section {_escape_mermaid_timeline_text(item.section)}")
        lines.append(
            f"        {_escape_mermaid_time(item.occurred_at)} : "
            f"{_escape_mermaid_timeline_text(item.event)}"
        )
    lines.append("```")
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
        + "\n".join(lines)
        + "\n\n"
        + _markdown_table(["阶段", "时间点", "事件描述", "关联事实"], rows)
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
        "columns": [
            "层级",
            "问题",
            "回答",
            "原因类型",
            "证据",
            "证据强度",
            "置信度",
            "可行动性",
        ],
        "rows": [
            {
                "层级": item.level,
                "问题": item.question,
                "回答": item.answer,
                "原因类型": item.cause_type,
                "证据": item.evidence,
                "证据强度": item.evidence_strength,
                "置信度": item.confidence,
                "可行动性": item.actionability,
            }
            for item in items
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
            _strategy_risk_rpn(item),
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
                "RPN": _strategy_risk_rpn(item),
                "缓解策略": item.mitigation,
                "覆盖建议": item.coverage,
            }
            for item in risks
        ],
    }
    return (
        "```ai4se-visual\n" + json.dumps(visual, ensure_ascii=False, indent=2) + "\n```"
    )


def _strategy_risk_rpn(risk: StrategyRisk) -> int:
    return (
        risk.rpn
        if risk.rpn is not None
        else risk.severity * risk.occurrence * risk.detection
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
    return "## 附录：文档信息\n" + _markdown_table(["字段", "内容"], rows)


def _render_delivery_executive_summary(
    items: list[DeliveryExecutiveSummaryItem],
) -> str:
    rows = [
        (item.summary_item, item.conclusion, item.evidence_source, item.status)
        for item in items
    ]
    return "## 1. 执行摘要\n" + _markdown_table(
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
    return "## 2. 需求分析摘要\n" + _markdown_table(
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
    return "## 3. 测试策略摘要\n" + _markdown_table(
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
    return "## 4. 测试用例摘要\n" + _markdown_table(
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
        "## 5. 覆盖地图\n"
        + _markdown_table(
            ["需求", "风险", "测试点", "用例", "验收状态"],
            rows,
        )
        + "\n\n"
        + _render_coverage_map_visual(items)
        + "\n\n### 5.1 需求/风险/测试点追溯矩阵\n"
        + _render_delivery_traceability_matrix_visual(items)
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


def _render_delivery_traceability_matrix_visual(
    items: list[DeliveryCoverageMapItem],
) -> str:
    visual = {
        "type": "traceability-matrix",
        "title": "需求-风险-测试点-用例追溯矩阵",
        "columns": ["需求", "风险", "测试点", "覆盖用例", "验收状态"],
        "rows": [
            {
                "需求": item.requirement,
                "风险": item.risk,
                "测试点": item.test_point,
                "覆盖用例": ", ".join(item.case_ids),
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
    return "## 6. 开放风险\n" + _markdown_table(
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
    return "## 7. 交付验收清单\n" + "\n".join(lines)


def _render_delivery_signoffs(items: list[DeliverySignoff]) -> str:
    rows = [(item.role, item.owner, item.opinion, item.status) for item in items]
    return "## 8. 签署确认\n" + _markdown_table(
        ["角色", "姓名/责任方", "签署意见", "状态"],
        rows,
    )


def _render_delivery_change_log(items: list[DeliveryChangeLogItem]) -> str:
    rows = [
        (item.version, item.date, item.change, item.reason, item.owner)
        for item in items
    ]
    return "## 9. 变更记录\n" + _markdown_table(
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
    return "## 附录：评审信息\n" + _markdown_table(["字段", "内容"], rows)


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


def _render_journey_map(stages: list[JourneyStage]) -> str:
    lines = [
        "```mermaid",
        "journey",
        "    title 核心用户旅程",
    ]
    for stage in stages:
        lines.append(f"    section {_escape_journey_text(stage.stage_name)}")
        lines.append(
            f"        {_escape_journey_text(stage.user_task)}: "
            f"{stage.emotion_score}: 用户"
        )
    lines.append("```")
    return (
        "## 用户旅程地图\n"
        + "\n".join(lines)
        + "\n\n> 数字为情绪评分：1=非常沮丧，5=非常满意"
    )


def _render_journey_map_visual(stages: list[JourneyStage]) -> str:
    visual = {
        "type": "journey-map",
        "title": "用户旅程结构化地图",
        "columns": [
            "阶段",
            "用户任务",
            "触点",
            "情绪评分",
            "关键痛点",
            "机会假设",
            "成功指标",
            "验证状态",
        ],
        "rows": [
            {
                "阶段": item.stage_name,
                "用户任务": item.user_task,
                "触点": item.touchpoint,
                "情绪评分": item.emotion_score,
                "关键痛点": item.key_pain,
                "机会假设": item.opportunity_hypothesis,
                "成功指标": item.success_metric,
                "验证状态": item.validation_status,
            }
            for item in stages
        ],
    }
    return (
        "## 结构化旅程地图\n"
        "```ai4se-visual\n" + json.dumps(visual, ensure_ascii=False, indent=2) + "\n```"
    )


def _render_journey_stage_details(stages: list[JourneyStage]) -> str:
    sections = ["## 关键阶段详细分析"]
    for index, stage in enumerate(stages, start=1):
        rows = [
            ("旅程阶段", f"{stage.stage_id} {stage.stage_name}"),
            ("触点渠道", stage.touchpoint),
            ("用户任务", stage.user_task),
            ("用户目标", stage.user_goal),
            ("用户行为", stage.user_behavior),
            ("情绪评分", f"{stage.emotion_score} 分：{stage.emotion_reason}"),
            ("关键痛点", f"{stage.pain_id} {stage.key_pain}"),
            ("现有方案不足", stage.existing_solution_gap),
            ("机会假设", f"{stage.opportunity_id} {stage.opportunity_hypothesis}"),
            ("成功指标", stage.success_metric),
            ("验证状态", stage.validation_status),
        ]
        sections.append(
            f"### 阶段 {index}：{stage.stage_name}\n"
            + _markdown_table(["维度", "描述"], rows)
        )
    return "\n\n".join(sections)


def _render_journey_pain_priorities(
    items: list[JourneyPainPriority],
    stages: list[JourneyStage],
) -> str:
    stage_names = {stage.stage_id: stage.stage_name for stage in stages}
    sections = ["## 痛点优先级排序"]
    priority_levels = ["高优先级痛点", "中等优先级痛点", "低优先级痛点"]
    headers = ["痛点 ID", "痛点", "影响阶段", "影响程度", "发生频率", "现有方案不足"]
    for level in priority_levels:
        rows = [
            (
                item.pain_id,
                item.pain,
                stage_names[item.stage_id],
                item.impact,
                item.frequency,
                item.existing_solution_gap,
            )
            for item in items
            if item.priority_level == level
        ]
        if not rows:
            rows = [("无", "本轮未识别", "无", "无", "无", "无")]
        sections.append(f"### {level}\n" + _markdown_table(headers, rows))
    return "\n\n".join(sections)


def _render_journey_opportunity_scores(
    items: list[JourneyOpportunityScore],
) -> str:
    rows = [
        (
            item.opportunity_id,
            item.opportunity,
            item.pain_id,
            item.value_potential,
            item.competition_strength,
            item.feasibility,
            item.success_metric,
            item.validation_status,
        )
        for item in items
    ]
    return "## 机会评分\n" + _markdown_table(
        [
            "机会 ID",
            "机会",
            "对应痛点",
            "价值潜力",
            "竞争强度",
            "实现可行性",
            "成功指标",
            "验证状态",
        ],
        rows,
    )


def _render_journey_entry_strategy(items: list[JourneyEntryStrategy]) -> str:
    rows = [
        (
            item.strategy_item,
            item.content,
            item.related_opportunity,
            item.tradeoff_reason,
            item.status,
        )
        for item in items
    ]
    return "## 产品切入策略\n" + _markdown_table(
        ["策略项", "内容", "关联机会", "取舍理由", "状态"],
        rows,
    )


def _render_journey_validation_experiments(
    items: list[JourneyValidationExperiment],
) -> str:
    rows = [
        (
            item.experiment_id,
            item.hypothesis,
            item.opportunity_id,
            item.method,
            item.success_metric,
            item.owner,
            item.status,
        )
        for item in items
    ]
    return "## 验证实验\n" + _markdown_table(
        ["实验 ID", "验证假设", "关联机会", "实验方式", "成功指标", "责任方", "状态"],
        rows,
    )


def _render_journey_summary(summary: JourneySummary) -> str:
    rows = [
        ("核心用户", summary.core_persona),
        ("核心痛点", summary.core_pain),
        ("产品切入策略", summary.entry_strategy),
        ("需求蓝图就绪判断", summary.blueprint_readiness),
    ]
    return "## 旅程摘要\n" + _markdown_table(["字段", "内容"], rows)


def _escape_journey_text(value: str) -> str:
    return value.replace("\n", " ").replace(":", "：").replace("|", "｜")


def _escape_mermaid_time(value: str) -> str:
    return value.replace("\n", " ").replace(":", "：")


def _escape_mermaid_timeline_text(value: str) -> str:
    return value.replace("\n", " ").replace(":", "：").replace("|", "｜")


def _escape_mermaid_mindmap_text(value: str) -> str:
    return (
        value.replace("\n", " ").replace(":", "：").replace("|", "｜").replace('"', "'")
    )


def _render_blueprint_document_info(info: BlueprintDocumentInfo) -> str:
    rows = [
        ("文档版本", info.version),
        ("创建日期", info.created_at),
        ("产品方向", info.product_direction),
        ("Artifact 名称", info.artifact_name),
        ("蓝图状态", info.blueprint_status),
    ]
    return "## 附录：文档信息\n" + _markdown_table(["维度", "内容"], rows)


def _render_blueprint_product_overview(overview: BlueprintProductOverview) -> str:
    core_value_rows = [
        ("用户价值", overview.user_value),
        ("商业价值", overview.business_value),
        ("商业模式", overview.business_model),
    ]
    return (
        "## 1. 产品概述\n\n"
        "### 1.1 产品愿景\n"
        f"> {overview.vision}\n\n"
        "### 1.2 定位声明\n"
        f"**For** {overview.positioning_for} **who** {overview.positioning_who},\n"
        f"**the** {overview.positioning_product} **is a** "
        f"{overview.positioning_category}\n"
        f"**that** {overview.positioning_value}. **Unlike** "
        f"{overview.positioning_unlike},\n"
        f"**our product** {overview.positioning_differentiator}.\n\n"
        "### 1.3 核心价值\n" + _markdown_table(["维度", "描述"], core_value_rows)
    )


def _render_blueprint_target_users(items: list[BlueprintTargetUser]) -> str:
    rows = [(item.user_type, item.core_pain, item.priority) for item in items]
    return "## 2. 目标用户（摘要）\n" + _markdown_table(
        ["用户类型", "核心痛点", "优先级"], rows
    )


def _render_blueprint_requirements(
    modules: list[BlueprintFeatureModule],
    requirements: list[BlueprintRequirement],
) -> str:
    sections = [
        "## 3. 核心需求",
        "### 功能架构\n" + _render_blueprint_feature_mindmap(modules),
    ]
    headings = [
        ("P0", "### P0 需求（核心功能，必须实现）"),
        ("P1", "### P1 需求（重要功能，应该实现）"),
        ("P2", "### P2 需求（增值功能，可以实现）"),
    ]
    headers = [
        "ID",
        "需求名称",
        "用户故事",
        "对应痛点",
        "范围边界",
        "依赖",
        "验收标准",
        "可测试性等级",
        "owner",
        "状态",
    ]
    for priority, heading in headings:
        rows = [
            (
                item.requirement_id,
                item.name,
                item.user_story,
                item.related_pain,
                item.scope,
                item.dependency,
                item.acceptance,
                item.testability_level,
                item.owner,
                item.status,
            )
            for item in requirements
            if item.priority == priority
        ]
        if not rows:
            rows = [
                ("无", "本轮未规划", "无", "无", "无", "无", "无", "无", "无", "无")
            ]
        sections.append(heading + "\n" + _markdown_table(headers, rows))
    return "\n\n".join(sections)


def _render_blueprint_feature_mindmap(modules: list[BlueprintFeatureModule]) -> str:
    lines = ["```mermaid", "mindmap", '    root(("产品名称"))']
    for module in modules:
        lines.append(f'        ("{_escape_mermaid_label(module.module_name)}")')
        for feature in module.features:
            lines.append(
                f'            ["{_escape_mermaid_label(feature.feature_name)}"]'
            )
    lines.append("```")
    return "\n".join(lines)


def _render_blueprint_main_flow(flow: BlueprintMainFlow) -> str:
    node_lookup = {node.node_id: node for node in flow.nodes}
    existing_ids: dict[str, str] = {}
    safe_ids = {
        node.node_id: _node_id(node.node_id, existing_ids) for node in flow.nodes
    }
    lines = ["```mermaid", "flowchart TD"]
    for node in flow.nodes:
        lines.append(
            f'    {safe_ids[node.node_id]}["{_escape_mermaid_label(node.label)}"]'
        )
    for link in flow.links:
        lines.append(
            f"    {safe_ids[link.from_node]} -->|"
            f'"{_escape_mermaid_label(link.label)}"| {safe_ids[link.to_node]}'
        )
    lines.append("```")
    rows = [
        (
            link.from_node,
            node_lookup[link.from_node].label,
            link.label,
            link.to_node,
            node_lookup[link.to_node].label,
        )
        for link in flow.links
    ]
    return "## 4. 核心流程\n\n" "### 主流程图\n" + "\n".join(
        lines
    ) + "\n\n" + _markdown_table(["起点 ID", "起点", "动作", "终点 ID", "终点"], rows)


def _render_blueprint_success_metrics(
    items: list[BlueprintSuccessMetric],
) -> str:
    rows = [
        (item.metric_type, item.metric_name, item.target, item.measurement)
        for item in items
    ]
    return "## 5. 成功指标\n" + _markdown_table(
        ["指标类型", "指标名称", "目标值", "衡量方式"],
        rows,
    )


def _render_blueprint_mvp_plan(plan: BlueprintMvpPlan) -> str:
    feature_lines = [
        f"- [{'x' if item.included else ' '}] {item.requirement_id}: "
        f"{item.feature_name} — {item.release}"
        for item in plan.included_features
    ]
    iteration_rows = [
        (item.version, item.time, item.core_features, item.goal)
        for item in plan.iterations
    ]
    return (
        "## 6. MVP 范围与计划\n"
        "### MVP 包含功能\n" + "\n".join(feature_lines) + "\n\n"
        "### 迭代路线\n"
        + _markdown_table(["版本", "时间", "核心功能", "目标"], iteration_rows)
    )


def _render_blueprint_non_functional_requirements(
    items: list[BlueprintNonFunctionalRequirement],
) -> str:
    rows = [
        (
            item.type,
            item.description,
            item.metric_or_constraint,
            item.verification,
            item.owner,
            item.status,
        )
        for item in items
    ]
    return "## 7. 非功能需求\n" + _markdown_table(
        ["类型", "需求描述", "指标/约束", "验证方式", "owner", "状态"],
        rows,
    )


def _render_blueprint_acceptance_criteria(
    items: list[BlueprintAcceptanceCriterion],
) -> str:
    rows = [
        (
            item.acceptance_id,
            item.requirement_id,
            item.criterion,
            item.verification,
            item.testability_level,
            item.owner,
            item.status,
        )
        for item in items
    ]
    return "## 8. 验收标准\n" + _markdown_table(
        [
            "验收 ID",
            "关联需求",
            "验收标准",
            "验证方式",
            "可测试性等级",
            "owner",
            "状态",
        ],
        rows,
    )


def _render_blueprint_roadmap(items: list[BlueprintRoadmapItem]) -> str:
    visual = {
        "type": "roadmap",
        "title": "产品迭代路线图",
        "columns": ["版本", "时间", "核心功能", "目标", "成功指标"],
        "rows": [
            {
                "版本": item.version,
                "时间": item.time,
                "核心功能": item.core_features,
                "目标": item.goal,
                "成功指标": item.success_metric,
            }
            for item in items
        ],
    }
    return (
        "## 9. 路线图\n"
        "```ai4se-visual\n" + json.dumps(visual, ensure_ascii=False, indent=2) + "\n```"
    )


def _render_blueprint_risks(items: list[BlueprintRisk]) -> str:
    rows = [
        (
            item.risk_type,
            item.description,
            item.probability,
            item.impact,
            item.mitigation,
            item.owner,
            item.status,
        )
        for item in items
    ]
    return "## 10. 风险评估\n" + _markdown_table(
        ["风险类型", "风险描述", "可能性", "影响", "缓解措施", "owner", "状态"],
        rows,
    )


def _render_blueprint_lisa_handoff_inputs(
    items: list[BlueprintLisaHandoffInput],
) -> str:
    rows = [
        (
            item.input_type,
            item.reference_id,
            item.content,
            item.source,
            item.usage,
            item.status,
        )
        for item in items
    ]
    return "## 11. Lisa Handoff 输入\n" + _markdown_table(
        ["输入类型", "ID", "内容", "来源", "给 Lisa 的用途", "状态"],
        rows,
    )


def _render_blueprint_stage_gate(checks: list[StageGateCheck]) -> str:
    lines = [f"- [{'x' if item.checked else ' '}] {item.item}" for item in checks]
    return "## 12. 阶段门禁\n" + "\n".join(lines)


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
    explanatory_headers = {
        ("字段", "内容"),
        ("维度", "内容"),
        ("格子", "内容"),
        ("属性", "详情"),
    }
    if len(headers) == 2 and tuple(headers) in explanatory_headers:
        return _definition_list(rows)

    header = "| " + " | ".join(headers) + " |"
    separator = "| " + " | ".join("---" for _ in headers) + " |"
    body = [
        "| " + " | ".join(_escape_table_cell(cell) for cell in row) + " |"
        for row in rows
    ]
    return "\n".join([header, separator, *body])


def _definition_list(rows: list[tuple[Any, ...]]) -> str:
    lines = []
    for row in rows:
        if len(row) != 2:
            lines.append(
                "- "
                + "：".join(_format_definition_value(cell) for cell in row)
            )
            continue
        label, value = row
        lines.append(
            f"- **{_format_definition_value(label)}**："
            f"{_format_definition_value(value)}"
        )
    return "\n".join(lines)


def _format_definition_value(value: Any) -> str:
    return str(value).replace("\n", "；")


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
    normalized = re.sub(r"\s+", " ", str(value)).strip()
    return normalized.replace("\\", "\\\\").replace('"', '\\"')
