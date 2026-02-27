import { describe, it, expect } from 'vitest';
import { getAgentWorkflows } from '../agentWorkflows';

describe('Workflow Configuration', () => {
    it('should return a list of workflows for Lisa', () => {
        const workflows = getAgentWorkflows('lisa');
        expect(workflows.length).toBeGreaterThanOrEqual(3);

        const testDesign = workflows.find(w => w.id === 'test-design');
        expect(testDesign).toBeDefined();
        expect(testDesign?.name).toBe('自动化测试设计');
        expect(testDesign?.status).toBe('online');

        const devWorkflow = workflows.find(w => w.status === 'dev');
        expect(devWorkflow).toBeDefined();
        expect(devWorkflow?.name).toBe('执行日志诊断');

        const planWorkflow = workflows.find(w => w.status === 'plan');
        expect(planWorkflow).toBeDefined();
        expect(planWorkflow?.name).toBe('智能断言生成');
    });

    it('should return empty array for unsupported agents', () => {
        const workflows = getAgentWorkflows('alex');
        expect(workflows).toEqual([]);

        const unknown = getAgentWorkflows('unknown');
        expect(unknown).toEqual([]);
    });
});
