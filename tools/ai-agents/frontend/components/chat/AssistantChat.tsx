/**
 * AssistantChat 组件 - 使用 Assistant-ui 构建的对话界面
 * 集成 Vercel AI SDK Data Stream Protocol (V2)
 */
import React, { useEffect, useState, useCallback, useRef } from 'react';
import {
    AssistantRuntimeProvider,
    ThreadPrimitive,
    ComposerPrimitive,
    MessagePrimitive,
    useMessage,
    ActionBarPrimitive,
    useComposerRuntime,
    useAssistantRuntime,
} from '@assistant-ui/react';
import { Bot, Send, User, ChevronLeft, Copy, Check, RefreshCw } from 'lucide-react';
import { MarkdownText } from './MarkdownText';
import { AttachmentList } from './AttachmentList';
import { AttachmentButton } from './AttachmentButton';
import { MessageAttachments } from './MessageAttachments';
import { createSession, ProgressInfo } from '../../services/backendService';
import { Assistant, AssistantId, PendingAttachment, MessageAttachment } from '../../types';
import { processFile, buildMessageWithAttachments } from '../../utils/attachmentUtils';
import { useChatRuntime } from '../../hooks/useChatRuntime';
import { UpdateArtifactToolUI } from '../tools/UpdateArtifactToolUI';
import { ConfirmationToolUI } from '../tools/ConfirmationToolUI';
import { ErrorBoundary } from '../common/ErrorBoundary';

interface AssistantChatProps {
    assistant: Assistant;
    onBack: () => void;
    onProgressChange?: (progress: ProgressInfo | null) => void;
}

// 错误提示组件
function RuntimeErrorDisplay() {
    const runtime = useAssistantRuntime();
    // 使用 any 绕过类型检查，以访问可能存在的 error 和 reload
    // Vercel AI SDK 的 error 对象会被适配器传递
    const error = (runtime.thread as any).error;
    
    if (!error) return null;
    
    return (
        <div className="absolute top-16 left-0 w-full bg-red-50 dark:bg-red-900/20 border-b border-red-200 dark:border-red-800 p-2 text-center text-sm text-red-600 dark:text-red-400 flex items-center justify-center gap-2 z-10 transition-all animate-in slide-in-from-top-2">
            <span>出错了: {error.message || "未知错误"}</span>
            <button 
                onClick={() => (runtime.thread as any).reload?.()} 
                className="px-3 py-0.5 bg-white dark:bg-red-950 rounded border border-red-200 dark:border-red-800 hover:bg-red-50 dark:hover:bg-red-900 transition-colors shadow-sm font-medium"
            >
                重试
            </button>
        </div>
    );
}

// 内部会话组件 (确保 sessionId 存在时渲染)
const ChatSession = ({ assistant, sessionId, onBack, onProgressChange }: AssistantChatProps & { sessionId: string }) => {
    // 使用 V2 Runtime
    const runtime = useChatRuntime(sessionId, assistant.id, onProgressChange);
    const welcomeSentRef = useRef(false);

    // 发送欢迎消息 (仅一次)
    useEffect(() => {
        if (welcomeSentRef.current) return;
        welcomeSentRef.current = true;

        const welcomeRequest = {
            role: "user" as const,
            content: [{ type: "text" as const, text: "请显示欢迎语" }],
            metadata: { custom: { type: 'welcome_trigger' } }
        };

        // 延迟一点发送，确保连接建立
        const timer = setTimeout(() => {
            // 检查是否已有消息 (避免 HMR 或重渲染导致重复)
            // 暂时无法直接同步访问 runtime.messages 状态，直接发送
            runtime.thread.append(welcomeRequest);
        }, 100);

        return () => clearTimeout(timer);
    }, [sessionId]); // 仅在 sessionId 变化时执行

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

                <RuntimeErrorDisplay />

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
                    <CustomComposer />
                </ThreadPrimitive.Root>
            </div>
        </AssistantRuntimeProvider>
    );
};

// 主组件：处理 Session 创建
export function AssistantChat(props: AssistantChatProps) {
    const [sessionId, setSessionId] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        let active = true;

        async function init() {
            try {
                const session = await createSession('AI4SE Project', props.assistant.id);
                if (active) {
                    setSessionId(session.sessionId);
                }
            } catch (err) {
                if (active) {
                    console.error("Failed to create session:", err);
                    setError(String(err));
                }
            }
        }

        // 重置状态
        setSessionId(null);
        setError(null);
        init();

        return () => { active = false; };
    }, [props.assistant.id]);

    if (error) {
        return (
            <div className="h-full flex items-center justify-center text-red-500">
                初始化失败: {error}
            </div>
        );
    }

    if (!sessionId) {
        return (
            <div className="h-full flex items-center justify-center text-gray-500">
                <div className="flex flex-col items-center gap-2">
                    <span className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
                    <span>正在创建会话...</span>
                </div>
            </div>
        );
    }

    return (
        <ErrorBoundary>
            <ChatSession {...props} sessionId={sessionId} />
        </ErrorBoundary>
    );
}

