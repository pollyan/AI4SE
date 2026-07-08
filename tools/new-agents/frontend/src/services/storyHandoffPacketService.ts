import {
    StoryHandoffCandidate,
    StoryHandoffCandidateResponse,
    StoryHandoffPacket,
    StoryHandoffPacketListItem,
    StoryHandoffPacketListResponse,
    WorkflowType,
} from '../core/types';
import { WORKFLOWS } from '../core/workflows';

const INVALID_RESPONSE = 'Invalid story handoff packet response';

const isRecord = (value: unknown): value is Record<string, unknown> => (
    typeof value === 'object' && value !== null
);

const isWorkflowType = (value: unknown): value is WorkflowType => (
    typeof value === 'string'
    && Object.prototype.hasOwnProperty.call(WORKFLOWS, value)
);

const parseStringArray = (value: unknown): string[] => {
    if (!Array.isArray(value) || value.some(item => typeof item !== 'string')) {
        throw new Error(INVALID_RESPONSE);
    }
    return value;
};

const parseInteger = (value: unknown): number => {
    if (typeof value !== 'number' || !Number.isInteger(value)) {
        throw new Error(INVALID_RESPONSE);
    }
    return value;
};

const parseCandidate = (candidate: unknown): StoryHandoffCandidate => {
    if (
        !isRecord(candidate)
        || typeof candidate.storyId !== 'string'
        || typeof candidate.title !== 'string'
        || typeof candidate.userValue !== 'string'
        || typeof candidate.readyReason !== 'string'
    ) {
        throw new Error(INVALID_RESPONSE);
    }
    return {
        storyId: candidate.storyId,
        title: candidate.title,
        requirementIds: parseStringArray(candidate.requirementIds),
        userValue: candidate.userValue,
        readyReason: candidate.readyReason,
    };
};

const parsePacket = (packet: unknown): StoryHandoffPacket => {
    if (
        !isRecord(packet)
        || typeof packet.sourceRunId !== 'string'
        || !isWorkflowType(packet.sourceWorkflowId)
        || typeof packet.sourceStageId !== 'string'
        || typeof packet.sourceArtifactDigest !== 'string'
        || typeof packet.storyId !== 'string'
        || typeof packet.userStory !== 'string'
    ) {
        throw new Error(INVALID_RESPONSE);
    }
    return {
        sourceRunId: packet.sourceRunId,
        sourceWorkflowId: packet.sourceWorkflowId,
        sourceStageId: packet.sourceStageId,
        sourceArtifactVersion: parseInteger(packet.sourceArtifactVersion),
        sourceArtifactDigest: packet.sourceArtifactDigest,
        createdAt: parseInteger(packet.createdAt),
        storyId: packet.storyId,
        requirementIds: parseStringArray(packet.requirementIds),
        userStory: packet.userStory,
        acceptanceCriteria: parseStringArray(packet.acceptanceCriteria),
        businessRules: parseStringArray(packet.businessRules),
        nonFunctionalNotes: parseStringArray(packet.nonFunctionalNotes),
        outOfScope: parseStringArray(packet.outOfScope),
        dependencies: parseStringArray(packet.dependencies),
        openQuestions: parseStringArray(packet.openQuestions),
    };
};

const parsePacketItem = (item: unknown): StoryHandoffPacketListItem => {
    if (
        !isRecord(item)
        || typeof item.id !== 'string'
        || typeof item.storyId !== 'string'
        || typeof item.isStale !== 'boolean'
        || typeof item.currentSourceArtifactDigest !== 'string'
    ) {
        throw new Error(INVALID_RESPONSE);
    }
    return {
        id: item.id,
        storyId: item.storyId,
        createdAt: parseInteger(item.createdAt),
        isStale: item.isStale,
        currentSourceArtifactVersion: parseInteger(item.currentSourceArtifactVersion),
        currentSourceArtifactDigest: item.currentSourceArtifactDigest,
        packet: parsePacket(item.packet),
    };
};

