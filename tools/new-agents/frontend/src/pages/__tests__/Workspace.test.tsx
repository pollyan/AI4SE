import { describe, it, expect, beforeEach, vi } from 'vitest';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { useStore } from '../../store';
import { BrowserRouter } from 'react-router-dom';

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
    const actual = await vi.importActual('react-router-dom');
    return {
        ...actual,
        useNavigate: () => mockNavigate,
        useParams: vi.fn(),
    };
});

const mockUseParams = vi.mocked(await import('react-router-dom')).useParams;

vi.mock('../../services/runSnapshotService', () => ({
    fetchRunSnapshot: vi.fn(),
}));

import { Workspace } from '../../pages/Workspace';
import { fetchRunSnapshot } from '../../services/runSnapshotService';

// Mock child components
vi.mock('../../components/Header', () => ({
    Header: () => <div data-testid="header">Header</div>,
}));
vi.mock('../../components/ChatPane', () => ({
    ChatPane: () => <div data-testid="chat-pane">ChatPane</div>,
}));
vi.mock('../../components/ArtifactPane', () => ({
    ArtifactPane: () => <div data-testid="artifact-pane">ArtifactPane</div>,
}));
vi.mock('../../components/SettingsModal', () => ({
    SettingsModal: () => <div data-testid="settings-modal">SettingsModal</div>,
}));

