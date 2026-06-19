import { WorkflowDef, WorkflowType } from './types';
import workflowManifestData from '../../../workflow_manifest.json';
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

type WorkflowManifestStage = {
    id: string;
    name: string;
};

type WorkflowManifestWorkflow = Omit<WorkflowDef, 'stages' | 'welcomeMessage'> & {
    stages: WorkflowManifestStage[];
};

type WorkflowManifest = {
    workflows: Record<WorkflowType, WorkflowManifestWorkflow>;
};

type StageContent = {
    description: string;
    template: string;
};

const workflowManifest = workflowManifestData as WorkflowManifest;

const STAGE_CONTENT: Record<WorkflowType, Record<string, StageContent>> = {
    TEST_DESIGN: {
        CLARIFY: {
            description: CLARIFY_PROMPT,
            template: CLARIFY_TEMPLATE,
        },
        STRATEGY: {
            description: STRATEGY_PROMPT,
            template: STRATEGY_TEMPLATE,
        },
        CASES: {
            description: CASES_PROMPT,
            template: CASES_TEMPLATE,
        },
        DELIVERY: {
            description: DELIVERY_PROMPT,
            template: DELIVERY_TEMPLATE,
        },
    },
    REQ_REVIEW: {
        REVIEW: {
            description: REVIEW_PROMPT,
            template: REVIEW_TEMPLATE,
        },
        REPORT: {
            description: REPORT_PROMPT,
            template: REPORT_TEMPLATE,
        },
    },
    INCIDENT_REVIEW: {
        TIMELINE: {
            description: TIMELINE_PROMPT,
            template: TIMELINE_TEMPLATE,
        },
        ROOT_CAUSE: {
            description: ROOT_CAUSE_PROMPT,
            template: ROOT_CAUSE_TEMPLATE,
        },
        IMPROVEMENT: {
            description: IMPROVEMENT_PROMPT,
            template: IMPROVEMENT_TEMPLATE,
        },
    },
    IDEA_BRAINSTORM: {
        DEFINE: {
            description: DEFINE_PROMPT,
            template: DEFINE_TEMPLATE,
        },
        DIVERGE: {
            description: DIVERGE_PROMPT,
            template: DIVERGE_TEMPLATE,
        },
        CONVERGE: {
            description: CONVERGE_PROMPT,
            template: CONVERGE_TEMPLATE,
        },
        CONCEPT: {
            description: CONCEPT_PROMPT,
            template: CONCEPT_TEMPLATE,
        },
    },
    VALUE_DISCOVERY: {
        ELEVATOR: {
            description: ELEVATOR_PROMPT,
            template: ELEVATOR_TEMPLATE,
        },
        PERSONA: {
            description: PERSONA_PROMPT,
            template: PERSONA_TEMPLATE,
        },
        JOURNEY: {
            description: JOURNEY_PROMPT,
            template: JOURNEY_TEMPLATE,
        },
        BLUEPRINT: {
            description: BLUEPRINT_PROMPT,
            template: BLUEPRINT_TEMPLATE,
        },
    },
};

const buildWorkflow = (workflowId: WorkflowType): WorkflowDef => {
    const manifestWorkflow = workflowManifest.workflows[workflowId];
    const stageContentById = STAGE_CONTENT[workflowId];

    return {
        ...manifestWorkflow,
        stages: manifestWorkflow.stages.map((stage) => {
            const content = stageContentById[stage.id];
            if (!content) {
                throw new Error(`Missing prompt/template content for ${workflowId}/${stage.id}`);
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
