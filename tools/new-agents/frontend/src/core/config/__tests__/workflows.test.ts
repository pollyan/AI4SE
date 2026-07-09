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

    it('exposes manifest artifact data contract for INCIDENT REVIEW TIMELINE', () => {
        const timeline = WORKFLOWS.INCIDENT_REVIEW.stages.find(stage => stage.id === 'TIMELINE');

        expect(timeline?.artifactDataContract?.modelOutputRules).toContain(
            '所有字符串字段必须是非空白内容',
        );
        expect(timeline?.artifactDataContract?.modelOutputRules).toContain(
            'impact_metrics、fact_sources、timeline_events、fact_separation、fact_summary、participants、missing_information 和 stage_gate 都必须至少包含 1 条',
        );
        expect(timeline?.artifactDataContract?.modelOutputRules).toContain(
            'timeline_events[].fact_ids 必须至少包含 1 个事实 ID',
        );
        expect(timeline?.artifactDataContract?.modelOutputRules).toContain(
            'fact_sources[].fact_id 必须唯一',
        );
        expect(timeline?.artifactDataContract?.modelOutputRules).toContain(
            'timeline_events[].fact_ids 只能引用 fact_sources[].fact_id 中已定义的事实 ID',
        );
        expect(timeline?.artifactDataContract?.forbiddenOutputs).toContain('Mermaid 代码块');
        expect(timeline?.artifactDataContract?.rendererOutputs).toContain('右侧故障复盘事件还原');
        expect(timeline?.artifactDataContract?.rendererOutputs).toContain('Mermaid timeline');
    });

    it('exposes manifest artifact data contract for INCIDENT REVIEW IMPROVEMENT', () => {
        const improvement = WORKFLOWS.INCIDENT_REVIEW.stages.find(stage => stage.id === 'IMPROVEMENT');

        expect(improvement?.artifactDataContract?.modelOutputRules).toContain(
            'report_info.action_count 必须等于 improvement_actions 数量',
        );
        expect(improvement?.artifactDataContract?.modelOutputRules).toContain(
            'improvement_actions[].action_id 必须唯一',
        );
        expect(improvement?.artifactDataContract?.modelOutputRules).toContain(
            'priority_distribution.urgent_count/important_count/normal_count 必须等于 improvement_actions[].priority 中紧急/重要/常规的数量',
        );
        expect(improvement?.artifactDataContract?.modelOutputRules).toContain(
            'root_cause_coverage[].action_ids 只能引用 improvement_actions[].action_id 中已定义的行动 ID',
        );
        expect(improvement?.artifactDataContract?.modelOutputRules).toContain(
            'improvement_actions[].root_cause_id 只能引用 root_cause_coverage[].cause_id 中已定义的根因 ID',
        );
        expect(improvement?.artifactDataContract?.forbiddenOutputs).toContain('action-board JSON 代码块');
        expect(improvement?.artifactDataContract?.rendererOutputs).toContain('右侧最终故障复盘报告');
        expect(improvement?.artifactDataContract?.rendererOutputs).toContain('ai4se-visual action-board');
    });

    it('exposes manifest artifact data contract for IDEA BRAINSTORM DEFINE', () => {
        const define = WORKFLOWS.IDEA_BRAINSTORM.stages.find(stage => stage.id === 'DEFINE');

        expect(define?.artifactDataContract?.modelOutputRules).toContain(
            'evidence_items[].evidence_id 必须唯一',
        );
        expect(define?.artifactDataContract?.modelOutputRules).toContain(
            'problem_landscape.subproblems[].problem_id 必须唯一',
        );
        expect(define?.artifactDataContract?.modelOutputRules).toContain(
            'problem_user_fit.evidence_ids 只能引用 evidence_items[].evidence_id 中已定义的证据 ID',
        );
        expect(define?.artifactDataContract?.modelOutputRules).toContain(
            'problem_landscape.root_problem 必须被至少一个 evidence_items.related_problem 或 problem_user_fit.evidence_or_assumption 条目覆盖',
        );
        expect(define?.artifactDataContract?.forbiddenOutputs).toContain('Mermaid 代码块');
        expect(define?.artifactDataContract?.forbiddenOutputs).toContain('mindmap 代码块');
        expect(define?.artifactDataContract?.rendererOutputs).toContain('Mermaid mindmap');
    });

    it('exposes manifest artifact data contract for IDEA BRAINSTORM DIVERGE', () => {
        const diverge = WORKFLOWS.IDEA_BRAINSTORM.stages.find(stage => stage.id === 'DIVERGE');

        expect(diverge?.artifactDataContract?.modelOutputRules).toContain(
            'idea_cards[].idea_id 必须唯一',
        );
        expect(diverge?.artifactDataContract?.modelOutputRules).toContain(
            'idea_sources[].source_id 必须唯一',
        );
        expect(diverge?.artifactDataContract?.modelOutputRules).toContain(
            'parked_or_excluded[].record_id 必须唯一',
        );
        expect(diverge?.artifactDataContract?.modelOutputRules).toContain(
            'idea_landscape.groups[].idea_ids 只能引用 idea_cards[].idea_id 中已定义的创意 ID',
        );
        expect(diverge?.artifactDataContract?.modelOutputRules).toContain(
            'idea_sources[].idea_ids 只能引用 idea_cards[].idea_id 中已定义的创意 ID',
        );
        expect(diverge?.artifactDataContract?.forbiddenOutputs).toContain('Mermaid 代码块');
        expect(diverge?.artifactDataContract?.forbiddenOutputs).toContain('mindmap 代码块');
        expect(diverge?.artifactDataContract?.rendererOutputs).toContain('Mermaid mindmap');
    });

    it('exposes manifest artifact data contract for IDEA BRAINSTORM CONCEPT', () => {
        const concept = WORKFLOWS.IDEA_BRAINSTORM.stages.find(stage => stage.id === 'CONCEPT');

        expect(concept?.artifactDataContract?.modelOutputRules).toContain(
            'core_assumptions[].assumption_id 必须唯一',
        );
        expect(concept?.artifactDataContract?.modelOutputRules).toContain(
            'validation_roadmap[].validation_id 必须唯一',
        );
        expect(concept?.artifactDataContract?.modelOutputRules).toContain(
            'next_actions[].action_id 必须唯一',
        );
        expect(concept?.artifactDataContract?.modelOutputRules).toContain(
            'lean_canvas.cell 必须覆盖问题、用户群体、独特价值主张、解决方案、渠道、收入来源、成本结构、关键指标、竞争壁垒',
        );
        expect(concept?.artifactDataContract?.modelOutputRules).toContain(
            'growth_funnel.stage 必须覆盖 Acquisition、Activation、Retention、Revenue、Referral',
        );
        expect(concept?.artifactDataContract?.modelOutputRules).toContain(
            'mvp_features[].assumption_ids 只能引用 core_assumptions[].assumption_id 中已定义的假设 ID',
        );
        expect(concept?.artifactDataContract?.modelOutputRules).toContain(
            'validation_roadmap[].assumption_ids 只能引用 core_assumptions[].assumption_id 中已定义的假设 ID',
        );
        expect(concept?.artifactDataContract?.modelOutputRules).toContain(
            'next_actions[].related_ids 只能引用 core_assumptions[].assumption_id、validation_roadmap[].validation_id 或 premortem_risks[].risk_id 中已定义的 ID',
        );
        expect(concept?.artifactDataContract?.forbiddenOutputs).toContain('mvp-map JSON 代码块');
        expect(concept?.artifactDataContract?.rendererOutputs).toContain('ai4se-visual mvp-map');
        expect(concept?.artifactDataContract?.rendererOutputs).toContain('Mermaid pie');
        expect(concept?.artifactDataContract?.rendererOutputs).toContain('Mermaid flowchart');
    });

    it('exposes manifest artifact data contract for VALUE DISCOVERY ELEVATOR', () => {
        const elevator = WORKFLOWS.VALUE_DISCOVERY.stages.find(stage => stage.id === 'ELEVATOR');

        expect(elevator?.artifactDataContract?.modelOutputRules).toContain(
            'value_flow.nodes[].node_id 必须唯一',
        );
        expect(elevator?.artifactDataContract?.modelOutputRules).toContain(
            'value_flow.links[].from_node 和 value_flow.links[].to_node 只能引用 value_flow.nodes[].node_id 中已定义的节点 ID',
        );
        expect(elevator?.artifactDataContract?.modelOutputRules).toContain(
            'score_matrix[].score 必须是 1 到 5 的整数',
        );
        expect(elevator?.artifactDataContract?.modelOutputRules).toContain(
            'score_summary.total_score 由后端根据 score_matrix[].score 求和计算，模型不要输出',
        );
        expect(elevator?.artifactDataContract?.modelOutputRules).toContain(
            'score_summary.average_score 由后端根据 score_matrix[].score 计算并保留 2 位小数，模型不要输出',
        );
        expect(elevator?.artifactDataContract?.modelOutputRules).toContain(
            '如果模型显式输出 score_summary.total_score 或 score_summary.average_score，必须与后端计算结果一致',
        );
        expect(elevator?.artifactDataContract?.forbiddenOutputs).toContain('score-matrix JSON 代码块');
        expect(elevator?.artifactDataContract?.rendererOutputs).toContain('Mermaid flowchart');
        expect(elevator?.artifactDataContract?.rendererOutputs).toContain('ai4se-visual score-matrix');
    });

    it('exposes manifest artifact data contract for VALUE DISCOVERY PERSONA', () => {
        const persona = WORKFLOWS.VALUE_DISCOVERY.stages.find(stage => stage.id === 'PERSONA');

        expect(persona?.artifactDataContract?.modelOutputRules).toContain(
            'personas[].persona_id 必须唯一',
        );
        expect(persona?.artifactDataContract?.modelOutputRules).toContain(
            'behavior_scenarios[].persona_id、decision_chain[].persona_id、pain_evidence[].persona_id、priority_ranking[].persona_id 只能引用 personas[].persona_id 中已定义的画像 ID',
        );
        expect(persona?.artifactDataContract?.modelOutputRules).toContain(
            'priority_ranking[].persona_id 必须唯一',
        );
        expect(persona?.artifactDataContract?.forbiddenOutputs).toContain('完整 Markdown 文档');
        expect(persona?.artifactDataContract?.forbiddenOutputs).toContain('Markdown 表格');
        expect(persona?.artifactDataContract?.rendererOutputs).toContain('右侧用户画像分析');
        expect(persona?.artifactDataContract?.rendererOutputs).toContain(
            '画像、行为场景、决策链、痛点证据、反画像和优先级排序 Markdown 表格',
        );
    });

    it('exposes manifest artifact data contract for VALUE DISCOVERY JOURNEY', () => {
        const journey = WORKFLOWS.VALUE_DISCOVERY.stages.find(stage => stage.id === 'JOURNEY');

        expect(journey?.artifactDataContract?.modelOutputRules).toContain(
            'journey_stages[].stage_id 必须唯一',
        );
        expect(journey?.artifactDataContract?.modelOutputRules).toContain(
            'journey_stages[].pain_id 必须唯一',
        );
        expect(journey?.artifactDataContract?.modelOutputRules).toContain(
            'journey_stages[].opportunity_id 必须唯一',
        );
        expect(journey?.artifactDataContract?.modelOutputRules).toContain(
            'journey_stages[].emotion_score 必须是 1 到 5 的整数',
        );
        expect(journey?.artifactDataContract?.modelOutputRules).toContain(
            'pain_priorities[].stage_id 只能引用 journey_stages[].stage_id 中已定义的旅程阶段 ID',
        );
        expect(journey?.artifactDataContract?.modelOutputRules).toContain(
            'pain_priorities[].pain_id 和 opportunity_scores[].pain_id 只能引用 journey_stages[].pain_id 中已定义的痛点 ID',
        );
        expect(journey?.artifactDataContract?.modelOutputRules).toContain(
            'opportunity_scores[].opportunity_id、entry_strategy[].related_opportunity 和 validation_experiments[].opportunity_id 只能引用 journey_stages[].opportunity_id 中已定义的机会 ID',
        );
        expect(journey?.artifactDataContract?.forbiddenOutputs).toContain('Mermaid 代码块');
        expect(journey?.artifactDataContract?.forbiddenOutputs).toContain('journey-map JSON 代码块');
        expect(journey?.artifactDataContract?.rendererOutputs).toContain('Mermaid journey');
        expect(journey?.artifactDataContract?.rendererOutputs).toContain('ai4se-visual journey-map');
    });

    it('exposes manifest artifact data contract for VALUE DISCOVERY BLUEPRINT', () => {
        const blueprint = WORKFLOWS.VALUE_DISCOVERY.stages.find(stage => stage.id === 'BLUEPRINT');

        expect(blueprint?.artifactDataContract?.modelOutputRules).toContain(
            'requirements[].requirement_id 必须唯一',
        );
        expect(blueprint?.artifactDataContract?.modelOutputRules).toContain(
            'acceptance_criteria[].acceptance_id 必须唯一',
        );
        expect(blueprint?.artifactDataContract?.modelOutputRules).toContain(
            'feature_modules[].features[].requirement_id 如果非空，只能引用 requirements[].requirement_id 中已定义的需求 ID',
        );
        expect(blueprint?.artifactDataContract?.modelOutputRules).toContain(
            'mvp_plan.included_features[].requirement_id 和 acceptance_criteria[].requirement_id 只能引用 requirements[].requirement_id 中已定义的需求 ID',
        );
        expect(blueprint?.artifactDataContract?.modelOutputRules).toContain(
            'lisa_handoff_inputs[] 中 input_type 为“需求”时 reference_id 只能引用 requirements[].requirement_id 中已定义的需求 ID',
        );
        expect(blueprint?.artifactDataContract?.modelOutputRules).toContain(
            'lisa_handoff_inputs[] 中 input_type 为“验收标准”时 reference_id 只能引用 acceptance_criteria[].acceptance_id 中已定义的验收标准 ID',
        );
        expect(blueprint?.artifactDataContract?.modelOutputRules).toContain(
            'main_flow.nodes[].node_id 必须唯一',
        );
        expect(blueprint?.artifactDataContract?.modelOutputRules).toContain(
            'main_flow.links[].from_node 和 main_flow.links[].to_node 只能引用 main_flow.nodes[].node_id 中已定义的流程节点 ID',
        );
        expect(blueprint?.artifactDataContract?.forbiddenOutputs).toContain('roadmap JSON 代码块');
        expect(blueprint?.artifactDataContract?.rendererOutputs).toContain('右侧需求蓝图');
        expect(blueprint?.artifactDataContract?.rendererOutputs).toContain('Mermaid mindmap');
        expect(blueprint?.artifactDataContract?.rendererOutputs).toContain('Mermaid flowchart');
        expect(blueprint?.artifactDataContract?.rendererOutputs).toContain('ai4se-visual roadmap');
    });

    it('exposes manifest artifact data contract for TEST DESIGN CLARIFY', () => {
        const clarify = WORKFLOWS.TEST_DESIGN.stages.find(stage => stage.id === 'CLARIFY');

        expect(clarify?.artifactDataContract?.modelOutputRules).toContain(
            'requirement_facts、system_boundaries、business_rules、flow_links、clarification_questions、quality_requirements、downstream_inputs 和 stage_gate 都必须至少包含 1 条',
        );
        expect(clarify?.artifactDataContract?.modelOutputRules).toContain(
            '所有字符串字段必须是非空白内容',
        );
        expect(clarify?.artifactDataContract?.forbiddenOutputs).toContain('Mermaid 代码块');
        expect(clarify?.artifactDataContract?.rendererOutputs).toContain('右侧需求分析文档');
        expect(clarify?.artifactDataContract?.rendererOutputs).toContain('Mermaid flowchart');
    });

    it('exposes manifest artifact data contract for TEST DESIGN DELIVERY', () => {
        const delivery = WORKFLOWS.TEST_DESIGN.stages.find(stage => stage.id === 'DELIVERY');

        expect(delivery?.artifactDataContract?.modelOutputRules).toContain(
            'case_summary_items[].case_count 必须等于 p0_count + p1_count + p2_count',
        );
        expect(delivery?.artifactDataContract?.modelOutputRules).toContain(
            'delivery_metrics.total_cases 必须等于 case_summary_items[].case_count 总和',
        );
        expect(delivery?.artifactDataContract?.modelOutputRules).toContain(
            'delivery_metrics.high_risk_count 必须等于 open_risks 中 risk_type 包含“风险”且 acceptable != “是”的数量',
        );
        expect(delivery?.artifactDataContract?.modelOutputRules).toContain(
            'coverage_map[].case_ids 必须至少包含 1 个用例 ID',
        );
        expect(delivery?.artifactDataContract?.forbiddenOutputs).toContain('coverage-map JSON 代码块');
        expect(delivery?.artifactDataContract?.rendererOutputs).toContain('右侧测试设计交付包');
        expect(delivery?.artifactDataContract?.rendererOutputs).toContain('ai4se-visual coverage-map');
    });

    it('exposes manifest artifact data contract for REQ REVIEW REVIEW', () => {
        const review = WORKFLOWS.REQ_REVIEW.stages.find(stage => stage.id === 'REVIEW');

        expect(review?.artifactDataContract?.modelOutputRules).toContain(
            'quality_overview[].severity_score 必须是 1 到 5 的整数',
        );
        expect(review?.artifactDataContract?.modelOutputRules).toContain(
            'issue_groups[].issues[].issue_id 必须唯一',
        );
        expect(review?.artifactDataContract?.modelOutputRules).toContain(
            'issue_statistics.p0_count/p1_count/p2_count 必须等于 issue_groups[].issues[].priority 中 P0/P1/P2 的数量',
        );
        expect(review?.artifactDataContract?.modelOutputRules).toContain(
            'revision_suggestions[].related_issues 只能引用 issue_groups[].issues[].issue_id 中已定义的问题 ID',
        );
        expect(review?.artifactDataContract?.forbiddenOutputs).toContain('score-matrix JSON 代码块');
        expect(review?.artifactDataContract?.rendererOutputs).toContain('右侧需求评审问题清单');
        expect(review?.artifactDataContract?.rendererOutputs).toContain('Mermaid flowchart');
        expect(review?.artifactDataContract?.rendererOutputs).toContain('ai4se-visual score-matrix');
    });

    it('exposes manifest artifact data contract for REQ REVIEW REPORT', () => {
        const report = WORKFLOWS.REQ_REVIEW.stages.find(stage => stage.id === 'REPORT');

        expect(report?.artifactDataContract?.modelOutputRules).toContain(
            'issue_closures[].issue_id 必须唯一',
        );
        expect(report?.artifactDataContract?.modelOutputRules).toContain(
            'issue_statistics.p0_count/p1_count/p2_count 必须等于 issue_closures[].priority 中 P0/P1/P2 的数量',
        );
        expect(report?.artifactDataContract?.modelOutputRules).toContain(
            'review_conditions[].related_issues 只能引用 issue_closures[].issue_id 中已定义的问题 ID',
        );
        expect(report?.artifactDataContract?.modelOutputRules).toContain(
            '当存在 closure_status != “已关闭” 的 P0/P1 issue_closures 时，conclusion.review_result 不能为“通过”',
        );
        expect(report?.artifactDataContract?.forbiddenOutputs).toContain('priority-board JSON 代码块');
        expect(report?.artifactDataContract?.rendererOutputs).toContain('右侧需求评审报告');
        expect(report?.artifactDataContract?.rendererOutputs).toContain('Mermaid pie');
        expect(report?.artifactDataContract?.rendererOutputs).toContain('ai4se-visual priority-board');
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
