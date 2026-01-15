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
import WorkflowProgress, { Stage } from './components/WorkflowProgress';
import { AssistantChat } from './components/chat';
import type { ProgressInfo } from './services/backendService';

// 从 Markdown 内容中解析 TOC（标题列表）
function parseTocFromMarkdown(content: string): SubNavItem[] {
    if (!content) return [];

    // 匹配 Markdown 标题 (## 或 ###)
    const headingRegex = /^(#{1,4})\s+(.+)$/gm;
    const items: SubNavItem[] = [];
    let match;

    while ((match = headingRegex.exec(content)) !== null) {
        const level = match[1].length;
        const title = match[2].trim();
        // 生成 slug ID (与 ArtifactPanel 中的 slugify 逻辑保持一致)
        const id = title
            .toString()
            .toLowerCase()
            .trim()
            .replace(/\s+/g, '-')
            .replace(/[^\w\u4e00-\u9fa5\-.+]/g, '');

        // 只取 h2 和 h3 作为 TOC 项
        if (level >= 2 && level <= 3) {
            items.push({
                id,
                title: title,
                status: 'pending' // 默认状态，后续可根据滚动位置动态更新
            });
        }
    }

    return items;
}

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
    const [streamingArtifactKey, setStreamingArtifactKey] = useState<string | null>(null);
    const [streamingArtifactContent, setStreamingArtifactContent] = useState<string>('');

    // 进度条选中阶段
    const [selectedStageId, setSelectedStageId] = useState<string | null>(null);
    // TOC 当前选中项
    const [currentTocItem, setCurrentTocItem] = useState<string | null>(null);

    useEffect(() => {
        const handleResize = () => {
            setIsDesktop(window.innerWidth >= 1024);
        };
        window.addEventListener('resize', handleResize);
        return () => window.removeEventListener('resize', handleResize);
    }, []);

    const handleMouseDown = (e: React.MouseEvent) => {
        e.preventDefault();
        setIsDragging(true);
    };

    const handleMouseMove = useCallback(
        (e: MouseEvent) => {
            if (!isDragging || !containerRef.current) return;
            const containerRect = containerRef.current.getBoundingClientRect();
            const newLeftWidth = ((e.clientX - containerRect.left) / containerRect.width) * 100;
            if (newLeftWidth >= 20 && newLeftWidth <= 80) {
                setLeftWidth(newLeftWidth);
            }
        },
        [isDragging]
    );

    const handleMouseUp = useCallback(() => {
        setIsDragging(false);
    }, []);

    useEffect(() => {
        if (isDragging) {
            window.addEventListener('mousemove', handleMouseMove);
            window.addEventListener('mouseup', handleMouseUp);
            document.body.style.cursor = 'col-resize';
            document.body.style.userSelect = 'none';
        } else {
            window.removeEventListener('mousemove', handleMouseMove);
            window.removeEventListener('mouseup', handleMouseUp);
            document.body.style.cursor = 'default';
            document.body.style.userSelect = 'auto';
        }
        return () => {
            window.removeEventListener('mousemove', handleMouseMove);
            window.removeEventListener('mouseup', handleMouseUp);
        };
    }, [isDragging, handleMouseMove, handleMouseUp]);

    const handleSelectAssistant = (id: AssistantId) => {
        setSelectedAssistantId(id);
        // 重置状态
        setWorkflowProgress(null);
        setArtifacts({});
        setStreamingArtifactKey(null);
        setStreamingArtifactContent('');
        setSelectedStageId(null);
    };

    const handleBack = () => {
        setSelectedAssistantId(null);
    };

    // 处理进度变化回调
    const handleProgressChange = useCallback((progress: ProgressInfo | null) => {
        setWorkflowProgress(progress);
        // 合并 artifacts
        if (progress?.artifacts) {
            setArtifacts(prev => ({ ...prev, ...progress.artifacts }));
        }
        // 自动选中当前活动阶段
        if (progress?.stages) {
            const activeStage = progress.stages.find(s => s.status === 'active');
            if (activeStage && !selectedStageId) {
                setSelectedStageId(activeStage.id);
            }
        }
    }, [selectedStageId]);

    const selectedAssistant = ASSISTANTS.find((a) => a.id === selectedAssistantId);

    // 转换进度数据
    const stages = useMemo(() => convertToStages(workflowProgress), [workflowProgress]);
    const currentStageIndex = workflowProgress?.currentStageIndex ?? 0;
    const currentStageId = stages[currentStageIndex]?.id || null;

    // 获取当前显示的产出物内容
    const displayStageId = selectedStageId || currentStageId;
    const artifactProgress = workflowProgress?.artifactProgress || null;
    const template = artifactProgress?.template.find(t => t.stageId === displayStageId);
    const effectiveKey = template?.artifactKey || streamingArtifactKey;
    const currentContent = streamingArtifactKey && streamingArtifactContent
        ? streamingArtifactContent
        : effectiveKey
            ? artifacts[effectiveKey] || ''
            : '';

    // 动态生成 TOC
    const tocItems = useMemo(() => {
        const items = parseTocFromMarkdown(currentContent);
        // 如果有当前选中项，更新其状态
        return items.map(item => ({
            ...item,
            status: (item.id === currentTocItem ? 'active' : 'pending') as SubNavItem['status']
        }));
    }, [currentContent, currentTocItem]);

    // 助手选择面板
    const AssistantSelectionPanel = () => (
        <div className="h-full flex flex-col items-center justify-center p-4 sm:p-6">
            <div className="text-center mb-6">
                <Bot className="w-12 h-12 text-primary mx-auto mb-3" />
                <h2 className="text-lg font-semibold text-gray-800 dark:text-white">选择智能助手</h2>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">选择一位 AI 助手开始对话</p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full max-w-md">
                {ASSISTANTS.map((assistant) => (
                    <button
                        key={assistant.id}
                        onClick={() => handleSelectAssistant(assistant.id)}
                        className="p-4 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 hover:border-primary hover:shadow-md transition-all cursor-pointer text-left group"
                    >
                        <div className="flex items-center gap-3">
                            <div
                                className={`w-10 h-10 rounded-full flex items-center justify-center text-white font-bold ${assistant.id === 'alex' ? 'bg-primary' : 'bg-secondary'
                                    }`}
                            >
                                {assistant.initial}
                            </div>
                            <div>
                                <div className="font-medium text-gray-800 dark:text-white group-hover:text-primary transition-colors">
                                    {assistant.name}
                                </div>
                                <div className="text-xs text-gray-500 dark:text-gray-400">{assistant.role}</div>
                            </div>
                        </div>
                    </button>
                ))}
            </div>
        </div>
    );

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
                    streamingArtifactKey={streamingArtifactKey}
                    streamingArtifactContent={streamingArtifactContent || null}
                    onBackToCurrentStage={() => setSelectedStageId(null)}
                    // 动态 TOC 侧边栏
                    subNavItems={tocItems.length > 0 ? tocItems : undefined}
                    onSubNavClick={(id) => setCurrentTocItem(id)}
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
