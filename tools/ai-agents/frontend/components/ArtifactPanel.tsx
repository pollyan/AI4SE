/**
 * ArtifactPanel - 产出物展示组件
 * 
 * 展示当前/选中阶段的产出物内容，支持实时流式渲染。
 */

import React from 'react';
import { Streamdown } from 'streamdown';
import { FileText, Clock, CheckCircle, ChevronLeft } from 'lucide-react';

export interface ArtifactTemplateItem {
    stageId: string;
    artifactKey: string;
    name: string;
}

export interface ArtifactProgress {
    template: ArtifactTemplateItem[];
    completed: string[];          // 已完成的 artifact keys
    generating: string | null;    // 正在生成的 artifact key
}

interface ArtifactPanelProps {
    /** 产出物进度信息 */
    artifactProgress: ArtifactProgress | null;
    /** 当前选中查看的阶段 ID (null 表示当前活动阶段) */
    selectedStageId: string | null;
    /** 当前活动阶段 ID */
    currentStageId: string | null;
    /** 产出物内容 (key -> content) */
    artifacts: Record<string, string>;
    /** 正在流式生成的 artifact key (前端状态) */
    streamingArtifactKey: string | null;
    /** 正在生成中的产出物内容 (实时流式) */
    streamingArtifactContent: string | null;
    /** 返回当前阶段的回调 */
    onBackToCurrentStage: () => void;
}

export function ArtifactPanel({
    artifactProgress,
    selectedStageId,
    currentStageId,
    artifacts,
    streamingArtifactKey,
    streamingArtifactContent,
    onBackToCurrentStage,
}: ArtifactPanelProps) {
    // 确定要显示哪个阶段的产出物
    const displayStageId = selectedStageId || currentStageId;

    // 找到该阶段对应的模板
    const template = artifactProgress?.template.find(t => t.stageId === displayStageId);

    // 即使没有匹配的模板，也显示占位符框架
    const templateName = template?.name || '产出物';
    const templateKey = template?.artifactKey;

    // 确定产出物状态
    // 使用前端的 streamingArtifactKey 作为判断 isGenerating 的关键依据
    // isCompleted 直接检查 artifacts 字典，而不是依赖后端 state 事件的 completed 列表
    // 当 templateKey 找不到时，使用 streamingArtifactKey 作为 fallback
    const effectiveKey = templateKey || streamingArtifactKey;
    const isCompleted = effectiveKey ? !!artifacts[effectiveKey] : false;
    const isGenerating = streamingArtifactKey !== null && (templateKey === streamingArtifactKey || !templateKey);

    // 获取产出物内容
    // 优先显示流式内容（确保流式效果不被中断），其次显示已完成内容
    const content = isGenerating && streamingArtifactContent
        ? streamingArtifactContent  // 正在生成中，显示流式内容
        : isCompleted && effectiveKey
            ? artifacts[effectiveKey]  // 已完成，显示完整内容
            : null;

    // 是否正在查看历史阶段
    const isViewingHistory = selectedStageId !== null && selectedStageId !== currentStageId;

    return (
        <div className="flex flex-col h-full">
            {/* 头部 */}
            <div className="flex items-center justify-between px-4 py-3 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
                <div className="flex items-center gap-2">
                    <FileText className="text-primary" size={18} />
                    <span className="font-medium text-gray-800 dark:text-gray-200">
                        {templateName}
                    </span>

                    {/* 状态标签 */}
                    {content ? (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 rounded-full">
                            <CheckCircle size={12} />
                            已生成
                        </span>
                    ) : (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400 rounded-full">
                            <Clock size={12} />
                            待生成
                        </span>
                    )}
                </div>

                {/* 返回按钮 */}
                {isViewingHistory && (
                    <button
                        onClick={onBackToCurrentStage}
                        className="flex items-center gap-1 text-sm text-primary hover:text-primary-dark transition-colors"
                    >
                        <ChevronLeft size={16} />
                        返回当前阶段
                    </button>
                )}
            </div>

            {/* 内容区域 */}
            <div className="flex-1 overflow-y-auto p-4">
                {content ? (
                    <div className="prose prose-sm dark:prose-invert max-w-none">
                        <Streamdown>{content}</Streamdown>
                    </div>
                ) : (
                    <div className="flex flex-col items-center justify-center h-full text-gray-400">
                        <Clock size={48} className="mb-4 opacity-50" />
                        <p>完成当前阶段对话后，将在此生成产出物</p>
                    </div>
                )}
            </div>
        </div>
    );
}

export default ArtifactPanel;
