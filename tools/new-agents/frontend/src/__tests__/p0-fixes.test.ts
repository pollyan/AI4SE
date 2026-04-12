import { describe, it, expect, beforeEach } from 'vitest';
import { useStore, WORKFLOWS } from '../store';
import { detectArtifactTruncation, parseLlmStreamChunk } from '../core/utils/llmParser';
import { buildSystemPrompt } from '../core/prompts/buildSystemPrompt';

describe('P0-4: Stage transition confirmation gate', () => {
    beforeEach(() => {
        useStore.getState().clearHistory();
    });

    it('should set pendingStageTransition=true without auto-transitioning', () => {
        const state = useStore.getState();
        expect(state.pendingStageTransition).toBe(false);
        expect(state.stageIndex).toBe(0);

        state.setPendingStageTransition(true);

        const updated = useStore.getState();
        expect(updated.pendingStageTransition).toBe(true);
        // Stage should NOT have advanced
        expect(updated.stageIndex).toBe(0);
    });

    it('should advance stage on confirmStageTransition after pending is set', () => {
        useStore.getState().setArtifactContent('current artifact data');
        useStore.getState().setPendingStageTransition(true);

        useStore.getState().confirmStageTransition();

        const state = useStore.getState();
        expect(state.stageIndex).toBe(1);
        expect(state.pendingStageTransition).toBe(false);
    });

    it('should be a no-op when confirmStageTransition is called without pending flag', () => {
        expect(useStore.getState().stageIndex).toBe(0);
        expect(useStore.getState().pendingStageTransition).toBe(false);

        useStore.getState().confirmStageTransition();

        // Nothing should change
        expect(useStore.getState().stageIndex).toBe(0);
    });

    it('should not advance past the last stage', () => {
        const wf = WORKFLOWS['TEST_DESIGN'];
        const lastStageIndex = wf.stages.length - 1;

        useStore.getState().setStageIndex(lastStageIndex);
        useStore.getState().setPendingStageTransition(true);
        useStore.getState().confirmStageTransition();

        const state = useStore.getState();
        expect(state.stageIndex).toBe(lastStageIndex);
        expect(state.pendingStageTransition).toBe(false);
    });

    it('should reset pendingStageTransition on clearHistory', () => {
        useStore.getState().setPendingStageTransition(true);
        expect(useStore.getState().pendingStageTransition).toBe(true);

        useStore.getState().clearHistory();

        expect(useStore.getState().pendingStageTransition).toBe(false);
        expect(useStore.getState().stageIndex).toBe(0);
    });

    it('confirmStageTransition should save current stage artifact correctly', () => {
        // Set up: stage 0 has some content
        useStore.getState().setArtifactContent('stage-0-content');

        // Trigger pending
        useStore.getState().setPendingStageTransition(true);

        // Confirm transition
        useStore.getState().confirmStageTransition();

        const state = useStore.getState();
        const currentStageId = WORKFLOWS['TEST_DESIGN'].stages[0].id;
        // The old stage's artifact should be saved
        expect(state.stageArtifacts[currentStageId]).toBe('stage-0-content');
    });
});

describe('P0-9: Artifact truncation detection', () => {
    it('should detect truncation when ARTIFACT opens but never closes', () => {
        const text = '<CHAT>Hello</CHAT>\n<ARTIFACT>\n# Some doc\ncontent...';
        expect(detectArtifactTruncation(text)).toBe(true);
    });

    it('should not detect truncation when ARTIFACT is properly closed', () => {
        const text = '<CHAT>Hello</CHAT>\n<ARTIFACT>\n# Some doc\ncontent...\n</ARTIFACT>';
        expect(detectArtifactTruncation(text)).toBe(false);
    });

    it('should not detect truncation when no ARTIFACT tag exists', () => {
        const text = '<CHAT>Hello</CHAT>';
        expect(detectArtifactTruncation(text)).toBe(false);
    });

    it('should detect truncation with case-insensitive tags', () => {
        const text = '<artifact>\n# Content';
        expect(detectArtifactTruncation(text)).toBe(true);
    });

    it('should handle artifactTruncated state in store', () => {
        expect(useStore.getState().artifactTruncated).toBe(false);

        useStore.getState().setArtifactTruncated(true);
        expect(useStore.getState().artifactTruncated).toBe(true);

        useStore.getState().setArtifactTruncated(false);
        expect(useStore.getState().artifactTruncated).toBe(false);
    });

    it('should reset artifactTruncated on clearHistory', () => {
        useStore.getState().setArtifactTruncated(true);
        expect(useStore.getState().artifactTruncated).toBe(true);

        useStore.getState().clearHistory();
        expect(useStore.getState().artifactTruncated).toBe(false);
    });
});

describe('P0-8: buildSystemPrompt 5000-char truncation threshold', () => {
    it('should truncate artifacts exceeding 5000 chars in last stage', () => {
        const wf = WORKFLOWS['TEST_DESIGN'];
        const lastStageIndex = wf.stages.length - 1;

        // Create a long artifact for a previous stage
        const longContent = 'X'.repeat(6000);
        const previousStageId = wf.stages[0].id;

        const prompt = buildSystemPrompt({
            agentId: 'lisa',
            workflow: 'TEST_DESIGN',
            stageIndex: lastStageIndex,
            currentArtifact: '# Current Doc',
            stageArtifacts: {
                [previousStageId]: longContent,
            },
        });

        // Should contain truncation marker
        expect(prompt).toContain('已截断');
        expect(prompt).toContain('6000');
        expect(prompt).toContain('5000');
        // Should NOT contain the full 6000 chars of the artifact
        expect(prompt).not.toContain(longContent);
    });

    it('should NOT truncate artifacts within 5000 chars', () => {
        const wf = WORKFLOWS['TEST_DESIGN'];
        const lastStageIndex = wf.stages.length - 1;
        const shortContent = 'Short content under limit';
        const previousStageId = wf.stages[0].id;

        const prompt = buildSystemPrompt({
            agentId: 'lisa',
            workflow: 'TEST_DESIGN',
            stageIndex: lastStageIndex,
            currentArtifact: '# Current Doc',
            stageArtifacts: {
                [previousStageId]: shortContent,
            },
        });

        expect(prompt).toContain(shortContent);
        expect(prompt).not.toContain('已截断');
    });

    it('should not inject previous artifacts context when not on last stage', () => {
        const previousStageId = WORKFLOWS['TEST_DESIGN'].stages[0].id;
        const prompt = buildSystemPrompt({
            agentId: 'lisa',
            workflow: 'TEST_DESIGN',
            stageIndex: 0, // Not last stage
            currentArtifact: '# Doc',
            stageArtifacts: {
                [previousStageId]: 'some content',
            },
        });

        expect(prompt).not.toContain('前序阶段有效结论摘要');
    });
});

describe('parseLlmStreamChunk integration', () => {
    it('should parse ARTIFACT with NO_UPDATE as no update', () => {
        const result = parseLlmStreamChunk(
            '<CHAT>Done</CHAT>\n<ARTIFACT>NO_UPDATE</ARTIFACT>',
            'current artifact'
        );
        expect(result.hasArtifactUpdate).toBe(false);
        expect(result.newArtifact).toBe('current artifact');
    });

    it('should detect artifact update from ARTIFACT tag', () => {
        const result = parseLlmStreamChunk(
            '<CHAT>Updated</CHAT>\n<ARTIFACT>\n# New Content\n</ARTIFACT>',
            'old artifact'
        );
        expect(result.hasArtifactUpdate).toBe(true);
        expect(result.newArtifact).toContain('# New Content');
    });
});
