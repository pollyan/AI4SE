/**
 * ArtifactPanel - 产出物展示组件
 * 
 * 展示当前/选中阶段的产出物内容，支持实时流式渲染。
 */

import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { CodeOverride as CodeBlock } from './chat/MarkdownText';
import { FileText, Clock, CheckCircle, ChevronLeft, ChevronRight, List, Loader2 } from 'lucide-react';

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

export interface SubNavItem {
    id: string;
    title: string;
    status: 'pending' | 'completed' | 'warning' | 'active';
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
    /** 二级导航项 (可选) */
    subNavItems?: SubNavItem[];
    /** 二级导航点击回调 */
    onSubNavClick?: (id: string) => void;
}

// 简单的 slugify 函数，支持中文
const slugify = (text: string) => {
    return text
        .toString()
        .toLowerCase()
        .trim()
        .replace(/\s+/g, '-')
        .replace(/[^\w\u4e00-\u9fa5\-.+]/g, '');
};

// 自定义标题组件，自动生成 ID
const HeadingRenderer = ({ level, children, ...props }: any) => {
    // 获取纯文本内容
    const getText = (node: any): string => {
        if (typeof node === 'string') return node;
        if (Array.isArray(node)) return node.map(getText).join('');
        if (node?.props?.children) return getText(node.props.children);
        return '';
    };

    const text = getText(children);
    const id = slugify(text);
    return React.createElement(`h${level}`, { id, ...props }, children);
};

export function ArtifactPanel({
    artifactProgress,
    selectedStageId,
    currentStageId,
    artifacts,
    streamingArtifactKey,
    streamingArtifactContent,
    onBackToCurrentStage,
    subNavItems,
    onSubNavClick
}: ArtifactPanelProps) {
    // ... existing logic ...
    const displayStageId = selectedStageId || currentStageId;
    const template = artifactProgress?.template.find(t => t.stageId === displayStageId);
    const templateName = template?.name || '产出物';
    const templateKey = template?.artifactKey;
    const effectiveKey = templateKey || streamingArtifactKey;
    const isGenerating = streamingArtifactKey !== null && (templateKey === streamingArtifactKey || !templateKey);
    const content = effectiveKey && artifacts[effectiveKey]
        ? artifacts[effectiveKey]
        : null;
    const isViewingHistory = selectedStageId !== null && selectedStageId !== currentStageId;

    // 处理自动滚动
    React.useEffect(() => {
        const activeItem = subNavItems?.find(item => item.status === 'active');
        if (activeItem) {
            const element = document.getElementById(activeItem.id);
            if (element) {
                element.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        }
    }, [subNavItems]);

    // TOC 侧边栏折叠状态
    const [isTocCollapsed, setIsTocCollapsed] = React.useState(false);

    return (
        <div className="flex flex-col h-full">
            {/* 头部 - 保持不变 */}
            <div className="flex items-center justify-between px-4 py-3 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 shrink-0">
                <div className="flex items-center gap-2">
                    <FileText className="text-primary" size={18} />
                    <span className="font-medium text-gray-800 dark:text-gray-200">
                        {templateName}
                    </span>

                    {/* 状态标签 */}
                    {isGenerating ? (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300 rounded-full">
                            <Loader2 size={12} className="animate-spin" />
                            生成中...
                        </span>
                    ) : content ? (
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

            {/* 内容区域容器 - 支持侧边栏布局 */}
            <div className="flex-1 flex overflow-hidden">
                {/* 二级导航侧边栏 - 可折叠 */}
                {subNavItems && subNavItems.length > 0 && (
                    <div className={`border-r border-gray-200 dark:border-gray-700 bg-gray-50/50 dark:bg-gray-800/30 shrink-0 transition-all duration-200 flex flex-col ${isTocCollapsed ? 'w-8' : 'w-32'}`}>
                        {/* 折叠/展开按钮 */}
                        <button
                            onClick={() => setIsTocCollapsed(!isTocCollapsed)}
                            className="flex items-center justify-center py-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors border-b border-gray-200 dark:border-gray-700"
                            title={isTocCollapsed ? '展开目录' : '收起目录'}
                        >
                            {isTocCollapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
                        </button>

                        {/* 目录内容 */}
                        {!isTocCollapsed ? (
                            <div className="flex-1 overflow-y-auto p-1.5 space-y-0.5">
                                {subNavItems.map(item => (
                                    <button
                                        key={item.id}
                                        onClick={() => onSubNavClick?.(item.id)}
                                        className={`w-full text-left px-2 py-1.5 rounded text-[11px] leading-tight transition-colors flex items-center justify-between ${item.status === 'active'
                                            ? 'bg-white dark:bg-gray-700 text-primary font-medium shadow-sm'
                                            : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
                                            }`}
                                    >
                                        <span className="truncate">{item.title}</span>
                                        {item.status === 'warning' && (
                                            <span className="w-1.5 h-1.5 rounded-full bg-orange-500 shrink-0 ml-1" />
                                        )}
                                    </button>
                                ))}
                            </div>
                        ) : (
                            <div className="flex-1 flex items-center justify-center">
                                <List size={14} className="text-gray-400" />
                            </div>
                        )}
                    </div>
                )}

                {/* 主内容 */}
                <div className="flex-1 overflow-y-auto p-4 bg-white dark:bg-gray-900 scroll-smooth">
                    {content ? (
                        <div className="prose prose-sm dark:prose-invert max-w-none break-words">
                            <ReactMarkdown
                                remarkPlugins={[remarkGfm]}
                                components={{
                                    code: CodeBlock,
                                    pre: React.Fragment,
                                    h1: (props) => <HeadingRenderer level={1} {...props} />,
                                    h2: (props) => <HeadingRenderer level={2} {...props} />,
                                    h3: (props) => <HeadingRenderer level={3} {...props} />,
                                    h4: (props) => <HeadingRenderer level={4} {...props} />,
                                }}
                            >
                                {content}
                            </ReactMarkdown>
                        </div>
                    ) : (
                        <div className="flex flex-col items-center justify-center h-full text-gray-400">
                            <Clock size={48} className="mb-4 opacity-50" />
                            <p>完成当前阶段对话后，将在此生成产出物</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

export default ArtifactPanel;
