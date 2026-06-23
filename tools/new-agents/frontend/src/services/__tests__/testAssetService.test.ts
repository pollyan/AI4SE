import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
    createTestAssetRisk,
    deleteTestAssetRisk,
    fetchTestAssetCollection,
    materializeRunTestAssets,
    recordTestAssetIntentTesterCase,
    recordTestAssetIntentTesterExecution,
    recordTestAssetIntentTesterResult,
    updateTestAssetCase,
    updateTestAssetIssueStatus,
    updateTestAssetPoint,
    updateTestAssetRisk,
    updateTestAssetRiskById,
} from '../testAssetService';

global.fetch = vi.fn();

const COLLECTION_PAYLOAD = {
    id: 7,
    runId: 'run-123',
    workflowId: 'TEST_DESIGN',
    sourceStageId: 'CASES',
    sourceArtifactVersion: 2,
    coverageSummary: {
        totalTestCases: 1,
        totalTestPoints: 1,
        coveredTestPoints: 1,
        partiallyCoveredTestPoints: 0,
        uncoveredTestPoints: 0,
        coverageRate: 100,
        byPriority: [],
    },
    qualitySummary: {
        status: 'ready',
        label: '可交付',
        pendingIssueCount: 0,
        confirmedIssueCount: 0,
        ignoredIssueCount: 0,
        uncoveredTestPointCount: 0,
        partialTestPointCount: 0,
        openRiskCount: 0,
        mitigatingRiskCount: 0,
        acceptedRiskCount: 1,
        closedRiskCount: 0,
        gates: [
            {
                id: 'asset-issues',
                status: 'pass',
                title: '资产问题',
                detail: '0 个待处理，0 个已确认，0 个已忽略',
            },
        ],
    },
    testCases: [
        {
            id: 'TC-001',
            title: '用户登录成功',
            priority: 'P0',
            dimension: '正向功能验证',
            testPoint: '登录主链路',
            risk: 'R-LOGIN-001',
            precondition: '用户已注册',
            steps: '1. 输入账号密码',
            testData: '正确账号密码',
            expectedResult: '进入工作台',
            versionNumber: 1,
            versions: [],
        },
    ],
    testPoints: [],
    coverageTrace: [],
    assetIssues: [],
    riskMatrix: [],
    intentTesterDrafts: [
        {
            sourceCaseId: 'TC-001',
            name: 'TC-001 用户登录成功',
            description: '来源: New Agents Lisa TEST_DESIGN/CASES',
            category: '正向功能验证',
            priority: 1,
            tags: ['lisa', 'new-agents', 'TC-001'],
            steps: [
                {
                    action: 'ai_assert',
                    params: { prompt: '验证预期结果：进入工作台' },
                },
            ],
            draftWarnings: ['导入前需要人工校准'],
        },
    ],
    intentTesterMappings: [
        {
            sourceCaseId: 'TC-001',
            intentTesterCaseId: 42,
            intentTesterCaseName: 'TC-001 用户登录成功',
            latestExecution: {
                executionId: 'exec-456',
                testCaseId: 42,
                status: 'success',
                mode: 'headless',
                browser: 'chrome',
                startTime: '2026-06-19T10:00:00',
                endTime: '2026-06-19T10:01:00',
                duration: 60,
                errorMessage: null,
            },
            latestResult: {
                executionId: 'exec-456',
                status: 'failed',
                stepsTotal: 2,
                stepsPassed: 1,
                stepsFailed: 1,
                duration: 60,
                errorMessage: '断言失败',
                screenshots: [
                    '/static/screenshots/step-0.png',
                    '/static/screenshots/step-1.png',
                ],
                failedSteps: [
                    {
                        stepIndex: 1,
                        description: '验证预期结果',
                        status: 'failed',
                        errorMessage: '未看到工作台',
                        screenshotPath: '/static/screenshots/step-1.png',
                        action: 'ai_assert',
                    },
                ],
            },
        },
    ],
};

const RISK_PAYLOAD = {
    id: 11,
    risk: 'R-LOGIN-001',
    isManual: false,
    testCases: ['TC-001'],
    testPoints: ['登录主链路'],
    priorities: ['P0'],
    dimensions: ['正向功能验证'],
    coverageStatuses: ['已覆盖'],
    status: 'open',
    owner: '',
    note: '',
};

