/**
 * AssistantChat 组件 - 使用原生 Vercel AI SDK 构建的对话界面
 * 使用 AI SDK 5.0 的 useChat hook，不再依赖 @assistant-ui/react
 */
import React, { useEffect, useState, useRef } from 'react';
import { ChevronLeft, Send, Square, Paperclip, X } from 'lucide-react';
import { createSession, ProgressInfo } from '../../services/backendService';
import { Assistant } from '../../types';
import { useVercelChat } from '../../hooks/useVercelChat';
import { ErrorBoundary } from '../common/ErrorBoundary';
import { MarkdownText } from './MarkdownText';

interface AssistantChatProps {
    assistant: Assistant;
    onBack: () => void;
    onProgressChange?: (progress: ProgressInfo | null) => void;
}

// 消息类型
interface ChatMessage {
    id: string;
    role: 'user' | 'assistant';
    parts: Array<{ type: string; text?: string;[key: string]: any }>;
}

const LISA_SUGGESTIONS = [
    { id: 'A', label: '需求评审', description: '扫描需求文档，识别逻辑漏洞与风险', action: '需求评审' },
    { id: 'B', label: '测试设计', description: '为新功能制定策略 (RBT) 并输出用例', action: '测试设计' },
    { id: 'C', label: '生产缺陷分析', description: '分析线上缺陷、性能瓶颈', action: '生产缺陷分析' },
    { id: 'D', label: '专项测试策略', description: '制定非功能、自动化等专项策略', action: '专项测试策略规划' },
    { id: 'E', label: '现状评估', description: '评估当前团队与流程质量', action: '产品测试现状评估' },
    { id: 'F', label: '通用咨询', description: '探讨任何测试与质量相关的话题', action: '通用测试咨询' },
];

// Helper: Read file content as Data URL
const readFileAsDataURL = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result as string);
        reader.onerror = reject;
        reader.readAsDataURL(file);
    });
};

