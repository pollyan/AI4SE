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
    kind: 'matrix';
    type: StructuredVisualType;
    title?: string;
    columns: string[];
    rows: Array<{
        cells: string[];
    }>;
}

export interface NodeEdgeStructuredVisualNode {
    id: string;
    label: string;
    title: string;
    description?: string;
    category?: string;
    evidence?: string;
    confidence?: string;
    status?: string;
}

export interface NodeEdgeStructuredVisualEdge {
    source: string;
    target: string;
    label?: string;
}

export interface NodeEdgeStructuredVisual {
    kind: 'node-edge';
    type: Extract<StructuredVisualType, 'cause-map'>;
    title?: string;
    nodes: NodeEdgeStructuredVisualNode[];
    edges: NodeEdgeStructuredVisualEdge[];
}

export type StructuredVisual = MatrixStructuredVisual | NodeEdgeStructuredVisual;

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

function requiredNonEmptyString(value: unknown): string | null {
    return typeof value === 'string' && value.trim().length > 0 ? value.trim() : null;
}

function optionalNonEmptyString(value: unknown): string | undefined {
    return typeof value === 'string' && value.trim().length > 0 ? value.trim() : undefined;
}

function parseNodeEdgeVisual(
    parsed: Record<string, unknown>,
    visualType: Extract<StructuredVisualType, 'cause-map'>,
    title: string | undefined
): StructuredVisualResult {
    if (!Array.isArray(parsed.nodes) || !parsed.nodes.every(isRecord) || !parsed.nodes.length) {
        return {
            valid: false,
            message: `${visualType} 必须包含非空 nodes 节点数组。`,
        };
    }

    const nodeIds = new Set<string>();
    const nodes: NodeEdgeStructuredVisualNode[] = [];
    for (const node of parsed.nodes) {
        const id = requiredNonEmptyString(node.id);
        const label = requiredNonEmptyString(node.label);
        const nodeTitle = requiredNonEmptyString(node.title);
        if (!id || !label || !nodeTitle) {
            return {
                valid: false,
                message: `${visualType} node 必须包含非空 id、label 和 title。`,
            };
        }
        if (nodeIds.has(id)) {
            return {
                valid: false,
                message: `${visualType} 包含重复 node id：${id}。`,
            };
        }
        nodeIds.add(id);
        nodes.push({
            id,
            label,
            title: nodeTitle,
            description: optionalNonEmptyString(node.description),
            category: optionalNonEmptyString(node.category),
            evidence: optionalNonEmptyString(node.evidence),
            confidence: optionalNonEmptyString(node.confidence),
            status: optionalNonEmptyString(node.status),
        });
    }

    if (!Array.isArray(parsed.edges) || !parsed.edges.every(isRecord)) {
        return {
            valid: false,
            message: `${visualType} 必须包含 edges 对象数组。`,
        };
    }

    const edges: NodeEdgeStructuredVisualEdge[] = [];
    for (const edge of parsed.edges) {
        const source = requiredNonEmptyString(edge.source);
        const target = requiredNonEmptyString(edge.target);
        if (!source || !target) {
            return {
                valid: false,
                message: `${visualType} edge 必须包含非空 source 和 target。`,
            };
        }
        if (!nodeIds.has(source) || !nodeIds.has(target)) {
            return {
                valid: false,
                message: `${visualType} edge 引用了不存在的节点：${source} -> ${target}。`,
            };
        }
        edges.push({
            source,
            target,
            label: optionalNonEmptyString(edge.label),
        });
    }

    return {
        valid: true,
        visual: {
            kind: 'node-edge',
            type: visualType,
            title,
            nodes,
            edges,
        },
    };
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

    const title = typeof parsed.title === 'string' && parsed.title.trim().length > 0
        ? parsed.title
        : undefined;

    if (visualType === 'cause-map') {
        return parseNodeEdgeVisual(parsed, visualType, title);
    }

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

    return {
        valid: true,
        visual: {
            kind: 'matrix',
            type: visualType,
            title,
            columns,
            rows: parsed.rows.map((row) => ({
                cells: columns.map((column) => stringifyCell(row[column])),
            })),
        },
    };
}
