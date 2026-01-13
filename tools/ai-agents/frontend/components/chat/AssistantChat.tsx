/**
 * AssistantChat 组件 - 使用 Assistant-ui 构建的对话界面
 * 集成现有后端 SSE API
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
import { createSession, sendMessageStream, ProgressInfo } from '../../services/backendService';
import { Assistant, AssistantId, PendingAttachment, MessageAttachment } from '../../types';
import { processFile, buildMessageWithAttachments } from '../../utils/attachmentUtils';

interface AssistantChatProps {
    assistant: Assistant;
    onBack: () => void;
    onProgressChange?: (progress: ProgressInfo | null) => void;
}

// 将后端消息格式转换为 Assistant-ui 格式
interface BackendMessage {
    id: string;  // 新增：消息 ID
    role: 'user' | 'model';
    text: string;
    timestamp: number;
    isThinking?: boolean;
    attachments?: MessageAttachment[];  // 新增
}

function convertToThreadMessage(msg: BackendMessage, index: number) {
    const baseMessage = {
        id: msg.id,  // 使用 BackendMessage 的原始 ID
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
                    attachments: msg.attachments,  // 传递附件元数据
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

// 内部聊天状态管理
function useChatState(assistantId: AssistantId, onProgressChange?: (progress: ProgressInfo | null) => void) {
    const [messages, setMessages] = useState<BackendMessage[]>([]);
    const [isRunning, setIsRunning] = useState(false);
    const sessionIdRef = useRef<string | null>(null);
    const [isInitialized, setIsInitialized] = useState(false);

    // 新增：附件状态
    const [pendingAttachments, setPendingAttachments] = useState<PendingAttachment[]>([]);

    // 新增：处理文件选择
    const handleFilesSelected = async (files: File[]) => {
        const processedFiles = await Promise.all(
            files.map(file => processFile(file))
        );
        setPendingAttachments(prev => [...prev, ...processedFiles]);
    };

    // 新增：删除附件
    const removeAttachment = (id: string) => {
        setPendingAttachments(prev => prev.filter(a => a.id !== id));
    };

    // 初始化会话
    useEffect(() => {
        let cancelled = false;

        async function initSession() {
            try {
                const session = await createSession('AI4SE Project', assistantId);
                if (cancelled) return;

                sessionIdRef.current = session.sessionId;

                // 发送隐藏的欢迎请求获取AI欢迎消息
                const welcomeMsgTimestamp = Date.now();
                setMessages([{
                    id: `msg-welcome-${welcomeMsgTimestamp}`,
                    role: 'model',
                    text: '',
                    timestamp: welcomeMsgTimestamp,
                    isThinking: true,
                }]);
                setIsRunning(true);

                await sendMessageStream(
                    session.sessionId,
                    '请显示欢迎语',
                    (fullText) => {
                        setMessages([{
                            id: `msg-welcome-${welcomeMsgTimestamp}`,
                            role: 'model',
                            text: fullText,
                            timestamp: welcomeMsgTimestamp,
                            isThinking: false,
                        }]);
                    }
                );

                setIsRunning(false);
                setIsInitialized(true);
            } catch (error) {
                console.error('Failed to initialize session:', error);
                const errorTimestamp = Date.now();
                setMessages([{
                    id: `msg-error-${errorTimestamp}`,
                    role: 'model',
                    text: '抱歉，无法连接到后端服务。请确保服务已启动。',
                    timestamp: errorTimestamp,
                    isThinking: false,
                }]);
                setIsRunning(false);
                setIsInitialized(true);
            }
        }

        initSession();
        return () => { cancelled = true; };
    }, [assistantId]);

    // 发送消息处理
    const onNew = async (message: AppendMessage) => {
        if (!sessionIdRef.current) return;

        const userText = typeof message.content === 'string'
            ? message.content
            : message.content
                .filter((part): part is { type: 'text'; text: string } => part.type === 'text')
                .map(part => part.text)
                .join('');

        // 检查消息内容或有效附件
        const hasContent = userText.trim().length > 0;
        const hasValidAttachments = pendingAttachments.some(
            a => a.content && !a.error
        );

        if (!hasContent && !hasValidAttachments) {
            setPendingAttachments([]);
            return;
        }

        // 构建包含文件内容的完整消息
        const fullMessageText = buildMessageWithAttachments(userText, pendingAttachments);

        // 提取附件元数据用于显示
        const attachmentMetadata: MessageAttachment[] = pendingAttachments
            .filter(a => a.content && !a.error)
            .map(a => ({
                filename: a.filename,
                size: a.size,
            }));

        // 添加用户消息（包含附件元数据）
        const userMsgTimestamp = Date.now();
        const userMsg: BackendMessage = {
            id: `msg-user-${userMsgTimestamp}`,
            role: 'user',
            text: userText,  // 原始用户文本
            timestamp: userMsgTimestamp,
            attachments: attachmentMetadata,  // 附件元数据
        };
        setMessages(prev => [...prev, userMsg]);
        setIsRunning(true);

        // 清空待发送附件
        setPendingAttachments([]);

        // 添加 AI 占位消息
        const botMsgTimestamp = Date.now();
        setMessages(prev => [...prev, {
            id: `msg-bot-${botMsgTimestamp}`,
            role: 'model',
            text: '',
            timestamp: botMsgTimestamp,
            isThinking: true,
        }]);

        try {
            await sendMessageStream(
                sessionIdRef.current,
                fullMessageText,  // 发送包含文件内容的完整消息
                (fullText) => {
                    // XML artifact: 匹配闭合和未闭合(流式)两种情况
                    const xmlArtifactRegex = /<artifact\s+key="[^"]*"\s*>[\s\S]*?(<\/artifact>|$)/g;
                    const mdArtifactRegex = /:::artifact\s*([\s\S]*?)(\s*:::|$)/g;
                    let displayMessage = fullText
                        .replace(xmlArtifactRegex, '\n*(已更新右侧分析成果)*\n')
                        .replace(mdArtifactRegex, '\n*(已更新右侧分析成果)*\n');

                    setMessages(prev => {
                        const newMessages = [...prev];
                        const lastIdx = newMessages.length - 1;
                        if (newMessages[lastIdx]?.role === 'model' && newMessages[lastIdx]?.timestamp === botMsgTimestamp) {
                            newMessages[lastIdx] = {
                                ...newMessages[lastIdx],
                                text: displayMessage,
                                isThinking: false,
                            };
                        }
                        return newMessages;
                    });
                },
                onProgressChange  // 传递进度回调
            );
        } catch (error) {
            console.error('Message send failed:', error);
            setMessages(prev => {
                const newMessages = [...prev];
                const lastIdx = newMessages.length - 1;
                if (newMessages[lastIdx]?.role === 'model') {
                    newMessages[lastIdx] = {
                        ...newMessages[lastIdx],
                        text: '抱歉，由于网络或服务原因，我无法完成回复。请稍后再试。',
                        isThinking: false,
                    };
                }
                return newMessages;
            });
        } finally {
            setIsRunning(false);
        }
    };

    return {
        messages,
        isRunning,
        onNew,
        onReload: async (parentId: string | null) => {
            console.log('[Reload] parentId:', parentId);
            console.log('[Reload] messages:', messages);

            // parentId 是要重试的消息的父消息 ID（用户消息）
            if (!parentId) {
                console.log('[Reload] No parentId, aborting');
                return;
            }

            // 找到父消息（用户消息）的索引
            const parentIndex = messages.findIndex(m => m.id === parentId);
            console.log('[Reload] parentIndex:', parentIndex);

            if (parentIndex === -1) {
                console.log('[Reload] Parent message not found, aborting');
                return;
            }

            const userMsg = messages[parentIndex];
            if (!userMsg || userMsg.role !== 'user') {
                console.log('[Reload] Parent is not a user message, aborting');
                return;
            }

            // 保留用户消息，只删除 AI 回复及其后的所有消息
            setMessages(prev => prev.slice(0, parentIndex + 1));

            // 使用用户消息重新生成 AI 回复
            const userText = userMsg.text;
            const attachments = userMsg.attachments || [];

            // 构建包含文件内容的完整消息
            const fullMessageText = attachments.length > 0
                ? buildMessageWithAttachments(userText, attachments.map(a => ({
                    id: `att-${Date.now()}`,
                    filename: a.filename,
                    size: a.size,
                    content: `File: ${a.filename}`, // 简化处理
                    type: 'text/plain'
                })))
                : userText;

            // 添加新的 AI 占位消息
            const botMsgTimestamp = Date.now();
            setMessages(prev => [...prev, {
                id: `msg-reload-${botMsgTimestamp}`,
                role: 'model',
                text: '',
                timestamp: botMsgTimestamp,
                isThinking: true,
            }]);

            setIsRunning(true);

            try {
                await sendMessageStream(
                    sessionIdRef.current!,
                    fullMessageText,
                    (fullText) => {
                        const xmlArtifactRegex = /<artifact\s+key="[^"]*"\s*>[\s\S]*?<\/artifact>/g;
                        const mdArtifactRegex = /:::artifact\s*([\s\S]*?)(\s*:::|$)/g;
                        let displayMessage = fullText
                            .replace(xmlArtifactRegex, '\n*(已更新右侧分析成果)*\n')
                            .replace(mdArtifactRegex, '\n*(已更新右侧分析成果)*\n');

                        setMessages(prev => {
                            const newMessages = [...prev];
                            const lastIdx = newMessages.length - 1;
                            if (newMessages[lastIdx]?.role === 'model' && newMessages[lastIdx]?.timestamp === botMsgTimestamp) {
                                newMessages[lastIdx] = {
                                    ...newMessages[lastIdx],
                                    text: displayMessage,
                                    isThinking: false,
                                };
                            }
                            return newMessages;
                        });
                    }
                );
            } catch (error) {
                console.error('Message reload failed:', error);
                setMessages(prev => {
                    const newMessages = [...prev];
                    const lastIdx = newMessages.length - 1;
                    if (newMessages[lastIdx]?.role === 'model') {
                        newMessages[lastIdx] = {
                            ...newMessages[lastIdx],
                            text: '抱歉，重试失败。请稍后再试。',
                            isThinking: false,
                        };
                    }
                    return newMessages;
                });
            } finally {
                setIsRunning(false);
            }
        },
        isInitialized,
        pendingAttachments,
        handleFilesSelected,
        removeAttachment,
    };
}

// 主组件
export function AssistantChat({ assistant, onBack, onProgressChange }: AssistantChatProps) {
    const {
        messages,
        isRunning,
        onNew,
        onReload,
        isInitialized,
        pendingAttachments,
        handleFilesSelected,
        removeAttachment
    } = useChatState(assistant.id, onProgressChange);

    // 创建 External Store 适配器
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
                <div className="px-6 py-4 border-b border-border-light dark:border-border-dark flex justify-between items-center bg-gray-50 dark:bg-gray-800/50 shrink-0 h-16">
                    <div className="flex items-center gap-3">
                        <button
                            onClick={onBack}
                            className="lg:hidden mr-2 text-gray-500 hover:text-gray-700"
                        >
                            <ChevronLeft size={20} />
                        </button>
                        <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-lg text-white ${assistant.id === 'alex' ? 'bg-primary' : 'bg-secondary'}`}>
                            {assistant.initial}
                        </div>
                        <div>
                            <h2 className="font-semibold text-gray-800 dark:text-white leading-tight">
                                {assistant.name}
                            </h2>
                            <p className="text-xs text-gray-500 dark:text-gray-400">
                                {assistant.role}
                            </p>
                        </div>
                    </div>
                    <button
                        onClick={onBack}
                        className="text-xs text-primary hover:underline hidden lg:block"
                    >
                        切换助手
                    </button>
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
                    <div className="p-4 border-t border-border-light dark:border-border-dark bg-gray-50 dark:bg-gray-800/30 shrink-0">
                        {/* 附件列表 */}
                        <AttachmentList
                            attachments={pendingAttachments}
                            onRemove={removeAttachment}
                        />

                        <ComposerPrimitive.Root className="relative flex items-center gap-2">
                            <ComposerPrimitive.Input
                                autoFocus
                                placeholder="请输入..."
                                className="flex-grow pl-4 pr-4 py-3 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-xl focus:ring-2 focus:ring-primary focus:border-primary text-sm shadow-sm text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 transition-shadow disabled:opacity-50 disabled:cursor-not-allowed"
                            />
                            {/* 附件按钮 - 在输入框和发送按钮之间 */}
                            <AttachmentButton
                                onFilesSelected={handleFilesSelected}
                                disabled={isRunning}
                            />
                            <ComposerPrimitive.Send className="p-3 rounded-full shadow-sm transition-colors flex items-center justify-center bg-primary hover:bg-indigo-600 text-white cursor-pointer disabled:bg-gray-200 disabled:dark:bg-gray-700 disabled:text-gray-400 disabled:cursor-not-allowed">
                                <Send size={20} />
                            </ComposerPrimitive.Send>
                        </ComposerPrimitive.Root>
                    </div>
                </ThreadPrimitive.Root>
            </div>
        </AssistantRuntimeProvider>
    );
}

