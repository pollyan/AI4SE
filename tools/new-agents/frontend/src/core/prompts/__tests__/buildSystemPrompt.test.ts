import { describe, it, expect } from 'vitest';
import { buildSystemPrompt } from '../buildSystemPrompt';
import { WorkflowType, WORKFLOWS } from '../../../store';

const migratedArtifactDataStages: Array<{
    agentId: string;
    workflow: WorkflowType;
    stageId: string;
}> = [
    { agentId: 'lisa', workflow: 'TEST_DESIGN', stageId: 'CLARIFY' },
    { agentId: 'lisa', workflow: 'TEST_DESIGN', stageId: 'STRATEGY' },
    { agentId: 'lisa', workflow: 'TEST_DESIGN', stageId: 'CASES' },
    { agentId: 'lisa', workflow: 'TEST_DESIGN', stageId: 'DELIVERY' },
    { agentId: 'lisa', workflow: 'REQ_REVIEW', stageId: 'REVIEW' },
    { agentId: 'lisa', workflow: 'REQ_REVIEW', stageId: 'REPORT' },
    { agentId: 'lisa', workflow: 'INCIDENT_REVIEW', stageId: 'TIMELINE' },
    { agentId: 'lisa', workflow: 'INCIDENT_REVIEW', stageId: 'ROOT_CAUSE' },
    { agentId: 'lisa', workflow: 'INCIDENT_REVIEW', stageId: 'IMPROVEMENT' },
    { agentId: 'alex', workflow: 'IDEA_BRAINSTORM', stageId: 'DEFINE' },
    { agentId: 'alex', workflow: 'IDEA_BRAINSTORM', stageId: 'DIVERGE' },
    { agentId: 'alex', workflow: 'IDEA_BRAINSTORM', stageId: 'CONVERGE' },
    { agentId: 'alex', workflow: 'IDEA_BRAINSTORM', stageId: 'CONCEPT' },
    { agentId: 'alex', workflow: 'VALUE_DISCOVERY', stageId: 'ELEVATOR' },
    { agentId: 'alex', workflow: 'VALUE_DISCOVERY', stageId: 'PERSONA' },
    { agentId: 'alex', workflow: 'VALUE_DISCOVERY', stageId: 'JOURNEY' },
    { agentId: 'alex', workflow: 'VALUE_DISCOVERY', stageId: 'BLUEPRINT' },
    { agentId: 'alex', workflow: 'STORY_BREAKDOWN', stageId: 'INPUT_ANALYSIS' },
    { agentId: 'alex', workflow: 'STORY_BREAKDOWN', stageId: 'EPIC_MAPPING' },
    { agentId: 'alex', workflow: 'STORY_BREAKDOWN', stageId: 'STORY_BACKLOG' },
    { agentId: 'alex', workflow: 'STORY_BREAKDOWN', stageId: 'SPRINT_PLAN' },
    { agentId: 'alex', workflow: 'PRD_REVIEW', stageId: 'INVENTORY' },
    { agentId: 'alex', workflow: 'PRD_REVIEW', stageId: 'QUALITY_AUDIT' },
    { agentId: 'alex', workflow: 'PRD_REVIEW', stageId: 'COMPLETION_PLAN' },
    { agentId: 'alex', workflow: 'PRD_REVIEW', stageId: 'REVISION_BLUEPRINT' },
];

