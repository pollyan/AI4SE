import type { LineDiffEntry } from './artifactDiff';

export type ContiguousDiffBlock = {
    startIndex: number;
    lines: string[];
    label: string;
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
