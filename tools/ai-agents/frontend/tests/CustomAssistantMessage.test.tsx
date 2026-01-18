import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
// @ts-expect-error - Component not created yet
import { CustomAssistantMessage } from '../components/chat/CustomAssistantMessage';
import * as AssistantUI from '@assistant-ui/react';

vi.mock('@assistant-ui/react', async (importOriginal) => {
    const actual = await importOriginal<typeof import('@assistant-ui/react')>();
    return {
        ...actual,
        useMessage: vi.fn(),
        MessagePrimitive: {
            Root: ({ children, className }: any) => <div className={className}>{children}</div>,
            Content: () => <div>Markdown Content</div>,
            If: ({ copied, children }: any) => copied ? null : children,
        },
        ActionBarPrimitive: {
            Root: ({ children, className }: any) => <div className={className}>{children}</div>,
            Copy: ({ children }: any) => <button>{children}</button>,
            Reload: ({ children }: any) => <button>{children}</button>,
        }
    };
});

// Mock Icons
vi.mock('lucide-react', () => ({
    Bot: () => <span>BotIcon</span>,
    Copy: () => <span>CopyIcon</span>,
    Check: () => <span>CheckIcon</span>,
    RefreshCw: () => <span>RefreshIcon</span>
}));

// Mock Components
vi.mock('../components/chat/TypingIndicator', () => ({
    TypingIndicator: () => <div>Typing...</div>
}));
vi.mock('../components/chat/MarkdownText', () => ({
    MarkdownText: () => <div>Markdown</div>
}));
// Tools UI mock if needed
vi.mock('../components/tools/UpdateArtifactToolUI', () => ({ UpdateArtifactToolUI: () => null }));
vi.mock('../components/tools/ConfirmationToolUI', () => ({ ConfirmationToolUI: () => null }));

const mockAssistant = { id: 'alex', initial: 'A', name: 'Alex', role: 'Analyst' } as any;

describe('CustomAssistantMessage', () => {
    it('renders assistant message', () => {
        vi.mocked(AssistantUI.useMessage).mockReturnValue({
            status: { type: 'complete' },
            content: [{ type: 'text', text: 'Hello' }]
        } as any);

        render(<CustomAssistantMessage assistant={mockAssistant} />);
        expect(screen.getByText('Markdown Content')).toBeInTheDocument();
        expect(screen.getByText('BotIcon')).toBeInTheDocument();
    });

    it('shows typing indicator when running with no content', () => {
        vi.mocked(AssistantUI.useMessage).mockReturnValue({
            status: { type: 'running' },
            content: []
        } as any);

        render(<CustomAssistantMessage assistant={mockAssistant} />);
        expect(screen.getByText('Typing...')).toBeInTheDocument();
    });
});
