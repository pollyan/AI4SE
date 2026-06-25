import React from 'react';
import { describe, it, expect, beforeEach, beforeAll, afterEach, vi } from 'vitest';
import { act, render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ChatPane } from '../ChatPane';
import { useStore, WORKFLOWS, WorkflowType, type Attachment } from '../../store';

const mockNavigate = vi.hoisted(() => vi.fn());

vi.mock('react-router-dom', () => ({
    useNavigate: () => mockNavigate,
}));

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
            handleRetryCurrentStageGeneration: vi.fn(),
            handleStop: vi.fn(),
            handleFileChange: vi.fn(),
            removeAttachment: vi.fn()
        }))
    };
});

vi.mock('../../services/workflowHandoffService', () => ({
    fetchWorkflowHandoffs: vi.fn(),
    startWorkflowHandoff: vi.fn(),
}));

import { useChatService } from '../../services/chatService';
import { fetchWorkflowHandoffs, startWorkflowHandoff } from '../../services/workflowHandoffService';

// Mock Mermaid and ReactMarkdown to simplify component testing
vi.mock('react-markdown', () => ({
    default: ({ children }: { children: React.ReactNode }) => <div data-testid="markdown">{children}</div>
}));

vi.mock('../Mermaid', () => ({
    Mermaid: ({ chart }: { chart: string }) => <div data-testid="mermaid">{chart}</div>
}));

