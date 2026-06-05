import { describe, it, expect, beforeEach, beforeAll, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ChatPane } from '../ChatPane';
import { useStore, WORKFLOWS, WorkflowType } from '../../store';

// Mock chatService since we only want to test the UI component
vi.mock('../../services/chatService', () => {
    return {
        useChatService: vi.fn(() => ({
            input: '',
            setInput: vi.fn(),
            pendingAttachments: [],
            handleSend: vi.fn(),
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
    beforeAll(() => {
        window.HTMLElement.prototype.scrollIntoView = vi.fn();
    });

    beforeEach(() => {
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

    it('renders the welcome message when chat history is empty', () => {
        render(<ChatPane />);
        const currentWorkflowName = WORKFLOWS['TEST_DESIGN'].name;
        
        expect(screen.getByText(currentWorkflowName)).toBeDefined();
        // Since markdown is mocked, we check the test id
        expect(screen.getAllByTestId('markdown').length).toBeGreaterThan(0);
        expect(screen.getByText('你可以试试这样问：')).toBeDefined();
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

    it('typing in textarea calls setInput', async () => {
        const mockSetInput = vi.fn();
        (useChatService as any).mockReturnValue({
            input: 'initial',
            setInput: mockSetInput,
            pendingAttachments: [],
            handleSend: vi.fn(),
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
        (useChatService as any).mockReturnValue({
            input: 'hello', // provide input so the button is not disabled
            setInput: vi.fn(),
            pendingAttachments: [],
            handleSend: mockHandleSend,
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
        (useChatService as any).mockReturnValue({
            input: 'hello', // provide input so the button is not disabled
            setInput: vi.fn(),
            pendingAttachments: [],
            handleSend: mockHandleSend,
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
        (useChatService as any).mockReturnValue({
            input: '',
            setInput: vi.fn(),
            pendingAttachments: [],
            handleSend: vi.fn(),
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

    it('confirms pending transition and triggers next-stage generation from chat pane', () => {
        const mockHandleSend = vi.fn();
        (useChatService as any).mockReturnValue({
            input: '',
            setInput: vi.fn(),
            pendingAttachments: [],
            handleSend: mockHandleSend,
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

        expect(useStore.getState().stageIndex).toBe(1);
        expect(useStore.getState().pendingStageTransition).toBeNull();
        expect(mockHandleSend).toHaveBeenCalledWith('请继续生成当前阶段产出物');
    });
});
