import type {
    IntentTesterDraft,
    IntentTesterExecutionRecord,
    IntentTesterStep,
    TestAssetCase,
    TestAssetCasePatch,
    TestAssetCollection,
    TestAssetCoverageSummary,
    TestAssetIntentTesterCasePatch,
    TestAssetIntentTesterMapping,
    TestAssetIntentTesterResultSnapshot,
    TestAssetIssue,
    TestAssetIssueStatus,
    TestAssetPoint,
    TestAssetPointPatch,
    TestAssetQualityGateStatus,
    TestAssetQualityStatus,
    TestAssetQualitySummary,
    TestAssetRisk,
    TestAssetRiskCreatePatch,
    TestAssetRiskDeleteResult,
    TestAssetRiskPatch,
    TestAssetRiskStatus,
    WorkflowType,
} from '../core/types';
import { WORKFLOWS } from '../core/workflows';

const INVALID_COLLECTION_ERROR = 'Invalid test asset collection response';
const INVALID_CASE_ERROR = 'Invalid test asset case response';
const INVALID_ISSUE_ERROR = 'Invalid test asset issue response';
const INVALID_POINT_ERROR = 'Invalid test asset point response';
const INVALID_RISK_ERROR = 'Invalid test asset risk response';
const INVALID_INTENT_TESTER_MAPPING_ERROR = 'Invalid test asset intent-tester mapping response';
const ISSUE_STATUSES = new Set<TestAssetIssueStatus>(['pending', 'confirmed', 'ignored']);
const QUALITY_STATUSES = new Set<TestAssetQualityStatus>(['blocked', 'attention', 'ready']);
const QUALITY_GATE_STATUSES = new Set<TestAssetQualityGateStatus>(['fail', 'warn', 'pass']);
const RISK_STATUSES = new Set<TestAssetRiskStatus>([
    'open',
    'mitigating',
    'accepted',
    'closed',
]);

const isRecord = (value: unknown): value is Record<string, unknown> => (
    typeof value === 'object' && value !== null
);

const isWorkflowType = (value: unknown): value is WorkflowType => (
    typeof value === 'string'
    && Object.prototype.hasOwnProperty.call(WORKFLOWS, value)
);

const parseString = (value: unknown, errorMessage: string): string => {
    if (typeof value === 'string') return value;
    throw new Error(errorMessage);
};

const parseNumber = (value: unknown, errorMessage: string): number => {
    if (typeof value === 'number' && Number.isFinite(value)) return value;
    throw new Error(errorMessage);
};

const parseInteger = (value: unknown, errorMessage: string): number => {
    if (typeof value === 'number' && Number.isInteger(value)) return value;
    throw new Error(errorMessage);
};

const parseBoolean = (value: unknown, errorMessage: string): boolean => {
    if (typeof value === 'boolean') return value;
    throw new Error(errorMessage);
};

const parseNullableString = (value: unknown, errorMessage: string): string | null => {
    if (value === null || value === undefined) return null;
    if (typeof value === 'string') return value;
    throw new Error(errorMessage);
};

const parseNullableNumber = (value: unknown, errorMessage: string): number | null => {
    if (value === null || value === undefined) return null;
    if (typeof value === 'number' && Number.isFinite(value)) return value;
    throw new Error(errorMessage);
};

const parseStringArray = (value: unknown, errorMessage: string): string[] => {
    if (!Array.isArray(value) || value.some(item => typeof item !== 'string')) {
        throw new Error(errorMessage);
    }
    return value;
};

const parseCoverageSummary = (
    value: unknown,
    errorMessage: string,
): TestAssetCoverageSummary => {
    if (!isRecord(value) || !Array.isArray(value.byPriority)) {
        throw new Error(errorMessage);
    }

    return {
        totalTestCases: parseInteger(value.totalTestCases, errorMessage),
        totalTestPoints: parseInteger(value.totalTestPoints, errorMessage),
        coveredTestPoints: parseInteger(value.coveredTestPoints, errorMessage),
        partiallyCoveredTestPoints: parseInteger(value.partiallyCoveredTestPoints, errorMessage),
        uncoveredTestPoints: parseInteger(value.uncoveredTestPoints, errorMessage),
        coverageRate: parseNumber(value.coverageRate, errorMessage),
        byPriority: value.byPriority.map((priority) => {
            if (!isRecord(priority)) {
                throw new Error(errorMessage);
            }
            return {
                priority: parseString(priority.priority, errorMessage),
                total: parseInteger(priority.total, errorMessage),
                covered: parseInteger(priority.covered, errorMessage),
                partial: parseInteger(priority.partial, errorMessage),
                uncovered: parseInteger(priority.uncovered, errorMessage),
                coverageRate: parseNumber(priority.coverageRate, errorMessage),
            };
        }),
    };
};

