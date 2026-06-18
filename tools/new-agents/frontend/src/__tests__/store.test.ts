import { beforeEach, describe, it, expect } from 'vitest';
import { useStore } from '../store';

describe('Zustand Store', () => {
    beforeEach(() => {
        localStorage.removeItem('agent-workspace-storage');
        useStore.getState().clearHistory();
    });

    it('should clear history to defaults', () => {
        const state = useStore.getState();
        state.addMessage({ id: '1', role: 'user', content: 'hello', timestamp: 123 });
        state.setStageIndex(2);
        state.setIsGenerating(true);

        useStore.getState().clearHistory();
        const newState = useStore.getState();

        expect(newState.chatHistory).toHaveLength(0);
        expect(newState.stageIndex).toBe(0);
        expect(newState.isGenerating).toBe(false);
    });

    it('should transition to next stage and preserve artifacts', () => {
        useStore.getState().transitionToNextStage('CLARIFY', 'Stage 0 Data');
        const state = useStore.getState();

        expect(state.stageIndex).toBe(1);
        expect(state.stageArtifacts['CLARIFY']).toBe('Stage 0 Data');
    });

    it('should not reuse the source artifact as the next stage artifact during legacy transitions', () => {
        const clarifyArtifact = '# Clarify-only artifact\n\nThis content belongs to CLARIFY.';
        useStore.getState().setArtifactContent(clarifyArtifact);

        useStore.getState().transitionToNextStage('CLARIFY', clarifyArtifact);

        const state = useStore.getState();
        expect(state.stageIndex).toBe(1);
        expect(state.artifactContent).toBe('# 策略制定\n\n暂无产出物。');
        expect(state.artifactContent).not.toBe(clarifyArtifact);
        expect(state.stageArtifacts.STRATEGY).not.toBe(clarifyArtifact);
    });

    it('should clear derived workflow state when legacy next-stage transition advances', () => {
        useStore.getState().setPendingStageTransition({ fromStageIndex: 0, toStageIndex: 1 });
        useStore.getState().setArtifactTruncated(true);
        useStore.getState().setIsGenerating(true);

        useStore.getState().transitionToNextStage('CLARIFY', '# Clarify artifact');

        const state = useStore.getState();
        expect(state.stageIndex).toBe(1);
        expect(state.pendingStageTransition).toBeNull();
        expect(state.artifactTruncated).toBe(false);
        expect(state.isGenerating).toBe(false);
    });

    it('should ignore out-of-range manual stage switches', () => {
        useStore.getState().setStageIndex(1);
        useStore.getState().setArtifactContent('# Strategy artifact');
        const before = useStore.getState();

        expect(() => useStore.getState().setStageIndex(999)).not.toThrow();

        const after = useStore.getState();
        expect(after.stageIndex).toBe(before.stageIndex);
        expect(after.artifactContent).toBe(before.artifactContent);
        expect(after.stageArtifacts).toEqual(before.stageArtifacts);
    });

    it('should ignore next-stage transitions when already on the final stage', () => {
        const finalStageIndex = 3;
        useStore.getState().setStageIndex(finalStageIndex);
        useStore.getState().setArtifactContent('# Delivery artifact');
        const before = useStore.getState();

        expect(() => {
            useStore.getState().transitionToNextStage('DELIVERY', '# Delivery artifact');
        }).not.toThrow();

        const after = useStore.getState();
        expect(after.stageIndex).toBe(before.stageIndex);
        expect(after.artifactContent).toBe(before.artifactContent);
        expect(after.stageArtifacts).toEqual(before.stageArtifacts);
    });

    it('should ignore next-stage transitions with a source stage outside the active workflow', () => {
        useStore.getState().setArtifactContent('# Clarify artifact');
        const before = useStore.getState();

        useStore.getState().transitionToNextStage('REPORT', '# Cross-workflow source artifact');

        const after = useStore.getState();
        expect(after.stageIndex).toBe(before.stageIndex);
        expect(after.artifactContent).toBe(before.artifactContent);
        expect(after.stageArtifacts).toEqual(before.stageArtifacts);
    });

    it('should clear artifact truncation state when confirming a stage transition', () => {
        useStore.getState().setArtifactTruncated(true);
        useStore.getState().setPendingStageTransition({ fromStageIndex: 0, toStageIndex: 1 });

        useStore.getState().confirmStageTransition();

        const state = useStore.getState();
        expect(state.stageIndex).toBe(1);
        expect(state.pendingStageTransition).toBeNull();
        expect(state.artifactTruncated).toBe(false);
    });

    it('should clear artifact truncation state when manually switching stages', () => {
        useStore.getState().setArtifactTruncated(true);
        useStore.getState().setIsGenerating(true);
        useStore.getState().setStageIndex(1);

        const state = useStore.getState();
        expect(state.stageIndex).toBe(1);
        expect(state.artifactTruncated).toBe(false);
        expect(state.isGenerating).toBe(false);
    });

    it('should clear pending stage transition when manually switching stages', () => {
        useStore.getState().setPendingStageTransition({ fromStageIndex: 0, toStageIndex: 1 });
        useStore.getState().setStageIndex(2);

        const state = useStore.getState();
        expect(state.stageIndex).toBe(2);
        expect(state.pendingStageTransition).toBeNull();
    });

    it('should stamp artifact versions with the current stage id', () => {
        useStore.getState().setStageIndex(1);

        useStore.getState().addArtifactVersion({
            id: 'v1',
            timestamp: 123,
            content: '# Strategy artifact',
        });

        expect(useStore.getState().artifactHistory[0]).toEqual(
            expect.objectContaining({
                stageId: 'STRATEGY',
            })
        );
    });

    it('should switch workflows and clear state', () => {
        useStore.getState().setStageIndex(2);
        useStore.getState().setArtifactTruncated(true);
        useStore.getState().setIsGenerating(true);
        useStore.getState().setWorkflow('REQ_REVIEW');
        const state = useStore.getState();

        expect(state.workflow).toBe('REQ_REVIEW');
        expect(state.stageIndex).toBe(0);
        expect(state.artifactTruncated).toBe(false);
        expect(state.isGenerating).toBe(false);
    });

    it('should ignore stage artifact updates for stages outside the active workflow', () => {
        useStore.getState().setWorkflow('TEST_DESIGN');
        useStore.getState().setStageArtifact('REPORT', '# Cross-workflow artifact');
        useStore.getState().setStageArtifact('UNKNOWN_STAGE', '# Unknown artifact');

        const state = useStore.getState();
        expect(state.workflow).toBe('TEST_DESIGN');
        expect(state.stageArtifacts.REPORT).toBeUndefined();
        expect(state.stageArtifacts.UNKNOWN_STAGE).toBeUndefined();
        expect(Object.keys(state.stageArtifacts)).toEqual(['CLARIFY']);
    });

    it('should drop non-array attachments when hydrating persisted chat history', async () => {
        localStorage.setItem(
            'agent-workspace-storage',
            JSON.stringify({
                state: {
                    workflow: 'TEST_DESIGN',
                    stageIndex: 0,
                    chatHistory: [
                        {
                            id: '1',
                            role: 'user',
                            content: '历史消息',
                            timestamp: 123,
                            attachments: { length: 1 },
                        },
                    ],
                    artifactContent: '# Persisted',
                    artifactHistory: [],
                    stageArtifacts: {
                        CLARIFY: '# Persisted',
                    },
                },
                version: 0,
            })
        );

        await useStore.persist.rehydrate();

        const [message] = useStore.getState().chatHistory;
        expect(message.content).toBe('历史消息');
        expect(message.attachments).toBeUndefined();
    });

    it('should drop malformed attachment entries when hydrating persisted chat history', async () => {
        localStorage.setItem(
            'agent-workspace-storage',
            JSON.stringify({
                state: {
                    workflow: 'TEST_DESIGN',
                    stageIndex: 0,
                    chatHistory: [
                        {
                            id: '1',
                            role: 'user',
                            content: '历史消息',
                            timestamp: 123,
                            attachments: [
                                null,
                                {
                                    name: 'valid.md',
                                    data: 'IyB2YWxpZA==',
                                    mimeType: 'text/markdown',
                                },
                                {
                                    name: 'missing-data.md',
                                    mimeType: 'text/markdown',
                                },
                                {
                                    name: 123,
                                    data: 'abc',
                                    mimeType: 'text/plain',
                                },
                            ],
                        },
                    ],
                    artifactContent: '# Persisted',
                    artifactHistory: [],
                    stageArtifacts: {
                        CLARIFY: '# Persisted',
                    },
                },
                version: 0,
            })
        );

        await useStore.persist.rehydrate();

        const [message] = useStore.getState().chatHistory;
        expect(message.attachments).toEqual([
            {
                name: 'valid.md',
                data: 'IyB2YWxpZA==',
                mimeType: 'text/markdown',
            },
        ]);
    });

    it('should preserve non-retryable assistant metadata when hydrating persisted chat history', async () => {
        localStorage.setItem(
            'agent-workspace-storage',
            JSON.stringify({
                state: {
                    workflow: 'TEST_DESIGN',
                    stageIndex: 1,
                    chatHistory: [
                        {
                            id: '1',
                            role: 'assistant',
                            content: '内部续写生成的新阶段内容',
                            timestamp: 123,
                            retryable: false,
                        },
                    ],
                    artifactContent: '# Persisted',
                    artifactHistory: [],
                    stageArtifacts: {
                        CLARIFY: '# Clarify',
                        STRATEGY: '# Persisted',
                    },
                },
                version: 0,
            })
        );

        await useStore.persist.rehydrate();

        const [message] = useStore.getState().chatHistory;
        expect(message.retryable).toBe(false);
    });

    it('should fall back to default workflow when hydrating an unknown workflow', async () => {
        localStorage.setItem(
            'agent-workspace-storage',
            JSON.stringify({
                state: {
                    workflow: 'UNKNOWN_WORKFLOW',
                    stageIndex: 999,
                    chatHistory: [],
                    artifactContent: '# Broken',
                    artifactHistory: [],
                    stageArtifacts: 'broken',
                },
                version: 0,
            })
        );

        await useStore.persist.rehydrate();

        const state = useStore.getState();
        expect(state.workflow).toBe('TEST_DESIGN');
        expect(state.stageIndex).toBe(0);
        expect(state.artifactContent).toContain('欢迎使用');
        expect(state.stageArtifacts.CLARIFY).toBe(state.artifactContent);
    });

    it('should clamp an out-of-range persisted stage index for a valid workflow', async () => {
        localStorage.setItem(
            'agent-workspace-storage',
            JSON.stringify({
                state: {
                    workflow: 'REQ_REVIEW',
                    stageIndex: 999,
                    chatHistory: [],
                    artifactContent: '# Broken',
                    artifactHistory: [],
                    stageArtifacts: {},
                },
                version: 0,
            })
        );

        await useStore.persist.rehydrate();

        const state = useStore.getState();
        expect(state.workflow).toBe('REQ_REVIEW');
        expect(state.stageIndex).toBe(0);
        expect(state.artifactContent).toContain('欢迎使用');
        expect(state.stageArtifacts.REVIEW).toBe(state.artifactContent);
    });

    it('should restore current artifact content when persisted stage artifacts are missing', async () => {
        localStorage.setItem(
            'agent-workspace-storage',
            JSON.stringify({
                state: {
                    workflow: 'TEST_DESIGN',
                    stageIndex: 0,
                    chatHistory: [],
                    artifactContent: '# Persisted artifact\n\n用户已经生成的需求分析内容',
                    artifactHistory: [],
                    stageArtifacts: {},
                },
                version: 0,
            })
        );

        await useStore.persist.rehydrate();

        const state = useStore.getState();
        expect(state.workflow).toBe('TEST_DESIGN');
        expect(state.stageIndex).toBe(0);
        expect(state.artifactContent).toBe('# Persisted artifact\n\n用户已经生成的需求分析内容');
        expect(state.stageArtifacts.CLARIFY).toBe(state.artifactContent);
    });

    it('should prefer persisted current artifact content over stale current-stage artifact', async () => {
        localStorage.setItem(
            'agent-workspace-storage',
            JSON.stringify({
                state: {
                    workflow: 'TEST_DESIGN',
                    stageIndex: 0,
                    chatHistory: [],
                    artifactContent: '# 最新需求分析\n\n用户刚生成的内容',
                    artifactHistory: [],
                    stageArtifacts: {
                        CLARIFY: '# 旧需求分析',
                    },
                },
                version: 0,
            })
        );

        await useStore.persist.rehydrate();

        const state = useStore.getState();
        expect(state.artifactContent).toBe('# 最新需求分析\n\n用户刚生成的内容');
        expect(state.stageArtifacts.CLARIFY).toBe(state.artifactContent);
    });

    it('should persist and restore artifact truncation state for the current artifact', async () => {
        localStorage.setItem(
            'agent-workspace-storage',
            JSON.stringify({
                state: {
                    workflow: 'TEST_DESIGN',
                    stageIndex: 0,
                    chatHistory: [],
                    artifactContent: '# 截断产物\n\n内容因为模型输出限制被截断',
                    artifactHistory: [],
                    stageArtifacts: {},
                    artifactTruncated: true,
                },
                version: 0,
            })
        );

        await useStore.persist.rehydrate();

        const state = useStore.getState();
        expect(state.artifactContent).toBe('# 截断产物\n\n内容因为模型输出限制被截断');
        expect(state.artifactTruncated).toBe(true);
    });
});
