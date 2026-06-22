import { describe, expect, it } from 'vitest';
import { buildObservabilityAlerts } from '../observabilityAlerts';
import type { ObservabilitySummary } from '../types';

const BASE_SUMMARY: ObservabilitySummary = {
    totals: {
        turns: 3,
        failedTurns: 1,
        successRate: 66.67,
        avgDurationMs: 1200,
        estimatedTokens: 900,
        providerIssueCount: 1,
        providerIssueCodes: { LLM_ERROR: 1 },
    },
    diagnostics: [],
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
        {
            workflowId: 'VALUE_DISCOVERY',
            stageId: 'BLUEPRINT',
            turns: 1,
            failedTurns: 0,
            successRate: 100,
            avgDurationMs: 800,
            estimatedTokens: 200,
            providerIssueCount: 0,
            providerIssueCodes: {},
            errorCodes: {},
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
    recentTurns: [],
};

describe('buildObservabilityAlerts', () => {
    it('builds total, stage, and provider alerts from failing observability summaries', () => {
        const alerts = buildObservabilityAlerts(BASE_SUMMARY);

        expect(alerts.map(alert => alert.title)).toEqual([
            '检测到失败运行',
            '模型/供应商异常集中',
            '阶段成功率偏低',
            '供应商成功率偏低',
        ]);
        expect(alerts[0].detail).toBe('最近 3 轮中有 1 轮失败，成功率 66.67%。');
        expect(alerts[1].detail).toBe('最近 3 轮中有 1 轮与模型配置、供应商额度、鉴权或网络有关。最高频错误：LLM_ERROR x1。');
        expect(alerts[2].detail).toBe('TEST_DESIGN / CLARIFY 成功率 50%，失败 1/2 轮。');
        expect(alerts[3].detail).toBe('api.test.com 成功率 66.67%，失败 1/3 轮。');
    });

    it('returns no alerts for healthy observability summaries', () => {
        const alerts = buildObservabilityAlerts({
            totals: {
                turns: 5,
                failedTurns: 0,
                successRate: 100,
                avgDurationMs: 900,
                estimatedTokens: 1200,
                providerIssueCount: 0,
                providerIssueCodes: {},
            },
            diagnostics: [],
            byStage: [
                {
                    workflowId: 'TEST_DESIGN',
                    stageId: 'CLARIFY',
                    turns: 5,
                    failedTurns: 0,
                    successRate: 100,
                    avgDurationMs: 900,
                    estimatedTokens: 1200,
                    providerIssueCount: 0,
                    providerIssueCodes: {},
                    errorCodes: {},
                },
            ],
            byProvider: [
                {
                    provider: 'api.test.com',
                    turns: 5,
                    failedTurns: 0,
                    successRate: 100,
                    avgDurationMs: 900,
                    estimatedTokens: 1200,
                    providerIssueCount: 0,
                    providerIssueCodes: {},
                    errorCodes: {},
                },
            ],
            recentTurns: [],
        });

        expect(alerts).toEqual([]);
    });

    it('builds provider issue alerts even when success rate is healthy', () => {
        const alerts = buildObservabilityAlerts({
            ...BASE_SUMMARY,
            totals: {
                ...BASE_SUMMARY.totals,
                turns: 10,
                failedTurns: 1,
                successRate: 90,
                providerIssueCount: 1,
                providerIssueCodes: { LLM_ERROR: 1 },
            },
            byStage: [
                {
                    ...BASE_SUMMARY.byStage[0],
                    turns: 10,
                    failedTurns: 1,
                    successRate: 90,
                    providerIssueCount: 1,
                    providerIssueCodes: { LLM_ERROR: 1 },
                },
            ],
            byProvider: [
                {
                    ...BASE_SUMMARY.byProvider[0],
                    turns: 10,
                    failedTurns: 1,
                    successRate: 90,
                    providerIssueCount: 1,
                    providerIssueCodes: { LLM_ERROR: 1 },
                },
            ],
        });

        expect(alerts.map(alert => alert.title)).toEqual([
            '检测到失败运行',
            '模型/供应商异常集中',
        ]);
    });
});
