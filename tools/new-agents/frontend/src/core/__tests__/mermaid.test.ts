import { describe, it, expect } from 'vitest';
import mermaid from 'mermaid';
import { WORKFLOWS } from '../workflows';

describe('Mermaid Syntax Validation for INCIDENT_REVIEW Workflow', () => {

    // Helper to safely parse syntax (since Mermaid might throw exception straight up instead of returning false)
    const validateMermaid = async (code: string) => {
        mermaid.initialize({ startOnLoad: false, securityLevel: 'loose' });
        try {
            await mermaid.parse(code);
            return true;
        } catch (error) {
            console.error(error);
            return false;
        }
    };

    it('should successfully parse the timeline mermaid syntax from timeline prompt', async () => {
        const promptText = WORKFLOWS.INCIDENT_REVIEW.stages.find(s => s.id === 'TIMELINE')?.template || '';
        const match = promptText.match(/```mermaid\n([\s\S]*?)```/);
        expect(match).toBeTruthy();

        // Remove standard prompt placeholders that invalidates real mermaid syntax
        const rawCode = match![1]
            .replace(/\[故障名称\]/g, '数据库宕机事故')
            .replace(/HH:MM : \[事件描述\]/g, '2023-01-01 : 系统挂了')
            .replace(/\[事件描述\]/g, '系统挂了');

        const isValid = await validateMermaid(rawCode);
        expect(isValid).toBe(true);
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
});