const parseQualityStatus = (value: unknown, errorMessage: string): TestAssetQualityStatus => {
    if (typeof value === 'string' && QUALITY_STATUSES.has(value as TestAssetQualityStatus)) {
        return value as TestAssetQualityStatus;
    }
    throw new Error(errorMessage);
};

const parseQualityGateStatus = (
    value: unknown,
    errorMessage: string,
): TestAssetQualityGateStatus => {
    if (
        typeof value === 'string'
        && QUALITY_GATE_STATUSES.has(value as TestAssetQualityGateStatus)
    ) {
        return value as TestAssetQualityGateStatus;
    }
    throw new Error(errorMessage);
};

const parseQualitySummary = (
    value: unknown,
    errorMessage: string,
): TestAssetQualitySummary => {
    if (!isRecord(value) || !Array.isArray(value.gates)) {
        throw new Error(errorMessage);
    }

    return {
        status: parseQualityStatus(value.status, errorMessage),
        label: parseString(value.label, errorMessage),
        pendingIssueCount: parseInteger(value.pendingIssueCount, errorMessage),
        confirmedIssueCount: parseInteger(value.confirmedIssueCount, errorMessage),
        ignoredIssueCount: parseInteger(value.ignoredIssueCount, errorMessage),
        uncoveredTestPointCount: parseInteger(value.uncoveredTestPointCount, errorMessage),
        partialTestPointCount: parseInteger(value.partialTestPointCount, errorMessage),
        openRiskCount: parseInteger(value.openRiskCount, errorMessage),
        mitigatingRiskCount: parseInteger(value.mitigatingRiskCount, errorMessage),
        acceptedRiskCount: parseInteger(value.acceptedRiskCount, errorMessage),
        closedRiskCount: parseInteger(value.closedRiskCount, errorMessage),
        gates: value.gates.map((gate) => {
            if (!isRecord(gate)) {
                throw new Error(errorMessage);
            }
            return {
                id: parseString(gate.id, errorMessage),
                status: parseQualityGateStatus(gate.status, errorMessage),
                title: parseString(gate.title, errorMessage),
                detail: parseString(gate.detail, errorMessage),
            };
        }),
    };
};

const parseTestCaseVersion = (
    value: unknown,
    errorMessage: string,
): Omit<TestAssetCase, 'id' | 'versions'> => {
    if (!isRecord(value)) {
        throw new Error(errorMessage);
    }

    return {
        title: parseString(value.title, errorMessage),
        priority: parseString(value.priority, errorMessage),
        dimension: parseString(value.dimension, errorMessage),
        testPoint: parseString(value.testPoint, errorMessage),
        risk: parseString(value.risk, errorMessage),
        precondition: parseString(value.precondition, errorMessage),
        steps: parseString(value.steps, errorMessage),
        testData: parseString(value.testData, errorMessage),
        expectedResult: parseString(value.expectedResult, errorMessage),
        versionNumber: parseInteger(value.versionNumber, errorMessage),
    };
};

const parseTestCase = (value: unknown, errorMessage: string): TestAssetCase => {
    if (!isRecord(value) || !Array.isArray(value.versions)) {
        throw new Error(errorMessage);
    }

    return {
        id: parseString(value.id, errorMessage),
        ...parseTestCaseVersion(value, errorMessage),
        versions: value.versions.map(version => parseTestCaseVersion(version, errorMessage)),
    };
};

const parseTraceItem = (value: unknown, errorMessage: string): TestAssetPoint => {
    if (!isRecord(value)) {
        throw new Error(errorMessage);
    }
    return {
        testPoint: parseString(value.testPoint, errorMessage),
        priority: parseString(value.priority, errorMessage),
        risk: parseString(value.risk, errorMessage),
        testCases: parseStringArray(value.testCases, errorMessage),
        status: parseString(value.status, errorMessage),
    };
};

const parseIssueStatus = (value: unknown, errorMessage: string): TestAssetIssueStatus => {
    if (typeof value === 'string' && ISSUE_STATUSES.has(value as TestAssetIssueStatus)) {
        return value as TestAssetIssueStatus;
    }
    throw new Error(errorMessage);
};

