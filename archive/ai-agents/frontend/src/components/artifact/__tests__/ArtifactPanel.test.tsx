import { render, screen } from '@testing-library/react';
import { ArtifactPanel, ArtifactProgress } from '@/components/ArtifactPanel';
// Path from `src/components/artifact/__tests__/` to `components/ArtifactPanel.tsx`:
// `../../../../components/ArtifactPanel`.
// Wait, `src` and `components` are siblings in `frontend/`.
// So `frontend/src/components/artifact/__tests__`.
// `../../../../components` is correct.
// Let's check alias. `@/components`? `vite.config.ts` alias `@` -> `.`.
// So `@/components/ArtifactPanel`.

import { describe, it, expect, vi } from 'vitest';
import { RequirementDoc } from '@/src/types/artifact';

// Mock StructuredRequirementView to easier detection
vi.mock('@/src/components/artifact/StructuredRequirementView', () => ({
    StructuredRequirementView: () => <div data-testid="structured-view">Structured View</div>
}));

// Mock ReactMarkdown
vi.mock('react-markdown', () => ({
    default: ({ children }: any) => <div data-testid="markdown-view">{children}</div>
}));

// Mock remark-gfm
vi.mock('remark-gfm', () => ({ default: () => { } }));

describe('ArtifactPanel Dual Rendering', () => {
    const mockProgress: ArtifactProgress = {
        template: [{ stageId: 'stage1', artifactKey: 'key1', name: 'Artifact 1' }],
        completed: [],
        generating: null
    };

    it('renders StructuredRequirementView when structuredArtifacts is present', () => {
        const artifacts = { 'key1': '# Markdown Content' };
        const structuredArtifacts: Record<string, RequirementDoc> = {
            'key1': {
                scope: [],
                out_of_scope: [],
                features: [],
                flow_mermaid: "",
                rules: [],
                assumptions: [],
                nfr_markdown: ""
            }
        };

        render(
            <ArtifactPanel
                artifactProgress={mockProgress}
                selectedStageId="stage1"
                currentStageId="stage1"
                artifacts={artifacts}
                structuredArtifacts={structuredArtifacts}
                streamingArtifactKey={null}
                streamingArtifactContent={null}
                onBackToCurrentStage={() => { }}
            />
        );

        expect(screen.getByTestId('structured-view')).toBeInTheDocument();
        expect(screen.queryByTestId('markdown-view')).not.toBeInTheDocument();
    });

    it('renders Markdown when structuredArtifacts is missing', () => {
        const artifacts = { 'key1': '# Markdown Content' };

        render(
            <ArtifactPanel
                artifactProgress={mockProgress}
                selectedStageId="stage1"
                currentStageId="stage1"
                artifacts={artifacts}
                structuredArtifacts={{}}
                streamingArtifactKey={null}
                streamingArtifactContent={null}
                onBackToCurrentStage={() => { }}
            />
        );

        expect(screen.queryByTestId('structured-view')).not.toBeInTheDocument();
        expect(screen.getByTestId('markdown-view')).toBeInTheDocument();
        expect(screen.getByText('# Markdown Content')).toBeInTheDocument();
    });
});