// 内部会话组件 (确保 sessionId 存在时渲染)
const ChatSession = ({ assistant, sessionId, onBack, onProgressChange }: AssistantChatProps & { sessionId: string }) => {
    const [input, setInput] = useState('');
    const [files, setFiles] = useState<File[]>([]);
    const viewportRef = useRef<HTMLDivElement>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    // 使用新的 useVercelChat hook
    const { messages, status, sendMessage, stop, error } = useVercelChat({
        sessionId,
        assistantType: assistant.id,
        onProgressChange: onProgressChange || undefined,
    });

    // 自动滚动到底部
    useEffect(() => {
        if (viewportRef.current) {
            viewportRef.current.scrollTop = viewportRef.current.scrollHeight;
        }
    }, [messages]);

    // 处理文件选择
    const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files) {
            setFiles(prev => [...prev, ...Array.from(e.target.files!)]);
        }
        // Reset input so same file can be selected again
        if (fileInputRef.current) fileInputRef.current.value = '';
    };

    // 移除文件
    const removeFile = (index: number) => {
        setFiles(prev => prev.filter((_, i) => i !== index));
    };

    // 处理建议点击
    const handleSuggestionClick = (action: string) => {
        sendMessage({ text: action });
    };

    // 发送消息处理
    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if ((!input.trim() && files.length === 0) || status === 'streaming') return;

        let attachments: any[] = [];

        // 处理附件
        if (files.length > 0) {
            try {
                // Convert files to Data URLs for Vercel AI SDK experimental_attachments
                attachments = await Promise.all(
                    files.map(async (file) => {
                        const url = await readFileAsDataURL(file);
                        return {
                            name: file.name,
                            contentType: file.type,
                            url: url
                        };
                    })
                );
            } catch (err) {
                console.error("Failed to process files:", err);
                return;
            }
        }

        sendMessage({ text: input.trim(), attachments: attachments.length > 0 ? attachments : undefined });
        setInput('');
        setFiles([]);
    };

    // 渲染单条消息
    const renderMessage = (message: ChatMessage, index: number) => {
        const isUser = message.role === 'user';
        const isLast = index === messages.length - 1;
        const isThinking = !isUser && isLast && status === 'streaming' &&
            (!message.parts.length || (message.parts.length === 1 && !message.parts[0].text));

        return (
            <div
                key={message.id}
                className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
            >
                <div className={`max-w-[80%] ${isUser ? 'order-2' : 'order-1'}`}>
                    {/* 头像 */}
                    {!isUser && (
                        <div className="flex items-center gap-2 mb-1">
                            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-white text-sm font-bold ${assistant.id === 'alex' ? 'bg-primary' : 'bg-secondary'}`}>
                                {assistant.initial}
                            </div>
                            <span className="text-xs text-gray-500">{assistant.name}</span>
                        </div>
                    )}

                    {/* 消息内容 */}
                    <div className={`rounded-2xl px-4 py-3 ${isUser
                        ? 'bg-primary text-white rounded-tr-sm'
                        : 'bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200 rounded-tl-sm'
                        }`}>
                        {message.parts.map((part, i) => {
                            if (part.type === 'text' && part.text) {
                                return isUser ? (
                                    <p key={i} className="whitespace-pre-wrap">{part.text}</p>
                                ) : (
                                    <MarkdownText key={i} content={part.text} />
                                );
                            }

                            // 渲染图像或文件附件 (Standard Vercel AI SDK parts)
                            // SDK might normalize experimental_attachments into 'image' parts or keep them separate?
                            // Actually, internal message state usually keeps experimental_attachments on the message object,
                            // OR parts might contain them if normalized.
                            // For now let's check message.experimental_attachments (if exposed by useChat hook message type)
                            // But our ChatMessage type above defined parts. 
                            // Let's use `experimental_attachments` if available on the raw message object, 
                            // OR check if parts have file/image type.

                            return null;
                        })}

                        {/* 渲染附件 (Separate from parts usually in current SDK version) */}
                        {/* @ts-ignore - experimental_attachments might not be in our strict type definition yet */}
                        {message.experimental_attachments && message.experimental_attachments.length > 0 && (
                            <div className="flex flex-wrap gap-2 mt-2">
                                {/* @ts-ignore */}
                                {message.experimental_attachments.map((att, idx) => (
                                    <div key={idx} className="flex items-center gap-2 bg-white/20 dark:bg-black/10 px-2 py-1 rounded text-xs border border-white/10">
                                        <Paperclip size={12} />
                                        <span className="truncate max-w-[150px]">{att.name}</span>
                                    </div>
                                ))}
                            </div>
                        )}

                        {/* 思考中状态 (在气泡内部) */}
                        {isThinking && (
                            <div className="flex items-center gap-2 text-gray-500 my-1 animate-in fade-in zoom-in duration-300">
                                <div className="flex space-x-1">
                                    <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
                                    <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
                                    <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
                                </div>
                                <span className="text-xs">正在思考...</span>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        );
    };

    return (
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

            {/* Error Display */}
            {error && (
                <div className="px-4 py-2 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 text-sm">
                    出错了: {error.message}
                </div>
            )}

            {/* Chat Messages */}
            <div
                ref={viewportRef}
                className="flex-grow overflow-y-auto p-4 space-y-6 scroll-smooth bg-white dark:bg-gray-900"
            >
                {/* Empty State */}
                {messages.length === 0 && (
                    <div className="flex flex-col items-center justify-center mt-10 gap-6 text-center px-4 animate-in fade-in zoom-in duration-500 w-full max-w-4xl mx-auto">
                        <div className="flex flex-col items-center gap-2">
                            <div className={`w-16 h-16 rounded-full flex items-center justify-center text-white text-2xl shadow-lg ${assistant.id === 'alex' ? 'bg-primary' : 'bg-secondary'}`}>
                                {assistant.initial}
                            </div>
                            <h3 className="text-xl font-semibold text-gray-800 dark:text-white">
                                你好，我是 {assistant.name}
                            </h3>
                            <p className="text-gray-500 dark:text-gray-400 max-w-md leading-relaxed">
                                我是你的{assistant.role}。
                                {assistant.id === 'alex' && '我可以协助你进行需求分析、梳理业务逻辑并生成 PRD 文档。请告诉我你的想法！'}
                            </p>
                        </div>

                        {assistant.id !== 'alex' && (
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 w-full">
                                {LISA_SUGGESTIONS.map((suggestion) => (
                                    <button
                                        key={suggestion.id}
                                        onClick={() => handleSuggestionClick(suggestion.action)}
                                        className="flex flex-col items-start p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl hover:border-secondary hover:shadow-md transition-all text-left group"
                                    >
                                        <div className="flex items-center gap-2 mb-1">
                                            <span className="text-lg font-bold text-secondary opacity-80 group-hover:opacity-100">{suggestion.id}.</span>
                                            <span className="font-semibold text-gray-800 dark:text-gray-200 group-hover:text-secondary transition-colors">{suggestion.label}</span>
                                        </div>
                                        <p className="text-xs text-gray-500 dark:text-gray-400 leading-normal">
                                            {suggestion.description}
                                        </p>
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>
                )}

                {/* Messages */}
                {messages.map((msg, idx) => renderMessage(msg, idx))}
            </div>

            {/* Composer */}
            <div className="border-t border-border-light dark:border-border-dark bg-gray-50 dark:bg-gray-800/50">
                {/* 附件预览区域 */}
                {files.length > 0 && (
                    <div className="px-4 pt-3 flex gap-2 overflow-x-auto">
                        {files.map((file, index) => (
                            <div key={index} className="flex items-center gap-2 bg-white dark:bg-gray-700 px-3 py-1.5 rounded-lg border border-gray-200 dark:border-gray-600 text-sm shadow-sm">
                                <span className="truncate max-w-[150px] text-gray-700 dark:text-gray-200">{file.name}</span>
                                <button
                                    onClick={() => removeFile(index)}
                                    className="text-gray-400 hover:text-red-500"
                                >
                                    <X size={14} />
                                </button>
                            </div>
                        ))}
                    </div>
                )}

                <form
                    onSubmit={handleSubmit}
                    className="p-4"
                >
                    <div className="flex items-center gap-2">
                        {/* 附件按钮 */}
                        <button
                            type="button"
                            onClick={() => fileInputRef.current?.click()}
                            disabled={status === 'streaming'}
                            className="p-3 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-full transition-colors disabled:opacity-50"
                            title="添加附件"
                        >
                            <Paperclip size={20} />
                        </button>
                        <input
                            type="file"
                            multiple
                            ref={fileInputRef}
                            className="hidden"
                            onChange={handleFileSelect}
                        />

                        <input
                            type="text"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            placeholder="输入消息..."
                            disabled={status === 'streaming'}
                            className="flex-grow px-4 py-3 rounded-full border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-800 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent disabled:opacity-50"
                        />
                        {status === 'streaming' ? (
                            <button
                                type="button"
                                onClick={stop}
                                className="p-3 rounded-full bg-red-500 hover:bg-red-600 text-white transition-colors"
                                title="停止生成"
                            >
                                <Square size={20} />
                            </button>
                        ) : (
                            <button
                                type="submit"
                                disabled={!input.trim() && files.length === 0}
                                className="p-3 rounded-full bg-primary hover:bg-primary/90 text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                                title="发送"
                            >
                                <Send size={20} />
                            </button>
                        )}
                    </div>
                </form>
            </div>
        </div>
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

export default AssistantChat;
