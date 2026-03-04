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

export const Mermaid: React.FC<{ chart: string }> = ({ chart }) => {
  const ref = useRef<HTMLDivElement>(null);
  const [svg, setSvg] = useState<string>('');
  const isGenerating = useStore((state) => state.isGenerating);

  useEffect(() => {
    let isMounted = true;

    const renderChart = async () => {
      try {
        const id = `mermaid-${Math.random().toString(36).substr(2, 9)}`;

        // --- 容错渲染策略 ---
        // 第一级：原始代码基本清洗
        const sanitized = sanitizeMermaidCode(chart);
        const originalParseResult = await mermaid.parse(sanitized, { suppressErrors: true });

        if (originalParseResult) {
          const { svg: generatedSvg } = await mermaid.render(id, sanitized);
          if (isMounted) setSvg(generatedSvg);
          return;
        }

        // 第二级：激进清洗（LLM 严重幻觉时）
        const aggressive = aggressiveSanitize(sanitized);
        const aggressiveParseResult = await mermaid.parse(aggressive, { suppressErrors: true });

        if (aggressiveParseResult) {
          const { svg: generatedSvg } = await mermaid.render(id, aggressive);
          if (isMounted) setSvg(generatedSvg);
          return;
        }

        // 全部尝试失败，抛出错误走降级
        throw new Error('Mermaid syntax validation failed after all sanitization attempts.');

      } catch (error) {
        // During streaming, the chart might be incomplete, causing a parsing error.
        // We catch it silently and show a loading state if still generating.
        if (isMounted) {
          if (isGenerating) {
            setSvg(`<div class="text-blue-400 p-4 border border-blue-500/30 rounded bg-blue-500/10 text-sm flex items-center gap-3"><span class="w-4 h-4 border-2 border-blue-400 border-t-transparent rounded-full animate-spin"></span> 正在绘制流程图...</div>`);
          } else {
            // If generation is done and it still fails, show degraded experience with link to Live Editor
            const encodedChart = btoa(unescape(encodeURIComponent(chart)));
            const liveEditorUrl = `https://mermaid.live/edit#pako:${encodedChart}`;
            const cleanHtmlChart = chart.replace(/</g, '&lt;').replace(/>/g, '&gt;');

            setSvg(`
              <div class="w-full bg-[#0f172a] rounded-lg border border-[#1e293b] overflow-hidden my-4">
                <div class="flex justify-between items-center bg-red-500/10 border-b border-red-500/20 px-4 py-3">
                  <div class="text-red-400 text-sm font-medium flex items-center gap-2">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                    图表语法受损，已启动格式降级
                  </div>
                  <a href="${liveEditorUrl}" target="_blank" rel="noopener noreferrer" class="text-xs bg-blue-500/20 hover:bg-blue-500/30 text-blue-400 px-3 py-1.5 rounded transition-colors flex items-center gap-1 border border-blue-500/30">
                    在 Live Editor 修复
                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path></svg>
                  </a>
                </div>
                <details class="text-slate-400 text-sm group">
                  <summary class="cursor-pointer font-mono px-4 py-3 hover:bg-white/5 transition-colors select-none flex items-center gap-2">
                    <span class="opacity-50 group-open:rotate-90 transition-transform">▶</span> 
                    查看原始代码
                  </summary>
                  <pre class="p-4 bg-black/20 border-t border-[#1e293b] overflow-x-auto text-xs font-mono leading-relaxed">${cleanHtmlChart}</pre>
                </details>
              </div>
            `);
          }
        }
      }
    };

    if (chart) {
      renderChart();
    }

    return () => {
      isMounted = false;
    };
  }, [chart, isGenerating]);

  return <div ref={ref} dangerouslySetInnerHTML={{ __html: svg }} className="flex justify-center my-6 w-full overflow-x-auto" />;
};
