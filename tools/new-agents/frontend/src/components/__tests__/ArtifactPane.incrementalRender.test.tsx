import { describe, it, expect, beforeEach, vi } from 'vitest';
import type { ReactElement } from 'react';
import { act, render } from '@testing-library/react';
import { ArtifactPane } from '../ArtifactPane';
import { useStore } from '../../store';

const { markdownRenderCounts } = vi.hoisted(() => ({
    markdownRenderCounts: new Map<string, number>(),
}));

vi.mock('react-markdown', () => ({
    default: ({ children }: { children: unknown }) => {
        const content = String(children);
        markdownRenderCounts.set(content, (markdownRenderCounts.get(content) ?? 0) + 1);
        return <div data-testid="mock-react-markdown">{content}</div>;
    },
}));

vi.mock('../../services/runSnapshotService', async (importOriginal) => {
    const actual = await importOriginal<typeof import('../../services/runSnapshotService')>();
    return {
        ...actual,
        updateRunArtifact: vi.fn(),
        updateRunArtifactCollaboration: vi.fn(),
    };
});

vi.mock('../Mermaid', () => ({
    Mermaid: ({ chart }: { chart: string }) => <div data-testid="mermaid">{chart}</div>,
}));

vi.mock('../../services/mermaidRetryService', () => ({
    retryMermaidGeneration: vi.fn(),
}));

vi.mock('lucide-react', () => {
    const icons = [
        'Download',
        'Code',
        'Eye',
        'History',
        'X',
        'AlertTriangle',
        'GitCompare',
        'Edit3',
        'Save',
        'MessageSquare',
        'Trash2',
        'Lock',
        'Unlock',
        'MoreHorizontal',
    ];
    const mod: Record<string, () => ReactElement> = {};
    icons.forEach((name) => {
        mod[name] = () => <span>{name}</span>;
    });
    return mod;
});

describe('ArtifactPane incremental section rendering', () => {
    beforeEach(() => {
        markdownRenderCounts.clear();
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 0,
            artifactContent: '',
            artifactChangeIndex: [],
            artifactHistory: [],
            stageArtifacts: {},
            artifactTruncated: false,
            artifactVisualDiagnostics: [],
            currentRunId: null,
            isGenerating: false,
        });
    });

    it('does not rerender unchanged markdown sections when another section changes', () => {
        const stableSection = '## 范围\n\n旧范围';
        const initialChangingSection = '## 风险\n\n旧风险';
        const nextChangingSection = '## 风险\n\n新风险';
        useStore.setState({
            artifactContent: `# 文档\n\n${stableSection}\n\n${initialChangingSection}`,
            stageArtifacts: {
                CLARIFY: `# 文档\n\n${stableSection}\n\n${initialChangingSection}`,
            },
        });

        render(<ArtifactPane />);

        expect(markdownRenderCounts.get(stableSection)).toBe(1);
        expect(markdownRenderCounts.get(initialChangingSection)).toBe(1);

        act(() => {
            useStore.getState().setArtifactContent(
                `# 文档\n\n${stableSection}\n\n${nextChangingSection}`,
            );
        });

        expect(markdownRenderCounts.get(stableSection)).toBe(1);
        expect(markdownRenderCounts.get(initialChangingSection)).toBe(1);
        expect(markdownRenderCounts.get(nextChangingSection)).toBe(1);
    });

    it('inserts a previously withheld middle section without rerendering stable anchors', () => {
        const firstSection = '## 范围\n\n稳定范围';
        const insertedSection = '## 规则\n\n后续闭合的业务规则';
        const thirdSection = '## 风险\n\n稳定风险';
        const initialArtifact = `# 文档\n\n${firstSection}\n\n${thirdSection}`;
        const expandedArtifact = `# 文档\n\n${firstSection}\n\n${insertedSection}\n\n${thirdSection}`;
        useStore.setState({
            artifactContent: initialArtifact,
            stageArtifacts: { CLARIFY: initialArtifact },
        });

        render(<ArtifactPane />);

        expect(markdownRenderCounts.get(firstSection)).toBe(1);
        expect(markdownRenderCounts.get(thirdSection)).toBe(1);

        act(() => {
            useStore.getState().setArtifactContent(expandedArtifact);
        });

        expect(markdownRenderCounts.get(firstSection)).toBe(1);
        expect(markdownRenderCounts.get(thirdSection)).toBe(1);
        expect(markdownRenderCounts.get(insertedSection)).toBe(1);
    });

    it('appends the metadata footer after business sections without rerendering them', () => {
        const businessSection = '## 业务结论\n\n业务正文保持稳定';
        const metadataSection = '## 文档信息\n\n文档元信息：Artifact 名称：需求分析 ｜ Workflow：TEST_DESIGN';
        const initialArtifact = `# 文档\n\n${businessSection}`;
        const completedArtifact = `${initialArtifact}\n\n${metadataSection}`;
        useStore.setState({
            artifactContent: initialArtifact,
            stageArtifacts: { CLARIFY: initialArtifact },
        });

        render(<ArtifactPane />);
        expect(markdownRenderCounts.get(businessSection)).toBe(1);

        act(() => {
            useStore.getState().setArtifactContent(completedArtifact);
        });

        expect(markdownRenderCounts.get(businessSection)).toBe(1);
        expect(markdownRenderCounts.get(metadataSection)).toBe(1);
        expect(useStore.getState().artifactContent.indexOf(businessSection))
            .toBeLessThan(useStore.getState().artifactContent.indexOf(metadataSection));
    });
});
