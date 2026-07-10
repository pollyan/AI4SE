import type { ArtifactComment, ArtifactSectionLock } from './types';

type UpdateCollaboration = (
    runId: string,
    comments: ArtifactComment[],
    sectionLocks: ArtifactSectionLock[],
) => Promise<unknown>;

type SyncArtifactCollaborationInput = {
    runId: string | null;
    comments: ArtifactComment[];
    sectionLocks: ArtifactSectionLock[];
    updateCollaboration: UpdateCollaboration;
};

export const syncArtifactCollaboration = async ({
    runId,
    comments,
    sectionLocks,
    updateCollaboration,
}: SyncArtifactCollaborationInput): Promise<string | null> => {
    if (!runId) return null;

    try {
        await updateCollaboration(runId, comments, sectionLocks);
        return null;
    } catch (error) {
        const message = error instanceof Error ? error.message : '未知错误';
        return `协作状态保存失败：${message}`;
    }
};