const parseAssetIssue = (value: unknown, errorMessage: string): TestAssetIssue => {
    if (!isRecord(value)) {
        throw new Error(errorMessage);
    }
    const issue = {
        id: parseInteger(value.id, errorMessage),
        type: parseString(value.type, errorMessage),
        message: parseString(value.message, errorMessage),
        status: parseIssueStatus(value.status, errorMessage),
    };
    return {
        ...issue,
        ...(value.caseId === undefined ? {} : { caseId: parseString(value.caseId, errorMessage) }),
        ...(value.testPoint === undefined ? {} : { testPoint: parseString(value.testPoint, errorMessage) }),
    };
};

const parseRiskStatus = (value: unknown, errorMessage: string): TestAssetRiskStatus => {
    if (typeof value === 'string' && RISK_STATUSES.has(value as TestAssetRiskStatus)) {
        return value as TestAssetRiskStatus;
    }
    throw new Error(errorMessage);
};

const parseRiskMatrixItem = (value: unknown, errorMessage: string): TestAssetRisk => {
    if (!isRecord(value)) {
        throw new Error(errorMessage);
    }
    return {
        id: parseInteger(value.id, errorMessage),
        risk: parseString(value.risk, errorMessage),
        isManual: parseBoolean(value.isManual, errorMessage),
        testCases: parseStringArray(value.testCases, errorMessage),
        testPoints: parseStringArray(value.testPoints, errorMessage),
        priorities: parseStringArray(value.priorities, errorMessage),
        dimensions: parseStringArray(value.dimensions, errorMessage),
        coverageStatuses: parseStringArray(value.coverageStatuses, errorMessage),
        status: parseRiskStatus(value.status, errorMessage),
        owner: parseString(value.owner, errorMessage),
        note: parseString(value.note, errorMessage),
    };
};

const parseIntentTesterStep = (
    value: unknown,
    errorMessage: string,
): IntentTesterStep => {
    if (!isRecord(value) || !isRecord(value.params)) {
        throw new Error(errorMessage);
    }
    return {
        action: parseString(value.action, errorMessage),
        params: value.params,
    };
};

const parseIntentTesterDraft = (
    value: unknown,
    errorMessage: string,
): IntentTesterDraft => {
    if (!isRecord(value) || !Array.isArray(value.tags) || !Array.isArray(value.steps) || !Array.isArray(value.draftWarnings)) {
        throw new Error(errorMessage);
    }
    return {
        sourceCaseId: parseString(value.sourceCaseId, errorMessage),
        name: parseString(value.name, errorMessage),
        description: parseString(value.description, errorMessage),
        category: parseString(value.category, errorMessage),
        priority: parseInteger(value.priority, errorMessage),
        tags: parseStringArray(value.tags, errorMessage),
        steps: value.steps.map(step => parseIntentTesterStep(step, errorMessage)),
        draftWarnings: parseStringArray(value.draftWarnings, errorMessage),
    };
};

const parseIntentTesterExecution = (
    value: unknown,
    errorMessage: string,
): IntentTesterExecutionRecord => {
    if (!isRecord(value)) {
        throw new Error(errorMessage);
    }
    return {
        executionId: parseString(value.executionId, errorMessage),
        testCaseId: parseInteger(value.testCaseId, errorMessage),
        status: parseString(value.status, errorMessage),
        mode: parseString(value.mode, errorMessage),
        browser: parseString(value.browser, errorMessage),
        startTime: parseNullableString(value.startTime, errorMessage),
        endTime: parseNullableString(value.endTime, errorMessage),
        duration: parseNullableNumber(value.duration, errorMessage),
        errorMessage: parseNullableString(value.errorMessage, errorMessage),
    };
};

const parseIntentTesterResultStep = (
    value: unknown,
    errorMessage: string,
): TestAssetIntentTesterResultSnapshot['failedSteps'][number] => {
    if (!isRecord(value)) {
        throw new Error(errorMessage);
    }
    return {
        stepIndex: parseInteger(value.stepIndex, errorMessage),
        description: parseString(value.description, errorMessage),
        status: parseString(value.status, errorMessage),
        errorMessage: parseNullableString(value.errorMessage, errorMessage),
        screenshotPath: parseNullableString(value.screenshotPath, errorMessage),
        action: parseNullableString(value.action, errorMessage),
    };
};

