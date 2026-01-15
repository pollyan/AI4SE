/**
 * MockAssistantChat - AssistantChat 的 Mock 版本
 * 用于在无后端环境下演示高级 UI 功能
 */
import React, { useEffect, useRef, useState } from 'react';
import {
    AssistantRuntimeProvider,
    useExternalStoreRuntime,
    ThreadPrimitive,
    ComposerPrimitive,
    MessagePrimitive,
    useMessage,
    ActionBarPrimitive,
} from '@assistant-ui/react';
import type {
    ExternalStoreAdapter,
    ThreadMessage,
    AppendMessage,
} from '@assistant-ui/react';
import { Bot, Send, User, ChevronLeft, Copy, Check, RefreshCw } from 'lucide-react';
import { MarkdownText } from './MarkdownText';
import { AttachmentList } from './AttachmentList';
import { AttachmentButton } from './AttachmentButton';
import { MessageAttachments } from './MessageAttachments';
import { Assistant, AssistantId, PendingAttachment, MessageAttachment } from '../../types';
import { processFile } from '../../utils/attachmentUtils';

interface AssistantChatProps {
    assistant: Assistant;
    onBack: () => void;
    // 模拟回调
    onMockResponse?: (userText: string) => void;
}

// 模拟后端消息
interface BackendMessage {
    id: string;
    role: 'user' | 'model';
    text: string;
    timestamp: number;
    isThinking?: boolean;
    attachments?: MessageAttachment[];
}

function convertToThreadMessage(msg: BackendMessage) {
    const baseMessage = {
        id: msg.id,
        createdAt: new Date(msg.timestamp),
        metadata: { custom: {} },
    };

    if (msg.role === 'user') {
        return {
            ...baseMessage,
            role: 'user' as const,
            content: [{ type: 'text' as const, text: msg.text }],
            attachments: [],
            metadata: {
                custom: {
                    attachments: msg.attachments,
                },
            },
        };
    } else {
        return {
            ...baseMessage,
            role: 'assistant' as const,
            content: [{ type: 'text' as const, text: msg.text }],
            status: msg.isThinking
                ? { type: 'running' as const }
                : { type: 'complete' as const, reason: 'stop' as const },
        };
    }
}

