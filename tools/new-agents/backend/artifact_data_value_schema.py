from __future__ import annotations

from pydantic import Field, model_validator

from artifact_data_renderer_base import (
    DocumentInfo,
    StageGateCheck,
    StrictArtifactDataModel,
)


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


def validate_value_flow_references(value_flow: ValueFlow) -> None:
    node_ids = {node.node_id for node in value_flow.nodes}
    if len(node_ids) != len(value_flow.nodes):
        raise ValueError("value_flow.nodes contains duplicate node_id")

    unknown_references = sorted(
        {
            reference
            for link in value_flow.links
            for reference in (link.from_node, link.to_node)
            if reference not in node_ids
        }
    )
    if unknown_references:
        raise ValueError(
            "value_flow.links references unknown node ids: "
            + ", ".join(unknown_references)
        )


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
    total_score: int | None = Field(default=None, ge=1)
    average_score: float | None = Field(default=None, ge=1, le=5)
    judgement: str


class ValueAssumption(StrictArtifactDataModel):
    assumption_id: str
    content: str
    impact: str
    validation_action: str
    owner: str
    status: str


def normalize_value_score_summary(
    score_matrix: list[ValueScore],
    score_summary: ValueScoreSummary,
) -> None:
    total_score = sum(item.score for item in score_matrix)
    if score_summary.total_score is None:
        score_summary.total_score = total_score
    elif score_summary.total_score != total_score:
        raise ValueError("score_summary.total_score must equal score_matrix score sum")

    expected_average = round(total_score / len(score_matrix), 2)
    if score_summary.average_score is None:
        score_summary.average_score = expected_average
    elif abs(score_summary.average_score - expected_average) > 0.001:
        raise ValueError(
            "score_summary.average_score must equal score_matrix average score "
            f"({expected_average})"
        )


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
        validate_value_flow_references(self.value_flow)

        normalize_value_score_summary(self.score_matrix, self.score_summary)
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


def validate_persona_ids(personas: list[PersonaProfile]) -> set[str]:
    persona_ids = {persona.persona_id for persona in personas}
    if len(persona_ids) != len(personas):
        raise ValueError("personas contains duplicate persona_id")
    return persona_ids


def validate_persona_references(
    personas: list[PersonaProfile],
    references: list[str],
) -> None:
    persona_ids = validate_persona_ids(personas)
    unknown = sorted(
        {persona_id for persona_id in references if persona_id not in persona_ids}
    )
    if unknown:
        raise ValueError(
            "persona references unknown persona ids: " + ", ".join(unknown)
        )


def validate_persona_priority_ranking(
    personas: list[PersonaProfile],
    priority_ranking: list[PersonaPriorityRanking],
) -> None:
    validate_persona_references(
        personas,
        [item.persona_id for item in priority_ranking],
    )
    ranked_ids = [item.persona_id for item in priority_ranking]
    if len(set(ranked_ids)) != len(ranked_ids):
        raise ValueError("priority_ranking contains duplicate persona_id")


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
        validate_persona_ids(self.personas)
        validate_persona_references(
            self.personas,
            [item.persona_id for item in self.behavior_scenarios],
        )
        validate_persona_references(
            self.personas,
            [item.persona_id for item in self.decision_chain],
        )
        validate_persona_references(
            self.personas,
            [item.persona_id for item in self.pain_evidence],
        )
        validate_persona_priority_ranking(self.personas, self.priority_ranking)
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


def validate_journey_stages(journey_stages: list[JourneyStage]) -> None:
    for field_name in ("stage_id", "pain_id", "opportunity_id"):
        values = [getattr(item, field_name) for item in journey_stages]
        if len(values) != len(set(values)):
            raise ValueError(f"journey_stages contains duplicate {field_name}")


def validate_journey_pain_priorities(
    journey_stages: list[JourneyStage],
    pain_priorities: list[JourneyPainPriority],
) -> None:
    validate_journey_stages(journey_stages)
    stage_ids = {item.stage_id for item in journey_stages}
    pain_ids = {item.pain_id for item in journey_stages}
    unknown_stage_ids = sorted(
        {item.stage_id for item in pain_priorities if item.stage_id not in stage_ids}
    )
    if unknown_stage_ids:
        raise ValueError(
            "pain_priorities references unknown stage ids: "
            + ", ".join(unknown_stage_ids)
        )
    unknown_pain_ids = sorted(
        {item.pain_id for item in pain_priorities if item.pain_id not in pain_ids}
    )
    if unknown_pain_ids:
        raise ValueError(
            "journey references unknown pain ids: " + ", ".join(unknown_pain_ids)
        )


