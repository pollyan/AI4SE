import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { server } from './mocks/server';
import { AssistantChat } from '../components/chat/AssistantChat';
import * as React from 'react';
import { describe, it, expect, vi, afterEach } from 'vitest';
import { Assistant, AssistantId } from '../types';

// Mock scrollIntoView
Element.prototype.scrollIntoView = vi.fn();

const API_BASE = '/ai-agents/api/requirements';

const assistant: Assistant = {
    id: AssistantId.Alex,
    name: 'Alex',
    role: '需求分析专家',
    initial: 'A',
    description: '测试助手',
    colorClass: 'text-blue-600',
    bgColorClass: 'bg-blue-100',
    borderColorClass: 'border-blue-200',
    textColorClass: 'text-blue-800',
    systemInstruction: 'You are a helpful assistant.',
    welcomeMessage: 'Hello!'
};

const createStreamResolver = (content: string, toolCall?: { id: string, args: string }) => {
    return () => {
        const encoder = new TextEncoder();
        const messageId = `msg_${Date.now()}_${Math.random()}`;
        const stream = new ReadableStream({
            start(controller) {
                // 1. Start
                controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: "text-start", id: messageId })}\n\n`));

                // 2. Text (Use 'delta' instead of 'text')
                if (content) {
                    controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: "text-delta", delta: content, id: messageId })}\n\n`));
                }

                // 3. Tool Call (Use 'tool-input-available')
                if (toolCall) {
                    controller.enqueue(encoder.encode(`data: ${JSON.stringify({
                        type: "tool-input-available",
                        toolCallId: toolCall.id,
                        toolName: "UpdateArtifact",
                        input: JSON.parse(toolCall.args)
                    })}\n\n`));
                }

                // 4. Finish
                controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: "finish", finishReason: "stop" })}\n\n`));
                controller.close();
            }
        });

        return new HttpResponse(stream, {
            headers: { 'Content-Type': 'text/event-stream' }
        });
    };
};

describe('AssistantChat Artifact Handling', () => {
    afterEach(() => {
        server.resetHandlers();
    });

    it('should handle UpdateArtifact tool call', async () => {
        const user = userEvent.setup();
        const onBack = vi.fn();

        // Specific handlers for this test
        server.use(
            http.post(`${API_BASE}/sessions`, () => {
                return HttpResponse.json({
                    data: { id: 'test-session', project_name: 'test', session_status: 'created', current_stage: 'initial' }
                });
            }),
            http.post(`${API_BASE}/sessions/:sessionId/sync`, () => {
                return HttpResponse.json({ success: true });
            }),
            http.post(`${API_BASE}/sessions/:sessionId/messages/v2/stream`, createStreamResolver('Ready')),
            // Fallback for default API path if configuration fails
            http.post('/api/chat', createStreamResolver('Ready'))
        );

        render(<AssistantChat assistant={assistant} onBack={onBack} />);

        // Wait for welcome message
        await waitFor(() => {
            expect(screen.queryByPlaceholderText('输入消息...')).toBeInTheDocument();
        }, { timeout: 8000 });

        // Change response for the next message
        const toolArgs = JSON.stringify({ key: 'test', markdown_body: 'SECRET_DATA' });
        const nextResolver = createStreamResolver('Analysis result:', { id: 'call_1', args: toolArgs });
        server.use(
            http.post(`${API_BASE}/sessions/:sessionId/messages/v2/stream`, nextResolver),
            http.post('/api/chat', nextResolver)
        );

        const input = screen.getByPlaceholderText('输入消息...');
        await user.type(input, 'test');
        await user.keyboard('{Enter}');

        // Check for UI feedback
        await waitFor(() => {
            const fullContent = document.body.textContent || '';
            expect(fullContent).toContain('Analysis result:');
            // Check for Tool UI
            // Check for Tool UI (Loading State)
            expect(fullContent).toContain('↻ 正在更新产出物...');

            // Ensure SECRET_DATA is NOT leaked in main chat
            // (It's in args, but UpdateArtifactView doesn't render it)
            expect(fullContent).not.toContain('SECRET_DATA');
        }, { timeout: 10000 });
    }, 20000);
});
