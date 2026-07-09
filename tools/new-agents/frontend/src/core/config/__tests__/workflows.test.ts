import { describe, it, expect } from 'vitest';
import { getAgentWorkflows } from '../agentWorkflows';
import { WORKFLOWS, WORKFLOW_SLUGS, SLUG_TO_WORKFLOW } from '../../workflows';
import { getStagePromptTemplateId } from '../../workflowRegistry';
import type { WorkflowType } from '../../types';

describe('Workflow Configuration', () => {
    it('should return a list of workflows for Lisa', () => {
        const workflows = getAgentWorkflows('lisa');
        expect(workflows.length).toBeGreaterThanOrEqual(4);

        const testDesign = workflows.find(w => w.id === 'test-design');
        expect(testDesign).toBeDefined();
        expect(testDesign?.name).toBe('测试策略与用例设计');
        expect(testDesign?.status).toBe('online');

        const devWorkflow = workflows.find(w => w.id === 'log-diagnostics');
        expect(devWorkflow).toBeDefined();
        expect(devWorkflow?.name).toBe('执行日志诊断');

        const planWorkflow = workflows.find(w => w.status === 'plan');
        expect(planWorkflow).toBeDefined();
        expect(planWorkflow?.name).toBe('智能断言生成');
    });

    it('should have req-review workflow configured as online for Lisa', () => {
        const workflows = getAgentWorkflows('lisa');
        const reqReview = workflows.find(w => w.id === 'req-review');

        expect(reqReview).toBeDefined();
        expect(reqReview?.status).toBe('online');
        expect(reqReview?.name).toBe('需求评审');
        expect(reqReview?.link).toBe('/workspace/lisa/req-review');
    });

    it('should have REQ_REVIEW workflow with 2 stages and valid descriptions', () => {
        const wf = WORKFLOWS.REQ_REVIEW;

        expect(wf).toBeDefined();
        expect(wf.name).toBe('需求评审');
        expect(wf.stages).toHaveLength(2);

        expect(wf.stages[0].id).toBe('REVIEW');
        expect(wf.stages[0].name).toBe('深度评审');
        expect(wf.stages[0].description.length).toBeGreaterThan(100);

        expect(wf.stages[1].id).toBe('REPORT');
        expect(wf.stages[1].name).toBe('评审报告');
        expect(wf.stages[1].description.length).toBeGreaterThan(100);
    });

    it('should return at least two core workflows for Alex', () => {
        const workflows = getAgentWorkflows('alex');
        const ids = workflows.map(w => w.id);
        expect(ids).toContain('idea-brainstorm');
        expect(ids).toContain('value-discovery');
    });

    it('should configure IDEA_BRAINSTORM as online for Alex', () => {
        const workflows = getAgentWorkflows('alex');
        const ideaBrainstorm = workflows.find(w => w.id === 'idea-brainstorm');
        expect(ideaBrainstorm).toBeDefined();
        expect(ideaBrainstorm?.status).toBe('online');
    });

    it('should have IDEA_BRAINSTORM workflow defined with correct agentId and stages', () => {
        const wf = WORKFLOWS.IDEA_BRAINSTORM;
        expect(wf).toBeDefined();
        expect(wf.name).toBe('创意头脑风暴');
        expect(wf.agentId).toBe('alex');
        expect(wf.stages).toHaveLength(4);
        expect(wf.stages[0].id).toBe('DEFINE');
        expect(wf.stages[3].id).toBe('CONCEPT');
    });

    it('should have VALUE_DISCOVERY workflow defined with correct agentId and stages', () => {
        const wf = WORKFLOWS.VALUE_DISCOVERY;
        expect(wf).toBeDefined();
        expect(wf.name).toBe('需求蓝图梳理');
        expect(wf.agentId).toBe('alex');
        expect(wf.stages).toHaveLength(4);
        expect(wf.stages[0].id).toBe('ELEVATOR');
        expect(wf.stages[3].id).toBe('BLUEPRINT');
        expect(wf.stages[0].description.length).toBeGreaterThan(100);
        expect(wf.stages[1].description.length).toBeGreaterThan(100);
        expect(wf.stages[2].description.length).toBeGreaterThan(100);
        expect(wf.stages[3].description.length).toBeGreaterThan(100);
    });

    it('should configure STORY_BREAKDOWN as an online Alex workflow', () => {
        const wf = WORKFLOWS.STORY_BREAKDOWN;
        expect(wf).toBeDefined();
        expect(wf.name).toBe('用户故事拆解');
        expect(wf.agentId).toBe('alex');
        expect(wf.slug).toBe('story-breakdown');
        expect(wf.stages).toHaveLength(4);
        expect(wf.stages[0].id).toBe('INPUT_ANALYSIS');
        expect(wf.stages[1].id).toBe('EPIC_MAPPING');
        expect(wf.stages[2].id).toBe('STORY_BACKLOG');
        expect(wf.stages[3].id).toBe('SPRINT_PLAN');

        const workflows = getAgentWorkflows('alex');
        const storyBreakdown = workflows.find(w => w.id === 'story-breakdown');
        expect(storyBreakdown).toBeDefined();
        expect(storyBreakdown?.status).toBe('online');
        expect(storyBreakdown?.link).toBe('/workspace/alex/story-breakdown');
    });

    it('publishes Alex PRD review as an online runtime workflow', () => {
        const workflow = WORKFLOWS.PRD_REVIEW;

        expect(workflow.agentId).toBe('alex');
        expect(workflow.slug).toBe('prd-review');
        expect(workflow.stages.map(stage => stage.id)).toEqual([
            'INVENTORY',
            'QUALITY_AUDIT',
            'COMPLETION_PLAN',
            'REVISION_BLUEPRINT',
        ]);
        for (const stage of workflow.stages) {
            expect(stage.description.length).toBeGreaterThan(100);
            expect(stage.template?.length).toBeGreaterThan(100);
        }

        expect(getAgentWorkflows('alex')).toEqual(
            expect.arrayContaining([
                expect.objectContaining({
                    id: 'prd-review',
                    status: 'online',
                    link: '/workspace/alex/prd-review',
                }),
            ])
        );
    });

    it('should have value-discovery workflow in Alex agent workflows as online and without prd-creation', () => {
        const workflows = getAgentWorkflows('alex');

        const valueDiscovery = workflows.find(w => w.id === 'value-discovery');
        expect(valueDiscovery).toBeDefined();
        expect(valueDiscovery?.status).toBe('online');

        const prdCreation = workflows.find(w => w.id === 'prd-creation');
        expect(prdCreation).toBeUndefined();
    });

    it('should expose story-breakdown as an online Alex runtime workflow', () => {
        const workflows = getAgentWorkflows('alex');
        const storyBreakdown = workflows.find(w => w.id === 'story-breakdown');

        expect(storyBreakdown).toBeDefined();
        expect(storyBreakdown?.status).toBe('online');
        expect(storyBreakdown?.link).toBe('/workspace/alex/story-breakdown');

        const wf = WORKFLOWS.STORY_BREAKDOWN;
        expect(wf.agentId).toBe('alex');
        expect(wf.slug).toBe('story-breakdown');
        expect(wf.stages.map(stage => stage.id)).toEqual([
            'INPUT_ANALYSIS',
            'EPIC_MAPPING',
            'STORY_BACKLOG',
            'SPRINT_PLAN',
        ]);
    });

    it('should configure PRD_REVIEW as an online Alex workflow', () => {
        const workflows = getAgentWorkflows('alex');
        const prdReview = workflows.find(w => w.id === 'prd-review');

        expect(prdReview).toBeDefined();
        expect(prdReview?.status).toBe('online');
        expect(prdReview?.link).toBe('/workspace/alex/prd-review');

        const wf = WORKFLOWS.PRD_REVIEW;
        expect(wf.agentId).toBe('alex');
        expect(wf.slug).toBe('prd-review');
        expect(wf.stages.map(stage => stage.id)).toEqual([
            'INVENTORY',
            'QUALITY_AUDIT',
            'COMPLETION_PLAN',
            'REVISION_BLUEPRINT',
        ]);
    });

    it('every workflow definition should configure an agentId', () => {
        for (const key of Object.keys(WORKFLOWS)) {
            const wf = WORKFLOWS[key as keyof typeof WORKFLOWS];
            expect(wf.agentId).toBeDefined();
            expect(typeof wf.agentId).toBe('string');
        }
    });

    it('should derive reversible workflow slug mappings from workflow definitions', () => {
        for (const workflowId of Object.keys(WORKFLOWS) as WorkflowType[]) {
            const wf = WORKFLOWS[workflowId];

            expect(wf.slug).toBeTruthy();
            expect(WORKFLOW_SLUGS[workflowId]).toBe(wf.slug);
            expect(SLUG_TO_WORKFLOW[wf.slug]).toBe(workflowId);
        }
    });

    it('should attach prompt descriptions and templates to every runtime workflow stage', () => {
        for (const workflowId of Object.keys(WORKFLOWS) as WorkflowType[]) {
            const wf = WORKFLOWS[workflowId];

            for (const stage of wf.stages) {
                expect(getStagePromptTemplateId(workflowId, stage.id)).toBeTruthy();
                expect(stage.description.trim().length).toBeGreaterThan(100);
                expect(stage.template.trim().length).toBeGreaterThan(100);
            }
        }
    });

    it('exposes manifest artifact data contract for TEST DESIGN STRATEGY', () => {
        const strategy = WORKFLOWS.TEST_DESIGN.stages.find(stage => stage.id === 'STRATEGY');

        expect(strategy?.artifactDataContract?.modelOutputRules).toContain(
            'risks[].rpn 由后端根据 severity * occurrence * detection 计算；RPN 由后端根据 severity * occurrence * detection 计算，模型不要输出',
        );
        expect(strategy?.artifactDataContract?.modelOutputRules).toContain('quality_goals[].goal_id 必须唯一');
        expect(strategy?.artifactDataContract?.modelOutputRules).toContain(
            'test_points.quality_goal、test_points.risk、test_points.technique 只能引用 artifact_data 中已定义的 QG/R/TS ID',
        );
        expect(strategy?.artifactDataContract?.forbiddenOutputs).toContain('risk-board JSON 代码块');
    });

    it('exposes manifest artifact data contract for INCIDENT REVIEW ROOT CAUSE', () => {
        const rootCause = WORKFLOWS.INCIDENT_REVIEW.stages.find(stage => stage.id === 'ROOT_CAUSE');

        expect(rootCause?.artifactDataContract?.modelOutputRules).toContain(
            'why_chain[].level 必须唯一，并按 5-Why 链路从直接原因到深层原因排序',
        );
        expect(rootCause?.artifactDataContract?.modelOutputRules).toContain(
            'cause_evidence.cause_id 必须唯一',
        );
        expect(rootCause?.artifactDataContract?.modelOutputRules).toContain(
            'cause_evidence.related_level 只能引用 why_chain[].level 中已定义的追问层级',
        );
        expect(rootCause?.artifactDataContract?.modelOutputRules).toContain(
            'fishbone_categories.cause_ids 只能引用 cause_evidence.cause_id 中已定义的原因 ID',
        );
        expect(rootCause?.artifactDataContract?.modelOutputRules).toContain(
            'root_cause_conclusions.related_cause_id 只能引用 cause_evidence.cause_id 中已定义的原因 ID',
        );
        expect(rootCause?.artifactDataContract?.forbiddenOutputs).toContain('cause-map JSON 代码块');
        expect(rootCause?.artifactDataContract?.rendererOutputs).toContain('ai4se-visual cause-map');
    });

    it('does not ask TEST DESIGN STRATEGY model to handwrite renderer-owned visuals in artifact data mode', () => {
        const strategy = WORKFLOWS.TEST_DESIGN.stages.find(stage => stage.id === 'STRATEGY');

        expect(strategy?.description).not.toContain('如果契约明确要求 artifact_update.markdown');
        expect(strategy?.description).not.toContain('Mermaid 必须严格按模板格式输出');
        expect(strategy?.description).not.toContain('手写 Mermaid');
        expect(strategy?.description).not.toContain('手写 Mermaid、ai4se-visual risk-board 或 Markdown 表格');
    });

    it('should derive every online agent workflow card from runtime workflow definitions', () => {
        const allCards = [
            ...getAgentWorkflows('lisa'),
            ...getAgentWorkflows('alex'),
        ];
        const onlineCards = allCards.filter(wf => wf.status === 'online');

        expect(onlineCards).toHaveLength(Object.keys(WORKFLOWS).length);

        for (const workflowId of Object.keys(WORKFLOWS) as WorkflowType[]) {
            const wf = WORKFLOWS[workflowId];
            const card = onlineCards.find(candidate => candidate.id === wf.slug);

            expect(card).toBeDefined();
            expect(card?.agentId).toBe(wf.agentId);
            expect(card?.status).toBe('online');
            expect(card?.name).toBe(wf.listing.name);
            expect(card?.description).toBe(wf.listing.description);
            expect(card?.icon).toBe(wf.listing.icon);
            expect(card?.link).toBe(`/workspace/${wf.agentId}/${wf.slug}`);
            expect(card?.preview).toEqual(wf.listing.preview);
            expect(card?.preview?.suitableFor.length).toBeGreaterThanOrEqual(2);
            expect(card?.preview?.notSuitableFor.length).toBeGreaterThanOrEqual(1);
            expect(card?.preview?.requiredInputs.length).toBeGreaterThanOrEqual(2);
            expect(card?.preview?.expectedOutputs.length).toBeGreaterThanOrEqual(2);
            expect(card?.preview?.sampleInput.trim()).not.toBe('');
        }
    });

    it('should return empty array for unsupported agents', () => {
        const unknown = getAgentWorkflows('unknown');
        expect(unknown).toEqual([]);
    });
});
