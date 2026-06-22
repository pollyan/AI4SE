import { describe, expect, it } from 'vitest';
import { deriveTestAssetQualityStatus } from '../testAssetQuality';
import type { TestAssetCollection } from '../types';

const baseCollection: TestAssetCollection = {
    id: 7,
    runId: 'run-123',
    workflowId: 'TEST_DESIGN',
    sourceStageId: 'CASES',
    sourceArtifactVersion: 2,
    coverageSummary: {
        totalTestCases: 2,
        totalTestPoints: 2,
        coveredTestPoints: 2,
        partiallyCoveredTestPoints: 0,
        uncoveredTestPoints: 0,
        coverageRate: 100,
        byPriority: [],
    },
    testCases: [],
    testPoints: [
        {
            testPoint: '登录主链路',
            priority: 'P0',
            risk: 'R-LOGIN-001',
            testCases: ['TC-001'],
            status: '已覆盖',
        },
    ],
    coverageTrace: [],
    assetIssues: [],
    riskMatrix: [
        {
            id: 11,
            risk: 'R-LOGIN-001',
            isManual: false,
            testCases: ['TC-001'],
            testPoints: ['登录主链路'],
            priorities: ['P0'],
            dimensions: ['正向功能验证'],
            coverageStatuses: ['已覆盖'],
            status: 'closed',
            owner: 'QA 王五',
            note: '已覆盖',
        },
    ],
    intentTesterDrafts: [],
    intentTesterMappings: [],
};

describe('deriveTestAssetQualityStatus', () => {
    it('marks assets blocked when pending issues uncovered points or unowned open risks remain', () => {
        const summary = deriveTestAssetQualityStatus({
            ...baseCollection,
            coverageSummary: {
                ...baseCollection.coverageSummary,
                coveredTestPoints: 0,
                uncoveredTestPoints: 1,
                coverageRate: 0,
            },
            assetIssues: [
                {
                    id: 5,
                    type: 'unknown_coverage_case',
                    caseId: 'TC-999',
                    testPoint: '登录异常链路',
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
            riskMatrix: [
                {
                    ...baseCollection.riskMatrix[0],
                    risk: 'R-LOGIN-002',
                    status: 'open',
                    owner: '',
                    testCases: [],
                    testPoints: ['登录异常链路'],
                    coverageStatuses: ['未覆盖'],
                },
            ],
        });

        expect(summary.status).toBe('blocked');
        expect(summary.label).toBe('需修复');
        expect(summary.blockingItems).toEqual([
            '1 个资产问题待处理',
            '1 个测试点未覆盖',
            '1 个开放风险未分配责任人',
        ]);
        expect(summary.nextAction).toContain('先处理阻断项');
    });

    it('marks assets attention when issues are triaged but partial coverage or accepted risks remain', () => {
        const summary = deriveTestAssetQualityStatus({
            ...baseCollection,
            assetIssues: [
                {
                    id: 5,
                    type: 'unknown_coverage_case',
                    message: '覆盖追溯引用了不存在的测试用例 TC-999',
                    status: 'confirmed',
                },
            ],
            testPoints: [
                {
                    testPoint: '登录异常链路',
                    priority: 'P1',
                    risk: 'R-LOGIN-002',
                    testCases: ['TC-002'],
                    status: '部分覆盖',
                },
            ],
            riskMatrix: [
                {
                    ...baseCollection.riskMatrix[0],
                    risk: 'R-LOGIN-002',
                    status: 'accepted',
                    owner: 'QA 王五',
                    coverageStatuses: ['部分覆盖'],
                },
            ],
        });

        expect(summary.status).toBe('attention');
        expect(summary.label).toBe('需关注');
        expect(summary.blockingItems).toEqual([]);
        expect(summary.attentionItems).toEqual([
            '1 个测试点部分覆盖',
            '1 个风险已接受',
        ]);
        expect(summary.nextAction).toContain('复核关注项');
    });

    it('marks assets ready when coverage issues and risks are closed', () => {
        const summary = deriveTestAssetQualityStatus(baseCollection);

        expect(summary.status).toBe('ready');
        expect(summary.label).toBe('可交付');
        expect(summary.blockingItems).toEqual([]);
        expect(summary.attentionItems).toEqual([]);
        expect(summary.nextAction).toBe('可以进入交付评审或 intent-tester 导入执行。');
    });
});
