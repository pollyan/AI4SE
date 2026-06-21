import React, { useEffect, useMemo, useRef, useState } from 'react';
import type { MermaidConfig } from 'mermaid';
import { sanitizeMermaidCode, aggressiveSanitize } from '../core/utils/mermaidSanitizer';

const mermaidConfig: MermaidConfig = {
  startOnLoad: false,
  theme: 'dark',
  securityLevel: 'strict',
  fontFamily: 'JetBrains Mono, monospace',
  suppressErrorRendering: true,
};

type MermaidRuntime = typeof import('mermaid')['default'];

let mermaidRuntimePromise: Promise<MermaidRuntime> | null = null;
const mermaidRenderCache = new Map<string, Promise<string>>();
const MAX_MERMAID_RENDER_CACHE_ENTRIES = 50;

async function loadMermaidRuntime(): Promise<MermaidRuntime> {
  if (!mermaidRuntimePromise) {
    mermaidRuntimePromise = import('mermaid').then(({ default: mermaid }) => {
      mermaid.initialize(mermaidConfig);
      return mermaid;
    });
  }
  return mermaidRuntimePromise;
}

async function renderMermaidSvg(chart: string): Promise<string> {
  const cached = mermaidRenderCache.get(chart);
  if (cached) return cached;

  const renderPromise = (async () => {
    const mermaid = await loadMermaidRuntime();
    const id = `mermaid-${Math.random().toString(36).substr(2, 9)}`;

    // --- 容错渲染策略 ---
    // 第一级：原始代码基本清洗
    const sanitized = sanitizeMermaidCode(chart);
    const originalParseResult = await mermaid.parse(sanitized, { suppressErrors: true });

    if (originalParseResult) {
      const { svg: generatedSvg } = await mermaid.render(id, sanitized);
      return generatedSvg;
    }

    // 第一级兜底：parse 返回 false 不一定是语法错误
    // timeline / mindmap 等懒加载图表类型在某些调用时序下 parse 会误返 false
    // 直接尝试 render，成功则正常显示，失败才走降级
    try {
      const { svg: generatedSvg } = await mermaid.render(id, sanitized);
      return generatedSvg;
    } catch {
      // render 也失败，说明真的有语法问题，继续走激进降级
    }

    // 第二级：激进清洗（LLM 严重幻觉时）
    const aggressive = aggressiveSanitize(sanitized);
    const aggressiveParseResult = await mermaid.parse(aggressive, { suppressErrors: true });

    if (aggressiveParseResult) {
      const { svg: generatedSvg } = await mermaid.render(id, aggressive);
      return generatedSvg;
    }

    // 全部尝试失败，抛出错误走降级
    throw new Error('Mermaid syntax validation failed after all sanitization attempts.');
  })();

  mermaidRenderCache.set(chart, renderPromise);
  if (mermaidRenderCache.size > MAX_MERMAID_RENDER_CACHE_ENTRIES) {
    const oldestKey = mermaidRenderCache.keys().next().value;
    if (oldestKey) mermaidRenderCache.delete(oldestKey);
  }
  return renderPromise;
}

type LightweightMindmapNode = {
  id: string;
  label: string;
  depth: number;
};

type LightweightMindmap = {
  rootLabel: string;
  nodes: LightweightMindmapNode[];
};

function getMermaidDiagramType(chart: string): string {
  return chart
    .split(/\r?\n/)
    .map(line => line.trim())
    .find(Boolean)
    ?.split(/\s+/)[0]
    ?.toLowerCase() || '';
}

