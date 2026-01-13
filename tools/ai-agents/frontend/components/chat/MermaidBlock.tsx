/**
 * MermaidBlock 组件 - 动态渲染 Mermaid 图表
 * 支持流式输出的防抖处理
 */
import { useEffect, useRef, useState, memo } from 'react';
import mermaid from 'mermaid';

interface MermaidBlockProps {
    code: string;
}

// 初始化 Mermaid
mermaid.initialize({
    startOnLoad: false,
    theme: 'default',
    securityLevel: 'loose',
    fontFamily: 'ui-sans-serif, system-ui, sans-serif',
});

let mermaidIdCounter = 0;

// 检测 Mermaid 代码是否可能完整（简单启发式检测）
const isCodeLikelyComplete = (code: string): boolean => {
    const trimmed = code.trim();
    if (!trimmed) return false;

    // 检查是否以常见的 Mermaid 图表类型开头
    const validStarts = ['graph', 'flowchart', 'sequenceDiagram', 'classDiagram',
        'stateDiagram', 'erDiagram', 'journey', 'gantt', 'pie',
        'gitGraph', 'mindmap', 'timeline', 'quadrantChart'];
    const hasValidStart = validStarts.some(start =>
        trimmed.toLowerCase().startsWith(start.toLowerCase())
    );

    if (!hasValidStart) return false;

    // 检查是否有足够的内容（至少有一个换行和一些节点定义）
    const lines = trimmed.split('\n').filter(line => line.trim());
    return lines.length >= 2;
};

const MermaidBlockImpl = ({ code }: MermaidBlockProps) => {
    const [error, setError] = useState<string | null>(null);
    const [svg, setSvg] = useState<string | null>(null);
    const [isRendering, setIsRendering] = useState(false);
    const lastCodeRef = useRef<string>('');
    const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

    useEffect(() => {
        // 清除之前的定时器
        if (debounceTimerRef.current) {
            clearTimeout(debounceTimerRef.current);
        }

        if (!code) return;

        // 检查代码是否可能完整
        if (!isCodeLikelyComplete(code)) {
            // 代码不完整，显示加载状态但不尝试渲染
            if (!svg && !isRendering) {
                setIsRendering(true);
            }
            return;
        }

        // 如果代码与上次相同，跳过渲染
        if (code === lastCodeRef.current && svg) {
            return;
        }

        // 防抖：等待 300ms 后再渲染
        debounceTimerRef.current = setTimeout(async () => {
            try {
                setError(null);
                setIsRendering(true);
                lastCodeRef.current = code;

                const uniqueId = `mermaid-diagram-${mermaidIdCounter++}`;
                const { svg: renderedSvg } = await mermaid.render(uniqueId, code.trim());
                setSvg(renderedSvg);
                setIsRendering(false);
            } catch (err) {
                console.error('Mermaid render error:', err);
                // 只有在代码稳定后才显示错误
                setError(err instanceof Error ? err.message : 'Failed to render diagram');
                setIsRendering(false);
            }
        }, 300);

        return () => {
            if (debounceTimerRef.current) {
                clearTimeout(debounceTimerRef.current);
            }
        };
    }, [code, svg]);

    // 显示已渲染的 SVG（如果有）
    if (svg && !isRendering) {
        return (
            <div
                className="my-4 p-4 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg overflow-x-auto"
                dangerouslySetInnerHTML={{ __html: svg }}
            />
        );
    }

    // 渲染中或等待完整代码
    if (isRendering || !error) {
        return (
            <div className="my-4 p-4 bg-gray-100 dark:bg-gray-800 rounded-lg">
                <div className="h-32 flex items-center justify-center text-gray-500">
                    <span className="animate-pulse">正在渲染图表...</span>
                </div>
            </div>
        );
    }

    // 渲染失败
    return (
        <div className="my-4 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
            <p className="text-sm text-red-600 dark:text-red-400 mb-2">
                ⚠️ 图表渲染失败
            </p>
            <pre className="text-xs text-gray-600 dark:text-gray-400 overflow-x-auto p-2 bg-gray-100 dark:bg-gray-800 rounded">
                {code}
            </pre>
        </div>
    );
};

export const MermaidBlock = memo(MermaidBlockImpl);

export default MermaidBlock;
