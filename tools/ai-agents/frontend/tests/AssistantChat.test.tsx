import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { AssistantChat } from '../components/chat/AssistantChat';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { Assistant } from '../types';

// Mock dependencies
vi.mock('../services/backendService', () => ({
    createSession: vi.fn().mockResolvedValue({ sessionId: 'sess_123' })
}));

// Mock useVercelChat
const mockSendMessage = vi.fn();
const mockStop = vi.fn();

vi.mock('../hooks/useVercelChat', () => ({
    useVercelChat: vi.fn(() => ({
        messages: [],
        status: 'ready',
        sendMessage: mockSendMessage,
        stop: mockStop,
        error: undefined
    }))
}));

// Mock MarkdownText to avoid complex rendering
vi.mock('../components/chat/MarkdownText', () => ({
    MarkdownText: ({ content }: { content: string }) => <div data-testid="markdown-text">{content}</div>
}));

// Mock scrollIntoView
Element.prototype.scrollIntoView = vi.fn();

const mockAssistant: Assistant = {
    id: 'alex',
    name: 'Alex',
    role: 'Analyst',
    initial: 'A',
    description: 'Test',
    bundle: 'bundle'
};

describe('AssistantChat Component', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('renders welcome message when session starts', async () => {
        render(
            <AssistantChat
                assistant={mockAssistant}
                onBack={vi.fn()}
            />
        );

        // Wait for session init
        await waitFor(() => {
            expect(screen.queryByText('正在创建会话...')).not.toBeInTheDocument();
        });

        // Expect welcome message
        expect(screen.getByText(`你好，我是 ${mockAssistant.name}`)).toBeInTheDocument();
        expect(screen.getByText(/我可以协助你/)).toBeInTheDocument();
    });

    it('displays error message when useVercelChat returns error', async () => {
        // Setup mock to return error state
        const { useVercelChat } = await import('../hooks/useVercelChat');
        vi.mocked(useVercelChat).mockReturnValue({
            messages: [],
            status: 'error',
            sendMessage: mockSendMessage,
            stop: mockStop,
            error: new Error("Twilio API Error")
        });

        render(
            <AssistantChat
                assistant={mockAssistant}
                onBack={vi.fn()}
            />
        );

        await waitFor(() => {
            expect(screen.queryByText('正在创建会话...')).not.toBeInTheDocument();
        });

        // 查找错误提示 (新组件直接显示错误文本)
        expect(screen.getByText(/出错了: Twilio API Error/i)).toBeInTheDocument();
    });

    it('renders messages correctly', async () => {
        // Mock messages
        const { useVercelChat } = await import('../hooks/useVercelChat');
        vi.mocked(useVercelChat).mockReturnValue({
            messages: [
                { id: '1', role: 'user', parts: [{ type: 'text', text: 'Hello' }] },
                { id: '2', role: 'assistant', parts: [{ type: 'text', text: 'Hi there' }] }
            ],
            status: 'ready',
            sendMessage: mockSendMessage,
            stop: mockStop,
            error: undefined
        });

        render(
            <AssistantChat
                assistant={mockAssistant}
                onBack={vi.fn()}
            />
        );

        await waitFor(() => {
            expect(screen.queryByText('正在创建会话...')).not.toBeInTheDocument();
        });

        expect(screen.getByText('Hello')).toBeInTheDocument();
        expect(screen.getByText('Hi there')).toBeInTheDocument();
    });

    it('handles message submission', async () => {
        // Setup default mock
        const { useVercelChat } = await import('../hooks/useVercelChat');
        vi.mocked(useVercelChat).mockReturnValue({
            messages: [],
            status: 'ready',
            sendMessage: mockSendMessage,
            stop: mockStop,
            error: undefined
        });

        render(
            <AssistantChat
                assistant={mockAssistant}
                onBack={vi.fn()}
            />
        );

        await waitFor(() => {
            expect(screen.queryByText('正在创建会话...')).not.toBeInTheDocument();
        });

        const input = screen.getByPlaceholderText('输入消息...');
        fireEvent.change(input, { target: { value: 'New message' } });

        const sendButton = screen.getByTitle('发送');
        fireEvent.click(sendButton);

        expect(mockSendMessage).toHaveBeenCalledWith({ text: 'New message' });
    });
});
