import type {
    ArtifactVisualDiagnosticInput,
    ArtifactVisualDiagnosticKind,
} from './types';

type BuildArtifactVisualDiagnosticInput = {
    stageId: string;
    kind: ArtifactVisualDiagnosticKind;
    blockIndex: number;
    message: string;
};

const diagnosticTitles: Record<ArtifactVisualDiagnosticKind, string> = {
    mermaid: 'Mermaid 图表渲染失败',
    'structured-visual': '结构化可视化格式错误',
};

const diagnosticFallbackMessages: Record<ArtifactVisualDiagnosticKind, string> = {
    mermaid: '右侧 Mermaid 图表暂时无法渲染。',
    'structured-visual': '结构化可视化暂时无法校验。',
};

export const buildArtifactVisualDiagnosticId = (
    stageId: string | undefined,
    kind: ArtifactVisualDiagnosticKind,
    blockIndex: number,
): string => `${kind}:${stageId || 'unknown'}:${blockIndex}`;

export const buildArtifactVisualDiagnostic = ({
    stageId,
    kind,
    blockIndex,
    message,
}: BuildArtifactVisualDiagnosticInput): ArtifactVisualDiagnosticInput => ({
    id: buildArtifactVisualDiagnosticId(stageId, kind, blockIndex),
    stageId,
    kind,
    title: diagnosticTitles[kind],
    message: message || diagnosticFallbackMessages[kind],
    blockIndex,
});

export const getArtifactVisualDiagnosticContainerClass = (
    diagnosticId: string,
    activeDiagnosticId: string | null,
): string => (
    `my-6 rounded-xl transition-shadow ${activeDiagnosticId === diagnosticId
        ? 'ring-2 ring-amber-300/70 shadow-[0_0_0_4px_rgba(252,211,77,0.12)]'
        : 'ring-1 ring-transparent'}`
);
