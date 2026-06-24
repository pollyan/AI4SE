import { AgentRunListItem, AgentRunListResponse, AgentRunSnapshot, AgentRunSnapshotArtifact, AgentRunSnapshotContextSummary, AgentRunSnapshotMessage, ArtifactAuditEvent, ArtifactComment, ArtifactCommentReply, ArtifactCommentStatus, ArtifactSectionLock, WorkflowType } from '../core/types';
import { WORKFLOWS } from '../core/workflows';

const INVALID_SNAPSHOT_ERROR = 'Invalid run snapshot response';
const INVALID_RUN_LIST_ERROR = 'Invalid run list response';

export class ArtifactConflictError extends Error {
    currentArtifact: AgentRunSnapshotArtifact;

    constructor(message: string, currentArtifact: AgentRunSnapshotArtifact) {
        super(message);
        this.name = 'ArtifactConflictError';
        this.currentArtifact = currentArtifact;
    }
}

const isRecord = (value: unknown): value is Record<string, unknown> => (
    typeof value === 'object' && value !== null
);

const isWorkflowType = (value: unknown): value is WorkflowType => (
    typeof value === 'string'
    && Object.prototype.hasOwnProperty.call(WORKFLOWS, value)
);

const parseMessage = (message: unknown): AgentRunSnapshotMessage => {
    if (
        !isRecord(message)
        || (message.role !== 'user' && message.role !== 'assistant')
        || typeof message.content !== 'string'
        || typeof message.sequenceIndex !== 'number'
        || !Number.isInteger(message.sequenceIndex)
    ) {
        throw new Error(INVALID_SNAPSHOT_ERROR);
    }

    return {
        role: message.role,
        content: message.content,
        sequenceIndex: message.sequenceIndex,
    };
};

const parseNullableString = (value: unknown, errorMessage: string): string | null => {
    if (value === null) return null;
    if (typeof value === 'string') return value;
    throw new Error(errorMessage);
};

const parseNullableNumber = (value: unknown, errorMessage: string): number | null => {
    if (value === null) return null;
    if (typeof value === 'number') return value;
    throw new Error(errorMessage);
};

const parseInteger = (value: unknown, errorMessage: string): number => {
    if (typeof value === 'number' && Number.isInteger(value)) return value;
    throw new Error(errorMessage);
};

const parseNullableInteger = (value: unknown, errorMessage: string): number | null => {
    if (value === null) return null;
    return parseInteger(value, errorMessage);
};

const parseArtifact = (artifact: unknown): AgentRunSnapshotArtifact => {
    if (
        !isRecord(artifact)
        || typeof artifact.stageId !== 'string'
        || typeof artifact.content !== 'string'
        || typeof artifact.versionNumber !== 'number'
        || !Number.isInteger(artifact.versionNumber)
    ) {
        throw new Error(INVALID_SNAPSHOT_ERROR);
    }

    return {
        stageId: artifact.stageId,
        content: artifact.content,
        versionNumber: artifact.versionNumber,
    };
};

const parseContextSummary = (summary: unknown): AgentRunSnapshotContextSummary => {
    if (!isRecord(summary)) {
        throw new Error(INVALID_SNAPSHOT_ERROR);
    }
    const sourceType = summary.sourceType;
    const sourceStageId = summary.sourceStageId;
    const summaryType = summary.summaryType;
    const content = summary.content;
    let parsedSourceStageId: string | null;
    if (sourceStageId === null) {
        parsedSourceStageId = null;
    } else if (typeof sourceStageId === 'string') {
        parsedSourceStageId = sourceStageId;
    } else {
        throw new Error(INVALID_SNAPSHOT_ERROR);
    }

    if (
        typeof sourceType !== 'string'
        || typeof summaryType !== 'string'
        || typeof content !== 'string'
    ) {
        throw new Error(INVALID_SNAPSHOT_ERROR);
    }

    return {
        sourceType,
        sourceStageId: parsedSourceStageId,
        summaryType,
        content,
    };
};

