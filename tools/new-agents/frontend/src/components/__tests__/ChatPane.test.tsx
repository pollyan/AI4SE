import { describe, it, expect, beforeEach, beforeAll, afterEach, vi } from 'vitest';
import { act, render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ChatPane } from '../ChatPane';
import { useStore, WORKFLOWS, WorkflowType, type Attachment } from '../../store';

// Mock chatService since we only want to test the UI component
vi.mock('../../services/chatService', () => {
    return {
        useChatService: vi.fn(() => ({
            input: '',
            setInput: vi.fn(),
            pendingAttachments: [],
            setPendingAttachments: vi.fn(),
            handleSend: vi.fn(),
            handleConfirmStageTransition: vi.fn(),
            handleRetry: vi.fn(),
            handleStop: vi.fn(),
            handleFileChange: vi.fn(),
            removeAttachment: vi.fn()
        }))
    };
});

import { useChatService } from '../../services/chatService';

// Mock Mermaid and ReactMarkdown to simplify component testing
vi.mock('react-markdown', () => ({
    default: ({ children }: { children: React.ReactNode }) => <div data-testid="markdown">{children}</div>
}));

vi.mock('../Mermaid', () => ({
    Mermaid: ({ chart }: { chart: string }) => <div data-testid="mermaid">{chart}</div>
}));

