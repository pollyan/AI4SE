import type {
    ObservabilityFormatFailureDiagnostics,
    ObservabilityFormatFailureKind,
    ObservabilityFormatFailureProvider,
    ObservabilityFormatFailureRecent,
    ObservabilityFormatFailureStage,
    ObservabilityProviderSummary,
    ObservabilityStageSummary,
    ObservabilitySummary,
    ObservabilityTotals,
    ObservabilityTurn,
    WorkflowType,
} from '../core/types';
import { WORKFLOWS } from '../core/workflows';

const INVALID_OBSERVABILITY_ERROR = 'Invalid observability summary response';

const isRecord = (value: unknown): value is Record<string, unknown> => (
    typeof value === 'object' && value !== null
);

const isWorkflowType = (value: unknown): value is WorkflowType => (
    typeof value === 'string'
    && Object.prototype.hasOwnProperty.call(WORKFLOWS, value)
);

const parseString = (value: unknown): string => {
    if (typeof value === 'string') return value;
    throw new Error(INVALID_OBSERVABILITY_ERROR);
};

const parseNullableString = (value: unknown): string | null => {
    if (value === null) return null;
    return parseString(value);
};

const parseNumber = (value: unknown): number => {
    if (typeof value === 'number' && Number.isFinite(value)) return value;
    throw new Error(INVALID_OBSERVABILITY_ERROR);
};

const parseInteger = (value: unknown): number => {
    if (typeof value === 'number' && Number.isInteger(value)) return value;
    throw new Error(INVALID_OBSERVABILITY_ERROR);
};

const parseWorkflowType = (value: unknown): WorkflowType => {
    if (isWorkflowType(value)) return value;
    throw new Error(INVALID_OBSERVABILITY_ERROR);
};

const parseErrorCodes = (value: unknown): Record<string, number> => {
    if (!isRecord(value)) {
        throw new Error(INVALID_OBSERVABILITY_ERROR);
    }

    return Object.fromEntries(
        Object.entries(value).map(([code, count]) => [code, parseInteger(count)])
    );
};

const parseTotals = (value: unknown): ObservabilityTotals => {
    if (!isRecord(value)) {
        throw new Error(INVALID_OBSERVABILITY_ERROR);
    }

    return {
        turns: parseInteger(value.turns),
        failedTurns: parseInteger(value.failedTurns),
        successRate: parseNumber(value.successRate),
        avgDurationMs: parseNumber(value.avgDurationMs),
        estimatedTokens: parseInteger(value.estimatedTokens),
        providerIssueCount: parseInteger(value.providerIssueCount),
        providerIssueCodes: parseErrorCodes(value.providerIssueCodes),
    };
};

const parseStageSummary = (value: unknown): ObservabilityStageSummary => {
    if (!isRecord(value)) {
        throw new Error(INVALID_OBSERVABILITY_ERROR);
    }

    return {
        ...parseTotals(value),
        workflowId: parseWorkflowType(value.workflowId),
        stageId: parseString(value.stageId),
        errorCodes: parseErrorCodes(value.errorCodes),
    };
};

const parseProviderSummary = (value: unknown): ObservabilityProviderSummary => {
    if (!isRecord(value)) {
        throw new Error(INVALID_OBSERVABILITY_ERROR);
    }

    return {
        ...parseTotals(value),
        provider: parseString(value.provider),
        errorCodes: parseErrorCodes(value.errorCodes),
    };
};

const parseFormatFailureKind = (value: unknown): ObservabilityFormatFailureKind => {
    if (!isRecord(value)) {
        throw new Error(INVALID_OBSERVABILITY_ERROR);
    }

    return {
        kind: parseString(value.kind),
        label: parseString(value.label),
        count: parseInteger(value.count),
        retryCount: parseInteger(value.retryCount),
        action: parseString(value.action),
    };
};

const parseFormatFailureStage = (value: unknown): ObservabilityFormatFailureStage => {
    if (!isRecord(value)) {
        throw new Error(INVALID_OBSERVABILITY_ERROR);
    }

    return {
        workflowId: parseWorkflowType(value.workflowId),
        stageId: parseString(value.stageId),
        count: parseInteger(value.count),
        retryCount: parseInteger(value.retryCount),
        kinds: parseErrorCodes(value.kinds),
        topKind: parseString(value.topKind),
        action: parseString(value.action),
    };
};

