import type {
    ArtifactSectionPatch,
    ArtifactVersion,
    Attachment,
    Message,
    PendingStageTransition,
} from './types';


export type AgentStreamChunk = {
    chatResponse: string;
    newArtifact: string;
    action: string;
    hasArtifactUpdate: boolean;
    artifactTruncated?: boolean;
    artifactPatch?: ArtifactSectionPatch;
};

export type AgentStreamContext = {
    stageIndex: number;
    stageCount: number;
    currentStageId: string;
    hasTransitioned: boolean;
};

export type AgentArtifactUpdateDecision = {
    stageId: string;
    content: string;
    patch?: ArtifactSectionPatch;
};

export type AgentStreamDecision = {
    assistantContent: string;
    artifactTruncated: boolean;
    artifactUpdate?: AgentArtifactUpdateDecision;
    pendingStageTransition?: PendingStageTransition;
    hasTransitioned: boolean;
    shouldStopStream: boolean;
};

export type AgentRetryPlan = {
    retryInput: string;
    retryAttachments: Attachment[];
    messagesToRemove: number;
};

export type AgentArtifactVersionUpdatePlan = {
    content: string;
};

export type AgentWorkflowStageSummary = {
    id: string;
    name: string;
};

export type AgentStageTransitionConfirmationInput = {
    pendingTransition: PendingStageTransition | null;
    stageIndex: number;
    stages: AgentWorkflowStageSummary[];
    artifactContent: string;
    stageArtifacts: Record<string, string>;
};

export type AgentStageTransitionConfirmationPlan = {
    pendingStageTransition: null;
    stageIndex?: number;
    stageArtifacts?: Record<string, string>;
    artifactContent?: string;
    artifactTruncated?: boolean;
};

const normalizeRetryAttachments = (attachments: unknown): Attachment[] => (
    Array.isArray(attachments) ? attachments : []
);

export function reduceAgentStreamChunk(
    chunk: AgentStreamChunk,
    context: AgentStreamContext
): AgentStreamDecision {
    const shouldRequestNextStage =
        chunk.action === 'NEXT_STAGE'
        && !context.hasTransitioned
        && context.stageIndex < context.stageCount - 1;

    if (shouldRequestNextStage) {
        return {
            assistantContent: chunk.chatResponse,
            artifactTruncated: chunk.artifactTruncated === true,
            artifactUpdate: chunk.hasArtifactUpdate
                ? {
                    stageId: context.currentStageId,
                    content: chunk.newArtifact,
                    ...(chunk.artifactPatch ? { patch: chunk.artifactPatch } : {}),
                }
                : undefined,
            pendingStageTransition: {
                fromStageIndex: context.stageIndex,
                toStageIndex: context.stageIndex + 1,
            },
            hasTransitioned: true,
            shouldStopStream: true,
        };
    }

    return {
        assistantContent: chunk.chatResponse,
        artifactTruncated: chunk.artifactTruncated === true,
        artifactUpdate: chunk.hasArtifactUpdate
            ? {
                stageId: context.currentStageId,
                content: chunk.newArtifact,
                ...(chunk.artifactPatch ? { patch: chunk.artifactPatch } : {}),
            }
            : undefined,
        hasTransitioned: context.hasTransitioned,
        shouldStopStream: false,
    };
}

export function planRetryFromHistory(history: Message[]): AgentRetryPlan | null {
    const latestMessage = history[history.length - 1];
    if (latestMessage?.role === 'assistant' && latestMessage.retryable === false) {
        return null;
    }

    let lastUserMessageIndex = -1;
    for (let i = history.length - 1; i >= 0; i -= 1) {
        if (history[i].role === 'user') {
            lastUserMessageIndex = i;
            break;
        }
    }

    if (lastUserMessageIndex === -1) return null;

    const lastUserMessage = history[lastUserMessageIndex];
    return {
        retryInput: lastUserMessage.content,
        retryAttachments: normalizeRetryAttachments(lastUserMessage.attachments),
        messagesToRemove: history.length - lastUserMessageIndex,
    };
}

export function planArtifactVersionUpdate(
    finalArtifact: string,
    history: ArtifactVersion[]
): AgentArtifactVersionUpdatePlan | null {
    if (!finalArtifact) return null;
    if (finalArtifact.startsWith('# 欢迎使用')) return null;

    const latestVersion = history[history.length - 1];
    if (latestVersion?.content === finalArtifact) return null;

    return {
        content: finalArtifact,
    };
}

export function planStageTransitionConfirmation(
    input: AgentStageTransitionConfirmationInput
): AgentStageTransitionConfirmationPlan | null {
    const pendingTransition = input.pendingTransition;
    if (!pendingTransition) return null;

    if (input.stageIndex !== pendingTransition.fromStageIndex) {
        return {
            pendingStageTransition: null,
        };
    }

    if (pendingTransition.toStageIndex !== pendingTransition.fromStageIndex + 1) {
        return {
            pendingStageTransition: null,
        };
    }

    const targetStage = input.stages[pendingTransition.toStageIndex];
    if (!targetStage) {
        return {
            pendingStageTransition: null,
        };
    }

    const stageArtifacts = { ...input.stageArtifacts };
    const sourceStage = input.stages[pendingTransition.fromStageIndex];
    if (sourceStage) {
        stageArtifacts[sourceStage.id] = input.artifactContent;
    }

    return {
        pendingStageTransition: null,
        stageIndex: pendingTransition.toStageIndex,
        stageArtifacts,
        artifactContent: stageArtifacts[targetStage.id] || `# ${targetStage.name}\n\n暂无产出物。`,
        artifactTruncated: false,
    };
}
