import type { ArtifactVisualDiagnostic, WorkflowStage } from './types';

export type ArtifactQualityStatus = 'empty' | 'pass' | 'warning' | 'fail';
export type ArtifactQualityItemStatus = 'pass' | 'warning' | 'fail';
export type ArtifactQualityCategory =
    | 'heading'
    | 'field'
    | 'visual'
    | 'stage-gate'
    | 'visual-diagnostic';

export type ArtifactQualityItem = {
    id: string;
    category: ArtifactQualityCategory;
    status: ArtifactQualityItemStatus;
    title: string;
    message: string;
    actionDiagnosticId?: string;
};

export type MissingInfoItem = {
    id: string;
    title: string;
    blocking: boolean;
    severity: 'blocking' | 'warning';
    reason: string;
    nextAction: string;
    actionDiagnosticId?: string;
};

export type ArtifactQualitySummary = {
    status: ArtifactQualityStatus;
    passedCount: number;
    failedCount: number;
    warningCount: number;
    items: ArtifactQualityItem[];
    missingInfoItems: MissingInfoItem[];
};

export type BuildArtifactQualitySummaryInput = {
    stage: WorkflowStage | undefined;
    content: string;
    visualDiagnostics: ArtifactVisualDiagnostic[];
};

type MarkdownFence = {
    language: string;
    body: string;
};

const normalizeLine = (value: string): string => value.trim();

const isHeadingRequirement = (requirement: string): boolean => /^#{1,6}\s+\S/.test(requirement.trim());

const buildItem = (
    category: ArtifactQualityCategory,
    status: ArtifactQualityItemStatus,
    title: string,
    message: string,
    actionDiagnosticId?: string
): ArtifactQualityItem => ({
    id: `${category}:${title}`,
    category,
    status,
    title,
    message,
    ...(actionDiagnosticId ? { actionDiagnosticId } : {}),
});

const buildMissingInfoNextAction = (item: ArtifactQualityItem): string => {
    switch (item.category) {
        case 'heading':
        case 'field':
            return '补充缺失内容后重新生成或手动完善当前阶段产物。';
        case 'visual':
            return '重新生成当前阶段产物，确保图表和结构化可视化按合同输出。';
        case 'stage-gate':
            return '确认阶段门禁决策项，明确是否可以进入下一阶段。';
        case 'visual-diagnostic':
            return '定位问题位置，修复可视化内容后再继续推进。';
        default:
            return '处理该缺失项后再继续推进当前阶段。';
    }
};

const buildMissingInfoItems = (items: ArtifactQualityItem[]): MissingInfoItem[] => (
    items
        .filter((item) => item.status !== 'pass')
        .map((item) => {
            const blocking = item.status === 'fail';
            return {
                id: `missing:${item.id}`,
                title: item.title,
                blocking,
                severity: blocking ? 'blocking' : 'warning',
                reason: item.message,
                nextAction: buildMissingInfoNextAction(item),
                ...(item.actionDiagnosticId ? { actionDiagnosticId: item.actionDiagnosticId } : {}),
            };
        })
);

