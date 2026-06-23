import { WorkflowDef, WorkflowType } from './types';
import { getStagePromptTemplateId, workflowManifest } from './workflowRegistry';
import { IMPROVEMENT_PROMPT, IMPROVEMENT_TEMPLATE } from './prompts/incident_review/improvement';
import { ROOT_CAUSE_PROMPT, ROOT_CAUSE_TEMPLATE } from './prompts/incident_review/root_cause';
import { TIMELINE_PROMPT, TIMELINE_TEMPLATE } from './prompts/incident_review/timeline';
import { DEFINE_PROMPT, DEFINE_TEMPLATE } from './prompts/idea_brainstorm/define';
import { DIVERGE_PROMPT, DIVERGE_TEMPLATE } from './prompts/idea_brainstorm/diverge';
import { CONVERGE_PROMPT, CONVERGE_TEMPLATE } from './prompts/idea_brainstorm/converge';
import { CONCEPT_PROMPT, CONCEPT_TEMPLATE } from './prompts/idea_brainstorm/concept';
import { CLARIFY_PROMPT, CLARIFY_TEMPLATE } from './prompts/test_design/clarify';
import { STRATEGY_PROMPT, STRATEGY_TEMPLATE } from './prompts/test_design/strategy';
import { CASES_PROMPT, CASES_TEMPLATE } from './prompts/test_design/cases';
import { DELIVERY_PROMPT, DELIVERY_TEMPLATE } from './prompts/test_design/delivery';
import { REVIEW_PROMPT, REVIEW_TEMPLATE } from './prompts/req_review/review';
import { REPORT_PROMPT, REPORT_TEMPLATE } from './prompts/req_review/report';
import { ELEVATOR_PROMPT, ELEVATOR_TEMPLATE } from './prompts/value_discovery/elevator';
import { PERSONA_PROMPT, PERSONA_TEMPLATE } from './prompts/value_discovery/persona';
import { JOURNEY_PROMPT, JOURNEY_TEMPLATE } from './prompts/value_discovery/journey';
import { BLUEPRINT_PROMPT, BLUEPRINT_TEMPLATE } from './prompts/value_discovery/blueprint';
import { INVENTORY_PROMPT, INVENTORY_TEMPLATE } from './prompts/prd_review/inventory';
import { QUALITY_AUDIT_PROMPT, QUALITY_AUDIT_TEMPLATE } from './prompts/prd_review/quality_audit';
import { COMPLETION_PLAN_PROMPT, COMPLETION_PLAN_TEMPLATE } from './prompts/prd_review/completion_plan';
import { REVISION_BLUEPRINT_PROMPT, REVISION_BLUEPRINT_TEMPLATE } from './prompts/prd_review/revision_blueprint';

type StageContent = {
    description: string;
    template: string;
};

const STAGE_CONTENT_BY_TEMPLATE_ID: Record<string, StageContent> = {
        'test_design.clarify': {
            description: CLARIFY_PROMPT,
            template: CLARIFY_TEMPLATE,
        },
        'test_design.strategy': {
            description: STRATEGY_PROMPT,
            template: STRATEGY_TEMPLATE,
        },
        'test_design.cases': {
            description: CASES_PROMPT,
            template: CASES_TEMPLATE,
        },
        'test_design.delivery': {
            description: DELIVERY_PROMPT,
            template: DELIVERY_TEMPLATE,
        },
        'req_review.review': {
            description: REVIEW_PROMPT,
            template: REVIEW_TEMPLATE,
        },
        'req_review.report': {
            description: REPORT_PROMPT,
            template: REPORT_TEMPLATE,
        },
        'incident_review.timeline': {
            description: TIMELINE_PROMPT,
            template: TIMELINE_TEMPLATE,
        },
        'incident_review.root_cause': {
            description: ROOT_CAUSE_PROMPT,
            template: ROOT_CAUSE_TEMPLATE,
        },
        'incident_review.improvement': {
            description: IMPROVEMENT_PROMPT,
            template: IMPROVEMENT_TEMPLATE,
        },
        'idea_brainstorm.define': {
            description: DEFINE_PROMPT,
            template: DEFINE_TEMPLATE,
        },
        'idea_brainstorm.diverge': {
            description: DIVERGE_PROMPT,
            template: DIVERGE_TEMPLATE,
        },
        'idea_brainstorm.converge': {
            description: CONVERGE_PROMPT,
            template: CONVERGE_TEMPLATE,
        },
        'idea_brainstorm.concept': {
            description: CONCEPT_PROMPT,
            template: CONCEPT_TEMPLATE,
        },
        'value_discovery.elevator': {
            description: ELEVATOR_PROMPT,
            template: ELEVATOR_TEMPLATE,
        },
        'value_discovery.persona': {
            description: PERSONA_PROMPT,
            template: PERSONA_TEMPLATE,
        },
        'value_discovery.journey': {
            description: JOURNEY_PROMPT,
            template: JOURNEY_TEMPLATE,
        },
        'value_discovery.blueprint': {
            description: BLUEPRINT_PROMPT,
            template: BLUEPRINT_TEMPLATE,
        },
        'prd_review.inventory': {
            description: INVENTORY_PROMPT,
            template: INVENTORY_TEMPLATE,
        },
        'prd_review.quality_audit': {
            description: QUALITY_AUDIT_PROMPT,
            template: QUALITY_AUDIT_TEMPLATE,
        },
        'prd_review.completion_plan': {
            description: COMPLETION_PLAN_PROMPT,
            template: COMPLETION_PLAN_TEMPLATE,
        },
        'prd_review.revision_blueprint': {
            description: REVISION_BLUEPRINT_PROMPT,
            template: REVISION_BLUEPRINT_TEMPLATE,
        },
};

const buildWorkflow = (workflowId: WorkflowType): WorkflowDef => {
    const manifestWorkflow = workflowManifest.workflows[workflowId];

    return {
        ...manifestWorkflow,
        stages: manifestWorkflow.stages.map((stage) => {
            const promptTemplateId = getStagePromptTemplateId(workflowId, stage.id);
            const content = STAGE_CONTENT_BY_TEMPLATE_ID[promptTemplateId];
            if (!content) {
                throw new Error(`Missing prompt/template content for ${workflowId}/${stage.id}: ${promptTemplateId}`);
            }
            return {
                ...stage,
                description: content.description,
                template: content.template,
            };
        }),
    };
};

export const WORKFLOWS: Record<WorkflowType, WorkflowDef> = Object.fromEntries(
    (Object.keys(workflowManifest.workflows) as WorkflowType[]).map((workflowId) => [
        workflowId,
        buildWorkflow(workflowId),
    ])
) as Record<WorkflowType, WorkflowDef>;

export const WORKFLOW_SLUGS: Record<WorkflowType, string> = Object.fromEntries(
    Object.entries(WORKFLOWS).map(([workflowId, workflow]) => [workflowId, workflow.slug])
) as Record<WorkflowType, string>;

export const SLUG_TO_WORKFLOW: Record<string, WorkflowType> = Object.fromEntries(
    Object.entries(WORKFLOWS).map(([workflowId, workflow]) => [workflow.slug, workflowId])
) as Record<string, WorkflowType>;
