import type { LineDiffEntry } from './artifactDiff';

export type ContiguousDiffBlock = {
    startIndex: number;
    lines: string[];
    label: string;
};

export type AutoMergedConflictResult = {
    content: string;
    summary: string;
};

export function truncateAuditLine(lineContent: string): string {
    const normalizedLine = lineContent.replace(/\s+/g, ' ').trim();
    return normalizedLine.length > 60
        ? `${normalizedLine.slice(0, 57)}...`
        : normalizedLine;
}

export function buildConflictMergeBlockLabel(lineContents: string[]): string {
    return lineContents.map(truncateAuditLine).join(' / ');
}

export function buildConflictModificationBlockLabel(
    removedLines: string[],
    addedLines: string[]
): string {
    return `${buildConflictMergeBlockLabel(removedLines)} → ${buildConflictMergeBlockLabel(addedLines)}`;
}

export function buildContiguousDiffBlocks(
    diff: LineDiffEntry[],
    type: Extract<LineDiffEntry['type'], 'added' | 'removed'>
): ContiguousDiffBlock[] {
    const blocks: ContiguousDiffBlock[] = [];
    let blockStartIndex: number | null = null;
    let blockLines: string[] = [];

    const flushBlock = () => {
        if (blockStartIndex !== null && blockLines.length > 1) {
            blocks.push({
                startIndex: blockStartIndex,
                lines: blockLines,
                label: buildConflictMergeBlockLabel(blockLines),
            });
        }
        blockStartIndex = null;
        blockLines = [];
    };

    diff.forEach((line, index) => {
        if (line.type === type && line.content.trim()) {
            if (blockStartIndex === null) {
                blockStartIndex = index;
            }
            blockLines.push(line.content);
            return;
        }
        flushBlock();
    });
    flushBlock();

    return blocks;
}

export function replaceFirstLineSequence(
    sourceLines: string[],
    targetLines: string[],
    replacementLines: string[]
): string[] {
    const normalizedTargetLines = targetLines.filter(line => line.trim());
    if (normalizedTargetLines.length === 0) return sourceLines;

    const startIndex = sourceLines.findIndex((_, index) => (
        normalizedTargetLines.every((targetLine, offset) => sourceLines[index + offset] === targetLine)
    ));
    if (startIndex < 0) return sourceLines;

    return [
        ...sourceLines.slice(0, startIndex),
        ...replacementLines.filter(line => line.trim()),
        ...sourceLines.slice(startIndex + normalizedTargetLines.length),
    ];
}

function collectInsertionSegments(
    baseLines: string[],
    targetLines: string[]
): string[][] | null {
    const segments = Array.from({ length: baseLines.length + 1 }, () => [] as string[]);
    let targetIndex = 0;

    for (let baseIndex = 0; baseIndex < baseLines.length; baseIndex += 1) {
        while (targetIndex < targetLines.length && targetLines[targetIndex] !== baseLines[baseIndex]) {
            segments[baseIndex].push(targetLines[targetIndex]);
            targetIndex += 1;
        }
        if (targetIndex >= targetLines.length) {
            return null;
        }
        targetIndex += 1;
    }

    segments[baseLines.length].push(...targetLines.slice(targetIndex));
    return segments;
}

function collectDraftInsertionSegments(
    baseLines: string[],
    draftLines: string[]
): {
    segments: string[][];
    retainedBaseLineIndexes: Set<number>;
    hasDraftDeletion: boolean;
} | null {
    const segments = Array.from({ length: baseLines.length + 1 }, () => [] as string[]);
    const retainedBaseLineIndexes = new Set<number>();
    const pendingInsertions: string[] = [];
    let baseIndex = 0;

    const flushPendingInsertions = (segmentIndex: number) => {
        if (pendingInsertions.length === 0) return;
        segments[segmentIndex].push(...pendingInsertions);
        pendingInsertions.length = 0;
    };

    for (const draftLine of draftLines) {
        if (baseIndex >= baseLines.length) {
            if (baseLines.includes(draftLine)) return null;
            pendingInsertions.push(draftLine);
            continue;
        }

        if (draftLine === baseLines[baseIndex]) {
            flushPendingInsertions(baseIndex);
            retainedBaseLineIndexes.add(baseIndex);
            baseIndex += 1;
            continue;
        }

        const futureMatchIndex = baseLines.findIndex((baseLine, index) => (
            index > baseIndex && baseLine === draftLine
        ));
        if (futureMatchIndex >= 0) {
            flushPendingInsertions(futureMatchIndex);
            retainedBaseLineIndexes.add(futureMatchIndex);
            baseIndex = futureMatchIndex + 1;
            continue;
        }

        if (baseLines.includes(draftLine)) return null;
        pendingInsertions.push(draftLine);
    }

    flushPendingInsertions(baseLines.length);
    return {
        segments,
        retainedBaseLineIndexes,
        hasDraftDeletion: retainedBaseLineIndexes.size < baseLines.length,
    };
}

function mergeUniqueInsertions(primaryLines: string[], secondaryLines: string[]): string[] {
    const mergedLines = [...primaryLines];
    secondaryLines.forEach((line) => {
        if (!mergedLines.includes(line)) {
            mergedLines.push(line);
        }
    });
    return mergedLines;
}

function hasRepeatedNonBlankLines(lines: string[]): boolean {
    const seenLines = new Set<string>();
    return lines.some((line) => {
        if (!line.trim()) return false;
        if (seenLines.has(line)) return true;
        seenLines.add(line);
        return false;
    });
}

function buildAutoMergedInsertionContent(
    baseContent: string,
    serverContent: string,
    draftContent: string
): string | null {
    const baseLines = baseContent.replace(/\r\n/g, '\n').split('\n');
    const serverLines = serverContent.replace(/\r\n/g, '\n').split('\n');
    const draftLines = draftContent.replace(/\r\n/g, '\n').split('\n');
    const serverSegments = collectInsertionSegments(baseLines, serverLines);
    const draftMerge = collectDraftInsertionSegments(baseLines, draftLines);
    if (!serverSegments || !draftMerge) return null;
    if (draftMerge.hasDraftDeletion && hasRepeatedNonBlankLines(baseLines)) return null;

    const mergedLines: string[] = [];
    let appliedDraftChange = draftMerge.hasDraftDeletion;
    for (let segmentIndex = 0; segmentIndex < serverSegments.length; segmentIndex += 1) {
        const draftInsertions = draftMerge.segments[segmentIndex];
        const mergedInsertions = mergeUniqueInsertions(serverSegments[segmentIndex], draftInsertions);
        if (draftInsertions.some(line => !serverSegments[segmentIndex].includes(line))) {
            appliedDraftChange = true;
        }
        mergedLines.push(...mergedInsertions);
        if (segmentIndex < baseLines.length && draftMerge.retainedBaseLineIndexes.has(segmentIndex)) {
            mergedLines.push(baseLines[segmentIndex]);
        }
    }

    const mergedContent = mergedLines.join('\n');
    if (!appliedDraftChange || mergedContent === serverContent.replace(/\r\n/g, '\n')) {
        return null;
    }
    return mergedContent;
}

export function buildAutoMergedInsertionResult(
    baseContent: string,
    serverContent: string,
    draftContent: string
): AutoMergedConflictResult | null {
    const content = buildAutoMergedInsertionContent(baseContent, serverContent, draftContent);
    return content
        ? {
            content,
            summary: '合并轨迹：自动合并服务端与草稿的非重叠补充',
        }
        : null;
}
