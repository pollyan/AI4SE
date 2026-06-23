import { workflowManifest } from './workflowRegistry';
import type { ArtifactVisualDiagnostic, WorkflowType } from './types';

export type ArtifactDiagnosticCategory =
    | 'heading'
    | 'mermaid'
    | 'structured-visual'
    | 'stage-gate'
    | 'runtime-visual';

export type ArtifactDiagnosticStatus = 'pass' | 'warn' | 'fail';

export type ArtifactQualityStatus = 'empty' | 'pass' | 'warn' | 'fail';

export type ArtifactQualityDiagnosticItem = {
    id: string;
    category: ArtifactDiagnosticCategory;
    status: ArtifactDiagnosticStatus;
    title: string;
    detail: string;
    nextAction: string;
};

export type ArtifactOpenQuestion = {
    id: string;
    title: string;
    detail: string;
    blocking: boolean;
    nextAction: string;
};

export type ArtifactQualityDiagnostics = {
    status: ArtifactQualityStatus;
    summary: {
        pass: number;
        warn: number;
        fail: number;
        openQuestions: number;
    };
    items: ArtifactQualityDiagnosticItem[];
    openQuestions: ArtifactOpenQuestion[];
};

export type BuildArtifactQualityDiagnosticsInput = {
    workflowId: WorkflowType;
    stageId: string;
    artifactContent: string;
    visualDiagnostics: ArtifactVisualDiagnostic[];
};

const EMPTY_RESULT: ArtifactQualityDiagnostics = {
    status: 'empty',
    summary: {
        pass: 0,
        warn: 0,
        fail: 0,
        openQuestions: 0,
    },
    items: [],
    openQuestions: [],
};

const normalizeSearchText = (value: string): string => (
    value.replace(/\s+/g, ' ').trim().toLowerCase()
);

const includesRequirement = (artifactContent: string, requirement: string): boolean => (
    normalizeSearchText(artifactContent).includes(normalizeSearchText(requirement))
);

const extractFencedBlocks = (artifactContent: string, language: string): string[] => {
    const pattern = new RegExp(`\`\`\`${language}\\s*([\\s\\S]*?)\`\`\``, 'gi');
    const blocks: string[] = [];
    let match = pattern.exec(artifactContent);
    while (match) {
        blocks.push(match[1] ?? '');
        match = pattern.exec(artifactContent);
    }
    return blocks;
};

const extractStructuredVisualTypes = (artifactContent: string): string[] => (
    extractFencedBlocks(artifactContent, 'ai4se-visual')
        .map((block) => {
            try {
                const parsed = JSON.parse(block);
                return typeof parsed.type === 'string' ? parsed.type.trim() : '';
            } catch {
                return '';
            }
        })
        .filter(Boolean)
);

const hasMermaidDiagram = (blocks: string[], requiredType: string): boolean => {
    const normalizedRequiredType = normalizeSearchText(requiredType);
    return blocks.some((block) => normalizeSearchText(block).includes(normalizedRequiredType));
};

const buildItem = (
    id: string,
    category: ArtifactDiagnosticCategory,
    status: ArtifactDiagnosticStatus,
    title: string,
    detail: string,
    nextAction: string
): ArtifactQualityDiagnosticItem => ({
    id,
    category,
    status,
    title,
    detail,
    nextAction,
});

const cleanQuestionLine = (line: string): string => (
    line
        .replace(/^\s*[-*]\s*/, '')
        .replace(/^\s*\|/, '')
        .replace(/\|\s*$/, '')
        .replace(/\s*\|\s*/g, ' ')
        .replace(/^checked=(?:false|true)[：:\s-]*/i, '')
        .trim()
);

const summarizeQuestionTitle = (line: string): string => {
    const withoutPrefix = cleanQuestionLine(line)
        .replace(/^(阻断|待确认|未确认|需补充|未验证|开放问题|缺失信息|待处理)[：:\s-]*/u, '')
        .trim();
    const candidate = withoutPrefix.split(/[，。；;,.]/u)[0]?.trim() || withoutPrefix;
    return candidate.length > 32 ? `${candidate.slice(0, 32)}...` : candidate;
};

type OpenQuestionSectionKind = 'question' | 'gate' | null;

