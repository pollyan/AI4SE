import { describe, it, expect } from 'vitest';
import { buildSystemPrompt } from '../buildSystemPrompt';
import { WORKFLOWS } from '../../../store';

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
            currentArtifact: '# 需求分析文档\n已有内容',
        });

        expect(prompt).toContain('target_stage_id');
        expect(prompt).toContain('STRATEGY');
        expect(prompt).toContain('策略制定');
        expect(prompt).toContain('不要填写阶段中文名称');
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

    it('keeps next-stage confirmation separate from next-stage artifact generation', () => {
        const prompt = buildSystemPrompt({
            agentId: 'lisa',
            workflow: 'TEST_DESIGN',
            stageIndex: 0,
            currentArtifact: '# 需求分析文档\n已有内容',
        });

        expect(prompt).toContain('不要在同一轮生成下一阶段产出物');
        expect(prompt).toContain('继续返回当前阶段的完整产出物');
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
});
