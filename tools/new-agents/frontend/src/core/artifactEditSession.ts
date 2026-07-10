import type {
    AgentRunSnapshotArtifact,
    ArtifactSectionLock,
    ArtifactVersion,
} from './types';
import { findLockedSectionChange } from './artifactLocking';
import { ArtifactConflictError, updateRunArtifact } from '../services/runSnapshotService';

type UpdateArtifact = typeof updateRunArtifact;

type SaveArtifactEditSessionInput = {
    currentRunId: string | null;
    currentStageId: string;
    artifactContent: string;
    editDraft: string;
    locks: ArtifactSectionLock[];
    latestStageVersion: ArtifactVersion | null;
    updateArtifact: UpdateArtifact;
};

export type SaveArtifactEditSessionResult =
    | { type: 'unchanged' }
    | { type: 'locked'; sectionTitle: string }
    | { type: 'saved'; content: string; versionId: string | null }
    | { type: 'conflict'; artifact: AgentRunSnapshotArtifact; message: string }
    | { type: 'error'; message: string };

const inferCurrentServerVersionNumber = (
    currentRunId: string | null,
    currentStageId: string,
    artifactContent: string,
    latestStageVersion: ArtifactVersion | null,
): number | undefined => {
    if (!currentRunId || !latestStageVersion || latestStageVersion.content !== artifactContent) {
        return undefined;
    }
    const expectedPrefix = `${currentRunId}-${currentStageId}-v`;
    if (!latestStageVersion.id.startsWith(expectedPrefix)) {
        return undefined;
    }
    const versionNumber = Number.parseInt(
        latestStageVersion.id.slice(expectedPrefix.length),
        10,
    );
    return Number.isInteger(versionNumber) ? versionNumber : undefined;
};

export const saveArtifactEditSession = ({
    currentRunId,
    currentStageId,
    artifactContent,
    editDraft,
    locks,
    latestStageVersion,
    updateArtifact,
}: SaveArtifactEditSessionInput): SaveArtifactEditSessionResult | Promise<SaveArtifactEditSessionResult> => {
    if (editDraft === artifactContent) return { type: 'unchanged' };

    const lockedSection = findLockedSectionChange({
        currentContent: artifactContent,
        nextContent: editDraft,
        locks,
    });
    if (lockedSection) return { type: 'locked', sectionTitle: lockedSection };

    if (!currentRunId) {
        return { type: 'saved', content: editDraft, versionId: null };
    }

    return updateArtifact(
            currentRunId,
            currentStageId,
            editDraft,
            {
                expectedVersionNumber: inferCurrentServerVersionNumber(
                    currentRunId,
                    currentStageId,
                    artifactContent,
                    latestStageVersion,
                ),
            },
        )
        .then((savedArtifact): SaveArtifactEditSessionResult => ({
            type: 'saved',
            content: savedArtifact.content,
            versionId: `${currentRunId}-${savedArtifact.stageId}-v${savedArtifact.versionNumber}`,
        }))
        .catch((error): SaveArtifactEditSessionResult => {
        if (error instanceof ArtifactConflictError) {
            return { type: 'conflict', artifact: error.currentArtifact, message: error.message };
        }
        return {
            type: 'error',
            message: error instanceof Error ? error.message : '未知错误',
        };
    });
};