describe('ChatPane Component', () => {
    const originalClipboard = navigator.clipboard;
    const mockFetch = vi.fn();

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
            pendingStageTransition: null,
            artifactVisualDiagnostics: [],
            currentRunId: null,
            isSettingsOpen: false,
        });
        global.fetch = mockFetch;
        mockFetch.mockReset();
        vi.mocked(fetchWorkflowHandoffs).mockResolvedValue([]);
        vi.mocked(startWorkflowHandoff).mockReset();
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
            handleRetryCurrentStageGeneration: vi.fn(),
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

    it('shows a structured output failure recovery card with a primary retry action', () => {
        const mockHandleRetry = vi.fn();
        const mockHandleRetryCurrentStageGeneration = vi.fn();
        vi.mocked(useChatService).mockReturnValue({
            input: '',
            setInput: vi.fn(),
            pendingAttachments: [],
            setPendingAttachments: vi.fn(),
            handleSend: vi.fn(),
            handleConfirmStageTransition: vi.fn(),
            handleRetry: mockHandleRetry,
            handleRetryCurrentStageGeneration: mockHandleRetryCurrentStageGeneration,
            handleStop: vi.fn(),
            handleFileChange: vi.fn(),
            removeAttachment: vi.fn()
        });
        useStore.setState({
            chatHistory: [
                { id: '1', role: 'user', content: '进入下一阶段', timestamp: Date.now() },
                {
                    id: '2',
                    role: 'assistant',
                    content: [
                        '⚠️ **结构化输出生成失败**',
                        '',
                        '模型本轮没有生成符合工作流契约的结果，右侧产出物已保持不变。可以直接重试。',
                    ].join('\n'),
                    timestamp: Date.now() + 1000,
                },
            ],
        });

        render(<ChatPane />);
        fireEvent.click(screen.getByRole('button', { name: '重试本阶段生成' }));

        expect(screen.getByText('右侧产出物已保持不变')).toBeDefined();
        expect(screen.getByText('连续失败时，请补充更明确的需求或阶段确认信息后再试。')).toBeDefined();
        expect(screen.queryByRole('button', { name: '补充信息后再试' })).toBeNull();
        expect(mockHandleRetry).not.toHaveBeenCalled();
        expect(mockHandleRetryCurrentStageGeneration).toHaveBeenCalledOnce();
    });

    it('hides stage transition confirmation when the latest assistant message is a structured output failure', () => {
        useStore.setState({
            pendingStageTransition: { fromStageIndex: 0, toStageIndex: 1 },
            chatHistory: [
                { id: '1', role: 'user', content: '进入下一阶段', timestamp: Date.now() },
                {
                    id: '2',
                    role: 'assistant',
                    content: '⚠️ **结构化输出生成失败**\n\n右侧产出物已保持不变。可以直接重试。',
                    timestamp: Date.now() + 1000,
                },
            ],
        });

        render(<ChatPane />);

        expect(screen.getByRole('button', { name: '重试本阶段生成' })).toBeDefined();
        expect(screen.queryByText(/AI 建议进入下一阶段：策略制定/)).toBeNull();
        expect(screen.queryByText('确认进入 策略制定')).toBeNull();
    });

    it('shows supplement guidance after repeated structured failures without retrying or sending', () => {
        const mockSetInput = vi.fn();
        const mockHandleRetry = vi.fn();
        const mockHandleSend = vi.fn();
        vi.mocked(useChatService).mockImplementation(() => {
            const [input, setInputState] = React.useState('');
            return {
                input,
                setInput: (nextInput: string) => {
                    mockSetInput(nextInput);
                    setInputState(nextInput);
                },
                pendingAttachments: [],
                setPendingAttachments: vi.fn(),
                handleSend: mockHandleSend,
                handleConfirmStageTransition: vi.fn(),
                handleRetry: mockHandleRetry,
                handleRetryCurrentStageGeneration: vi.fn(),
                handleStop: vi.fn(),
                handleFileChange: vi.fn(),
                removeAttachment: vi.fn()
            };
        });
        useStore.setState({
            chatHistory: [
                { id: '1', role: 'user', content: '生成测试策略', timestamp: Date.now() },
                {
                    id: '2',
                    role: 'assistant',
                    content: '⚠️ **结构化输出生成失败**\n\n右侧产出物已保持不变。可以直接重试。',
                    timestamp: Date.now() + 1000,
                },
                { id: '3', role: 'user', content: '重试', timestamp: Date.now() + 2000 },
                {
                    id: '4',
                    role: 'assistant',
                    content: '⚠️ **结构化输出生成失败**\n\n右侧产出物已保持不变。可以直接重试。',
                    timestamp: Date.now() + 3000,
                },
            ],
        });

        render(<ChatPane />);

        fireEvent.click(screen.getByRole('button', { name: '补充信息后再试' }));

        const textarea = screen.getByRole('textbox') as HTMLTextAreaElement;
        expect(textarea.value).toContain('请补充更明确的需求或阶段确认信息');
        expect(document.activeElement).toBe(textarea);
        expect(mockSetInput).toHaveBeenCalledWith(expect.stringContaining('请补充更明确的需求或阶段确认信息'));
        expect(mockHandleRetry).not.toHaveBeenCalled();
        expect(mockHandleSend).not.toHaveBeenCalled();
    });

    it('does not duplicate current-stage artifact visual diagnostics in the chat pane', () => {
        useStore.setState({
            chatHistory: [
                { id: '1', role: 'assistant', content: '右侧产物已更新。', timestamp: Date.now() },
            ],
            artifactVisualDiagnostics: [
                {
                    id: 'structured-visual:CLARIFY:0',
                    stageId: 'CLARIFY',
                    kind: 'structured-visual',
                    title: '结构化可视化格式错误',
                    message: '结构化可视化必须是合法 JSON。',
                    createdAt: Date.now(),
                },
            ],
        });

        render(<ChatPane />);

        expect(screen.getByText('右侧产物已更新。')).toBeDefined();
        expect(screen.queryByText('右侧产物有可视化需要处理')).toBeNull();
        expect(screen.queryByText('结构化可视化必须是合法 JSON。')).toBeNull();
        expect(screen.queryByRole('button', { name: '查看诊断详情' })).toBeNull();
        expect(screen.queryByRole('button', { name: '查看问题位置' })).toBeNull();
    });

    it('does not show visual diagnostics from another stage', () => {
        useStore.setState({
            chatHistory: [
                { id: '1', role: 'assistant', content: '右侧产物已更新。', timestamp: Date.now() },
            ],
            artifactVisualDiagnostics: [
                {
                    id: 'structured-visual:STRATEGY:0',
                    stageId: 'STRATEGY',
                    kind: 'structured-visual',
                    title: '结构化可视化格式错误',
                    message: '策略阶段可视化错误。',
                    createdAt: Date.now(),
                },
            ],
        });

        render(<ChatPane />);

        expect(screen.queryByText('右侧产物有可视化需要处理')).toBeNull();
        expect(screen.queryByText('策略阶段可视化错误。')).toBeNull();
    });

    it('shows a provider failure recovery card with a retry action', () => {
        const mockHandleRetry = vi.fn();
        const mockHandleRetryCurrentStageGeneration = vi.fn();
        vi.mocked(useChatService).mockReturnValue({
            input: '',
            setInput: vi.fn(),
            pendingAttachments: [],
            setPendingAttachments: vi.fn(),
            handleSend: vi.fn(),
            handleConfirmStageTransition: vi.fn(),
            handleRetry: mockHandleRetry,
            handleRetryCurrentStageGeneration: mockHandleRetryCurrentStageGeneration,
            handleStop: vi.fn(),
            handleFileChange: vi.fn(),
            removeAttachment: vi.fn()
        });
        useStore.setState({
            chatHistory: [
                { id: '1', role: 'user', content: '生成测试策略', timestamp: Date.now() },
                {
                    id: '2',
                    role: 'assistant',
                    content: '⚠️ 模型调用未完成：密钥或权限异常，右侧产出物已保持不变。',
                    timestamp: Date.now() + 1000,
                    errorDiagnostic: {
                        kind: 'provider',
                        summary: '模型调用未完成：密钥或权限异常，右侧产出物已保持不变。',
                        reason: '密钥或权限异常',
                        action: '请检查 API Key、Base URL、模型名称和供应商权限。',
                        rawMessage: '401 invalid api key',
                    },
                },
            ],
        });

        render(<ChatPane />);
        fireEvent.click(screen.getByRole('button', { name: '重试本阶段生成' }));

        expect(screen.getByText('模型调用未完成')).toBeDefined();
        expect(screen.getByText(/右侧产出物已保持不变/)).toBeDefined();
        expect(screen.queryByText('请检查 API Key、Base URL、模型名称和供应商权限。')).toBeNull();
        fireEvent.click(screen.getByRole('button', { name: '查看详情' }));
        expect(screen.getByText(/请检查 API Key、Base URL、模型名称和供应商权限/)).toBeDefined();
        expect(screen.getByRole('button', { name: '打开模型设置' })).toBeDefined();
        expect(screen.getByRole('button', { name: '检测连接' })).toBeDefined();
        expect(mockHandleRetry).not.toHaveBeenCalled();
        expect(mockHandleRetryCurrentStageGeneration).toHaveBeenCalledOnce();
    });

    it('keeps error details collapsed inside the latest assistant message until requested', () => {
        const diagnosticMessage = Object.assign(
            {
                id: '2',
                role: 'assistant' as const,
                content: '⚠️ 本轮生成失败：请查看错误详情后重试。',
                timestamp: Date.now() + 1000,
            },
            {
                errorDiagnostic: {
                    kind: 'generic',
                    summary: '本轮生成失败：请查看错误详情后重试。',
                    rawMessage: 'LLM_ERROR: raw backend detail that should be hidden by default',
                },
            }
        );
        useStore.setState({
            chatHistory: [
                { id: '1', role: 'user', content: '触发失败', timestamp: Date.now() },
                diagnosticMessage,
            ],
        });

        render(<ChatPane />);

        expect(screen.getByText('本轮生成失败：请查看错误详情后重试。')).toBeDefined();
        expect(screen.getByRole('button', { name: '查看详情' })).toBeDefined();
        expect(screen.queryByText(/raw backend detail/)).toBeNull();

        fireEvent.click(screen.getByRole('button', { name: '查看详情' }));
        expect(screen.getByText(/LLM_ERROR: raw backend detail/)).toBeDefined();

        fireEvent.click(screen.getByRole('button', { name: '收起详情' }));
        expect(screen.queryByText(/raw backend detail/)).toBeNull();
    });

    it('opens settings from the provider failure recovery card', () => {
        useStore.setState({
            chatHistory: [
                {
                    id: '1',
                    role: 'assistant',
                    content: '⚠️ 模型调用未完成：模型配置缺失，右侧产出物已保持不变。',
                    timestamp: Date.now(),
                    errorDiagnostic: {
                        kind: 'provider',
                        summary: '模型调用未完成：模型配置缺失，右侧产出物已保持不变。',
                        reason: '模型配置缺失',
                        action: '请先到设置中维护后端默认 LLM 配置。',
                        rawMessage: '系统未配置默认 LLM',
                    },
                },
            ],
            isSettingsOpen: false,
        });

        render(<ChatPane />);
        fireEvent.click(screen.getByRole('button', { name: '打开模型设置' }));

        expect(useStore.getState().isSettingsOpen).toBe(true);
    });

    it('checks model connectivity from the provider failure recovery card', async () => {
        mockFetch.mockResolvedValueOnce({
            ok: true,
            json: () => Promise.resolve({
                ok: true,
                message: '模型配置可用',
            }),
        });
        useStore.setState({
            chatHistory: [
                {
                    id: '1',
                    role: 'assistant',
                    content: '⚠️ 模型调用未完成：模型配置缺失，右侧产出物已保持不变。',
                    timestamp: Date.now(),
                    errorDiagnostic: {
                        kind: 'provider',
                        summary: '模型调用未完成：模型配置缺失，右侧产出物已保持不变。',
                        reason: '模型配置缺失',
                        action: '请先到设置中维护后端默认 LLM 配置。',
                        rawMessage: '系统未配置默认 LLM',
                    },
                },
            ],
        });

        render(<ChatPane />);
        fireEvent.click(screen.getByRole('button', { name: '检测连接' }));

        await waitFor(() => {
            expect(mockFetch).toHaveBeenCalledWith('/new-agents/api/config/check', {
                method: 'POST',
            });
        });
        expect(await screen.findByText('模型配置可用')).toBeDefined();
    });

    it('shows a connection check failure from the provider failure recovery card', async () => {
        mockFetch.mockResolvedValueOnce({
            ok: false,
            json: () => Promise.resolve({
                message: '供应商无法访问',
            }),
        });
        useStore.setState({
            chatHistory: [
                {
                    id: '1',
                    role: 'assistant',
                    content: '⚠️ 模型调用未完成：模型配置缺失，右侧产出物已保持不变。',
                    timestamp: Date.now(),
                    errorDiagnostic: {
                        kind: 'provider',
                        summary: '模型调用未完成：模型配置缺失，右侧产出物已保持不变。',
                        reason: '模型配置缺失',
                        action: '请先到设置中维护后端默认 LLM 配置。',
                        rawMessage: '系统未配置默认 LLM',
                    },
                },
            ],
        });

        render(<ChatPane />);
        fireEvent.click(screen.getByRole('button', { name: '检测连接' }));

        expect(await screen.findByText('供应商无法访问')).toBeDefined();
    });

    it('shows backend error details from the provider failure connection check', async () => {
        mockFetch.mockResolvedValueOnce({
            ok: false,
            json: () => Promise.resolve({
                error: '系统未配置默认 LLM，请维护后端默认 LLM 配置后重试',
            }),
        });
        useStore.setState({
            chatHistory: [
                {
                    id: '1',
                    role: 'assistant',
                    content: '⚠️ 模型调用未完成：模型配置缺失，右侧产出物已保持不变。',
                    timestamp: Date.now(),
                    errorDiagnostic: {
                        kind: 'provider',
                        summary: '模型调用未完成：模型配置缺失，右侧产出物已保持不变。',
                        reason: '模型配置缺失',
                        action: '请先到设置中维护后端默认 LLM 配置。',
                        rawMessage: '系统未配置默认 LLM',
                    },
                },
            ],
        });

        render(<ChatPane />);
        fireEvent.click(screen.getByRole('button', { name: '检测连接' }));

        expect(await screen.findByText('系统未配置默认 LLM，请维护后端默认 LLM 配置后重试')).toBeDefined();
    });

    it('keeps provider connection check feedback on the clicked failure message', async () => {
        mockFetch.mockResolvedValueOnce({
            ok: true,
            json: () => Promise.resolve({
                ok: true,
                message: '模型配置可用',
            }),
        });
        useStore.setState({
            chatHistory: [
                {
                    id: '1',
                    role: 'assistant',
                    content: '⚠️ 模型调用未完成：第一次失败。',
                    timestamp: Date.now(),
                    errorDiagnostic: {
                        kind: 'provider',
                        summary: '模型调用未完成：第一次失败。',
                        reason: '模型配置缺失',
                        action: '请先到设置中维护后端默认 LLM 配置。',
                        rawMessage: '第一次失败。',
                    },
                },
                {
                    id: '2',
                    role: 'assistant',
                    content: '⚠️ 模型调用未完成：第二次失败。',
                    timestamp: Date.now() + 1000,
                    errorDiagnostic: {
                        kind: 'provider',
                        summary: '模型调用未完成：第二次失败。',
                        reason: '模型配置缺失',
                        action: '请先到设置中维护后端默认 LLM 配置。',
                        rawMessage: '第二次失败。',
                    },
                },
            ],
        });

        render(<ChatPane />);
        const failureCards = screen.getAllByText('模型调用未完成').map((title) => title.closest('.rounded-xl'));
        const firstFailureCard = failureCards[0] as HTMLElement;
        const secondFailureCard = failureCards[1] as HTMLElement;
        fireEvent.click(screen.getAllByRole('button', { name: '检测连接' })[0]);

        await waitFor(() => {
            expect(firstFailureCard.textContent).toContain('模型配置可用');
        });
        expect(secondFailureCard.textContent).not.toContain('模型配置可用');
    });

    it('hides stage transition confirmation when the latest assistant message is a provider failure', () => {
        useStore.setState({
            pendingStageTransition: { fromStageIndex: 0, toStageIndex: 1 },
            chatHistory: [
                { id: '1', role: 'user', content: '进入下一阶段', timestamp: Date.now() },
                {
                    id: '2',
                    role: 'assistant',
                    content: '⚠️ 模型调用未完成：模型配置缺失，右侧产出物已保持不变。',
                    timestamp: Date.now() + 1000,
                    errorDiagnostic: {
                        kind: 'provider',
                        summary: '模型调用未完成：模型配置缺失，右侧产出物已保持不变。',
                        reason: '模型配置缺失',
                        action: '请先到设置中维护后端默认 LLM 配置。',
                        rawMessage: '系统未配置默认 LLM',
                    },
                },
            ],
        });

        render(<ChatPane />);

        expect(screen.getByRole('button', { name: '重试本阶段生成' })).toBeDefined();
        expect(screen.queryByText(/AI 建议进入下一阶段：策略制定/)).toBeNull();
        expect(screen.queryByText('确认进入 策略制定')).toBeNull();
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
            handleRetryCurrentStageGeneration: vi.fn(),
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
            handleRetryCurrentStageGeneration: vi.fn(),
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
            handleRetryCurrentStageGeneration: vi.fn(),
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
            handleRetryCurrentStageGeneration: vi.fn(),
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

    it('loads workflow handoff actions for the current persisted run', async () => {
        useStore.setState({
            workflow: 'VALUE_DISCOVERY' as WorkflowType,
            stageIndex: 3,
            currentRunId: 'alex-run-123',
            chatHistory: [
                { id: '1', role: 'assistant', content: '价值蓝图已完成', timestamp: Date.now() },
            ],
        });
        vi.mocked(fetchWorkflowHandoffs).mockResolvedValue([
            {
                id: 'handoff-1',
                label: '交给 Lisa 做测试设计',
                sourceWorkflowId: 'VALUE_DISCOVERY',
                sourceStageId: 'BLUEPRINT',
                sourceArtifactVersion: 2,
                targetWorkflowId: 'TEST_DESIGN',
                targetStageId: 'CLARIFY',
                targetAgentId: 'lisa',
                prompt: '请基于 Alex 的价值蓝图设计测试策略。',
            },
        ]);

        render(<ChatPane />);

        expect(fetchWorkflowHandoffs).toHaveBeenCalledWith('alex-run-123');
        expect(await screen.findByText('交给 Lisa 做测试设计')).toBeDefined();
    });

    it('applies a workflow handoff from the chat pane action', async () => {
        useStore.setState({
            workflow: 'VALUE_DISCOVERY' as WorkflowType,
            stageIndex: 3,
            currentRunId: 'alex-run-123',
            chatHistory: [
                { id: '1', role: 'assistant', content: '价值蓝图已完成', timestamp: Date.now() },
            ],
        });
        vi.mocked(fetchWorkflowHandoffs).mockResolvedValue([
            {
                id: 'handoff-1',
                label: '交给 Lisa 做测试设计',
                sourceWorkflowId: 'VALUE_DISCOVERY',
                sourceStageId: 'BLUEPRINT',
                sourceArtifactVersion: 2,
                targetWorkflowId: 'TEST_DESIGN',
                targetStageId: 'CLARIFY',
                targetAgentId: 'lisa',
                prompt: '请基于 Alex 的价值蓝图设计测试策略。',
            },
        ]);
        vi.mocked(startWorkflowHandoff).mockResolvedValue({
            id: 'handoff-1',
            label: '交给 Lisa 做测试设计',
            sourceWorkflowId: 'VALUE_DISCOVERY',
            sourceStageId: 'BLUEPRINT',
            sourceArtifactVersion: 2,
            targetWorkflowId: 'TEST_DESIGN',
            targetStageId: 'CLARIFY',
            targetAgentId: 'lisa',
            targetRunId: 'lisa-run-456',
            prompt: '请基于 Alex 的价值蓝图设计测试策略。',
        });

        render(<ChatPane />);
        fireEvent.click(await screen.findByText('交给 Lisa 做测试设计'));

        await waitFor(() => {
            expect(startWorkflowHandoff).toHaveBeenCalledWith('alex-run-123', 'handoff-1');
        });
        expect(useStore.getState().workflow).toBe('TEST_DESIGN');
        expect(useStore.getState().stageIndex).toBe(0);
        expect(useStore.getState().currentRunId).toBe('lisa-run-456');
        expect(useStore.getState().chatHistory[0]).toEqual(expect.objectContaining({
            role: 'user',
            content: '请基于 Alex 的价值蓝图设计测试策略。',
        }));
        expect(mockNavigate).toHaveBeenCalledWith('/workspace/lisa/test-design?runId=lisa-run-456');
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
            handleRetryCurrentStageGeneration: vi.fn(),
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

    it('keeps a confirmed stage transition as chat history after pending state clears', () => {
        useStore.setState({
            pendingStageTransition: null,
            chatHistory: [
                { id: '1', role: 'assistant', content: '当前阶段产出物已更新。', timestamp: Date.now() },
                { id: '2', role: 'user', content: '已确认进入策略制定', timestamp: Date.now() + 1000 },
                { id: '3', role: 'assistant', content: '继续生成策略内容', timestamp: Date.now() + 2000, retryable: false },
            ],
        });

        render(<ChatPane />);

        expect(screen.queryByText(/AI 建议进入下一阶段/)).toBeNull();
        expect(screen.getByText('已确认进入策略制定')).toBeDefined();
        expect(screen.getByText('继续生成策略内容')).toBeDefined();
    });
});
