import type { ArtifactVisualDiagnostic, WorkflowType } from './types';

export type ArtifactQualityStatus = 'pass' | 'warning' | 'fail';

export type ArtifactQualityItem = {
    id: string;
    title: string;
    message: string;
    status: ArtifactQualityStatus;
};

export type ArtifactQualityGroup = {
    id: 'contract' | 'visual' | 'stage-gate' | 'runtime';
    title: string;
    items: ArtifactQualityItem[];
};

export type ArtifactQualityDiagnostics = {
    status: ArtifactQualityStatus;
    summary: {
        passed: number;
        warning: number;
        failed: number;
    };
    groups: ArtifactQualityGroup[];
};

type BuildArtifactQualityDiagnosticsInput = {
    workflow: WorkflowType;
    stageId: string;
    artifactContent: string;
    visualDiagnostics: ArtifactVisualDiagnostic[];
};

const PROFESSIONAL_GATE_KEYWORDS = [
    '阶段门禁',
    '验收',
    '风险',
    '开放问题',
    '待澄清',
    'handoff',
    'checklist',
];

const hasMarkdownHeading = (content: string): boolean => /^#\s+\S/m.test(content);

const hasMarkdownSubheading = (content: string): boolean => /^##\s+\S/m.test(content);

const hasMermaidFence = (content: string): boolean => /```mermaid\b/i.test(content);

const hasStructuredVisualFence = (content: string): boolean => /```ai4se-visual\b/i.test(content);

const hasProfessionalGateKeyword = (content: string): boolean => {
    const lowerContent = content.toLowerCase();
    return PROFESSIONAL_GATE_KEYWORDS.some(keyword => lowerContent.includes(keyword.toLowerCase()));
};

const buildItem = (
    id: string,
    title: string,
    message: string,
    status: ArtifactQualityStatus
): ArtifactQualityItem => ({
    id,
    title,
    message,
    status,
});

const deriveStatus = (items: ArtifactQualityItem[]): ArtifactQualityStatus => {
    if (items.some(item => item.status === 'fail')) return 'fail';
    if (items.some(item => item.status === 'warning')) return 'warning';
    return 'pass';
};

export const buildArtifactQualityDiagnostics = ({
    workflow,
    stageId,
    artifactContent,
    visualDiagnostics,
}: BuildArtifactQualityDiagnosticsInput): ArtifactQualityDiagnostics | null => {
    const content = artifactContent.trim();
    if (!content) return null;

    const currentStageVisualDiagnostics = visualDiagnostics.filter(
        diagnostic => diagnostic.stageId === stageId
    );

    const groups: ArtifactQualityGroup[] = [
        {
            id: 'contract',
            title: 'Artifact Contract',
            items: [
                hasMarkdownHeading(content) && hasMarkdownSubheading(content)
                    ? buildItem(
                        `${workflow}:${stageId}:headings`,
                        '必需标题',
                        '已包含 H1 和 H2 标题结构。',
                        'pass'
                    )
                    : buildItem(
                        `${workflow}:${stageId}:headings`,
                        '必需标题',
                        '缺少 H1 或 H2 标题，当前产物可能无法满足阶段 artifact contract。',
                        'fail'
                    ),
            ],
        },
        {
            id: 'visual',
            title: '可视化 Contract',
            items: [
                hasMermaidFence(content) && hasStructuredVisualFence(content)
                    ? buildItem(
                        `${workflow}:${stageId}:visuals`,
                        '必需可视化',
                        '已包含 Mermaid 和 ai4se-visual 可视化块。',
                        'pass'
                    )
                    : buildItem(
                        `${workflow}:${stageId}:visuals`,
                        '必需可视化',
                        '缺少 Mermaid 或 ai4se-visual 可视化块。',
                        'fail'
                    ),
            ],
        },
        {
            id: 'stage-gate',
            title: '阶段门禁',
            items: [
                hasProfessionalGateKeyword(content)
                    ? buildItem(
                        `${workflow}:${stageId}:stage-gate`,
                        '专业门禁',
                        '已包含阶段门禁、风险、验收、开放问题或 handoff 等专业字段。',
                        'pass'
                    )
                    : buildItem(
                        `${workflow}:${stageId}:stage-gate`,
                        '专业门禁',
                        '缺少阶段门禁、风险、验收、开放问题或 handoff 等专业字段。',
                        'fail'
                    ),
            ],
        },
    ];

    if (currentStageVisualDiagnostics.length > 0) {
        groups.push({
            id: 'runtime',
            title: '运行时诊断',
            items: currentStageVisualDiagnostics.map(diagnostic => buildItem(
                diagnostic.id,
                '可视化运行时警告',
                diagnostic.message,
                'warning'
            )),
        });
    }

    const items = groups.flatMap(group => group.items);
    return {
        status: deriveStatus(items),
        summary: {
            passed: items.filter(item => item.status === 'pass').length,
            warning: items.filter(item => item.status === 'warning').length,
            failed: items.filter(item => item.status === 'fail').length,
        },
        groups,
    };
};
