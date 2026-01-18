import React from 'react';
import {
    MessagePrimitive,
    useMessage,
    ActionBarPrimitive,
} from '@assistant-ui/react';
import { User, Copy, Check } from 'lucide-react';
import { MessageAttachments } from './MessageAttachments';
import { MessageAttachment } from '../../types';

export function CustomUserMessage() {
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
