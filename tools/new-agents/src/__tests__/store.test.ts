import { beforeEach, describe, it, expect } from 'vitest';
import { useStore } from '../store';

describe('Zustand Store', () => {
    beforeEach(() => {
        useStore.getState().clearHistory();
    });

    it('should clear history to defaults', () => {
        const state = useStore.getState();
        state.addMessage({ id: '1', role: 'user', content: 'hello', timestamp: 123 });
        state.setStageIndex(2);

        useStore.getState().clearHistory();
        const newState = useStore.getState();

        expect(newState.chatHistory).toHaveLength(0);
        expect(newState.stageIndex).toBe(0);
    });

    it('should transition to next stage and preserve artifacts', () => {
        useStore.getState().transitionToNextStage(0, 'Stage 0 Data');
        const state = useStore.getState();

        expect(state.stageIndex).toBe(1);
        expect(state.stageArtifacts[0]).toBe('Stage 0 Data');
    });

    it('should switch workflows and clear state', () => {
        useStore.getState().setStageIndex(2);
        useStore.getState().setWorkflow('REQ_REVIEW');
        const state = useStore.getState();

        expect(state.workflow).toBe('REQ_REVIEW');
        expect(state.stageIndex).toBe(0);
    });
});
