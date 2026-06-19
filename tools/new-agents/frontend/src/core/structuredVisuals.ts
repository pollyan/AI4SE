export type StructuredVisualType =
    | 'traceability-matrix'
    | 'score-matrix'
    | 'risk-board'
    | 'action-board'
    | 'journey-map'
    | 'coverage-map'
    | 'priority-board'
    | 'cause-map'
    | 'mvp-map'
    | 'roadmap';

const SUPPORTED_VISUAL_TYPES: StructuredVisualType[] = [
    'traceability-matrix',
    'score-matrix',
    'risk-board',
    'action-board',
    'journey-map',
    'coverage-map',
    'priority-board',
    'cause-map',
    'mvp-map',
    'roadmap',
];

export interface MatrixStructuredVisual {
    type: StructuredVisualType;
    title?: string;
    columns: string[];
    rows: Array<{
        cells: string[];
    }>;
}

export type StructuredVisual = MatrixStructuredVisual;

export type StructuredVisualResult =
    | {
        valid: true;
        visual: StructuredVisual;
    }
    | {
        valid: false;
        message: string;
    };

function isRecord(value: unknown): value is Record<string, unknown> {
    return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function asNonEmptyStringArray(value: unknown): string[] | null {
    if (!Array.isArray(value)) return null;
    const strings = value.filter((entry): entry is string => (
        typeof entry === 'string' && entry.trim().length > 0
    ));
    return strings.length === value.length && strings.length > 0 ? strings : null;
}

function stringifyCell(value: unknown): string {
    if (value === null || value === undefined) return '';
    if (typeof value === 'string') return value;
    if (typeof value === 'number' || typeof value === 'boolean') return String(value);
    return JSON.stringify(value);
}

export function parseStructuredVisual(source: string): StructuredVisualResult {
    let parsed: unknown;

    try {
        parsed = JSON.parse(source);
    } catch {
        return {
            valid: false,
            message: '结构化可视化必须是合法 JSON。',
        };
    }

    if (!isRecord(parsed)) {
        return {
            valid: false,
            message: '结构化可视化必须是 JSON 对象。',
        };
    }

    if (
        typeof parsed.type !== 'string'
        || !SUPPORTED_VISUAL_TYPES.includes(parsed.type as StructuredVisualType)
    ) {
        return {
            valid: false,
            message: `不支持的结构化可视化类型：${String(parsed.type)}。`,
        };
    }
    const visualType = parsed.type as StructuredVisualType;

    const columns = asNonEmptyStringArray(parsed.columns);
    if (!columns) {
        return {
            valid: false,
            message: `${visualType} 必须包含非空 columns 字符串数组。`,
        };
    }

    if (!Array.isArray(parsed.rows) || !parsed.rows.every(isRecord)) {
        return {
            valid: false,
            message: `${visualType} 必须包含 rows 对象数组。`,
        };
    }

    const title = typeof parsed.title === 'string' && parsed.title.trim().length > 0
        ? parsed.title
        : undefined;

    return {
        valid: true,
        visual: {
            type: visualType,
            title,
            columns,
            rows: parsed.rows.map((row) => ({
                cells: columns.map((column) => stringifyCell(row[column])),
            })),
        },
    };
}
