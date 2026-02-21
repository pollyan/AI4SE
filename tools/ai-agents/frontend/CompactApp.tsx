/**
 * CompactApp - 紧凑型智能体操作页面 (真实后端对接版)
 * 包含：附件上传、Markdown/Mermaid、动态TOC、流式渲染
 */
import React, { useState, useRef, useCallback, useEffect, useMemo } from 'react';
import CompactLayout from './components/CompactLayout';
import { Bot, MessageSquare, FileText } from 'lucide-react';
import { ASSISTANTS } from './constants';
import { AssistantId } from './types';
import { default as ArtifactPanel, SubNavItem } from './components/ArtifactPanel';
import { parseTocFromMarkdown, getActiveArtifactContent } from './src/utils/tocUtils';
import WorkflowProgress, { Stage } from './components/WorkflowProgress';
import { AssistantChat } from './components/chat';
import type { ProgressInfo } from './services/backendService';



// 将后端 ProgressInfo.stages 转换为 WorkflowProgress 组件期望的 Stage 格式
function convertToStages(progress: ProgressInfo | null): Stage[] {
    if (!progress || !progress.stages) return [];

    return progress.stages.map((stage, index) => {
        // 如果当前阶段是 active，且有 currentTask，将其作为唯一子任务
        const subTasks: Stage['subTasks'] = [];
        if (stage.status === 'active' && progress.currentTask) {
            subTasks.push({
                id: `${stage.id}-current-task`,
                name: progress.currentTask,
                status: 'active'
            });
        }

        return {
            id: stage.id,
            name: stage.name,
            status: stage.status,
            subTasks: subTasks.length > 0 ? subTasks : undefined
        };
    });
}

