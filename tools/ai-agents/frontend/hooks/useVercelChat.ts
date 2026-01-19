/**
 * useVercelChat - 原生 Vercel AI SDK useChat 封装
 * 
 * 替代 @assistant-ui/react-ai-sdk 的 useChatRuntime
 * 使用 AI SDK 5.0 的 transport-based 架构
 */
import { useChat } from '@ai-sdk/react';
import { DefaultChatTransport } from 'ai';
import { useMemo, useCallback } from 'react';
import type { ProgressInfo } from '../services/backendService';

const API_BASE = '/ai-agents/api/requirements';

export interface UseVercelChatOptions {
    /** 会话 ID */
    sessionId: string;
    /** 智能体类型 */
    assistantType: string;
    /** 进度变化回调 */
    onProgressChange?: (progress: ProgressInfo) => void;
}

export interface UseVercelChatReturn {
    /** 消息列表 */
    messages: Array<{
        id: string;
        role: 'user' | 'assistant';
        parts: Array<{ type: string; text?: string;[key: string]: any }>;
    }>;
    /** 当前状态 */
    status: 'ready' | 'streaming' | 'error';
    /** 发送消息 */
    sendMessage: (options: { text: string }) => void;
    /** 停止生成 */
    stop: () => void;
    /** 错误信息 */
    error?: Error;
}

/**
 * Vercel AI SDK Chat Hook
 * 
 * 使用 AI SDK 5.0 的 useChat hook 与后端通信
 */
export function useVercelChat({
    sessionId,
    assistantType,
    onProgressChange,
}: UseVercelChatOptions): UseVercelChatReturn {

    const api = `${API_BASE}/sessions/${sessionId}/messages/v2/stream`;

    // 创建 transport 实例
    const transport = useMemo(
        () =>
            new DefaultChatTransport({
                api,
                headers: { 'X-Assistant-Type': assistantType },
            }),
        [api, assistantType]
    );

    // useChat hook 配置
    const {
        messages: rawMessages,
        status: rawStatus,
        error,
        sendMessage: sdkSendMessage,
        stop,
    } = useChat({
        transport,
        // 处理自定义数据事件（进度更新）
        onData: (dataPart) => {
            if (onProgressChange && dataPart) {
                // Data Stream Protocol: data events might be array or object
                const dataValue = Array.isArray(dataPart) ? dataPart[0] : dataPart;

                if (dataValue && typeof dataValue === 'object') {
                    // Fix: Extract inner data from data-progress event
                    // Event format: { type: "data-progress", data: { stages: [...] } }
                    if ('data' in dataValue && (dataValue as any).type === 'data-progress') {
                        onProgressChange((dataValue as any).data as ProgressInfo);
                    } else {
                        // Fallback for direct objects
                        onProgressChange(dataValue as ProgressInfo);
                    }
                }
            }
        },
        // 完成后同步消息到后端
        onFinish: async (message) => {
            try {
                await fetch(`${API_BASE}/sessions/${sessionId}/sync`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ messages: [message] }),
                });
            } catch (err) {
                console.error('Failed to sync message:', err);
            }
        },
    });

    // 转换消息格式（确保 parts 存在）
    const messages = useMemo(() => {
        return rawMessages.map((msg) => ({
            id: msg.id,
            role: msg.role as 'user' | 'assistant',
            parts: msg.parts || [{ type: 'text', text: typeof (msg as any).content === 'string' ? (msg as any).content : '' }],
        }));
    }, [rawMessages]);

    // 转换状态
    const status = useMemo((): 'ready' | 'streaming' | 'error' => {
        if (rawStatus === 'streaming' || rawStatus === 'submitted') return 'streaming';
        if (error) return 'error';
        return 'ready';
    }, [rawStatus, error]);

    // 封装发送消息方法
    const sendMessage = useCallback(
        ({ text }: { text: string }) => {
            sdkSendMessage({ text });
        },
        [sdkSendMessage]
    );

    return {
        messages,
        status,
        sendMessage,
        stop,
        error: error || undefined,
    };
}
