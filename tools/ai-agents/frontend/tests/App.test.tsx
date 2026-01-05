import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { server } from './mocks/server';
import App from '../App';
import * as React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock scrollIntoView since JSDOM doesn't support it
Element.prototype.scrollIntoView = vi.fn();

const API_BASE = '/ai-agents/api/requirements';

const mockStreamResponse = (content: string) => {
    return http.post(`${API_BASE}/sessions/:sessionId/messages/stream`, async () => {
        const encoder = new TextEncoder();
        const stream = new ReadableStream({
            start(controller) {
                controller.enqueue(encoder.encode(`data: {"type": "content", "chunk": "${content}"}\n\n`));
                controller.enqueue(encoder.encode('data: {"type": "done"}\n\n'));
                controller.close();
            }
        });
        return new HttpResponse(stream, { headers: { 'Content-Type': 'text/event-stream' } });
    });
};

describe('AI Agents App', () => {

    beforeEach(() => {
        // Default mock for session creation and welcome message
        server.use(mockStreamResponse('你好，我是Alex，需求分析专家。'));
    });

    it('P0: Renders assistant selection screen', async () => {
        render(<App />);

        // Should show assistant selection interface
        expect(screen.getByText('选择智能助手')).toBeInTheDocument();
        expect(screen.getByText('Alex')).toBeInTheDocument();
        expect(screen.getByText('Lisa')).toBeInTheDocument();

        // Should show assistant cards with descriptions
        expect(screen.getByText('需求分析专家')).toBeInTheDocument();
        expect(screen.getByText('测试专家 (v5.0)')).toBeInTheDocument();
    });

    it('P0: Selects Assistant (Alex) and shows chat interface', async () => {
        server.use(mockStreamResponse('你好，我是Alex'));

        render(<App />);

        // Click Alex
        fireEvent.click(screen.getByText('Alex'));

        // Should show chat interface with Alex header
        await waitFor(() => {
            // Check for main heading
            expect(screen.getByRole('heading', { name: '智能助手', level: 1 })).toBeInTheDocument();
        });

        // Wait for welcome message to appear
        await waitFor(() => {
            expect(screen.getByText(/你好，我是Alex/)).toBeInTheDocument();
        }, { timeout: 5000 });

        // Should see the input field
        expect(screen.getByPlaceholderText('请输入...')).toBeInTheDocument();
    });

    it('P0: Shows back button and can switch assistant', async () => {
        server.use(mockStreamResponse('Welcome'));

        render(<App />);

        // Select Alex
        fireEvent.click(screen.getByText('Alex'));

        // Wait for chat interface
        await waitFor(() => {
            expect(screen.getByText(/Welcome/)).toBeInTheDocument();
        }, { timeout: 5000 });

        // Find and click switch assistant button
        const switchButton = screen.getByText('切换助手');
        expect(switchButton).toBeInTheDocument();
        fireEvent.click(switchButton);

        // Should go back to assistant selection
        await waitFor(() => {
            expect(screen.getByText('选择智能助手')).toBeInTheDocument();
        });
    });

    it('P0: Sends message using input field', async () => {
        const user = userEvent.setup();

        // Welcome message
        server.use(mockStreamResponse('Ready'));

        render(<App />);

        // Select Alex
        fireEvent.click(screen.getByText('Alex'));

        // Wait for welcome and input to be ready
        await waitFor(() => {
            expect(screen.getByText(/Ready/)).toBeInTheDocument();
        }, { timeout: 5000 });

        // Mock response for user message
        server.use(
            http.post(`${API_BASE}/sessions/:sessionId/messages/stream`, async ({ request }) => {
                const body = await request.json() as any;
                if (body?.content === '测试消息') {
                    const encoder = new TextEncoder();
                    const stream = new ReadableStream({
                        start(controller) {
                            controller.enqueue(encoder.encode('data: {"type": "content", "chunk": "收到您的测试消息"}\n\n'));
                            controller.enqueue(encoder.encode('data: {"type": "done"}\n\n'));
                            controller.close();
                        }
                    });
                    return new HttpResponse(stream, { headers: { 'Content-Type': 'text/event-stream' } });
                }
                return new HttpResponse(null, { status: 200 });
            })
        );

        // Type in input using userEvent for better React compatibility
        const input = screen.getByPlaceholderText('请输入...');
        await user.type(input, '测试消息');
        await user.keyboard('{Enter}');

        // Wait for response
        await waitFor(() => {
            expect(screen.getByText(/收到您的测试消息/)).toBeInTheDocument();
        }, { timeout: 5000 });
    });

    it('P1: Handles connection error gracefully', async () => {
        // First welcome works
        server.use(mockStreamResponse('Ready'));

        render(<App />);
        fireEvent.click(screen.getByText('Alex'));

        await waitFor(() => {
            expect(screen.getByText(/Ready/)).toBeInTheDocument();
        }, { timeout: 5000 });

        // Now force error for next request
        server.use(
            http.post(`${API_BASE}/sessions/:sessionId/messages/stream`, () => {
                return new HttpResponse(null, { status: 500 });
            })
        );

        const user = userEvent.setup();
        const input = screen.getByPlaceholderText('请输入...');
        await user.type(input, '这会报错');
        await user.keyboard('{Enter}');

        // Should show error message
        await waitFor(() => {
            expect(screen.getByText(/无法完成回复/)).toBeInTheDocument();
        }, { timeout: 5000 });
    });

    it('P0: Analysis panel shows placeholder when no result', async () => {
        render(<App />);

        // Analysis panel should show waiting state
        expect(screen.getByText('分析成果')).toBeInTheDocument();
        expect(screen.getByText(/开始与AI助手对话后，这里将实时显示结构化的分析成果/)).toBeInTheDocument();
    });
});