const CompactApp: React.FC = () => {
    const [selectedAssistantId, setSelectedAssistantId] = useState<AssistantId | null>(null);
    const [activeTab, setActiveTab] = useState<'chat' | 'result'>('chat');

    // 面板拖动相关
    const [leftWidth, setLeftWidth] = useState<number>(30);
    const [isDragging, setIsDragging] = useState<boolean>(false);
    const [isDesktop, setIsDesktop] = useState<boolean>(
        typeof window !== 'undefined' ? window.innerWidth >= 1024 : true
    );
    const containerRef = useRef<HTMLDivElement>(null);

    // 真实状态管理
    const [workflowProgress, setWorkflowProgress] = useState<ProgressInfo | null>(null);
    const [artifacts, setArtifacts] = useState<Record<string, string>>({});
    const [structuredArtifacts, setStructuredArtifacts] = useState<Record<string, any>>({});
    const [streamingArtifactKey, setStreamingArtifactKey] = useState<string | null>(null);
    const [streamingArtifactContent, setStreamingArtifactContent] = useState<string>('');
    const [selectedStageId, setSelectedStageId] = useState<string | null>(null); // Added missing state
    const [currentTocItem, setCurrentTocItem] = useState<string>(''); // Added missing state

    // 选中助手详情
    const selectedAssistant = useMemo(() =>
        ASSISTANTS.find(a => a.id === selectedAssistantId),
        [selectedAssistantId]
    );

    // 转换 stages
    const stages = useMemo(() => convertToStages(workflowProgress), [workflowProgress]);

    // 计算当前 stage index
    const currentStageIndex = useMemo(() => {
        if (!stages.length) return 0;
        const activeIndex = stages.findIndex(s => s.status === 'active');
        return activeIndex === -1 ? stages.length - 1 : activeIndex;
    }, [stages]);

    // 计算当前 stage ID
    const currentStageId = useMemo(() => {
        const activeStage = stages.find(s => s.status === 'active');
        return activeStage?.id;
    }, [stages]);

    // 计算 artifactProgress
    const artifactProgress = useMemo(() => {
        return workflowProgress?.artifactProgress;
    }, [workflowProgress]);

    // 计算 TOC — 与 ArtifactPanel 逻辑一致，只取当前阶段的 artifact 内容
    const tocItems = useMemo(() => {
        const content = getActiveArtifactContent({
            artifacts,
            artifactProgress: workflowProgress?.artifactProgress ?? null,
            selectedStageId,
            currentStageId,
            streamingArtifactContent,
            streamingArtifactKey,
        });
        return parseTocFromMarkdown(content);
    }, [artifacts, workflowProgress, selectedStageId, currentStageId, streamingArtifactContent, streamingArtifactKey]);


    // 监听窗口大小
    useEffect(() => {
        const handleResize = () => {
            setIsDesktop(window.innerWidth >= 1024);
        };
        window.addEventListener('resize', handleResize);
        return () => window.removeEventListener('resize', handleResize);
    }, []);

    const handleSelectAssistant = (id: AssistantId) => {
        setSelectedAssistantId(id);
        // 重置状态
        setWorkflowProgress(null);
        setArtifacts({});
        setStructuredArtifacts({});
        setStreamingArtifactKey(null);
        setStreamingArtifactContent('');
        setSelectedStageId(null);
    };

    const handleBack = () => {
        setSelectedAssistantId(null);
    };

    // 处理进度变化回调
    const handleProgressChange = useCallback((progress: ProgressInfo | null) => {
        // [DEBUG] Log progress event
        if (progress?.artifactProgress?.generating) {
            console.log('[CompactApp] Received generating event:', progress.artifactProgress.generating);
        }

        setWorkflowProgress(progress);

        // 只在 generating 有具体值时更新 streamingArtifactKey
        // 不在这里清空，清空操作由 handleStreamEnd 负责（流真正结束时）
        if (progress?.artifactProgress?.generating) {
            console.log('[CompactApp] Setting streamingArtifactKey to:', progress.artifactProgress.generating);
            setStreamingArtifactKey(progress.artifactProgress.generating);
        }

        // 合并 artifacts
        if (progress?.artifacts) {
            setArtifacts(prev => ({ ...prev, ...progress.artifacts }));
        }

        // 合并 structured_artifacts
        if (progress?.structured_artifacts) {
            setStructuredArtifacts(prev => ({ ...prev, ...progress.structured_artifacts }));
        }

        // 自动选中当前活动阶段
        if (progress?.stages) {
            const activeStage = progress.stages.find(s => s.status === 'active');
            if (activeStage && !selectedStageId) {
                setSelectedStageId(activeStage.id);
            }
        }
    }, [selectedStageId]);

    // 流结束时清空 generating 状态
    const handleStreamEnd = useCallback(() => {
        setStreamingArtifactKey(null);
    }, []);

    // 拖动逻辑
    const handleMouseDown = (e: React.MouseEvent) => {
        e.preventDefault();
        setIsDragging(true);
        document.body.style.cursor = 'col-resize';
        document.body.style.userSelect = 'none';
    };

    useEffect(() => {
        if (!isDragging) return;

        const handleMouseMove = (e: MouseEvent) => {
            if (containerRef.current) {
                const containerRect = containerRef.current.getBoundingClientRect();
                const newLeftWidth = ((e.clientX - containerRect.left) / containerRect.width) * 100;
                // 限制范围 20% - 80%
                if (newLeftWidth >= 20 && newLeftWidth <= 80) {
                    setLeftWidth(newLeftWidth);
                }
            }
        };

        const handleMouseUp = () => {
            setIsDragging(false);
            document.body.style.cursor = '';
            document.body.style.userSelect = '';
        };

        document.addEventListener('mousemove', handleMouseMove);
        document.addEventListener('mouseup', handleMouseUp);

        return () => {
            document.removeEventListener('mousemove', handleMouseMove);
            document.removeEventListener('mouseup', handleMouseUp);
        };
    }, [isDragging]);

    // 助手选择面板
    const AssistantSelectionPanel = () => {
        return (
            <div className="h-full flex flex-col items-center justify-center p-4 sm:p-6">
                <div className="max-w-4xl w-full grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
                    {ASSISTANTS.map(assistant => (
                        <button
                            key={assistant.id}
                            onClick={() => handleSelectAssistant(assistant.id)}
                            className="flex flex-col items-center p-6 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 hover:border-primary hover:shadow-md transition-all group text-center"
                        >
                            <div className={`p-4 rounded-full ${assistant.colorClass} mb-4 group-hover:scale-110 transition-transform`}>
                                <Bot size={32} />
                            </div>
                            <h3 className="text-lg font-bold text-gray-900 dark:text-gray-100 mb-2">
                                {assistant.name}
                            </h3>
                            <p className="text-sm text-gray-500 dark:text-gray-400">
                                {assistant.description}
                            </p>
                        </button>
                    ))}
                </div>
            </div>
        );
    };

    // Result Panel
    const ResultPanelWrapper = () => (
        <div className="h-full flex flex-col bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 overflow-hidden">
            {/* 顶部进度条 */}
            {stages.length > 0 && (
                <div className="shrink-0">
                    <WorkflowProgress
                        stages={stages}
                        currentStageIndex={currentStageIndex}
                        selectedStageId={selectedStageId}
                        onStageClick={setSelectedStageId}
                    />
                </div>
            )}

            {/* 内容区 */}
            <div className="flex-1 overflow-hidden">
                <ArtifactPanel
                    artifactProgress={artifactProgress}
                    selectedStageId={selectedStageId}
                    currentStageId={currentStageId}
                    artifacts={artifacts}
                    structuredArtifacts={structuredArtifacts}
                    streamingArtifactKey={streamingArtifactKey}
                    streamingArtifactContent={streamingArtifactContent || null}
                    onBackToCurrentStage={() => setSelectedStageId(null)}
                    // 动态 TOC 侧边栏
                    subNavItems={tocItems.length > 0 ? tocItems : undefined}
                    onSubNavClick={(id) => {
                        setCurrentTocItem(id);
                        const element = document.getElementById(id);
                        if (element) {
                            element.scrollIntoView({ behavior: 'smooth' });
                        }
                    }}
                />
            </div>
        </div>
    );

    return (
        <CompactLayout>
            <div ref={containerRef} className="h-full p-2 sm:p-3 lg:p-4">
                {!selectedAssistant ? (
                    <div className="h-full bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800">
                        <AssistantSelectionPanel />
                    </div>
                ) : isDesktop ? (
                    /* 桌面端：双面板 */
                    <div className="h-full flex gap-1">
                        <div style={{ width: `${leftWidth}%` }} className="h-full shrink-0">
                            {/* 真实 AssistantChat */}
                            <AssistantChat
                                assistant={selectedAssistant}
                                onBack={handleBack}
                                onProgressChange={handleProgressChange}
                                onStreamEnd={handleStreamEnd}
                            />
                        </div>

                        {/* 拖动条 */}
                        <div
                            className="w-2 cursor-col-resize flex items-center justify-center hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors rounded group"
                            onMouseDown={handleMouseDown}
                        >
                            <div className="w-0.5 h-8 bg-gray-300 dark:bg-gray-600 rounded-full group-hover:bg-primary" />
                        </div>

                        <div style={{ width: `${100 - leftWidth}%` }} className="h-full shrink-0">
                            <ResultPanelWrapper />
                        </div>
                    </div>
                ) : (
                    /* 移动端：标签页切换 */
                    <div className="h-full flex flex-col">
                        {/* 标签栏 */}
                        <div className="flex bg-gray-100 dark:bg-gray-800 rounded-lg p-1 mb-2 shrink-0">
                            <button
                                onClick={() => setActiveTab('chat')}
                                className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-md text-sm font-medium transition-colors ${activeTab === 'chat'
                                    ? 'bg-white dark:bg-gray-700 text-primary shadow-sm'
                                    : 'text-gray-500 hover:text-gray-700'
                                    }`}
                            >
                                <MessageSquare size={16} />
                                对话
                            </button>
                            <button
                                onClick={() => setActiveTab('result')}
                                className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-md text-sm font-medium transition-colors ${activeTab === 'result'
                                    ? 'bg-white dark:bg-gray-700 text-secondary shadow-sm'
                                    : 'text-gray-500 hover:text-gray-700'
                                    }`}
                            >
                                <FileText size={16} />
                                成果
                            </button>
                        </div>

                        {/* 内容区 */}
                        <div className="flex-1 overflow-hidden">
                            {activeTab === 'chat' ? (
                                <AssistantChat
                                    assistant={selectedAssistant}
                                    onBack={handleBack}
                                    onProgressChange={handleProgressChange}
                                    onStreamEnd={handleStreamEnd}
                                />
                            ) : (
                                <ResultPanelWrapper />
                            )}
                        </div>
                    </div>
                )}
            </div>
        </CompactLayout>
    );
};

export default CompactApp;
