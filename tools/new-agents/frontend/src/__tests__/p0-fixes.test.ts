import { describe, it, expect, beforeEach } from 'vitest';
import { useStore, WORKFLOWS } from '../store';
import { buildSystemPrompt } from '../core/prompts/buildSystemPrompt';

describe('P0-4: Stage transition confirmation gate', () => {
    beforeEach(() => {
        useStore.getState().clearHistory();
    });

    it('should set explicit pendingStageTransition without auto-transitioning', () => {
        const state = useStore.getState();
        expect(state.pendingStageTransition).toBeNull();
        expect(state.stageIndex).toBe(0);

        state.setPendingStageTransition({ fromStageIndex: 0, toStageIndex: 1 });

        const updated = useStore.getState();
        expect(updated.pendingStageTransition).toEqual({ fromStageIndex: 0, toStageIndex: 1 });
        // Stage should NOT have advanced
        expect(updated.stageIndex).toBe(0);
    });

    it('should advance stage on confirmStageTransition after pending is set', () => {
        useStore.getState().setArtifactContent('current artifact data');
        useStore.getState().setPendingStageTransition({ fromStageIndex: 0, toStageIndex: 1 });

        useStore.getState().confirmStageTransition();

        const state = useStore.getState();
        expect(state.stageIndex).toBe(1);
        expect(state.pendingStageTransition).toBeNull();
        expect(state.artifactContent).toContain('策略制定');
    });

    it('should clear stale pending transition without rewinding the current stage', () => {
        useStore.getState().setStageIndex(2);
        useStore.getState().setPendingStageTransition({ fromStageIndex: 0, toStageIndex: 1 });

        useStore.getState().confirmStageTransition();

        const state = useStore.getState();
        expect(state.stageIndex).toBe(2);
        expect(state.artifactContent).toContain('用例编写');
        expect(state.pendingStageTransition).toBeNull();
    });

    it('should be a no-op when confirmStageTransition is called without pending flag', () => {
        expect(useStore.getState().stageIndex).toBe(0);
        expect(useStore.getState().pendingStageTransition).toBeNull();

        useStore.getState().confirmStageTransition();

        // Nothing should change
        expect(useStore.getState().stageIndex).toBe(0);
    });

    it('should not advance past the last stage', () => {
        const wf = WORKFLOWS['TEST_DESIGN'];
        const lastStageIndex = wf.stages.length - 1;

        useStore.getState().setStageIndex(lastStageIndex);
        useStore.getState().setPendingStageTransition({ fromStageIndex: lastStageIndex, toStageIndex: lastStageIndex + 1 });
        useStore.getState().confirmStageTransition();

        const state = useStore.getState();
        expect(state.stageIndex).toBe(lastStageIndex);
        expect(state.pendingStageTransition).toBeNull();
    });

    it('should reset pendingStageTransition on clearHistory', () => {
        useStore.getState().setPendingStageTransition({ fromStageIndex: 0, toStageIndex: 1 });
        expect(useStore.getState().pendingStageTransition).toEqual({ fromStageIndex: 0, toStageIndex: 1 });

        useStore.getState().clearHistory();

        expect(useStore.getState().pendingStageTransition).toBeNull();
        expect(useStore.getState().stageIndex).toBe(0);
    });

    it('should clear pendingStageTransition without changing stage', () => {
        useStore.getState().setPendingStageTransition({ fromStageIndex: 0, toStageIndex: 1 });

        useStore.getState().clearPendingStageTransition();

        expect(useStore.getState().pendingStageTransition).toBeNull();
        expect(useStore.getState().stageIndex).toBe(0);
    });

    it('confirmStageTransition should save current stage artifact correctly', () => {
        // Set up: stage 0 has some content
        useStore.getState().setArtifactContent('stage-0-content');

        // Trigger pending
        useStore.getState().setPendingStageTransition({ fromStageIndex: 0, toStageIndex: 1 });

        // Confirm transition
        useStore.getState().confirmStageTransition();

        const state = useStore.getState();
        const currentStageId = WORKFLOWS['TEST_DESIGN'].stages[0].id;
        // The old stage's artifact should be saved
        expect(state.stageArtifacts[currentStageId]).toBe('stage-0-content');
    });
});

describe('P0-9: Artifact truncation state', () => {
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

    it('should not inject previous artifacts context on the first stage', () => {
        const previousStageId = WORKFLOWS['TEST_DESIGN'].stages[0].id;
        const prompt = buildSystemPrompt({
            agentId: 'lisa',
            workflow: 'TEST_DESIGN',
            stageIndex: 0,
            currentArtifact: '# Doc',
            stageArtifacts: {
                [previousStageId]: 'some content',
            },
        });

        expect(prompt).not.toContain('前序阶段有效结论摘要');
    });
});
