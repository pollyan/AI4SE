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
});
