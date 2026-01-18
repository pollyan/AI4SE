import React from 'react';
import {
    MessagePrimitive,
    useMessage,
    ActionBarPrimitive,
} from '@assistant-ui/react';
import { Bot, Copy, Check, RefreshCw } from 'lucide-react';
import { MarkdownText } from './MarkdownText';
import { UpdateArtifactToolUI } from '../tools/UpdateArtifactToolUI';
import { ConfirmationToolUI } from '../tools/ConfirmationToolUI';
import { TypingIndicator } from './TypingIndicator';
import { Assistant } from '../../types';

interface CustomAssistantMessageProps {
    assistant: Assistant;
}

export function CustomAssistantMessage({ assistant }: CustomAssistantMessageProps) {
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
                <div style={{ border: '2px solid red' }} className="px-4 py-3 rounded-2xl text-sm leading-relaxed shadow-sm bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200 rounded-tl-none border border-gray-200 dark:border-gray-700">
                    <div>DEBUG: Content Length: {message.content?.length}</div>
                    <MessagePrimitive.Content
                        components={{
                            Text: MarkdownText,
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
