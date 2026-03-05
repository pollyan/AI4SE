import { describe, it, expect } from 'vitest';
import { getAgentWorkflows } from '../agentWorkflows';
import { WORKFLOWS } from '../../workflows';

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

    it('should return workflows for Alex', () => {
        const workflows = getAgentWorkflows('alex');
        expect(workflows.length).toBeGreaterThanOrEqual(2);

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
        expect(wf.name).toBe('价值发现');
        expect(wf.agentId).toBe('alex');
        expect(wf.stages).toHaveLength(4);
        expect(wf.stages[0].id).toBe('ELEVATOR');
        expect(wf.stages[3].id).toBe('BLUEPRINT');
        expect(wf.stages[0].description.length).toBeGreaterThan(100);
        expect(wf.stages[1].description.length).toBeGreaterThan(100);
        expect(wf.stages[2].description.length).toBeGreaterThan(100);
        expect(wf.stages[3].description.length).toBeGreaterThan(100);
    });

    it('should have value-discovery workflow in Alex agent workflows as online and without prd-creation', () => {
        const workflows = getAgentWorkflows('alex');

        const valueDiscovery = workflows.find(w => w.id === 'value-discovery');
        expect(valueDiscovery).toBeDefined();
        expect(valueDiscovery?.status).toBe('online');

        const prdCreation = workflows.find(w => w.id === 'prd-creation');
        expect(prdCreation).toBeUndefined();
    });

    it('every workflow definition should configure an agentId', () => {
        for (const key of Object.keys(WORKFLOWS)) {
            const wf = WORKFLOWS[key as keyof typeof WORKFLOWS];
            expect(wf.agentId).toBeDefined();
            expect(typeof wf.agentId).toBe('string');
        }
    });

    it('should return empty array for unsupported agents', () => {
        const unknown = getAgentWorkflows('unknown');
        expect(unknown).toEqual([]);
    });
});

