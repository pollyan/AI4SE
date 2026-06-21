import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { Mermaid } from '../Mermaid';
import mermaid from 'mermaid';
import type { ParseResult, RenderResult } from 'mermaid';

// Mock mermaid rendering to prevent actual heavy DOM manipulations
vi.mock('mermaid', () => {
    return {
        default: {
            initialize: vi.fn(),
            render: vi.fn(),
            parse: vi.fn()
        }
    };
});

describe('Mermaid Component', () => {
    const successfulParseResult: ParseResult = {
        diagramType: 'graph',
        config: {},
    };
    const successfulRenderResult: RenderResult = {
        svg: '<svg id="mocked-svg"></svg>',
        bindFunctions: undefined,
        diagramType: 'graph',
    };

    beforeEach(() => {
        vi.clearAllMocks();
        // Default mock implementation
        vi.mocked(mermaid.parse).mockResolvedValue(successfulParseResult);
        vi.mocked(mermaid.render).mockResolvedValue(successfulRenderResult);
    });

    it('renders successfully with valid chart data without triggering onRetry (AC8 - F10)', async () => {
        const mockOnRetry = vi.fn().mockResolvedValue(true);
        const chartCode = 'graph TD\nStreamingStart-->StreamingEnd';

        const { container } = render(<Mermaid chart={chartCode} onRetry={mockOnRetry} blockIndex={0} />);

        await waitFor(() => {
            expect(mermaid.render).toHaveBeenCalled();
            expect(container.innerHTML).toContain('mocked-svg');
            expect(mockOnRetry).not.toHaveBeenCalled();
        });
    });

    it('reports render success through the success callback', async () => {
        const mockOnRenderSuccess = vi.fn();
        const chartCode = 'graph TD\nCallbackStart-->CallbackEnd';

        render(<Mermaid chart={chartCode} blockIndex={3} onRenderSuccess={mockOnRenderSuccess} />);

        await waitFor(() => {
            expect(mockOnRenderSuccess).toHaveBeenCalledWith(3);
        });
    });

    it('reuses the rendered SVG when the same chart remounts during artifact streaming', async () => {
        const chartCode = 'graph TD\nRemountStart-->RemountEnd';

        const firstRender = render(<Mermaid chart={chartCode} blockIndex={0} />);

        await waitFor(() => {
            expect(firstRender.container.innerHTML).toContain('mocked-svg');
        });
        expect(mermaid.render).toHaveBeenCalledTimes(1);

        firstRender.unmount();
        const secondRender = render(<Mermaid chart={chartCode} blockIndex={0} />);

        await waitFor(() => {
            expect(secondRender.container.innerHTML).toContain('mocked-svg');
        });
        expect(mermaid.render).toHaveBeenCalledTimes(1);
    });

    it('does not rerender the same chart when callback identities change', async () => {
        const chartCode = 'graph TD\nStableStart-->StableEnd';

        const firstOnRenderSuccess = vi.fn();
        const { container, rerender } = render(
            <Mermaid chart={chartCode} blockIndex={0} onRenderSuccess={firstOnRenderSuccess} />
        );

        await waitFor(() => {
            expect(container.innerHTML).toContain('mocked-svg');
        });
        expect(mermaid.render).toHaveBeenCalledTimes(1);
        expect(firstOnRenderSuccess).toHaveBeenCalledWith(0);

        const nextOnRenderSuccess = vi.fn();
        rerender(<Mermaid chart={chartCode} blockIndex={0} onRenderSuccess={nextOnRenderSuccess} />);

        await waitFor(() => {
            expect(container.innerHTML).toContain('mocked-svg');
        });
        expect(mermaid.render).toHaveBeenCalledTimes(1);
        expect(nextOnRenderSuccess).not.toHaveBeenCalled();
    });

    it('shows loading animation when generating and encountering parse error (AC6)', async () => {
        vi.mocked(mermaid.parse).mockRejectedValue(new Error('Syntax Error'));

        const incompleteChartCode = 'graph TD\nA-->';
        render(<Mermaid chart={incompleteChartCode} />);

        await waitFor(() => {
            expect(screen.getByText('正在绘制流程图...')).toBeDefined();
        });
    });

    it('does not auto retry when code fails and onRetry is provided', async () => {
        vi.mocked(mermaid.parse).mockRejectedValue(new Error('Syntax Error'));

        const mockOnRetry = vi.fn().mockResolvedValue(true);
        const mockOnRenderError = vi.fn();
        const brokenCode = 'graph TD\nA-->?';

        render(<Mermaid chart={brokenCode} onRetry={mockOnRetry} onRenderError={mockOnRenderError} blockIndex={0} />);

        await waitFor(() => {
            expect(screen.getByText('重新生成图表')).toBeDefined();
        });
        expect(mockOnRetry).not.toHaveBeenCalled();
        expect(mockOnRenderError).toHaveBeenCalledWith(expect.objectContaining({
            code: brokenCode,
            message: 'Syntax Error',
            blockIndex: 0,
        }));
    });

    it('keeps the same broken code in error state on rerender without retrying', async () => {
        vi.mocked(mermaid.parse).mockRejectedValue(new Error('Syntax Error'));

        const mockOnRetry = vi.fn().mockResolvedValue(false);
        const brokenCode = 'graph TD\nbroken-same';

        const { rerender } = render(<Mermaid chart={brokenCode} onRetry={mockOnRetry} blockIndex={0} />);

        await waitFor(() => {
            expect(screen.getByText('重新生成图表')).toBeDefined();
        });
        expect(mockOnRetry).not.toHaveBeenCalled();

        rerender(<Mermaid chart={brokenCode} onRetry={mockOnRetry} blockIndex={0} />);

        await waitFor(() => {
            expect(screen.getByText('重新生成图表')).toBeDefined();
        });
        expect(mockOnRetry).not.toHaveBeenCalled();
    });

    it('shows error state when onRetry returns false (AC5 / F5)', async () => {
        vi.mocked(mermaid.parse).mockRejectedValue(new Error('Syntax Error'));

        const mockOnRetry = vi.fn().mockResolvedValue(false); // fail recovery
        const brokenCode = 'graph TD\nfail';

        render(<Mermaid chart={brokenCode} onRetry={mockOnRetry} blockIndex={0} />);

        await waitFor(() => {
            expect(screen.getByText('重新生成图表')).toBeDefined();
        });
        expect(mockOnRetry).not.toHaveBeenCalled();
    });

    it('allows manual retry by clicking the button in degraded UI (AC3 / AC4)', async () => {
        vi.mocked(mermaid.parse).mockRejectedValue(new Error('Syntax Error'));

        const mockOnRetry = vi.fn().mockResolvedValue(false);
        const brokenCode = 'graph TD\nmanual';

        render(<Mermaid chart={brokenCode} onRetry={mockOnRetry} blockIndex={0} />);

        // Wait to reach error state
        let retryBtn: HTMLElement;
        await waitFor(() => {
            retryBtn = screen.getByText('重新生成图表');
            expect(retryBtn).toBeDefined();
        });

        // Click the manual retry button
        fireEvent.click(retryBtn!);

        await waitFor(() => {
            expect(mockOnRetry).toHaveBeenCalledTimes(1);
            expect(mockOnRetry).toHaveBeenCalledWith(brokenCode, 'Syntax Error', 0);
        });
    });

    it('returns to degraded UI when manual retry rejects', async () => {
        vi.mocked(mermaid.parse).mockRejectedValue(new Error('Syntax Error'));

        const mockOnRetry = vi.fn().mockRejectedValue(new Error('repair endpoint unavailable'));
        const brokenCode = 'graph TD\nmanual-reject';

        render(<Mermaid chart={brokenCode} onRetry={mockOnRetry} blockIndex={0} />);

        let retryBtn: HTMLElement;
        await waitFor(() => {
            retryBtn = screen.getByText('重新生成图表');
            expect(retryBtn).toBeDefined();
        });

        fireEvent.click(retryBtn!);

        await waitFor(() => {
            expect(mockOnRetry).toHaveBeenCalledTimes(1);
            expect(screen.queryByText('正在绘制流程图...')).toBeNull();
            expect(screen.getByText('重新生成图表')).toBeDefined();
            expect(screen.getByText('repair endpoint unavailable')).toBeDefined();
        });
    });
});
