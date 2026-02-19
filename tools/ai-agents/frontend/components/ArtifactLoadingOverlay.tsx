/**
 * ArtifactLoadingOverlay - 产出物更新覆盖层组件
 *
 * 在产出物更新（已有旧内容）时，在旧内容上方显示半透明遮罩 + 进度动画。
 * 用户仍可透过遮罩查看旧内容，减少等待焦虑。
 */

import React, { useState, useEffect, useRef } from 'react';
import { Loader2 } from 'lucide-react';

interface ArtifactLoadingOverlayProps {
    /** 是否正在加载 */
    isLoading: boolean;
    /** 产出物名称 */
    artifactName?: string;
}

/** 模拟进度：缓慢增长到 90%，完成时跳到 100% */
function useSimulatedProgress(isLoading: boolean): number {
    const [progress, setProgress] = useState(0);
    const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

    useEffect(() => {
        if (isLoading) {
            setProgress(0);
            let current = 0;
            intervalRef.current = setInterval(() => {
                // 越接近 90% 增长越慢
                const remaining = 90 - current;
                const increment = Math.max(0.3, remaining * 0.04);
                current = Math.min(90, current + increment);
                setProgress(current);
            }, 300);
        } else {
            // 结束时跳到 100%
            if (intervalRef.current) {
                clearInterval(intervalRef.current);
                intervalRef.current = null;
            }
            setProgress(100);
        }

        return () => {
            if (intervalRef.current) {
                clearInterval(intervalRef.current);
                intervalRef.current = null;
            }
        };
    }, [isLoading]);

    return progress;
}

export function ArtifactLoadingOverlay({
    isLoading,
    artifactName = '产出物',
}: ArtifactLoadingOverlayProps) {
    const progress = useSimulatedProgress(isLoading);

    if (!isLoading && progress >= 100) {
        return null;
    }

    return (
        <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-black/40 backdrop-blur-[3px] transition-opacity duration-300">
            <Loader2 size={40} className="text-indigo-400 animate-spin mb-4" />
            <p className="text-sm font-medium text-gray-200 mb-1">
                正在更新{artifactName}...
            </p>
            <p className="text-xs text-gray-400 mb-4">
                AI 正在根据最新对话内容更新文档
            </p>
            {/* 进度条 */}
            <div className="w-48 h-1 bg-gray-700 rounded-full overflow-hidden">
                <div
                    className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full transition-all duration-500 ease-out"
                    style={{ width: `${progress}%` }}
                />
            </div>
        </div>
    );
}

export default ArtifactLoadingOverlay;
