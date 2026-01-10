/**
 * WorkflowProgress - 工作流进度组件
 * 
 * 紧凑的单行设计，展示阶段进度和当前子任务
 */

import React from 'react';
import { Check, Circle, Loader2 } from 'lucide-react';

export interface Stage {
    id: string;
    name: string;
    status: 'pending' | 'active' | 'completed';
}

export interface WorkflowProgressProps {
    stages: Stage[];
    currentStageIndex: number;
    currentTask: string | null;
}

export function WorkflowProgress({ stages, currentStageIndex, currentTask }: WorkflowProgressProps) {
    if (!stages || stages.length === 0) {
        return null;
    }

    return (
        <div className="flex items-center gap-2 px-4 py-2 bg-gray-50 dark:bg-gray-800/50 border-b border-gray-200 dark:border-gray-700 text-sm overflow-x-auto">
            {/* 阶段指示器 */}
            <div className="flex items-center gap-1 shrink-0">
                {stages.map((stage, index) => (
                    <React.Fragment key={stage.id}>
                        {/* 连接线（非首个） */}
                        {index > 0 && (
                            <div
                                className={`w-4 h-0.5 ${stage.status === 'completed' || stages[index - 1].status === 'completed'
                                        ? 'bg-green-500'
                                        : 'bg-gray-300 dark:bg-gray-600'
                                    }`}
                            />
                        )}

                        {/* 阶段项 */}
                        <div
                            className="flex items-center gap-1"
                            data-status={stage.status}
                        >
                            {/* 状态图标 */}
                            {stage.status === 'completed' && (
                                <Check
                                    size={14}
                                    className="text-green-500 shrink-0"
                                    data-testid={`status-completed-${stage.id}`}
                                />
                            )}
                            {stage.status === 'active' && (
                                <Loader2
                                    size={14}
                                    className="text-primary animate-spin shrink-0"
                                    data-testid={`status-active-${stage.id}`}
                                />
                            )}
                            {stage.status === 'pending' && (
                                <Circle
                                    size={14}
                                    className="text-gray-400 shrink-0"
                                    data-testid={`status-pending-${stage.id}`}
                                />
                            )}

                            {/* 阶段名称 */}
                            <span
                                className={`whitespace-nowrap ${stage.status === 'active'
                                        ? 'text-primary font-medium'
                                        : stage.status === 'completed'
                                            ? 'text-green-600 dark:text-green-400'
                                            : 'text-gray-400'
                                    }`}
                            >
                                {stage.name}
                            </span>
                        </div>
                    </React.Fragment>
                ))}
            </div>

            {/* 分隔符 + 子任务 */}
            {currentTask && (
                <>
                    <div className="w-px h-4 bg-gray-300 dark:bg-gray-600 shrink-0" />
                    <span className="text-gray-500 dark:text-gray-400 truncate">
                        {currentTask}
                    </span>
                </>
            )}
        </div>
    );
}

export default WorkflowProgress;
