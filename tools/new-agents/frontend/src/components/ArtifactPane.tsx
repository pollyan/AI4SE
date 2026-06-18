import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import type { Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import { useStore, ArtifactVersion, WORKFLOWS } from '../store';
import { preprocessMarkdown, replaceMermaidBlockAtIndex } from '../core/utils/markdownUtils';
import { Download, Code, Eye, History, X, AlertTriangle } from 'lucide-react';
import { createMarkdownCodeRenderer } from './markdownCodeRenderer';

export const ArtifactPane: React.FC = () => {
  const workflow = useStore((state) => state.workflow);
  const stageIndex = useStore((state) => state.stageIndex);
  const artifactContent = useStore((state) => state.artifactContent);
  const artifactHistory = useStore((state) => state.artifactHistory);
  const artifactTruncated = useStore((state) => state.artifactTruncated);
  const isGenerating = useStore((state) => state.isGenerating);
  const [viewMode, setViewMode] = useState<'preview' | 'code'>('preview');
  const [showHistory, setShowHistory] = useState(false);
  const [selectedVersion, setSelectedVersion] = useState<ArtifactVersion | null>(null);
  const currentStageId = WORKFLOWS[workflow].stages[stageIndex]?.id;
  const currentStageArtifactHistory = useMemo(
    () => currentStageId
      ? artifactHistory.filter(version => version.stageId === currentStageId)
      : [],
    [artifactHistory, currentStageId]
  );

  const handleDownload = () => {
    const blob = new Blob([artifactContent], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${workflow.toLowerCase()}_artifact.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const openHistory = () => {
    if (currentStageArtifactHistory.length > 0) {
      setSelectedVersion(currentStageArtifactHistory[currentStageArtifactHistory.length - 1]);
    } else {
      setSelectedVersion(null);
    }
    setShowHistory(true);
  };

  useEffect(() => {
    if (!showHistory) return;
    if (
      selectedVersion
      && currentStageArtifactHistory.some(version => version.id === selectedVersion.id)
    ) {
      return;
    }
    setSelectedVersion(
      currentStageArtifactHistory.length > 0
        ? currentStageArtifactHistory[currentStageArtifactHistory.length - 1]
        : null
    );
  }, [currentStageArtifactHistory, selectedVersion, showHistory]);

  // Content displays using the imported preprocessMarkdown utility

  const displayContent = preprocessMarkdown(artifactContent);

  const handleMermaidRetry = useCallback(async (brokenCode: string, errorMessage: string, blockIndex: number) => {
    // dynamically import to avoid cyclic or immediate heavy deps
    const { retryMermaidGeneration } = await import('../services/mermaidRetryService');
    const newCode = await retryMermaidGeneration(brokenCode, errorMessage, blockIndex);
    if (!newCode) return false;

    const content = useStore.getState().artifactContent;
    const updatedContent = replaceMermaidBlockAtIndex(content, blockIndex, newCode);
    if (!updatedContent) return false;

    useStore.getState().setArtifactContent(updatedContent);
    return true;
  }, []);

  const createArtifactMarkdownComponents = (
    onMermaidRetry?: Parameters<typeof createMarkdownCodeRenderer>[0]['onMermaidRetry']
  ): Components => {
    let mermaidBlockCounter = 0;
    return {
    h1: ({ node, ...props }) => <h1 className="text-3xl font-bold text-white mb-6 pb-2 border-b border-[#1e293b]" {...props} />,
    h2: ({ node, ...props }) => <h2 className="text-2xl font-bold text-white mt-8 mb-4 before:content-['#'] before:text-blue-500 before:opacity-50 before:mr-2" {...props} />,
    h3: ({ node, ...props }) => <h3 className="text-xl font-semibold text-slate-200 mt-6 mb-3" {...props} />,
    p: ({ node, ...props }) => <p className="mb-4 leading-relaxed text-slate-400" {...props} />,
    ul: ({ node, ...props }) => <ul className="list-disc pl-6 mb-4 space-y-2 text-slate-400" {...props} />,
    ol: ({ node, ...props }) => <ol className="list-decimal pl-6 mb-4 space-y-2 text-slate-400" {...props} />,
    li: ({ node, ...props }) => <li className="leading-relaxed" {...props} />,
    strong: ({ node, ...props }) => <strong className="font-bold text-white" {...props} />,
    blockquote: ({ node, ...props }) => <blockquote className="border-l-4 border-blue-500 pl-4 py-2 my-4 bg-blue-500/5 rounded-r text-slate-400 italic" {...props} />,
    table: ({ node, ...props }) => <div className="overflow-x-auto mb-6"><table className="w-full border-collapse text-sm" {...props} /></div>,
    th: ({ node, ...props }) => <th className="bg-[#1e293b] text-slate-200 font-semibold text-left p-3 border-b border-[#334155]" {...props} />,
    td: ({ node, ...props }) => <td className="p-3 border-b border-[#1e293b] text-slate-400 group-hover:bg-white/5" {...props} />,
    tr: ({ node, ...props }) => <tr className="hover:bg-white/[0.02] transition-colors group" {...props} />,
    mark: ({ node, ...props }) => <mark className="bg-emerald-500/15 text-emerald-400 px-1.5 py-0.5 rounded font-medium shadow-[0_0_8px_rgba(16,185,129,0.1)] box-decoration-clone" {...props} />,
    code: createMarkdownCodeRenderer({
      nextMermaidBlockIndex: () => mermaidBlockCounter++,
      onMermaidRetry,
      renderBlockCode: ({ language, className, children, props }) => (
        <div className="relative my-6 rounded-lg overflow-hidden border border-[#1e293b] bg-[#0f172a]">
          {language && (
            <div className="flex items-center px-4 py-2 bg-[#1e293b] text-xs text-slate-400 font-mono border-b border-[#0f172a]">
              {language}
            </div>
          )}
          <pre className="p-4 overflow-x-auto text-sm font-mono text-slate-300">
            <code className={className} {...props}>
              {children}
            </code>
          </pre>
        </div>
      ),
      renderInlineCode: ({ children, props }) => (
        <code className="bg-white/10 text-blue-300 px-1.5 py-0.5 rounded font-mono text-sm" {...props}>
          {children}
        </code>
      ),
    }),
    };
  };

  const editableMarkdownComponents = createArtifactMarkdownComponents(handleMermaidRetry);
  const readOnlyMarkdownComponents = createArtifactMarkdownComponents();

  return (
    <section className="flex flex-col w-full lg:w-[60%] bg-[#0B0F17] text-gray-300 relative shadow-2xl overflow-hidden bg-grid-pattern h-full">
      <style>{`
        .bg-grid-pattern {
            background-image: linear-gradient(to right, #1f2937 1px, transparent 1px), linear-gradient(to bottom, #1f2937 1px, transparent 1px);
            background-size: 40px 40px;
            background-color: #0d1117;
        }
        .bg-grid-pattern::before {
            content: "";
            position: absolute;
            inset: 0;
            background: radial-gradient(circle at center, transparent 0%, #0d1117 100%);
            pointer-events: none;
        }
      `}</style>

      <div className="flex items-center justify-between px-6 py-3 border-b border-[#1e293b] bg-[#0d1117]/80 backdrop-blur sticky top-0 z-10 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="p-1 rounded bg-purple-500/10 text-purple-400">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
          </div>
          <div className="flex flex-col">
            <h2 className="text-gray-200 font-semibold text-sm tracking-tight">当前产出物.md</h2>
            <span className="text-[10px] text-slate-500">实时渲染</span>
          </div>
          <span className={`ml-2 px-2 py-0.5 rounded-full text-[10px] font-medium border flex items-center gap-1 ${
            isGenerating
              ? 'bg-sky-500/10 text-sky-300 border-sky-500/20'
              : 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20'
          }`}>
            <span className={`w-1.5 h-1.5 rounded-full animate-pulse ${
              isGenerating ? 'bg-sky-300' : 'bg-emerald-500'
            }`}></span>
            {isGenerating ? '正在构建产出物' : '实时同步'}
          </span>
        </div>
        <div className="flex items-center gap-1 bg-[#0f172a] p-1 rounded-lg border border-[#1e293b]">
          <button onClick={() => setViewMode('preview')} className={`p-1.5 rounded transition-colors ${viewMode === 'preview' ? 'bg-white/10 text-white' : 'text-slate-400 hover:text-white hover:bg-white/5'}`} title="预览">
            <Eye className="w-4 h-4" />
          </button>
          <button onClick={() => setViewMode('code')} className={`p-1.5 rounded transition-colors ${viewMode === 'code' ? 'bg-white/10 text-white' : 'text-slate-400 hover:text-white hover:bg-white/5'}`} title="代码">
            <Code className="w-4 h-4" />
          </button>
          <div className="w-px h-4 bg-[#1e293b] mx-1"></div>
          <button onClick={openHistory} className="p-1.5 rounded hover:bg-white/10 text-slate-400 hover:text-white transition-colors" title="历史版本">
            <History className="w-4 h-4" />
          </button>
          <button onClick={handleDownload} className="p-1.5 rounded hover:bg-white/10 text-slate-400 hover:text-white transition-colors" title="下载">
            <Download className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-8 md:px-16 relative z-0 custom-scrollbar">
        {/* P0-9: Truncation warning banner */}
        {artifactTruncated && (
          <div className="max-w-4xl mx-auto mb-4 flex items-center gap-3 px-4 py-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-300 text-sm">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>产出物内容可能因流式响应中断而不完整，请检查文档完整性。</span>
          </div>
        )}
        {isGenerating && (
          <div className="max-w-4xl mx-auto mb-4 overflow-hidden rounded-lg border border-sky-500/20 bg-sky-500/10 px-4 py-3 text-sky-100 shadow-[0_0_24px_rgba(14,165,233,0.08)]">
            <div className="flex items-center justify-between gap-4">
              <div className="min-w-0">
                <div className="text-sm font-medium">正在构建右侧产出物</div>
                <div className="mt-1 text-xs text-sky-200/70">模型正在整理结构、章节和图表内容</div>
              </div>
              <div
                className="flex h-8 shrink-0 items-end gap-1.5"
                data-testid="artifact-generation-animation"
                aria-hidden="true"
              >
                <span className="block h-3 w-1.5 rounded-full bg-sky-300/70 animate-pulse"></span>
                <span className="block h-5 w-1.5 rounded-full bg-cyan-200/80 animate-pulse [animation-delay:120ms]"></span>
                <span className="block h-7 w-1.5 rounded-full bg-blue-200/80 animate-pulse [animation-delay:240ms]"></span>
                <span className="block h-4 w-1.5 rounded-full bg-sky-300/70 animate-pulse [animation-delay:360ms]"></span>
              </div>
            </div>
            <div className="mt-3 h-1 overflow-hidden rounded-full bg-sky-950/80">
              <div className="h-full w-1/3 rounded-full bg-gradient-to-r from-sky-400 via-cyan-200 to-blue-300 animate-pulse"></div>
            </div>
          </div>
        )}
        <div className="max-w-4xl mx-auto pb-20">
          {viewMode === 'preview' ? (
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              rehypePlugins={[rehypeRaw]}
              components={editableMarkdownComponents}
            >
              {displayContent}
            </ReactMarkdown>
          ) : (
            <pre className="text-sm font-mono text-slate-300 whitespace-pre-wrap break-words bg-[#0f172a] p-6 rounded-xl border border-[#1e293b]">
              {displayContent}
            </pre>
          )}
        </div>
      </div>

      {showHistory && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
          <div className="flex w-full max-w-6xl h-[85vh] overflow-hidden rounded-xl bg-[#0f172a] shadow-2xl ring-1 ring-white/10">
            {/* Sidebar */}
            <div className="w-64 bg-[#0B1120] border-r border-[#1e293b] flex flex-col shrink-0">
              <div className="p-4 border-b border-[#1e293b] flex justify-between items-center">
                <h3 className="text-white font-bold flex items-center gap-2">
                  <History className="w-4 h-4 text-blue-400" />
                  历史版本
                </h3>
                <button onClick={() => setShowHistory(false)} className="text-slate-400 hover:text-white">
                  <X className="w-4 h-4" />
                </button>
              </div>
              <div className="flex-1 overflow-y-auto p-3 space-y-2 custom-scrollbar">
                {currentStageArtifactHistory.length === 0 ? (
                  <div className="text-slate-500 text-sm text-center mt-10">暂无历史版本</div>
                ) : (
                  [...currentStageArtifactHistory].reverse().map((v, i) => {
                    const titleMatch = v.content.match(/^#\s+(.+)$/m);
                    const title = titleMatch ? titleMatch[1].trim() : '未命名文档';
                    return (
                      <button
                        key={v.id}
                        onClick={() => setSelectedVersion(v)}
                        className={`w-full text-left px-3 py-2.5 rounded-lg text-sm transition-all ${selectedVersion?.id === v.id ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30 shadow-inner' : 'text-slate-300 hover:bg-white/5 border border-transparent'}`}
                      >
                        <div className="font-medium truncate" title={title}>{title}</div>
                        <div className="flex justify-between items-center mt-1.5">
                          <span className={`text-[10px] px-1.5 py-0.5 rounded font-mono ${selectedVersion?.id === v.id ? 'bg-blue-500/20 text-blue-300' : 'bg-white/10 text-slate-400'}`}>v{currentStageArtifactHistory.length - i}</span>
                          <span className="text-[10px] opacity-60 font-mono">{new Date(v.timestamp).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</span>
                        </div>
                      </button>
                    );
                  })
                )}
              </div>
            </div>

            {/* Main content */}
            <div className="flex-1 flex flex-col bg-[#0B0F17] overflow-hidden relative">
              <div className="px-6 py-3 border-b border-[#1e293b] bg-[#0d1117]/80 backdrop-blur flex items-center justify-between shadow-sm">
                <h2 className="text-gray-200 font-semibold text-sm tracking-tight flex items-center gap-2">
                  <Eye className="w-4 h-4 text-slate-400" />
                  版本预览 <span className="text-slate-500 font-normal">（只读）</span>
                </h2>
              </div>
              <div className="flex-1 overflow-y-auto p-8 md:px-16 custom-scrollbar">
                <div className="max-w-4xl mx-auto pb-20">
                  {selectedVersion ? (
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      rehypePlugins={[rehypeRaw]}
                      components={readOnlyMarkdownComponents}
                    >
                      {preprocessMarkdown(selectedVersion.content)}
                    </ReactMarkdown>
                  ) : (
                    <div className="flex items-center justify-center h-full text-slate-500">
                      请在左侧选择一个历史版本查看
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </section>
  );
};
