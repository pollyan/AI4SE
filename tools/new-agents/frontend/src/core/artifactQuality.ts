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

export type MissingInfoItem = {
    id: string;
    question: string;
    blocking: boolean;
    owner?: string;
    status?: string;
    nextStep?: string;
};

export type MissingInfoChecklist = {
    summary: {
        total: number;
        blocking: number;
    };
    items: MissingInfoItem[];
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

const MISSING_INFO_HEADING_KEYWORDS = [
    '待澄清',
    '缺失信息',
    '待补充',
    '开放问题',
    'missing_information',
    'missing information',
    'open questions',
    'blocking questions',
];

type MissingInfoSection = {
    heading: string;
    lines: string[];
};

const cleanCell = (value: string | undefined): string => (
    (value || '')
        .replace(/^["'`]+|["'`]+$/g, '')
        .replace(/\s+/g, ' ')
        .trim()
);

const stripEndingPunctuation = (value: string): string => (
    value.replace(/[。；;,.，\s]+$/g, '').trim()
);

const normalizeHeader = (value: string): string => cleanCell(value).toLowerCase().replace(/\s+/g, '');

const isMissingInfoHeading = (heading: string): boolean => {
    const normalizedHeading = heading.toLowerCase();
    return MISSING_INFO_HEADING_KEYWORDS.some(keyword => (
        normalizedHeading.includes(keyword.toLowerCase())
    ));
};

const isBlockingValue = (value: string): boolean => {
    const normalizedValue = value.toLowerCase();
    if (!normalizedValue) return false;
    if (
        normalizedValue.includes('非阻断')
        || normalizedValue.includes('不阻断')
        || normalizedValue.includes('not blocking')
        || normalizedValue.includes('non-blocking')
        || normalizedValue === 'no'
        || normalizedValue === '否'
    ) {
        return false;
    }
    return normalizedValue.includes('阻断') || normalizedValue.includes('blocking') || normalizedValue === 'yes' || normalizedValue === '是';
};

const splitMarkdownTableRow = (line: string): string[] => {
    const trimmedLine = line.trim();
    if (!trimmedLine.startsWith('|') || !trimmedLine.endsWith('|')) return [];
    return trimmedLine.slice(1, -1).split('|').map(cleanCell);
};

const isMarkdownTableSeparator = (line: string): boolean => (
    /^\|?[\s|:-]+\|?$/.test(line.trim()) && line.includes('---')
);

const findColumnIndex = (headers: string[], aliases: string[]): number => (
    headers.findIndex(header => aliases.some(alias => header.includes(alias)))
);

const extractField = (text: string, labels: string[]): string | undefined => {
    for (const label of labels) {
        const match = text.match(new RegExp(`${label}\\s*[:：]\\s*([^；;。\\n]+)`, 'i'));
        if (match?.[1]) return stripEndingPunctuation(cleanCell(match[1]));
    }
    return undefined;
};

const removeInlineFields = (text: string): string => (
    text
        .replace(/责任方\s*[:：]\s*[^；;。]+[；;。]?/gi, '')
        .replace(/owner\s*[:：]\s*[^；;。]+[；;。]?/gi, '')
        .replace(/状态\s*[:：]\s*[^；;。]+[；;。]?/gi, '')
        .replace(/status\s*[:：]\s*[^；;。]+[；;。]?/gi, '')
        .replace(/下一步\s*[:：]\s*[^；;。]+[；;。]?/gi, '')
        .replace(/next step\s*[:：]\s*[^；;。]+[；;。]?/gi, '')
        .replace(/\[(?:阻断|blocking|非阻断|non-blocking)\]/gi, '')
        .replace(/^\((?:阻断|blocking|非阻断|non-blocking)\)\s*/i, '')
        .trim()
);

const collectMissingInfoSections = (content: string): MissingInfoSection[] => {
    const lines = content.replace(/\r\n/g, '\n').split('\n');
    const sections: MissingInfoSection[] = [];
    let currentSection: MissingInfoSection | null = null;

    lines.forEach((line) => {
        const headingMatch = line.match(/^#{1,6}\s+(.+)$/);
        if (headingMatch) {
            if (currentSection) sections.push(currentSection);
            const heading = cleanCell(headingMatch[1]);
            currentSection = isMissingInfoHeading(heading)
                ? { heading, lines: [] }
                : null;
            return;
        }
        if (currentSection) {
            currentSection.lines.push(line);
        }
    });

    if (currentSection) sections.push(currentSection);
    return sections;
};

const buildTableItems = (section: MissingInfoSection, startIndex: number): MissingInfoItem[] => {
    const items: MissingInfoItem[] = [];
    for (let lineIndex = 0; lineIndex < section.lines.length - 1; lineIndex += 1) {
        const headerCells = splitMarkdownTableRow(section.lines[lineIndex]);
        if (headerCells.length === 0 || !isMarkdownTableSeparator(section.lines[lineIndex + 1])) continue;

        const headers = headerCells.map(normalizeHeader);
        const questionIndex = findColumnIndex(headers, ['问题', '事项', '缺口', '缺失信息', '待澄清', '内容', 'description']);
        const blockingIndex = findColumnIndex(headers, ['阻断', 'blocking']);
        const ownerIndex = findColumnIndex(headers, ['责任方', 'owner']);
        const statusIndex = findColumnIndex(headers, ['状态', 'status']);
        const nextStepIndex = findColumnIndex(headers, ['下一步', '行动', '补充动作', 'nextstep']);
        if (questionIndex < 0) continue;

        let rowIndex = lineIndex + 2;
        while (rowIndex < section.lines.length && splitMarkdownTableRow(section.lines[rowIndex]).length > 0) {
            const row = splitMarkdownTableRow(section.lines[rowIndex]);
            const question = stripEndingPunctuation(cleanCell(row[questionIndex]));
            if (question) {
                items.push({
                    id: `missing-info-${startIndex + items.length + 1}`,
                    question,
                    blocking: blockingIndex >= 0 ? isBlockingValue(cleanCell(row[blockingIndex])) : false,
                    owner: ownerIndex >= 0 ? cleanCell(row[ownerIndex]) || undefined : undefined,
                    status: statusIndex >= 0 ? cleanCell(row[statusIndex]) || undefined : undefined,
                    nextStep: nextStepIndex >= 0 ? stripEndingPunctuation(cleanCell(row[nextStepIndex])) || undefined : undefined,
                });
            }
            rowIndex += 1;
        }
    }
    return items;
};

const buildListItems = (section: MissingInfoSection, startIndex: number): MissingInfoItem[] => (
    section.lines.flatMap((line) => {
        const listMatch = line.match(/^\s*(?:[-*+]\s+|\d+\.\s+)(.+)$/);
        if (!listMatch?.[1]) return [];

        const rawText = cleanCell(listMatch[1].replace(/^\[[ x-]\]\s*/i, ''));
        const question = stripEndingPunctuation(removeInlineFields(rawText).split(/[；;]/)[0] || '');
        if (!question) return [];

        return [{
            id: `missing-info-${startIndex + 1}`,
            question,
            blocking: isBlockingValue(rawText),
            owner: extractField(rawText, ['责任方', 'owner']),
            status: extractField(rawText, ['状态', 'status']),
            nextStep: extractField(rawText, ['下一步', 'next step']),
        }];
    })
);

export const buildMissingInfoChecklist = (artifactContent: string): MissingInfoChecklist | null => {
    const content = artifactContent.trim();
    if (!content) return null;

    const items = collectMissingInfoSections(content).reduce<MissingInfoItem[]>((accumulator, section) => {
        const tableItems = buildTableItems(section, accumulator.length);
        if (tableItems.length > 0) return [...accumulator, ...tableItems];
        const listItems = buildListItems(section, accumulator.length);
        return [...accumulator, ...listItems.map((item, index) => ({
            ...item,
            id: `missing-info-${accumulator.length + index + 1}`,
        }))];
    }, []);

    if (items.length === 0) return null;

    return {
        summary: {
            total: items.length,
            blocking: items.filter(item => item.blocking).length,
        },
        items,
    };
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
