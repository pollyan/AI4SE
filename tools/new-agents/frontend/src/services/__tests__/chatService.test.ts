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

    it('should transition to next stage upon NEXT_STAGE action', async () => {
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

        const state = useStore.getState();
        // Since stageIndex is 0 originally, it should increment to 1 for test-design workflow
        expect(state.stageIndex).toBe(1);
        // 新阶段的产出物应该是 LLM 输出的新内容，而不是旧阶段的内容
        expect(state.artifactContent).toBe('new stage artifact');
        expect(state.stageArtifacts['STRATEGY']).toBe('new stage artifact');
        // 旧阶段的产出物应该被正确保存为切换前的值
        expect(state.stageArtifacts['CLARIFY']).toBe('initial artifact');
    });

    it('should correctly save both stage artifacts when artifact is updated before NEXT_STAGE in same stream', async () => {
        // 模拟场景：LLM 先生成需求分析文档（更新产出物），然后在后续 chunk 中同时输出 NEXT_STAGE 和新阶段内容
        vi.mocked(generateResponseStream).mockImplementation(async function* () {
            // 第一个 chunk：仅更新当前阶段的产出物
            yield { chatResponse: '正在分析需求...', newArtifact: '# 需求分析文档\n内容', action: '', hasArtifactUpdate: true };
            // 第二个 chunk：触发阶段切换并输出新阶段的产出物
            yield { chatResponse: '好的，进入策略制定阶段', newArtifact: '# 测试策略蓝图\n策略内容', action: 'NEXT_STAGE', hasArtifactUpdate: true };
        });

        const { result } = renderHook(() => useChatService());

        act(() => {
            result.current.setInput('帮我设计登录测试并推进到下一阶段');
        });

        await act(async () => {
            await result.current.handleSend();
        });

        const state = useStore.getState();
        expect(state.stageIndex).toBe(1);
        // 新阶段（策略制定）应该显示策略蓝图
        expect(state.artifactContent).toBe('# 测试策略蓝图\n策略内容');
        expect(state.stageArtifacts['STRATEGY']).toBe('# 测试策略蓝图\n策略内容');
        // 旧阶段（需求澄清）应该保存的是需求分析文档，而不是初始内容
        expect(state.stageArtifacts['CLARIFY']).toBe('# 需求分析文档\n内容');
    });
});
