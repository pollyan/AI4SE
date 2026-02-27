import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useChatService } from '../chatService';
import { useStore } from '../../store';
import { generateResponseStream } from '../../llm';

// Mock the LLM service to avoid making real API calls during tests
vi.mock('../../llm', () => ({
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
            yield { chatResponse: 'Moving to next stage', newArtifact: 'content', action: 'NEXT_STAGE', hasArtifactUpdate: true };
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
    });
});
