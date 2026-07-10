import type { AgentRunSnapshotArtifact, ArtifactVersion } from './types';

type UpdateArtifactHistoryContentInput = {
    operation: 'restore' | 'discard';
    currentContent: string;
    historicalContent: string;
    lines: string[];
};

type BuildConflictRefreshHistoryInput = {
    currentRunId: string | null;
    currentStageId: string;
    artifactContent: string;
    latestVersionContent: string | undefined;
    draftContent: string;
    serverArtifact: AgentRunSnapshotArtifact;
    timestamp: number;
};

const splitArtifactLines = (content: string): string[] => (
    content.replace(/\r\n/g, '\n').split('\n')
);

export const updateArtifactHistoryContent = ({
    operation,
    currentContent,
    historicalContent,
    lines,
}: UpdateArtifactHistoryContentInput): string => {
    const nonEmptyLines = lines.filter(line => line.trim());
    if (nonEmptyLines.length === 0) return currentContent;

    const currentLines = splitArtifactLines(currentContent);
    if (operation === 'discard') {
        const nextLines = [...currentLines];
        nonEmptyLines.forEach((lineContent) => {
            const lineIndex = nextLines.findIndex(line => line === lineContent);
            if (lineIndex >= 0) nextLines.splice(lineIndex, 1);
        });
        return nextLines.join('\n');
    }

    const linesToRestore = nonEmptyLines.filter(line => !currentLines.includes(line));
    if (linesToRestore.length === 0) return currentContent;

    const historicalLines = splitArtifactLines(historicalContent);
    const historicalLineIndex = historicalLines.findIndex(line => line === nonEmptyLines[0]);
    if (historicalLineIndex < 0) return currentContent;

    const insertIndex = Math.min(historicalLineIndex, currentLines.length);
    return [
        ...currentLines.slice(0, insertIndex),
        ...linesToRestore,
        ...currentLines.slice(insertIndex),
    ].join('\n');
};

export const buildConflictRefreshHistory = ({
    currentRunId,
    currentStageId,
    artifactContent,
    latestVersionContent,
    draftContent,
    serverArtifact,
    timestamp,
}: BuildConflictRefreshHistoryInput): { content: string; versions: ArtifactVersion[] } => {
    const versions: ArtifactVersion[] = [];
    if (latestVersionContent !== artifactContent) {
        versions.push({
            id: `conflict-local-backup-${timestamp}`,
            timestamp,
            content: artifactContent,
            stageId: currentStageId,
        });
    }
    versions.push(
        {
            id: `conflict-draft-${timestamp}`,
            timestamp: timestamp + 1,
            content: draftContent,
            stageId: currentStageId,
        },
        {
            id: currentRunId
                ? `${currentRunId}-${serverArtifact.stageId}-v${serverArtifact.versionNumber}`
                : `conflict-server-${timestamp}`,
            timestamp: timestamp + 2,
            content: serverArtifact.content,
            stageId: currentStageId,
        },
    );
    return {
        content: serverArtifact.content,
        versions,
    };
};
