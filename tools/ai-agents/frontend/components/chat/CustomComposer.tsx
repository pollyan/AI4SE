import React, { useState } from 'react';
import {
    ComposerPrimitive,
    useComposerRuntime,
} from '@assistant-ui/react';
import { Send } from 'lucide-react';
import { AttachmentButton } from './AttachmentButton';
import { useAutomationBridge } from '../../hooks/useAutomationBridge';

export function CustomComposer() {
    const composerRuntime = useComposerRuntime();
    const [isUploading, setIsUploading] = useState(false);

    // 新增：处理文件选择 (Native)
    const handleFilesSelected = async (files: File[]) => {
        setIsUploading(true);
        try {
            for (const file of files) {
                await composerRuntime.addAttachment(file);
            }
        } finally {
            setIsUploading(false);
        }
    };

    // 使用 Hook 暴露自动化 API
    useAutomationBridge({
        api: {
            setText: (text: string) => composerRuntime.setText(text),
            send: () => composerRuntime.send(),
            getText: () => composerRuntime.getState().text,
        }
    });

    return (
        <div className="p-4 border-t border-border-light dark:border-border-dark bg-gray-50 dark:bg-gray-800/30 shrink-0">
            {/* Native Attachments UI */}
            <ComposerPrimitive.Attachments 
                components={{
                    File: ({ attachment, onRemove }) => (
                        <div className="flex items-center gap-2 p-2 mb-2 bg-white dark:bg-gray-700 rounded border border-gray-200 dark:border-gray-600 text-sm w-fit">
                            <span className="text-gray-500 dark:text-gray-400 text-xs uppercase border border-gray-300 dark:border-gray-500 px-1 rounded">
                                FILE
                            </span>
                            <span className="truncate max-w-[200px] text-gray-700 dark:text-gray-200">
                                {attachment.name}
                            </span>
                            <button 
                                onClick={onRemove}
                                className="ml-auto text-gray-400 hover:text-red-500 px-2"
                            >
                                ×
                            </button>
                        </div>
                    )
                }}
            />

            <ComposerPrimitive.Root className="relative flex items-center gap-2">
                <ComposerPrimitive.Input
                    autoFocus
                    placeholder="请输入..."
                    className="flex-grow pl-4 pr-4 py-3 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-xl focus:ring-2 focus:ring-primary focus:border-primary text-sm shadow-sm text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 transition-shadow disabled:opacity-50 disabled:cursor-not-allowed"
                />
                
                <AttachmentButton
                    onFilesSelected={handleFilesSelected}
                    disabled={isUploading}
                />

                <ComposerPrimitive.Send asChild>
                    <button className="p-3 rounded-full shadow-sm transition-colors flex items-center justify-center bg-primary hover:bg-primary/90 text-white cursor-pointer disabled:bg-gray-200 disabled:dark:bg-gray-700 disabled:text-gray-400 disabled:cursor-not-allowed">
                        <Send size={20} />
                    </button>
                </ComposerPrimitive.Send>
            </ComposerPrimitive.Root>
        </div>
    );
}