const parseFormatFailureProvider = (value: unknown): ObservabilityFormatFailureProvider => {
    if (!isRecord(value)) {
        throw new Error(INVALID_OBSERVABILITY_ERROR);
    }

    return {
        provider: parseString(value.provider),
        count: parseInteger(value.count),
        retryCount: parseInteger(value.retryCount),
        kinds: parseErrorCodes(value.kinds),
        topKind: parseString(value.topKind),
        action: parseString(value.action),
    };
};

const parseFormatFailureRecent = (value: unknown): ObservabilityFormatFailureRecent => {
    if (!isRecord(value)) {
        throw new Error(INVALID_OBSERVABILITY_ERROR);
    }

    return {
        turnId: parseInteger(value.turnId),
        runId: parseString(value.runId),
        workflowId: parseWorkflowType(value.workflowId),
        stageId: parseString(value.stageId),
        provider: parseString(value.provider),
        model: parseString(value.model),
        kind: parseString(value.kind),
        label: parseString(value.label),
        errorCode: parseString(value.errorCode),
        retryCount: parseInteger(value.retryCount),
        createdAt: parseNullableString(value.createdAt),
        action: parseString(value.action),
    };
};

const parseFormatFailureDiagnostics = (value: unknown): ObservabilityFormatFailureDiagnostics => {
    if (
        !isRecord(value)
        || !Array.isArray(value.byKind)
        || !Array.isArray(value.byStage)
        || !Array.isArray(value.byProvider)
        || !Array.isArray(value.recentFailures)
    ) {
        throw new Error(INVALID_OBSERVABILITY_ERROR);
    }

    return {
        total: parseInteger(value.total),
        byKind: value.byKind.map(parseFormatFailureKind),
        byStage: value.byStage.map(parseFormatFailureStage),
        byProvider: value.byProvider.map(parseFormatFailureProvider),
        recentFailures: value.recentFailures.map(parseFormatFailureRecent),
    };
};

const parseTurn = (value: unknown): ObservabilityTurn => {
    if (!isRecord(value)) {
        throw new Error(INVALID_OBSERVABILITY_ERROR);
    }

    return {
        id: parseInteger(value.id),
        runId: parseString(value.runId),
        workflowId: parseWorkflowType(value.workflowId),
        stageId: parseString(value.stageId),
        model: parseString(value.model),
        provider: parseString(value.provider),
        status: parseString(value.status),
        errorCode: parseNullableString(value.errorCode),
        durationMs: parseInteger(value.durationMs),
        inputChars: parseInteger(value.inputChars),
        outputChars: parseInteger(value.outputChars),
        estimatedTokens: parseInteger(value.estimatedTokens),
        contractRetryCount: parseInteger(value.contractRetryCount),
        createdAt: parseNullableString(value.createdAt),
    };
};

const parseSummary = (payload: unknown): ObservabilitySummary => {
    if (
        !isRecord(payload)
        || !Array.isArray(payload.byStage)
        || !Array.isArray(payload.byProvider)
        || !Array.isArray(payload.recentTurns)
    ) {
        throw new Error(INVALID_OBSERVABILITY_ERROR);
    }

    return {
        totals: parseTotals(payload.totals),
        byStage: payload.byStage.map(parseStageSummary),
        byProvider: payload.byProvider.map(parseProviderSummary),
        formatFailureDiagnostics: parseFormatFailureDiagnostics(
            payload.formatFailureDiagnostics
        ),
        recentTurns: payload.recentTurns.map(parseTurn),
    };
};

export const fetchObservabilitySummary = async (options?: {
    limit?: number;
    workflowId?: WorkflowType;
    stageId?: string;
}): Promise<ObservabilitySummary> => {
    const params = new URLSearchParams();
    if (options?.limit !== undefined) {
        params.set('limit', String(options.limit));
    }
    if (options?.workflowId) {
        params.set('workflowId', options.workflowId);
    }
    if (options?.stageId) {
        params.set('stageId', options.stageId);
    }
    const query = params.toString();
    const response = await fetch(
        `/new-agents/api/agent/observability${query ? `?${query}` : ''}`
    );

    if (!response.ok) {
        throw new Error(`Failed to fetch observability summary: ${response.status}`);
    }

    return parseSummary(await response.json());
};