const parseArtifactComment = (comment: unknown): ArtifactComment => {
    if (
        !isRecord(comment)
        || typeof comment.id !== 'string'
        || typeof comment.stageId !== 'string'
        || typeof comment.content !== 'string'
        || typeof comment.artifactExcerpt !== 'string'
        || (
            comment.anchorText !== undefined
            && comment.anchorText !== null
            && typeof comment.anchorText !== 'string'
        )
        || typeof comment.createdAt !== 'number'
        || (comment.status !== 'open' && comment.status !== 'resolved')
        || (comment.resolvedAt !== null && typeof comment.resolvedAt !== 'number')
        || !Array.isArray(comment.replies)
    ) {
        throw new Error(INVALID_SNAPSHOT_ERROR);
    }
    const status: ArtifactCommentStatus = comment.status;
    const resolvedAt: number | null = typeof comment.resolvedAt === 'number'
        ? comment.resolvedAt
        : null;

    return {
        id: comment.id,
        stageId: comment.stageId,
        content: comment.content,
        artifactExcerpt: comment.artifactExcerpt,
        anchorText: typeof comment.anchorText === 'string' ? comment.anchorText : null,
        createdAt: comment.createdAt,
        status,
        resolvedAt,
        replies: comment.replies.map(parseArtifactCommentReply),
    };
};

const parseArtifactCommentReply = (reply: unknown): ArtifactCommentReply => {
    if (
        !isRecord(reply)
        || typeof reply.id !== 'string'
        || typeof reply.content !== 'string'
        || typeof reply.createdAt !== 'number'
    ) {
        throw new Error(INVALID_SNAPSHOT_ERROR);
    }

    return {
        id: reply.id,
        content: reply.content,
        createdAt: reply.createdAt,
    };
};

const parseArtifactSectionLock = (lock: unknown): ArtifactSectionLock => {
    if (
        !isRecord(lock)
        || typeof lock.id !== 'string'
        || typeof lock.stageId !== 'string'
        || typeof lock.heading !== 'string'
        || typeof lock.content !== 'string'
        || typeof lock.createdAt !== 'number'
    ) {
        throw new Error(INVALID_SNAPSHOT_ERROR);
    }

    return {
        id: lock.id,
        stageId: lock.stageId,
        heading: lock.heading,
        sectionAnchor: typeof lock.sectionAnchor === 'string' && lock.sectionAnchor.trim()
            ? lock.sectionAnchor.trim()
            : null,
        content: lock.content,
        createdAt: lock.createdAt,
    };
};

const parseArtifactAuditEvent = (event: unknown): ArtifactAuditEvent => {
    if (
        !isRecord(event)
        || typeof event.stageId !== 'string'
        || typeof event.eventType !== 'string'
        || typeof event.summary !== 'string'
        || typeof event.createdAt !== 'number'
    ) {
        throw new Error(INVALID_SNAPSHOT_ERROR);
    }

    return {
        stageId: event.stageId,
        eventType: event.eventType,
        summary: event.summary,
        createdAt: event.createdAt,
    };
};

const parseArtifactCollaborationState = (
    payload: unknown,
): Pick<AgentRunSnapshot, 'artifactComments' | 'artifactSectionLocks'> => {
    if (
        !isRecord(payload)
        || !Array.isArray(payload.artifactComments)
        || !Array.isArray(payload.artifactSectionLocks)
    ) {
        throw new Error(INVALID_SNAPSHOT_ERROR);
    }

    return {
        artifactComments: payload.artifactComments.map(parseArtifactComment),
        artifactSectionLocks: payload.artifactSectionLocks.map(parseArtifactSectionLock),
    };
};

const parseRunSnapshot = (payload: unknown): AgentRunSnapshot => {
    if (
        !isRecord(payload)
        || !isRecord(payload.run)
        || !Array.isArray(payload.messages)
        || !Array.isArray(payload.artifacts)
        || !Array.isArray(payload.contextSummaries)
    ) {
        throw new Error(INVALID_SNAPSHOT_ERROR);
    }

    const { run } = payload;
    const runId = run.id;
    const workflowId = run.workflowId;
    const agentId = run.agentId;
    const currentStageId = run.currentStageId;
    const status = run.status;
    const model = run.model;
    let parsedModel: string | null;
    if (model === null) {
        parsedModel = null;
    } else if (typeof model === 'string') {
        parsedModel = model;
    } else {
        throw new Error(INVALID_SNAPSHOT_ERROR);
    }
    if (
        typeof runId !== 'string'
        || !isWorkflowType(workflowId)
        || typeof agentId !== 'string'
        || typeof currentStageId !== 'string'
        || typeof status !== 'string'
    ) {
        throw new Error(INVALID_SNAPSHOT_ERROR);
    }

    const workflow = WORKFLOWS[workflowId];
    if (
        workflow.agentId !== agentId
        || !workflow.stages.some(stage => stage.id === currentStageId)
    ) {
        throw new Error(INVALID_SNAPSHOT_ERROR);
    }

    const collaborationState = parseArtifactCollaborationState(payload);
    const artifactAuditEvents = Array.isArray(payload.artifactAuditEvents)
        ? payload.artifactAuditEvents.map(parseArtifactAuditEvent)
        : [];

    return {
        run: {
            id: runId,
            workflowId,
            agentId,
            currentStageId,
            status,
            model: parsedModel,
        },
        messages: payload.messages.map(parseMessage),
        artifacts: payload.artifacts.map(parseArtifact),
        contextSummaries: payload.contextSummaries.map(parseContextSummary),
        artifactComments: collaborationState.artifactComments,
        artifactSectionLocks: collaborationState.artifactSectionLocks,
        artifactAuditEvents,
    };
};

