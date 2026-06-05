import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
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
            pendingStageTransition: null,
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

    it('does not render stage transition confirmation in the header when pendingStageTransition exists', () => {
        useStore.setState({ pendingStageTransition: { fromStageIndex: 0, toStageIndex: 1 }, stageIndex: 0 });
        renderHeader();
        expect(screen.queryByText(/AI 建议进入下一阶段/)).toBeNull();
    });

    it('hides stage transition banner when pendingStageTransition is false', () => {
        useStore.setState({ pendingStageTransition: null });
        renderHeader();
        expect(screen.queryByText(/AI 建议进入下一阶段/)).toBeNull();
    });
});
