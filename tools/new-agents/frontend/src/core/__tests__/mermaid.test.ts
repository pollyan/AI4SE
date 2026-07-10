import { describe, it, expect } from 'vitest';
import mermaid from 'mermaid';
import { WORKFLOWS } from '../workflows';
import { parseStructuredVisual } from '../structuredVisuals';
import { sanitizeMermaidCode } from '../utils/mermaidSanitizer';

describe('Mermaid Syntax Validation for workflow prompt examples', () => {

    // Helper to safely parse syntax (since Mermaid might throw exception straight up instead of returning false)
    const validateMermaid = async (code: string) => {
        mermaid.initialize({ startOnLoad: false, securityLevel: 'loose' });
        try {
            await mermaid.parse(code);
            return true;
        } catch {
            return false;
        }
    };

    it('does not expose literal FENCE placeholders in workflow templates', () => {
        const templatesWithLiteralFence = Object.entries(WORKFLOWS)
            .flatMap(([workflowId, workflow]) => (
                workflow.stages
                    .filter((stage) => stage.template.includes('${FENCE}'))
                    .map((stage) => `${workflowId}/${stage.id}`)
            ));

        expect(templatesWithLiteralFence).toEqual([]);
    });

    it.each([
        [
            'flowchart',
            'flowchart TD\n    User["用户"] --> Entry["登录页"]\n    Entry --> Result["工作台"]',
        ],
        [
            'mindmap',
            'mindmap\n  root(("登录问题"))\n    凭证错误\n      密码错误',
        ],
        [
            'pie',
            'pie showData\n    "P0" : 2\n    "P1" : 3',
        ],
        [
            'quadrantChart',
            'quadrantChart\n    title 风险矩阵\n    x-axis 低发生 --> 高发生\n    y-axis 低影响 --> 高影响\n    "验证码绕过": [0.7, 0.8]',
        ],
        [
            'block-beta',
            'block-beta\n    columns 1\n    A["单元测试"]\n    B["集成测试"]\n    A --> B',
        ],
        [
            'journey',
            'journey\n    title 用户旅程\n    section 发现问题\n      提交反馈: 3: 用户',
        ],
    ])('parses backend renderer Mermaid fixture: %s', async (_name, source) => {
        expect(await validateMermaid(sanitizeMermaidCode(source))).toBe(true);
    });

    it('parses a deterministic strategy risk quadrant chart at the maximum coordinate', async () => {
        const source = [
            'quadrantChart',
            '    title 风险优先级矩阵',
            '    x-axis "低发生度" --> "高发生度"',
            '    y-axis "低严重度" --> "高严重度"',
            '    quadrant-1 "紧急处理"',
            '    quadrant-2 "重点关注"',
            '    quadrant-3 "观察监控"',
            '    quadrant-4 "常规覆盖"',
            '    "认证服务不可用": [1, 1]',
        ].join('\n');

        expect(await validateMermaid(sanitizeMermaidCode(source))).toBe(true);
    });

    it('uses timeline-map instead of Mermaid timeline in the timeline prompt', () => {
        const promptText = WORKFLOWS.INCIDENT_REVIEW.stages.find(s => s.id === 'TIMELINE')?.template || '';
        expect(promptText).not.toContain('```mermaid');
        expect(promptText).not.toContain('\ntimeline\n');

        const match = promptText.match(/```ai4se-visual\n([\s\S]*?)```/);
        expect(match).toBeTruthy();
        const result = parseStructuredVisual(match![1]);
        expect(result.valid).toBe(true);
        if (result.valid === false) throw new Error(result.message);
        expect(result.visual.kind).toBe('timeline');
    });

    it('should successfully parse the mindmap mermaid syntax from root_cause prompt', async () => {
        const promptText = WORKFLOWS.INCIDENT_REVIEW.stages.find(s => s.id === 'ROOT_CAUSE')?.template || '';
        const match = promptText.match(/```mermaid\n([\s\S]*?)```/);
        expect(match).toBeTruthy();

        const rawCode = match![1]
            .replace(/\[原因项1\]/g, '没配置环境变量');

        const isValid = await validateMermaid(rawCode);
        expect(isValid).toBe(true);
    });

    it('should successfully parse the pie mermaid syntax from improvement prompt', async () => {
        const promptText = WORKFLOWS.INCIDENT_REVIEW.stages.find(s => s.id === 'IMPROVEMENT')?.template || '';
        const match = promptText.match(/```mermaid\n([\s\S]*?)```/);
        expect(match).toBeTruthy();

        const rawCode = match![1]
            .replace(/\[数量\]/g, '2');

        const isValid = await validateMermaid(rawCode);
        expect(isValid).toBe(true);
    });

    it('should successfully parse the flowchart mermaid syntax from test design clarify prompt', async () => {
        const promptText = WORKFLOWS.TEST_DESIGN.stages.find(s => s.id === 'CLARIFY')?.template || '';
        const match = promptText.match(/```mermaid\n([\s\S]*?)```/);
        expect(match).toBeTruthy();

        const isValid = await validateMermaid(match![1]);
        expect(isValid).toBe(true);
    });

    it('should successfully parse the strategy mermaid syntax from test design strategy prompt', async () => {
        const promptText = WORKFLOWS.TEST_DESIGN.stages.find(s => s.id === 'STRATEGY')?.template || '';
        const matches = Array.from(promptText.matchAll(/```mermaid\n([\s\S]*?)```/g));
        expect(matches).toHaveLength(2);

        const quadrantCode = matches[0][1]
            .replace(/\[风险名称1\]/g, '登录失败锁定')
            .replace(/\[风险名称2\]/g, '验证码绕过')
            .replace(/\[发生度0-1, 严重度0-1\]/g, '[0.7, 0.8]');
        const blockCode = matches[1][1]
            .replace(/占比%/g, '20%');

        expect(await validateMermaid(quadrantCode)).toBe(true);
        expect(await validateMermaid(blockCode)).toBe(true);
    });

    it('should successfully parse the mindmap mermaid syntax from idea brainstorm define prompt', async () => {
        const promptText = WORKFLOWS.IDEA_BRAINSTORM.stages.find(s => s.id === 'DEFINE')?.template || '';
        const match = promptText.match(/```mermaid\n([\s\S]*?)```/);
        expect(match).toBeTruthy();

        const isValid = await validateMermaid(match![1]);
        expect(isValid).toBe(true);
    });
});
