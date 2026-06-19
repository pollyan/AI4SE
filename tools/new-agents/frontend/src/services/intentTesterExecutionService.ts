import type {
    IntentTesterExecutionCreateResult,
    IntentTesterExecutionDetail,
    IntentTesterExecutionRecord,
    IntentTesterExecutionStep,
} from '../core/types';

const INVALID_CREATE_RESPONSE = 'Invalid intent-tester execution create response';
const INVALID_LIST_RESPONSE = 'Invalid intent-tester execution list response';
const INVALID_DETAIL_RESPONSE = 'Invalid intent-tester execution detail response';

const isRecord = (value: unknown): value is Record<string, unknown> => (
    typeof value === 'object' && value !== null
);

const parseNullableString = (value: unknown, errorMessage: string): string | null => {
    if (value === null || value === undefined) return null;
    if (typeof value !== 'string') throw new Error(errorMessage);
    return value;
};

const parseNullableNumber = (value: unknown, errorMessage: string): number | null => {
    if (value === null || value === undefined) return null;
    if (typeof value !== 'number') throw new Error(errorMessage);
    return value;
};

const parseNullableInteger = (value: unknown, errorMessage: string): number | null => {
    if (value === null || value === undefined) return null;
    if (typeof value === 'number' && Number.isInteger(value)) return value;
    throw new Error(errorMessage);
};

const parseCreateResult = (payload: unknown): IntentTesterExecutionCreateResult => {
    if (!isRecord(payload) || !isRecord(payload.data)) {
        throw new Error(INVALID_CREATE_RESPONSE);
    }

    const {
        execution_id: executionId,
        status,
        testcase_name: testcaseName,
        start_time: startTime,
    } = payload.data;

    if (
        typeof executionId !== 'string'
        || typeof status !== 'string'
        || typeof testcaseName !== 'string'
        || typeof startTime !== 'string'
    ) {
        throw new Error(INVALID_CREATE_RESPONSE);
    }

    return {
        executionId,
        status,
        testcaseName,
        startTime,
    };
};

const parseExecutionRecord = (
    payload: unknown,
    invalidMessage = INVALID_LIST_RESPONSE,
): IntentTesterExecutionRecord => {
    if (!isRecord(payload)) {
        throw new Error(invalidMessage);
    }

    const {
        execution_id: executionId,
        test_case_id: testCaseId,
        status,
        mode,
        browser,
        start_time: startTime,
        end_time: endTime,
        duration,
        error_message: errorMessage,
    } = payload;

    if (
        typeof executionId !== 'string'
        || typeof testCaseId !== 'number'
        || typeof status !== 'string'
    ) {
        throw new Error(invalidMessage);
    }

    return {
        executionId,
        testCaseId,
        status,
        mode: typeof mode === 'string' ? mode : '',
        browser: typeof browser === 'string' ? browser : '',
        startTime: parseNullableString(startTime, invalidMessage),
        endTime: parseNullableString(endTime, invalidMessage),
        duration: parseNullableNumber(duration, invalidMessage),
        errorMessage: parseNullableString(errorMessage, invalidMessage),
    };
};

const parseExecutionStep = (
    payload: unknown,
    errorMessage: string,
): IntentTesterExecutionStep => {
    if (!isRecord(payload)) {
        throw new Error(errorMessage);
    }

    const {
        step_index: stepIndex,
        step_description: description,
        status,
        error_message: errorMessageValue,
        screenshot_path: screenshotPath,
        action,
    } = payload;

    if (
        typeof stepIndex !== 'number'
        || !Number.isInteger(stepIndex)
        || typeof description !== 'string'
        || typeof status !== 'string'
    ) {
        throw new Error(errorMessage);
    }

    return {
        stepIndex,
        description,
        status,
        errorMessage: parseNullableString(errorMessageValue, errorMessage),
        screenshotPath: parseNullableString(screenshotPath, errorMessage),
        action: parseNullableString(action, errorMessage),
    };
};

const parseExecutionDetail = (payload: unknown): IntentTesterExecutionDetail => {
    if (!isRecord(payload) || !isRecord(payload.data) || !Array.isArray(payload.data.step_executions)) {
        throw new Error(INVALID_DETAIL_RESPONSE);
    }

    return {
        ...parseExecutionRecord(payload.data, INVALID_DETAIL_RESPONSE),
        stepsTotal: parseNullableInteger(payload.data.steps_total, INVALID_DETAIL_RESPONSE),
        stepsPassed: parseNullableInteger(payload.data.steps_passed, INVALID_DETAIL_RESPONSE),
        stepsFailed: parseNullableInteger(payload.data.steps_failed, INVALID_DETAIL_RESPONSE),
        steps: payload.data.step_executions.map(step => parseExecutionStep(step, INVALID_DETAIL_RESPONSE)),
    };
};

const parseLatestExecution = (payload: unknown): IntentTesterExecutionRecord | null => {
    if (!isRecord(payload) || !isRecord(payload.data) || !Array.isArray(payload.data.items)) {
        throw new Error(INVALID_LIST_RESPONSE);
    }

    const [latestExecution] = payload.data.items;
    return latestExecution === undefined ? null : parseExecutionRecord(latestExecution);
};

export const createIntentTesterExecution = async (
    testcaseId: number,
): Promise<IntentTesterExecutionCreateResult> => {
    const response = await fetch('/intent-tester/api/executions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            testcase_id: testcaseId,
            mode: 'headless',
            browser: 'chrome',
            executed_by: 'new-agents',
        }),
    });

    if (!response.ok) {
        throw new Error(`Failed to create intent-tester execution: ${response.status}`);
    }

    return parseCreateResult(await response.json());
};

export const fetchLatestIntentTesterExecution = async (
    testcaseId: number,
): Promise<IntentTesterExecutionRecord | null> => {
    const response = await fetch(`/intent-tester/api/executions?testcase_id=${testcaseId}&size=1`);

    if (!response.ok) {
        throw new Error(`Failed to fetch intent-tester executions: ${response.status}`);
    }

    return parseLatestExecution(await response.json());
};

export const fetchIntentTesterExecutionDetail = async (
    executionId: string,
): Promise<IntentTesterExecutionDetail> => {
    const normalizedExecutionId = executionId.trim();
    if (!normalizedExecutionId) {
        throw new Error('executionId is required');
    }

    const response = await fetch(`/intent-tester/api/executions/${encodeURIComponent(normalizedExecutionId)}`);

    if (!response.ok) {
        throw new Error(`Failed to fetch intent-tester execution detail: ${response.status}`);
    }

    return parseExecutionDetail(await response.json());
};