export const fetchRunSnapshot = async (runId: string): Promise<AgentRunSnapshot> => {
    const normalizedRunId = runId.trim();
    if (!normalizedRunId) {
        throw new Error('runId is required');
    }

    const response = await fetch(
        `/new-agents/api/agent/runs/${encodeURIComponent(normalizedRunId)}`
    );

    if (!response.ok) {
        throw new Error(`Failed to fetch run snapshot: ${response.status}`);
    }

    return parseRunSnapshot(await response.json());
};

export const updateRunContextSummary = async (
    runId: string,
    summary: Pick<AgentRunSnapshotContextSummary, 'sourceType' | 'sourceStageId' | 'summaryType'>,
    content: string,
): Promise<AgentRunSnapshotContextSummary> => {
    const normalizedRunId = runId.trim();
    if (!normalizedRunId) {
        throw new Error('runId is required');
    }

    const response = await fetch(
        `/new-agents/api/agent/runs/${encodeURIComponent(normalizedRunId)}/context-summaries`,
        {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                sourceType: summary.sourceType,
                sourceStageId: summary.sourceStageId,
                summaryType: summary.summaryType,
                content,
            }),
        }
    );

    if (!response.ok) {
        throw new Error(`Failed to update run context summary: ${response.status}`);
    }

    return parseContextSummary(await response.json());
};

export const createRunDecisionSummary = async (
    runId: string,
    stageId: string,
    content: string,
): Promise<AgentRunSnapshotContextSummary> => {
    const normalizedRunId = runId.trim();
    if (!normalizedRunId) {
        throw new Error('runId is required');
    }

    const response = await fetch(
        `/new-agents/api/agent/runs/${encodeURIComponent(normalizedRunId)}/context-summaries/decisions`,
        {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                stageId,
                content,
            }),
        }
    );

    if (!response.ok) {
        throw new Error(`Failed to create run decision summary: ${response.status}`);
    }

    return parseContextSummary(await response.json());
};

export const updateRunArtifact = async (
    runId: string,
    stageId: string,
    content: string,
    options?: { expectedVersionNumber?: number },
): Promise<AgentRunSnapshotArtifact> => {
    const normalizedRunId = runId.trim();
    if (!normalizedRunId) {
        throw new Error('runId is required');
    }
    const normalizedStageId = stageId.trim();
    if (!normalizedStageId) {
        throw new Error('stageId is required');
    }
    if (!content.trim()) {
        throw new Error('content is required');
    }

    const requestBody: {
        stageId: string;
        content: string;
        expectedVersionNumber?: number;
    } = {
        stageId: normalizedStageId,
        content,
    };
    if (options?.expectedVersionNumber !== undefined) {
        if (!Number.isInteger(options.expectedVersionNumber)) {
            throw new Error('expectedVersionNumber must be an integer');
        }
        requestBody.expectedVersionNumber = options.expectedVersionNumber;
    }

    const response = await fetch(
        `/new-agents/api/agent/runs/${encodeURIComponent(normalizedRunId)}/artifacts`,
        {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestBody),
        }
    );

    if (response.status === 409) {
        const payload = await response.json();
        if (
            !isRecord(payload)
            || typeof payload.error !== 'string'
        ) {
            throw new Error('Invalid artifact conflict response');
        }
        throw new ArtifactConflictError(
            payload.error,
            parseArtifact(payload.currentArtifact),
        );
    }

    if (!response.ok) {
        throw new Error(`Failed to update run artifact: ${response.status}`);
    }

    return parseArtifact(await response.json());
};

