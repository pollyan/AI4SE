import { describe, it, expect, vi, beforeEach } from 'vitest';
import { collectLlmResponse } from '../llmClient';
import * as storeModule from '../../../store';
import OpenAI from 'openai';

// Mock zustand store
vi.mock('../../../store', () => ({
    useStore: {
        getState: vi.fn()
    }
}));

export const mockCreate = vi.fn();
vi.mock('openai', () => {
    return {
        default: class {
            constructor() { }
            chat = {
                completions: {
                    create: mockCreate
                }
            };
        }
    };
});

// Mock fetch
global.fetch = vi.fn();

describe('llmClient - collectLlmResponse', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('should use fetch via proxy when user is not configured or apiKey is missing', async () => {
        // Setup store mock
        vi.mocked(storeModule.useStore.getState).mockReturnValue({
            isUserConfigured: false,
            apiKey: '',
            baseUrl: '',
            model: 'default-model'
        } as any);

        // Setup fetch mock for SSE
        const encoder = new TextEncoder();
        const mockStream = new ReadableStream({
            start(controller) {
                controller.enqueue(encoder.encode('data: {"response": "Hello"}\n\n'));
                controller.enqueue(encoder.encode('data: {"response": " World"}\n\n'));
                controller.enqueue(encoder.encode('data: [DONE]\n\n'));
                controller.close();
            }
        });

        vi.mocked(fetch).mockResolvedValue({
            ok: true,
            body: { getReader: () => mockStream.getReader() }
        } as any);

        const result = await collectLlmResponse([{ role: 'user', content: 'Hi' }]);

        expect(fetch).toHaveBeenCalledWith('/new-agents/api/chat/stream', expect.objectContaining({
            method: 'POST',
            body: expect.stringContaining('"temperature":0.7') // simple verification
        }));
        expect(result).toBe('Hello World');
    });

    it('should use OpenAI SDK directly when user is configured and apiKey exists', async () => {
        // Setup store mock
        vi.mocked(storeModule.useStore.getState).mockReturnValue({
            isUserConfigured: true,
            apiKey: 'test-api-key',
            baseUrl: 'https://test.api',
            model: 'test-model'
        } as any);

        // Setup OpenAI mock
        mockCreate.mockResolvedValue((async function* () {
            yield { choices: [{ delta: { content: 'Direct' } }] };
            yield { choices: [{ delta: { content: ' Message' } }] };
        })());

        const result = await collectLlmResponse([{ role: 'user', content: 'Hi' }]);

        // In vitest when we mock a class constructor like this, checking instantiation args is tricky
        // so we just verify the `create` method was called correctly

        expect(mockCreate).toHaveBeenCalledWith(
            expect.objectContaining({
                model: 'test-model',
                stream: true
            }),
            expect.any(Object)
        );

        expect(result).toBe('Direct Message');
    });

    it('should throw error when fetch returns false ok', async () => {
        vi.mocked(storeModule.useStore.getState).mockReturnValue({
            isUserConfigured: false
        } as any);

        vi.mocked(fetch).mockResolvedValue({
            ok: false,
            json: async () => ({ error: 'Proxy Backend Failed' })
        } as any);

        await expect(collectLlmResponse([])).rejects.toThrow('Proxy Backend Failed');
    });
});
