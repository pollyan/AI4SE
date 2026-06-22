import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { TestAssetsPage } from '../TestAssetsPage';
import {
    createTestAssetRisk,
    deleteTestAssetRisk,
    fetchTestAssetCollection,
    recordTestAssetIntentTesterCase,
    recordTestAssetIntentTesterExecution,
    recordTestAssetIntentTesterResult,
    updateTestAssetCase,
    updateTestAssetIssueStatus,
    updateTestAssetPoint,
    updateTestAssetRiskById,
} from '../../services/testAssetService';
import { importIntentTesterDraft } from '../../services/intentTesterImportService';
import {
    createIntentTesterExecution,
    fetchIntentTesterExecutionDetail,
    fetchLatestIntentTesterExecution,
} from '../../services/intentTesterExecutionService';
import type { TestAssetCollection } from '../../store';

vi.mock('../../services/testAssetService', () => ({
    createTestAssetRisk: vi.fn(),
    deleteTestAssetRisk: vi.fn(),
    fetchTestAssetCollection: vi.fn(),
    recordTestAssetIntentTesterCase: vi.fn(),
    recordTestAssetIntentTesterExecution: vi.fn(),
    recordTestAssetIntentTesterResult: vi.fn(),
    updateTestAssetCase: vi.fn(),
    updateTestAssetIssueStatus: vi.fn(),
    updateTestAssetPoint: vi.fn(),
    updateTestAssetRiskById: vi.fn(),
}));

vi.mock('../../services/intentTesterImportService', () => ({
    importIntentTesterDraft: vi.fn(),
}));

vi.mock('../../services/intentTesterExecutionService', () => ({
    createIntentTesterExecution: vi.fn(),
    fetchIntentTesterExecutionDetail: vi.fn(),
    fetchLatestIntentTesterExecution: vi.fn(),
}));

const TEST_ASSET_COLLECTION: TestAssetCollection = {
    id: 7,
    runId: 'run-123',
    workflowId: 'TEST_DESIGN',
    sourceStageId: 'CASES',
    sourceArtifactVersion: 2,
    coverageSummary: {
        totalTestCases: 2,
        totalTestPoints: 2,
        coveredTestPoints: 1,
        partiallyCoveredTestPoints: 0,
        uncoveredTestPoints: 1,
        coverageRate: 50,
        byPriority: [
            {
                priority: 'P0',
                total: 1,
                covered: 1,
                partial: 0,
                uncovered: 0,
                coverageRate: 100,
            },
            {
                priority: 'P1',
                total: 1,
                covered: 0,
                partial: 0,
                uncovered: 1,
                coverageRate: 0,
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
        {
            id: 'TC-002',
            title: '用户登录失败提示错误',
            priority: 'P1',
            dimension: '异常功能验证',
            testPoint: '登录异常链路',
            risk: 'R-LOGIN-002',
            precondition: '用户已注册',
            steps: '1. 输入错误密码',
            testData: '错误密码',
            expectedResult: '提示账号或密码错误',
            versionNumber: 1,
            versions: [],
        },
    ],
    testPoints: [
        {
            testPoint: '登录主链路',
            priority: 'P0',
            risk: 'R-LOGIN-001',
            testCases: ['TC-001'],
            status: '已覆盖',
        },
        {
            testPoint: '登录异常链路',
            priority: 'P1',
            risk: 'R-LOGIN-002',
            testCases: [],
            status: '未覆盖',
        },
    ],
    coverageTrace: [],
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
    riskMatrix: [
        {
            id: 11,
            risk: 'R-LOGIN-002',
            isManual: false,
            testCases: ['TC-002'],
            testPoints: ['登录异常链路'],
            priorities: ['P1'],
            dimensions: ['异常功能验证'],
            coverageStatuses: ['未覆盖'],
            status: 'open',
            owner: '',
            note: '',
        },
    ],
    intentTesterDrafts: [],
    intentTesterMappings: [],
};

const LARGE_TEST_ASSET_COLLECTION: TestAssetCollection = {
    ...TEST_ASSET_COLLECTION,
    coverageSummary: {
        ...TEST_ASSET_COLLECTION.coverageSummary,
        totalTestCases: 7,
    },
    testCases: [
        TEST_ASSET_COLLECTION.testCases[0],
        TEST_ASSET_COLLECTION.testCases[1],
        {
            id: 'TC-003',
            title: '管理员登录成功',
            priority: 'P0',
            dimension: '正向功能验证',
            testPoint: '管理员主链路',
            risk: 'R-ADMIN-001',
            precondition: '管理员已注册',
            steps: '1. 输入管理员账号密码',
            testData: '管理员账号',
            expectedResult: '进入管理员工作台',
            versionNumber: 1,
            versions: [],
        },
        {
            id: 'TC-004',
            title: '用户退出登录成功',
            priority: 'P2',
            dimension: '正向功能验证',
            testPoint: '退出登录链路',
            risk: 'R-LOGOUT-001',
            precondition: '用户已登录',
            steps: '1. 点击退出',
            testData: '无',
            expectedResult: '返回登录页',
            versionNumber: 1,
            versions: [],
        },
        {
            id: 'TC-005',
            title: '用户连续失败后提示锁定',
            priority: 'P1',
            dimension: '异常功能验证',
            testPoint: '登录锁定链路',
            risk: 'R-LOGIN-LOCK',
            precondition: '用户已注册',
            steps: '1. 连续输入错误密码',
            testData: '错误密码',
            expectedResult: '提示账号已锁定',
            versionNumber: 1,
            versions: [],
        },
        {
            id: 'TC-006',
            title: '用户重置密码成功',
            priority: 'P1',
            dimension: '正向功能验证',
            testPoint: '密码重置链路',
            risk: 'R-PASSWORD-001',
            precondition: '用户邮箱可用',
            steps: '1. 点击忘记密码',
            testData: 'user@example.com',
            expectedResult: '密码重置成功',
            versionNumber: 1,
            versions: [],
        },
        {
            id: 'TC-007',
            title: '用户登录失败审计记录',
            priority: 'P2',
            dimension: '审计验证',
            testPoint: '登录审计链路',
            risk: 'R-AUDIT-001',
            precondition: '审计服务可用',
            steps: '1. 输入错误密码',
            testData: '错误密码',
            expectedResult: '生成失败审计记录',
            versionNumber: 1,
            versions: [],
        },
    ],
};

const TEST_ASSET_COLLECTION_WITH_INTENT_TESTER_DRAFT: TestAssetCollection = {
    ...TEST_ASSET_COLLECTION,
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
            draftWarnings: ['导入前需要人工校准 URL'],
        },
    ],
};