describe('buildSystemPrompt', () => {
    it('generates different prompts for different workflows', () => {
        const prompt1 = buildSystemPrompt({
            agentId: 'lisa',
            workflow: 'TEST_DESIGN',
            stageIndex: 0,
            currentArtifact: '',
        });
        const prompt2 = buildSystemPrompt({
            agentId: 'lisa',
            workflow: 'INCIDENT_REVIEW',
            stageIndex: 0,
            currentArtifact: '',
        });
        // Different workflow names should appear
        expect(prompt1).toContain('测试设计');
        expect(prompt2).toContain('故障复盘');
        expect(prompt1).not.toBe(prompt2);
    });

    it('includes correct agent persona for lisa', () => {
        const prompt = buildSystemPrompt({
            agentId: 'lisa',
            workflow: 'TEST_DESIGN',
            stageIndex: 0,
            currentArtifact: '',
        });
        // Lisa persona should be present (it contains Lisa-related content)
        expect(prompt).toContain('Lisa');
    });

    it('includes correct agent persona for alex', () => {
        const prompt = buildSystemPrompt({
            agentId: 'alex',
            workflow: 'IDEA_BRAINSTORM',
            stageIndex: 0,
            currentArtifact: '',
        });
        expect(prompt).toContain('Alex');
    });

    it('rejects unknown agent ids instead of silently falling back to Lisa', () => {
        expect(() => buildSystemPrompt({
            agentId: 'unknown-agent',
            workflow: 'TEST_DESIGN',
            stageIndex: 0,
            currentArtifact: '',
        })).toThrow('Unknown agent persona: unknown-agent');
    });

    it('includes correct stage info', () => {
        const prompt = buildSystemPrompt({
            agentId: 'lisa',
            workflow: 'TEST_DESIGN',
            stageIndex: 0,
            currentArtifact: '',
        });
        const stage = WORKFLOWS['TEST_DESIGN'].stages[0];
        expect(prompt).toContain(stage.name);
        expect(prompt).toContain('当前阶段');
    });

    it('injects the current prompt template version for the active stage', () => {
        const prompt = buildSystemPrompt({
            agentId: 'lisa',
            workflow: 'TEST_DESIGN',
            stageIndex: 1,
            currentArtifact: '# 测试策略蓝图',
        });

        expect(prompt).toContain('【Prompt/template 版本】');
        expect(prompt).toContain('当前阶段版本：2026.06.24.1');
    });

    it('does not include legacy tag-based output protocol instructions', () => {
        const prompt = buildSystemPrompt({
            agentId: 'lisa',
            workflow: 'TEST_DESIGN',
            stageIndex: 0,
            currentArtifact: '# 当前文档\n已有内容',
        });

        expect(prompt).not.toContain('<CHAT>');
        expect(prompt).not.toContain('</CHAT>');
        expect(prompt).not.toContain('<ARTIFACT>');
        expect(prompt).not.toContain('</ARTIFACT>');
        expect(prompt).not.toContain('<ACTION>');
        expect(prompt).not.toContain('</ACTION>');
        expect(prompt).not.toContain('NO_UPDATE');
        expect(prompt).not.toContain('严格按照以下格式输出');
    });

    it('keeps task context and artifact context after removing output protocol details', () => {
        const prompt = buildSystemPrompt({
            agentId: 'lisa',
            workflow: 'TEST_DESIGN',
            stageIndex: 0,
            currentArtifact: '# 当前文档\n已有内容',
        });

        expect(prompt).toContain('当前工作流：测试设计');
        expect(prompt).toContain('当前阶段：需求澄清');
        expect(prompt).toContain('阶段目标：');
        expect(prompt).toContain('# 当前文档\n已有内容');
        expect(prompt).toContain('阶段完成确认');
    });

    it('instructs the model to use the internal next stage id for structured stage actions', () => {
        const prompt = buildSystemPrompt({
            agentId: 'lisa',
            workflow: 'TEST_DESIGN',
            stageIndex: 0,
            currentArtifact: '# 需求分析文档\n已有内容\n\n```mermaid\nflowchart TD\nA-->B\n```',
        });

        expect(prompt).toContain('target_stage_id');
        expect(prompt).toContain('STRATEGY');
        expect(prompt).toContain('策略制定');
        expect(prompt).toContain('不要填写阶段中文名称');
    });

    it('requests the transition confirmation control in the same turn when a stage is complete', () => {
        const prompt = buildSystemPrompt({
            agentId: 'lisa',
            workflow: 'TEST_DESIGN',
            stageIndex: 0,
            currentArtifact: '# 需求分析文档\n已有内容',
        });

        expect(prompt).toContain('同一轮返回 stage_action');
        expect(prompt).toContain('前端显示确认控件');
        expect(prompt).not.toContain('只有当用户在对话中明确回复同意或确认进入下一阶段后');
    });

    it('requires chat to bridge the left conversation and right artifact', () => {
        const prompt = buildSystemPrompt({
            agentId: 'lisa',
            workflow: 'TEST_DESIGN',
            stageIndex: 0,
            currentArtifact: '# 需求分析文档\n已有内容',
        });

        expect(prompt).toContain('左侧对话');
        expect(prompt).toContain('本轮总结');
        expect(prompt).toContain('右侧产出物');
        expect(prompt).toContain('确认后继续');
    });

    it('requires chat to keep a conversational summary with progress, focus, and next step', () => {
        const prompt = buildSystemPrompt({
            agentId: 'lisa',
            workflow: 'TEST_DESIGN',
            stageIndex: 0,
            currentArtifact: '# 需求分析文档\n已有内容',
        });

        expect(prompt).toContain('像一次自然的工作对话');
        expect(prompt).toContain('我本轮已经做了什么');
        expect(prompt).toContain('本轮确认或假定的关键点');
        expect(prompt).toContain('接下来需要用户确认或补充什么');
        expect(prompt).toContain('不要只用一两句模板化提示');
    });

    it('does not ask migrated artifact_data stages to format markdown artifacts', () => {
        const prompt = buildSystemPrompt({
            agentId: 'lisa',
            workflow: 'TEST_DESIGN',
            stageIndex: 0,
            currentArtifact: '# 需求分析文档\n已有内容',
        });

        expect(prompt).not.toContain('<mark>');
        expect(prompt).not.toContain('artifact_update');
        expect(prompt).not.toContain('必须提供完整、全部的 Markdown 文档内容');
        expect(prompt).not.toContain('```markdown');
        expect(prompt).not.toContain('Mermaid');
        expect(prompt).not.toContain('flowchart TD');
        expect(prompt).toContain('当前工作流：测试设计');
        expect(prompt).toContain('当前阶段：需求澄清');
        expect(prompt).toContain('target_stage_id');
    });

    it.each(migratedArtifactDataStages)(
        'keeps $workflow/$stageId in artifact_data prompt mode',
        ({ agentId, workflow, stageId }) => {
            const stageIndex = WORKFLOWS[workflow].stages.findIndex((stage) => stage.id === stageId);
            expect(stageIndex).toBeGreaterThanOrEqual(0);

            const prompt = buildSystemPrompt({
                agentId,
                workflow,
                stageIndex,
                currentArtifact: '# 已渲染产物\n\n```mermaid\nflowchart TD\nA-->B\n```',
            });

            expect(prompt).toContain('结构化业务数据模式');
            expect(prompt).not.toContain('<mark>');
            expect(prompt).not.toContain('artifact_update');
            expect(prompt).not.toContain('必须提供完整、全部的 Markdown 文档内容');
            expect(prompt).not.toContain('```markdown');
            expect(prompt).not.toContain('flowchart TD');
            expect(prompt).not.toContain('Mermaid');
            expect(prompt).toContain(WORKFLOWS[workflow].name);
            expect(prompt).toContain(WORKFLOWS[workflow].stages[stageIndex].name);
        }
    );

    it('injects TEST DESIGN STRATEGY artifact data contract exactly once from the manifest', () => {
        const prompt = buildSystemPrompt({
            agentId: 'lisa',
            workflow: 'TEST_DESIGN',
            stageIndex: 1,
            currentArtifact: '# 测试策略蓝图\n已有内容',
        });

        const rpnRule = 'risks[].rpn 由后端根据 severity * occurrence * detection 计算';
        expect(prompt).toContain('【artifact_data 结构化契约】');
        expect(prompt).toContain(rpnRule);
        expect(prompt).toContain('quality_goals[].goal_id 必须唯一');
        expect(prompt).toContain('test_points.quality_goal、test_points.risk、test_points.technique 只能引用 artifact_data 中已定义的 QG/R/TS ID');
        expect(prompt).toContain('risk-board JSON 代码块');
        expect(prompt).not.toContain('【artifact_data 契约同步约束】');
        const rpnRuleMatches = prompt.match(new RegExp(rpnRule.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g')) ?? [];
        expect(rpnRuleMatches).toHaveLength(1);
    });

    it('injects IDEA BRAINSTORM DEFINE artifact data contract from the manifest', () => {
        const prompt = buildSystemPrompt({
            agentId: 'alex',
            workflow: 'IDEA_BRAINSTORM',
            stageIndex: 0,
            currentArtifact: '# 问题域分析\n已有内容',
        });

        const evidenceRule = 'evidence_items[].evidence_id 必须唯一';
        expect(prompt).toContain('【artifact_data 结构化契约】');
        expect(prompt).toContain(evidenceRule);
        expect(prompt).toContain('problem_landscape.subproblems[].problem_id 必须唯一');
        expect(prompt).toContain('problem_user_fit.evidence_ids 只能引用 evidence_items[].evidence_id 中已定义的证据 ID');
        expect(prompt).toContain('problem_landscape.root_problem 必须被至少一个 evidence_items.related_problem 或 problem_user_fit.evidence_or_assumption 条目覆盖');
        expect(prompt).toContain('图表 代码块');
        expect(prompt).toContain('mindmap 代码块');
        expect(prompt).toContain('图表 mindmap');
        expect(prompt).not.toContain('Mermaid 代码块');
        const evidenceRuleMatches = prompt.match(new RegExp(evidenceRule.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g')) ?? [];
        expect(evidenceRuleMatches).toHaveLength(1);
    });

    it('injects IDEA BRAINSTORM DIVERGE artifact data contract from the manifest', () => {
        const prompt = buildSystemPrompt({
            agentId: 'alex',
            workflow: 'IDEA_BRAINSTORM',
            stageIndex: 1,
            currentArtifact: '# 创意发散\n已有内容',
        });

        const ideaIdRule = 'idea_cards[].idea_id 必须唯一';
        expect(prompt).toContain('【artifact_data 结构化契约】');
        expect(prompt).toContain(ideaIdRule);
        expect(prompt).toContain('idea_sources[].source_id 必须唯一');
        expect(prompt).toContain('parked_or_excluded[].record_id 必须唯一');
        expect(prompt).toContain('idea_landscape.groups[].idea_ids 只能引用 idea_cards[].idea_id 中已定义的创意 ID');
        expect(prompt).toContain('idea_sources[].idea_ids 只能引用 idea_cards[].idea_id 中已定义的创意 ID');
        expect(prompt).toContain('stage_gate 至少包含一个 checked=true');
        expect(prompt).toContain('图表 代码块');
        expect(prompt).toContain('mindmap 代码块');
        expect(prompt).toContain('右侧创意发散产物');
        expect(prompt).toContain('图表 mindmap');
        expect(prompt).not.toContain('Mermaid 代码块');
        const ideaIdRuleMatches = prompt.match(new RegExp(ideaIdRule.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g')) ?? [];
        expect(ideaIdRuleMatches).toHaveLength(1);
    });

    it('injects IDEA BRAINSTORM CONCEPT artifact data contract from the manifest', () => {
        const prompt = buildSystemPrompt({
            agentId: 'alex',
            workflow: 'IDEA_BRAINSTORM',
            stageIndex: 3,
            currentArtifact: '# 产品概念简报\n已有内容',
        });

        const assumptionIdRule = 'core_assumptions[].assumption_id 必须唯一';
        expect(prompt).toContain('【artifact_data 结构化契约】');
        expect(prompt).toContain(assumptionIdRule);
        expect(prompt).toContain('validation_roadmap[].validation_id 必须唯一');
        expect(prompt).toContain('next_actions[].action_id 必须唯一');
        expect(prompt).toContain('lean_canvas.cell 必须覆盖问题、用户群体、独特价值主张、解决方案、渠道、收入来源、成本结构、关键指标、竞争壁垒');
        expect(prompt).toContain('growth_funnel.stage 必须覆盖 Acquisition、Activation、Retention、Revenue、Referral');
        expect(prompt).toContain('mvp_features[].assumption_ids 只能引用 core_assumptions[].assumption_id 中已定义的假设 ID');
        expect(prompt).toContain('validation_roadmap[].assumption_ids 只能引用 core_assumptions[].assumption_id 中已定义的假设 ID');
        expect(prompt).toContain('next_actions[].related_ids 只能引用 core_assumptions[].assumption_id、validation_roadmap[].validation_id 或 premortem_risks[].risk_id 中已定义的 ID');
        expect(prompt).toContain('stage_gate 至少包含一个 checked=true');
        expect(prompt).toContain('mvp-map JSON 代码块');
        expect(prompt).toContain('右侧产品概念简报');
        expect(prompt).toContain('ai4se-visual mvp-map');
        expect(prompt).toContain('图表 pie');
        expect(prompt).toContain('图表 flowchart');
        expect(prompt).not.toContain('Mermaid 代码块');
        const assumptionIdRuleMatches = prompt.match(new RegExp(assumptionIdRule.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g')) ?? [];
        expect(assumptionIdRuleMatches).toHaveLength(1);
    });

    it('injects VALUE DISCOVERY ELEVATOR artifact data contract from the manifest', () => {
        const prompt = buildSystemPrompt({
            agentId: 'alex',
            workflow: 'VALUE_DISCOVERY',
            stageIndex: 0,
            currentArtifact: '# 价值定位分析\n已有内容',
        });

        const nodeIdRule = 'value_flow.nodes[].node_id 必须唯一';
        expect(prompt).toContain('【artifact_data 结构化契约】');
        expect(prompt).toContain(nodeIdRule);
        expect(prompt).toContain('value_flow.links[].from_node 和 value_flow.links[].to_node 只能引用 value_flow.nodes[].node_id 中已定义的节点 ID');
        expect(prompt).toContain('score_matrix[].score 必须是 1 到 5 的整数');
        expect(prompt).toContain('score_summary.total_score 由后端根据 score_matrix[].score 求和计算，模型不要输出');
        expect(prompt).toContain('score_summary.average_score 由后端根据 score_matrix[].score 计算并保留 2 位小数，模型不要输出');
        expect(prompt).toContain('如果模型显式输出 score_summary.total_score 或 score_summary.average_score，必须与后端计算结果一致');
        expect(prompt).toContain('图表 代码块');
        expect(prompt).toContain('score-matrix JSON 代码块');
        expect(prompt).toContain('右侧价值定位分析');
        expect(prompt).toContain('图表 flowchart');
        expect(prompt).toContain('ai4se-visual score-matrix');
        expect(prompt).not.toContain('Mermaid 代码块');
        const nodeIdRuleMatches = prompt.match(new RegExp(nodeIdRule.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g')) ?? [];
        expect(nodeIdRuleMatches).toHaveLength(1);
    });

    it('injects VALUE DISCOVERY PERSONA artifact data contract from the manifest', () => {
        const prompt = buildSystemPrompt({
            agentId: 'alex',
            workflow: 'VALUE_DISCOVERY',
            stageIndex: 1,
            currentArtifact: '# 用户画像分析\n已有内容',
        });

        const personaIdRule = 'personas[].persona_id 必须唯一';
        expect(prompt).toContain('【artifact_data 结构化契约】');
        expect(prompt).toContain(personaIdRule);
        expect(prompt).toContain('behavior_scenarios[].persona_id、decision_chain[].persona_id、pain_evidence[].persona_id、priority_ranking[].persona_id 只能引用 personas[].persona_id 中已定义的画像 ID');
        expect(prompt).toContain('priority_ranking[].persona_id 必须唯一');
        expect(prompt).toContain('完整 Markdown 文档');
        expect(prompt).toContain('Markdown 表格');
        expect(prompt).toContain('右侧用户画像分析');
        expect(prompt).toContain('画像、行为场景、决策链、痛点证据、反画像和优先级排序 Markdown 表格');
        const personaIdRuleMatches = prompt.match(new RegExp(personaIdRule.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g')) ?? [];
        expect(personaIdRuleMatches).toHaveLength(1);
    });

    it('injects VALUE DISCOVERY JOURNEY artifact data contract from the manifest', () => {
        const prompt = buildSystemPrompt({
            agentId: 'alex',
            workflow: 'VALUE_DISCOVERY',
            stageIndex: 2,
            currentArtifact: '# 用户旅程分析\n已有内容',
        });

        const stageIdRule = 'journey_stages[].stage_id 必须唯一';
        expect(prompt).toContain('【artifact_data 结构化契约】');
        expect(prompt).toContain(stageIdRule);
        expect(prompt).toContain('journey_stages[].pain_id 必须唯一');
        expect(prompt).toContain('journey_stages[].opportunity_id 必须唯一');
        expect(prompt).toContain('journey_stages[].emotion_score 必须是 1 到 5 的整数');
        expect(prompt).toContain('pain_priorities[].stage_id 只能引用 journey_stages[].stage_id 中已定义的旅程阶段 ID');
        expect(prompt).toContain('pain_priorities[].pain_id 和 opportunity_scores[].pain_id 只能引用 journey_stages[].pain_id 中已定义的痛点 ID');
        expect(prompt).toContain('opportunity_scores[].opportunity_id、entry_strategy[].related_opportunity 和 validation_experiments[].opportunity_id 只能引用 journey_stages[].opportunity_id 中已定义的机会 ID');
        expect(prompt).toContain('图表 代码块');
        expect(prompt).toContain('journey-map JSON 代码块');
        expect(prompt).toContain('右侧用户旅程分析');
        expect(prompt).toContain('图表 journey');
        expect(prompt).toContain('ai4se-visual journey-map');
        expect(prompt).not.toContain('Mermaid 代码块');
        const stageIdRuleMatches = prompt.match(new RegExp(stageIdRule.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g')) ?? [];
        expect(stageIdRuleMatches).toHaveLength(1);
    });

    it('describes story breakdown work without markdown direct-write instructions', () => {
        const prompt = buildSystemPrompt({
            agentId: 'alex',
            workflow: 'STORY_BREAKDOWN',
            stageIndex: 2,
            currentArtifact: '# 用户故事拆解包\n已有内容',
        });

        expect(prompt).toContain('用户故事拆解');
        expect(prompt).toContain('User Story Backlog');
        expect(prompt).toContain('验收标准');
        expect(prompt).toContain('Sprint 切片');
        expect(prompt).toContain('Lisa Handoff');
        expect(prompt).toContain('结构化业务数据模式');
        expect(prompt).not.toContain('artifact_update');
        expect(prompt).not.toContain('必须提供完整、全部的 Markdown 文档内容');
    });

    it('keeps next-stage confirmation separate from next-stage artifact generation', () => {
        const prompt = buildSystemPrompt({
            agentId: 'lisa',
            workflow: 'TEST_DESIGN',
            stageIndex: 0,
            currentArtifact: '# 需求分析文档\n已有内容',
        });

        expect(prompt).toContain('不要在同一轮准备下一阶段业务数据');
        expect(prompt).not.toContain('继续返回当前阶段的完整产出物');
    });

    it('allows the test design clarify stage to assume a scenario when the user asks for one', () => {
        const prompt = buildSystemPrompt({
            agentId: 'lisa',
            workflow: 'TEST_DESIGN',
            stageIndex: 0,
            currentArtifact: '# 需求分析文档\n已有内容',
        });

        expect(prompt).toContain('用户要求你代为设定场景');
        expect(prompt).toContain('直接设定一个合理、可测试、可推进的默认场景');
    });

    it('injects previous stage artifacts when generating a later non-final stage', () => {
        const prompt = buildSystemPrompt({
            agentId: 'lisa',
            workflow: 'TEST_DESIGN',
            stageIndex: 1,
            currentArtifact: '# 测试策略蓝图',
            stageArtifacts: {
                CLARIFY: '# 需求分析文档\n\n关键需求事实',
            },
        });

        expect(prompt).toContain('前序阶段有效结论摘要');
        expect(prompt).toContain('阶段 [CLARIFY] 核心成果');
        expect(prompt).toContain('关键需求事实');
    });

    it('removes mark tags from previous stage artifacts while preserving marked text', () => {
        const prompt = buildSystemPrompt({
            agentId: 'lisa',
            workflow: 'TEST_DESIGN',
            stageIndex: 1,
            currentArtifact: '# 测试策略蓝图',
            stageArtifacts: {
                CLARIFY: '# 需求分析文档\n\n已确认 <mark>登录链路</mark> 的核心边界',
            },
        });

        const previousContextStart = prompt.indexOf('【前序阶段有效结论摘要】');
        const previousContextEnd = prompt.indexOf('要求：基于上述前置阶段', previousContextStart);
        const previousContext = prompt.slice(previousContextStart, previousContextEnd);

        expect(previousContext).toContain('登录链路');
        expect(previousContext).not.toContain('<mark>');
        expect(previousContext).not.toContain('</mark>');
    });

    it('does not inject future stage artifacts into previous stage context', () => {
        const prompt = buildSystemPrompt({
            agentId: 'lisa',
            workflow: 'TEST_DESIGN',
            stageIndex: 1,
            currentArtifact: '# 测试策略蓝图',
            stageArtifacts: {
                CLARIFY: '# 需求分析文档\n\n已确认登录和支付边界',
                CASES: '# 测试用例集\n\n未来阶段用例内容',
                DELIVERY: '# 测试设计文档\n\n未来交付内容',
            },
        });

        expect(prompt).toContain('阶段 [CLARIFY] 核心成果');
        expect(prompt).toContain('已确认登录和支付边界');
        expect(prompt).not.toContain('阶段 [CASES] 核心成果');
        expect(prompt).not.toContain('未来阶段用例内容');
        expect(prompt).not.toContain('阶段 [DELIVERY] 核心成果');
        expect(prompt).not.toContain('未来交付内容');
    });

    it('does not include Mermaid rendering repair instructions', () => {
        const prompt = buildSystemPrompt({
            agentId: 'lisa',
            workflow: 'TEST_DESIGN',
            stageIndex: 0,
            currentArtifact: '# 当前文档\n已有内容',
        });

        expect(prompt).not.toContain('Mermaid 分段强制约束');
        expect(prompt).not.toContain('前端崩溃');
        expect(prompt).not.toContain('<br/>');
        expect(prompt).not.toContain('${FENCE}');
        expect(prompt).not.toContain('特殊字符包裹');
        expect(prompt).not.toContain('围栏格式');
    });

    it('does not inject TEST_DESIGN artifact template structure into the system prompt', () => {
        const prompt = buildSystemPrompt({
            agentId: 'lisa',
            workflow: 'TEST_DESIGN',
            stageIndex: 0,
            currentArtifact: '# 当前文档\n已有内容',
        });

        expect(prompt).not.toContain('产出物强制结构');
        expect(prompt).not.toContain('唯一合法的产出物格式');
        expect(prompt).not.toContain('禁止增删章节标题');
        expect(prompt).not.toContain('## 1. 被测系统与边界');
        expect(prompt).not.toContain('## 3. 待澄清与阻断性问题');
    });

    it('does not inject REQ_REVIEW artifact template structure into the system prompt', () => {
        const prompt = buildSystemPrompt({
            agentId: 'lisa',
            workflow: 'REQ_REVIEW',
            stageIndex: 0,
            currentArtifact: '# 当前文档\n已有内容',
        });

        expect(prompt).not.toContain('产出物强制结构');
        expect(prompt).not.toContain('唯一合法的产出物格式');
        expect(prompt).not.toContain('禁止增删章节标题');
        expect(prompt).not.toContain('## 评审概要');
        expect(prompt).not.toContain('## 问题统计');
    });

    it('does not inject INCIDENT_REVIEW artifact template structure into the system prompt', () => {
        const prompt = buildSystemPrompt({
            agentId: 'lisa',
            workflow: 'INCIDENT_REVIEW',
            stageIndex: 0,
            currentArtifact: '# 当前文档\n已有内容',
        });

        expect(prompt).not.toContain('产出物强制结构');
        expect(prompt).not.toContain('唯一合法的产出物格式');
        expect(prompt).not.toContain('禁止增删章节标题');
        expect(prompt).not.toContain('## 1. 事件概要');
        expect(prompt).not.toContain('## 2. 事件时间线');
    });

    it('does not inject IDEA_BRAINSTORM artifact template structure into the system prompt', () => {
        const prompt = buildSystemPrompt({
            agentId: 'alex',
            workflow: 'IDEA_BRAINSTORM',
            stageIndex: 0,
            currentArtifact: '# 当前文档\n已有内容',
        });

        expect(prompt).not.toContain('产出物强制结构');
        expect(prompt).not.toContain('唯一合法的产出物格式');
        expect(prompt).not.toContain('禁止增删章节标题');
        expect(prompt).not.toContain('## 问题假设陈述');
        expect(prompt).not.toContain('## 目标用户画像');
    });

    it('does not inject VALUE_DISCOVERY artifact template structure into the system prompt', () => {
        const prompt = buildSystemPrompt({
            agentId: 'alex',
            workflow: 'VALUE_DISCOVERY',
            stageIndex: 0,
            currentArtifact: '# 当前文档\n已有内容',
        });

        expect(prompt).not.toContain('产出物强制结构');
        expect(prompt).not.toContain('唯一合法的产出物格式');
        expect(prompt).not.toContain('禁止增删章节标题');
        expect(prompt).not.toContain('## 产品核心定位');
        expect(prompt).not.toContain('## 目标用户概览');
    });

    it('injects professional method guidance for configured Lisa strategy stages', () => {
        const prompt = buildSystemPrompt({
            agentId: 'lisa',
            workflow: 'TEST_DESIGN',
            stageIndex: 1,
            currentArtifact: '# 测试策略蓝图',
        });

        expect(prompt).toContain('【专业方法参考】');
        expect(prompt).toContain('FMEA 失效模式与影响分析');
        expect(prompt).toContain('测试金字塔');
        expect(prompt).toContain('风险优先级');
    });

    it('injects product discovery methods for configured Alex journey stages', () => {
        const prompt = buildSystemPrompt({
            agentId: 'alex',
            workflow: 'VALUE_DISCOVERY',
            stageIndex: 2,
            currentArtifact: '# 用户旅程分析',
        });

        expect(prompt).toContain('【专业方法参考】');
        expect(prompt).toContain('JTBD 任务理论');
        expect(prompt).toContain('RICE 优先级评分');
        expect(prompt).toContain('Kano 需求分层');
    });

    it('does not inject an empty professional method section for stages without method ids', () => {
        const prompt = buildSystemPrompt({
            agentId: 'lisa',
            workflow: 'TEST_DESIGN',
            stageIndex: 0,
            currentArtifact: '# 需求分析文档',
        });

        expect(prompt).not.toContain('【专业方法参考】');
    });
});
