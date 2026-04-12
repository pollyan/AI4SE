import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Header } from '../Header';
import { useStore } from '../../store';
import { BrowserRouter } from 'react-router-dom';

// Mock react-router-dom navigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
    const actual = await vi.importActual('react-router-dom');
    return {
        ...actual,
        useNavigate: () => mockNavigate,
        useParams: () => ({ agentId: 'lisa' }),
    };
});

// Mock WorkflowDropdown
vi.mock('../WorkflowDropdown', () => ({
    WorkflowDropdown: () => <div data-testid="workflow-dropdown" />,
}));

// Mock lucide-react icons to avoid SVG complexity
vi.mock('lucide-react', () => {
    const icons = ['Settings', 'Share', 'Bot', 'Plus', 'AlertTriangle', 'ArrowLeft', 'ChevronRight'];
    const mod: Record<string, React.FC> = {};
    icons.forEach(name => {
        mod[name] = () => <span>{name}</span>;
    });
    return mod;
});

describe('Header Component', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 0,
            pendingStageTransition: false,
            chatHistory: [],
        });
    });

    function renderHeader() {
        return render(
            <BrowserRouter>
                <Header />
            </BrowserRouter>
        );
    }

    it('renders the app header with navigation and controls', () => {
        renderHeader();
        // Should have a "新会话" button
        expect(screen.getByText(/新会话/)).toBeTruthy();
        // Should have settings button area (Settings icon)
        expect(screen.getByText('Settings')).toBeTruthy();
    });

    it('shows stage transition confirmation banner when pendingStageTransition is true', () => {
        useStore.setState({ pendingStageTransition: true, stageIndex: 0 });
        renderHeader();
        expect(screen.getByText(/AI 建议进入下一阶段/)).toBeTruthy();
    });

    it('hides stage transition banner when pendingStageTransition is false', () => {
        useStore.setState({ pendingStageTransition: false });
        renderHeader();
        expect(screen.queryByText(/AI 建议进入下一阶段/)).toBeNull();
    });

    it('confirm button click triggers confirmStageTransition', () => {
        useStore.setState({ pendingStageTransition: true, stageIndex: 0 });
        renderHeader();
        const btn = screen.getByText(/确认进入/);
        fireEvent.click(btn);
        // After confirm, pendingStageTransition should be false
        expect(useStore.getState().pendingStageTransition).toBe(false);
        expect(useStore.getState().stageIndex).toBe(1);
    });
});
