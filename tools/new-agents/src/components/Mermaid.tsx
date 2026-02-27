import React, { useEffect, useRef, useState } from 'react';
import mermaid from 'mermaid';
import { useStore } from '../store';

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
        const { svg } = await mermaid.render(id, chart);
        if (isMounted) {
          setSvg(svg);
        }
      } catch (error) {
        // During streaming, the chart might be incomplete, causing a parsing error.
        // We catch it silently and show a loading state if still generating.
        if (isMounted) {
          if (isGenerating) {
            setSvg(`<div class="text-blue-400 p-4 border border-blue-500/30 rounded bg-blue-500/10 text-sm flex items-center gap-3"><span class="w-4 h-4 border-2 border-blue-400 border-t-transparent rounded-full animate-spin"></span> 正在绘制流程图...</div>`);
          } else {
            // If generation is done and it still fails, show the error and the raw code
            setSvg(`
              <div class="w-full">
                <div class="text-red-400 p-3 border border-red-500/30 rounded-t bg-red-500/10 text-sm">图表语法错误，无法渲染</div>
                <pre class="text-xs text-slate-400 overflow-x-auto p-4 bg-[#0f172a] rounded-b border border-t-0 border-[#1e293b]">${chart.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</pre>
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
