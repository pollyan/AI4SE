import React, { useEffect, useRef, useState } from 'react';
import mermaid from 'mermaid';
import { useStore } from '../store';
import { sanitizeMermaidCode, aggressiveSanitize } from '../core/utils/mermaidSanitizer';

mermaid.initialize({
  startOnLoad: false,
  theme: 'dark',
  securityLevel: 'loose',
  fontFamily: 'JetBrains Mono, monospace',
  // @ts-ignore - suppressErrorRendering exists but might not be in types
  suppressErrorRendering: true,
});

const simpleHash = (str: string) => {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = ((hash << 5) - hash) + str.charCodeAt(i);
    hash |= 0;
  }
  return hash.toString();
};

export interface MermaidProps {
  chart: string;
  blockIndex?: number;
  onRetry?: (brokenCode: string, errorMessage: string, blockIndex: number) => Promise<boolean>;
}

export const Mermaid: React.FC<MermaidProps> = ({ chart, blockIndex, onRetry }) => {
  const ref = useRef<HTMLDivElement>(null);
  const [renderState, setRenderState] = useState<'success' | 'loading' | 'error'>('loading');
  const [svgHtml, setSvgHtml] = useState<string>('');
  const [errorInfo, setErrorInfo] = useState<{ code: string; message: string }>({ code: '', message: '' });
  const retriedCodes = useRef<Set<string>>(new Set());
  const isGenerating = useStore((state) => state.isGenerating);

  useEffect(() => {
    let isMounted = true;
    if (!chart) return;

    const renderChart = async () => {
      if (isMounted) setRenderState('loading');

      try {
        const id = `mermaid-${Math.random().toString(36).substr(2, 9)}`;

        // --- 容错渲染策略 ---
        // 第一级：原始代码基本清洗
        const sanitized = sanitizeMermaidCode(chart);
        const originalParseResult = await mermaid.parse(sanitized, { suppressErrors: true });

        if (originalParseResult) {
          const { svg: generatedSvg } = await mermaid.render(id, sanitized);
          if (isMounted) {
            setSvgHtml(generatedSvg);
            setRenderState('success');
          }
          return;
        }

        // 第二级：激进清洗（LLM 严重幻觉时）
        const aggressive = aggressiveSanitize(sanitized);
        const aggressiveParseResult = await mermaid.parse(aggressive, { suppressErrors: true });

        if (aggressiveParseResult) {
          const { svg: generatedSvg } = await mermaid.render(id, aggressive);
          if (isMounted) {
            setSvgHtml(generatedSvg);
            setRenderState('success');
          }
          return;
        }

        // 全部尝试失败，抛出错误走降级
        throw new Error('Mermaid syntax validation failed after all sanitization attempts.');

      } catch (error: any) {
        if (!isMounted) return;

        // During streaming, the chart might be incomplete, causing a parsing error.
        // We catch it silently and show a loading state if still generating.
        if (isGenerating) {
          setRenderState('loading');
        } else {
          const errorMessage = error instanceof Error ? error.message : String(error);
          const codeHash = simpleHash(chart);

          if (!retriedCodes.current.has(codeHash) && onRetry) {
            retriedCodes.current.add(codeHash);
            setRenderState('loading');
            const ok = await onRetry(chart, errorMessage, blockIndex ?? 0);
            if (isMounted && !ok) {
              setErrorInfo({ code: chart, message: errorMessage });
              setRenderState('error');
            }
            // if ok === true, the parent updates the `chart` prop, triggering this useEffect again
          } else {
            setErrorInfo({ code: chart, message: errorMessage });
            setRenderState('error');
          }
        }
      }
    };

    renderChart();

    return () => {
      isMounted = false;
    };
  }, [chart, isGenerating, onRetry, blockIndex]);

  const handleManualRetry = async () => {
    if (!onRetry) return;
    setRenderState('loading');
    const ok = await onRetry(errorInfo.code, errorInfo.message, blockIndex ?? 0);
    if (!ok) {
      setRenderState('error');
    }
  };

  if (renderState === 'loading') {
    return (
      <div className="flex justify-center my-6 w-full overflow-x-auto">
        <div className="text-blue-400 p-4 border border-blue-500/30 rounded bg-blue-500/10 text-sm flex items-center gap-3">
          <span className="w-4 h-4 border-2 border-blue-400 border-t-transparent rounded-full animate-spin"></span>
          正在绘制流程图...
        </div>
      </div>
    );
  }

  if (renderState === 'error') {
    const encodedChart = btoa(unescape(encodeURIComponent(errorInfo.code)));
    const liveEditorUrl = `https://mermaid.live/edit#pako:${encodedChart}`;

    return (
      <div className="flex justify-center my-6 w-full overflow-x-auto">
        <div className="w-full bg-[#0f172a] rounded-lg border border-[#1e293b] overflow-hidden my-4">
          <div className="flex justify-between items-center bg-red-500/10 border-b border-red-500/20 px-4 py-3">
            <div className="text-red-400 text-sm font-medium flex items-center gap-2">
              <svg className="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
              <div>
                <div>图表语法受损，已启动格式降级</div>
                {errorInfo.message && <div className="text-xs text-red-400/70 mt-0.5 truncate max-w-[400px]" title={errorInfo.message}>{errorInfo.message}</div>}
              </div>
            </div>
            <div className="flex gap-2">
              {onRetry && (
                <button onClick={handleManualRetry} className="text-xs bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-400 px-3 py-1.5 rounded transition-colors flex items-center gap-1 border border-emerald-500/30">
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>
                  重新生成图表
                </button>
              )}
              <a href={liveEditorUrl} target="_blank" rel="noopener noreferrer" className="text-xs bg-blue-500/20 hover:bg-blue-500/30 text-blue-400 px-3 py-1.5 rounded transition-colors flex items-center gap-1 border border-blue-500/30">
                在 Live Editor 修复
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path></svg>
              </a>
            </div>
          </div>
          <details className="text-slate-400 text-sm group">
            <summary className="cursor-pointer font-mono px-4 py-3 hover:bg-white/5 transition-colors select-none flex items-center gap-2">
              <span className="opacity-50 group-open:rotate-90 transition-transform">▶</span>
              查看原始代码
            </summary>
            <pre className="p-4 bg-black/20 border-t border-[#1e293b] overflow-x-auto text-xs font-mono leading-relaxed">{errorInfo.code}</pre>
          </details>
        </div>
      </div>
    );
  }

  return <div ref={ref} dangerouslySetInnerHTML={{ __html: svgHtml }} className="flex justify-center my-6 w-full overflow-x-auto" />;
};
