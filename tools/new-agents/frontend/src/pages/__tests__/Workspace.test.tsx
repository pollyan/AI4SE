import { describe, it, expect, beforeEach, vi } from 'vitest';
import { act, render, screen, waitFor } from '@testing-library/react';
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

import { Workspace } from '../../pages/Workspace';

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
        mockUseParams.mockReturnValue({});
        useStore.setState({
            chatHistory: [],
            workflow: 'TEST_DESIGN',
            stageIndex: 0,
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
        expect(screen.getByText(/NEW_AGENTS_DEFAULT_LLM_API_KEY/)).toBeTruthy();
        expect(screen.getByText(/NEW_AGENTS_DEFAULT_LLM_MODEL/)).toBeTruthy();
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
});