const parseCandidateResponse = (payload: unknown): StoryHandoffCandidateResponse => {
    if (
        !isRecord(payload)
        || typeof payload.runId !== 'string'
        || !isWorkflowType(payload.workflowId)
        || typeof payload.stageId !== 'string'
        || typeof payload.sourceArtifactDigest !== 'string'
        || !Array.isArray(payload.candidates)
    ) {
        throw new Error(INVALID_RESPONSE);
    }
    return {
        runId: payload.runId,
        workflowId: payload.workflowId,
        stageId: payload.stageId,
        sourceArtifactVersion: parseInteger(payload.sourceArtifactVersion),
        sourceArtifactDigest: payload.sourceArtifactDigest,
        candidates: payload.candidates.map(parseCandidate),
    };
};

const parsePacketListResponse = (payload: unknown): StoryHandoffPacketListResponse => {
    if (
        !isRecord(payload)
        || typeof payload.runId !== 'string'
        || !isWorkflowType(payload.workflowId)
        || typeof payload.stageId !== 'string'
        || typeof payload.sourceArtifactDigest !== 'string'
        || !Array.isArray(payload.packets)
    ) {
        throw new Error(INVALID_RESPONSE);
    }
    return {
        runId: payload.runId,
        workflowId: payload.workflowId,
        stageId: payload.stageId,
        sourceArtifactVersion: parseInteger(payload.sourceArtifactVersion),
        sourceArtifactDigest: payload.sourceArtifactDigest,
        packets: payload.packets.map(parsePacketItem),
    };
};

export const fetchStoryHandoffCandidates = async (
    runId: string,
    stageId: string,
): Promise<StoryHandoffCandidateResponse> => {
    const normalizedRunId = runId.trim();
    const normalizedStageId = stageId.trim();
    if (!normalizedRunId || !normalizedStageId) {
        throw new Error('runId and stageId are required');
    }

    const params = new URLSearchParams();
    params.set('stageId', normalizedStageId);
    const response = await fetch(
        `/new-agents/api/agent/runs/${encodeURIComponent(normalizedRunId)}/story-handoff-candidates?${params.toString()}`
    );
    if (!response.ok) {
        throw new Error(`Failed to fetch story handoff candidates: ${response.status}`);
    }
    return parseCandidateResponse(await response.json());
};

export const fetchStoryHandoffPackets = async (
    runId: string,
    stageId: string,
): Promise<StoryHandoffPacketListResponse> => {
    const normalizedRunId = runId.trim();
    const normalizedStageId = stageId.trim();
    if (!normalizedRunId || !normalizedStageId) {
        throw new Error('runId and stageId are required');
    }

    const params = new URLSearchParams();
    params.set('stageId', normalizedStageId);
    const response = await fetch(
        `/new-agents/api/agent/runs/${encodeURIComponent(normalizedRunId)}/story-handoff-packets?${params.toString()}`
    );
    if (!response.ok) {
        throw new Error(`Failed to fetch story handoff packets: ${response.status}`);
    }
    return parsePacketListResponse(await response.json());
};

export const createStoryHandoffPacket = async (
    runId: string,
    stageId: string,
    storyId: string,
): Promise<StoryHandoffPacket> => {
    const normalizedRunId = runId.trim();
    const normalizedStageId = stageId.trim();
    const normalizedStoryId = storyId.trim();
    if (!normalizedRunId || !normalizedStageId || !normalizedStoryId) {
        throw new Error('runId, stageId and storyId are required');
    }

    const response = await fetch(
        `/new-agents/api/agent/runs/${encodeURIComponent(normalizedRunId)}/story-handoff-packets`,
        {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                stageId: normalizedStageId,
                storyId: normalizedStoryId,
            }),
        },
    );
    if (!response.ok) {
        throw new Error(`Failed to create story handoff packet: ${response.status}`);
    }
    return parsePacket(await response.json());
};
