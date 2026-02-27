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
                controller.enqueue(encoder.encode(part));
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
    // V2: data: {"type": "text-start", ...}
    start: (id = "msg_" + Math.random()) => `data: ${JSON.stringify({ type: "text-start", id: id })}\n\n`,

    // V2: data: {"type": "text-delta", "delta": "t", "id": "..."}
    text: (t: string, id: string = "msg_default") => `data: ${JSON.stringify({ type: "text-delta", delta: t, id: id })}\n\n`,

    // V2: data: {"type": "data", "data": [...]}
    data: (d: any[]) => `data: ${JSON.stringify({ type: "data", data: d })}\n\n`,

    // V2: data: {"type": "tool-input-available", ...}
    toolCall: (id: string, name: string, args: any) => `data: ${JSON.stringify({
        type: "tool-input-available",
        toolCallId: id,
        toolName: name,
        input: args
    })}\n\n`,

    // V2: data: {"type": "tool-output-available", ...}
    toolResult: (id: string, name: string, result: any) => `data: ${JSON.stringify({
        type: "tool-output-available",
        toolCallId: id,
        toolName: name,
        output: result
    })}\n\n`,

    // V2: data: {"type": "finish", ...}
    finish: (reason = "stop", usage = { promptTokens: 10, completionTokens: 10 }) => `data: ${JSON.stringify({
        type: "finish",
        finishReason: reason,
        usage
    })}\n\n`,

    // V2: data: {"type": "error", ...}
    error: (msg: string) => `data: ${JSON.stringify({ type: "error", error: msg })}\n\n`
};
