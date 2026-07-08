import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useChatService } from '../chatService';
import { getWelcomeMessage, useStore } from '../../store';
import { generateResponseStream } from '../../core/llm';

// Mock the LLM service to avoid making real API calls during tests
vi.mock('../../core/llm', () => ({
    generateResponseStream: vi.fn()
}));

describe('useChatService', () => {
    beforeEach(() => {
        // Reset our Zustand store before each test
        const store = useStore.getState();
        useStore.setState({
            chatHistory: [],
            artifactContent: 'initial artifact',
            artifactChangeIndex: [],
            artifactHistory: [],
            artifactComments: [],
            artifactSectionLocks: [],
            stageArtifacts: {
                CLARIFY: 'initial artifact',
            },
            stageIndex: 0,
            workflow: 'TEST_DESIGN',
            isGenerating: false,
            pendingStageTransition: null,
        });
        vi.clearAllMocks();
    });

    it('should initialize with empty input and no attachments', () => {
        const { result } = renderHook(() => useChatService());
        expect(result.current.input).toBe('');
        expect(result.current.pendingAttachments.length).toBe(0);
    });

    it('should update input text', () => {
        const { result } = renderHook(() => useChatService());
        act(() => {
            result.current.setInput('New message');
        });
        expect(result.current.input).toBe('New message');
    });

    it('should not default unknown uploaded file types to text/plain', async () => {
        const { result } = renderHook(() => useChatService());
        const file = new File(['fake png bytes'], 'screen.png', { type: '' });
        const files = {
            0: file,
            length: 1,
            item: (index: number) => (index === 0 ? file : null),
        } as unknown as FileList;

        act(() => {
            result.current.handleFileChange(files);
        });

        await waitFor(() => {
            expect(result.current.pendingAttachments).toEqual([
                expect.objectContaining({
                    name: 'screen.png',
                    mimeType: 'application/octet-stream',
                }),
            ]);
        });
    });

    it('should not send if input is empty and no attachments', async () => {
        const { result } = renderHook(() => useChatService());
        await act(async () => {
            await result.current.handleSend();
        });
        const state = useStore.getState();
        expect(state.chatHistory.length).toBe(0);
        expect(state.isGenerating).toBe(false);
    });

    it('should handle LLM stream and update chat history and artifacts', async () => {
        vi.mocked(generateResponseStream).mockImplementation(async function* () {
            yield { chatResponse: 'Hello world', newArtifact: 'new artifact content', action: 'NONE', hasArtifactUpdate: true };
        });

        const { result } = renderHook(() => useChatService());

        act(() => {
            result.current.setInput('simulate user request');
        });

        await act(async () => {
            await result.current.handleSend();
        });

        const state = useStore.getState();

        expect(state.chatHistory.length).toBe(2);
        expect(state.chatHistory[0].content).toBe('simulate user request');
        expect(state.chatHistory[0].role).toBe('user');

        expect(state.chatHistory[1].content).toBe('Hello world');
        expect(state.chatHistory[1].role).toBe('assistant');

        expect(result.current.input).toBe('');
        expect(state.artifactContent).toBe('new artifact content');
    });

    it('applies matching artifact patches from the stream before falling back to full replacement', async () => {
        const base = '# 文档\n\n## 范围\n\n旧范围\n\n## 风险\n\n保持不变';
        useStore.setState({
            artifactContent: base,
            stageArtifacts: { CLARIFY: base },
        });
        const patch = {
            operation: 'replace' as const,
            sectionAnchor: 'h2:范围:1',
            replacementMarkdown: '## 范围\n\n新范围',
            baseContent: base,
        };
        const patchSpy = vi.spyOn(useStore.getState(), 'applyArtifactSectionPatch');
        vi.mocked(generateResponseStream).mockImplementation(async function* () {
            yield {
                chatResponse: '已局部更新',
                newArtifact: '# 文档\n\n## 范围\n\n新范围\n\n## 风险\n\n保持不变',
                action: '',
                hasArtifactUpdate: true,
                artifactPatch: patch,
            };
        });

        const { result } = renderHook(() => useChatService());
        act(() => result.current.setInput('更新范围'));

        await act(async () => {
            await result.current.handleSend();
        });

        expect(patchSpy).toHaveBeenCalledWith(patch);
        expect(useStore.getState().artifactContent).toBe('# 文档\n\n## 范围\n\n新范围\n\n## 风险\n\n保持不变');
        expect(useStore.getState().artifactChangeIndex).toEqual([
            expect.objectContaining({ anchor: 'h2:范围:1' }),
        ]);
        patchSpy.mockRestore();
    });

    it('applies add_after artifact patches from the stream', async () => {
        const base = '# 文档\n\n## 范围\n\n旧范围';
        const fullArtifact = '# 文档\n\n## 范围\n\n旧范围\n\n## 风险\n\n| 风险 | 状态 |\n| --- | --- |\n| R1 | 待处理 |';
        useStore.setState({
            artifactContent: base,
            stageArtifacts: { CLARIFY: base },
        });
        vi.mocked(generateResponseStream).mockImplementation(async function* () {
            yield {
                chatResponse: '已追加风险章节',
                newArtifact: fullArtifact,
                action: '',
                hasArtifactUpdate: true,
                artifactPatch: {
                    operation: 'add_after',
                    sectionAnchor: 'h2:风险:1',
                    afterSectionAnchor: 'h2:范围:1',
                    replacementMarkdown: '## 风险\n\n| 风险 | 状态 |\n| --- | --- |\n| R1 | 待处理 |',
                    baseContent: base,
                },
            };
        });

        const { result } = renderHook(() => useChatService());
        act(() => result.current.setInput('追加风险'));

        await act(async () => {
            await result.current.handleSend();
        });

        expect(useStore.getState().artifactContent).toBe(fullArtifact);
        expect(useStore.getState().artifactChangeIndex).toEqual([
            expect.objectContaining({
                kind: 'added',
                anchor: 'h2:风险:1',
            }),
        ]);
    });

    it('falls back to full markdown when artifact patch result does not match the full artifact', async () => {
        const base = '# 文档\n\n## 范围\n\n旧范围\n\n## 风险\n\n旧风险';
        const fullFallback = '# 文档\n\n## 范围\n\n旧范围\n\n## 风险\n\n完整替换结果';
        useStore.setState({
            artifactContent: base,
            stageArtifacts: { CLARIFY: base },
        });
        vi.mocked(generateResponseStream).mockImplementation(async function* () {
            yield {
                chatResponse: '已更新',
                newArtifact: fullFallback,
                action: '',
                hasArtifactUpdate: true,
                artifactPatch: {
                    operation: 'replace',
                    sectionAnchor: 'h2:范围:1',
                    replacementMarkdown: '## 范围\n\n局部结果',
                    baseContent: base,
                },
            };
        });

        const { result } = renderHook(() => useChatService());
        act(() => result.current.setInput('更新范围'));

        await act(async () => {
            await result.current.handleSend();
        });

        expect(useStore.getState().artifactContent).toBe(fullFallback);
        expect(useStore.getState().artifactChangeIndex).toEqual([
            expect.objectContaining({ anchor: 'h2:风险:1' }),
        ]);
    });

    it('should update assistant message and artifact as soon as the first stream chunk arrives', async () => {
        let releaseSecondChunk: () => void = () => undefined;
        const waitForSecondChunk = new Promise<void>((resolve) => {
            releaseSecondChunk = resolve;
        });
        vi.mocked(generateResponseStream).mockImplementation(async function* () {
            yield {
                chatResponse: '正在生成第一帧',
                newArtifact: '# Draft artifact',
                action: '',
                hasArtifactUpdate: true,
            };
            await waitForSecondChunk;
            yield {
                chatResponse: '最终回复',
                newArtifact: '# Final artifact',
                action: '',
                hasArtifactUpdate: true,
            };
        });

        const { result } = renderHook(() => useChatService());

        act(() => {
            result.current.setInput('simulate streaming request');
        });

        let sendPromise: Promise<void> | undefined;
        act(() => {
            sendPromise = result.current.handleSend();
        });

        await waitFor(() => {
            const state = useStore.getState();
            expect(state.chatHistory[1]).toEqual(
                expect.objectContaining({
                    role: 'assistant',
                    content: '正在生成第一帧',
                })
            );
            expect(state.artifactContent).toBe('# Draft artifact');
            expect(state.isGenerating).toBe(true);
        });

        await act(async () => {
            releaseSecondChunk();
            await sendPromise;
        });

        const finalState = useStore.getState();
        expect(finalState.chatHistory[1].content).toBe('最终回复');
        expect(finalState.artifactContent).toBe('# Final artifact');
        expect(finalState.isGenerating).toBe(false);
    });

    it('should clear draft input when sending an override starter prompt', async () => {
        vi.mocked(generateResponseStream).mockImplementation(async function* () {
            yield {
                chatResponse: 'Starter reply',
                newArtifact: 'starter artifact content',
                action: '',
                hasArtifactUpdate: true,
            };
        });

        const { result } = renderHook(() => useChatService());

        act(() => {
            result.current.setInput('用户尚未发送的草稿');
        });

        await act(async () => {
            await result.current.handleSend('推荐问题 prompt');
        });

        const state = useStore.getState();
        expect(state.chatHistory[0]).toEqual(expect.objectContaining({
            role: 'user',
            content: '推荐问题 prompt',
        }));
        expect(result.current.input).toBe('');
    });

    it('should ignore duplicate sends triggered before the hook rerenders', async () => {
        let releaseStream: () => void = () => {};
        vi.mocked(generateResponseStream).mockImplementation(async function* () {
            await new Promise<void>((resolve) => {
                releaseStream = resolve;
            });
            yield {
                chatResponse: '只应生成一次',
                newArtifact: 'new artifact content',
                action: '',
                hasArtifactUpdate: true,
            };
        });

        const { result } = renderHook(() => useChatService());

        act(() => {
            result.current.setInput('连续点击发送');
        });

        let firstSendPromise: Promise<void>;
        let secondSendPromise: Promise<void>;
        await act(async () => {
            firstSendPromise = result.current.handleSend();
            secondSendPromise = result.current.handleSend();
            await Promise.resolve();
        });

        expect(useStore.getState().isGenerating).toBe(true);
        expect(generateResponseStream).toHaveBeenCalledTimes(1);
        expect(useStore.getState().chatHistory).toEqual([
            expect.objectContaining({
                role: 'user',
                content: '连续点击发送',
            }),
        ]);

        await act(async () => {
            releaseStream();
            await firstSendPromise;
            await secondSendPromise;
        });

        const state = useStore.getState();
        expect(generateResponseStream).toHaveBeenCalledTimes(1);
        expect(state.chatHistory).toEqual([
            expect.objectContaining({
                role: 'user',
                content: '连续点击发送',
            }),
            expect.objectContaining({
                role: 'assistant',
                content: '只应生成一次',
            }),
        ]);
    });

    it('should allow a new request after clearing history while the previous stream is still pending', async () => {
        let releaseOldStream: () => void = () => {};
        let releaseNewStream: () => void = () => {};
        const streamSignals: AbortSignal[] = [];
        vi.mocked(generateResponseStream).mockImplementation(async function* (message, _attachments, signal) {
            if (signal) streamSignals.push(signal);
            if (message === '旧请求') {
                await new Promise<void>((resolve) => {
                    releaseOldStream = resolve;
                });
                yield {
                    chatResponse: '旧请求回复不应出现',
                    newArtifact: '# 需求分析文档\n旧请求产物',
                    action: '',
                    hasArtifactUpdate: true,
                };
                return;
            }

            await new Promise<void>((resolve) => {
                releaseNewStream = resolve;
            });
            yield {
                chatResponse: '新请求回复',
                newArtifact: '# 需求分析文档\n新请求产物',
                action: '',
                hasArtifactUpdate: true,
            };
        });

        const { result } = renderHook(() => useChatService());

        act(() => {
            result.current.setInput('旧请求');
        });

        let oldSendPromise: Promise<void>;
        await act(async () => {
            oldSendPromise = result.current.handleSend();
            await Promise.resolve();
        });

        expect(useStore.getState().isGenerating).toBe(true);
        expect(generateResponseStream).toHaveBeenCalledTimes(1);

        act(() => {
            useStore.getState().clearHistory();
        });

        expect(useStore.getState().isGenerating).toBe(false);

        act(() => {
            result.current.setInput('新请求');
        });

        let newSendPromise: Promise<void>;
        await act(async () => {
            newSendPromise = result.current.handleSend();
            await Promise.resolve();
        });

        expect(useStore.getState().isGenerating).toBe(true);
        expect(generateResponseStream).toHaveBeenCalledTimes(2);
        expect(useStore.getState().chatHistory).toEqual([
            expect.objectContaining({
                role: 'user',
                content: '新请求',
            }),
        ]);

        await act(async () => {
            releaseOldStream();
            await oldSendPromise;
        });

        expect(streamSignals[1].aborted).toBe(false);
        expect(useStore.getState().isGenerating).toBe(true);
        expect(useStore.getState().chatHistory).toEqual([
            expect.objectContaining({
                role: 'user',
                content: '新请求',
            }),
        ]);

        await act(async () => {
            releaseNewStream();
            await newSendPromise;
        });

        const state = useStore.getState();
        expect(state.isGenerating).toBe(false);
        expect(state.chatHistory).toEqual([
            expect.objectContaining({
                role: 'user',
                content: '新请求',
            }),
            expect.objectContaining({
                role: 'assistant',
                content: '新请求回复',
            }),
        ]);
        expect(state.artifactContent).toBe('# 需求分析文档\n新请求产物');
        expect(state.artifactContent).not.toContain('旧请求产物');
    });

    it.each([
        ['clearing history', () => useStore.getState().clearHistory()],
        ['switching workflows', () => useStore.getState().setWorkflow('REQ_REVIEW')],
        ['manually switching stages', () => useStore.getState().setStageIndex(1)],
    ])('should abort an in-flight request immediately when %s', async (_scenario, resetWorkspace) => {
        let capturedSignal: AbortSignal | undefined;
        vi.mocked(generateResponseStream).mockImplementation(async function* (_message, _attachments, signal) {
            capturedSignal = signal;
            await new Promise<void>(() => {});
        });

        const { result } = renderHook(() => useChatService());

        act(() => {
            result.current.setInput('旧请求');
        });

        await act(async () => {
            void result.current.handleSend();
            await Promise.resolve();
        });

        expect(capturedSignal?.aborted).toBe(false);

        act(() => {
            resetWorkspace();
        });

        expect(capturedSignal?.aborted).toBe(true);
    });

    it('should keep artifact markdown out of the assistant chat message', async () => {
        const artifactMarkdown = '# 需求分析文档\n\n## 1. 被测系统与边界\n登录功能';
        vi.mocked(generateResponseStream).mockImplementation(async function* () {
            yield {
                chatResponse: '已更新右侧需求分析文档，请确认。',
                newArtifact: artifactMarkdown,
                action: '',
                hasArtifactUpdate: true,
            };
        });

        const { result } = renderHook(() => useChatService());

        act(() => {
            result.current.setInput('帮我设计登录功能测试用例');
        });

        await act(async () => {
            await result.current.handleSend();
        });

        const state = useStore.getState();
        expect(state.chatHistory[1].content).toBe('已更新右侧需求分析文档，请确认。');
        expect(state.chatHistory[1].content).not.toContain('# 需求分析文档');
        expect(state.artifactContent).toBe(artifactMarkdown);
    });

    it('should preserve locked artifact sections when applying model artifact updates', async () => {
        const originalArtifact = [
            '# 需求分析文档',
            '',
            '## 已确认范围',
            '',
            '登录边界已经由业务确认。',
            '',
            '## 可更新建议',
            '',
            '旧建议。',
        ].join('\n');
        const modelArtifact = [
            '# 需求分析文档',
            '',
            '## 已确认范围',
            '',
            '模型试图改写登录边界。',
            '',
            '## 可更新建议',
            '',
            '新建议。',
        ].join('\n');
        useStore.setState({
            artifactContent: originalArtifact,
            stageArtifacts: {
                CLARIFY: originalArtifact,
            },
            artifactSectionLocks: [
                {
                    id: 'lock-1',
                    stageId: 'CLARIFY',
                    heading: '## 已确认范围',
                    content: [
                        '## 已确认范围',
                        '',
                        '登录边界已经由业务确认。',
                    ].join('\n'),
                    createdAt: 1710000000000,
                },
            ],
        });
        vi.mocked(generateResponseStream).mockImplementation(async function* () {
            yield {
                chatResponse: '已补充建议，锁定章节保持不变。',
                newArtifact: modelArtifact,
                action: '',
                hasArtifactUpdate: true,
            };
        });

        const { result } = renderHook(() => useChatService());

        act(() => {
            result.current.setInput('继续补充建议');
        });

        await act(async () => {
            await result.current.handleSend();
        });

        const state = useStore.getState();
        expect(state.artifactContent).toContain('登录边界已经由业务确认。');
        expect(state.artifactContent).not.toContain('模型试图改写登录边界。');
        expect(state.artifactContent).toContain('新建议。');
        expect(state.stageArtifacts.CLARIFY).toBe(state.artifactContent);
        expect(state.artifactHistory[state.artifactHistory.length - 1].content).toBe(state.artifactContent);
    });

    it('should keep truncation warning when an artifact update is marked truncated', async () => {
        vi.mocked(generateResponseStream).mockImplementation(async function* () {
            yield {
                chatResponse: '产出物内容可能不完整，请检查。',
                newArtifact: '# 需求分析文档\n部分内容',
                action: '',
                hasArtifactUpdate: true,
                artifactTruncated: true,
            };
        });

        const { result } = renderHook(() => useChatService());

        act(() => {
            result.current.setInput('生成长文档');
        });

        await act(async () => {
            await result.current.handleSend();
        });

        const state = useStore.getState();
        expect(state.artifactContent).toBe('# 需求分析文档\n部分内容');
        expect(state.artifactTruncated).toBe(true);
    });

    it('should set pendingStageTransition upon NEXT_STAGE action and preserve the source-stage artifact', async () => {
        vi.mocked(generateResponseStream).mockImplementation(async function* () {
            yield {
                chatResponse: 'Moving to next stage',
                newArtifact: '# 需求分析文档\n最终版',
                action: 'NEXT_STAGE',
                hasArtifactUpdate: true,
            };
        });

        const { result } = renderHook(() => useChatService());

        act(() => {
            result.current.setInput('next step');
        });

        await act(async () => {
            await result.current.handleSend();
        });

        // P0-4: NEXT_STAGE no longer auto-transitions; sets pending flag instead
        const state = useStore.getState();
        expect(state.pendingStageTransition).toEqual({ fromStageIndex: 0, toStageIndex: 1 });
        expect(state.stageIndex).toBe(0);
        expect(state.artifactContent).toBe('# 需求分析文档\n最终版');

        // Simulate user confirming the transition via Header button
        act(() => {
            useStore.getState().confirmStageTransition();
        });

        const confirmedState = useStore.getState();
        expect(confirmedState.stageIndex).toBe(1);
        expect(confirmedState.pendingStageTransition).toBeNull();
        expect(confirmedState.artifactContent).toContain('策略制定');
        expect(confirmedState.stageArtifacts['CLARIFY']).toBe('# 需求分析文档\n最终版');
    });

    it('should save the final source-stage artifact before stopping on NEXT_STAGE', async () => {
        vi.mocked(generateResponseStream).mockImplementation(async function* () {
            yield {
                chatResponse: '需求澄清完成，请确认进入策略制定。',
                newArtifact: '# 需求分析文档\n最终版',
                action: 'NEXT_STAGE',
                hasArtifactUpdate: true,
            };
            yield {
                chatResponse: '不应继续消费',
                newArtifact: '# 测试策略蓝图\n不应写入',
                action: '',
                hasArtifactUpdate: true,
            };
        });

        const { result } = renderHook(() => useChatService());

        act(() => {
            result.current.setInput('完成需求澄清');
        });

        await act(async () => {
            await result.current.handleSend();
        });

        const state = useStore.getState();
        expect(state.pendingStageTransition).toEqual({ fromStageIndex: 0, toStageIndex: 1 });
        expect(state.stageIndex).toBe(0);
        expect(state.artifactContent).toBe('# 需求分析文档\n最终版');
        expect(state.stageArtifacts.CLARIFY).toBe('# 需求分析文档\n最终版');
        expect(state.stageArtifacts.STRATEGY).toBeUndefined();
    });

    it('should clear a previous pending stage transition when the user sends a new message', async () => {
        vi.mocked(generateResponseStream).mockImplementation(async function* () {
            yield {
                chatResponse: '已根据补充信息更新当前阶段。',
                newArtifact: '# 需求分析文档\n补充后版本',
                action: '',
                hasArtifactUpdate: true,
            };
        });

        const { result } = renderHook(() => useChatService());

        act(() => {
            useStore.getState().setPendingStageTransition({ fromStageIndex: 0, toStageIndex: 1 });
            result.current.setInput('我先补充一个约束，不要进入下一阶段');
        });

        await act(async () => {
            await result.current.handleSend();
        });

        const state = useStore.getState();
        expect(state.pendingStageTransition).toBeNull();
        expect(state.stageIndex).toBe(0);
        expect(state.artifactContent).toBe('# 需求分析文档\n补充后版本');
    });

    it('should stop consuming stream after NEXT_STAGE and ignore later artifact updates', async () => {
        vi.mocked(generateResponseStream).mockImplementation(async function* () {
            yield { chatResponse: '正在分析需求...', newArtifact: '# 需求分析文档\n内容', action: '', hasArtifactUpdate: true };
            yield { chatResponse: '好的，进入策略制定阶段', newArtifact: '# 需求分析文档\n最终版', action: 'NEXT_STAGE', hasArtifactUpdate: true };
            yield { chatResponse: '继续生成策略细节', newArtifact: '# 测试策略蓝图\n不应写入', action: '', hasArtifactUpdate: true };
        });

        const { result } = renderHook(() => useChatService());

        act(() => {
            result.current.setInput('帮我设计登录测试并推进到下一阶段');
        });

        await act(async () => {
            await result.current.handleSend();
        });

        // P0-4: NEXT_STAGE sets pending flag, does not auto-transition
        const state = useStore.getState();
        expect(state.pendingStageTransition).toEqual({ fromStageIndex: 0, toStageIndex: 1 });
        expect(state.stageIndex).toBe(0);
        expect(state.artifactContent).toBe('# 需求分析文档\n最终版');
        expect(state.stageArtifacts['CLARIFY']).toBe('# 需求分析文档\n最终版');

        // Simulate user confirming the transition
        act(() => {
            useStore.getState().confirmStageTransition();
        });

        const confirmedState = useStore.getState();
        expect(confirmedState.stageIndex).toBe(1);
        expect(confirmedState.pendingStageTransition).toBeNull();
        expect(confirmedState.artifactContent).toContain('策略制定');
        expect(confirmedState.artifactContent).not.toContain('不应写入');
        expect(confirmedState.stageArtifacts['CLARIFY']).toBe('# 需求分析文档\n最终版');
    });

    it('should confirm pending stage transition through the service and continue generation with a stable prompt', async () => {
        vi.mocked(generateResponseStream).mockImplementation(async function* () {
            yield {
                chatResponse: '继续生成策略内容',
                newArtifact: '# 测试策略蓝图\n内容',
                action: '',
                hasArtifactUpdate: true,
            };
        });

        const { result } = renderHook(() => useChatService());

        act(() => {
            useStore.getState().setArtifactContent('# 需求分析文档\n内容');
            useStore.getState().setPendingStageTransition({ fromStageIndex: 0, toStageIndex: 1 });
        });

        await act(async () => {
            await result.current.handleConfirmStageTransition();
        });

        const state = useStore.getState();
        expect(state.stageIndex).toBe(1);
        expect(state.pendingStageTransition).toBeNull();
        expect(state.stageArtifacts['CLARIFY']).toBe('# 需求分析文档\n内容');
        expect(state.stageArtifacts['STRATEGY']).toBe('# 测试策略蓝图\n内容');
        expect(state.chatHistory).toEqual([
            expect.objectContaining({
                role: 'user',
                content: '已确认进入策略制定',
            }),
            expect.objectContaining({
                role: 'assistant',
                content: '继续生成策略内容',
                retryable: false,
            }),
        ]);
        expect(generateResponseStream).toHaveBeenCalledWith(
            '请继续生成当前阶段产出物',
            [],
            expect.any(AbortSignal)
        );
    });

    it('should ignore retry after an internal stage-continuation response', async () => {
        vi.mocked(generateResponseStream).mockImplementation(async function* () {
            yield {
                chatResponse: '继续生成策略内容',
                newArtifact: '# 测试策略蓝图\n内容',
                action: '',
                hasArtifactUpdate: true,
            };
        });

        const { result } = renderHook(() => useChatService());

        act(() => {
            useStore.getState().addMessage({
                id: 'user-1',
                role: 'user',
                content: '完成需求澄清并推进',
                timestamp: 1,
            });
            useStore.getState().addMessage({
                id: 'assistant-1',
                role: 'assistant',
                content: '需求澄清完成，请确认进入策略制定。',
                timestamp: 2,
            });
            useStore.getState().setArtifactContent('# 需求分析文档\n内容');
            useStore.getState().setPendingStageTransition({ fromStageIndex: 0, toStageIndex: 1 });
        });

        await act(async () => {
            await result.current.handleConfirmStageTransition();
        });

        const historyAfterContinuation = useStore.getState().chatHistory;
        expect(historyAfterContinuation).toHaveLength(4);
        expect(historyAfterContinuation[2]).toEqual(expect.objectContaining({
            role: 'user',
            content: '已确认进入策略制定',
        }));
        expect(historyAfterContinuation[3]).toEqual(expect.objectContaining({
            role: 'assistant',
            content: '继续生成策略内容',
            retryable: false,
        }));

        act(() => {
            result.current.handleRetry();
        });

        expect(useStore.getState().chatHistory).toEqual(historyAfterContinuation);
        expect(result.current.input).toBe('');
    });

    it('should immediately retry current stage generation after an internal structured failure', async () => {
        vi.mocked(generateResponseStream).mockImplementation(async function* (message) {
            expect(message).toBe('请继续生成当前阶段产出物');
            yield {
                chatResponse: '已重新生成策略内容',
                newArtifact: '# 测试策略蓝图\n重试后的内容',
                action: '',
                hasArtifactUpdate: true,
            };
        });

        const { result } = renderHook(() => useChatService());

        act(() => {
            useStore.setState({
                stageIndex: 1,
                artifactContent: '# 测试策略蓝图\n暂无产出物。',
                stageArtifacts: {
                    CLARIFY: '# 需求分析文档\n内容',
                    STRATEGY: '# 测试策略蓝图\n暂无产出物。',
                },
                chatHistory: [
                    {
                        id: 'user-1',
                        role: 'user',
                        content: '完成需求澄清并推进',
                        timestamp: 1,
                    },
                    {
                        id: 'assistant-1',
                        role: 'assistant',
                        content: '需求澄清完成，请确认进入策略制定。',
                        timestamp: 2,
                    },
                    {
                        id: 'assistant-2',
                        role: 'assistant',
                        content: '⚠️ **结构化输出生成失败**\n\n模型本轮没有生成符合工作流契约的结果，右侧产出物已保持不变。',
                        timestamp: 3,
                        retryable: false,
                    },
                ],
            });
        });

        await act(async () => {
            await result.current.handleRetryCurrentStageGeneration();
        });

        const state = useStore.getState();
        expect(generateResponseStream).toHaveBeenCalledWith(
            '请继续生成当前阶段产出物',
            [],
            expect.any(AbortSignal)
        );
        expect(state.chatHistory).toEqual([
            expect.objectContaining({ id: 'user-1' }),
            expect.objectContaining({ id: 'assistant-1' }),
            expect.objectContaining({
                role: 'assistant',
                content: '已重新生成策略内容',
                retryable: false,
            }),
        ]);
        expect(state.artifactContent).toBe('# 测试策略蓝图\n重试后的内容');
        expect(state.stageArtifacts.STRATEGY).toBe('# 测试策略蓝图\n重试后的内容');
        expect(result.current.input).toBe('');
    });

    it('should not save a stale internal continuation artifact after clearing history', async () => {
        let releaseStream: () => void = () => {};
        const continuationArtifact = '# 测试策略蓝图\n内部续写半成品';
        vi.mocked(generateResponseStream).mockImplementation(async function* () {
            yield {
                chatResponse: '继续生成策略内容',
                newArtifact: continuationArtifact,
                action: '',
                hasArtifactUpdate: true,
            };
            await new Promise<void>((resolve) => {
                releaseStream = resolve;
            });
        });

        const { result } = renderHook(() => useChatService());

        act(() => {
            useStore.getState().setArtifactContent('# 需求分析文档\n内容');
            useStore.getState().setPendingStageTransition({ fromStageIndex: 0, toStageIndex: 1 });
        });

        let continuationPromise: Promise<void>;
        await act(async () => {
            continuationPromise = result.current.handleConfirmStageTransition();
            await Promise.resolve();
        });

        expect(useStore.getState().stageIndex).toBe(1);
        expect(useStore.getState().artifactContent).toBe(continuationArtifact);

        act(() => {
            useStore.getState().clearHistory();
        });

        await act(async () => {
            releaseStream();
            await continuationPromise;
        });

        const state = useStore.getState();
        expect(state.stageIndex).toBe(0);
        expect(state.chatHistory).toEqual([]);
        expect(state.artifactHistory).toEqual([]);
        expect(state.artifactContent).toBe(getWelcomeMessage('TEST_DESIGN'));
        expect(state.artifactContent).not.toBe(continuationArtifact);
    });

    it('should ignore an internal continuation chunk after clearing history even if the user returns to the same stage', async () => {
        let releaseStream: () => void = () => {};
        const staleArtifact = '# 测试策略蓝图\n首包前清空后的旧产物';
        vi.mocked(generateResponseStream).mockImplementation(async function* () {
            await new Promise<void>((resolve) => {
                releaseStream = resolve;
            });
            yield {
                chatResponse: '不应写回的旧内部续写',
                newArtifact: staleArtifact,
                action: '',
                hasArtifactUpdate: true,
            };
        });

        const { result } = renderHook(() => useChatService());

        act(() => {
            useStore.getState().setArtifactContent('# 需求分析文档\n内容');
            useStore.getState().setPendingStageTransition({ fromStageIndex: 0, toStageIndex: 1 });
        });

        let continuationPromise: Promise<void>;
        await act(async () => {
            continuationPromise = result.current.handleConfirmStageTransition();
            await Promise.resolve();
        });

        expect(useStore.getState().stageIndex).toBe(1);

        act(() => {
            useStore.getState().clearHistory();
            useStore.getState().setStageIndex(1);
        });

        await act(async () => {
            releaseStream();
            await continuationPromise;
        });

        const state = useStore.getState();
        expect(state.stageIndex).toBe(1);
        expect(state.chatHistory).toEqual([]);
        expect(state.artifactHistory).toEqual([]);
        expect(state.artifactContent).toContain('策略制定');
        expect(state.artifactContent).not.toBe(staleArtifact);
    });

    it('should not send or clear draft attachments when confirming a stage transition', async () => {
        vi.mocked(generateResponseStream).mockImplementation(async function* () {
            yield {
                chatResponse: '继续生成策略内容',
                newArtifact: '# 测试策略蓝图\n内容',
                action: '',
                hasArtifactUpdate: true,
            };
        });

        const { result } = renderHook(() => useChatService());
        const draftAttachment = {
            name: 'draft.md',
            data: 'ZHJhZnQ=',
            mimeType: 'text/markdown',
        };

        act(() => {
            result.current.setPendingAttachments([draftAttachment]);
            useStore.getState().setArtifactContent('# 需求分析文档\n内容');
            useStore.getState().setPendingStageTransition({ fromStageIndex: 0, toStageIndex: 1 });
        });

        await act(async () => {
            await result.current.handleConfirmStageTransition();
        });

        expect(generateResponseStream).toHaveBeenCalledWith(
            '请继续生成当前阶段产出物',
            [],
            expect.any(AbortSignal)
        );
        expect(result.current.pendingAttachments).toEqual([draftAttachment]);
    });

    it('should clear pending stage transition when retrying the assistant response that requested it', () => {
        const { result } = renderHook(() => useChatService());

        act(() => {
            useStore.getState().addMessage({
                id: 'user-1',
                role: 'user',
                content: '生成需求分析并进入下一阶段',
                timestamp: 1,
            });
            useStore.getState().addMessage({
                id: 'assistant-1',
                role: 'assistant',
                content: '需求澄清完成，请确认进入策略制定。',
                timestamp: 2,
            });
            useStore.getState().setPendingStageTransition({ fromStageIndex: 0, toStageIndex: 1 });
        });

        act(() => {
            result.current.handleRetry();
        });

        const state = useStore.getState();
        expect(state.chatHistory).toEqual([]);
        expect(state.pendingStageTransition).toBeNull();
        expect(result.current.input).toBe('生成需求分析并进入下一阶段');
    });

    it('should clear artifact truncation warning when retrying the assistant response that caused it', () => {
        const { result } = renderHook(() => useChatService());

        act(() => {
            useStore.getState().addMessage({
                id: 'user-1',
                role: 'user',
                content: '生成一份较长产物',
                timestamp: 1,
            });
            useStore.getState().addMessage({
                id: 'assistant-1',
                role: 'assistant',
                content: '产出物可能不完整。',
                timestamp: 2,
            });
            useStore.getState().setArtifactTruncated(true);
        });

        act(() => {
            result.current.handleRetry();
        });

        const state = useStore.getState();
        expect(state.chatHistory).toEqual([]);
        expect(state.artifactTruncated).toBe(false);
        expect(result.current.input).toBe('生成一份较长产物');
    });

    it('should roll back artifact state when retrying the assistant response that updated it', async () => {
        const previousArtifact = '# 需求分析文档\n发送前内容';
        vi.mocked(generateResponseStream).mockImplementation(async function* () {
            yield {
                chatResponse: '已生成错误产物。',
                newArtifact: '# Bad artifact',
                action: '',
                hasArtifactUpdate: true,
            };
        });

        act(() => {
            useStore.setState({
                artifactContent: previousArtifact,
                artifactHistory: [
                    {
                        id: 'version-before',
                        timestamp: 1,
                        content: previousArtifact,
                        stageId: 'CLARIFY',
                    },
                ],
                stageArtifacts: {
                    CLARIFY: previousArtifact,
                },
            });
        });

        const { result } = renderHook(() => useChatService());

        act(() => {
            result.current.setInput('生成错误产物后重试');
        });

        await act(async () => {
            await result.current.handleSend();
        });

        expect(useStore.getState().artifactContent).toBe('# Bad artifact');
        expect(useStore.getState().stageArtifacts.CLARIFY).toBe('# Bad artifact');
        expect(useStore.getState().artifactHistory).toEqual([
            expect.objectContaining({ content: previousArtifact }),
            expect.objectContaining({ content: '# Bad artifact' }),
        ]);

        act(() => {
            result.current.handleRetry();
        });

        const state = useStore.getState();
        expect(state.chatHistory).toEqual([]);
        expect(state.artifactContent).toBe(previousArtifact);
        expect(state.stageArtifacts.CLARIFY).toBe(previousArtifact);
        expect(state.artifactHistory).toEqual([
            expect.objectContaining({ content: previousArtifact }),
        ]);
        expect(result.current.input).toBe('生成错误产物后重试');
    });

    it('should roll back persisted artifact state when retrying after the hook remounts', () => {
        const previousArtifact = '# 需求分析文档\n发送前内容';
        const badArtifact = '# Bad artifact';

        act(() => {
            useStore.setState({
                chatHistory: [
                    {
                        id: 'user-1',
                        role: 'user',
                        content: '生成错误产物后刷新再重试',
                        timestamp: 1,
                    },
                    {
                        id: 'assistant-1',
                        role: 'assistant',
                        content: '已生成错误产物。',
                        timestamp: 2,
                    },
                ],
                artifactContent: badArtifact,
                artifactHistory: [
                    {
                        id: 'version-before',
                        timestamp: 1,
                        content: previousArtifact,
                        stageId: 'CLARIFY',
                    },
                    {
                        id: 'version-bad',
                        timestamp: 2,
                        content: badArtifact,
                        stageId: 'CLARIFY',
                    },
                ],
                stageArtifacts: {
                    CLARIFY: badArtifact,
                },
            });
        });

        const { result } = renderHook(() => useChatService());

        act(() => {
            result.current.handleRetry();
        });

        const state = useStore.getState();
        expect(state.chatHistory).toEqual([]);
        expect(state.artifactContent).toBe(previousArtifact);
        expect(state.stageArtifacts.CLARIFY).toBe(previousArtifact);
        expect(state.artifactHistory).toEqual([
            expect.objectContaining({ content: previousArtifact }),
        ]);
        expect(result.current.input).toBe('生成错误产物后刷新再重试');
    });

    it('should roll back the first persisted artifact to the workflow welcome state after remounting', () => {
        const badArtifact = '# Bad first artifact';

        act(() => {
            useStore.setState({
                chatHistory: [
                    {
                        id: 'user-1',
                        role: 'user',
                        content: '首次生成错误产物后刷新再重试',
                        timestamp: 1,
                    },
                    {
                        id: 'assistant-1',
                        role: 'assistant',
                        content: '已生成错误产物。',
                        timestamp: 2,
                    },
                ],
                artifactContent: badArtifact,
                artifactHistory: [
                    {
                        id: 'version-bad',
                        timestamp: 2,
                        content: badArtifact,
                        stageId: 'CLARIFY',
                    },
                ],
                stageArtifacts: {
                    CLARIFY: badArtifact,
                },
            });
        });

        const { result } = renderHook(() => useChatService());

        act(() => {
            result.current.handleRetry();
        });

        const state = useStore.getState();
        expect(state.chatHistory).toEqual([]);
        expect(state.artifactContent).toBe(getWelcomeMessage('TEST_DESIGN'));
        expect(state.stageArtifacts.CLARIFY).toBe(getWelcomeMessage('TEST_DESIGN'));
        expect(state.artifactHistory).toEqual([]);
        expect(result.current.input).toBe('首次生成错误产物后刷新再重试');
    });

    it('should not roll back the current stage to a previous stage artifact after remounting', () => {
        const previousStageArtifact = '# 需求分析文档\n需求澄清最终版';
        const badStrategyArtifact = '# Bad strategy artifact';

        act(() => {
            useStore.setState({
                workflow: 'TEST_DESIGN',
                stageIndex: 1,
                chatHistory: [
                    {
                        id: 'user-1',
                        role: 'user',
                        content: '生成错误策略后刷新再重试',
                        timestamp: 1,
                    },
                    {
                        id: 'assistant-1',
                        role: 'assistant',
                        content: '已生成错误策略。',
                        timestamp: 2,
                    },
                ],
                artifactContent: badStrategyArtifact,
                artifactHistory: [
                    {
                        id: 'version-clarify',
                        timestamp: 1,
                        content: previousStageArtifact,
                        stageId: 'CLARIFY',
                    },
                    {
                        id: 'version-bad-strategy',
                        timestamp: 2,
                        content: badStrategyArtifact,
                        stageId: 'STRATEGY',
                    },
                ],
                stageArtifacts: {
                    CLARIFY: previousStageArtifact,
                    STRATEGY: badStrategyArtifact,
                },
            });
        });

        const { result } = renderHook(() => useChatService());

        act(() => {
            result.current.handleRetry();
        });

        const state = useStore.getState();
        expect(state.chatHistory).toEqual([]);
        expect(state.artifactContent).toContain('# 测试策略蓝图');
        expect(state.artifactContent).not.toBe(previousStageArtifact);
        expect(state.stageArtifacts.STRATEGY).toContain('# 测试策略蓝图');
        expect(state.stageArtifacts.STRATEGY).not.toBe(previousStageArtifact);
        expect(state.stageArtifacts.CLARIFY).toBe(previousStageArtifact);
        expect(state.artifactHistory).toEqual([
            expect.objectContaining({ content: previousStageArtifact }),
        ]);
        expect(result.current.input).toBe('生成错误策略后刷新再重试');
    });

    it('should use artifact version stage ids when deciding persisted retry rollback content', () => {
        const previousClarifyVersion = '# 需求分析文档\n旧澄清历史版本';
        const currentClarifyArtifact = '# 需求分析文档\n当前澄清阶段内容';
        const badStrategyArtifact = '# Bad strategy artifact';

        act(() => {
            useStore.setState({
                workflow: 'TEST_DESIGN',
                stageIndex: 1,
                chatHistory: [
                    {
                        id: 'user-1',
                        role: 'user',
                        content: '生成错误策略并刷新后重试',
                        timestamp: 1,
                    },
                    {
                        id: 'assistant-1',
                        role: 'assistant',
                        content: '已生成错误策略。',
                        timestamp: 2,
                    },
                ],
                artifactContent: badStrategyArtifact,
                artifactHistory: [
                    {
                        id: 'version-old-clarify',
                        timestamp: 1,
                        content: previousClarifyVersion,
                        stageId: 'CLARIFY',
                    },
                    {
                        id: 'version-bad-strategy',
                        timestamp: 2,
                        content: badStrategyArtifact,
                        stageId: 'STRATEGY',
                    },
                ],
                stageArtifacts: {
                    CLARIFY: currentClarifyArtifact,
                    STRATEGY: badStrategyArtifact,
                },
            });
        });

        const { result } = renderHook(() => useChatService());

        act(() => {
            result.current.handleRetry();
        });

        const state = useStore.getState();
        expect(state.chatHistory).toEqual([]);
        expect(state.artifactContent).toContain('# 测试策略蓝图');
        expect(state.artifactContent).not.toBe(previousClarifyVersion);
        expect(state.stageArtifacts.STRATEGY).toContain('# 测试策略蓝图');
        expect(state.stageArtifacts.STRATEGY).not.toBe(previousClarifyVersion);
        expect(state.stageArtifacts.CLARIFY).toBe(currentClarifyArtifact);
        expect(state.artifactHistory).toEqual([
            expect.objectContaining({
                content: previousClarifyVersion,
                stageId: 'CLARIFY',
            }),
        ]);
        expect(result.current.input).toBe('生成错误策略并刷新后重试');
    });

    it('should roll back the first persisted artifact in a later stage to the stage template after remounting', () => {
        const clarifyArtifact = '# 需求分析文档\n当前澄清阶段内容';
        const badStrategyArtifact = '# Bad first strategy artifact';

        act(() => {
            useStore.setState({
                workflow: 'TEST_DESIGN',
                stageIndex: 1,
                chatHistory: [
                    {
                        id: 'user-1',
                        role: 'user',
                        content: '首次生成错误策略后刷新再重试',
                        timestamp: 1,
                    },
                    {
                        id: 'assistant-1',
                        role: 'assistant',
                        content: '已生成错误策略。',
                        timestamp: 2,
                    },
                ],
                artifactContent: badStrategyArtifact,
                artifactHistory: [
                    {
                        id: 'version-bad-strategy',
                        timestamp: 2,
                        content: badStrategyArtifact,
                        stageId: 'STRATEGY',
                    },
                ],
                stageArtifacts: {
                    CLARIFY: clarifyArtifact,
                    STRATEGY: badStrategyArtifact,
                },
            });
        });

        const { result } = renderHook(() => useChatService());

        act(() => {
            result.current.handleRetry();
        });

        const state = useStore.getState();
        expect(state.chatHistory).toEqual([]);
        expect(state.artifactContent).toContain('# 测试策略蓝图');
        expect(state.stageArtifacts.STRATEGY).toContain('# 测试策略蓝图');
        expect(state.stageArtifacts.CLARIFY).toBe(clarifyArtifact);
        expect(state.artifactHistory).toEqual([]);
        expect(result.current.input).toBe('首次生成错误策略后刷新再重试');
    });

    it('should ignore retry when generation starts before the hook rerenders', () => {
        useStore.setState({
            chatHistory: [
                {
                    id: 'user-1',
                    role: 'user',
                    content: '上一轮输入',
                    timestamp: 1,
                },
                {
                    id: 'assistant-1',
                    role: 'assistant',
                    content: '上一轮回复',
                    timestamp: 2,
                },
            ],
            isGenerating: false,
        });

        const { result } = renderHook(() => useChatService());
        const handleRetryFromIdleRender = result.current.handleRetry;

        act(() => {
            useStore.getState().setIsGenerating(true);
            handleRetryFromIdleRender();
        });

        const state = useStore.getState();
        expect(state.chatHistory).toEqual([
            expect.objectContaining({
                role: 'user',
                content: '上一轮输入',
            }),
            expect.objectContaining({
                role: 'assistant',
                content: '上一轮回复',
            }),
        ]);
        expect(result.current.input).toBe('');
    });

    it('should not confirm a stage transition when generation starts before the hook rerenders', async () => {
        const { result } = renderHook(() => useChatService());
        const handleConfirmFromIdleRender = result.current.handleConfirmStageTransition;

        act(() => {
            useStore.getState().setPendingStageTransition({ fromStageIndex: 0, toStageIndex: 1 });
            useStore.getState().setIsGenerating(true);
        });

        await act(async () => {
            await handleConfirmFromIdleRender();
        });

        const state = useStore.getState();
        expect(state.stageIndex).toBe(0);
        expect(state.pendingStageTransition).toEqual({ fromStageIndex: 0, toStageIndex: 1 });
        expect(generateResponseStream).not.toHaveBeenCalled();
        expect(state.chatHistory).toEqual([]);
    });

    it('should not continue generation when confirming a stale stage transition', async () => {
        vi.mocked(generateResponseStream).mockImplementation(async function* () {
            yield {
                chatResponse: '不应生成',
                newArtifact: '# 测试策略蓝图\n不应写入',
                action: '',
                hasArtifactUpdate: true,
            };
        });

        const { result } = renderHook(() => useChatService());

        act(() => {
            useStore.getState().setStageIndex(2);
            useStore.getState().setPendingStageTransition({ fromStageIndex: 0, toStageIndex: 1 });
        });

        await act(async () => {
            await result.current.handleConfirmStageTransition();
        });

        const state = useStore.getState();
        expect(state.stageIndex).toBe(2);
        expect(state.pendingStageTransition).toBeNull();
        expect(generateResponseStream).not.toHaveBeenCalled();
        expect(state.chatHistory).toEqual([]);
    });

    it('should ignore stale stream chunks after switching workflows during generation', async () => {
        let releaseStream: () => void = () => {};
        vi.mocked(generateResponseStream).mockImplementation(async function* () {
            await new Promise<void>((resolve) => {
                releaseStream = resolve;
            });
            yield {
                chatResponse: '旧请求回复',
                newArtifact: '# 需求分析文档\n旧请求产物',
                action: '',
                hasArtifactUpdate: true,
            };
        });

        const { result } = renderHook(() => useChatService());

        act(() => {
            result.current.setInput('开始旧工作流生成');
        });

        let sendPromise: Promise<void>;
        await act(async () => {
            sendPromise = result.current.handleSend();
            await Promise.resolve();
        });

        expect(useStore.getState().isGenerating).toBe(true);

        act(() => {
            useStore.getState().setWorkflow('REQ_REVIEW');
        });

        await act(async () => {
            releaseStream();
            await sendPromise;
        });

        const state = useStore.getState();
        expect(state.workflow).toBe('REQ_REVIEW');
        expect(state.chatHistory).toEqual([]);
        expect(state.artifactContent).toBe(getWelcomeMessage('REQ_REVIEW'));
        expect(state.stageArtifacts.REVIEW).toBe(getWelcomeMessage('REQ_REVIEW'));
        expect(state.artifactContent).not.toContain('旧请求产物');
    });

    it('should allow a new request after switching workflows while the previous stream is still pending', async () => {
        let releaseOldStream: () => void = () => {};
        let releaseNewStream: () => void = () => {};
        const streamSignals: AbortSignal[] = [];
        vi.mocked(generateResponseStream).mockImplementation(async function* (message, _attachments, signal) {
            if (signal) streamSignals.push(signal);
            if (message === '旧工作流请求') {
                await new Promise<void>((resolve) => {
                    releaseOldStream = resolve;
                });
                yield {
                    chatResponse: '旧工作流回复不应出现',
                    newArtifact: '# 需求分析文档\n旧工作流产物',
                    action: '',
                    hasArtifactUpdate: true,
                };
                return;
            }

            await new Promise<void>((resolve) => {
                releaseNewStream = resolve;
            });
            yield {
                chatResponse: '新工作流回复',
                newArtifact: '# 需求评审问题清单\n新工作流产物',
                action: '',
                hasArtifactUpdate: true,
            };
        });

        const { result } = renderHook(() => useChatService());

        act(() => {
            result.current.setInput('旧工作流请求');
        });

        let oldSendPromise: Promise<void>;
        await act(async () => {
            oldSendPromise = result.current.handleSend();
            await Promise.resolve();
        });

        expect(useStore.getState().isGenerating).toBe(true);
        expect(generateResponseStream).toHaveBeenCalledTimes(1);

        act(() => {
            useStore.getState().setWorkflow('REQ_REVIEW');
        });

        expect(useStore.getState().workflow).toBe('REQ_REVIEW');
        expect(useStore.getState().isGenerating).toBe(false);

        act(() => {
            result.current.setInput('新工作流请求');
        });

        let newSendPromise: Promise<void>;
        await act(async () => {
            newSendPromise = result.current.handleSend();
            await Promise.resolve();
        });

        expect(useStore.getState().isGenerating).toBe(true);
        expect(generateResponseStream).toHaveBeenCalledTimes(2);
        expect(useStore.getState().chatHistory).toEqual([
            expect.objectContaining({
                role: 'user',
                content: '新工作流请求',
            }),
        ]);

        await act(async () => {
            releaseOldStream();
            await oldSendPromise;
        });

        expect(streamSignals[1].aborted).toBe(false);
        expect(useStore.getState().workflow).toBe('REQ_REVIEW');
        expect(useStore.getState().isGenerating).toBe(true);
        expect(useStore.getState().chatHistory).toEqual([
            expect.objectContaining({
                role: 'user',
                content: '新工作流请求',
            }),
        ]);

        await act(async () => {
            releaseNewStream();
            await newSendPromise;
        });

        const state = useStore.getState();
        expect(state.workflow).toBe('REQ_REVIEW');
        expect(state.isGenerating).toBe(false);
        expect(state.chatHistory).toEqual([
            expect.objectContaining({
                role: 'user',
                content: '新工作流请求',
            }),
            expect.objectContaining({
                role: 'assistant',
                content: '新工作流回复',
            }),
        ]);
        expect(state.artifactContent).toBe('# 需求评审问题清单\n新工作流产物');
        expect(state.artifactContent).not.toContain('旧工作流产物');
    });

    it('should ignore stale stream chunks after clearing history during generation', async () => {
        let releaseStream: () => void = () => {};
        vi.mocked(generateResponseStream).mockImplementation(async function* () {
            await new Promise<void>((resolve) => {
                releaseStream = resolve;
            });
            yield {
                chatResponse: '清空后的旧回复',
                newArtifact: '# 需求分析文档\n清空后的旧产物',
                action: '',
                hasArtifactUpdate: true,
            };
        });

        const { result } = renderHook(() => useChatService());

        act(() => {
            result.current.setInput('开始生成后清空');
        });

        let sendPromise: Promise<void>;
        await act(async () => {
            sendPromise = result.current.handleSend();
            await Promise.resolve();
        });

        expect(useStore.getState().isGenerating).toBe(true);

        act(() => {
            useStore.getState().clearHistory();
        });

        await act(async () => {
            releaseStream();
            await sendPromise;
        });

        const state = useStore.getState();
        expect(state.workflow).toBe('TEST_DESIGN');
        expect(state.stageIndex).toBe(0);
        expect(state.chatHistory).toEqual([]);
        expect(state.artifactContent).toBe(getWelcomeMessage('TEST_DESIGN'));
        expect(state.stageArtifacts.CLARIFY).toBe(getWelcomeMessage('TEST_DESIGN'));
        expect(state.artifactContent).not.toContain('清空后的旧产物');
    });

    it('should save artifact history for the run artifact when manually switching stages before stream ends', async () => {
        let releaseStream: () => void = () => {};
        const runArtifact = '# 需求分析文档\n阶段内产物';
        vi.mocked(generateResponseStream).mockImplementation(async function* () {
            yield {
                chatResponse: '已生成需求分析文档',
                newArtifact: runArtifact,
                action: '',
                hasArtifactUpdate: true,
            };
            await new Promise<void>((resolve) => {
                releaseStream = resolve;
            });
        });

        const { result } = renderHook(() => useChatService());

        act(() => {
            result.current.setInput('生成后切阶段');
        });

        let sendPromise: Promise<void>;
        await act(async () => {
            sendPromise = result.current.handleSend();
            await Promise.resolve();
        });

        expect(useStore.getState().artifactContent).toBe(runArtifact);

        act(() => {
            useStore.getState().setStageIndex(1);
        });

        expect(useStore.getState().artifactContent).toContain('策略制定');

        await act(async () => {
            releaseStream();
            await sendPromise;
        });

        const state = useStore.getState();
        expect(state.stageIndex).toBe(1);
        expect(state.artifactHistory).toEqual([
            expect.objectContaining({
                content: runArtifact,
            }),
        ]);
        expect(state.artifactHistory[0].content).not.toContain('策略制定');
    });

    it('should not save an aborted partial artifact as a normal history version after manually switching stages', async () => {
        let releaseStream: () => void = () => {};
        const partialArtifact = '# 需求分析文档\n半成品';
        vi.mocked(generateResponseStream).mockImplementation(async function* (_message, _attachments, signal) {
            yield {
                chatResponse: '正在生成半成品',
                newArtifact: partialArtifact,
                action: '',
                hasArtifactUpdate: true,
            };
            await new Promise<void>((resolve) => {
                releaseStream = resolve;
            });
            if (signal?.aborted) {
                throw new Error('Aborted by user');
            }
        });

        const { result } = renderHook(() => useChatService());

        act(() => {
            result.current.setInput('生成后切阶段并中止旧流');
        });

        let sendPromise: Promise<void>;
        await act(async () => {
            sendPromise = result.current.handleSend();
            await Promise.resolve();
        });

        expect(useStore.getState().artifactContent).toBe(partialArtifact);

        act(() => {
            useStore.getState().setStageIndex(1);
        });

        await act(async () => {
            releaseStream();
            await sendPromise;
        });

        const state = useStore.getState();
        expect(state.stageIndex).toBe(1);
        expect(state.artifactHistory).toEqual([]);
        expect(state.stageArtifacts.CLARIFY).toBe(partialArtifact);
        expect(state.artifactContent).toContain('策略制定');
    });

    it('should allow a new request after manually switching stages while the previous stream is still pending', async () => {
        let releaseOldStream: () => void = () => {};
        let releaseNewStream: () => void = () => {};
        const streamSignals: AbortSignal[] = [];
        vi.mocked(generateResponseStream).mockImplementation(async function* (message, _attachments, signal) {
            if (signal) streamSignals.push(signal);
            if (message === '旧阶段请求') {
                await new Promise<void>((resolve) => {
                    releaseOldStream = resolve;
                });
                yield {
                    chatResponse: '旧阶段回复不应出现',
                    newArtifact: '# 需求分析文档\n旧阶段产物',
                    action: '',
                    hasArtifactUpdate: true,
                };
                return;
            }

            await new Promise<void>((resolve) => {
                releaseNewStream = resolve;
            });
            yield {
                chatResponse: '新阶段回复',
                newArtifact: '# 测试策略蓝图\n新阶段产物',
                action: '',
                hasArtifactUpdate: true,
            };
        });

        const { result } = renderHook(() => useChatService());

        act(() => {
            result.current.setInput('旧阶段请求');
        });

        let oldSendPromise: Promise<void>;
        await act(async () => {
            oldSendPromise = result.current.handleSend();
            await Promise.resolve();
        });

        expect(useStore.getState().stageIndex).toBe(0);
        expect(useStore.getState().isGenerating).toBe(true);
        expect(generateResponseStream).toHaveBeenCalledTimes(1);

        act(() => {
            useStore.getState().setStageIndex(1);
        });

        expect(useStore.getState().stageIndex).toBe(1);
        expect(useStore.getState().isGenerating).toBe(false);

        act(() => {
            result.current.setInput('新阶段请求');
        });

        let newSendPromise: Promise<void>;
        await act(async () => {
            newSendPromise = result.current.handleSend();
            await Promise.resolve();
        });

        expect(useStore.getState().isGenerating).toBe(true);
        expect(generateResponseStream).toHaveBeenCalledTimes(2);
        expect(useStore.getState().chatHistory).toEqual([
            expect.objectContaining({
                role: 'user',
                content: '旧阶段请求',
            }),
            expect.objectContaining({
                role: 'user',
                content: '新阶段请求',
            }),
        ]);

        await act(async () => {
            releaseOldStream();
            await oldSendPromise;
        });

        expect(streamSignals[1].aborted).toBe(false);
        expect(useStore.getState().stageIndex).toBe(1);
        expect(useStore.getState().isGenerating).toBe(true);
        expect(useStore.getState().chatHistory).toEqual([
            expect.objectContaining({
                role: 'user',
                content: '旧阶段请求',
            }),
            expect.objectContaining({
                role: 'user',
                content: '新阶段请求',
            }),
        ]);

        await act(async () => {
            releaseNewStream();
            await newSendPromise;
        });

        const state = useStore.getState();
        expect(state.stageIndex).toBe(1);
        expect(state.isGenerating).toBe(false);
        expect(state.chatHistory).toEqual([
            expect.objectContaining({
                role: 'user',
                content: '旧阶段请求',
            }),
            expect.objectContaining({
                role: 'user',
                content: '新阶段请求',
            }),
            expect.objectContaining({
                role: 'assistant',
                content: '新阶段回复',
            }),
        ]);
        expect(state.artifactContent).toBe('# 测试策略蓝图\n新阶段产物');
        expect(state.artifactContent).not.toContain('旧阶段产物');
    });

    it('should not save a stale artifact version after clearing history before stream ends', async () => {
        let releaseStream: () => void = () => {};
        const staleArtifact = '# 需求分析文档\n清空前旧产物';
        vi.mocked(generateResponseStream).mockImplementation(async function* () {
            yield {
                chatResponse: '已生成清空前产物',
                newArtifact: staleArtifact,
                action: '',
                hasArtifactUpdate: true,
            };
            await new Promise<void>((resolve) => {
                releaseStream = resolve;
            });
        });

        const { result } = renderHook(() => useChatService());

        act(() => {
            result.current.setInput('生成后清空');
        });

        let sendPromise: Promise<void>;
        await act(async () => {
            sendPromise = result.current.handleSend();
            await Promise.resolve();
        });

        expect(useStore.getState().artifactContent).toBe(staleArtifact);

        act(() => {
            useStore.getState().clearHistory();
        });

        await act(async () => {
            releaseStream();
            await sendPromise;
        });

        const state = useStore.getState();
        expect(state.chatHistory).toEqual([]);
        expect(state.artifactContent).toBe(getWelcomeMessage('TEST_DESIGN'));
        expect(state.stageArtifacts.CLARIFY).toBe(getWelcomeMessage('TEST_DESIGN'));
        expect(state.artifactHistory).toEqual([]);
    });

    it('should not add stopped feedback after clearing history before the first chunk', async () => {
        vi.mocked(generateResponseStream).mockImplementation(async function* (_message, _attachments, signal) {
            await new Promise<never>((_resolve, reject) => {
                signal?.addEventListener('abort', () => {
                    reject(new Error('Aborted by user'));
                });
            });
        });

        const { result } = renderHook(() => useChatService());

        act(() => {
            result.current.setInput('首包前清空并停止');
        });

        let sendPromise: Promise<void>;
        await act(async () => {
            sendPromise = result.current.handleSend();
            await Promise.resolve();
        });

        expect(useStore.getState().isGenerating).toBe(true);

        act(() => {
            useStore.getState().clearHistory();
            result.current.handleStop();
        });

        await act(async () => {
            await sendPromise;
        });

        const state = useStore.getState();
        expect(state.isGenerating).toBe(false);
        expect(state.chatHistory).toEqual([]);
        expect(state.artifactContent).toBe(getWelcomeMessage('TEST_DESIGN'));
        expect(state.stageArtifacts.CLARIFY).toBe(getWelcomeMessage('TEST_DESIGN'));
    });

    it('should not add stale error feedback after clearing history before the first chunk', async () => {
        let releaseStream: () => void = () => {};
        vi.mocked(generateResponseStream).mockImplementation(async function* () {
            await new Promise<void>((resolve) => {
                releaseStream = resolve;
            });
            throw new Error('LLM_ERROR_AFTER_CLEAR');
        });

        const { result } = renderHook(() => useChatService());

        act(() => {
            result.current.setInput('首包前清空后旧错误');
        });

        let sendPromise: Promise<void>;
        await act(async () => {
            sendPromise = result.current.handleSend();
            await Promise.resolve();
        });

        expect(useStore.getState().isGenerating).toBe(true);

        act(() => {
            useStore.getState().clearHistory();
        });

        await act(async () => {
            releaseStream();
            await sendPromise;
        });

        const state = useStore.getState();
        expect(state.isGenerating).toBe(false);
        expect(state.chatHistory).toEqual([]);
        expect(state.artifactContent).toBe(getWelcomeMessage('TEST_DESIGN'));
        expect(state.stageArtifacts.CLARIFY).toBe(getWelcomeMessage('TEST_DESIGN'));
    });

    it('should show an assistant error message before the first stream chunk without changing artifact', async () => {
        vi.mocked(generateResponseStream).mockImplementation(async function* () {
            throw new Error('SCHEMA_VALIDATION_FAILED');
        });

        const { result } = renderHook(() => useChatService());

        act(() => {
            result.current.setInput('触发错误');
        });

        await act(async () => {
            await result.current.handleSend();
        });

        const state = useStore.getState();
        expect(state.chatHistory).toHaveLength(2);
        expect(state.chatHistory[1]).toMatchObject({
            role: 'assistant',
            errorDiagnostic: {
                kind: 'structured',
                rawMessage: 'SCHEMA_VALIDATION_FAILED',
            },
        });
        expect(state.chatHistory[1].content).toContain('结构化输出生成失败');
        expect(state.chatHistory[1].content).not.toContain('SCHEMA_VALIDATION_FAILED');
        expect(state.artifactContent).toBe('initial artifact');
        expect(state.artifactHistory).toEqual([]);
        expect(state.isGenerating).toBe(false);
    });

    it('should show a friendly schema validation message instead of raw retry exhaustion', async () => {
        vi.mocked(generateResponseStream).mockImplementation(async function* () {
            throw new Error('SCHEMA_VALIDATION_FAILED: Exceeded maximum output retries (3)');
        });

        const { result } = renderHook(() => useChatService());

        act(() => {
            result.current.setInput('进入下一阶段');
        });

        await act(async () => {
            await result.current.handleSend();
        });

        const state = useStore.getState();
        expect(state.chatHistory[1].content).toContain('结构化输出生成失败');
        expect(state.chatHistory[1].content).toContain('可以直接重试');
        expect(state.chatHistory[1].content).not.toContain('Exceeded maximum output retries');
        expect(state.chatHistory[1]).toMatchObject({
            errorDiagnostic: {
                kind: 'structured',
                rawMessage: 'SCHEMA_VALIDATION_FAILED: Exceeded maximum output retries (3)',
            },
        });
        expect(state.artifactContent).toBe('initial artifact');
        expect(state.artifactHistory).toEqual([]);
    });

    it('should preserve backend structured diagnostic details in the assistant error card', async () => {
        vi.mocked(generateResponseStream).mockImplementation(async function* () {
            throw Object.assign(
                new Error('SCHEMA_VALIDATION_FAILED: 模型连续生成的结构化结果未通过校验。'),
                {
                    code: 'SCHEMA_VALIDATION_FAILED',
                    diagnostic: {
                        phase: 'structured_output',
                        workflowId: 'TEST_DESIGN',
                        stageId: 'CLARIFY',
                        fieldPath: 'artifact_data.requirement_facts.0.fact',
                        validator: 'string_too_short',
                        retryable: true,
                        publicReason: '模型输出的结构化字段未通过校验，右侧产出物已保持不变。',
                    },
                }
            );
        });

        const { result } = renderHook(() => useChatService());

        act(() => {
            result.current.setInput('触发结构化诊断');
        });

        await act(async () => {
            await result.current.handleSend();
        });

        const state = useStore.getState();
        expect(state.chatHistory[1]).toMatchObject({
            errorDiagnostic: {
                kind: 'structured',
                code: 'SCHEMA_VALIDATION_FAILED',
                phase: 'structured_output',
                workflowId: 'TEST_DESIGN',
                stageId: 'CLARIFY',
                fieldPath: 'artifact_data.requirement_facts.0.fact',
                validator: 'string_too_short',
                retryable: true,
            },
        });
        expect(state.chatHistory[1].content).toContain('右侧产出物已保持不变');
        expect(state.artifactContent).toBe('initial artifact');
        expect(state.artifactHistory).toEqual([]);
    });

    it.each([
        'Artifact Mermaid parse failed: Parse error on line 3',
        'Artifact validation failed: missing required section',
        'Artifact structured visual validation failed: 结构化可视化必须是合法 JSON。',
        'Mermaid parse failed: invalid edge syntax',
    ])('should show structured recovery when artifact validation fails without changing artifact: %s', async (errorMessage) => {
        vi.mocked(generateResponseStream).mockImplementation(async function* () {
            throw new Error(errorMessage);
        });

        const { result } = renderHook(() => useChatService());

        act(() => {
            result.current.setInput('生成包含流程图的测试策略');
        });

        await act(async () => {
            await result.current.handleSend();
        });

        const state = useStore.getState();
        expect(state.chatHistory).toHaveLength(2);
        expect(state.chatHistory[1]).toMatchObject({
            role: 'assistant',
        });
        expect(state.chatHistory[1].content).toContain('结构化输出生成失败');
        expect(state.chatHistory[1].content).not.toContain('**Error:**');
        expect(state.chatHistory[1]).toMatchObject({
            errorDiagnostic: {
                kind: 'structured',
                rawMessage: errorMessage,
            },
        });
        expect(state.artifactContent).toBe('initial artifact');
        expect(state.artifactHistory).toEqual([]);
    });

    it('should append an error to the in-progress assistant message when stream fails after a chunk', async () => {
        vi.mocked(generateResponseStream).mockImplementation(async function* () {
            yield {
                chatResponse: '正在分析...',
                newArtifact: 'initial artifact',
                action: '',
                hasArtifactUpdate: false,
            };
            throw new Error('LLM_ERROR');
        });

        const { result } = renderHook(() => useChatService());

        act(() => {
            result.current.setInput('中途失败');
        });

        await act(async () => {
            await result.current.handleSend();
        });

        const state = useStore.getState();
        expect(state.chatHistory).toHaveLength(2);
        expect(state.chatHistory[1].content).toContain('正在分析...');
        expect(state.chatHistory[1].content).toContain('本轮生成失败');
        expect(state.chatHistory[1].content).not.toContain('LLM_ERROR');
        expect(state.chatHistory[1]).toMatchObject({
            errorDiagnostic: {
                kind: 'generic',
                rawMessage: 'LLM_ERROR',
            },
        });
        expect(state.artifactContent).toBe('initial artifact');
        expect(state.artifactHistory).toEqual([]);
    });

    it('should mark a partially updated artifact as truncated and not save a normal version when stream errors after an artifact update', async () => {
        vi.mocked(generateResponseStream).mockImplementation(async function* () {
            yield {
                chatResponse: '正在生成部分产物...',
                newArtifact: '# Partial artifact from failed stream',
                action: '',
                hasArtifactUpdate: true,
            };
            throw new Error('LLM_ERROR_AFTER_ARTIFACT');
        });

        const { result } = renderHook(() => useChatService());

        act(() => {
            result.current.setInput('生成后中途失败');
        });

        await act(async () => {
            await result.current.handleSend();
        });

        const state = useStore.getState();
        expect(state.chatHistory[1].content).toContain('正在生成部分产物...');
        expect(state.chatHistory[1].content).toContain('本轮生成失败');
        expect(state.chatHistory[1].content).not.toContain('LLM_ERROR_AFTER_ARTIFACT');
        expect(state.chatHistory[1]).toMatchObject({
            errorDiagnostic: {
                kind: 'generic',
                rawMessage: 'LLM_ERROR_AFTER_ARTIFACT',
            },
        });
        expect(state.artifactContent).toBe('# Partial artifact from failed stream');
        expect(state.stageArtifacts.CLARIFY).toBe('# Partial artifact from failed stream');
        expect(state.artifactTruncated).toBe(true);
        expect(state.artifactHistory).toEqual([]);
    });

    it('should mark an in-progress response as stopped without rendering an error', async () => {
        vi.mocked(generateResponseStream).mockImplementation(async function* () {
            yield {
                chatResponse: '正在生成...',
                newArtifact: 'initial artifact',
                action: '',
                hasArtifactUpdate: false,
            };
            throw new Error('Aborted by user');
        });

        const { result } = renderHook(() => useChatService());

        act(() => {
            result.current.setInput('停止生成');
        });

        await act(async () => {
            await result.current.handleSend();
        });

        const state = useStore.getState();
        expect(state.chatHistory[1].content).toBe(
            '正在生成...\n\n*(已停止生成)*'
        );
        expect(state.chatHistory[1].content).not.toContain('**Error:**');
        expect(state.artifactHistory).toEqual([]);
    });

    it('should mark a partially updated artifact as truncated and not save a normal version when stopped', async () => {
        vi.mocked(generateResponseStream).mockImplementation(async function* () {
            yield {
                chatResponse: '正在生成部分产物...',
                newArtifact: '# Partial artifact',
                action: '',
                hasArtifactUpdate: true,
            };
            throw new Error('Aborted by user');
        });

        const { result } = renderHook(() => useChatService());

        act(() => {
            result.current.setInput('停止部分产物生成');
        });

        await act(async () => {
            await result.current.handleSend();
        });

        const state = useStore.getState();
        expect(state.chatHistory[1].content).toBe(
            '正在生成部分产物...\n\n*(已停止生成)*'
        );
        expect(state.artifactContent).toBe('# Partial artifact');
        expect(state.stageArtifacts.CLARIFY).toBe('# Partial artifact');
        expect(state.artifactTruncated).toBe(true);
        expect(state.artifactHistory).toEqual([]);
    });

    it('should add a stopped assistant message when stopped before the first chunk', async () => {
        vi.mocked(generateResponseStream).mockImplementation(async function* (_message, _attachments, signal) {
            await new Promise<never>((_resolve, reject) => {
                signal?.addEventListener('abort', () => {
                    reject(new Error('Aborted by user'));
                });
            });
        });

        const { result } = renderHook(() => useChatService());

        act(() => {
            result.current.setInput('首包前停止');
        });

        let sendPromise: Promise<void>;
        await act(async () => {
            sendPromise = result.current.handleSend();
            await Promise.resolve();
        });

        expect(useStore.getState().isGenerating).toBe(true);

        act(() => {
            result.current.handleStop();
        });

        await act(async () => {
            await sendPromise;
        });

        const state = useStore.getState();
        expect(state.isGenerating).toBe(false);
        expect(state.chatHistory).toHaveLength(2);
        expect(state.chatHistory[1]).toMatchObject({
            role: 'assistant',
            content: '*(已停止生成)*',
        });
        expect(state.chatHistory[1].content).not.toContain('**Error:**');
    });

    it('should treat DOM AbortError before the first chunk as a stopped generation', async () => {
        vi.mocked(generateResponseStream).mockImplementation(async function* () {
            throw new DOMException('The operation was aborted.', 'AbortError');
        });

        const { result } = renderHook(() => useChatService());

        act(() => {
            result.current.setInput('浏览器中止');
        });

        await act(async () => {
            await result.current.handleSend();
        });

        const state = useStore.getState();
        expect(state.chatHistory).toHaveLength(2);
        expect(state.chatHistory[1]).toMatchObject({
            role: 'assistant',
            content: '*(已停止生成)*',
        });
        expect(state.chatHistory[1].content).not.toContain('**Error:**');
    });

    it('should show a friendly quota message when the model returns quota errors', async () => {
        vi.mocked(generateResponseStream).mockImplementation(async function* () {
            throw new Error('429 quota exceeded');
        });

        const { result } = renderHook(() => useChatService());

        act(() => {
            result.current.setInput('额度错误');
        });

        await act(async () => {
            await result.current.handleSend();
        });

        const state = useStore.getState();
        expect(state.chatHistory[1].content).toContain('模型额度或限流异常');
        expect(state.chatHistory[1].content).not.toContain('429 quota exceeded');
        expect(state.chatHistory[1]).toMatchObject({
            errorDiagnostic: {
                kind: 'provider',
                reason: '模型额度或限流异常',
                rawMessage: '429 quota exceeded',
            },
        });
        expect(state.artifactHistory).toEqual([]);
    });

    it.each([
        [
            '系统未配置默认 LLM',
            '模型配置缺失',
            '请先到设置中维护后端默认 LLM 配置',
        ],
        [
            '401 invalid api key',
            '密钥或权限异常',
            '请检查 API Key、Base URL、模型名称和供应商权限',
        ],
        [
            'request timeout while connecting to provider',
            '供应商连接异常',
            '请检查 Base URL、网络连通性或供应商服务状态',
        ],
    ])('should show actionable provider diagnostics for %s', async (
        rawError,
        expectedReason,
        expectedAction,
    ) => {
        vi.mocked(generateResponseStream).mockImplementation(async function* () {
            throw new Error(rawError);
        });

        const { result } = renderHook(() => useChatService());

        act(() => {
            result.current.setInput('模型供应商错误');
        });

        await act(async () => {
            await result.current.handleSend();
        });

        const state = useStore.getState();
        expect(state.chatHistory[1].content).toContain('模型调用未完成');
        expect(state.chatHistory[1].content).toContain(expectedReason);
        expect(state.chatHistory[1].content).not.toContain(expectedAction);
        expect(state.chatHistory[1].content).not.toContain(rawError);
        expect(state.chatHistory[1].content).not.toContain('**Error:**');
        expect(state.chatHistory[1]).toMatchObject({
            errorDiagnostic: {
                kind: 'provider',
                reason: expectedReason,
                action: expect.stringContaining(expectedAction),
                rawMessage: rawError,
            },
        });
        expect(state.artifactHistory).toEqual([]);
    });
});
