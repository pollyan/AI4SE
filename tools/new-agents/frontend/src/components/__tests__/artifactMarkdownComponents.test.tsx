import ReactMarkdown from 'react-markdown';
import { render, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { createArtifactMarkdownComponents } from '../artifactMarkdownComponents';

describe('artifact markdown components', () => {
    it('reports a structured visual failure through the shared callback with its block index', async () => {
        const onStructuredVisualValidationError = vi.fn();

        render(
            <ReactMarkdown
                components={createArtifactMarkdownComponents({
                    currentStageId: 'CLARIFY',
                    reportVisualDiagnostics: true,
                    onStructuredVisualValidationError,
                })}
            >
                {'```ai4se-visual\n{ broken\n```'}
            </ReactMarkdown>
        );

        await waitFor(() => {
            expect(onStructuredVisualValidationError).toHaveBeenCalledWith(0, '结构化可视化必须是合法 JSON。');
        });
    });
});
