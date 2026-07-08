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

    it('appends manifest artifact data contract guidance to IDEA CONVERGE prompt description', () => {
        const convergeStage = WORKFLOWS.IDEA_BRAINSTORM.stages.find(stage => stage.id === 'CONVERGE');

        expect(convergeStage).toBeDefined();
        expect(convergeStage?.description).toContain('【artifact_data 契约同步约束】');
        expect(convergeStage?.description).toContain('ice_evaluations.idea_id 必须唯一');
        expect(convergeStage?.description).toContain('decision_matrix.recommended_idea_id');
        expect(convergeStage?.description).toContain('validation_experiments.idea_ids');
        expect(convergeStage?.description).toContain('merge_paths.source_idea_ids');
        expect(convergeStage?.description).toContain('不要输出完整 Markdown 文档、Markdown 表格、Mermaid 代码块或 quadrantChart');
        expect(convergeStage?.description).toContain('后端会负责确定性渲染右侧收敛聚焦产物和 Mermaid quadrantChart');
    });

    it('appends manifest artifact data contract guidance to TEST DESIGN CASES prompt description', () => {
        const casesStage = WORKFLOWS.TEST_DESIGN.stages.find(stage => stage.id === 'CASES');

        expect(casesStage).toBeDefined();
        expect(casesStage?.description).toContain('【artifact_data 契约同步约束】');
        expect(casesStage?.description).toContain('case_statistics 由后端根据 case_groups 计算，模型不要输出');
        expect(casesStage?.description).toContain('case_groups[].cases[].case_id 必须唯一');
        expect(casesStage?.description).toContain('automation_candidates.case_id');
        expect(casesStage?.description).toContain('coverage_trace.covered_cases');
        expect(casesStage?.description).toContain('不要输出完整 Markdown 文档、Markdown 表格、Mermaid 代码块或 traceability-matrix JSON 代码块');
        expect(casesStage?.description).toContain('后端会负责确定性渲染右侧测试用例集和 ai4se-visual traceability-matrix');
    });

    it('does not ask TEST DESIGN CASES to handwrite renderer-owned visuals', () => {
        const casesStage = WORKFLOWS.TEST_DESIGN.stages.find(stage => stage.id === 'CASES');

        expect(casesStage).toBeDefined();
        expect(casesStage?.description).not.toContain('测试点覆盖追溯必须同时输出 Markdown 表格和 ai4se-visual 结构化矩阵');
        expect(casesStage?.description).not.toContain('ai4se-visual 必须使用 ```ai4se-visual fenced 代码块');
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
