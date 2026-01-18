import { vi } from 'vitest';

/**
 * Creates a mock ReadableStream that emits Vercel AI SDK Data Stream Protocol parts.
 * 
 * Protocol Reference:
 * 0: Text
 * 8: Data
 * 9: Tool Call
 * a: Tool Result
 * d: Finish
 * e: Error
 */
export function createMockStream(parts: string[], delay = 10): ReadableStream {
    const encoder = new TextEncoder();
    
    return new ReadableStream({
        async start(controller) {
            for (const part of parts) {
                // Simulate network delay
                if (delay > 0) {
                    await new Promise(resolve => setTimeout(resolve, delay));
                }
                controller.enqueue(encoder.encode(part + '\n'));
            }
            controller.close();
        }
    });
}

/**
 * Helper to mock global fetch for a specific stream scenario
 */
export function mockFetchStream(parts: string[]) {
    const stream = createMockStream(parts);
    const mockResponse = new Response(stream, {
        headers: { 'Content-Type': 'text/event-stream' }
    });
    
    global.fetch = vi.fn().mockResolvedValue(mockResponse);
}

/**
 * Helper to mock fetch error
 */
export function mockFetchError(message: string) {
    global.fetch = vi.fn().mockRejectedValue(new Error(message));
}

/**
 * Protocol Builders
 */
export const Protocol = {
    text: (t: string) => `0:${JSON.stringify(t)}`,
    data: (d: any[]) => `8:${JSON.stringify(d)}`,
    toolCall: (id: string, name: string, args: any) => `9:${JSON.stringify({toolCallId: id, toolName: name, args})}`,
    toolResult: (id: string, name: string, result: any) => `a:${JSON.stringify({toolCallId: id, toolName: name, result})}`,
    finish: (reason = "stop", usage = {promptTokens: 10, completionTokens: 10}) => `d:${JSON.stringify({finishReason: reason, usage})}`,
    error: (msg: string) => `e:${JSON.stringify({error: msg})}`
};
