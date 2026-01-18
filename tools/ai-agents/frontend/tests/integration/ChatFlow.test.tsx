import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { AssistantChat } from '../../components/chat/AssistantChat';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { Assistant } from '../../types';
import { createMockStream, Protocol } from '../utils/stream-mock';
import { server } from '../mocks/server';
import { http, HttpResponse } from 'msw';

// Mock dependencies
vi.mock('../../services/backendService', () => ({
    createSession: vi.fn().mockResolvedValue({ sessionId: 'test-session-id' })
}));

const mockAssistant: Assistant = {
    id: 'alex',
    name: 'Alex',
    role: 'Analyst',
    initial: 'A',
    description: 'Test',
    bundle: 'bundle'
};

describe.skip('ChatFlow Integration Tests', () => {
    // 1. Basic Messaging
    it('T1.1: Renders text stream correctly', async () => {
        // Setup MSW handler
        server.use(
            http.post('*/messages/v2/stream', () => {
                const stream = createMockStream([
                    Protocol.data([{messageId: "msg_1"}]),
                    Protocol.text("Hello"),
                    Protocol.text(" World"),
                    Protocol.finish()
                ]);
                return new HttpResponse(stream, {
                    headers: { 'Content-Type': 'text/event-stream' }
                });
            })
        );

        render(<AssistantChat assistant={mockAssistant} onBack={vi.fn()} />);

        // Wait for session init
        await waitFor(() => expect(screen.queryByText('正在创建会话...')).not.toBeInTheDocument());
        
        // Find input
        const input = await screen.findByPlaceholderText(/请输入/i);
        const sendBtn = screen.getByRole('button', { name: /发送消息/i });

        // Type and send
        fireEvent.change(input, { target: { value: 'Hi' } });
        fireEvent.click(sendBtn);

        // Expect Hello World to appear
        await waitFor(() => {
            expect(screen.getByText(/Hello World/i)).toBeInTheDocument();
        });
    });

    // 2. Tool Interaction
    it('T2.3: Renders confirmation tool and handles interaction', async () => {
        // Setup handlers for sequence
        let callCount = 0;
        server.use(
            http.post('*/messages/v2/stream', async ({ request }) => {
                callCount++;
                const body = await request.json() as any;
                
                if (callCount === 1) {
                    // First call: Return confirmation tool
                    const stream = createMockStream([
                        Protocol.data([{messageId: "msg_2"}]),
                        Protocol.text("I need confirmation."),
                        Protocol.toolCall("call_1", "ask_confirmation", { message: "Proceed?" }),
                    ]);
                    return new HttpResponse(stream, {
                        headers: { 'Content-Type': 'text/event-stream' }
                    });
                } else {
                    // Second call: Return result response
                    const stream = createMockStream([
                        Protocol.text("Action confirmed."),
                        Protocol.finish()
                    ]);
                    return new HttpResponse(stream, {
                        headers: { 'Content-Type': 'text/event-stream' }
                    });
                }
            })
        );

        render(<AssistantChat assistant={mockAssistant} onBack={vi.fn()} />);
        await waitFor(() => expect(screen.queryByText('正在创建会话...')).not.toBeInTheDocument());

        // Send message
        const input = await screen.findByPlaceholderText(/请输入/i);
        fireEvent.change(input, { target: { value: 'Do it' } });
        fireEvent.click(screen.getByRole('button', { name: /发送消息/i }));

        // Wait for Tool UI
        await waitFor(() => {
            expect(screen.getByText("Proceed?")).toBeInTheDocument();
            expect(screen.getByRole('button', { name: /Confirm/i })).toBeInTheDocument();
        });

        // Click Confirm
        fireEvent.click(screen.getByRole('button', { name: /Confirm/i }));

        // Verify final text
        await waitFor(() => {
            expect(screen.getByText("Action confirmed.")).toBeInTheDocument();
        });
    });

    // 3. Sync on Finish
    it('T3.1: Triggers Sync on Finish', async () => {
        const syncListener = vi.fn();
        server.use(
            http.post('*/messages/v2/stream', () => {
                const stream = createMockStream([
                    Protocol.data([{messageId: "msg_3"}]),
                    Protocol.text("Done."),
                    Protocol.finish()
                ]);
                return new HttpResponse(stream, {
                    headers: { 'Content-Type': 'text/event-stream' }
                });
            }),
            http.post('*/sessions/:id/sync', async ({ request }) => {
                syncListener(await request.json());
                return HttpResponse.json({ success: true });
            })
        );

        render(<AssistantChat assistant={mockAssistant} onBack={vi.fn()} />);
        await waitFor(() => expect(screen.queryByText('正在创建会话...')).not.toBeInTheDocument());

        // Send
        fireEvent.change(await screen.findByPlaceholderText(/请输入/i), { target: { value: 'Hi' } });
        fireEvent.click(screen.getByRole('button', { name: /发送消息/i }));

        // Wait for finish
        await waitFor(() => {
            expect(screen.getByText("Done.")).toBeInTheDocument();
        });

        // Verify Sync Call
        await waitFor(() => {
            expect(syncListener).toHaveBeenCalled();
            const body = syncListener.mock.calls[0][0];
            expect(body.messages).toBeDefined();
        });
    });

    // 4. Error Handling
    it('T4.2: Handles network error', async () => {
        server.use(
            http.post('*/messages/v2/stream', () => {
                return HttpResponse.error();
            })
        );

        render(<AssistantChat assistant={mockAssistant} onBack={vi.fn()} />);
        await waitFor(() => expect(screen.queryByText('正在创建会话...')).not.toBeInTheDocument());

        // Send
        fireEvent.change(await screen.findByPlaceholderText(/请输入/i), { target: { value: 'Hi' } });
        fireEvent.click(screen.getByRole('button', { name: /发送消息/i }));

        // Expect Error UI
        // Note: MSW HttpResponse.error() simulates network error
        await waitFor(() => {
            // Text might vary depending on what Vercel SDK maps Network Error to
            // Usually "Failed to fetch" or similar.
            // Our Display shows error.message.
            // We search for "出错了" which is in our component.
            expect(screen.getByText(/出错了/i)).toBeInTheDocument();
            expect(screen.getByRole('button', { name: /重试/i })).toBeInTheDocument();
        });
    });
});
