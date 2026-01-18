import { render, screen, waitFor } from '@testing-library/react';
import { AssistantChat } from '../components/chat/AssistantChat';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { Assistant } from '../types';
import * as AssistantUI from '@assistant-ui/react';

// Mock dependencies
vi.mock('../services/backendService', () => ({
    createSession: vi.fn().mockResolvedValue({ sessionId: 'sess_123' })
}));

// Mock useChatRuntime
vi.mock('../hooks/useChatRuntime', () => ({
    useChatRuntime: vi.fn().mockReturnValue({
        // Minimal mock of runtime object
        thread: {
            messages: [],
            append: vi.fn(),
        }
    })
}));

// Mock assistant-ui hooks to simulate error state
// We need to spy on useAssistantRuntime or mock the module
vi.mock('@assistant-ui/react', async (importOriginal) => {
    const actual = await importOriginal();
    return {
        ...actual,
        useAssistantRuntime: vi.fn(),
        // Mock Provider to avoid internal errors from incomplete runtime mock
        AssistantRuntimeProvider: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
        // Mock other primitives to avoid errors
        ThreadPrimitive: {
            Root: ({ children }: any) => <div>{children}</div>,
            Viewport: ({ children }: any) => <div>{children}</div>,
            Messages: () => <div>Messages</div>,
        },
        ComposerPrimitive: {
            Root: ({ children }: any) => <div>{children}</div>,
            Input: () => <input />,
        },
        ActionBarPrimitive: {
            Root: ({ children }: any) => <div>{children}</div>,
            Copy: ({ children }: any) => <div>{children}</div>,
            Reload: ({ children }: any) => <div>{children}</div>,
        },
        useComposerRuntime: () => ({
            getState: () => ({ text: "" }),
            setText: vi.fn(),
        }),
        useMessage: () => ({ status: { type: 'running' } }), 
    };
});

const mockAssistant: Assistant = {
    id: 'alex',
    name: 'Alex',
    role: 'Analyst',
    initial: 'A',
    description: 'Test',
    bundle: 'bundle'
};

describe('AssistantChat Error Handling', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('displays error message when runtime has error', async () => {
        // Setup mock to return error state
        const mockRuntime = {
            thread: {
                messages: [],
                append: vi.fn(),
            }
        };
        
        // Mock useChatRuntime to return our runtime
        const { useChatRuntime } = await import('../hooks/useChatRuntime');
        vi.mocked(useChatRuntime).mockReturnValue(mockRuntime as any);

        // Mock useAssistantRuntime to return error
        // Note: AssistantChat renders Provider with this runtime.
        // Components INSIDE AssistantChat call useAssistantRuntime.
        // We are mocking useAssistantRuntime to simulate what happens when 
        // the runtime passed to Provider has an error (or the hook reads it).
        vi.mocked(AssistantUI.useAssistantRuntime).mockReturnValue({
            thread: {
                messages: [],
                append: vi.fn(),
                error: new Error("Network connection failed") // Simulate error
            }
        } as any);

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

        // Expect error UI
        expect(await screen.findByText(/Network connection failed/i)).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /重试/i })).toBeInTheDocument();
    });
});
