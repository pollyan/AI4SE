import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
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

    it('renders successfully with valid chart data', async () => {
        vi.mocked(storeModule.useStore).mockReturnValue(false); // isGenerating = false

        const chartCode = 'graph TD\nA-->B';
        const { container } = render(<Mermaid chart={chartCode} />);

        await waitFor(() => {
            expect(mermaid.render).toHaveBeenCalled();
            expect(container.innerHTML).toContain('mocked-svg');
        });
    });

    it('shows loading animation when generating and encountering parse error (streaming state)', async () => {
        vi.mocked(storeModule.useStore).mockReturnValue(true); // isGenerating = true

        // Simulate parse failure (e.g., incomplete code while streaming)
        vi.mocked(mermaid.parse).mockRejectedValue(new Error('Syntax Error'));

        const incompleteChartCode = 'graph TD\nA-->';
        render(<Mermaid chart={incompleteChartCode} />);

        await waitFor(() => {
            expect(screen.getByText('正在绘制流程图...')).toBeDefined();
        });
    });

    it('shows degraded error UI when generation is complete but code is completely broken', async () => {
        vi.mocked(storeModule.useStore).mockReturnValue(false); // isGenerating = false

        // Simulate total failure even after aggressive sanitization
        vi.mocked(mermaid.parse).mockResolvedValue(false as any);

        const totallyBrokenCode = 'invalid mermaid entirely';
        render(<Mermaid chart={totallyBrokenCode} />);

        await waitFor(() => {
            expect(screen.getByText('图表语法受损，已启动格式降级')).toBeDefined();
            // Verify code fold element exists
            expect(screen.getByText('查看原始代码')).toBeDefined();
            // Verify original code is preserved in pre block
            expect(screen.getByText(totallyBrokenCode)).toBeDefined();
        });
    });
});
