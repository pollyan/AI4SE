import { describe, expect, it } from 'vitest';
import type { TestAssetCollection } from '../types';
import { withTestAssetQualitySummary } from '../testAssetQuality';

const buildCollection = (
    patch: Partial<TestAssetCollection> = {},
): TestAssetCollection => ({
    id: 7,
    runId: 'run-123',
    workflowId: 'TEST_DESIGN',
    sourceStageId: 'CASES',
    sourceArtifactVersion: 1,
    coverageSummary: {
        totalTestCases: 1,
        totalTestPoints: 1,
        coveredTestPoints: 0,
        partiallyCoveredTestPoints: 1,
        uncoveredTestPoints: 0,
        coverageRate: 0,
        byPriority: [],
    },
    qualitySummary: {
        status: 'attention',
        label: '需要关注',
        pendingIssueCount: 0,
        confirmedIssueCount: 0,
        ignoredIssueCount: 0,
        uncoveredTestPointCount: 0,
        partialTestPointCount: 1,
        openRiskCount: 1,
        mitigatingRiskCount: 0,
        acceptedRiskCount: 0,
        closedRiskCount: 0,
        gates: [],
    },
    testCases: [],
    testPoints: [
        {
            testPoint: '登录异常链路',
            priority: 'P1',
            risk: 'R-LOGIN-002',
            testCases: ['TC-002'],
            status: '部分覆盖',
        },
    ],
    coverageTrace: [],
    assetIssues: [],
    riskMatrix: [
        {
            id: 11,
            risk: 'R-LOGIN-002',
            isManual: false,
            testCases: ['TC-002'],
            testPoints: ['登录异常链路'],
            priorities: ['P1'],
            dimensions: ['异常功能验证'],
            coverageStatuses: ['部分覆盖'],
            status: 'open',
            owner: '',
            note: '',
        },
    ],
    intentTesterDrafts: [],
    intentTesterMappings: [],
    ...patch,
});

describe('testAssetQuality', () => {
    it('marks a collection blocked when pending issues or uncovered points remain', () => {
        const collection = buildCollection({
            assetIssues: [
                {
                    id: 5,
                    type: 'unknown_coverage_case',
                    caseId: 'TC-999',
                    message: '覆盖追溯引用了不存在的测试用例 TC-999',
                    status: 'pending',
                },
            ],
            testPoints: [
                {
                    testPoint: '登录异常链路',
                    priority: 'P1',
                    risk: 'R-LOGIN-002',
                    testCases: [],
                    status: '未覆盖',
                },
            ],
        });

        const updated = withTestAssetQualitySummary(collection);

        expect(updated.qualitySummary.status).toBe('blocked');
        expect(updated.qualitySummary.label).toBe('存在阻断');
        expect(updated.qualitySummary.pendingIssueCount).toBe(1);
        expect(updated.qualitySummary.uncoveredTestPointCount).toBe(1);
        expect(updated.qualitySummary.gates.map(gate => gate.status)).toEqual([
            'fail',
            'fail',
            'warn',
        ]);
    });

    it('marks a collection attention when only confirmed issues, partial coverage, or open risks remain', () => {
        const collection = buildCollection({
            assetIssues: [
                {
                    id: 5,
                    type: 'unknown_coverage_case',
                    caseId: 'TC-999',
                    message: '覆盖追溯引用了不存在的测试用例 TC-999',
                    status: 'confirmed',
                },
            ],
        });

        const updated = withTestAssetQualitySummary(collection);

        expect(updated.qualitySummary.status).toBe('attention');
        expect(updated.qualitySummary.label).toBe('需要关注');
        expect(updated.qualitySummary.confirmedIssueCount).toBe(1);
        expect(updated.qualitySummary.partialTestPointCount).toBe(1);
        expect(updated.qualitySummary.openRiskCount).toBe(1);
    });

    it('marks a collection ready when issues are ignored, points covered, and risks accepted', () => {
        const collection = buildCollection({
            assetIssues: [
                {
                    id: 5,
                    type: 'unknown_coverage_case',
                    caseId: 'TC-999',
                    message: '覆盖追溯引用了不存在的测试用例 TC-999',
                    status: 'ignored',
                },
            ],
            testPoints: [
                {
                    testPoint: '登录异常链路',
                    priority: 'P1',
                    risk: 'R-LOGIN-002',
                    testCases: ['TC-002'],
                    status: '已覆盖',
                },
            ],
            riskMatrix: [
                {
                    id: 11,
                    risk: 'R-LOGIN-002',
                    isManual: false,
                    testCases: ['TC-002'],
                    testPoints: ['登录异常链路'],
                    priorities: ['P1'],
                    dimensions: ['异常功能验证'],
                    coverageStatuses: ['已覆盖'],
                    status: 'accepted',
                    owner: 'QA',
                    note: '业务接受残余风险',
                },
            ],
        });

        const updated = withTestAssetQualitySummary(collection);

        expect(updated.qualitySummary.status).toBe('ready');
        expect(updated.qualitySummary.label).toBe('可交付');
        expect(updated.qualitySummary.ignoredIssueCount).toBe(1);
        expect(updated.qualitySummary.acceptedRiskCount).toBe(1);
        expect(updated.qualitySummary.gates.every(gate => gate.status === 'pass')).toBe(true);
    });
});