function useMockChatState(assistantId: AssistantId, onMockResponse?: (text: string) => void) {
    const [messages, setMessages] = useState<BackendMessage[]>([{
        id: 'msg-welcome',
        role: 'model',
        text: '你好！我是需求分析专家 Alex。我可以帮你分析业务需求，生成用户画像和需求文档。\n\n请尝试上传需求文档，或者直接告诉我你的想法。',
        timestamp: Date.now(),
        isThinking: false
    }]);
    const [isRunning, setIsRunning] = useState(false);
    const [pendingAttachments, setPendingAttachments] = useState<PendingAttachment[]>([]);

    const handleFilesSelected = async (files: File[]) => {
        const processedFiles = await Promise.all(
            files.map(file => processFile(file))
        );
        setPendingAttachments(prev => [...prev, ...processedFiles]);
    };

    const removeAttachment = (id: string) => {
        setPendingAttachments(prev => prev.filter(a => a.id !== id));
    };

    const onNew = async (message: AppendMessage) => {
        const userText = typeof message.content === 'string'
            ? message.content
            : message.content.filter((p): p is { type: 'text', text: string } => p.type === 'text').map(p => p.text).join('');

        // 添加用户消息
        const attachmentMetadata: MessageAttachment[] = pendingAttachments
            .filter(a => a.content && !a.error)
            .map(a => ({
                filename: a.filename,
                size: a.size,
            }));

        const userMsg: BackendMessage = {
            id: `msg-user-${Date.now()}`,
            role: 'user',
            text: userText,
            timestamp: Date.now(),
            attachments: attachmentMetadata,
        };
        setMessages(prev => [...prev, userMsg]);
        setPendingAttachments([]);
        setIsRunning(true);

        // 模拟 AI 回复
        const botMsgId = `msg-bot-${Date.now()}`;
        setMessages(prev => [...prev, {
            id: botMsgId,
            role: 'model',
            text: '',
            timestamp: Date.now(),
            isThinking: true,
        }]);

        // 模拟流式延迟
        setTimeout(() => {
            let responseText = "我收到了你的消息";
            if (attachmentMetadata.length > 0) {
                responseText += `，并看到了 ${attachmentMetadata.length} 个附件（${attachmentMetadata[0].filename}）`;
            }
            responseText += "。\n\n正在分析您的需求，以下是初步分析结果：\n\n### 用户分布预测\n\n```mermaid\npie title 用户群体占比\n    \"K12 学生\" : 45\n    \"大学生\" : 25\n    \"职场人士\" : 20\n    \"其他\" : 10\n```\n\n### 项目开发计划\n\n```mermaid\ngantt\n    title 在线教育平台开发计划\n    dateFormat  YYYY-MM-DD\n    section 需求阶段\n    需求分析       :active, a1, 2024-01-01, 10d\n    UI设计         :after a1, 5d\n    section 开发阶段\n    核心功能开发    :2024-01-16, 20d\n    次要功能开发    :2024-02-05, 15d\n    section 测试发布\n    集成测试       :2024-02-20, 5d\n    正式发布       :2024-02-25, 2d\n```\n\n请确认以上分析是否符合预期。";

            // 分段显示
            let currentText = "";
            const chunks = responseText.split("");
            let i = 0;
            const interval = setInterval(() => {
                if (i >= chunks.length) {
                    clearInterval(interval);
                    setIsRunning(false);
                    setMessages(prev => prev.map(m => m.id === botMsgId ? { ...m, isThinking: false } : m));
                    onMockResponse?.(userText);
                    return;
                }
                currentText += chunks[i];
                setMessages(prev => prev.map(m => m.id === botMsgId ? { ...m, text: currentText } : m));
                i++;
            }, 10); // 加快一点速度，30 -> 10
        }, 1000);
    };

    return {
        messages,
        isRunning,
        onNew,
        onReload: async () => { console.log("Reload mocked"); },
        pendingAttachments,
        handleFilesSelected,
        removeAttachment,
    };
}