describe('testAssetService', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('materializes Lisa test assets for a persisted run', async () => {
        vi.mocked(fetch).mockResolvedValue(new Response(
            JSON.stringify(COLLECTION_PAYLOAD),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
        ));

        const collection = await materializeRunTestAssets('run-123');

        expect(fetch).toHaveBeenCalledWith(
            '/new-agents/api/agent/runs/run-123/test-assets/materialize',
            { method: 'POST' },
        );
        expect(collection.id).toBe(7);
        expect(collection.testCases[0].id).toBe('TC-001');
        expect(collection.coverageSummary.coverageRate).toBe(100);
        expect(collection.qualitySummary.status).toBe('ready');
        expect(collection.qualitySummary.gates[0].id).toBe('asset-issues');
        expect(collection.intentTesterDrafts[0].sourceCaseId).toBe('TC-001');
        expect(collection.intentTesterMappings[0].intentTesterCaseId).toBe(42);
        expect(collection.intentTesterMappings[0].latestExecution?.executionId).toBe('exec-456');
        expect(collection.intentTesterMappings[0].latestResult?.stepsFailed).toBe(1);
    });

    it('fetches a materialized test asset collection by id', async () => {
        vi.mocked(fetch).mockResolvedValue(new Response(
            JSON.stringify(COLLECTION_PAYLOAD),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
        ));

        const collection = await fetchTestAssetCollection(7);

        expect(fetch).toHaveBeenCalledWith('/new-agents/api/agent/test-assets/7');
        expect(collection.id).toBe(7);
        expect(collection.runId).toBe('run-123');
    });

    it('records the persisted intent-tester testcase mapping for a Lisa source case', async () => {
        vi.mocked(fetch).mockResolvedValue(new Response(
            JSON.stringify({
                sourceCaseId: 'TC-001',
                intentTesterCaseId: 42,
                intentTesterCaseName: 'TC-001 用户登录成功',
                latestExecution: null,
                latestResult: null,
            }),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
        ));

        const mapping = await recordTestAssetIntentTesterCase(7, 'TC-001', {
            intentTesterCaseId: 42,
            intentTesterCaseName: 'TC-001 用户登录成功',
        });

        expect(fetch).toHaveBeenCalledWith(
            '/new-agents/api/agent/test-assets/7/intent-tester/cases/TC-001',
            {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    intentTesterCaseId: 42,
                    intentTesterCaseName: 'TC-001 用户登录成功',
                }),
            },
        );
        expect(mapping.intentTesterCaseId).toBe(42);
        expect(mapping.latestExecution).toBeNull();
    });

    it('records the latest intent-tester execution for a Lisa source case', async () => {
        vi.mocked(fetch).mockResolvedValue(new Response(
            JSON.stringify(COLLECTION_PAYLOAD.intentTesterMappings[0]),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
        ));

        const execution = COLLECTION_PAYLOAD.intentTesterMappings[0].latestExecution;
        const mapping = await recordTestAssetIntentTesterExecution(7, 'TC-001', execution);

        expect(fetch).toHaveBeenCalledWith(
            '/new-agents/api/agent/test-assets/7/intent-tester/cases/TC-001/execution',
            {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    executionId: 'exec-456',
                    status: 'success',
                    mode: 'headless',
                    browser: 'chrome',
                    startTime: '2026-06-19T10:00:00',
                    endTime: '2026-06-19T10:01:00',
                    duration: 60,
                    errorMessage: null,
                }),
            },
        );
        expect(mapping.latestExecution?.executionId).toBe('exec-456');
    });

    it('records an intent-tester execution result snapshot for a Lisa source case', async () => {
        vi.mocked(fetch).mockResolvedValue(new Response(
            JSON.stringify(COLLECTION_PAYLOAD.intentTesterMappings[0]),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
        ));

        const result = COLLECTION_PAYLOAD.intentTesterMappings[0].latestResult;
        const mapping = await recordTestAssetIntentTesterResult(7, 'TC-001', result);

        expect(fetch).toHaveBeenCalledWith(
            '/new-agents/api/agent/test-assets/7/intent-tester/cases/TC-001/result',
            {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(result),
            },
        );
        expect(mapping.latestResult?.failedSteps[0].description).toBe('验证预期结果');
    });

    it('parses risk stable id and manual flag from a collection', async () => {
        vi.mocked(fetch).mockResolvedValue(new Response(
            JSON.stringify({
                ...COLLECTION_PAYLOAD,
                riskMatrix: [RISK_PAYLOAD],
            }),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
        ));

        const collection = await fetchTestAssetCollection(7);

        expect(collection.riskMatrix[0].id).toBe(11);
        expect(collection.riskMatrix[0].isManual).toBe(false);
        expect(collection.riskMatrix[0].risk).toBe('R-LOGIN-001');
    });

    it('updates a test case in a materialized collection', async () => {
        vi.mocked(fetch).mockResolvedValue(new Response(
            JSON.stringify({
                ...COLLECTION_PAYLOAD.testCases[0],
                title: '登录成功后进入首页',
                priority: 'P1',
                versionNumber: 2,
            }),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
        ));

        const updated = await updateTestAssetCase(7, 'TC-001', {
            title: '登录成功后进入首页',
            priority: 'P1',
        });

        expect(fetch).toHaveBeenCalledWith(
            '/new-agents/api/agent/test-assets/7/test-cases/TC-001',
            {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    title: '登录成功后进入首页',
                    priority: 'P1',
                }),
            },
        );
        expect(updated.title).toBe('登录成功后进入首页');
        expect(updated.versionNumber).toBe(2);
    });

    it('updates a test asset issue status in a materialized collection', async () => {
        vi.mocked(fetch).mockResolvedValue(new Response(
            JSON.stringify({
                id: 5,
                type: 'unknown_coverage_case',
                caseId: 'TC-999',
                testPoint: '登录异常链路',
                message: '覆盖追溯引用了不存在的测试用例 TC-999',
                status: 'confirmed',
            }),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
        ));

        const updated = await updateTestAssetIssueStatus(7, 5, 'confirmed');

        expect(fetch).toHaveBeenCalledWith(
            '/new-agents/api/agent/test-assets/7/issues/5',
            {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status: 'confirmed' }),
            },
        );
        expect(updated.status).toBe('confirmed');
        expect(updated.caseId).toBe('TC-999');
    });

    it('updates a test point calibration in a materialized collection', async () => {
        vi.mocked(fetch).mockResolvedValue(new Response(
            JSON.stringify({
                testPoint: '登录异常链路',
                priority: 'P0',
                risk: 'R-LOGIN-LOCK',
                testCases: ['TC-002'],
                status: '已覆盖',
            }),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
        ));

        const updated = await updateTestAssetPoint(7, '登录异常链路', {
            priority: 'P0',
            risk: 'R-LOGIN-LOCK',
            testCases: ['TC-002'],
            status: '已覆盖',
        });

        expect(fetch).toHaveBeenCalledWith(
            '/new-agents/api/agent/test-assets/7/test-points/%E7%99%BB%E5%BD%95%E5%BC%82%E5%B8%B8%E9%93%BE%E8%B7%AF',
            {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    priority: 'P0',
                    risk: 'R-LOGIN-LOCK',
                    testCases: ['TC-002'],
                    status: '已覆盖',
                }),
            },
        );
        expect(updated.testPoint).toBe('登录异常链路');
        expect(updated.testCases).toEqual(['TC-002']);
    });

    it('fails explicitly when an updated test point payload is malformed', async () => {
        vi.mocked(fetch).mockResolvedValue(new Response(
            JSON.stringify({ testPoint: '登录异常链路', testCases: 'broken' }),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
        ));

        await expect(updateTestAssetPoint(7, '登录异常链路', {
            status: '已覆盖',
        })).rejects.toThrow('Invalid test asset point response');
    });

    it('updates a risk lifecycle in a materialized collection', async () => {
        vi.mocked(fetch).mockResolvedValue(new Response(
            JSON.stringify({
                id: 11,
                risk: 'R-登录-001',
                isManual: false,
                testCases: ['TC-001'],
                testPoints: ['登录主链路'],
                priorities: ['P0'],
                dimensions: ['正向功能验证'],
                coverageStatuses: ['已覆盖'],
                status: 'mitigating',
                owner: 'QA 赵六',
                note: '补充异常登录覆盖',
            }),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
        ));

        const updated = await updateTestAssetRisk(7, 'R-登录-001', {
            status: 'mitigating',
            owner: 'QA 赵六',
            note: '补充异常登录覆盖',
        });

        expect(fetch).toHaveBeenCalledWith(
            '/new-agents/api/agent/test-assets/7/risks/R-%E7%99%BB%E5%BD%95-001',
            {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    status: 'mitigating',
                    owner: 'QA 赵六',
                    note: '补充异常登录覆盖',
                }),
            },
        );
        expect(updated.status).toBe('mitigating');
        expect(updated.owner).toBe('QA 赵六');
        expect(updated.note).toBe('补充异常登录覆盖');
    });

    it('creates a manual risk in a materialized collection', async () => {
        vi.mocked(fetch).mockResolvedValue(new Response(
            JSON.stringify({
                ...RISK_PAYLOAD,
                id: 21,
                risk: 'R-MANUAL-001',
                isManual: true,
                testCases: [],
                testPoints: [],
            }),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
        ));

        const created = await createTestAssetRisk(7, {
            risk: 'R-MANUAL-001',
            owner: 'QA 王五',
        });

        expect(fetch).toHaveBeenCalledWith(
            '/new-agents/api/agent/test-assets/7/risks',
            {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    risk: 'R-MANUAL-001',
                    owner: 'QA 王五',
                }),
            },
        );
        expect(created.id).toBe(21);
        expect(created.isManual).toBe(true);
    });

    it('updates a risk by stable id in a materialized collection', async () => {
        vi.mocked(fetch).mockResolvedValue(new Response(
            JSON.stringify({
                ...RISK_PAYLOAD,
                risk: 'R-LOGIN-LOCK',
                status: 'mitigating',
            }),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
        ));

        const updated = await updateTestAssetRiskById(7, 11, {
            risk: 'R-LOGIN-LOCK',
            status: 'mitigating',
        });

        expect(fetch).toHaveBeenCalledWith(
            '/new-agents/api/agent/test-assets/7/risks/by-id/11',
            {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    risk: 'R-LOGIN-LOCK',
                    status: 'mitigating',
                }),
            },
        );
        expect(updated.id).toBe(11);
        expect(updated.risk).toBe('R-LOGIN-LOCK');
    });

    it('deletes a risk by stable id in a materialized collection', async () => {
        vi.mocked(fetch).mockResolvedValue(new Response(
            JSON.stringify({ id: 21, deleted: true }),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
        ));

        const deleted = await deleteTestAssetRisk(7, 21);

        expect(fetch).toHaveBeenCalledWith(
            '/new-agents/api/agent/test-assets/7/risks/by-id/21',
            { method: 'DELETE' },
        );
        expect(deleted).toEqual({ id: 21, deleted: true });
    });

    it('fails explicitly when an updated risk lifecycle payload is malformed', async () => {
        vi.mocked(fetch).mockResolvedValue(new Response(
            JSON.stringify({ risk: 'R-登录-001', status: 'blocked' }),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
        ));

        await expect(updateTestAssetRisk(7, 'R-登录-001', {
            status: 'closed',
        })).rejects.toThrow('Invalid test asset risk response');
    });

    it('fails explicitly when a risk payload is missing stable id', async () => {
        vi.mocked(fetch).mockResolvedValue(new Response(
            JSON.stringify({
                ...COLLECTION_PAYLOAD,
                riskMatrix: [{ ...RISK_PAYLOAD, id: undefined }],
            }),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
        ));

        await expect(fetchTestAssetCollection(7)).rejects.toThrow(
            'Invalid test asset collection response'
        );
    });

    it('fails explicitly when a collection payload is malformed', async () => {
        vi.mocked(fetch).mockResolvedValue(new Response(
            JSON.stringify({ id: 7, testCases: 'broken' }),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
        ));

        await expect(materializeRunTestAssets('run-123')).rejects.toThrow(
            'Invalid test asset collection response'
        );
    });

    it('fails explicitly when a collection payload is missing quality summary', async () => {
        const { qualitySummary: _qualitySummary, ...payload } = COLLECTION_PAYLOAD;
        vi.mocked(fetch).mockResolvedValue(new Response(
            JSON.stringify(payload),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
        ));

        await expect(fetchTestAssetCollection(7)).rejects.toThrow(
            'Invalid test asset collection response'
        );
    });

    it('fails explicitly when quality summary gates are malformed', async () => {
        vi.mocked(fetch).mockResolvedValue(new Response(
            JSON.stringify({
                ...COLLECTION_PAYLOAD,
                qualitySummary: {
                    ...COLLECTION_PAYLOAD.qualitySummary,
                    gates: [{ id: 'asset-issues', status: 'unknown' }],
                },
            }),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
        ));

        await expect(fetchTestAssetCollection(7)).rejects.toThrow(
            'Invalid test asset collection response'
        );
    });
});