describe('ChatPane Component', () => {
    const originalClipboard = navigator.clipboard;

    beforeAll(() => {
        window.HTMLElement.prototype.scrollIntoView = vi.fn();
    });

    beforeEach(() => {
        Object.defineProperty(navigator, 'clipboard', {
            configurable: true,
            value: originalClipboard,
        });
        // Reset the store to default state
        useStore.setState({ 
            chatHistory: [],
            isGenerating: false,
            workflow: 'TEST_DESIGN' as WorkflowType,
            stageIndex: 0,
            pendingStageTransition: null
        });
        vi.clearAllMocks();
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it('renders the welcome message when chat history is empty', () => {
        render(<ChatPane />);
        const currentWorkflowName = WORKFLOWS['TEST_DESIGN'].name;
        
        expect(screen.getAllByText(currentWorkflowName).length).toBeGreaterThan(0);
        // Since markdown is mocked, we check the test id
        expect(screen.getAllByTestId('markdown').length).toBeGreaterThan(0);
        expect(screen.getByText('你可以试试这样问：')).toBeDefined();
    });

    it('sends starter prompts without consuming draft attachments', () => {
        const mockHandleSend = vi.fn();
        vi.mocked(useChatService).mockReturnValue({
            input: '用户尚未发送的草稿',
            setInput: vi.fn(),
            pendingAttachments: [
                {
                    name: 'draft.md',
                    data: 'ZHJhZnQ=',
                    mimeType: 'text/markdown',
                },
            ],
            setPendingAttachments: vi.fn(),
            handleSend: mockHandleSend,
            handleConfirmStageTransition: vi.fn(),
            handleRetry: vi.fn(),
            handleStop: vi.fn(),
            handleFileChange: vi.fn(),
            removeAttachment: vi.fn()
        });

        render(<ChatPane />);
        const starterPrompt = WORKFLOWS.TEST_DESIGN.onboarding.starterPrompts[0];

        fireEvent.click(screen.getByText(starterPrompt));

        expect(mockHandleSend).toHaveBeenCalledWith(starterPrompt, {
            useDraftAttachments: false,
        });
    });

    it('renders chat history when it is not empty', () => {
        useStore.setState({ 
            chatHistory: [
                { id: '1', role: 'user', content: 'Hello AI', timestamp: Date.now() },
                { id: '2', role: 'assistant', content: 'Hello User', timestamp: Date.now() + 1000 }
            ]
        });

        render(<ChatPane />);
        
        const markdownElements = screen.getAllByTestId('markdown');
        expect(markdownElements.length).toBe(2);
        
        // Ensure standard welcome UI is gone
        expect(screen.queryByText('你可以试试这样问：')).toBeNull();
    });

    it('does not show retry for non-retryable assistant messages', () => {
        useStore.setState({
            chatHistory: [
                {
                    id: '1',
                    role: 'assistant',
                    content: '内部续写生成的新阶段内容',
                    timestamp: Date.now(),
                    retryable: false,
                },
            ],
        });

        render(<ChatPane />);

        expect(screen.queryByTitle('重新生成')).toBeNull();
    });

    it('shows the active workflow name in the chat header', () => {
        useStore.setState({
            workflow: 'VALUE_DISCOVERY' as WorkflowType,
            chatHistory: [
                { id: '1', role: 'user', content: '梳理产品价值', timestamp: Date.now() },
            ],
        });

        render(<ChatPane />);

        expect(screen.getByRole('heading', { name: '价值发现' })).toBeDefined();
        expect(screen.queryByRole('heading', { name: '智能需求分析' })).toBeNull();
    });

    it('renders messages when persisted attachments is a non-array value', () => {
        useStore.setState({
            chatHistory: [
                {
                    id: '1',
                    role: 'user',
                    content: '历史消息仍应显示',
                    timestamp: Date.now(),
                    attachments: { length: 1 } as unknown as Attachment[],
                },
            ],
        });

        expect(() => render(<ChatPane />)).not.toThrow();
        expect(screen.getByText('历史消息仍应显示')).toBeDefined();
    });

    it('renders messages when persisted attachments contain malformed entries', () => {
        useStore.setState({
            chatHistory: [
                {
                    id: '1',
                    role: 'user',
                    content: '历史消息仍应显示',
                    timestamp: Date.now(),
                    attachments: [
                        null,
                        {
                            name: 'valid.md',
                            data: 'IyB2YWxpZA==',
                            mimeType: 'text/markdown',
                        },
                        {
                            name: 123,
                            data: 'abc',
                            mimeType: 'text/plain',
                        },
                    ] as unknown as Attachment[],
                },
            ],
        });

        expect(() => render(<ChatPane />)).not.toThrow();
        expect(screen.getByText('历史消息仍应显示')).toBeDefined();
        expect(screen.getByText('valid.md')).toBeDefined();
        expect(screen.queryByText('123')).toBeNull();
    });

    it('typing in textarea calls setInput', async () => {
        const mockSetInput = vi.fn();
        vi.mocked(useChatService).mockReturnValue({
            input: 'initial',
            setInput: mockSetInput,
            pendingAttachments: [],
            setPendingAttachments: vi.fn(),
            handleSend: vi.fn(),
            handleConfirmStageTransition: vi.fn(),
            handleRetry: vi.fn(),
            handleStop: vi.fn(),
            handleFileChange: vi.fn(),
            removeAttachment: vi.fn()
        });

        render(<ChatPane />);
        
        const textarea = screen.getByRole('textbox') as HTMLTextAreaElement;
        fireEvent.change(textarea, { target: { value: 'testing input' } });
        
        expect(mockSetInput).toHaveBeenCalledWith('testing input');
    });

    it('clicking send button calls handleSend', async () => {
        const mockHandleSend = vi.fn();
        vi.mocked(useChatService).mockReturnValue({
            input: 'hello', // provide input so the button is not disabled
            setInput: vi.fn(),
            pendingAttachments: [],
            setPendingAttachments: vi.fn(),
            handleSend: mockHandleSend,
            handleConfirmStageTransition: vi.fn(),
            handleRetry: vi.fn(),
            handleStop: vi.fn(),
            handleFileChange: vi.fn(),
            removeAttachment: vi.fn()
        });

        render(<ChatPane />);
        
        // Find send button wrapper by title since we don't have aria-label
        const sendButton = screen.getByTitle('发送');
        fireEvent.click(sendButton);
        
        expect(mockHandleSend).toHaveBeenCalled();
    });

    it('pressing Enter in textarea calls handleSend', async () => {
        const mockHandleSend = vi.fn();
        vi.mocked(useChatService).mockReturnValue({
            input: 'hello', // provide input so the button is not disabled
            setInput: vi.fn(),
            pendingAttachments: [],
            setPendingAttachments: vi.fn(),
            handleSend: mockHandleSend,
            handleConfirmStageTransition: vi.fn(),
            handleRetry: vi.fn(),
            handleStop: vi.fn(),
            handleFileChange: vi.fn(),
            removeAttachment: vi.fn()
        });

        render(<ChatPane />);
        
        const textarea = screen.getByRole('textbox') as HTMLTextAreaElement;
        fireEvent.keyDown(textarea, { key: 'Enter', code: 'Enter' });
        
        expect(mockHandleSend).toHaveBeenCalled();
    });

    it('shows stop button when generating', async () => {
        const mockHandleStop = vi.fn();
        useStore.setState({ isGenerating: true });
        vi.mocked(useChatService).mockReturnValue({
            input: '',
            setInput: vi.fn(),
            pendingAttachments: [],
            setPendingAttachments: vi.fn(),
            handleSend: vi.fn(),
            handleConfirmStageTransition: vi.fn(),
            handleRetry: vi.fn(),
            handleStop: mockHandleStop,
            handleFileChange: vi.fn(),
            removeAttachment: vi.fn()
        });

        render(<ChatPane />);
        
        // Send button should be replaced by Stop button
        expect(screen.queryByTitle('发送')).toBeNull();
        const stopButton = screen.getByTitle('停止生成');
        expect(stopButton).toBeDefined();

        fireEvent.click(stopButton);
        expect(mockHandleStop).toHaveBeenCalled();
    });

    it('shows thinking animation when generating and assistant message is empty', async () => {
        useStore.setState({ 
            isGenerating: true,
            chatHistory: [
                { id: '1', role: 'user', content: 'Hello', timestamp: Date.now() },
                { id: '2', role: 'assistant', content: '', timestamp: Date.now() + 1000 }
            ]
        });

        render(<ChatPane />);
        
        expect(screen.getByText(/思考中\.\.\./)).toBeDefined();
    });

    it('renders stage transition confirmation card in the chat pane', () => {
        useStore.setState({
            pendingStageTransition: { fromStageIndex: 0, toStageIndex: 1 },
            chatHistory: [
                { id: '1', role: 'user', content: '确认', timestamp: Date.now() },
                { id: '2', role: 'assistant', content: '当前阶段产出物已更新。', timestamp: Date.now() + 1000 }
            ]
        });

        render(<ChatPane />);

        expect(screen.getByText(/AI 建议进入下一阶段：策略制定/)).toBeDefined();
        expect(screen.getByText('暂不进入')).toBeDefined();
        expect(screen.getByText('确认进入 策略制定')).toBeDefined();
    });

    it('clears pending transition when user declines in chat pane', () => {
        useStore.setState({
            pendingStageTransition: { fromStageIndex: 0, toStageIndex: 1 },
            chatHistory: [
                { id: '1', role: 'assistant', content: '当前阶段产出物已更新。', timestamp: Date.now() }
            ]
        });

        render(<ChatPane />);
        fireEvent.click(screen.getByText('暂不进入'));

        expect(useStore.getState().pendingStageTransition).toBeNull();
        expect(useStore.getState().stageIndex).toBe(0);
    });

    it('shows failure feedback when copying to clipboard is rejected', async () => {
        Object.defineProperty(navigator, 'clipboard', {
            configurable: true,
            value: {
                writeText: vi.fn().mockRejectedValue(new Error('permission denied')),
            },
        });
        useStore.setState({
            chatHistory: [
                { id: '1', role: 'assistant', content: '复制失败场景', timestamp: Date.now() },
            ],
        });

        render(<ChatPane />);
        fireEvent.click(screen.getByTitle('复制内容'));

        expect(await screen.findByText('复制失败')).toBeDefined();
        expect(screen.queryByText('已复制到剪贴板')).toBeNull();
    });

    it('keeps the latest copy feedback when copying messages in quick succession', async () => {
        vi.useFakeTimers();
        Object.defineProperty(navigator, 'clipboard', {
            configurable: true,
            value: {
                writeText: vi.fn().mockResolvedValue(undefined),
            },
        });
        useStore.setState({
            chatHistory: [
                { id: '1', role: 'assistant', content: '第一条消息', timestamp: Date.now() },
                { id: '2', role: 'assistant', content: '第二条消息', timestamp: Date.now() + 1000 },
            ],
        });

        render(<ChatPane />);
        const copyButtons = screen.getAllByTitle('复制内容');

        fireEvent.click(copyButtons[0]);
        await act(async () => {
            await Promise.resolve();
        });
        expect(screen.getByText('已复制到剪贴板')).toBeDefined();

        await act(async () => {
            vi.advanceTimersByTime(1000);
        });

        fireEvent.click(copyButtons[1]);
        await act(async () => {
            await Promise.resolve();
        });
        expect(copyButtons[1].textContent).toContain('已复制');

        await act(async () => {
            vi.advanceTimersByTime(1000);
        });

        expect(screen.getByText('已复制到剪贴板')).toBeDefined();
        expect(copyButtons[1].textContent).toContain('已复制');
    });

    it('confirms pending transition and triggers next-stage generation from chat pane', () => {
        const mockHandleConfirmStageTransition = vi.fn();
        vi.mocked(useChatService).mockReturnValue({
            input: '',
            setInput: vi.fn(),
            pendingAttachments: [],
            setPendingAttachments: vi.fn(),
            handleSend: vi.fn(),
            handleConfirmStageTransition: mockHandleConfirmStageTransition,
            handleRetry: vi.fn(),
            handleStop: vi.fn(),
            handleFileChange: vi.fn(),
            removeAttachment: vi.fn()
        });

        useStore.setState({
            pendingStageTransition: { fromStageIndex: 0, toStageIndex: 1 },
            chatHistory: [
                { id: '1', role: 'assistant', content: '当前阶段产出物已更新。', timestamp: Date.now() }
            ]
        });

        render(<ChatPane />);
        fireEvent.click(screen.getByText('确认进入 策略制定'));

        expect(mockHandleConfirmStageTransition).toHaveBeenCalledOnce();
    });
});