def validate_journey_opportunity_scores(
    journey_stages: list[JourneyStage],
    opportunity_scores: list[JourneyOpportunityScore],
) -> None:
    validate_journey_stages(journey_stages)
    pain_ids = {item.pain_id for item in journey_stages}
    opportunity_ids = {item.opportunity_id for item in journey_stages}
    unknown_pain_ids = sorted(
        {item.pain_id for item in opportunity_scores if item.pain_id not in pain_ids}
    )
    if unknown_pain_ids:
        raise ValueError(
            "journey references unknown pain ids: " + ", ".join(unknown_pain_ids)
        )
    unknown_opportunity_ids = sorted(
        {
            item.opportunity_id
            for item in opportunity_scores
            if item.opportunity_id not in opportunity_ids
        }
    )
    if unknown_opportunity_ids:
        raise ValueError(
            "journey references unknown opportunity ids: "
            + ", ".join(unknown_opportunity_ids)
        )


def validate_journey_opportunity_references(
    journey_stages: list[JourneyStage],
    references: list[str],
) -> None:
    validate_journey_stages(journey_stages)
    opportunity_ids = {item.opportunity_id for item in journey_stages}
    unknown = sorted({item for item in references if item not in opportunity_ids})
    if unknown:
        raise ValueError(
            "journey references unknown opportunity ids: " + ", ".join(unknown)
        )


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
        validate_journey_stages(self.journey_stages)
        validate_journey_pain_priorities(self.journey_stages, self.pain_priorities)
        validate_journey_opportunity_scores(
            self.journey_stages, self.opportunity_scores
        )
        validate_journey_opportunity_references(
            self.journey_stages,
            [item.related_opportunity for item in self.entry_strategy],
        )
        validate_journey_opportunity_references(
            self.journey_stages,
            [item.opportunity_id for item in self.validation_experiments],
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


def validate_blueprint_requirements(
    requirements: list[BlueprintRequirement],
) -> set[str]:
    requirement_ids = {item.requirement_id for item in requirements}
    if len(requirement_ids) != len(requirements):
        raise ValueError("requirements contains duplicate requirement_id")
    return requirement_ids


def validate_blueprint_requirement_references(
    requirements: list[BlueprintRequirement],
    references: list[str],
) -> None:
    requirement_ids = validate_blueprint_requirements(requirements)
    unknown = sorted({item for item in references if item not in requirement_ids})
    if unknown:
        raise ValueError(
            "blueprint references unknown requirement ids: " + ", ".join(unknown)
        )


def validate_blueprint_acceptance_criteria(
    requirements: list[BlueprintRequirement],
    acceptance_criteria: list[BlueprintAcceptanceCriterion],
) -> set[str]:
    acceptance_ids = {item.acceptance_id for item in acceptance_criteria}
    if len(acceptance_ids) != len(acceptance_criteria):
        raise ValueError("acceptance_criteria contains duplicate acceptance_id")
    validate_blueprint_requirement_references(
        requirements,
        [item.requirement_id for item in acceptance_criteria],
    )
    return acceptance_ids


def validate_blueprint_handoff_inputs(
    requirements: list[BlueprintRequirement],
    acceptance_criteria: list[BlueprintAcceptanceCriterion],
    lisa_handoff_inputs: list[BlueprintLisaHandoffInput],
) -> None:
    requirement_ids = validate_blueprint_requirements(requirements)
    acceptance_ids = validate_blueprint_acceptance_criteria(
        requirements, acceptance_criteria
    )
    unknown_requirements = sorted(
        {
            item.reference_id
            for item in lisa_handoff_inputs
            if item.input_type == "需求" and item.reference_id not in requirement_ids
        }
    )
    if unknown_requirements:
        raise ValueError(
            "blueprint references unknown requirement ids: "
            + ", ".join(unknown_requirements)
        )
    unknown_acceptance_ids = sorted(
        {
            item.reference_id
            for item in lisa_handoff_inputs
            if item.input_type == "验收标准" and item.reference_id not in acceptance_ids
        }
    )
    if unknown_acceptance_ids:
        raise ValueError(
            "blueprint references unknown acceptance ids: "
            + ", ".join(unknown_acceptance_ids)
        )


def validate_blueprint_main_flow(main_flow: BlueprintMainFlow) -> None:
    flow_node_ids = {item.node_id for item in main_flow.nodes}
    if len(flow_node_ids) != len(main_flow.nodes):
        raise ValueError("main_flow.nodes contains duplicate node_id")
    unknown_flow_nodes = sorted(
        {
            node_id
            for link in main_flow.links
            for node_id in (link.from_node, link.to_node)
            if node_id not in flow_node_ids
        }
    )
    if unknown_flow_nodes:
        raise ValueError(
            "main_flow.links references unknown node ids: "
            + ", ".join(unknown_flow_nodes)
        )


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
        validate_blueprint_requirements(self.requirements)
        validate_blueprint_requirement_references(
            self.requirements,
            [
                feature.requirement_id
                for module in self.feature_modules
                for feature in module.features
                if feature.requirement_id is not None
            ],
        )
        validate_blueprint_requirement_references(
            self.requirements,
            [item.requirement_id for item in self.mvp_plan.included_features],
        )
        validate_blueprint_acceptance_criteria(
            self.requirements, self.acceptance_criteria
        )
        validate_blueprint_handoff_inputs(
            self.requirements,
            self.acceptance_criteria,
            self.lisa_handoff_inputs,
        )
        validate_blueprint_main_flow(self.main_flow)

        return self
