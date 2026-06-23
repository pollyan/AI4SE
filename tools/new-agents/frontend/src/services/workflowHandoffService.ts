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

const isStringArray = (value: unknown): value is string[] => (
    Array.isArray(value) && value.every(item => typeof item === 'string')
);

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
    const sourceSummary = payload.sourceSummary;
    const unconfirmedItems = payload.unconfirmedItems;
    const targetInputChecklist = payload.targetInputChecklist;
    const targetRunId = payload.targetRunId;
    const targetWorkflowId = payload.targetWorkflowId;
    const targetStageId = payload.targetStageId;
    const targetAgentId = payload.targetAgentId;
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
        || typeof sourceSummary !== 'string'
        || !isStringArray(unconfirmedItems)
        || !isStringArray(targetInputChecklist)
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
        sourceSummary,
        unconfirmedItems,
        targetInputChecklist,
        ...(parsedTargetRunId !== undefined ? { targetRunId: parsedTargetRunId } : {}),
        targetWorkflowId,
        targetStageId,
        targetAgentId,
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
