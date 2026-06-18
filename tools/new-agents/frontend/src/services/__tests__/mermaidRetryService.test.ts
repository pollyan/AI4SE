import { describe, it, expect, vi, beforeEach } from 'vitest';
import { retryMermaidGeneration } from '../mermaidRetryService';

global.fetch = vi.fn();

// Mock store module
vi.mock('../../store', () => ({
    useStore: {
        getState: vi.fn().mockReturnValue({
            workflow: 'test-workflow',
            stageIndex: 0
        })
    }
}));

describe('mermaidRetryService', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('should request typed Mermaid repair endpoint and return repaired code', async () => {
        vi.mocked(fetch).mockResolvedValue(new Response(
            JSON.stringify({ repairedCode: 'graph TD;\n  A-->B;' }),
            {
                status: 200,
                headers: { 'Content-Type': 'application/json' },
            },
        ));

        const result = await retryMermaidGeneration('broken code', 'Syntax Error', 10);

        expect(result).toBe('graph TD;\n  A-->B;');
        expect(fetch).toHaveBeenCalledWith(
            '/new-agents/api/utils/mermaid/repair',
            expect.objectContaining({
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    brokenCode: 'broken code',
                    errorMessage: 'Syntax Error',
                    blockIndex: 10,
                }),
            }),
        );
    });

    it('should return null when repair endpoint fails', async () => {
        vi.mocked(fetch).mockResolvedValue(new Response(
            JSON.stringify({ error: 'Repair failed' }),
            {
                status: 502,
                headers: { 'Content-Type': 'application/json' },
            },
        ));

        const result = await retryMermaidGeneration('broken code', 'error', 0);
        expect(result).toBeNull();
    });
});
