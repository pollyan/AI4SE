import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Workspace } from '../../pages/Workspace';
import { useStore } from '../../store';
import { BrowserRouter } from 'react-router-dom';

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
        useStore.setState({
            isUserConfigured: false,
            chatHistory: [],
            workflow: 'TEST_DESIGN',
            stageIndex: 0,
        });
    });

    it('renders basic layout with ChatPane and ArtifactPane', () => {
        mockFetch.mockResolvedValue({ ok: true, json: () => Promise.resolve({ hasDefault: true }) });
        render(
            <BrowserRouter>
                <Workspace />
            </BrowserRouter>
        );
        expect(screen.getByTestId('header')).toBeTruthy();
        expect(screen.getByTestId('chat-pane')).toBeTruthy();
        expect(screen.getByTestId('artifact-pane')).toBeTruthy();
    });

    it('shows onboarding overlay when backend has no default config', async () => {
        mockFetch.mockResolvedValue({ ok: true, json: () => Promise.resolve({ hasDefault: false }) });
        render(
            <BrowserRouter>
                <Workspace />
            </BrowserRouter>
        );
        // Wait for async fetch + state update
        const onboarding = await screen.findByText(/配置你的 AI 模型/);
        expect(onboarding).toBeTruthy();
    });
});
