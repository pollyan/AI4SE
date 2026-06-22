import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fetchObservabilitySummary } from '../observabilityService';

global.fetch = vi.fn();

const OBSERVABILITY_PAYLOAD = {
    totals: {
        turns: 3,
        failedTurns: 1,
        successRate: 66.67,
        avgDurationMs: 1200,
        estimatedTokens: 900,
        providerIssueCount: 1,
        providerIssueCodes: { LLM_ERROR: 1 },
    },
    diagnostics: [
        {
            id: 'contract-retry-TEST_DESIGN-CLARIFY',
            severity: 'warning',
            title: '结构化产物重试集中',
            detail: 'TEST_DESIGN / CLARIFY 最近触发 2 次 contract retry。',
            action: '优先检查该阶段 artifact_data schema、required headings、visual contract 与 prompt 示例是否一致。',
            workflowId: 'TEST_DESIGN',
            stageId: 'CLARIFY',
            provider: null,
            metric: 'contractRetryCount',
            count: 2,
        },
    ],
    byStage: [
        {
            workflowId: 'TEST_DESIGN',
            stageId: 'CLARIFY',
            turns: 2,
            failedTurns: 1,
            successRate: 50,
            avgDurationMs: 1500,
            estimatedTokens: 700,
            errorCodes: { LLM_ERROR: 1 },
            providerIssueCount: 1,
            providerIssueCodes: { LLM_ERROR: 1 },
        },
    ],
    byProvider: [
        {
            provider: 'api.test.com',
            turns: 3,
            failedTurns: 1,
            successRate: 66.67,
            avgDurationMs: 1200,
            estimatedTokens: 900,
            errorCodes: { LLM_ERROR: 1 },
            providerIssueCount: 1,
            providerIssueCodes: { LLM_ERROR: 1 },
        },
    ],
    recentTurns: [
        {
            id: 11,
            runId: 'run-123',
            workflowId: 'TEST_DESIGN',
            stageId: 'CLARIFY',
            model: 'gpt-test',
            provider: 'api.test.com',
            status: 'error',
            errorCode: 'LLM_ERROR',
            durationMs: 1500,
            inputChars: 300,
            outputChars: 600,
            estimatedTokens: 225,
            contractRetryCount: 0,
            createdAt: '2026-06-19T10:00:00',
        },
    ],
};

describe('observabilityService', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('fetches runtime observability summary with a limit', async () => {
        vi.mocked(fetch).mockResolvedValue(new Response(
            JSON.stringify(OBSERVABILITY_PAYLOAD),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
        ));

        const summary = await fetchObservabilitySummary({ limit: 20 });

        expect(fetch).toHaveBeenCalledWith('/new-agents/api/agent/observability?limit=20');
        expect(summary.totals.turns).toBe(3);
        expect(summary.byStage[0].workflowId).toBe('TEST_DESIGN');
        expect(summary.byProvider[0].provider).toBe('api.test.com');
        expect(summary.totals.providerIssueCount).toBe(1);
        expect(summary.byStage[0].providerIssueCodes).toEqual({ LLM_ERROR: 1 });
        expect(summary.byProvider[0].providerIssueCount).toBe(1);
        expect(summary.recentTurns[0].errorCode).toBe('LLM_ERROR');
        expect(summary.diagnostics[0].metric).toBe('contractRetryCount');
        expect(summary.diagnostics[0].workflowId).toBe('TEST_DESIGN');
    });

    it('serializes workflow and stage filters', async () => {
        vi.mocked(fetch).mockResolvedValue(new Response(
            JSON.stringify(OBSERVABILITY_PAYLOAD),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
        ));

        await fetchObservabilitySummary({
            limit: 20,
            workflowId: 'TEST_DESIGN',
            stageId: 'CLARIFY',
        });

        expect(fetch).toHaveBeenCalledWith(
            '/new-agents/api/agent/observability?limit=20&workflowId=TEST_DESIGN&stageId=CLARIFY'
        );
    });

    it('omits the limit query when no limit is provided', async () => {
        vi.mocked(fetch).mockResolvedValue(new Response(
            JSON.stringify(OBSERVABILITY_PAYLOAD),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
        ));

        await fetchObservabilitySummary();

        expect(fetch).toHaveBeenCalledWith('/new-agents/api/agent/observability');
    });

    it('fails explicitly when the summary payload is malformed', async () => {
        vi.mocked(fetch).mockResolvedValue(new Response(
            JSON.stringify({ totals: {}, recentTurns: 'broken' }),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
        ));

        await expect(fetchObservabilitySummary({ limit: 20 })).rejects.toThrow(
            'Invalid observability summary response'
        );
    });

    it('fails explicitly when provider issue counts are malformed', async () => {
        vi.mocked(fetch).mockResolvedValue(new Response(
            JSON.stringify({
                ...OBSERVABILITY_PAYLOAD,
                totals: {
                    ...OBSERVABILITY_PAYLOAD.totals,
                    providerIssueCount: '1',
                },
            }),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
        ));

        await expect(fetchObservabilitySummary({ limit: 20 })).rejects.toThrow(
            'Invalid observability summary response'
        );
    });

    it('fails explicitly when diagnostics are malformed', async () => {
        vi.mocked(fetch).mockResolvedValue(new Response(
            JSON.stringify({
                ...OBSERVABILITY_PAYLOAD,
                diagnostics: [
                    {
                        ...OBSERVABILITY_PAYLOAD.diagnostics[0],
                        count: '2',
                    },
                ],
            }),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
        ));

        await expect(fetchObservabilitySummary({ limit: 20 })).rejects.toThrow(
            'Invalid observability summary response'
        );
    });
});
