import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useChatService } from '../chatService';
import { useStore } from '../../store';
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
            artifactHistory: [],
            stageIndex: 0,
            workflow: 'TEST_DESIGN',
            isGenerating: false,
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

    it('should set pendingStageTransition upon NEXT_STAGE action without writing unconfirmed next-stage artifact', async () => {
        vi.mocked(generateResponseStream).mockImplementation(async function* () {
            yield { chatResponse: 'Moving to next stage', newArtifact: 'new stage artifact', action: 'NEXT_STAGE', hasArtifactUpdate: true };
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
        expect(state.artifactContent).toBe('initial artifact');

        // Simulate user confirming the transition via Header button
        act(() => {
            useStore.getState().confirmStageTransition();
        });

        const confirmedState = useStore.getState();
        expect(confirmedState.stageIndex).toBe(1);
        expect(confirmedState.pendingStageTransition).toBeNull();
        expect(confirmedState.artifactContent).toContain('策略制定');
        expect(confirmedState.stageArtifacts['CLARIFY']).toBe('initial artifact');
    });

    it('should stop consuming stream after NEXT_STAGE and ignore later artifact updates', async () => {
        vi.mocked(generateResponseStream).mockImplementation(async function* () {
            yield { chatResponse: '正在分析需求...', newArtifact: '# 需求分析文档\n内容', action: '', hasArtifactUpdate: true };
            yield { chatResponse: '好的，进入策略制定阶段', newArtifact: '# 测试策略蓝图\n策略内容', action: 'NEXT_STAGE', hasArtifactUpdate: true };
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
        expect(state.artifactContent).toBe('# 需求分析文档\n内容');
        expect(state.stageArtifacts['CLARIFY']).toBe('# 需求分析文档\n内容');

        // Simulate user confirming the transition
        act(() => {
            useStore.getState().confirmStageTransition();
        });

        const confirmedState = useStore.getState();
        expect(confirmedState.stageIndex).toBe(1);
        expect(confirmedState.pendingStageTransition).toBeNull();
        expect(confirmedState.artifactContent).toContain('策略制定');
        expect(confirmedState.artifactContent).not.toContain('不应写入');
        expect(confirmedState.stageArtifacts['CLARIFY']).toBe('# 需求分析文档\n内容');
    });
});
