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

const mockStreamResponseV2 = (content: string, toolCall?: { id: string, args: string }) => {
    return http.post(`${API_BASE}/sessions/:sessionId/messages/v2/stream`, async () => {
        const encoder = new TextEncoder();
        const messageId = `msg_${Date.now()}_${Math.random()}`;
        const stream = new ReadableStream({
            start(controller) {
                // 1. Start
                controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: "start", messageId })}\n\n`));
                
                // 2. Text
                if (content) {
                    controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: "text-delta", text: content })}\n\n`));
                }
                
                // 3. Tool Call
                if (toolCall) {
                    controller.enqueue(encoder.encode(`data: ${JSON.stringify({ 
                        type: "tool-call", 
                        toolCallId: toolCall.id, 
                        toolName: "UpdateArtifact", 
                        input: JSON.parse(toolCall.args) 
                    })}\n\n`));
                    // Tool Result (simulated immediate success)
                    controller.enqueue(encoder.encode(`data: ${JSON.stringify({ 
                        type: "tool-result", 
                        toolCallId: toolCall.id, 
                        toolName: "UpdateArtifact", 
                        result: { status: "success" } 
                    })}\n\n`));
                }
                
                // 4. Finish
                controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: "finish", finishReason: "stop" })}\n\n`));
                controller.enqueue(encoder.encode('data: [DONE]\n\n'));
                controller.close();
            }
        });
        return new HttpResponse(stream, { headers: { 'Content-Type': 'text/event-stream' } });
    });
};

describe.skip('AssistantChat Artifact Handling', () => {
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
            mockStreamResponseV2('Ready'),
            // Fallback for default API path if configuration fails
            http.post('/api/chat', async () => {
                 return mockStreamResponseV2('Ready')();
            })
        );

        render(<AssistantChat assistant={assistant} onBack={onBack} />);

        // Wait for welcome message
        await waitFor(() => {
            expect(screen.queryByPlaceholderText('请输入...')).toBeInTheDocument();
        }, { timeout: 8000 });

        // Change response for the next message
        const toolArgs = JSON.stringify({ key: 'test', markdown_body: 'SECRET_DATA' });
        const nextResponse = mockStreamResponseV2('Analysis result:', { id: 'call_1', args: toolArgs });
        server.use(
            nextResponse,
            http.post('/api/chat', async () => nextResponse())
        );

        const input = screen.getByPlaceholderText('请输入...');
        await user.type(input, 'test');
        await user.keyboard('{Enter}');

        // Check for UI feedback
        await waitFor(() => {
            const fullContent = document.body.textContent || '';
            expect(fullContent).toContain('Analysis result:');
            // Check for Tool UI
            expect(fullContent).toContain('✅ 已更新右侧产出物面板');

            // Ensure SECRET_DATA is NOT leaked in main chat
            // (It's in args, but UpdateArtifactView doesn't render it)
            expect(fullContent).not.toContain('SECRET_DATA');
        }, { timeout: 10000 });
    }, 20000);
});
