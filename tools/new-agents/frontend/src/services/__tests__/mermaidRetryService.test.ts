import { describe, it, expect, vi, beforeEach } from 'vitest';
import { retryMermaidGeneration } from '../mermaidRetryService';

const { mockMermaidParse } = vi.hoisted(() => ({
    mockMermaidParse: vi.fn(),
}));

vi.mock('mermaid', () => ({
    default: {
        parse: mockMermaidParse,
    },
}));

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
        mockMermaidParse.mockResolvedValue({});
    });

    it('should request typed Mermaid repair endpoint, parse repaired code, and return repaired code', async () => {
        vi.mocked(fetch).mockResolvedValue(new Response(
            JSON.stringify({ repairedCode: 'graph TD;\n  A-->B;' }),
            {
                status: 200,
                headers: { 'Content-Type': 'application/json' },
            },
        ));

        const result = await retryMermaidGeneration('broken code', 'Syntax Error', 10);

        expect(result).toBe('graph TD;\n  A-->B;');
        expect(mockMermaidParse).toHaveBeenCalledWith(
            'graph TD;\n  A-->B;',
            { suppressErrors: false },
        );
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

    it('should include artifact contract context when provided', async () => {
        vi.mocked(fetch).mockResolvedValue(new Response(
            JSON.stringify({ repairedCode: 'graph TD;\n  A-->B;' }),
            {
                status: 200,
                headers: { 'Content-Type': 'application/json' },
            },
        ));

        const result = await retryMermaidGeneration(
            'broken code',
            'Syntax Error',
            2,
            {
                workflowId: 'TEST_DESIGN',
                stageId: 'CLARIFY',
                currentArtifact: '# 需求分析文档\n\n```mermaid\ngraph TD\n  A-->\n```',
            },
        );

        expect(result).toBe('graph TD;\n  A-->B;');
        expect(fetch).toHaveBeenCalledWith(
            '/new-agents/api/utils/mermaid/repair',
            expect.objectContaining({
                body: JSON.stringify({
                    brokenCode: 'broken code',
                    errorMessage: 'Syntax Error',
                    blockIndex: 2,
                    workflowId: 'TEST_DESIGN',
                    stageId: 'CLARIFY',
                    currentArtifact: '# 需求分析文档\n\n```mermaid\ngraph TD\n  A-->\n```',
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

    it('should return null when repaired code still fails Mermaid parse', async () => {
        vi.mocked(fetch).mockResolvedValue(new Response(
            JSON.stringify({ repairedCode: 'graph TD;\n  A-->' }),
            {
                status: 200,
                headers: { 'Content-Type': 'application/json' },
            },
        ));
        mockMermaidParse.mockRejectedValueOnce(new Error('Syntax Error'));

        const result = await retryMermaidGeneration('broken code', 'error', 0);

        expect(result).toBeNull();
        expect(mockMermaidParse).toHaveBeenCalledWith(
            'graph TD;\n  A-->',
            { suppressErrors: false },
        );
    });

    it('should return null when Mermaid parse returns false for repaired code', async () => {
        vi.mocked(fetch).mockResolvedValue(new Response(
            JSON.stringify({ repairedCode: 'graph TD;\n  A-->B;' }),
            {
                status: 200,
                headers: { 'Content-Type': 'application/json' },
            },
        ));
        mockMermaidParse.mockResolvedValueOnce(false);

        const result = await retryMermaidGeneration('broken code', 'error', 0);

        expect(result).toBeNull();
    });
});
