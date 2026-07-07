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

    it('should return core workflows for Alex', () => {
        const workflows = getAgentWorkflows('alex');
        const ids = workflows.map(w => w.id);
        expect(ids).toContain('idea-brainstorm');
        expect(ids).toContain('value-discovery');
        expect(ids).toContain('user-story-breakdown');
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

    it('should have USER_STORY_BREAKDOWN workflow defined with correct agentId and stages', () => {
        const wf = WORKFLOWS.USER_STORY_BREAKDOWN;
        expect(wf).toBeDefined();
        expect(wf.name).toBe('用户故事拆解');
        expect(wf.agentId).toBe('alex');
        expect(wf.slug).toBe('user-story-breakdown');
        expect(wf.stages.map(stage => stage.id)).toEqual(['SCOPE', 'STORY_MAP', 'STORIES', 'HANDOFF']);
        for (const stage of wf.stages) {
            expect(stage.description.length).toBeGreaterThan(100);
            expect(stage.template.length).toBeGreaterThan(100);
        }
    });

    it('should have value-discovery workflow in Alex agent workflows as online and without prd-creation', () => {
        const workflows = getAgentWorkflows('alex');

        const valueDiscovery = workflows.find(w => w.id === 'value-discovery');
        expect(valueDiscovery).toBeDefined();
        expect(valueDiscovery?.status).toBe('online');

        const prdCreation = workflows.find(w => w.id === 'prd-creation');
        expect(prdCreation).toBeUndefined();
    });

    it('should expose user-story-breakdown as online instead of plan for Alex', () => {
        const workflows = getAgentWorkflows('alex');

        const storyBreakdown = workflows.find(w => w.id === 'user-story-breakdown');
        expect(storyBreakdown).toBeDefined();
        expect(storyBreakdown?.status).toBe('online');
        expect(storyBreakdown?.link).toBe('/workspace/alex/user-story-breakdown');
        expect(workflows.find(w => w.id === 'story-breakdown')).toBeUndefined();
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
