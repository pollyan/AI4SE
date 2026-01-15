import React from 'react';
import { Check, Circle, Loader2, ChevronRight } from 'lucide-react';

export interface Stage {
    id: string;
    name: string;
    status: 'pending' | 'active' | 'completed';
    subTasks?: {
        id: string;
        name: string;
        status: 'pending' | 'active' | 'completed' | 'warning';
    }[];
}

export interface WorkflowProgressProps {
    stages: Stage[];
    /** 当前活动的主阶段索引 */
    currentStageIndex: number;
    /** 当选中的阶段 ID (用于高亮显示) */
    selectedStageId?: string | null;
    /** 阶段点击回调 (只有已完成阶段可点击) */
    onStageClick?: (stageId: string) => void;
}

export function WorkflowProgress({
    stages,
    currentStageIndex,
    selectedStageId,
    onStageClick
}: WorkflowProgressProps) {
    if (!stages || stages.length === 0) {
        return null;
    }

    const currentStage = stages[currentStageIndex];
    // 如果选中了其他阶段，优先显示选中阶段的子任务（如果有），否则显示当前活动阶段的子任务
    const displaySubTasksStage = selectedStageId
        ? stages.find(s => s.id === selectedStageId)
        : currentStage;

    const subTasks = displaySubTasksStage?.subTasks || [];

    const handleStageClick = (stage: Stage) => {
        // 只有已完成或正在进行的阶段可以点击（查看详情）
        if ((stage.status === 'completed' || stage.status === 'active') && onStageClick) {
            onStageClick(stage.id);
        }
    };

    return (
        <div className="flex flex-col border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
            {/* 一级进度条 (Main Stages) */}
            <div className="flex items-center gap-2 px-4 py-2 border-b border-gray-200/50 dark:border-gray-700/50 overflow-x-auto text-sm">
                <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider shrink-0 mr-2">阶段</span>
                {stages.map((stage, index) => {
                    const isClickable = stage.status === 'completed' || stage.status === 'active';
                    const isSelected = selectedStageId === stage.id || (!selectedStageId && index === currentStageIndex);

                    return (
                        <React.Fragment key={stage.id}>
                            {index > 0 && (
                                <ChevronRight size={14} className="text-gray-300 dark:text-gray-600 shrink-0" />
                            )}

                            <div
                                className={`flex items-center gap-1.5 px-2 py-1 rounded transition-colors whitespace-nowrap ${isClickable ? 'cursor-pointer hover:bg-gray-200 dark:hover:bg-gray-700' : 'opacity-60 cursor-default'
                                    } ${isSelected ? 'bg-white dark:bg-gray-700 shadow-sm font-medium text-primary' : ''}`}
                                onClick={() => handleStageClick(stage)}
                            >
                                {stage.status === 'completed' && <Check size={14} className="text-green-500" />}
                                {stage.status === 'active' && <Loader2 size={14} className="text-primary animate-spin" />}
                                <span className={stage.status === 'completed' ? 'text-gray-700 dark:text-gray-300' : ''}>
                                    {stage.name}
                                </span>
                            </div>
                        </React.Fragment>
                    );
                })}
            </div>

            {/* 二级进度条 (Sub Tasks) */}
            {subTasks.length > 0 && (
                <div className="flex items-center gap-3 px-4 py-1.5 overflow-x-auto text-xs bg-white dark:bg-gray-900/30">
                    <span className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider shrink-0 mr-1">任务</span>
                    {subTasks.map((task, index) => (
                        <React.Fragment key={task.id}>
                            {index > 0 && <div className="w-px h-3 bg-gray-300 dark:bg-gray-700 shrink-0" />}

                            <div className="flex items-center gap-1.5 whitespace-nowrap py-0.5">
                                {task.status === 'completed' && <Check size={12} className="text-green-500" />}
                                {task.status === 'active' && <Loader2 size={12} className="text-primary animate-spin" />}
                                {task.status === 'warning' && <Circle size={8} className="text-orange-500 fill-orange-500" />}
                                {task.status === 'pending' && <Circle size={8} className="text-gray-300 dark:text-gray-600" />}

                                <span className={`
                                    ${task.status === 'active' ? 'text-primary font-medium' : ''}
                                    ${task.status === 'completed' ? 'text-gray-500' : ''}
                                    ${task.status === 'warning' ? 'text-orange-600 dark:text-orange-400 font-medium' : ''}
                                    ${task.status === 'pending' ? 'text-gray-400' : ''}
                                `}>
                                    {task.name}
                                </span>
                            </div>
                        </React.Fragment>
                    ))}
                </div>
            )}
        </div>
    );
}

export default WorkflowProgress;
