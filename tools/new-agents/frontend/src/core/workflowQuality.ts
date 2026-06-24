import type { ArtifactVisualDiagnostic, WorkflowDef } from './types';

export type WorkflowQualityStatus = 'pass' | 'warning' | 'fail';

export type WorkflowQualityCheck = {
    id: string;
    label: string;
    status: WorkflowQualityStatus;
    statusLabel: string;
    evidence: string;
    impact: string;
};

export type WorkflowQualitySummary = {
    score: number;
    status: WorkflowQualityStatus;
    statusLabel: string;
    summary: string;
    passedCount: number;
    warningCount: number;
    failedCount: number;
    checks: WorkflowQualityCheck[];
    actionItems: string[];
};

export type BuildWorkflowQualitySummaryInput = {
    workflow: WorkflowDef;
    stageId: string | undefined;
    artifactMarkdown: string;
    visualDiagnostics: ArtifactVisualDiagnostic[];
};

const STATUS_LABELS: Record<WorkflowQualityStatus, string> = {
    pass: '可交付',
    warning: '需关注',
    fail: '需修复',
};

const normalize = (value: string): string => value.replace(/\s+/g, ' ').trim().toLowerCase();

const hasRequiredText = (artifactMarkdown: string, requiredText: string): boolean => (
    normalize(artifactMarkdown).includes(normalize(requiredText))
);

const extractFencedBlocks = (artifactMarkdown: string, language: string): string[] => {
    const blocks: string[] = [];
    const pattern = new RegExp(`\`\`\`${language}\\s*\\n([\\s\\S]*?)\\n\`\`\``, 'gi');
    let match = pattern.exec(artifactMarkdown);
    while (match) {
        blocks.push(match[1]);
        match = pattern.exec(artifactMarkdown);
    }
    return blocks;
};

const includesVisualType = (blocks: string[], visualType: string): boolean => (
    blocks.some(block => normalize(block).includes(normalize(visualType)))
);

const makeCheck = (
    id: string,
    label: string,
    status: WorkflowQualityStatus,
    evidence: string,
    impact: string
): WorkflowQualityCheck => ({
    id,
    label,
    status,
    statusLabel: STATUS_LABELS[status],
    evidence,
    impact,
});

const addUniqueActionItem = (items: string[], item: string): void => {
    if (!items.includes(item)) {
        items.push(item);
    }
};

const summarizeQuality = (status: WorkflowQualityStatus): string => {
    if (status === 'pass') {
        return '当前阶段产出物满足确定性质量门禁，可进入交付或下一阶段审阅。';
    }
    if (status === 'warning') {
        return '当前阶段产出物存在质量关注项，建议交付前补齐证据或修复可视化。';
    }
    return '当前阶段产出物存在阻断性质量缺口，需要修复后再交付。';
};

