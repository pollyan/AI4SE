import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ChatPane } from '../ChatPane';
import { useStore, type WorkflowType } from '../../store';

vi.mock('../../services/chatService', () => ({
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
        removeAttachment: vi.fn(),
    })),
}));

vi.mock('../Mermaid', () => ({
    Mermaid: ({ chart }: { chart: string }) => <div data-testid="mermaid">{chart}</div>,
}));

vi.mock('../../services/workflowHandoffService', () => ({
    fetchWorkflowHandoffs: vi.fn().mockResolvedValue([]),
    startWorkflowHandoff: vi.fn(),
}));

describe('ChatPane Markdown readability', () => {
    beforeAll(() => {
        window.HTMLElement.prototype.scrollIntoView = vi.fn();
    });

    beforeEach(() => {
        useStore.setState({
            chatHistory: [],
            isGenerating: false,
            workflow: 'TEST_DESIGN' as WorkflowType,
            stageIndex: 0,
            pendingStageTransition: null,
        });
        vi.clearAllMocks();
    });

    it('renders assistant long markdown with readable list, link, emphasis, and code styles', () => {
        useStore.setState({
            chatHistory: [
                {
                    id: 'assistant-1',
                    role: 'assistant',
                    content: [
                        '我先把关键点收拢一下：',
                        '',
                        '- **关键风险**：`登录失败` 需要补异常路径。',
                        '- 参考 [需求说明](https://example.com)。',
                        '',
                        '> 请优先确认 P0 风险。',
                        '',
                        '```ts',
                        'const risk = "P0";',
                        '```',
                    ].join('\n'),
                    timestamp: Date.now(),
                },
            ],
        });

        const { container } = render(
            <MemoryRouter>
                <ChatPane />
            </MemoryRouter>
        );

        const list = container.querySelector('ul');
        expect(list?.className).toContain('list-disc');
        expect(container.querySelector('li')?.className).toContain('leading-relaxed');
        expect(screen.getByText('关键风险').className).toContain('text-blue-400');
        expect(screen.getByText('登录失败').className).toContain('font-mono');
        expect(screen.getByRole('link', { name: '需求说明' }).className).toContain('underline');
        expect(container.querySelector('blockquote')?.className).toContain('border-l');
        expect(container.querySelector('pre')?.className).toContain('overflow-x-auto');
    });
});
