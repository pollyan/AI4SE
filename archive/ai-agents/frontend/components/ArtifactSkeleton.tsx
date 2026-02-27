/**
 * ArtifactSkeleton - 产出物骨架屏加载组件
 *
 * 在产出物首次生成（无已有内容）时显示，模拟文档结构逐渐成形。
 * 使用 shimmer 动画减少用户等待焦虑。
 */

import React from 'react';
import { Loader2 } from 'lucide-react';

interface ArtifactSkeletonProps {
    /** 产出物名称，用于提示文案 */
    artifactName?: string;
}

export function ArtifactSkeleton({ artifactName = '产出物' }: ArtifactSkeletonProps) {
    return (
        <div className="flex flex-col h-full p-4 animate-fadeIn">
            {/* 顶部提示条 */}
            <div className="flex items-center gap-3 mb-6 px-4 py-3 bg-indigo-500/10 border border-indigo-500/20 rounded-lg">
                <Loader2 size={18} className="text-indigo-400 animate-spin flex-shrink-0" />
                <span className="text-sm text-indigo-300 font-medium">
                    AI 正在根据对话内容生成{artifactName}
                    <span className="inline-block w-6 text-left animate-dotPulse">...</span>
                </span>
            </div>

            {/* 骨架文档结构 */}
            <div className="space-y-3">
                {/* 标题行 */}
                <div className="skeleton-line h-6 w-1/2 rounded-lg" />

                {/* 第一段 */}
                <div className="skeleton-line h-4 w-[35%] rounded mt-5" />
                <div className="skeleton-line h-3.5 w-[95%] rounded" />
                <div className="skeleton-line h-3.5 w-[80%] rounded" />
                <div className="skeleton-line h-3.5 w-[60%] rounded" />

                {/* 第二段 */}
                <div className="skeleton-line h-4 w-[30%] rounded mt-5" />
                <div className="skeleton-line h-3.5 w-[90%] rounded" />
                <div className="skeleton-line h-3.5 w-[95%] rounded" />
                <div className="skeleton-line h-3.5 w-[75%] rounded" />
                <div className="skeleton-line h-3.5 w-[50%] rounded" />

                {/* 第三段 */}
                <div className="skeleton-line h-4 w-[40%] rounded mt-5" />
                <div className="skeleton-line h-3.5 w-[88%] rounded" />
                <div className="skeleton-line h-3.5 w-[70%] rounded" />
                <div className="skeleton-line h-3.5 w-[45%] rounded" />
            </div>
        </div>
    );
}

export default ArtifactSkeleton;