const getOpenQuestionSectionKind = (line: string): OpenQuestionSectionKind => {
    if (!/^#{1,4}\s+/.test(line)) return null;
    if (/阶段门禁/u.test(line)) return 'gate';
    if (/待澄清|开放问题|未验证|未确认|缺失信息|阻断|待处理/u.test(line)) return 'question';
    return null;
};

const isNegativeGateLine = (line: string): boolean => (
    /阻断|P0|必须|无法进入|checked=false|待确认|未确认|需补充|未验证/u.test(line)
);

const isRelevantQuestionLine = (line: string, sectionKind: OpenQuestionSectionKind): boolean => {
    const cleaned = cleanQuestionLine(line);
    if (!cleaned) return false;
    if (/^\|?\s*-{2,}/.test(cleaned)) return false;
    if (/^```/.test(cleaned)) return false;
    if (/^#{1,4}\s+/.test(cleaned)) return false;
    if (sectionKind === 'question') return true;
    if (sectionKind === 'gate') return isNegativeGateLine(cleaned);
    return isNegativeGateLine(cleaned);
};

const isBlockingQuestion = (line: string): boolean => (
    /阻断|P0|必须|无法进入|checked=false/u.test(line)
);

const extractOpenQuestions = (artifactContent: string): ArtifactOpenQuestion[] => {
    const lines = artifactContent.split(/\r?\n/);
    const questions: ArtifactOpenQuestion[] = [];
    let sectionKind: OpenQuestionSectionKind = null;

    lines.forEach((line, index) => {
        if (/^#{1,4}\s+/.test(line)) {
            sectionKind = getOpenQuestionSectionKind(line);
            return;
        }
        if (!isRelevantQuestionLine(line, sectionKind)) return;

        const detail = cleanQuestionLine(line);
        const title = summarizeQuestionTitle(detail);
        if (!title) return;

        questions.push({
            id: `open-question:${index}`,
            title,
            detail,
            blocking: isBlockingQuestion(detail),
            nextAction: '补充输入或手工修订后重新生成当前阶段产物。',
        });
    });

    return questions.slice(0, 6);
};

export const buildArtifactQualityDiagnostics = ({
    workflowId,
    stageId,
    artifactContent,
    visualDiagnostics,
}: BuildArtifactQualityDiagnosticsInput): ArtifactQualityDiagnostics => {
    if (!artifactContent.trim()) {
        return EMPTY_RESULT;
    }

    const workflow = workflowManifest.workflows[workflowId];
    const stage = workflow?.stages.find(candidate => candidate.id === stageId);
    const items: ArtifactQualityDiagnosticItem[] = [];

    const requiredHeadings = stage?.artifactContract?.requiredHeadings ?? [];
    const missingHeadings = requiredHeadings.filter(
        heading => !includesRequirement(artifactContent, heading)
    );
    items.push(buildItem(
        'required-headings',
        'heading',
        missingHeadings.length === 0 ? 'pass' : 'fail',
        missingHeadings.length === 0 ? '必填标题完整' : '缺少必填标题',
        missingHeadings.length === 0
            ? '当前产物包含本阶段要求的标题和关键字段。'
            : missingHeadings.slice(0, 8).join('、'),
        missingHeadings.length === 0
            ? '无需处理。'
            : '补齐缺失标题或重新生成当前阶段产物。'
    ));

    const mermaidBlocks = extractFencedBlocks(artifactContent, 'mermaid');
    const requiredMermaid = stage?.visualContract?.requiredMermaidDiagrams ?? [];
    if (requiredMermaid.length > 0) {
        const missingMermaid = requiredMermaid.filter(
            diagramType => !hasMermaidDiagram(mermaidBlocks, diagramType)
        );
        items.push(buildItem(
            'required-mermaid',
            'mermaid',
            missingMermaid.length === 0 ? 'pass' : 'fail',
            missingMermaid.length === 0 ? 'Mermaid 图表完整' : '缺少 Mermaid 图表',
            missingMermaid.length === 0
                ? '当前产物包含本阶段要求的 Mermaid 图表。'
                : missingMermaid.join('、'),
            missingMermaid.length === 0
                ? '无需处理。'
                : '补齐图表或重新生成当前阶段产物。'
        ));
    }

    const structuredVisualTypes = extractStructuredVisualTypes(artifactContent);
    const requiredStructuredVisuals = stage?.visualContract?.requiredStructuredVisuals ?? [];
    if (requiredStructuredVisuals.length > 0) {
        const missingStructuredVisuals = requiredStructuredVisuals.filter(
            visualType => !structuredVisualTypes.includes(visualType)
        );
        items.push(buildItem(
            'required-structured-visual',
            'structured-visual',
            missingStructuredVisuals.length === 0 ? 'pass' : 'fail',
            missingStructuredVisuals.length === 0 ? '结构化可视化完整' : '缺少结构化可视化',
            missingStructuredVisuals.length === 0
                ? '当前产物包含本阶段要求的 ai4se-visual。'
                : missingStructuredVisuals.join('、'),
            missingStructuredVisuals.length === 0
                ? '无需处理。'
                : '补齐结构化可视化或重新生成当前阶段产物。'
        ));
    }

    const hasStageGate = /阶段门禁/u.test(artifactContent);
    items.push(buildItem(
        'stage-gate',
        'stage-gate',
        hasStageGate ? 'pass' : 'fail',
        hasStageGate ? '阶段门禁已声明' : '缺少阶段门禁',
        hasStageGate
            ? '当前产物包含阶段门禁信息。'
            : '当前产物没有明确阶段门禁。',
        hasStageGate
            ? '按门禁结论决定是否推进。'
            : '补齐阶段门禁或重新生成当前阶段产物。'
    ));

    visualDiagnostics
        .filter(diagnostic => diagnostic.stageId === stageId)
        .forEach((diagnostic) => {
            items.push(buildItem(
                `runtime-visual:${diagnostic.id}`,
                'runtime-visual',
                'warn',
                '运行时可视化警告',
                diagnostic.message,
                '打开预览定位该图表，修订 Mermaid 或 ai4se-visual 后重试。'
            ));
        });

    const openQuestions = extractOpenQuestions(artifactContent);
    const summary = items.reduce(
        (counts, item) => ({
            ...counts,
            [item.status]: counts[item.status] + 1,
        }),
        {
            pass: 0,
            warn: 0,
            fail: 0,
            openQuestions: openQuestions.length,
        }
    );

    return {
        status: summary.fail > 0 ? 'fail' : summary.warn > 0 ? 'warn' : 'pass',
        summary,
        items,
        openQuestions,
    };
};
