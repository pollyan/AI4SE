import type {
    IntentTesterDraft,
    IntentTesterImportResult,
} from '../core/types';

const INVALID_IMPORT_RESPONSE = 'Invalid intent-tester import response';

const isRecord = (value: unknown): value is Record<string, unknown> => (
    typeof value === 'object' && value !== null
);

const parseImportResult = (payload: unknown): IntentTesterImportResult => {
    if (!isRecord(payload) || !isRecord(payload.data)) {
        throw new Error(INVALID_IMPORT_RESPONSE);
    }
    const { id, name } = payload.data;
    if (typeof id !== 'number' || !Number.isInteger(id) || typeof name !== 'string') {
        throw new Error(INVALID_IMPORT_RESPONSE);
    }
    return { id, name };
};

export const importIntentTesterDraft = async (
    draft: IntentTesterDraft,
): Promise<IntentTesterImportResult> => {
    const response = await fetch('/intent-tester/api/testcases', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            name: draft.name,
            description: draft.description,
            category: draft.category,
            priority: draft.priority,
            tags: draft.tags,
            steps: draft.steps,
        }),
    });

    if (!response.ok) {
        throw new Error(`Failed to import intent-tester draft: ${response.status}`);
    }

    return parseImportResult(await response.json());
};