const TEST_ASSET_COLLECTION_WITH_INTENT_TESTER_MAPPING: TestAssetCollection = {
    ...TEST_ASSET_COLLECTION_WITH_INTENT_TESTER_DRAFT,
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
            latestResult: null,
        },
    ],
};

const INTENT_TESTER_RESULT_SNAPSHOT = {
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
};

const TEST_ASSET_COLLECTION_WITH_INTENT_TESTER_RESULT: TestAssetCollection = {
    ...TEST_ASSET_COLLECTION_WITH_INTENT_TESTER_MAPPING,
    intentTesterMappings: [
        {
            ...TEST_ASSET_COLLECTION_WITH_INTENT_TESTER_MAPPING.intentTesterMappings[0],
            latestResult: INTENT_TESTER_RESULT_SNAPSHOT,
        },
    ],
};

const LocationProbe = () => {
    const location = useLocation();
    return <div data-testid="asset-center-location">{location.search}</div>;
};

const renderPage = (path = '/test-assets/7') => render(
    <MemoryRouter initialEntries={[path]}>
        <LocationProbe />
        <Routes>
            <Route path="/test-assets/:collectionId" element={<TestAssetsPage />} />
        </Routes>
    </MemoryRouter>
);

describe('TestAssetsPage', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        vi.mocked(fetchTestAssetCollection).mockResolvedValue(TEST_ASSET_COLLECTION);
        vi.mocked(updateTestAssetCase).mockResolvedValue({
            ...TEST_ASSET_COLLECTION.testCases[1],
            priority: 'P0',
            versionNumber: 2,
        });
        vi.mocked(updateTestAssetIssueStatus).mockResolvedValue({
            ...TEST_ASSET_COLLECTION.assetIssues[0],
            status: 'confirmed',
        });
        vi.mocked(updateTestAssetPoint).mockResolvedValue({
            testPoint: '登录异常链路',
            priority: 'P0',
            risk: 'R-LOGIN-LOCK',
            testCases: ['TC-002'],
            status: '已覆盖',
        });
        vi.mocked(createTestAssetRisk).mockResolvedValue({
            id: 21,
            risk: 'R-MANUAL-001',
            isManual: true,
            testCases: [],
            testPoints: [],
            priorities: [],
            dimensions: [],
            coverageStatuses: [],
            status: 'open',
            owner: 'QA 王五',
            note: '',
        });
        vi.mocked(updateTestAssetRiskById).mockResolvedValue({
            ...TEST_ASSET_COLLECTION.riskMatrix[0],
            risk: 'R-LOGIN-LOCK',
            status: 'mitigating',
        });
        vi.mocked(deleteTestAssetRisk).mockResolvedValue({ id: 21, deleted: true });
        vi.mocked(recordTestAssetIntentTesterCase).mockResolvedValue({
            sourceCaseId: 'TC-001',
            intentTesterCaseId: 42,
            intentTesterCaseName: 'TC-001 用户登录成功',
            latestExecution: null,
            latestResult: null,
        });
        vi.mocked(recordTestAssetIntentTesterExecution).mockResolvedValue(
            TEST_ASSET_COLLECTION_WITH_INTENT_TESTER_MAPPING.intentTesterMappings[0],
        );
        vi.mocked(recordTestAssetIntentTesterResult).mockResolvedValue(
            TEST_ASSET_COLLECTION_WITH_INTENT_TESTER_RESULT.intentTesterMappings[0],
        );
        vi.mocked(importIntentTesterDraft).mockResolvedValue({
            id: 42,
            name: 'TC-001 用户登录成功',
        });
        vi.mocked(createIntentTesterExecution).mockResolvedValue({
            executionId: 'exec-123',
            status: 'pending',
            testcaseName: 'TC-001 用户登录成功',
            startTime: '2026-06-19T10:00:00',
        });
        vi.mocked(fetchLatestIntentTesterExecution).mockResolvedValue({
            executionId: 'exec-456',
            testCaseId: 42,
            status: 'success',
            mode: 'headless',
            browser: 'chrome',
            startTime: '2026-06-19T10:00:00',
            endTime: '2026-06-19T10:01:00',
            duration: 60,
            errorMessage: null,
        });
        vi.mocked(fetchIntentTesterExecutionDetail).mockResolvedValue({
            executionId: 'exec-456',
            testCaseId: 42,
            status: 'failed',
            mode: 'headless',
            browser: 'chrome',
            startTime: '2026-06-19T10:00:00',
            endTime: '2026-06-19T10:01:00',
            duration: 60,
            errorMessage: '断言失败',
            stepsTotal: 2,
            stepsPassed: 1,
            stepsFailed: 1,
            steps: [
                {
                    stepIndex: 0,
                    description: '打开登录页',
                    status: 'success',
                    errorMessage: null,
                    screenshotPath: '/static/screenshots/step-0.png',
                    action: 'ai_assert',
                },
                {
                    stepIndex: 1,
                    description: '验证预期结果',
                    status: 'failed',
                    errorMessage: '未看到工作台',
                    screenshotPath: '/static/screenshots/step-1.png',
                    action: 'ai_assert',
                },
            ],
        });
    });

    it('loads and displays the materialized Lisa test asset collection', async () => {
        renderPage();

        expect(await screen.findByText('Lisa 测试资产中心')).toBeTruthy();
        expect(fetchTestAssetCollection).toHaveBeenCalledWith(7);
        expect(screen.getByText('覆盖率 50%')).toBeTruthy();
        expect(screen.getByText('质量状态')).toBeTruthy();
        expect(screen.getByText('需修复')).toBeTruthy();
        expect(screen.getByText('1 个资产问题待处理')).toBeTruthy();
        expect(screen.getByText('1 个测试点未覆盖')).toBeTruthy();
        expect(screen.getByText(/先处理阻断项/)).toBeTruthy();
        expect(screen.getByText('用户登录成功')).toBeTruthy();
        expect(screen.getByText('用户登录失败提示错误')).toBeTruthy();
        expect(screen.getByText('覆盖追溯引用了不存在的测试用例 TC-999')).toBeTruthy();
        expect(screen.getAllByText('R-LOGIN-002').length).toBeGreaterThan(0);
        expect(screen.getAllByText('登录异常链路').length).toBeGreaterThan(0);
    });

    it('shows an explicit error when the collection cannot be loaded', async () => {
        renderPage('/test-assets/not-a-number');

        expect(await screen.findByText('无法加载测试资产集合')).toBeTruthy();
        expect(fetchTestAssetCollection).not.toHaveBeenCalled();
    });

    it('restores list controls from the URL query', async () => {
        vi.mocked(fetchTestAssetCollection).mockResolvedValueOnce(LARGE_TEST_ASSET_COLLECTION);

        renderPage('/test-assets/7?q=失败&priority=P1&sort=risk&direction=desc&pageSize=5&page=1');

        expect(await screen.findByText('Lisa 测试资产中心')).toBeTruthy();
        expect(screen.getByLabelText('搜索测试用例')).toHaveProperty('value', '失败');
        expect(screen.getByLabelText('优先级过滤')).toHaveProperty('value', 'P1');
        expect(screen.getByLabelText('排序字段')).toHaveProperty('value', 'risk');
        expect(screen.getByLabelText('排序方向')).toHaveProperty('value', 'desc');
        expect(screen.getByLabelText('每页数量')).toHaveProperty('value', '5');
        expect(screen.getByTestId('test-asset-case-TC-005')).toBeTruthy();
        expect(screen.getByTestId('test-asset-case-TC-002')).toBeTruthy();
        expect(screen.queryByTestId('test-asset-case-TC-001')).toBeNull();
    });

    it('paginates sorted test cases and persists page changes in the URL', async () => {
        vi.mocked(fetchTestAssetCollection).mockResolvedValueOnce(LARGE_TEST_ASSET_COLLECTION);

        renderPage('/test-assets/7?pageSize=5&sort=id');

        expect(await screen.findByTestId('test-asset-case-TC-001')).toBeTruthy();
        expect(screen.queryByTestId('test-asset-case-TC-006')).toBeNull();
        fireEvent.click(screen.getByRole('button', { name: '下一页' }));

        expect(await screen.findByTestId('test-asset-case-TC-006')).toBeTruthy();
        expect(screen.getByTestId('asset-center-location').textContent).toContain('page=2');
    });

    it('selects all only on the current page', async () => {
        vi.mocked(fetchTestAssetCollection).mockResolvedValueOnce(LARGE_TEST_ASSET_COLLECTION);

        renderPage('/test-assets/7?pageSize=5');

        await screen.findByTestId('test-asset-case-TC-001');
        fireEvent.click(screen.getByRole('button', { name: '选择全部' }));
        fireEvent.click(screen.getByRole('button', { name: '更新选中用例' }));

        await waitFor(() => {
            expect(updateTestAssetCase).toHaveBeenCalledTimes(5);
        });
        expect(updateTestAssetCase).not.toHaveBeenCalledWith(
            7,
            'TC-006',
            expect.anything(),
        );
    });

    it('batch updates only selected test asset cases', async () => {
        renderPage();

        await screen.findByText('用户登录失败提示错误');
        fireEvent.click(screen.getByLabelText('选择 TC-002'));
        fireEvent.change(screen.getByLabelText('批量优先级'), {
            target: { value: 'P0' },
        });
        fireEvent.click(screen.getByRole('button', { name: '更新选中用例' }));

        await waitFor(() => {
            expect(updateTestAssetCase).toHaveBeenCalledTimes(1);
        });
        expect(updateTestAssetCase).toHaveBeenCalledWith(7, 'TC-002', {
            title: '用户登录失败提示错误',
            priority: 'P0',
        });
        expect(await screen.findByText('已更新 1 条测试用例')).toBeTruthy();

        const updatedCase = screen.getByTestId('test-asset-case-TC-002');
        expect(within(updatedCase).getByText('P0')).toBeTruthy();
        expect(within(updatedCase).getByText('版本 2')).toBeTruthy();

        const untouchedCase = screen.getByTestId('test-asset-case-TC-001');
        expect(within(untouchedCase).getByText('P0')).toBeTruthy();
        expect(within(untouchedCase).getByText('版本 1')).toBeTruthy();
    });

    it('filters test asset cases by search query and priority', async () => {
        renderPage();

        await screen.findByText('用户登录失败提示错误');
        fireEvent.change(screen.getByLabelText('搜索测试用例'), {
            target: { value: '失败' },
        });

        expect(screen.queryByTestId('test-asset-case-TC-001')).toBeNull();
        expect(screen.getByTestId('test-asset-case-TC-002')).toBeTruthy();
        expect(screen.getByText('显示 1-1 / 过滤后 1 条 / 总计 2 条')).toBeTruthy();

        fireEvent.change(screen.getByLabelText('搜索测试用例'), {
            target: { value: '' },
        });
        fireEvent.change(screen.getByLabelText('优先级过滤'), {
            target: { value: 'P0' },
        });

        expect(screen.getByTestId('test-asset-case-TC-001')).toBeTruthy();
        expect(screen.queryByTestId('test-asset-case-TC-002')).toBeNull();
    });

    it('edits full test asset case details in the asset center', async () => {
        vi.mocked(updateTestAssetCase).mockResolvedValueOnce({
            ...TEST_ASSET_COLLECTION.testCases[1],
            testPoint: '登录锁定链路',
            expectedResult: '提示账号已锁定',
            versionNumber: 2,
        });

        renderPage();

        await screen.findByText('用户登录失败提示错误');
        fireEvent.click(screen.getByRole('button', { name: '编辑 TC-002' }));
        fireEvent.change(screen.getByLabelText('测试点'), {
            target: { value: '登录锁定链路' },
        });
        fireEvent.change(screen.getByLabelText('预期结果'), {
            target: { value: '提示账号已锁定' },
        });
        fireEvent.click(screen.getByRole('button', { name: '保存用例' }));

        await waitFor(() => {
            expect(updateTestAssetCase).toHaveBeenCalledTimes(1);
        });
        expect(updateTestAssetCase).toHaveBeenCalledWith(7, 'TC-002', {
            title: '用户登录失败提示错误',
            priority: 'P1',
            dimension: '异常功能验证',
            testPoint: '登录锁定链路',
            risk: 'R-LOGIN-002',
            precondition: '用户已注册',
            steps: '1. 输入错误密码',
            testData: '错误密码',
            expectedResult: '提示账号已锁定',
        });
        const updatedCase = await screen.findByTestId('test-asset-case-TC-002');
        expect(within(updatedCase).getByText('登录锁定链路')).toBeTruthy();
        expect(within(updatedCase).getByText('提示账号已锁定')).toBeTruthy();
        expect(within(updatedCase).getByText('版本 2')).toBeTruthy();
    });

    it('imports an intent-tester draft creates an execution record and refreshes status from the asset center', async () => {
        vi.mocked(fetchTestAssetCollection).mockResolvedValueOnce(
            TEST_ASSET_COLLECTION_WITH_INTENT_TESTER_DRAFT,
        );
        vi.mocked(recordTestAssetIntentTesterExecution)
            .mockResolvedValueOnce({
                sourceCaseId: 'TC-001',
                intentTesterCaseId: 42,
                intentTesterCaseName: 'TC-001 用户登录成功',
                latestExecution: {
                    executionId: 'exec-123',
                    testCaseId: 42,
                    status: 'pending',
                    mode: 'headless',
                    browser: 'chrome',
                    startTime: '2026-06-19T10:00:00',
                    endTime: null,
                    duration: null,
                    errorMessage: null,
                },
                latestResult: null,
            })
            .mockResolvedValueOnce(
                TEST_ASSET_COLLECTION_WITH_INTENT_TESTER_MAPPING.intentTesterMappings[0],
            );
        vi.mocked(recordTestAssetIntentTesterCase).mockImplementationOnce(async () => {
            await new Promise(resolve => setTimeout(resolve, 0));
            return {
                sourceCaseId: 'TC-001',
                intentTesterCaseId: 42,
                intentTesterCaseName: 'TC-001 用户登录成功',
                latestExecution: null,
                latestResult: null,
            };
        });

        renderPage();

        const caseCard = await screen.findByTestId('test-asset-case-TC-001');
        expect(within(caseCard).getByText('1 条 intent-tester 草稿')).toBeTruthy();
        expect(within(caseCard).getByText('导入前需要人工校准 URL')).toBeTruthy();

        fireEvent.click(within(caseCard).getByRole('button', {
            name: '导入 intent-tester TC-001',
        }));

        await waitFor(() => {
            expect(importIntentTesterDraft).toHaveBeenCalledWith(
                TEST_ASSET_COLLECTION_WITH_INTENT_TESTER_DRAFT.intentTesterDrafts[0],
            );
        });
        expect(recordTestAssetIntentTesterCase).toHaveBeenCalledWith(7, 'TC-001', {
            intentTesterCaseId: 42,
            intentTesterCaseName: 'TC-001 用户登录成功',
        });
        const importedCaseCard = screen.getByTestId('test-asset-case-TC-001');
        expect(await within(importedCaseCard).findByText('已导入 intent-tester #42')).toBeTruthy();

        fireEvent.click(screen.getByRole('button', { name: '创建执行记录 #42' }));

        await waitFor(() => {
            expect(createIntentTesterExecution).toHaveBeenCalledWith(42);
        });
        expect(recordTestAssetIntentTesterExecution).toHaveBeenCalledWith(7, 'TC-001', {
            executionId: 'exec-123',
            testCaseId: 42,
            status: 'pending',
            mode: 'headless',
            browser: 'chrome',
            startTime: '2026-06-19T10:00:00',
            endTime: null,
            duration: null,
            errorMessage: null,
        });
        expect(within(screen.getByTestId('test-asset-case-TC-001'))
            .getByText('最近执行 exec-123 · pending')).toBeTruthy();

        fireEvent.click(screen.getByRole('button', { name: '刷新执行结果 #42' }));

        await waitFor(() => {
            expect(fetchLatestIntentTesterExecution).toHaveBeenCalledWith(42);
        });
        expect(recordTestAssetIntentTesterExecution).toHaveBeenCalledWith(7, 'TC-001', {
            executionId: 'exec-456',
            testCaseId: 42,
            status: 'success',
            mode: 'headless',
            browser: 'chrome',
            startTime: '2026-06-19T10:00:00',
            endTime: '2026-06-19T10:01:00',
            duration: 60,
            errorMessage: null,
        });
        expect(within(screen.getByTestId('test-asset-case-TC-001'))
            .getByText('最近执行 exec-456 · success')).toBeTruthy();
        expect(screen.getByRole('link', { name: '去执行 #42' }).getAttribute('href'))
            .toBe('/intent-tester/execution?testcase_id=42');
    });

    it('restores persisted intent-tester mapping and latest execution in the asset center', async () => {
        vi.mocked(fetchTestAssetCollection).mockResolvedValueOnce(
            TEST_ASSET_COLLECTION_WITH_INTENT_TESTER_MAPPING,
        );

        renderPage();

        const caseCard = await screen.findByTestId('test-asset-case-TC-001');
        expect(within(caseCard).getByText('已导入 intent-tester #42')).toBeTruthy();
        expect(within(caseCard).getByText('最近执行 exec-456 · success')).toBeTruthy();
        expect(within(caseCard).getByRole('link', { name: '去执行 #42' }).getAttribute('href'))
            .toBe('/intent-tester/execution?testcase_id=42');
    });

    it('records an intent-tester execution result snapshot from the asset center', async () => {
        vi.mocked(fetchTestAssetCollection).mockResolvedValueOnce(
            TEST_ASSET_COLLECTION_WITH_INTENT_TESTER_MAPPING,
        );

        renderPage();

        await screen.findByText('最近执行 exec-456 · success');
        fireEvent.click(screen.getByRole('button', { name: '承接执行结果 #exec-456' }));

        await waitFor(() => {
            expect(fetchIntentTesterExecutionDetail).toHaveBeenCalledWith('exec-456');
        });
        expect(recordTestAssetIntentTesterResult).toHaveBeenCalledWith(
            7,
            'TC-001',
            INTENT_TESTER_RESULT_SNAPSHOT,
        );
        const caseCard = screen.getByTestId('test-asset-case-TC-001');
        expect(within(caseCard).getByText('执行结果 failed · 通过 1 / 2 · 失败 1')).toBeTruthy();
        expect(within(caseCard).getByText('失败步骤 1 验证预期结果')).toBeTruthy();
        expect(within(caseCard).getByText('未看到工作台')).toBeTruthy();
        expect(within(caseCard).getByText('截图 2')).toBeTruthy();
    });

    it('restores persisted intent-tester result snapshot in the asset center', async () => {
        vi.mocked(fetchTestAssetCollection).mockResolvedValueOnce(
            TEST_ASSET_COLLECTION_WITH_INTENT_TESTER_RESULT,
        );

        renderPage();

        const caseCard = await screen.findByTestId('test-asset-case-TC-001');
        expect(within(caseCard).getByText('执行结果 failed · 通过 1 / 2 · 失败 1')).toBeTruthy();
        expect(within(caseCard).getByText('失败步骤 1 验证预期结果')).toBeTruthy();
        expect(within(caseCard).getByText('截图 2')).toBeTruthy();
    });

    it('triages asset issues in the asset center', async () => {
        renderPage();

        await screen.findByText('覆盖追溯引用了不存在的测试用例 TC-999');
        fireEvent.click(screen.getByRole('button', { name: '确认问题' }));

        await waitFor(() => {
            expect(updateTestAssetIssueStatus).toHaveBeenCalledWith(7, 5, 'confirmed');
        });
        const issue = screen.getByTestId('asset-issue-5');
        expect(within(issue).getByText('已确认')).toBeTruthy();
        expect(screen.queryByText('1 个资产问题待处理')).toBeNull();
        expect(screen.getByText('1 个测试点未覆盖')).toBeTruthy();
    });

    it('edits a test point and refreshes derived coverage and risk matrix', async () => {
        const updatedCollection: TestAssetCollection = {
            ...TEST_ASSET_COLLECTION,
            coverageSummary: {
                ...TEST_ASSET_COLLECTION.coverageSummary,
                coveredTestPoints: 2,
                uncoveredTestPoints: 0,
                coverageRate: 100,
            },
            testPoints: TEST_ASSET_COLLECTION.testPoints.map(testPoint => (
                testPoint.testPoint === '登录异常链路'
                    ? {
                        ...testPoint,
                        priority: 'P0',
                        risk: 'R-LOGIN-LOCK',
                        testCases: ['TC-002'],
                        status: '已覆盖',
                    }
                    : testPoint
            )),
            riskMatrix: [
                {
                    id: 12,
                    risk: 'R-LOGIN-LOCK',
                    isManual: false,
                    testCases: ['TC-002'],
                    testPoints: ['登录异常链路'],
                    priorities: ['P0'],
                    dimensions: [],
                    coverageStatuses: ['已覆盖'],
                    status: 'open',
                    owner: '',
                    note: '',
                },
            ],
        };
        vi.mocked(fetchTestAssetCollection)
            .mockResolvedValueOnce(TEST_ASSET_COLLECTION)
            .mockResolvedValueOnce(updatedCollection);

        renderPage();

        await screen.findByText('Lisa 测试资产中心');
        fireEvent.click(screen.getByRole('button', { name: '编辑测试点 登录异常链路' }));
        fireEvent.change(screen.getByLabelText('测试点优先级'), {
            target: { value: 'P0' },
        });
        fireEvent.change(screen.getByLabelText('测试点覆盖状态'), {
            target: { value: '已覆盖' },
        });
        fireEvent.change(screen.getByLabelText('测试点关联风险'), {
            target: { value: 'R-LOGIN-LOCK' },
        });
        fireEvent.change(screen.getByLabelText('测试点覆盖用例'), {
            target: { value: 'TC-002' },
        });
        fireEvent.click(screen.getByRole('button', { name: '保存测试点' }));

        await waitFor(() => {
            expect(updateTestAssetPoint).toHaveBeenCalledWith(7, '登录异常链路', {
                priority: 'P0',
                risk: 'R-LOGIN-LOCK',
                status: '已覆盖',
                testCases: ['TC-002'],
            });
        });
        expect(fetchTestAssetCollection).toHaveBeenCalledTimes(2);
        expect(await screen.findByText('已保存测试点 登录异常链路')).toBeTruthy();
        expect(screen.getByText('覆盖率 100%')).toBeTruthy();
        expect(screen.getAllByText('R-LOGIN-LOCK').length).toBeGreaterThan(0);
        const editedPoint = screen.getByTestId('test-asset-point-登录异常链路');
        expect(within(editedPoint).getByText('P0 · 已覆盖')).toBeTruthy();
        expect(within(editedPoint).getByText('用例 TC-002')).toBeTruthy();
    });

    it('edits risk lifecycle status owner and note in the asset center', async () => {
        const updatedCollection: TestAssetCollection = {
            ...TEST_ASSET_COLLECTION,
            riskMatrix: [
                {
                    ...TEST_ASSET_COLLECTION.riskMatrix[0],
                    status: 'mitigating',
                    owner: 'QA 赵六',
                    note: '补充异常登录覆盖',
                },
            ],
        };
        vi.mocked(fetchTestAssetCollection)
            .mockResolvedValueOnce(TEST_ASSET_COLLECTION)
            .mockResolvedValueOnce(updatedCollection);
        vi.mocked(updateTestAssetRiskById).mockResolvedValueOnce(updatedCollection.riskMatrix[0]);

        renderPage();

        await screen.findByText('Lisa 测试资产中心');
        fireEvent.click(screen.getByRole('button', { name: '编辑风险 R-LOGIN-002' }));
        fireEvent.change(screen.getByLabelText('风险处置状态'), {
            target: { value: 'mitigating' },
        });
        fireEvent.change(screen.getByLabelText('风险责任人'), {
            target: { value: 'QA 赵六' },
        });
        fireEvent.change(screen.getByLabelText('风险处置备注'), {
            target: { value: '补充异常登录覆盖' },
        });
        fireEvent.click(screen.getByRole('button', { name: '保存风险' }));

        await waitFor(() => {
            expect(updateTestAssetRiskById).toHaveBeenCalledWith(7, 11, {
                risk: 'R-LOGIN-002',
                status: 'mitigating',
                owner: 'QA 赵六',
                note: '补充异常登录覆盖',
            });
        });
        expect(await screen.findByText('已保存风险 R-LOGIN-002')).toBeTruthy();
        const risk = screen.getByTestId('test-asset-risk-11');
        expect(within(risk).getByText('缓解中')).toBeTruthy();
        expect(within(risk).getByText('责任人 QA 赵六')).toBeTruthy();
        expect(within(risk).getByText('备注 补充异常登录覆盖')).toBeTruthy();
    });

    it('creates a manual risk in the asset center', async () => {
        renderPage();

        await screen.findByText('Lisa 测试资产中心');
        fireEvent.change(screen.getByLabelText('新增风险名称'), {
            target: { value: 'R-MANUAL-001' },
        });
        fireEvent.change(screen.getByLabelText('新增风险责任人'), {
            target: { value: 'QA 王五' },
        });
        fireEvent.click(screen.getByRole('button', { name: '新增风险' }));

        await waitFor(() => {
            expect(createTestAssetRisk).toHaveBeenCalledWith(7, {
                risk: 'R-MANUAL-001',
                owner: 'QA 王五',
                note: '',
                status: 'open',
            });
        });
        expect(await screen.findByText('已新增风险 R-MANUAL-001')).toBeTruthy();
        const risk = screen.getByTestId('test-asset-risk-21');
        expect(within(risk).getByText('R-MANUAL-001')).toBeTruthy();
        expect(within(risk).getByText('手工风险')).toBeTruthy();
    });

    it('renames a linked risk and refreshes derived assets', async () => {
        const updatedCollection: TestAssetCollection = {
            ...TEST_ASSET_COLLECTION,
            testCases: TEST_ASSET_COLLECTION.testCases.map(testCase => (
                testCase.id === 'TC-002'
                    ? {
                        ...testCase,
                        risk: 'R-LOGIN-LOCK',
                        versionNumber: 2,
                    }
                    : testCase
            )),
            testPoints: TEST_ASSET_COLLECTION.testPoints.map(testPoint => (
                testPoint.testPoint === '登录异常链路'
                    ? { ...testPoint, risk: 'R-LOGIN-LOCK' }
                    : testPoint
            )),
            riskMatrix: [
                {
                    ...TEST_ASSET_COLLECTION.riskMatrix[0],
                    risk: 'R-LOGIN-LOCK',
                    status: 'mitigating',
                },
            ],
        };
        vi.mocked(fetchTestAssetCollection)
            .mockResolvedValueOnce(TEST_ASSET_COLLECTION)
            .mockResolvedValueOnce(updatedCollection);
        vi.mocked(updateTestAssetRiskById).mockResolvedValueOnce(updatedCollection.riskMatrix[0]);

        renderPage();

        await screen.findByText('Lisa 测试资产中心');
        fireEvent.click(screen.getByRole('button', { name: '编辑风险 R-LOGIN-002' }));
        fireEvent.change(screen.getByLabelText('风险名称'), {
            target: { value: 'R-LOGIN-LOCK' },
        });
        fireEvent.change(screen.getByLabelText('风险处置状态'), {
            target: { value: 'mitigating' },
        });
        fireEvent.click(screen.getByRole('button', { name: '保存风险' }));

        await waitFor(() => {
            expect(updateTestAssetRiskById).toHaveBeenCalledWith(7, 11, {
                risk: 'R-LOGIN-LOCK',
                status: 'mitigating',
                owner: '',
                note: '',
            });
        });
        expect(fetchTestAssetCollection).toHaveBeenCalledTimes(2);
        expect(await screen.findByText('已保存风险 R-LOGIN-LOCK')).toBeTruthy();
        expect(screen.getAllByText('R-LOGIN-LOCK').length).toBeGreaterThan(0);
        expect(within(screen.getByTestId('test-asset-case-TC-002')).getByText('版本 2')).toBeTruthy();
    });

    it('deletes an unlinked manual risk', async () => {
        const collectionWithManualRisk: TestAssetCollection = {
            ...TEST_ASSET_COLLECTION,
            riskMatrix: [
                ...TEST_ASSET_COLLECTION.riskMatrix,
                {
                    id: 21,
                    risk: 'R-MANUAL-001',
                    isManual: true,
                    testCases: [],
                    testPoints: [],
                    priorities: [],
                    dimensions: [],
                    coverageStatuses: [],
                    status: 'open',
                    owner: 'QA 王五',
                    note: '',
                },
            ],
        };
        vi.mocked(fetchTestAssetCollection).mockResolvedValueOnce(collectionWithManualRisk);

        renderPage();

        await screen.findByTestId('test-asset-risk-21');
        fireEvent.click(screen.getByRole('button', { name: '删除风险 R-MANUAL-001' }));

        await waitFor(() => {
            expect(deleteTestAssetRisk).toHaveBeenCalledWith(7, 21);
        });
        expect(await screen.findByText('已删除风险 R-MANUAL-001')).toBeTruthy();
        expect(screen.queryByTestId('test-asset-risk-21')).toBeNull();
    });
});
