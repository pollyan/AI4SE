import { describe, it, expect, vi, beforeEach } from 'vitest';
import { retryMermaidGeneration } from '../mermaidRetryService';
import * as llmClientModule from '../../core/utils/llmClient';

// Mock llmClient
vi.mock('../../core/utils/llmClient', () => ({
    collectLlmResponse: vi.fn()
}));

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

    it('should return pure mermaid code stripped of markdown fences', async () => {
        // Setup mock response
        vi.mocked(llmClientModule.collectLlmResponse).mockResolvedValue(
            '```mermaid\ngraph TD;\n  A-->B;\n```'
        );

        const result = await retryMermaidGeneration('broken code', 'Syntax Error', 10);

        // Verify it drops the fences
        expect(result).toBe('graph TD;\n  A-->B;');

        // Verify correct prompt construction
        expect(llmClientModule.collectLlmResponse).toHaveBeenCalledWith(
            expect.arrayContaining([
                expect.objectContaining({ role: 'system' }),
                expect.objectContaining({ role: 'user', content: expect.stringContaining('Syntax Error') })
            ])
        );
    });

    it('should handle missing fences gracefully', async () => {
        vi.mocked(llmClientModule.collectLlmResponse).mockResolvedValue(
            'graph TD;\n  C-->D;'
        );

        const result = await retryMermaidGeneration('broken code', 'error', 0);
        expect(result).toBe('graph TD;\n  C-->D;');
    });

    it('should return null when network request fails', async () => {
        vi.mocked(llmClientModule.collectLlmResponse).mockRejectedValue(new Error('Network error'));

        // Should not throw, should return null
        const result = await retryMermaidGeneration('broken code', 'error', 0);
        expect(result).toBeNull();
    });
});
