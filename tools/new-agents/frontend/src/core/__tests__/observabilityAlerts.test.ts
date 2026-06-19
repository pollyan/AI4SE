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
            errorCodes: { SCHEMA_VALIDATION_FAILED: 1 },
        },
        {
            workflowId: 'VALUE_DISCOVERY',
            stageId: 'BLUEPRINT',
            turns: 1,
            failedTurns: 0,
            successRate: 100,
            avgDurationMs: 800,
            estimatedTokens: 200,
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
            errorCodes: { SCHEMA_VALIDATION_FAILED: 1 },
        },
    ],
    recentTurns: [],
};

describe('buildObservabilityAlerts', () => {
    it('builds total, stage, and provider alerts from failing observability summaries', () => {
        const alerts = buildObservabilityAlerts(BASE_SUMMARY);

        expect(alerts.map(alert => alert.title)).toEqual([
            '检测到失败运行',
            '阶段成功率偏低',
            '供应商成功率偏低',
        ]);
        expect(alerts[0].detail).toBe('最近 3 轮中有 1 轮失败，成功率 66.67%。');
        expect(alerts[1].detail).toBe('TEST_DESIGN / CLARIFY 成功率 50%，失败 1/2 轮。');
        expect(alerts[2].detail).toBe('api.test.com 成功率 66.67%，失败 1/3 轮。');
    });

    it('returns no alerts for healthy observability summaries', () => {
        const alerts = buildObservabilityAlerts({
            totals: {
                turns: 5,
                failedTurns: 0,
                successRate: 100,
                avgDurationMs: 900,
                estimatedTokens: 1200,
            },
            byStage: [
                {
                    workflowId: 'TEST_DESIGN',
                    stageId: 'CLARIFY',
                    turns: 5,
                    failedTurns: 0,
                    successRate: 100,
                    avgDurationMs: 900,
                    estimatedTokens: 1200,
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
                    errorCodes: {},
                },
            ],
            recentTurns: [],
        });

        expect(alerts).toEqual([]);
    });
});
