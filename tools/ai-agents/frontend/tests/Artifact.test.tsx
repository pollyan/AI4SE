import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { server } from './mocks/server';
import { AssistantChat } from '../components/chat/AssistantChat';
import * as React from 'react';
import { describe, it, expect, vi, afterEach } from 'vitest';
import { Assistant } from '../types';

// Mock scrollIntoView
Element.prototype.scrollIntoView = vi.fn();

const API_BASE = '/ai-agents/api/requirements';

const assistant: Assistant = {
    id: 'alex',
    name: 'Alex',
    role: '需求分析专家',
    initial: 'A',
    description: '测试助手'
};

const mockStreamResponse = (content: string) => {
    return http.post(`${API_BASE}/sessions/:sessionId/messages/stream`, async () => {
        const encoder = new TextEncoder();
        const stream = new ReadableStream({
            start(controller) {
                const data = JSON.stringify({ type: "content", chunk: content });
                controller.enqueue(encoder.encode(`data: ${data}\n\n`));
                controller.enqueue(encoder.encode('data: {"type": "done"}\n\n'));
                controller.close();
            }
        });
        return new HttpResponse(stream, { headers: { 'Content-Type': 'text/event-stream' } });
    });
};

describe('AssistantChat Artifact Handling', () => {
    afterEach(() => {
        server.resetHandlers();
    });

    it('should mask artifact content in assistant messages', async () => {
        const user = userEvent.setup();
        const onBack = vi.fn();

        // Specific handlers for this test
        server.use(
            http.post(`${API_BASE}/sessions`, () => {
                return HttpResponse.json({
                    data: { id: 'test-session', project_name: 'test', session_status: 'created', current_stage: 'initial' }
                });
            }),
            mockStreamResponse('Ready')
        );

        render(<AssistantChat assistant={assistant} onBack={onBack} />);

        // Wait for welcome message
        await waitFor(() => {
            expect(screen.queryByPlaceholderText('请输入...')).toBeInTheDocument();
        }, { timeout: 8000 });

        // Change response for the next message
        const artifactMsg = 'Analysis result:\n:::artifact\nSECRET_DATA\n:::\nDone.';
        server.use(mockStreamResponse(artifactMsg));

        const input = screen.getByPlaceholderText('请输入...');
        await user.type(input, 'test');
        await user.keyboard('{Enter}');

        // Use a more robust way to check for content that might be split across elements
        await waitFor(() => {
            const fullContent = document.body.textContent || '';
            expect(fullContent).toContain('Analysis result:');
            expect(fullContent).toContain('(已更新右侧分析成果)');
            expect(fullContent).toContain('Done.');

            // Ensure SECRET_DATA is NOT leaked
            expect(fullContent).not.toContain('SECRET_DATA');
        }, { timeout: 10000 });
    }, 20000);
});
