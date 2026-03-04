import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { Mermaid } from '../Mermaid';
import * as storeModule from '../../store';
import mermaid from 'mermaid';

// Mock the zustand store to control state
vi.mock('../../store', () => ({
    useStore: vi.fn(),
}));

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
    beforeEach(() => {
        vi.clearAllMocks();
        // Default mock implementation
        vi.mocked(mermaid.parse).mockResolvedValue({} as any);
        vi.mocked(mermaid.render).mockResolvedValue({ svg: '<svg id="mocked-svg"></svg>', bindFunctions: undefined, diagramType: 'graph' } as any);
    });

    it('renders successfully with valid chart data without triggering onRetry (AC8 - F10)', async () => {
        vi.mocked(storeModule.useStore).mockImplementation(((s: any) => s({ isGenerating: false })) as any); // isGenerating = false
        const mockOnRetry = vi.fn().mockResolvedValue(true);
        const chartCode = 'graph TD\nA-->B';

        const { container } = render(<Mermaid chart={chartCode} onRetry={mockOnRetry} blockIndex={0} />);

        await waitFor(() => {
            expect(mermaid.render).toHaveBeenCalled();
            expect(container.innerHTML).toContain('mocked-svg');
            expect(mockOnRetry).not.toHaveBeenCalled();
        });
    });

    it('shows loading animation when generating and encountering parse error (AC6)', async () => {
        vi.mocked(storeModule.useStore).mockImplementation(((s: any) => s({ isGenerating: true })) as any); // isGenerating = true
        vi.mocked(mermaid.parse).mockRejectedValue(new Error('Syntax Error'));

        const incompleteChartCode = 'graph TD\nA-->';
        render(<Mermaid chart={incompleteChartCode} />);

        await waitFor(() => {
            expect(screen.getByText('正在绘制流程图...')).toBeDefined();
        });
    });

    it('triggers automatic retry once when code fails and onRetry is provided (AC1)', async () => {
        vi.mocked(storeModule.useStore).mockImplementation(((s: any) => s({ isGenerating: false })) as any); // isGenerating = false
        vi.mocked(mermaid.parse).mockRejectedValue(new Error('Syntax Error'));

        const mockOnRetry = vi.fn().mockResolvedValue(true);
        const brokenCode = 'graph TD\nA-->?';

        render(<Mermaid chart={brokenCode} onRetry={mockOnRetry} blockIndex={0} />);

        await waitFor(() => {
            expect(mockOnRetry).toHaveBeenCalledTimes(1);
            expect(mockOnRetry).toHaveBeenCalledWith(brokenCode, 'Syntax Error', 0);
            // Component should be in loading state
            expect(screen.getByText('正在绘制流程图...')).toBeDefined();
        });
    });

    it('does not trigger automatic retry again for the same broken code hash (AC2 / F1)', async () => {
        vi.mocked(storeModule.useStore).mockImplementation(((s: any) => s({ isGenerating: false })) as any);
        vi.mocked(mermaid.parse).mockRejectedValue(new Error('Syntax Error'));

        const mockOnRetry = vi.fn().mockResolvedValue(false); // simulate retry failure
        const brokenCode = 'graph TD\nbroken-same';

        const { rerender } = render(<Mermaid chart={brokenCode} onRetry={mockOnRetry} blockIndex={0} />);

        // First Mount: Should trigger onRetry once and fallback to error state since it returned false
        await waitFor(() => {
            expect(mockOnRetry).toHaveBeenCalledTimes(1);
            expect(screen.getByText('重新生成图表')).toBeDefined();
        });

        // Rerender with the SAME exact code (simulate what happens if the returned code from LLM is exactly the same or we just rerender)
        rerender(<Mermaid chart={brokenCode} onRetry={mockOnRetry} blockIndex={0} />);

        // Should NOT trigger onRetry again automatically
        await waitFor(() => {
            expect(mockOnRetry).toHaveBeenCalledTimes(1); // Still 1
            expect(screen.getByText('重新生成图表')).toBeDefined(); // Remains in error state
        });
    });

    it('shows error state when onRetry returns false (AC5 / F5)', async () => {
        vi.mocked(storeModule.useStore).mockImplementation(((s: any) => s({ isGenerating: false })) as any);
        vi.mocked(mermaid.parse).mockRejectedValue(new Error('Syntax Error'));

        const mockOnRetry = vi.fn().mockResolvedValue(false); // fail recovery
        const brokenCode = 'graph TD\nfail';

        render(<Mermaid chart={brokenCode} onRetry={mockOnRetry} blockIndex={0} />);

        await waitFor(() => {
            expect(mockOnRetry).toHaveBeenCalledTimes(1);
            expect(screen.getByText('重新生成图表')).toBeDefined();
        });
    });

    it('allows manual retry by clicking the button in degraded UI (AC3 / AC4)', async () => {
        vi.mocked(storeModule.useStore).mockImplementation(((s: any) => s({ isGenerating: false })) as any);
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

        // Should call onRetry again
        await waitFor(() => {
            expect(mockOnRetry).toHaveBeenCalledTimes(2); // Auto (1) + Manual (1)
        });
    });
});
