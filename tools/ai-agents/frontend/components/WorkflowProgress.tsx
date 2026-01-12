/**
 * WorkflowProgress - 工作流进度组件
 * 
 * 紧凑的单行设计，展示阶段进度和当前子任务
 * 支持点击已完成阶段查看历史产出物
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
    /** 当选中的阶段 ID (用于高亮显示) */
    selectedStageId?: string | null;
    /** 阶段点击回调 (只有已完成阶段可点击) */
    onStageClick?: (stageId: string) => void;
}

export function WorkflowProgress({
    stages,
    currentStageIndex,
    currentTask,
    selectedStageId,
    onStageClick
}: WorkflowProgressProps) {
    if (!stages || stages.length === 0) {
        return null;
    }

    const handleStageClick = (stage: Stage) => {
        // 只有已完成阶段可以点击
        if (stage.status === 'completed' && onStageClick) {
            onStageClick(stage.id);
        }
    };

    return (
        <div className="flex items-center gap-2 px-4 py-2 bg-gray-50 dark:bg-gray-800/50 border-b border-gray-200 dark:border-gray-700 text-sm overflow-x-auto">
            {/* 阶段指示器 */}
            <div className="flex items-center gap-1 shrink-0">
                {stages.map((stage, index) => {
                    const isClickable = stage.status === 'completed';
                    const isSelected = selectedStageId === stage.id;

                    return (
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
                                className={`flex items-center gap-1 ${isClickable
                                        ? 'cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 rounded px-1 -mx-1 transition-colors'
                                        : ''
                                    } ${isSelected
                                        ? 'bg-green-100 dark:bg-green-900/30 rounded px-1 -mx-1'
                                        : ''
                                    }`}
                                data-status={stage.status}
                                onClick={() => handleStageClick(stage)}
                                role={isClickable ? 'button' : undefined}
                                tabIndex={isClickable ? 0 : undefined}
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
                                        } ${isSelected ? 'font-semibold' : ''}`}
                                >
                                    {stage.name}
                                </span>
                            </div>
                        </React.Fragment>
                    );
                })}
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
