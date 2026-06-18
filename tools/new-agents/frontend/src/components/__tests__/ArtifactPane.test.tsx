import { describe, it, expect, beforeEach, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { ArtifactPane } from '../ArtifactPane';
import { useStore } from '../../store';

// Mock Mermaid component
vi.mock('../Mermaid', () => ({
    Mermaid: ({
        chart,
        onRetry,
    }: {
        chart: string;
        onRetry?: () => Promise<boolean>;
    }) => (
        <div data-testid="mermaid">
            {chart}
            {onRetry && <button type="button">重新生成图表</button>}
        </div>
    ),
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
    const originalCreateElement = document.createElement.bind(document);

    beforeEach(() => {
        vi.restoreAllMocks();
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 0,
            artifactContent: '',
            artifactHistory: [],
            artifactTruncated: false,
            isGenerating: false,
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

    it('shows a friendly animated artifact generation state while generating', () => {
        useStore.setState({
            artifactContent: '# 需求分析文档\n\n初始内容',
            isGenerating: true,
        });

        render(<ArtifactPane />);

        expect(screen.getByText('正在构建产出物')).toBeTruthy();
        expect(screen.getByText('正在构建右侧产出物')).toBeTruthy();
        expect(screen.getByTestId('artifact-generation-animation')).toBeTruthy();
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

    it('does not expose Mermaid retry actions in read-only history preview', () => {
        useStore.setState({
            artifactContent: '# Current artifact',
            artifactHistory: [
                {
                    id: 'v1',
                    timestamp: 123,
                    content: '# Historical artifact\n\n```mermaid\ngraph TD\nA-->B\n```',
                    stageId: 'CLARIFY',
                },
            ],
        });

        render(<ArtifactPane />);
        fireEvent.click(screen.getByTitle('历史版本'));

        expect(screen.getByText(/版本预览/)).toBeTruthy();
        expect(screen.getByTestId('mermaid').textContent).toContain('graph TD');
        expect(screen.queryByRole('button', { name: '重新生成图表' })).toBeNull();
    });

    it('only lists history versions for the current workflow stage', () => {
        const artifactHistory = [
            {
                id: 'clarify-version',
                timestamp: 123,
                content: '# CLARIFY version\n\n需求澄清版本',
                stageId: 'CLARIFY',
            },
            {
                id: 'strategy-version',
                timestamp: 456,
                content: '# STRATEGY version\n\n策略制定版本',
                stageId: 'STRATEGY',
            },
        ];
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 1,
            artifactContent: '# Current strategy artifact',
            artifactHistory,
        });

        render(<ArtifactPane />);
        fireEvent.click(screen.getByTitle('历史版本'));

        expect(screen.getAllByText('STRATEGY version').length).toBeGreaterThan(0);
        expect(screen.queryByText('CLARIFY version')).toBeNull();
    });

    it('downloads artifact with a workflow-specific filename', () => {
        const createdAnchors: HTMLAnchorElement[] = [];
        const click = vi.fn();
        vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:artifact');
        vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});
        vi.spyOn(document, 'createElement').mockImplementation((tagName, options) => {
            const element = originalCreateElement(tagName, options);
            if (tagName.toLowerCase() === 'a') {
                Object.defineProperty(element, 'click', {
                    configurable: true,
                    value: click,
                });
                createdAnchors.push(element as HTMLAnchorElement);
            }
            return element;
        });
        useStore.setState({
            workflow: 'REQ_REVIEW',
            artifactContent: '# 需求评审报告',
        });

        render(<ArtifactPane />);
        fireEvent.click(screen.getByTitle('下载'));

        expect(createdAnchors).toHaveLength(1);
        expect(createdAnchors[0].download).toBe('req_review_artifact.md');
        expect(createdAnchors[0].download).not.toBe('lisa_artifact.md');
        expect(click).toHaveBeenCalledTimes(1);
    });
});