const parseIntentTesterResultSnapshot = (
    value: unknown,
    errorMessage: string,
): TestAssetIntentTesterResultSnapshot => {
    if (!isRecord(value) || !Array.isArray(value.screenshots) || !Array.isArray(value.failedSteps)) {
        throw new Error(errorMessage);
    }
    return {
        executionId: parseString(value.executionId, errorMessage),
        status: parseString(value.status, errorMessage),
        stepsTotal: parseInteger(value.stepsTotal, errorMessage),
        stepsPassed: parseInteger(value.stepsPassed, errorMessage),
        stepsFailed: parseInteger(value.stepsFailed, errorMessage),
        duration: parseNullableNumber(value.duration, errorMessage),
        errorMessage: parseNullableString(value.errorMessage, errorMessage),
        screenshots: parseStringArray(value.screenshots, errorMessage),
        failedSteps: value.failedSteps.map(step => parseIntentTesterResultStep(step, errorMessage)),
    };
};

const parseIntentTesterMapping = (
    value: unknown,
    errorMessage: string,
): TestAssetIntentTesterMapping => {
    if (!isRecord(value)) {
        throw new Error(errorMessage);
    }
    return {
        sourceCaseId: parseString(value.sourceCaseId, errorMessage),
        intentTesterCaseId: parseInteger(value.intentTesterCaseId, errorMessage),
        intentTesterCaseName: parseString(value.intentTesterCaseName, errorMessage),
        latestExecution: value.latestExecution === null
            ? null
            : parseIntentTesterExecution(value.latestExecution, errorMessage),
        latestResult: value.latestResult === null
            ? null
            : parseIntentTesterResultSnapshot(value.latestResult, errorMessage),
    };
};

const parseCollection = (payload: unknown): TestAssetCollection => {
    if (
        !isRecord(payload)
        || !isWorkflowType(payload.workflowId)
        || !Array.isArray(payload.testCases)
        || !Array.isArray(payload.testPoints)
        || !Array.isArray(payload.coverageTrace)
        || !Array.isArray(payload.assetIssues)
        || !Array.isArray(payload.riskMatrix)
        || !Array.isArray(payload.intentTesterMappings)
    ) {
        throw new Error(INVALID_COLLECTION_ERROR);
    }

    return {
        id: parseInteger(payload.id, INVALID_COLLECTION_ERROR),
        runId: parseString(payload.runId, INVALID_COLLECTION_ERROR),
        workflowId: payload.workflowId,
        sourceStageId: parseString(payload.sourceStageId, INVALID_COLLECTION_ERROR),
        sourceArtifactVersion: parseInteger(payload.sourceArtifactVersion, INVALID_COLLECTION_ERROR),
        coverageSummary: parseCoverageSummary(payload.coverageSummary, INVALID_COLLECTION_ERROR),
        qualitySummary: parseQualitySummary(payload.qualitySummary, INVALID_COLLECTION_ERROR),
        testCases: payload.testCases.map(testCase => parseTestCase(testCase, INVALID_COLLECTION_ERROR)),
        testPoints: payload.testPoints.map(testPoint => parseTraceItem(testPoint, INVALID_COLLECTION_ERROR)),
        coverageTrace: payload.coverageTrace.map(trace => parseTraceItem(trace, INVALID_COLLECTION_ERROR)),
        assetIssues: payload.assetIssues.map(issue => parseAssetIssue(issue, INVALID_COLLECTION_ERROR)),
        riskMatrix: payload.riskMatrix.map(risk => parseRiskMatrixItem(risk, INVALID_COLLECTION_ERROR)),
        intentTesterDrafts: Array.isArray(payload.intentTesterDrafts)
            ? payload.intentTesterDrafts.map(draft => parseIntentTesterDraft(draft, INVALID_COLLECTION_ERROR))
            : (() => {
                throw new Error(INVALID_COLLECTION_ERROR);
            })(),
        intentTesterMappings: payload.intentTesterMappings.map(mapping => (
            parseIntentTesterMapping(mapping, INVALID_COLLECTION_ERROR)
        )),
    };
};

export const materializeRunTestAssets = async (
    runId: string,
): Promise<TestAssetCollection> => {
    const normalizedRunId = runId.trim();
    if (!normalizedRunId) {
        throw new Error('runId is required');
    }

    const response = await fetch(
        `/new-agents/api/agent/runs/${encodeURIComponent(normalizedRunId)}/test-assets/materialize`,
        { method: 'POST' },
    );

    if (!response.ok) {
        throw new Error(`Failed to materialize test assets: ${response.status}`);
    }

    return parseCollection(await response.json());
};

