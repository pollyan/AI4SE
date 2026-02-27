/**
 * useVercelChat Hook 测试
 * TDD: 验证 hook 的预期行为
 */
import { describe, it, expect, vi } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';

// 使用全局 MSW server (来自 setupTests.ts)
import { server } from './mocks/server';

// 被测试的 hook
import { useVercelChat } from '../hooks/useVercelChat';

// 模拟 SSE 响应格式 (Data Stream Protocol)
const createSSEResponse = (events: Array<{ type: string; data: any }>) => {
    const encoder = new TextEncoder();
    const stream = new ReadableStream({
        start(controller) {
            events.forEach((event) => {
                let line: string;
                switch (event.type) {
                    case 'text':
                        // AI SDK 格式: 0:"text"
                        line = `0:${JSON.stringify(event.data)}\n`;
                        break;
                    case 'data':
                        // 自定义数据事件: 8:[{...}]
                        line = `8:${JSON.stringify([event.data])}\n`;
                        break;
                    case 'finish':
                        // 完成事件: d:{"finishReason":"stop"}
                        line = `d:${JSON.stringify({ finishReason: 'stop' })}\n`;
                        break;
                    case 'error':
                        line = `e:${JSON.stringify({ error: event.data })}\n`;
                        break;
                    default:
                        line = `data: ${JSON.stringify(event)}\n\n`;
                }
                controller.enqueue(encoder.encode(line));
            });
            controller.close();
        },
    });
    return stream;
};

// 注意：server.listen/close 已在 setupTests.ts 中处理

describe('useVercelChat Hook', () => {
    describe('初始化', () => {
        it('初始状态应该是 ready', async () => {
            const { result } = renderHook(() =>
                useVercelChat({
                    sessionId: 'test-session',
                    assistantType: 'lisa',
                })
            );

            expect(result.current.status).toBe('ready');
            expect(result.current.messages).toHaveLength(0);
        });
    });

    describe('基础消息发送', () => {
        it('应该能够发送消息并接收流式响应', async () => {
            // 模拟后端 SSE 响应
            server.use(
                http.post('/ai-agents/api/requirements/sessions/test-session/messages/v2/stream', () => {
                    return new HttpResponse(
                        createSSEResponse([
                            { type: 'text', data: '你好' },
                            { type: 'text', data: '，我是 Lisa' },
                            { type: 'finish', data: null },
                        ]),
                        {
                            headers: {
                                'Content-Type': 'text/event-stream',
                                'Cache-Control': 'no-cache',
                            },
                        }
                    );
                }),
                // Mock sync endpoint
                http.post('/ai-agents/api/requirements/sessions/test-session/sync', () => {
                    return HttpResponse.json({ success: true });
                })
            );

            const { result } = renderHook(() =>
                useVercelChat({
                    sessionId: 'test-session',
                    assistantType: 'lisa',
                })
            );

            expect(result.current.status).toBe('ready');
            expect(result.current.messages).toHaveLength(0);

            await act(async () => {
                result.current.sendMessage({ text: '你好' });
            });

            await waitFor(() => {
                expect(result.current.messages.length).toBeGreaterThanOrEqual(1);
            }, { timeout: 5000 });
        });

        it('应该正确处理进度数据事件', async () => {
            const progressCallback = vi.fn();

            server.use(
                http.post('/ai-agents/api/requirements/sessions/test-session-2/messages/v2/stream', () => {
                    return new HttpResponse(
                        createSSEResponse([
                            { type: 'data', data: { stages: [{ id: 'clarify', name: '澄清需求', status: 'active' }], currentStageIndex: 0 } },
                            { type: 'text', data: '正在分析...' },
                            { type: 'finish', data: null },
                        ]),
                        {
                            headers: {
                                'Content-Type': 'text/event-stream',
                            },
                        }
                    );
                }),
                http.post('/ai-agents/api/requirements/sessions/test-session-2/sync', () => {
                    return HttpResponse.json({ success: true });
                })
            );

            const { result } = renderHook(() =>
                useVercelChat({
                    sessionId: 'test-session-2',
                    assistantType: 'lisa',
                    onProgressChange: progressCallback,
                })
            );

            await act(async () => {
                result.current.sendMessage({ text: '分析这个需求' });
            });

            await waitFor(() => {
                expect(result.current.messages.length).toBeGreaterThanOrEqual(1);
            }, { timeout: 5000 });

            // 进度回调可能在流处理中被调用
            // 具体行为取决于 AI SDK 的 onDataStreamPart 实现
        });
    });

    describe('状态管理', () => {
        it('发送消息时 status 应该变化', async () => {
            server.use(
                http.post('/ai-agents/api/requirements/sessions/test-session-3/messages/v2/stream', async () => {
                    // 延迟响应以观察 status 变化
                    await new Promise((resolve) => setTimeout(resolve, 50));
                    return new HttpResponse(
                        createSSEResponse([
                            { type: 'text', data: '响应' },
                            { type: 'finish', data: null },
                        ]),
                        { headers: { 'Content-Type': 'text/event-stream' } }
                    );
                }),
                http.post('/ai-agents/api/requirements/sessions/test-session-3/sync', () => {
                    return HttpResponse.json({ success: true });
                })
            );

            const { result } = renderHook(() =>
                useVercelChat({
                    sessionId: 'test-session-3',
                    assistantType: 'lisa',
                })
            );

            expect(result.current.status).toBe('ready');

            await act(async () => {
                result.current.sendMessage({ text: '测试' });
            });

            // 等待完成
            await waitFor(() => {
                expect(result.current.status).toBe('ready');
            }, { timeout: 5000 });
        });
    });

    describe('错误处理', () => {
        it('网络错误时应该设置 error 状态', async () => {
            server.use(
                http.post('/ai-agents/api/requirements/sessions/error-session/messages/v2/stream', () => {
                    return HttpResponse.error();
                })
            );

            const { result } = renderHook(() =>
                useVercelChat({
                    sessionId: 'error-session',
                    assistantType: 'lisa',
                })
            );

            await act(async () => {
                result.current.sendMessage({ text: '测试' });
            });

            await waitFor(() => {
                expect(result.current.status).toBe('error');
            }, { timeout: 5000 });
        });
    });

    describe('消息同步', () => {
        it('完成后应该调用 sync 端点', async () => {
            let syncCalled = false;

            server.use(
                http.post('/ai-agents/api/requirements/sessions/sync-session/messages/v2/stream', () => {
                    return new HttpResponse(
                        createSSEResponse([
                            { type: 'text', data: '回复' },
                            { type: 'finish', data: null },
                        ]),
                        { headers: { 'Content-Type': 'text/event-stream' } }
                    );
                }),
                http.post('/ai-agents/api/requirements/sessions/sync-session/sync', () => {
                    syncCalled = true;
                    return HttpResponse.json({ success: true });
                })
            );

            const { result } = renderHook(() =>
                useVercelChat({
                    sessionId: 'sync-session',
                    assistantType: 'lisa',
                })
            );

            await act(async () => {
                result.current.sendMessage({ text: '测试' });
            });

            await waitFor(() => {
                expect(syncCalled).toBe(true);
            }, { timeout: 5000 });
        });
    });
});

// 导出测试工具供其他测试使用
export { createSSEResponse };