function cleanMindmapLabel(source: string): string {
  let label = source.trim().replace(/^root\s*/i, '').trim();
  for (let index = 0; index < 4; index += 1) {
    const nextLabel = label.trim();
    if (
      (nextLabel.startsWith('((') && nextLabel.endsWith('))'))
      || (nextLabel.startsWith('[[') && nextLabel.endsWith(']]'))
    ) {
      label = nextLabel.slice(2, -2);
      continue;
    }
    if (
      (nextLabel.startsWith('(') && nextLabel.endsWith(')'))
      || (nextLabel.startsWith('[') && nextLabel.endsWith(']'))
      || (nextLabel.startsWith('{') && nextLabel.endsWith('}'))
    ) {
      label = nextLabel.slice(1, -1);
      continue;
    }
    label = nextLabel;
    break;
  }
  return label.trim().replace(/^["'“”]+|["'“”]+$/g, '').trim();
}

function parseLightweightMindmap(chart: string): LightweightMindmap | null {
  if (getMermaidDiagramType(chart) !== 'mindmap') return null;

  const bodyLines = chart
    .replace(/\r\n/g, '\n')
    .split('\n')
    .slice(1)
    .filter(line => line.trim() && !/^\s*(class|style|:::)/.test(line.trim()));

  const nodes = bodyLines
    .map((line, index): LightweightMindmapNode | null => {
      const label = cleanMindmapLabel(line);
      if (!label) return null;
      const indent = line.match(/^ */)?.[0].length ?? 0;
      return {
        id: `mindmap-node-${index}`,
        label,
        depth: Math.min(Math.floor(indent / 2), 5),
      };
    })
    .filter((node): node is LightweightMindmapNode => node !== null);

  if (nodes.length === 0) return null;
  const [rootNode, ...childNodes] = nodes;
  return {
    rootLabel: rootNode.label,
    nodes: childNodes,
  };
}

const LightweightMindmapView: React.FC<{ mindmap: LightweightMindmap }> = ({ mindmap }) => (
  <div className="my-6 w-full overflow-x-auto" data-testid="lightweight-mindmap">
    <div className="mx-auto w-full max-w-3xl rounded-xl border border-sky-500/25 bg-slate-950/70 p-5 shadow-lg shadow-sky-950/20">
      <div className="mb-4 inline-flex rounded-lg border border-sky-400/30 bg-sky-500/10 px-4 py-2 text-sm font-semibold text-sky-100">
        {mindmap.rootLabel}
      </div>
      <div className="space-y-2">
        {mindmap.nodes.map((node) => (
          <div
            key={node.id}
            className="flex items-center gap-3"
            style={{ paddingLeft: `${Math.max(node.depth - 1, 0) * 24}px` }}
          >
            <span className="h-px w-5 shrink-0 bg-sky-500/40" aria-hidden="true" />
            <span className="rounded-md border border-slate-700/80 bg-slate-900/90 px-3 py-2 text-sm text-slate-200">
              {node.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  </div>
);

export interface MermaidProps {
  chart: string;
  blockIndex?: number;
  onRetry?: (brokenCode: string, errorMessage: string, blockIndex: number) => Promise<boolean>;
  onRenderError?: (details: { code: string; message: string; blockIndex: number }) => void;
  onRenderSuccess?: (blockIndex: number) => void;
}

export const Mermaid: React.FC<MermaidProps> = ({
  chart,
  blockIndex,
  onRetry,
  onRenderError,
  onRenderSuccess,
}) => {
  const ref = useRef<HTMLDivElement>(null);
  const [renderState, setRenderState] = useState<'success' | 'loading' | 'error'>('loading');
  const [svgHtml, setSvgHtml] = useState<string>('');
  const [errorInfo, setErrorInfo] = useState<{ code: string; message: string }>({ code: '', message: '' });
  const lightweightMindmap = useMemo(() => parseLightweightMindmap(chart), [chart]);

  useEffect(() => {
    let isMounted = true;
    if (!chart) return;

    if (lightweightMindmap) {
      setSvgHtml('');
      setRenderState('success');
      onRenderSuccess?.(blockIndex ?? 0);
      return () => {
        isMounted = false;
      };
    }

    const renderChart = async () => {
      if (isMounted) setRenderState('loading');

      try {
        const generatedSvg = await renderMermaidSvg(chart);
        if (isMounted) {
          setSvgHtml(generatedSvg);
          setRenderState('success');
          onRenderSuccess?.(blockIndex ?? 0);
        }

      } catch (error) {
        if (!isMounted) return;

        const errorMessage = error instanceof Error ? error.message : String(error);
        setErrorInfo({ code: chart, message: errorMessage });
        setRenderState('error');
        onRenderError?.({
          code: chart,
          message: errorMessage,
          blockIndex: blockIndex ?? 0,
        });
      }
    };

    renderChart();

    return () => {
      isMounted = false;
    };
  }, [chart, lightweightMindmap, onRetry, onRenderError, onRenderSuccess, blockIndex]);

  if (lightweightMindmap) {
    return <LightweightMindmapView mindmap={lightweightMindmap} />;
  }

  const handleManualRetry = async () => {
    if (!onRetry) return;
    setRenderState('loading');
    let ok = false;
    try {
      ok = await onRetry(errorInfo.code, errorInfo.message, blockIndex ?? 0);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      setErrorInfo({
        code: errorInfo.code,
        message: errorMessage || errorInfo.message,
      });
      setRenderState('error');
      return;
    }
    if (!ok) {
      setRenderState('error');
      return;
    }

    // The parent will re-render this component if the artifact/message code was
    // actually replaced. If it was not, return to the degraded state instead of
    // leaving the chart in an endless loading state.
    setRenderState('error');
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
                <div>图表语法受损，可手动修复</div>
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