// 自定义用户消息组件
function CustomUserMessage() {
    const message = useMessage();

    // 从消息元数据中提取附件
    const attachments = message.metadata?.custom?.attachments as MessageAttachment[] | undefined;

    return (
        <MessagePrimitive.Root className="flex gap-3 flex-row-reverse group">
            <div className="w-8 h-8 rounded-full flex items-center justify-center shrink-0 mt-1 bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
                <User size={16} />
            </div>
            <div className="flex flex-col max-w-[85%] items-end">
                <div className="px-4 py-3 rounded-2xl text-sm leading-relaxed shadow-sm bg-primary text-white rounded-tr-none">
                    <MessagePrimitive.Content />
                </div>
                {/* 显示附件 */}
                {attachments && attachments.length > 0 && (
                    <MessageAttachments attachments={attachments} />
                )}

                {/* 操作栏 */}
                <ActionBarPrimitive.Root className="gap-1 mt-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <ActionBarPrimitive.Copy
                        className="p-1.5 hover:bg-gray-200 dark:hover:bg-gray-700 rounded text-gray-600 dark:text-gray-400"
                        title="复制消息"
                    >
                        <MessagePrimitive.If copied={false}>
                            <Copy size={14} />
                        </MessagePrimitive.If>
                        <MessagePrimitive.If copied>
                            <Check size={14} className="text-green-500" />
                        </MessagePrimitive.If>
                    </ActionBarPrimitive.Copy>
                </ActionBarPrimitive.Root>
            </div>
        </MessagePrimitive.Root>
    );
}

