import type { ArtifactCommentInput } from './types';

type BuildArtifactCommentInput = {
    stageId: string;
    draft: string;
    artifactContent: string;
    selectedAnchor: string | null;
};

const isFenceStart = (line: string): boolean => /^```/.test(line.trim());
const isHeading = (line: string): boolean => /^#{1,3}\s+/.test(line);

const stripInlineMarkdown = (content: string): string => (
    content
        .replace(/`([^`]+)`/g, '$1')
        .replace(/\*\*([^*]+)\*\*/g, '$1')
        .replace(/\*([^*]+)\*/g, '$1')
        .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
        .trim()
);

export const normalizeArtifactCommentAnchor = (value: string): string | null => {
    const normalizedValue = value.replace(/\s+/g, ' ').trim();
    if (!normalizedValue) return null;
    return normalizedValue.length > 120
        ? `${normalizedValue.slice(0, 117)}...`
        : normalizedValue;
};

export const buildArtifactCommentExcerpt = (content: string): string => {
    const lines = content.split(/\r?\n/);
    const firstBodyLine = lines.find((line) => {
        const trimmedLine = line.trim();
        return trimmedLine && !isHeading(trimmedLine) && !isFenceStart(trimmedLine);
    }) || lines.find(line => line.trim()) || '当前产出物';
    const excerpt = stripInlineMarkdown(firstBodyLine.replace(/^\s*[-*]\s+/, ''));
    return excerpt.length > 120 ? `${excerpt.slice(0, 117)}...` : excerpt;
};

export const buildArtifactCommentInput = ({
    stageId,
    draft,
    artifactContent,
    selectedAnchor,
}: BuildArtifactCommentInput): ArtifactCommentInput | null => {
    const content = draft.trim();
    if (!content) return null;
    const anchorText = normalizeArtifactCommentAnchor(selectedAnchor ?? '');
    return {
        stageId,
        content,
        artifactExcerpt: anchorText ?? buildArtifactCommentExcerpt(artifactContent),
        anchorText,
    };
};

export const getArtifactCommentAnchorStatus = (
    anchorText: string | null,
    artifactContent: string,
): 'none' | 'active' | 'stale' => {
    const normalizedAnchorText = normalizeArtifactCommentAnchor(anchorText ?? '');
    if (!normalizedAnchorText) return 'none';
    const normalizedArtifactContent = artifactContent.replace(/\s+/g, ' ');
    return normalizedArtifactContent.includes(normalizedAnchorText) ? 'active' : 'stale';
};
