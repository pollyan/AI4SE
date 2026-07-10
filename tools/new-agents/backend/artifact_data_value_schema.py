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
        if self.score_summary.total_score is None:
            self.score_summary.total_score = total_score
        elif self.score_summary.total_score != total_score:
            raise ValueError(
                "score_summary.total_score must equal score_matrix score sum"
            )

        expected_average = round(total_score / len(self.score_matrix), 2)
        if self.score_summary.average_score is None:
            self.score_summary.average_score = expected_average
        elif abs(self.score_summary.average_score - expected_average) > 0.001:
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

