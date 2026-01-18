import React from 'react';
import { useAssistantRuntime } from '@assistant-ui/react';

export function RuntimeErrorDisplay() {
    const runtime = useAssistantRuntime();
    // 使用扩展类型来访问 error 和 reload
    const thread = runtime.thread as unknown as { error?: Error | null; reload?: () => void };
    const error = thread.error;
    
    if (!error) return null;
    
    return (
        <div className="absolute top-16 left-0 w-full bg-red-50 dark:bg-red-900/20 border-b border-red-200 dark:border-red-800 p-2 text-center text-sm text-red-600 dark:text-red-400 flex items-center justify-center gap-2 z-10 transition-all animate-in slide-in-from-top-2">
            <span>出错了: {error.message || "未知错误"}</span>
            <button 
                onClick={() => thread.reload?.()} 
                className="px-3 py-0.5 bg-white dark:bg-red-950 rounded border border-red-200 dark:border-red-800 hover:bg-red-50 dark:hover:bg-red-900 transition-colors shadow-sm font-medium"
            >
                重试
            </button>
        </div>
    );
}
