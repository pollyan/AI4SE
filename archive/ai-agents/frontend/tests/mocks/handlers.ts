import { http, HttpResponse } from 'msw';

const API_BASE = '/ai-agents/api/requirements';

export const handlers = [
    // Create Session
    http.post(`${API_BASE}/sessions`, () => {
        return HttpResponse.json({
            data: {
                id: 'mock-session-id',
                project_name: 'AI4SE Project',
                session_status: 'created',
                current_stage: 'initial'
            }
        });
    }),

    // Stream Messages
    http.post(`${API_BASE}/sessions/:sessionId/messages/stream`, async () => {
        const encoder = new TextEncoder();
        const stream = new ReadableStream({
            start(controller) {
                // Simulate a delay and stream chunks
                const chunks = [
                    'data: {"type": "content", "chunk": "Hello"}\n\n',
                    'data: {"type": "content", "chunk": ", I am"}\n\n',
                    'data: {"type": "content", "chunk": " ready."}\n\n',
                    'data: {"type": "done"}\n\n'
                ];

                chunks.forEach(chunk => {
                    controller.enqueue(encoder.encode(chunk));
                });

                controller.close();
            }
        });

        return new HttpResponse(stream, {
            headers: {
                'Content-Type': 'text/event-stream',
            },
        });
    }),
];
