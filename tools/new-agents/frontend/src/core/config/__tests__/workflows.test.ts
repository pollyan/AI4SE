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

    it('should return empty array for unsupported agents', () => {
        const workflows = getAgentWorkflows('alex');
        expect(workflows).toEqual([]);

        const unknown = getAgentWorkflows('unknown');
        expect(unknown).toEqual([]);
    });
});