export const fetchTestAssetCollection = async (
    collectionId: number,
): Promise<TestAssetCollection> => {
    if (!Number.isInteger(collectionId) || collectionId <= 0) {
        throw new Error('collectionId is required');
    }

    const response = await fetch(`/new-agents/api/agent/test-assets/${collectionId}`);

    if (!response.ok) {
        throw new Error(`Failed to fetch test asset collection: ${response.status}`);
    }

    return parseCollection(await response.json());
};

export const updateTestAssetCase = async (
    collectionId: number,
    caseId: string,
    patch: TestAssetCasePatch,
): Promise<TestAssetCase> => {
    const normalizedCaseId = caseId.trim();
    if (!Number.isInteger(collectionId) || collectionId <= 0) {
        throw new Error('collectionId is required');
    }
    if (!normalizedCaseId) {
        throw new Error('caseId is required');
    }

    const response = await fetch(
        `/new-agents/api/agent/test-assets/${collectionId}/test-cases/${encodeURIComponent(normalizedCaseId)}`,
        {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(patch),
        },
    );

    if (!response.ok) {
        throw new Error(`Failed to update test asset case: ${response.status}`);
    }

    return parseTestCase(await response.json(), INVALID_CASE_ERROR);
};

export const recordTestAssetIntentTesterCase = async (
    collectionId: number,
    caseId: string,
    patch: TestAssetIntentTesterCasePatch,
): Promise<TestAssetIntentTesterMapping> => {
    const normalizedCaseId = caseId.trim();
    if (!Number.isInteger(collectionId) || collectionId <= 0) {
        throw new Error('collectionId is required');
    }
    if (!normalizedCaseId) {
        throw new Error('caseId is required');
    }

    const response = await fetch(
        `/new-agents/api/agent/test-assets/${collectionId}/intent-tester/cases/${encodeURIComponent(normalizedCaseId)}`,
        {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(patch),
        },
    );

    if (!response.ok) {
        throw new Error(`Failed to record intent-tester case mapping: ${response.status}`);
    }

    return parseIntentTesterMapping(
        await response.json(),
        INVALID_INTENT_TESTER_MAPPING_ERROR,
    );
};

export const recordTestAssetIntentTesterExecution = async (
    collectionId: number,
    caseId: string,
    execution: IntentTesterExecutionRecord,
): Promise<TestAssetIntentTesterMapping> => {
    const normalizedCaseId = caseId.trim();
    if (!Number.isInteger(collectionId) || collectionId <= 0) {
        throw new Error('collectionId is required');
    }
    if (!normalizedCaseId) {
        throw new Error('caseId is required');
    }

    const response = await fetch(
        `/new-agents/api/agent/test-assets/${collectionId}/intent-tester/cases/${encodeURIComponent(normalizedCaseId)}/execution`,
        {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                executionId: execution.executionId,
                status: execution.status,
                mode: execution.mode,
                browser: execution.browser,
                startTime: execution.startTime,
                endTime: execution.endTime,
                duration: execution.duration,
                errorMessage: execution.errorMessage,
            }),
        },
    );

    if (!response.ok) {
        throw new Error(`Failed to record intent-tester execution mapping: ${response.status}`);
    }

    return parseIntentTesterMapping(
        await response.json(),
        INVALID_INTENT_TESTER_MAPPING_ERROR,
    );
};

export const recordTestAssetIntentTesterResult = async (
    collectionId: number,
    caseId: string,
    result: TestAssetIntentTesterResultSnapshot,
): Promise<TestAssetIntentTesterMapping> => {
    const normalizedCaseId = caseId.trim();
    if (!Number.isInteger(collectionId) || collectionId <= 0) {
        throw new Error('collectionId is required');
    }
    if (!normalizedCaseId) {
        throw new Error('caseId is required');
    }

    const response = await fetch(
        `/new-agents/api/agent/test-assets/${collectionId}/intent-tester/cases/${encodeURIComponent(normalizedCaseId)}/result`,
        {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(result),
        },
    );

    if (!response.ok) {
        throw new Error(`Failed to record intent-tester result snapshot: ${response.status}`);
    }

    return parseIntentTesterMapping(
        await response.json(),
        INVALID_INTENT_TESTER_MAPPING_ERROR,
    );
};