export const updateRunArtifactCollaboration = async (
    runId: string,
    comments: ArtifactComment[],
    sectionLocks: ArtifactSectionLock[],
): Promise<Pick<AgentRunSnapshot, 'artifactComments' | 'artifactSectionLocks'>> => {
    const normalizedRunId = runId.trim();
    if (!normalizedRunId) {
        throw new Error('runId is required');
    }

    const response = await fetch(
        `/new-agents/api/agent/runs/${encodeURIComponent(normalizedRunId)}/artifact-collaboration`,
        {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                comments,
                sectionLocks,
            }),
        }
    );

    if (!response.ok) {
        let diagnostic = `${response.status}`;
        try {
            const payload = await response.json();
            if (
                isRecord(payload)
                && typeof payload.error === 'string'
                && payload.error.trim()
            ) {
                diagnostic = payload.error.trim();
            }
        } catch {
            diagnostic = `${response.status}`;
        }
        throw new Error(`Failed to update artifact collaboration state: ${diagnostic}`);
    }

    return parseArtifactCollaborationState(await response.json());
};

const parseRunListItem = (run: unknown): AgentRunListItem => {
    if (!isRecord(run)) {
        throw new Error(INVALID_RUN_LIST_ERROR);
    }

    const id = run.id;
    const workflowId = run.workflowId;
    const agentId = run.agentId;
    const currentStageId = run.currentStageId;
    const status = run.status;
    const model = parseNullableString(run.model, INVALID_RUN_LIST_ERROR);
    const createdAt = parseNullableString(run.createdAt, INVALID_RUN_LIST_ERROR);
    const updatedAt = parseNullableString(run.updatedAt, INVALID_RUN_LIST_ERROR);

    if (
        typeof id !== 'string'
        || !isWorkflowType(workflowId)
        || typeof agentId !== 'string'
        || typeof currentStageId !== 'string'
        || typeof status !== 'string'
    ) {
        throw new Error(INVALID_RUN_LIST_ERROR);
    }

    const workflow = WORKFLOWS[workflowId];
    if (
        workflow.agentId !== agentId
        || !workflow.stages.some(stage => stage.id === currentStageId)
    ) {
        throw new Error(INVALID_RUN_LIST_ERROR);
    }

    let lastMessage: AgentRunSnapshotMessage | null = null;
    if (run.lastMessage !== null) {
        lastMessage = parseMessage(run.lastMessage);
    }

    let currentArtifact: AgentRunListItem['currentArtifact'] = null;
    if (run.currentArtifact !== null) {
        if (
            !isRecord(run.currentArtifact)
            || typeof run.currentArtifact.stageId !== 'string'
            || typeof run.currentArtifact.summary !== 'string'
        ) {
            throw new Error(INVALID_RUN_LIST_ERROR);
        }
        currentArtifact = {
            stageId: run.currentArtifact.stageId,
            versionNumber: parseNullableNumber(
                run.currentArtifact.versionNumber,
                INVALID_RUN_LIST_ERROR
            ),
            summary: run.currentArtifact.summary,
        };
    }

    return {
        id,
        workflowId,
        agentId,
        currentStageId,
        status,
        model,
        createdAt,
        updatedAt,
        lastMessage,
        currentArtifact,
    };
};

const parseRunList = (payload: unknown): AgentRunListResponse => {
    if (
        !isRecord(payload)
        || typeof payload.hasMore !== 'boolean'
        || !Array.isArray(payload.runs)
    ) {
        throw new Error(INVALID_RUN_LIST_ERROR);
    }

    return {
        limit: parseInteger(payload.limit, INVALID_RUN_LIST_ERROR),
        offset: parseInteger(payload.offset, INVALID_RUN_LIST_ERROR),
        total: parseInteger(payload.total, INVALID_RUN_LIST_ERROR),
        hasMore: payload.hasMore,
        nextOffset: parseNullableInteger(payload.nextOffset, INVALID_RUN_LIST_ERROR),
        query: parseNullableString(payload.query, INVALID_RUN_LIST_ERROR),
        runs: payload.runs.map(parseRunListItem),
    };
};

export const fetchRunList = async (options?: {
    workflowId?: WorkflowType;
    limit?: number;
    offset?: number;
    query?: string;
}): Promise<AgentRunListResponse> => {
    const params = new URLSearchParams();
    if (options?.workflowId) {
        params.set('workflowId', options.workflowId);
    }
    if (options?.limit !== undefined) {
        params.set('limit', String(options.limit));
    }
    if (options?.offset !== undefined) {
        params.set('offset', String(options.offset));
    }
    const normalizedQuery = options?.query?.trim();
    if (normalizedQuery) {
        params.set('query', normalizedQuery);
    }
    const query = params.toString();
    const response = await fetch(
        `/new-agents/api/agent/runs${query ? `?${query}` : ''}`
    );

    if (!response.ok) {
        throw new Error(`Failed to fetch run list: ${response.status}`);
    }

    return parseRunList(await response.json());
};