// 等待动画组件
function TypingIndicator() {
    return (
        <div className="flex items-center gap-1 py-1">
            <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
            <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
            <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
        </div>
    );
}

// 自定义助手消息组件
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
                <div className="px-4 py-3 rounded-2xl text-sm leading-relaxed shadow-sm bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200 rounded-tl-none border border-gray-200 dark:border-gray-700">
                    <MessagePrimitive.Content components={{ Text: MarkdownText }} />
                    {isInProgress && hasNoContent && <TypingIndicator />}
                </div>

                {/* 操作栏 */}
                <ActionBarPrimitive.Root className="gap-1 mt-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <ActionBarPrimitive.Reload
                        className="p-1.5 hover:bg-gray-200 dark:hover:bg-gray-700 rounded text-gray-600 dark:text-gray-400 disabled:opacity-50 disabled:cursor-not-allowed"
                        title="重新生成"
                        disabled={isInProgress}
                    >
                        <RefreshCw size={14} className={isInProgress ? 'animate-spin' : ''} />
                    </ActionBarPrimitive.Reload>

                    <ActionBarPrimitive.Copy
                        className="p-1.5 hover:bg-gray-200 dark:hover:bg-gray-700 rounded text-gray-600 dark:text-gray-400"
                        title="复制消息"
                    >
                        <MessagePrimitive.If copied={false}>
                            <Copy size={14} />
                        </MessagePrimitive.If>
                        <MessagePrimitive.If copied>
                            <Check size={14} className="text-green-500" />
                        </MessagePrimitive.If>
                    </ActionBarPrimitive.Copy>
                </ActionBarPrimitive.Root>
            </div>
        </MessagePrimitive.Root>
    );
}

export default AssistantChat;
