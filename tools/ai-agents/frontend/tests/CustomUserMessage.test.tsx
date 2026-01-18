import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
// @ts-expect-error - Component not created yet
import { CustomUserMessage } from '../components/chat/CustomUserMessage';
import * as AssistantUI from '@assistant-ui/react';

vi.mock('@assistant-ui/react', async (importOriginal) => {
    const actual = await importOriginal<typeof import('@assistant-ui/react')>();
    return {
        ...actual,
        useMessage: vi.fn(),
        MessagePrimitive: {
            Root: ({ children, className }: any) => <div className={className}>{children}</div>,
            Content: () => <div>Message Content</div>,
            If: ({ copied, children }: any) => copied ? null : children,
        },
        ActionBarPrimitive: {
            Root: ({ children, className }: any) => <div className={className}>{children}</div>,
            Copy: ({ children }: any) => <button>{children}</button>,
        }
    };
});

// Mock Icons
vi.mock('lucide-react', () => ({
    User: () => <span>UserIcon</span>,
    Copy: () => <span>CopyIcon</span>,
    Check: () => <span>CheckIcon</span>
}));

// Mock MessageAttachments (internal dependency)
vi.mock('../components/chat/MessageAttachments', () => ({
    MessageAttachments: ({ attachments }: any) => (
        <div data-testid="attachments">
            {attachments.map((a: any) => a.filename).join(', ')}
        </div>
    )
}));

describe('CustomUserMessage', () => {
    it('renders user message content', () => {
        vi.mocked(AssistantUI.useMessage).mockReturnValue({
            metadata: {}
        } as any);

        render(<CustomUserMessage />);
        expect(screen.getByText('Message Content')).toBeInTheDocument();
        expect(screen.getByText('UserIcon')).toBeInTheDocument();
    });

    it('displays attachments when present', () => {
        vi.mocked(AssistantUI.useMessage).mockReturnValue({
            metadata: {
                custom: {
                    attachments: [{ filename: 'test.txt', size: 100 }]
                }
            }
        } as any);

        render(<CustomUserMessage />);
        expect(screen.getByTestId('attachments')).toHaveTextContent('test.txt');
    });
});
