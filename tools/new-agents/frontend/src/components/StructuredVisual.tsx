import React, { useEffect, useMemo } from 'react';
import { parseStructuredVisual, StructuredVisualType } from '../core/structuredVisuals';

interface StructuredVisualProps {
    source: string;
    onValidationError?: (message: string) => void;
    onValidationSuccess?: () => void;
}

const DEFAULT_TITLES: Record<StructuredVisualType, string> = {
    'traceability-matrix': '结构化追溯矩阵',
    'score-matrix': '结构化评分矩阵',
    'risk-board': '风险处置看板',
    'action-board': '改进行动看板',
    'journey-map': '用户旅程地图',
    'coverage-map': '交付覆盖地图',
    'priority-board': '问题优先级看板',
    'cause-map': '根因链路图',
    'flow-map': '流程图',
    'mvp-map': 'MVP 功能地图',
    'roadmap': '产品路线图',
    'story-map': '用户故事地图',
    'timeline-map': '事件时间线',
};

export const StructuredVisual: React.FC<StructuredVisualProps> = ({
    source,
    onValidationError,
    onValidationSuccess,
}) => {
    const result = useMemo(() => parseStructuredVisual(source), [source]);

    useEffect(() => {
        if (result.valid === false) {
            onValidationError?.(result.message);
            return;
        }
        onValidationSuccess?.();
    }, [onValidationError, onValidationSuccess, result]);

    if (result.valid === false) {
        return (
            <div className="my-6 rounded-lg border border-rose-500/25 bg-rose-500/10 p-4 text-sm text-rose-100">
                <div className="font-semibold">结构化可视化格式错误</div>
                <div className="mt-1 text-rose-100/80">{result.message}</div>
            </div>
        );
    }

    const visual = result.visual;
    const title = visual.title || DEFAULT_TITLES[visual.type];

    if (visual.kind === 'node-edge' || visual.kind === 'flow') {
        const connectionLabel = visual.kind === 'flow' ? '流程连接' : '因果连接';
        return (
            <div
                role="group"
                aria-label={title}
                className="my-6 overflow-hidden rounded-lg border border-[#1e293b] bg-[#0f172a] shadow-sm"
            >
                <div className="border-b border-[#1e293b] bg-[#111827] px-4 py-3">
                    <h3 className="text-sm font-semibold text-slate-100">{title}</h3>
                    <p className="mt-1 text-xs text-slate-500">ai4se-visual · {visual.type}</p>
                </div>
                <div className="space-y-3 p-4">
                    {visual.nodes.map((node) => (
                        <div
                            key={node.id}
                            className="rounded-md border border-[#334155] bg-[#111827] p-3"
                        >
                            <div className="flex flex-wrap items-center gap-2">
                                <span className="rounded bg-cyan-500/15 px-2 py-0.5 text-xs font-semibold text-cyan-200">
                                    {node.label}
                                </span>
                                <span className="text-sm font-semibold text-slate-100">
                                    {node.title}
                                </span>
                            </div>
                            {node.description && (
                                <p className="mt-2 text-sm text-slate-300">{node.description}</p>
                            )}
                            <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-400">
                                {node.category && <span>类型：{node.category}</span>}
                                {node.evidence && <span>证据：{node.evidence}</span>}
                                {node.confidence && <span>置信度：{node.confidence}</span>}
                                {node.status && <span>状态：{node.status}</span>}
                            </div>
                        </div>
                    ))}
                    {visual.edges.length > 0 && (
                        <div className="border-t border-[#1e293b] pt-3">
                            <div className="text-xs font-semibold text-slate-500">
                                {connectionLabel}
                            </div>
                            <div className="mt-2 space-y-2">
                                {visual.edges.map((edge) => (
                                    <div
                                        key={`${edge.source}-${edge.target}-${edge.label || ''}`}
                                        className="flex flex-wrap items-center gap-2 text-sm text-slate-300"
                                    >
                                        <span className="font-mono text-cyan-200">
                                            {edge.source} -&gt; {edge.target}
                                        </span>
                                        {edge.label && (
                                            <span className="rounded bg-slate-800 px-2 py-0.5 text-xs text-slate-300">
                                                {edge.label}
                                            </span>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            </div>
        );
    }

    if (visual.kind === 'timeline') {
        return (
            <div
                role="group"
                aria-label={title}
                className="my-6 overflow-hidden rounded-lg border border-[#1e293b] bg-[#0f172a] shadow-sm"
            >
                <div className="border-b border-[#1e293b] bg-[#111827] px-4 py-3">
                    <h3 className="text-sm font-semibold text-slate-100">{title}</h3>
                    <p className="mt-1 text-xs text-slate-500">ai4se-visual · {visual.type}</p>
                </div>
                <ol className="relative space-y-4 p-4">
                    {visual.events.map((event, index) => (
                        <li key={event.id} className="grid grid-cols-[5.5rem_1fr] gap-3">
                            <div className="pt-1 text-right">
                                <div className="font-mono text-sm font-semibold text-cyan-200">
                                    {event.time}
                                </div>
                                <div className="mt-1 text-xs text-slate-500">{event.id}</div>
                            </div>
                            <div className="relative border-l border-[#334155] pb-1 pl-4">
                                <span
                                    aria-hidden="true"
                                    className="absolute -left-[5px] top-2 h-2.5 w-2.5 rounded-full bg-cyan-300"
                                />
                                {index < visual.events.length - 1 && (
                                    <span
                                        aria-hidden="true"
                                        className="absolute -left-px top-5 h-full border-l border-[#334155]"
                                    />
                                )}
                                <div className="text-sm font-semibold text-slate-100">
                                    {event.title}
                                </div>
                                <p className="mt-1 text-sm text-slate-300">{event.description}</p>
                                <div className="mt-3 flex flex-wrap gap-2">
                                    {event.factIds.map((factId) => (
                                        <span
                                            key={factId}
                                            className="rounded bg-slate-800 px-2 py-0.5 text-xs text-slate-300"
                                        >
                                            {factId}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        </li>
                    ))}
                </ol>
            </div>
        );
    }

    return (
        <div className="my-6 overflow-hidden rounded-lg border border-[#1e293b] bg-[#0f172a] shadow-sm">
            <div className="border-b border-[#1e293b] bg-[#111827] px-4 py-3">
                <h3 className="text-sm font-semibold text-slate-100">{title}</h3>
                <p className="mt-1 text-xs text-slate-500">ai4se-visual · {visual.type}</p>
            </div>
            <div className="overflow-x-auto">
                <table aria-label={title} className="w-full border-collapse text-sm">
                    <thead>
                        <tr>
                            {visual.columns.map((column) => (
                                <th
                                    key={column}
                                    className="border-b border-[#334155] bg-[#1e293b] px-3 py-2 text-left font-semibold text-slate-200"
                                >
                                    {column}
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {visual.rows.map((row, rowIndex) => (
                            <tr key={rowIndex} className="transition-colors hover:bg-white/[0.03]">
                                {row.cells.map((cell, cellIndex) => (
                                    <td
                                        key={`${rowIndex}-${cellIndex}`}
                                        className="border-b border-[#1e293b] px-3 py-2 text-slate-300"
                                    >
                                        {cell}
                                    </td>
                                ))}
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
};