// Mock fetch for onboarding check
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('Workspace Page', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        window.history.pushState({}, '', '/new-agents/workspace/lisa/test-design');
        mockUseParams.mockReturnValue({});
        vi.mocked(fetchRunSnapshot).mockReset();
        useStore.setState({
            chatHistory: [],
            workflow: 'TEST_DESIGN',
            stageIndex: 0,
            currentRunId: null,
        });
    });

    it('renders basic layout with ChatPane and ArtifactPane without act warnings', async () => {
        const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
        mockFetch.mockResolvedValue({ ok: true, json: () => Promise.resolve({ hasDefault: true }) });
        try {
            render(
                <BrowserRouter>
                    <Workspace />
                </BrowserRouter>
            );
            expect(screen.getByTestId('header')).toBeTruthy();
            expect(await screen.findByTestId('chat-pane')).toBeTruthy();
            expect(await screen.findByTestId('artifact-pane')).toBeTruthy();

            await waitFor(() => {
                expect(mockFetch).toHaveBeenCalledWith('/new-agents/api/config');
            });

            expect(consoleErrorSpy).not.toHaveBeenCalledWith(
                expect.stringContaining('not wrapped in act'),
                expect.anything(),
                expect.anything(),
                expect.anything()
            );
        } finally {
            consoleErrorSpy.mockRestore();
        }
    });

    it('shows onboarding overlay when backend has no default config', async () => {
        mockFetch.mockResolvedValue({ ok: true, json: () => Promise.resolve({ hasDefault: false }) });
        render(
            <BrowserRouter>
                <Workspace />
            </BrowserRouter>
        );
        // Wait for async fetch + state update
        const onboarding = await screen.findByText(/后端默认 LLM 未配置/);
        expect(onboarding).toBeTruthy();
        expect(screen.getByText(/直接打开模型设置/)).toBeTruthy();
        expect(screen.getByRole('button', { name: '打开模型设置' })).toBeTruthy();
        expect(screen.getByRole('button', { name: '重新检查配置' })).toBeTruthy();
    });

    it('opens model settings from the missing default LLM onboarding overlay', async () => {
        mockFetch.mockResolvedValue({ ok: true, json: () => Promise.resolve({ hasDefault: false }) });
        render(
            <BrowserRouter>
                <Workspace />
            </BrowserRouter>
        );

        expect(await screen.findByText(/后端默认 LLM 未配置/)).toBeTruthy();
        fireEvent.click(screen.getByRole('button', { name: '打开模型设置' }));

        expect(useStore.getState().isSettingsOpen).toBe(true);
    });

    it('hides onboarding after settings report a usable default LLM config', async () => {
        mockFetch
            .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ hasDefault: false }) })
            .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ hasDefault: true }) });
        render(
            <BrowserRouter>
                <Workspace />
            </BrowserRouter>
        );

        expect(await screen.findByText(/后端默认 LLM 未配置/)).toBeTruthy();
        act(() => {
            const state = useStore.getState() as unknown as {
                notifyDefaultLlmConfigChanged?: () => void;
            };
            state.notifyDefaultLlmConfigChanged?.();
        });

        await waitFor(() => {
            expect(screen.queryByText(/后端默认 LLM 未配置/)).toBeNull();
        });
        expect(mockFetch).toHaveBeenCalledTimes(2);
    });

    it('keeps onboarding visible when a manual default LLM config recheck still fails', async () => {
        mockFetch
            .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ hasDefault: false }) })
            .mockRejectedValueOnce(new Error('backend unavailable'));
        render(
            <BrowserRouter>
                <Workspace />
            </BrowserRouter>
        );

        expect(await screen.findByText(/后端默认 LLM 未配置/)).toBeTruthy();
        fireEvent.click(screen.getByRole('button', { name: '重新检查配置' }));

        await waitFor(() => {
            expect(mockFetch).toHaveBeenCalledTimes(2);
        });
        expect(screen.getByText(/后端默认 LLM 未配置/)).toBeTruthy();
    });

    it('shows onboarding overlay when backend config response has malformed hasDefault', async () => {
        mockFetch.mockResolvedValue({ ok: true, json: () => Promise.resolve({ hasDefault: 'false' }) });
        render(
            <BrowserRouter>
                <Workspace />
            </BrowserRouter>
        );

        const onboarding = await screen.findByText(/后端默认 LLM 未配置/);
        expect(onboarding).toBeTruthy();
    });

    it('does not show stale onboarding when config check resolves after chat starts', async () => {
        let resolveConfig: (value: { ok: boolean; json: () => Promise<{ hasDefault: boolean }> }) => void = () => {};
        const pendingConfig = new Promise<{ ok: boolean; json: () => Promise<{ hasDefault: boolean }> }>((resolve) => {
            resolveConfig = resolve;
        });
        mockFetch.mockReturnValueOnce(pendingConfig);

        render(
            <BrowserRouter>
                <Workspace />
            </BrowserRouter>
        );

        await waitFor(() => {
            expect(mockFetch).toHaveBeenCalledWith('/new-agents/api/config');
        });

        act(() => {
            useStore.getState().addMessage({
                id: 'user-1',
                role: 'user',
                content: '已经开始对话',
                timestamp: 1,
            });
        });

        await act(async () => {
            resolveConfig({
                ok: true,
                json: () => Promise.resolve({ hasDefault: false }),
            });
            await pendingConfig;
            await Promise.resolve();
        });

        expect(screen.queryByText(/后端默认 LLM 未配置/)).toBeNull();
    });

    it('redirects when workflow slug belongs to a different agent than the URL agent', async () => {
        mockUseParams.mockReturnValue({
            agentId: 'lisa',
            workflowId: 'idea-brainstorm',
        });
        mockFetch.mockResolvedValue({ ok: true, json: () => Promise.resolve({ hasDefault: true }) });

        render(
            <BrowserRouter>
                <Workspace />
            </BrowserRouter>
        );

        await waitFor(() => {
            expect(mockNavigate).toHaveBeenCalledWith(
                '/workspace/alex/idea-brainstorm',
                { replace: true }
            );
        });
    });

    it('restores workspace state from the runId query parameter', async () => {
        window.history.pushState({}, '', '/new-agents/workspace/lisa/test-design?runId=run-123');
        mockUseParams.mockReturnValue({
            agentId: 'lisa',
            workflowId: 'test-design',
        });
        mockFetch.mockResolvedValue({ ok: true, json: () => Promise.resolve({ hasDefault: true }) });
        vi.mocked(fetchRunSnapshot).mockResolvedValue({
            run: {
                id: 'run-123',
                workflowId: 'TEST_DESIGN',
                agentId: 'lisa',
                currentStageId: 'STRATEGY',
                status: 'active',
                model: 'test-model',
            },
            messages: [
                {
                    role: 'user',
                    content: '用户需求: 登录功能',
                    sequenceIndex: 1,
                },
                {
                    role: 'assistant',
                    content: '已更新测试策略。',
                    sequenceIndex: 2,
                },
            ],
            artifacts: [
                {
                    stageId: 'STRATEGY',
                    content: '# 测试策略蓝图',
                    versionNumber: 1,
                },
            ],
            contextSummaries: [],
            artifactComments: [],
            artifactSectionLocks: [],
            artifactAuditEvents: [],
        });

        render(
            <BrowserRouter>
                <Workspace />
            </BrowserRouter>
        );

        await waitFor(() => {
            expect(fetchRunSnapshot).toHaveBeenCalledWith('run-123');
        });
        await waitFor(() => {
            expect(useStore.getState().currentRunId).toBe('run-123');
        });
        expect(useStore.getState().workflow).toBe('TEST_DESIGN');
        expect(useStore.getState().stageIndex).toBe(1);
        expect(useStore.getState().artifactContent).toBe('# 测试策略蓝图');
        expect(useStore.getState().chatHistory[0].content).toBe('用户需求: 登录功能');
        expect(mockNavigate).not.toHaveBeenCalledWith(
            expect.stringContaining('/workspace/lisa/test-design?runId=run-123'),
            expect.anything()
        );
    });

    it('prefers the server snapshot when the query run id matches stale local state', async () => {
        window.history.pushState({}, '', '/new-agents/workspace/lisa/test-design?runId=run-123');
        mockUseParams.mockReturnValue({
            agentId: 'lisa',
            workflowId: 'test-design',
        });
        useStore.setState({
            currentRunId: 'run-123',
            stageIndex: 0,
            chatHistory: [{
                id: 'stale-message',
                role: 'user',
                content: '陈旧本地会话',
                timestamp: 1,
            }],
            artifactContent: '# 陈旧本地产物',
            stageArtifacts: { CLARIFY: '# 陈旧本地产物' },
        });
        mockFetch.mockResolvedValue({ ok: true, json: () => Promise.resolve({ hasDefault: true }) });
        vi.mocked(fetchRunSnapshot).mockResolvedValue({
            run: {
                id: 'run-123',
                workflowId: 'TEST_DESIGN',
                agentId: 'lisa',
                currentStageId: 'STRATEGY',
                status: 'active',
                model: 'test-model',
            },
            messages: [{
                role: 'user',
                content: '服务端权威会话',
                sequenceIndex: 1,
            }],
            artifacts: [{
                stageId: 'STRATEGY',
                content: '# 服务端权威产物',
                versionNumber: 2,
            }],
            contextSummaries: [],
            artifactComments: [],
            artifactSectionLocks: [],
            artifactAuditEvents: [],
        });

        render(
            <BrowserRouter>
                <Workspace />
            </BrowserRouter>
        );

        await waitFor(() => {
            expect(fetchRunSnapshot).toHaveBeenCalledWith('run-123');
        });
        await waitFor(() => {
            expect(useStore.getState().artifactContent).toBe('# 服务端权威产物');
        });
        expect(useStore.getState().chatHistory[0].content).toBe('服务端权威会话');
        expect(useStore.getState().stageIndex).toBe(1);
    });

    it('redirects to the snapshot workflow when runId query points to a different workflow', async () => {
        window.history.pushState({}, '', '/new-agents/workspace/lisa/test-design?runId=alex-run-123');
        mockUseParams.mockReturnValue({
            agentId: 'lisa',
            workflowId: 'test-design',
        });
        mockFetch.mockResolvedValue({ ok: true, json: () => Promise.resolve({ hasDefault: true }) });
        vi.mocked(fetchRunSnapshot).mockResolvedValue({
            run: {
                id: 'alex-run-123',
                workflowId: 'VALUE_DISCOVERY',
                agentId: 'alex',
                currentStageId: 'BLUEPRINT',
                status: 'active',
                model: 'test-model',
            },
            messages: [],
            artifacts: [],
            contextSummaries: [],
            artifactComments: [],
            artifactSectionLocks: [],
            artifactAuditEvents: [],
        });

        render(
            <BrowserRouter>
                <Workspace />
            </BrowserRouter>
        );

        await waitFor(() => {
            expect(useStore.getState().currentRunId).toBe('alex-run-123');
        });
        expect(mockNavigate).toHaveBeenCalledWith(
            '/workspace/alex/value-discovery?runId=alex-run-123',
            { replace: true }
        );
    });
});
