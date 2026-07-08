import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fetchObservabilitySummary } from '../observabilityService';

global.fetch = vi.fn();

const OBSERVABILITY_PAYLOAD = {
    contractRetryReasons: { STRUCTURED_OUTPUT_CONTRACT_RETRY: 2 },
    diagnostics: [
        {
            id: 'contract-retry',
            severity: 'warning',
            title: '结构化输出重试偏高',
            detail: '最近运行中有 2 次 contract retry。',
            action: '检查该阶段 prompt、artifact contract 和 renderer 输出是否同步。',
        },
    ],
    totals: {
        turns: 3,
        failedTurns: 1,
        successRate: 66.67,
        avgDurationMs: 1200,
        estimatedTokens: 900,
        providerIssueCount: 1,
        providerIssueCodes: { LLM_ERROR: 1 },
    },
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
            diagnostic: {
                phase: 'structured_output',
                workflowId: 'TEST_DESIGN',
                stageId: 'CLARIFY',
                fieldPath: 'artifact_data.requirement_facts.0.fact',
                validator: 'pydantic_validation',
                retryable: true,
                publicReason: '模型输出的结构化字段未通过校验，右侧产出物已保持不变。',
            },
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
        expect(summary.recentTurns[0].diagnostic?.fieldPath).toBe(
            'artifact_data.requirement_facts.0.fact'
        );
        expect(summary.contractRetryReasons).toEqual({ STRUCTURED_OUTPUT_CONTRACT_RETRY: 2 });
        expect(summary.diagnostics[0].title).toBe('结构化输出重试偏高');
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
                diagnostics: [{ id: 'bad', severity: 'unknown' }],
            }),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
        ));

        await expect(fetchObservabilitySummary({ limit: 20 })).rejects.toThrow(
            'Invalid observability summary response'
        );
    });
});
