import { WorkflowHandoff, WorkflowType } from '../core/types';
import { WORKFLOWS } from '../core/workflows';

type HandoffPayload = Record<string, unknown>;

const isRecord = (value: unknown): value is Record<string, unknown> => (
    typeof value === 'object' && value !== null
);

const isWorkflowType = (value: unknown): value is WorkflowType => (
    typeof value === 'string'
    && Object.prototype.hasOwnProperty.call(WORKFLOWS, value)
);

const parseWorkflowHandoffContext = (context: unknown): WorkflowHandoff['context'] => {
    if (context === undefined) {
        return undefined;
    }
    if (!isRecord(context)) {
        throw new Error('Invalid workflow handoff response');
    }

    const sourceArtifactTitle = context.sourceArtifactTitle;
    const sourceArtifactSummary = context.sourceArtifactSummary;
    const targetInputSummary = context.targetInputSummary;
    const unconfirmedItems = context.unconfirmedItems;
    if (
        typeof sourceArtifactTitle !== 'string'
        || typeof sourceArtifactSummary !== 'string'
        || typeof targetInputSummary !== 'string'
        || !Array.isArray(unconfirmedItems)
        || !unconfirmedItems.every((item): item is string => typeof item === 'string')
    ) {
        throw new Error('Invalid workflow handoff response');
    }

    return {
        sourceArtifactTitle,
        sourceArtifactSummary,
        targetInputSummary,
        unconfirmedItems,
    };
};

const parseWorkflowHandoff = (handoff: unknown): WorkflowHandoff => {
    if (!isRecord(handoff)) {
        throw new Error('Invalid workflow handoff response');
    }

    const payload = handoff as HandoffPayload;
    const id = payload.id;
    const label = payload.label;
    const sourceWorkflowId = payload.sourceWorkflowId;
    const sourceStageId = payload.sourceStageId;
    const sourceArtifactVersion = payload.sourceArtifactVersion;
    const targetRunId = payload.targetRunId;
    const targetWorkflowId = payload.targetWorkflowId;
    const targetStageId = payload.targetStageId;
    const targetAgentId = payload.targetAgentId;
    const context = parseWorkflowHandoffContext(payload.context);
    const prompt = payload.prompt;
    let parsedTargetRunId: string | undefined;
    if (targetRunId !== undefined) {
        if (typeof targetRunId !== 'string') {
            throw new Error('Invalid workflow handoff response');
        }
        parsedTargetRunId = targetRunId;
    }

    if (
        typeof id !== 'string'
        || typeof label !== 'string'
        || !isWorkflowType(sourceWorkflowId)
        || typeof sourceStageId !== 'string'
        || typeof sourceArtifactVersion !== 'number'
        || !Number.isInteger(sourceArtifactVersion)
        || !isWorkflowType(targetWorkflowId)
        || typeof targetStageId !== 'string'
        || typeof targetAgentId !== 'string'
        || typeof prompt !== 'string'
    ) {
        throw new Error('Invalid workflow handoff response');
    }

    return {
        id,
        label,
        sourceWorkflowId,
        sourceStageId,
        sourceArtifactVersion,
        ...(parsedTargetRunId !== undefined ? { targetRunId: parsedTargetRunId } : {}),
        targetWorkflowId,
        targetStageId,
        targetAgentId,
        ...(context !== undefined ? { context } : {}),
        prompt,
    };
};

export const fetchWorkflowHandoffs = async (runId: string): Promise<WorkflowHandoff[]> => {
    const normalizedRunId = runId.trim();
    if (!normalizedRunId) {
        return [];
    }

    const response = await fetch(
        `/new-agents/api/agent/runs/${encodeURIComponent(normalizedRunId)}/handoffs`
    );

    if (!response.ok) {
        throw new Error(`Failed to fetch workflow handoffs: ${response.status}`);
    }

    const payload: unknown = await response.json();
    if (!isRecord(payload) || !Array.isArray(payload.handoffs)) {
        throw new Error('Invalid workflow handoff response');
    }

    return payload.handoffs.map(parseWorkflowHandoff);
};

export const startWorkflowHandoff = async (
    runId: string,
    handoffId: string,
): Promise<WorkflowHandoff> => {
    const normalizedRunId = runId.trim();
    const normalizedHandoffId = handoffId.trim();
    if (!normalizedRunId || !normalizedHandoffId) {
        throw new Error('runId and handoffId are required');
    }

    const response = await fetch(
        `/new-agents/api/agent/runs/${encodeURIComponent(normalizedRunId)}/handoffs/${encodeURIComponent(normalizedHandoffId)}/start`,
        { method: 'POST' },
    );

    if (!response.ok) {
        throw new Error(`Failed to start workflow handoff: ${response.status}`);
    }

    return parseWorkflowHandoff(await response.json());
};