export const updateTestAssetIssueStatus = async (
    collectionId: number,
    issueId: number,
    status: TestAssetIssueStatus,
): Promise<TestAssetIssue> => {
    if (!Number.isInteger(collectionId) || collectionId <= 0) {
        throw new Error('collectionId is required');
    }
    if (!Number.isInteger(issueId) || issueId <= 0) {
        throw new Error('issueId is required');
    }
    if (!ISSUE_STATUSES.has(status)) {
        throw new Error('status is invalid');
    }

    const response = await fetch(
        `/new-agents/api/agent/test-assets/${collectionId}/issues/${issueId}`,
        {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status }),
        },
    );

    if (!response.ok) {
        throw new Error(`Failed to update test asset issue status: ${response.status}`);
    }

    return parseAssetIssue(await response.json(), INVALID_ISSUE_ERROR);
};

export const updateTestAssetPoint = async (
    collectionId: number,
    testPoint: string,
    patch: TestAssetPointPatch,
): Promise<TestAssetPoint> => {
    const normalizedTestPoint = testPoint.trim();
    if (!Number.isInteger(collectionId) || collectionId <= 0) {
        throw new Error('collectionId is required');
    }
    if (!normalizedTestPoint) {
        throw new Error('testPoint is required');
    }

    const response = await fetch(
        `/new-agents/api/agent/test-assets/${collectionId}/test-points/${encodeURIComponent(normalizedTestPoint)}`,
        {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(patch),
        },
    );

    if (!response.ok) {
        throw new Error(`Failed to update test asset point: ${response.status}`);
    }

    return parseTraceItem(await response.json(), INVALID_POINT_ERROR);
};

export const updateTestAssetRisk = async (
    collectionId: number,
    risk: string,
    patch: TestAssetRiskPatch,
): Promise<TestAssetRisk> => {
    const normalizedRisk = risk.trim();
    if (!Number.isInteger(collectionId) || collectionId <= 0) {
        throw new Error('collectionId is required');
    }
    if (!normalizedRisk) {
        throw new Error('risk is required');
    }

    const response = await fetch(
        `/new-agents/api/agent/test-assets/${collectionId}/risks/${encodeURIComponent(normalizedRisk)}`,
        {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(patch),
        },
    );

    if (!response.ok) {
        throw new Error(`Failed to update test asset risk: ${response.status}`);
    }

    return parseRiskMatrixItem(await response.json(), INVALID_RISK_ERROR);
};

export const createTestAssetRisk = async (
    collectionId: number,
    patch: TestAssetRiskCreatePatch,
): Promise<TestAssetRisk> => {
    if (!Number.isInteger(collectionId) || collectionId <= 0) {
        throw new Error('collectionId is required');
    }

    const response = await fetch(
        `/new-agents/api/agent/test-assets/${collectionId}/risks`,
        {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(patch),
        },
    );

    if (!response.ok) {
        throw new Error(`Failed to create test asset risk: ${response.status}`);
    }

    return parseRiskMatrixItem(await response.json(), INVALID_RISK_ERROR);
};

export const updateTestAssetRiskById = async (
    collectionId: number,
    riskId: number,
    patch: TestAssetRiskPatch,
): Promise<TestAssetRisk> => {
    if (!Number.isInteger(collectionId) || collectionId <= 0) {
        throw new Error('collectionId is required');
    }
    if (!Number.isInteger(riskId) || riskId <= 0) {
        throw new Error('riskId is required');
    }

    const response = await fetch(
        `/new-agents/api/agent/test-assets/${collectionId}/risks/by-id/${riskId}`,
        {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(patch),
        },
    );

    if (!response.ok) {
        throw new Error(`Failed to update test asset risk: ${response.status}`);
    }

    return parseRiskMatrixItem(await response.json(), INVALID_RISK_ERROR);
};

const parseRiskDeleteResult = (
    value: unknown,
    errorMessage: string,
): TestAssetRiskDeleteResult => {
    if (!isRecord(value)) {
        throw new Error(errorMessage);
    }
    return {
        id: parseInteger(value.id, errorMessage),
        deleted: parseBoolean(value.deleted, errorMessage),
    };
};

export const deleteTestAssetRisk = async (
    collectionId: number,
    riskId: number,
): Promise<TestAssetRiskDeleteResult> => {
    if (!Number.isInteger(collectionId) || collectionId <= 0) {
        throw new Error('collectionId is required');
    }
    if (!Number.isInteger(riskId) || riskId <= 0) {
        throw new Error('riskId is required');
    }

    const response = await fetch(
        `/new-agents/api/agent/test-assets/${collectionId}/risks/by-id/${riskId}`,
        { method: 'DELETE' },
    );

    if (!response.ok) {
        throw new Error(`Failed to delete test asset risk: ${response.status}`);
    }

    return parseRiskDeleteResult(await response.json(), INVALID_RISK_ERROR);
};
