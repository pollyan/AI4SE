import React from 'react';
import { Check, X } from 'lucide-react';

interface ToolInvocationProps {
    toolInvocation: {
        toolCallId: string;
        toolName: string;
        args: any;
        state: 'call' | 'input-available' | 'output-available';
        output?: any;
    };
    addToolResult: (options: { toolCallId: string; toolName: string; result: any }) => void;
}

const AskConfirmation = ({ toolInvocation, addToolResult }: ToolInvocationProps) => {
    const { toolCallId, args, state } = toolInvocation;
    const isCompleted = state === 'output-available';

    const handleConfirm = () => {
        addToolResult({ toolCallId, toolName: 'ask_confirmation', result: 'Yes' });
    };

    const handleReject = () => {
        addToolResult({ toolCallId, toolName: 'ask_confirmation', result: 'No' });
    };

    return (
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4 my-2 shadow-sm max-w-md">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 flex items-center gap-2">
                需要确认
            </h3>
            <p className="text-gray-600 dark:text-gray-300 mt-2 mb-4">
                {args?.message || '请确认是否继续执行操作？'}
            </p>

            {!isCompleted ? (
                <div className="flex gap-3">
                    <button
                        onClick={handleConfirm}
                        className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-primary hover:bg-primary/90 text-white rounded-md text-sm font-medium transition-colors"
                        title="Confirm"
                        aria-label="Confirm"
                    >
                        <Check size={16} />
                        确认
                    </button>
                    <button
                        onClick={handleReject}
                        className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-200 rounded-md text-sm font-medium transition-colors"
                        title="Cancel"
                        aria-label="Cancel"
                    >
                        <X size={16} />
                        取消
                    </button>
                </div>
            ) : (
                <div className="text-sm text-gray-500 italic">
                    {toolInvocation.output === 'Yes' ? '已确认' : '已取消'}
                </div>
            )}
        </div>
    );
};

const UpdateArtifact = ({ toolInvocation }: ToolInvocationProps) => {
    const { state } = toolInvocation;

    // Only verify success state during streaming? 
    // Usually backend sends result.
    // Frontend just shows status.

    if (state === 'output-available') {
        return (
            <div className="text-xs text-green-600 dark:text-green-400 mt-1 flex items-center gap-1">
                ✅ 已更新右侧产出物面板
            </div>
        );
    }
    return (
        <div className="text-xs text-gray-500 mt-1 flex items-center gap-1 animate-pulse">
            ↻ 正在更新产出物...
        </div>
    );
};

export const ToolInvocation = ({ toolInvocation, addToolResult }: ToolInvocationProps) => {
    const { toolName } = toolInvocation;

    switch (toolName) {
        case 'ask_confirmation':
            return <AskConfirmation toolInvocation={toolInvocation} addToolResult={addToolResult} />;
        case 'UpdateArtifact':
            return <UpdateArtifact toolInvocation={toolInvocation} addToolResult={addToolResult} />;
        default:
            return (
                <div className="text-xs text-gray-400 italic mt-1">
                    调用工具: {toolName}
                </div>
            );
    }
};
