import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ArtifactPane } from '../ArtifactPane';
import { useStore } from '../../store';

// Mock Mermaid component
vi.mock('../Mermaid', () => ({
    Mermaid: ({ chart }: { chart: string }) => <div data-testid="mermaid">{chart}</div>,
}));

// Mock mermaidRetryService
vi.mock('../../services/mermaidRetryService', () => ({
    retryMermaidGeneration: vi.fn(),
}));

// Mock lucide-react
vi.mock('lucide-react', () => {
    const icons = ['Download', 'Code', 'Eye', 'History', 'X', 'AlertTriangle'];
    const mod: Record<string, React.FC> = {};
    icons.forEach(name => {
        mod[name] = () => <span>{name}</span>;
    });
    return mod;
});

describe('ArtifactPane Component', () => {
    beforeEach(() => {
        useStore.setState({
            artifactContent: '',
            artifactHistory: [],
            artifactTruncated: false,
        });
    });

    it('shows placeholder when content is empty', () => {
        render(<ArtifactPane />);
        // Should render the pane with "当前产出物.md" header
        expect(screen.getByText(/当前产出物/)).toBeTruthy();
    });

    it('renders markdown content', () => {
        useStore.setState({ artifactContent: '# Hello World\n\nThis is **bold** text.' });
        const { container } = render(<ArtifactPane />);
        // ReactMarkdown renders the heading and paragraph
        expect(container.textContent).toContain('Hello World');
        expect(container.textContent).toContain('bold');
    });

    it('renders mermaid diagrams', () => {
        useStore.setState({ artifactContent: '```mermaid\ngraph TD\nA-->B\n```' });
        render(<ArtifactPane />);
        expect(screen.getByTestId('mermaid')).toBeTruthy();
    });

    it('renders code blocks', () => {
        useStore.setState({ artifactContent: '```python\nprint("hello")\n```' });
        render(<ArtifactPane />);
        expect(screen.getByText('python')).toBeTruthy();
    });
});