const extractMarkdownFences = (content: string): MarkdownFence[] => {
    const lines = content.split(/\r?\n/);
    const fences: MarkdownFence[] = [];
    let currentLanguage: string | null = null;
    let currentBody: string[] = [];

    lines.forEach((line) => {
        const fenceMatch = line.match(/^```\s*([A-Za-z0-9_-]+)?\s*$/);
        if (!fenceMatch) {
            if (currentLanguage !== null) {
                currentBody.push(line);
            }
            return;
        }

        if (currentLanguage === null) {
            currentLanguage = (fenceMatch[1] ?? '').trim().toLowerCase();
            currentBody = [];
            return;
        }

        fences.push({
            language: currentLanguage,
            body: currentBody.join('\n'),
        });
        currentLanguage = null;
        currentBody = [];
    });

    return fences;
};

const hasMarkdownHeading = (content: string, requiredHeading: string): boolean => {
    const normalizedRequirement = normalizeLine(requiredHeading);
    return content.split(/\r?\n/).some((line) => normalizeLine(line) === normalizedRequirement);
};

const hasMermaidDiagram = (fences: MarkdownFence[], diagramType: string): boolean => {
    const normalizedDiagramType = diagramType.trim().toLowerCase();
    return fences.some((fence) => {
        if (fence.language !== 'mermaid') return false;
        const firstLine = fence.body
            .split(/\r?\n/)
            .map((line) => line.trim())
            .find(Boolean);
        return firstLine?.toLowerCase().startsWith(normalizedDiagramType) ?? false;
    });
};

const hasStructuredVisual = (fences: MarkdownFence[], visualType: string): boolean => {
    const normalizedVisualType = visualType.trim();
    return fences.some((fence) => {
        if (fence.language !== 'ai4se-visual') return false;
        try {
            const parsed = JSON.parse(fence.body) as { type?: unknown };
            return parsed.type === normalizedVisualType;
        } catch {
            return false;
        }
    });
};

const extractStageGateSection = (content: string, stageGateHeading: string): string | null => {
    const lines = content.split(/\r?\n/);
    const targetHeading = normalizeLine(stageGateHeading);
    const startIndex = lines.findIndex((line) => normalizeLine(line) === targetHeading);
    if (startIndex < 0) return null;

    const currentLevel = targetHeading.match(/^(#{1,6})\s+/)?.[1].length ?? 1;
    const endIndex = lines.findIndex((line, index) => {
        if (index <= startIndex) return false;
        const headingMatch = line.match(/^(#{1,6})\s+\S/);
        return Boolean(headingMatch && headingMatch[1].length <= currentLevel);
    });

    return lines.slice(startIndex, endIndex < 0 ? undefined : endIndex).join('\n');
};

export const buildArtifactQualitySummary = ({
    stage,
    content,
    visualDiagnostics,
}: BuildArtifactQualitySummaryInput): ArtifactQualitySummary => {
    if (!stage) {
        return {
            status: 'empty',
            passedCount: 0,
            failedCount: 0,
            warningCount: 0,
            items: [],
            missingInfoItems: [],
        };
    }

    const trimmedContent = content.trim();
    const requiredEntries = stage.artifactContract?.requiredHeadings ?? [];
    const fences = extractMarkdownFences(content);
    const items: ArtifactQualityItem[] = [];

    requiredEntries.forEach((entry) => {
        const requirement = entry.trim();
        if (!requirement) return;

        if (isHeadingRequirement(requirement)) {
            const exists = hasMarkdownHeading(content, requirement);
            items.push(buildItem(
                'heading',
                exists ? 'pass' : 'fail',
                exists ? `已包含标题：${requirement}` : `缺少标题：${requirement}`,
                exists
                    ? '产出物包含当前阶段要求的 Markdown 标题。'
                    : '产出物缺少当前阶段 artifact contract 要求的 Markdown 标题。'
            ));
            return;
        }

        const exists = content.includes(requirement);
        items.push(buildItem(
            'field',
            exists ? 'pass' : 'fail',
            exists ? `已包含专业字段：${requirement}` : `缺少专业字段：${requirement}`,
            exists
                ? '产出物包含当前阶段要求的专业字段或表格列。'
                : '产出物缺少当前阶段 artifact contract 要求的专业字段或表格列。'
        ));
    });

    (stage.visualContract?.requiredMermaidDiagrams ?? []).forEach((diagramType) => {
        const exists = hasMermaidDiagram(fences, diagramType);
        items.push(buildItem(
            'visual',
            exists ? 'pass' : 'fail',
            exists ? `已包含 Mermaid 图：${diagramType}` : `缺少 Mermaid 图：${diagramType}`,
            exists
                ? '产出物包含当前阶段要求的 Mermaid 图表类型。'
                : '产出物缺少当前阶段 visual contract 要求的 Mermaid 图表类型。'
        ));
    });

    (stage.visualContract?.requiredStructuredVisuals ?? []).forEach((visualType) => {
        const exists = hasStructuredVisual(fences, visualType);
        items.push(buildItem(
            'visual',
            exists ? 'pass' : 'fail',
            exists ? `已包含结构化可视化：${visualType}` : `缺少结构化可视化：${visualType}`,
            exists
                ? '产出物包含当前阶段要求的 ai4se-visual 类型。'
                : '产出物缺少当前阶段 visual contract 要求的 ai4se-visual 类型。'
        ));
    });

    const stageGateHeading = requiredEntries.find((entry) => isHeadingRequirement(entry) && entry.includes('阶段门禁'));
    if (stageGateHeading && hasMarkdownHeading(content, stageGateHeading)) {
        const stageGateSection = extractStageGateSection(content, stageGateHeading);
        const hasDecisionCheckbox = Boolean(stageGateSection?.match(/-\s+\[[ xX]\]\s+\S/));
        items.push(buildItem(
            'stage-gate',
            hasDecisionCheckbox ? 'pass' : 'warning',
            hasDecisionCheckbox ? '阶段门禁已有决策项' : '阶段门禁缺少决策项',
            hasDecisionCheckbox
                ? '阶段门禁章节包含可确认的 checkbox 决策项。'
                : '阶段门禁章节存在，但缺少 checkbox 决策项，用户难以判断是否可进入下一阶段。'
        ));
    }

    visualDiagnostics.forEach((diagnostic) => {
        items.push(buildItem(
            'visual-diagnostic',
            'fail',
            diagnostic.title,
            diagnostic.message,
            diagnostic.id
        ));
    });

    const passedCount = items.filter((item) => item.status === 'pass').length;
    const failedCount = items.filter((item) => item.status === 'fail').length;
    const warningCount = items.filter((item) => item.status === 'warning').length;
    const status: ArtifactQualityStatus = !trimmedContent && visualDiagnostics.length === 0
        ? 'empty'
        : failedCount > 0
            ? 'fail'
            : warningCount > 0
                ? 'warning'
                : 'pass';
    const missingInfoItems = status === 'empty' ? [] : buildMissingInfoItems(items);

    return {
        status,
        passedCount,
        failedCount,
        warningCount,
        items,
        missingInfoItems,
    };
};
