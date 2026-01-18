import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
// @ts-expect-error - Component not created yet
import { CustomComposer } from '../components/chat/CustomComposer';
import * as AssistantUI from '@assistant-ui/react';

vi.mock('@assistant-ui/react', async (importOriginal) => {
    const actual = await importOriginal<typeof import('@assistant-ui/react')>();
    return {
        ...actual,
        useComposerRuntime: vi.fn(),
        useAssistantRuntime: vi.fn(),
        ComposerPrimitive: {
            Root: ({ children }: any) => <div>{children}</div>,
            Input: ({ onKeyDown, ...props }: any) => (
                <input 
                    {...props} 
                    onKeyDown={(e) => onKeyDown && onKeyDown(e)} 
                />
            ),
            Attachments: () => <div data-testid="native-attachments" />,
            Send: ({ children, onClick }: any) => <div onClick={onClick}>{children}</div>
        }
    };
});

vi.mock('lucide-react', () => ({
    Send: () => <span>SendIcon</span>
}));

vi.mock('../components/chat/AttachmentButton', () => ({
    AttachmentButton: ({ onFilesSelected }: any) => (
        <button onClick={() => onFilesSelected([new File([], 'test.txt')])}>
            AddFile
        </button>
    )
}));

// Mock attachmentUtils as they might be removed/unused
vi.mock('../../utils/attachmentUtils', () => ({
    processFile: vi.fn(),
    buildMessageWithAttachments: vi.fn()
}));

describe('CustomComposer', () => {
    const mockSetText = vi.fn();
    const mockSend = vi.fn();
    const mockAddAttachment = vi.fn();

    beforeEach(() => {
        vi.clearAllMocks();
        vi.mocked(AssistantUI.useComposerRuntime).mockReturnValue({
            getState: () => ({ text: '' }),
            setText: mockSetText,
            send: mockSend,
            addAttachment: mockAddAttachment
        } as any);
    });

    it('adds attachment via runtime', () => {
        render(<CustomComposer />);
        fireEvent.click(screen.getByText('AddFile'));
        expect(mockAddAttachment).toHaveBeenCalled();
    });

    it('renders native attachments', () => {
        render(<CustomComposer />);
        expect(screen.getByTestId('native-attachments')).toBeInTheDocument();
    });

    it('exposes automation API using native send', () => {
        render(<CustomComposer />);
        window.assistantComposer?.send();
        expect(mockSend).toHaveBeenCalled();
    });
});
