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
    'mvp-map': 'MVP 功能地图',
    'roadmap': '产品路线图',
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