// 为 window 对象添加 assistantComposer 类型声明
declare global {
    interface Window {
        assistantComposer?: {
            setText: (text: string) => void;
            send: () => void;
            getText: () => string;
        };
    }
}

// 自定义 Composer 组件 - 暴露编程式 API 供浏览器自动化使用 + 处理附件
function CustomComposer() {
    const composerRuntime = useComposerRuntime();
    const assistantRuntime = useAssistantRuntime();

    // 附件状态管理
    const [pendingAttachments, setPendingAttachments] = useState<PendingAttachment[]>([]);
    const [isUploading, setIsUploading] = useState(false);

    // 新增：处理文件选择
    const handleFilesSelected = async (files: File[]) => {
        setIsUploading(true);
        try {
            const processedFiles = await Promise.all(
                files.map(file => processFile(file))
            );
            setPendingAttachments(prev => [...prev, ...processedFiles]);
        } finally {
            setIsUploading(false);
        }
    };

    // 新增：删除附件
    const removeAttachment = (id: string) => {
        setPendingAttachments(prev => prev.filter(a => a.id !== id));
    };

    // 处理发送
    const handleSend = () => {
        const text = composerRuntime.getState().text.trim();

        const hasContent = text.length > 0;
        const hasValidAttachments = pendingAttachments.some(a => a.content && !a.error);

        if (!hasContent && !hasValidAttachments) return;

        // 构建包含文件内容的完整消息
        const fullMessageText = buildMessageWithAttachments(text, pendingAttachments);

        // 构造附件元数据
        const attachmentMetadata: MessageAttachment[] = pendingAttachments
            .filter(a => a.content && !a.error)
            .map(a => ({
                filename: a.filename,
                size: a.size,
            }));

        // 调用 runtime append 发送消息
        assistantRuntime.thread.append({
            role: "user",
            content: [{ type: "text", text: fullMessageText }],
            metadata: {
                custom: {
                    attachments: attachmentMetadata
                }
            }
        });

        // 清空状态
        composerRuntime.setText("");
        setPendingAttachments([]);
    };

    // 将 composer 方法暴露到 window 对象供浏览器自动化使用
    useEffect(() => {
        window.assistantComposer = {
            setText: (text: string) => {
                composerRuntime.setText(text);
            },
            send: () => {
                // 自动化调用 send 时也走 handleSend 逻辑
                // 但 handleSend 依赖闭包中的 pendingAttachments
                // 这里直接调用 handleSend 即可
                handleSend();
            },
            getText: () => {
                return composerRuntime.getState().text;
            },
        };

        return () => {
            delete window.assistantComposer;
        };
    }, [composerRuntime, assistantRuntime, pendingAttachments]); // 依赖 pendingAttachments 确保 send 获取最新状态

    return (
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
                    onKeyDown={(e) => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                            e.preventDefault();
                            handleSend();
                        }
                    }}
                />
                {/* 附件按钮 - 在输入框和发送按钮之间 */}
                <AttachmentButton
                    onFilesSelected={handleFilesSelected}
                    disabled={isUploading}
                />

                {/* 自定义发送按钮 (替换 ComposerPrimitive.Send) */}
                <button
                    id="send-button"
                    aria-label="发送消息"
                    onClick={handleSend}
                    disabled={isUploading || (!composerRuntime.getState().text.trim() && pendingAttachments.length === 0)}
                    className="p-3 rounded-full shadow-sm transition-colors flex items-center justify-center bg-primary hover:bg-indigo-600 text-white cursor-pointer disabled:bg-gray-200 disabled:dark:bg-gray-700 disabled:text-gray-400 disabled:cursor-not-allowed"
                >
                    <Send size={20} />
                </button>
            </ComposerPrimitive.Root>
        </div>
    );
}

// 自定义用户消息组件
function CustomUserMessage() {
    const message = useMessage();

    // 如果是欢迎触发消息，不显示
    // 兼容 metadata 检查和内容检查 (因为 Vercel SDK 可能丢弃 metadata)
    if (message.metadata?.custom?.type === 'welcome_trigger' || (message.content[0]?.type === 'text' && message.content[0]?.text === '请显示欢迎语')) {
        return null;
    }

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
                    <MessagePrimitive.Content
                        components={{
                            Text: MarkdownText as any,
                            tools: {
                                by_name: {
                                    UpdateArtifact: UpdateArtifactToolUI,
                                    ask_confirmation: ConfirmationToolUI
                                }
                            }
                        }}
                    />
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