export const buildWorkflowQualitySummary = ({
    workflow,
    stageId,
    artifactMarkdown,
    visualDiagnostics,
}: BuildWorkflowQualitySummaryInput): WorkflowQualitySummary => {
    const checks: WorkflowQualityCheck[] = [];
    const actionItems: string[] = [];
    const trimmedArtifact = artifactMarkdown.trim();
    const stage = stageId ? workflow.stages.find(candidate => candidate.id === stageId) : undefined;

    if (!stage) {
        checks.push(makeCheck(
            'stage-context',
            '阶段上下文',
            'fail',
            '无法定位当前 workflow stage。',
            '无法根据阶段 contract 判断产出物质量。'
        ));
        addUniqueActionItem(actionItems, '恢复当前 workflow stage 后重新审阅产出物。');
    }

    if (!trimmedArtifact) {
        checks.push(makeCheck(
            'artifact-content',
            '产出物内容',
            'fail',
            '当前阶段 artifact 为空。',
            '没有可审阅内容，无法判断 headings、visual 和 stage gate。'
        ));
        addUniqueActionItem(actionItems, '生成或恢复当前阶段产出物后再进行质量审阅。');
    } else {
        checks.push(makeCheck(
            'artifact-content',
            '产出物内容',
            'pass',
            `当前 artifact 包含 ${trimmedArtifact.length} 个字符。`,
            '已有可审阅内容。'
        ));
    }

    const requiredHeadings = stage?.artifactContract?.requiredHeadings ?? [];
    if (stage && requiredHeadings.length > 0 && trimmedArtifact) {
        const missingHeadings = requiredHeadings.filter(required => !hasRequiredText(artifactMarkdown, required));
        if (missingHeadings.length > 0) {
            checks.push(makeCheck(
                'artifact-required-headings',
                '必需章节与字段',
                'fail',
                `缺少 ${missingHeadings.length} 个必需项：${missingHeadings.slice(0, 5).join('、')}`,
                '缺失 contract 要求会降低产物完整性，并可能阻断后续 handoff 或导出审阅。'
            ));
            addUniqueActionItem(actionItems, `补齐必需章节或字段：${missingHeadings.slice(0, 3).join('、')}`);
        } else {
            checks.push(makeCheck(
                'artifact-required-headings',
                '必需章节与字段',
                'pass',
                `已覆盖 ${requiredHeadings.length} 个 required headings / fields。`,
                '当前产物满足 manifest 中声明的 artifact contract。'
            ));
        }
    }

    const mermaidBlocks = trimmedArtifact ? extractFencedBlocks(artifactMarkdown, 'mermaid') : [];
    const requiredMermaidDiagrams = stage?.visualContract?.requiredMermaidDiagrams ?? [];
    if (stage && requiredMermaidDiagrams.length > 0 && trimmedArtifact) {
        const missingMermaid = requiredMermaidDiagrams.filter(required => !includesVisualType(mermaidBlocks, required));
        if (missingMermaid.length > 0) {
            checks.push(makeCheck(
                'artifact-mermaid-visuals',
                'Mermaid 可视化',
                'warning',
                `缺少 Mermaid 图：${missingMermaid.join('、')}`,
                '缺少流程、矩阵或结构图会降低审阅可读性。'
            ));
            addUniqueActionItem(actionItems, `补齐可视化：${missingMermaid.join('、')}`);
        } else {
            checks.push(makeCheck(
                'artifact-mermaid-visuals',
                'Mermaid 可视化',
                'pass',
                `已覆盖 ${requiredMermaidDiagrams.length} 个 Mermaid visual contract。`,
                '当前产物满足 Mermaid 可视化要求。'
            ));
        }
    }

    const structuredVisualBlocks = trimmedArtifact ? extractFencedBlocks(artifactMarkdown, 'ai4se-visual') : [];
    const requiredStructuredVisuals = stage?.visualContract?.requiredStructuredVisuals ?? [];
    if (stage && requiredStructuredVisuals.length > 0 && trimmedArtifact) {
        const missingStructuredVisuals = requiredStructuredVisuals.filter(
            required => !includesVisualType(structuredVisualBlocks, required)
        );
        if (missingStructuredVisuals.length > 0) {
            checks.push(makeCheck(
                'artifact-structured-visuals',
                '结构化可视化',
                'warning',
                `缺少 ai4se-visual：${missingStructuredVisuals.join('、')}`,
                '缺少结构化可视化会影响质量状态、风险或追溯矩阵的快速扫描。'
            ));
            addUniqueActionItem(actionItems, `补齐可视化：${missingStructuredVisuals.join('、')}`);
        } else {
            checks.push(makeCheck(
                'artifact-structured-visuals',
                '结构化可视化',
                'pass',
                `已覆盖 ${requiredStructuredVisuals.length} 个 structured visual contract。`,
                '当前产物满足结构化可视化要求。'
            ));
        }
    }

    if (trimmedArtifact) {
        const hasStageGate = /阶段门禁|stage\s*gate|\bgate\b/i.test(artifactMarkdown);
        if (hasStageGate) {
            checks.push(makeCheck(
                'stage-gate',
                '阶段门禁',
                'pass',
                '当前 artifact 包含阶段门禁或 gate 说明。',
                '用户可以判断当前阶段是否满足继续推进条件。'
            ));
        } else {
            checks.push(makeCheck(
                'stage-gate',
                '阶段门禁',
                'warning',
                '当前 artifact 缺少阶段门禁说明。',
                '缺少门禁会让用户难以判断能否进入下一阶段或交付。'
            ));
            addUniqueActionItem(actionItems, '补充阶段门禁、验收条件或继续推进条件。');
        }
    }

    visualDiagnostics
        .filter(diagnostic => diagnostic.stageId === stageId)
        .forEach((diagnostic) => {
            checks.push(makeCheck(
                `visual-diagnostic-${diagnostic.id}`,
                diagnostic.title,
                'warning',
                diagnostic.message,
                '当前阶段存在可视化渲染问题，审阅前需要修复。'
            ));
            addUniqueActionItem(actionItems, `修复当前阶段可视化渲染问题：${diagnostic.message}`);
        });

    const failedCount = checks.filter(check => check.status === 'fail').length;
    const warningCount = checks.filter(check => check.status === 'warning').length;
    const passedCount = checks.filter(check => check.status === 'pass').length;
    const status: WorkflowQualityStatus = failedCount > 0 ? 'fail' : warningCount > 0 ? 'warning' : 'pass';
    const rawScore = Math.max(0, 100 - failedCount * 18 - warningCount * 8);
    const score = trimmedArtifact ? rawScore : Math.min(rawScore, 40);

    return {
        score,
        status,
        statusLabel: STATUS_LABELS[status],
        summary: summarizeQuality(status),
        passedCount,
        warningCount,
        failedCount,
        checks,
        actionItems,
    };
};