export function MockAssistantChat({ assistant, onBack, onMockResponse }: AssistantChatProps) {
    const {
        messages,
        isRunning,
        onNew,
        onReload,
        pendingAttachments,
        handleFilesSelected,
        removeAttachment
    } = useMockChatState(assistant.id, onMockResponse);

    const adapter: ExternalStoreAdapter = {
        isRunning,
        messages: messages.map(convertToThreadMessage) as unknown as readonly ThreadMessage[],
        onNew,
        onReload,
    };

    const runtime = useExternalStoreRuntime(adapter);

    return (
        <AssistantRuntimeProvider runtime={runtime}>
            <div className="w-full flex flex-col bg-surface-light dark:bg-surface-dark rounded-xl shadow-lg border border-border-light dark:border-border-dark overflow-hidden h-full">
                {/* Header */}
                <div className="px-4 py-3 border-b border-border-light dark:border-border-dark flex justify-between items-center bg-gray-50 dark:bg-gray-800/50 shrink-0 h-12">
                    <div className="flex items-center gap-3">
                        <button onClick={onBack} className="lg:hidden mr-1 text-gray-500 hover:text-gray-700">
                            <ChevronLeft size={20} />
                        </button>
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm text-white ${assistant.id === 'alex' ? 'bg-primary' : 'bg-secondary'}`}>
                            {assistant.initial}
                        </div>
                        <div>
                            <h2 className="font-semibold text-sm text-gray-800 dark:text-white leading-tight">
                                {assistant.name}
                            </h2>
                            <p className="text-[10px] text-gray-500 dark:text-gray-400">
                                {assistant.role}
                            </p>
                        </div>
                    </div>
                </div>

                {/* Chat Thread */}
                <ThreadPrimitive.Root className="flex-grow overflow-hidden flex flex-col bg-white dark:bg-gray-900">
                    <ThreadPrimitive.Viewport className="flex-grow overflow-y-auto p-4 space-y-6 scroll-smooth">
                        <ThreadPrimitive.Messages
                            components={{
                                UserMessage: CustomUserMessage,
                                AssistantMessage: ({ ...props }) => <CustomAssistantMessage assistant={assistant} {...props} />,
                            }}
                        />
                    </ThreadPrimitive.Viewport>

                    {/* Composer */}
                    <div className="p-3 border-t border-border-light dark:border-border-dark bg-gray-50 dark:bg-gray-800/30 shrink-0">
                        <AttachmentList attachments={pendingAttachments} onRemove={removeAttachment} />
                        <ComposerPrimitive.Root className="relative flex items-center gap-2">
                            <ComposerPrimitive.Input
                                autoFocus
                                placeholder="请输入..."
                                className="flex-grow pl-3 pr-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary focus:border-primary text-sm shadow-sm text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 transition-shadow disabled:opacity-50 disabled:cursor-not-allowed"
                            />
                            <AttachmentButton onFilesSelected={handleFilesSelected} disabled={isRunning} />
                            <ComposerPrimitive.Send className="p-2 rounded-lg shadow-sm transition-colors flex items-center justify-center bg-primary hover:bg-indigo-600 text-white cursor-pointer disabled:bg-gray-200 disabled:dark:bg-gray-700 disabled:text-gray-400 disabled:cursor-not-allowed">
                                <Send size={18} />
                            </ComposerPrimitive.Send>
                        </ComposerPrimitive.Root>
                    </div>
                </ThreadPrimitive.Root>
            </div>
        </AssistantRuntimeProvider>
    );
}

function CustomUserMessage() {
    const message = useMessage();
    const attachments = message.metadata?.custom?.attachments as MessageAttachment[] | undefined;

    return (
        <MessagePrimitive.Root className="flex gap-3 flex-row-reverse group">
            <div className="w-8 h-8 rounded-full flex items-center justify-center shrink-0 mt-1 bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
                <User size={16} />
            </div>
            <div className="flex flex-col max-w-[85%] items-end">
                <div className="px-4 py-2.5 rounded-2xl text-sm leading-relaxed shadow-sm bg-primary text-white rounded-tr-none">
                    <MessagePrimitive.Content />
                </div>
                {attachments && attachments.length > 0 && (
                    <MessageAttachments attachments={attachments} />
                )}
            </div>
        </MessagePrimitive.Root>
    );
}

function TypingIndicator() {
    return (
        <div className="flex items-center gap-1 py-1">
            <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
            <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
            <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
        </div>
    );
}

function CustomAssistantMessage({ assistant }: { assistant: Assistant }) {
    const message = useMessage();
    const isInProgress = message.status?.type === 'running';
    const hasNoContent = !message.content || message.content.length === 0 ||
        (message.content.length === 1 && message.content[0].type === 'text' && !message.content[0].text);

    return (
        <MessagePrimitive.Root className="flex gap-3 flex-row group">
            <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 mt-1 text-white ${assistant.id === 'alex' ? 'bg-primary' : 'bg-secondary'}`}>
                <Bot size={16} />
            </div>
            <div className="flex flex-col max-w-[85%] items-start">
                <div className="px-4 py-2.5 rounded-2xl text-sm leading-relaxed shadow-sm bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200 rounded-tl-none border border-gray-200 dark:border-gray-700">
                    <MessagePrimitive.Content components={{ Text: MarkdownText }} />
                    {isInProgress && hasNoContent && <TypingIndicator />}
                </div>
                <ActionBarPrimitive.Root className="gap-1 mt-1 opacity-0 group-hover:opacity-100 transition-opacity flex">
                    <ActionBarPrimitive.Copy className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded text-gray-600 dark:text-gray-400" title="复制消息">
                        <MessagePrimitive.If copied={false}><Copy size={14} /></MessagePrimitive.If>
                        <MessagePrimitive.If copied><Check size={14} className="text-green-500" /></MessagePrimitive.If>
                    </ActionBarPrimitive.Copy>
                    <ActionBarPrimitive.Reload className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded text-gray-600 dark:text-gray-400" title="重新生成">
                        <RefreshCw size={14} />
                    </ActionBarPrimitive.Reload>
                </ActionBarPrimitive.Root>
            </div>
        </MessagePrimitive.Root>
    );
}
