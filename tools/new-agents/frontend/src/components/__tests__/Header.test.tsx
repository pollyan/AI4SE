import { describe, it, expect, beforeEach, vi } from 'vitest';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { Header } from '../Header';
import { useStore } from '../../store';
import { BrowserRouter } from 'react-router-dom';

// Mock react-router-dom navigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
    const actual = await vi.importActual('react-router-dom');
    return {
        ...actual,
        useNavigate: () => mockNavigate,
        useParams: () => ({ agentId: 'lisa' }),
    };
});

// Mock WorkflowDropdown
vi.mock('../WorkflowDropdown', () => ({
    WorkflowDropdown: () => <div data-testid="workflow-dropdown" />,
}));

vi.mock('../../services/runSnapshotService', () => ({
    cloneRun: vi.fn(),
    createRunDecisionSummary: vi.fn(),
    fetchRunList: vi.fn(),
    updateRunContextSummary: vi.fn(),
}));

vi.mock('../../services/testAssetService', () => ({
    materializeRunTestAssets: vi.fn(),
    updateTestAssetCase: vi.fn(),
    updateTestAssetIssueStatus: vi.fn(),
}));

vi.mock('../../services/observabilityService', () => ({
    fetchObservabilitySummary: vi.fn(),
}));

vi.mock('../../services/intentTesterImportService', () => ({
    importIntentTesterDraft: vi.fn(),
}));

vi.mock('../../services/configService', () => ({
    checkDefaultLlmConfig: vi.fn(),
}));

// Mock lucide-react icons to avoid SVG complexity
vi.mock('lucide-react', () => {
    const icons = ['Settings', 'Share', 'Bot', 'Plus', 'AlertTriangle', 'ArrowLeft', 'ChevronRight', 'History', 'Search', 'ClipboardList', 'Save', 'Activity', 'Upload', 'FileText', 'MoreHorizontal'];
    const mod: Record<string, React.FC> = {};
    icons.forEach(name => {
        mod[name] = () => <span>{name}</span>;
    });
    return mod;
});

import { cloneRun, createRunDecisionSummary, fetchRunList, updateRunContextSummary } from '../../services/runSnapshotService';
import { materializeRunTestAssets, updateTestAssetCase, updateTestAssetIssueStatus } from '../../services/testAssetService';
import { fetchObservabilitySummary } from '../../services/observabilityService';
import { importIntentTesterDraft } from '../../services/intentTesterImportService';
import { checkDefaultLlmConfig } from '../../services/configService';
import type { ObservabilitySummary, TestAssetCollection } from '../../store';

const TEST_ASSET_COLLECTION: TestAssetCollection = {
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
    intentTesterMappings: [],
};

const TEST_ASSET_COLLECTION_WITH_TWO_DRAFTS: TestAssetCollection = {
    ...TEST_ASSET_COLLECTION,
    coverageSummary: {
        ...TEST_ASSET_COLLECTION.coverageSummary,
        totalTestCases: 2,
    },
    testCases: [
        TEST_ASSET_COLLECTION.testCases[0],
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
    intentTesterDrafts: [
        TEST_ASSET_COLLECTION.intentTesterDrafts[0],
        {
            sourceCaseId: 'TC-002',
            name: 'TC-002 用户登录失败提示错误',
            description: '来源: New Agents Lisa TEST_DESIGN/CASES',
            category: '异常功能验证',
            priority: 2,
            tags: ['lisa', 'new-agents', 'TC-002'],
            steps: [
                {
                    action: 'ai_assert',
                    params: { prompt: '验证预期结果：提示账号或密码错误' },
                },
            ],
            draftWarnings: ['导入前需要人工校准'],
        },
    ],
};

const TEST_ASSET_COLLECTION_WITH_ISSUES: TestAssetCollection = {
    ...TEST_ASSET_COLLECTION,
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
};

const TEST_ASSET_COLLECTION_WITH_RISK_MATRIX: TestAssetCollection = {
    ...TEST_ASSET_COLLECTION,
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
            status: 'open',
            owner: '',
            note: '',
        },
    ],
};

const TEST_ASSET_COLLECTION_WITH_TEST_POINTS: TestAssetCollection = {
    ...TEST_ASSET_COLLECTION,
    testPoints: [
        {
            testPoint: '支付异常链路',
            priority: 'P1',
            risk: 'R-PAY-001',
            testCases: [],
            status: '未覆盖',
        },
    ],
};

const OBSERVABILITY_SUMMARY: ObservabilitySummary = {
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
            createdAt: '2026-06-19T10:00:00',
        },
    ],
};

describe('Header Component', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 0,
            pendingStageTransition: null,
            chatHistory: [],
            artifactContent: '',
            contextSummaries: [],
            currentRunId: null,
        });
        vi.mocked(fetchRunList).mockReset();
        vi.mocked(fetchRunList).mockResolvedValue({
            limit: 20,
            offset: 0,
            total: 0,
            hasMore: false,
            nextOffset: null,
            query: null,
            runs: [],
        });
        vi.mocked(cloneRun).mockReset();
        vi.mocked(cloneRun).mockResolvedValue({
            run: {
                id: 'cloned-run-456',
                workflowId: 'TEST_DESIGN',
                agentId: 'lisa',
                currentStageId: 'STRATEGY',
                status: 'active',
                model: 'test-model',
            },
            messages: [],
            artifacts: [],
            contextSummaries: [],
            artifactComments: [],
            artifactSectionLocks: [],
            artifactAuditEvents: [],
        });
        vi.mocked(updateRunContextSummary).mockReset();
        vi.mocked(updateRunContextSummary).mockResolvedValue({
            sourceType: 'stage',
            sourceStageId: 'CLARIFY',
            summaryType: 'user_supplement',
            content: '服务端保存后的摘要。',
        });
        vi.mocked(createRunDecisionSummary).mockReset();
        vi.mocked(createRunDecisionSummary).mockResolvedValue({
            sourceType: 'artifact',
            sourceStageId: 'CLARIFY',
            summaryType: 'decision',
            content: '决定优先覆盖第三方登录回调失败',
        });
        vi.mocked(materializeRunTestAssets).mockReset();
        vi.mocked(materializeRunTestAssets).mockResolvedValue(TEST_ASSET_COLLECTION);
        vi.mocked(updateTestAssetCase).mockReset();
        vi.mocked(updateTestAssetCase).mockResolvedValue({
            ...TEST_ASSET_COLLECTION.testCases[0],
            title: '登录成功后进入首页',
            priority: 'P1',
            versionNumber: 2,
        });
        vi.mocked(updateTestAssetIssueStatus).mockReset();
        vi.mocked(updateTestAssetIssueStatus).mockResolvedValue({
            ...TEST_ASSET_COLLECTION_WITH_ISSUES.assetIssues[0],
            status: 'confirmed',
        });
        vi.mocked(fetchObservabilitySummary).mockReset();
        vi.mocked(fetchObservabilitySummary).mockResolvedValue(OBSERVABILITY_SUMMARY);
        vi.mocked(importIntentTesterDraft).mockReset();
        vi.mocked(importIntentTesterDraft).mockResolvedValue({
            id: 42,
            name: 'TC-001 用户登录成功',
        });
        vi.mocked(checkDefaultLlmConfig).mockReset();
        vi.mocked(checkDefaultLlmConfig).mockResolvedValue({
            ok: true,
            message: '模型配置可用',
        });
    });

    function renderHeader() {
        return render(
            <BrowserRouter>
                <Header />
            </BrowserRouter>
        );
    }

    function clickMoreAction(name: RegExp | string) {
        fireEvent.click(screen.getByRole('button', { name: /更多操作/ }));
        fireEvent.click(screen.getByRole('button', { name }));
    }

    it('renders the app header with navigation and controls', () => {
        renderHeader();
        expect(screen.getByRole('button', { name: /新会话/ })).toBeTruthy();
        expect(screen.getByRole('button', { name: /历史会话/ })).toBeTruthy();
        expect(screen.getByRole('button', { name: /更多操作/ })).toBeTruthy();
        expect(screen.queryByRole('button', { name: /导出报告/ })).toBeNull();
        expect(screen.queryByRole('button', { name: /上下文摘要/ })).toBeNull();
        expect(screen.queryByRole('button', { name: /运行统计/ })).toBeNull();
        expect(screen.queryByRole('button', { name: /测试资产/ })).toBeNull();
    });

    it('does not render stage transition confirmation in the header when pendingStageTransition exists', () => {
        useStore.setState({ pendingStageTransition: { fromStageIndex: 0, toStageIndex: 1 }, stageIndex: 0 });
        renderHeader();
        expect(screen.queryByText(/AI 建议进入下一阶段/)).toBeNull();
    });

    it('hides stage transition banner when pendingStageTransition is false', () => {
        useStore.setState({ pendingStageTransition: null });
        renderHeader();
        expect(screen.queryByText(/AI 建议进入下一阶段/)).toBeNull();
    });

    it('keeps artifact export out of the header action group', () => {
        renderHeader();

        expect(screen.queryByRole('button', { name: /导出报告/ })).toBeNull();
    });

    it('opens recent runs and navigates to the selected run workspace', async () => {
        vi.mocked(fetchRunList).mockResolvedValue({
            limit: 20,
            offset: 0,
            total: 1,
            hasMore: false,
            nextOffset: null,
            query: null,
            runs: [
                {
                    id: 'alex-run-123',
                    workflowId: 'VALUE_DISCOVERY',
                    agentId: 'alex',
                    currentStageId: 'BLUEPRINT',
                    status: 'active',
                    qualityStatus: 'reusable',
                    model: 'test-model',
                    createdAt: '2026-06-19T09:00:00',
                    updatedAt: '2026-06-19T09:05:00',
                    lastMessage: {
                        role: 'assistant',
                        content: '价值蓝图已完成。',
                        sequenceIndex: 2,
                    },
                    currentArtifact: {
                        stageId: 'BLUEPRINT',
                        versionNumber: 1,
                        summary: 'AI 测试设计助手需求蓝图',
                    },
                },
            ],
        });

        renderHeader();
        fireEvent.click(screen.getByRole('button', { name: /历史会话/ }));

        await waitFor(() => {
            expect(fetchRunList).toHaveBeenCalledWith({ limit: 20 });
        });
        fireEvent.click(await screen.findByRole('button', { name: /价值发现/ }));

        expect(mockNavigate).toHaveBeenCalledWith(
            '/workspace/alex/value-discovery?runId=alex-run-123'
        );
    });

    it('filters recent runs by reusable quality status', async () => {
        renderHeader();
        fireEvent.click(screen.getByRole('button', { name: /历史会话/ }));

        await waitFor(() => {
            expect(fetchRunList).toHaveBeenCalledWith({ limit: 20 });
        });
        fireEvent.change(screen.getByLabelText('复用质量'), {
            target: { value: 'reusable' },
        });

        await waitFor(() => {
            expect(fetchRunList).toHaveBeenLastCalledWith({
                limit: 20,
                qualityStatus: 'reusable',
            });
        });
    });

    it('shows run reuse quality, artifact preview and clones a run as a new session', async () => {
        vi.mocked(fetchRunList).mockResolvedValue({
            limit: 20,
            offset: 0,
            total: 1,
            hasMore: false,
            nextOffset: null,
            query: null,
            runs: [
                {
                    id: 'test-run-123',
                    workflowId: 'TEST_DESIGN',
                    agentId: 'lisa',
                    currentStageId: 'STRATEGY',
                    status: 'active',
                    qualityStatus: 'reusable',
                    model: 'test-model',
                    createdAt: '2026-06-19T10:00:00',
                    updatedAt: '2026-06-19T10:05:00',
                    lastMessage: null,
                    currentArtifact: {
                        stageId: 'STRATEGY',
                        versionNumber: 2,
                        summary: '覆盖登录主链路和异常链路',
                    },
                },
            ],
        });

        renderHeader();
        fireEvent.click(screen.getByRole('button', { name: /历史会话/ }));

        expect(await screen.findByText('可复用')).toBeTruthy();
        expect(screen.getByText('产物预览')).toBeTruthy();
        expect(screen.getByText('STRATEGY · v2')).toBeTruthy();
        expect(screen.getByText('覆盖登录主链路和异常链路')).toBeTruthy();
        fireEvent.click(screen.getByRole('button', { name: /复制为新会话/ }));

        await waitFor(() => {
            expect(cloneRun).toHaveBeenCalledWith('test-run-123');
        });
        expect(mockNavigate).toHaveBeenCalledWith(
            '/workspace/lisa/test-design?runId=cloned-run-456'
        );
    });

    it('shows an error when cloning a recent run fails', async () => {
        vi.mocked(fetchRunList).mockResolvedValue({
            limit: 20,
            offset: 0,
            total: 1,
            hasMore: false,
            nextOffset: null,
            query: null,
            runs: [
                {
                    id: 'test-run-123',
                    workflowId: 'TEST_DESIGN',
                    agentId: 'lisa',
                    currentStageId: 'STRATEGY',
                    status: 'active',
                    qualityStatus: 'reusable',
                    model: 'test-model',
                    createdAt: '2026-06-19T10:00:00',
                    updatedAt: '2026-06-19T10:05:00',
                    lastMessage: null,
                    currentArtifact: {
                        stageId: 'STRATEGY',
                        versionNumber: 2,
                        summary: '覆盖登录主链路和异常链路',
                    },
                },
            ],
        });
        vi.mocked(cloneRun).mockRejectedValue(new Error('failed'));

        renderHeader();
        fireEvent.click(screen.getByRole('button', { name: /历史会话/ }));
        fireEvent.click(await screen.findByRole('button', { name: /复制为新会话/ }));

        expect(await screen.findByText('无法复制历史会话')).toBeTruthy();
        expect(mockNavigate).not.toHaveBeenCalledWith(
            '/workspace/lisa/test-design?runId=cloned-run-456'
        );
    });

    it('opens Lisa test assets and saves an edited test case', async () => {
        useStore.setState({
            workflow: 'TEST_DESIGN',
            currentRunId: 'run-123',
        });

        renderHeader();
        clickMoreAction(/测试资产/);

        await waitFor(() => {
            expect(materializeRunTestAssets).toHaveBeenCalledWith('run-123');
        });
        expect(await screen.findByText('Lisa 测试资产')).toBeTruthy();
        expect(screen.getByText('覆盖率 100%')).toBeTruthy();
        expect(screen.getByText('用户登录成功')).toBeTruthy();

        fireEvent.click(screen.getByRole('button', { name: /编辑 TC-001/ }));
        fireEvent.change(screen.getByLabelText('用例标题'), {
            target: { value: '登录成功后进入首页' },
        });
        fireEvent.change(screen.getByLabelText('优先级'), {
            target: { value: 'P1' },
        });
        fireEvent.click(screen.getByRole('button', { name: /保存用例/ }));

        await waitFor(() => {
            expect(updateTestAssetCase).toHaveBeenCalledWith(7, 'TC-001', {
                title: '登录成功后进入首页',
                priority: 'P1',
            });
        });
        expect(await screen.findByText('版本 2')).toBeTruthy();
        expect(screen.getByText('登录成功后进入首页')).toBeTruthy();
    });

    it('opens the Lisa test asset center from the test assets dialog', async () => {
        useStore.setState({
            workflow: 'TEST_DESIGN',
            currentRunId: 'run-123',
        });

        renderHeader();
        clickMoreAction(/测试资产/);

        await screen.findByText('用户登录成功');
        fireEvent.click(screen.getByRole('button', { name: /打开资产中心/ }));

        expect(mockNavigate).toHaveBeenCalledWith('/test-assets/7');
    });

    it('opens runtime observability summary', async () => {
        renderHeader();
        clickMoreAction(/运行统计/);

        await waitFor(() => {
            expect(fetchObservabilitySummary).toHaveBeenCalledWith({ limit: 20 });
        });
        expect((await screen.findAllByText('成功率 66.67%')).length).toBeGreaterThan(0);
        expect(screen.getByText('TEST_DESIGN / CLARIFY')).toBeTruthy();
        expect(screen.getAllByText('api.test.com').length).toBeGreaterThan(0);
        expect(screen.getAllByText('LLM_ERROR').length).toBeGreaterThan(0);
        expect(screen.getAllByText('模型/供应商问题 x1').length).toBeGreaterThan(0);
        expect(screen.getByText(/run-123/)).toBeTruthy();
    });

    it('opens context summaries and persists calibrated summary content', async () => {
        useStore.setState({
            currentRunId: 'run-123',
            contextSummaries: [
                {
                    sourceType: 'stage',
                    sourceStageId: 'CLARIFY',
                    summaryType: 'user_supplement',
                    content: '用户补充了登录异常场景。',
                },
            ],
        });

        renderHeader();
        clickMoreAction(/上下文摘要/);

        expect(screen.getByText('上下文摘要详情')).toBeTruthy();
        expect(screen.getByText('用户补充')).toBeTruthy();
        expect(screen.getByText('CLARIFY')).toBeTruthy();
        expect(screen.getByDisplayValue('用户补充了登录异常场景。')).toBeTruthy();

        fireEvent.change(screen.getByLabelText('摘要内容'), {
            target: { value: '用户补充了登录异常和锁定场景。' },
        });
        fireEvent.click(screen.getByRole('button', { name: /保存摘要/ }));

        await waitFor(() => {
            expect(updateRunContextSummary).toHaveBeenCalledWith(
                'run-123',
                {
                    sourceType: 'stage',
                    sourceStageId: 'CLARIFY',
                    summaryType: 'user_supplement',
                },
                '用户补充了登录异常和锁定场景。',
            );
        });
        expect(useStore.getState().contextSummaries[0].content).toBe('服务端保存后的摘要。');
        expect(screen.getByDisplayValue('服务端保存后的摘要。')).toBeTruthy();
    });

    it('creates a manual decision summary from the context summary modal', async () => {
        useStore.setState({
            currentRunId: 'run-123',
            contextSummaries: [],
        });

        renderHeader();
        clickMoreAction(/上下文摘要/);
        fireEvent.change(screen.getByLabelText('关键决策内容'), {
            target: { value: '决定优先覆盖第三方登录回调失败' },
        });
        fireEvent.click(screen.getByRole('button', { name: /保存关键决策/ }));

        await waitFor(() => {
            expect(createRunDecisionSummary).toHaveBeenCalledWith(
                'run-123',
                'CLARIFY',
                '决定优先覆盖第三方登录回调失败',
            );
        });
        expect(useStore.getState().contextSummaries).toContainEqual({
            sourceType: 'artifact',
            sourceStageId: 'CLARIFY',
            summaryType: 'decision',
            content: '决定优先覆盖第三方登录回调失败',
        });
        expect(screen.getByText('关键决策')).toBeTruthy();
    });

    it('shows runtime observability alerts', async () => {
        renderHeader();
        clickMoreAction(/运行统计/);

        await waitFor(() => {
            expect(fetchObservabilitySummary).toHaveBeenCalledWith({ limit: 20 });
        });

        expect(await screen.findByText('运行告警')).toBeTruthy();
        expect(screen.getByText('检测到失败运行')).toBeTruthy();
        expect(screen.getByText('阶段成功率偏低')).toBeTruthy();
        expect(screen.getByText('供应商成功率偏低')).toBeTruthy();
        expect(screen.getByText('模型/供应商异常集中')).toBeTruthy();
    });

    it('opens settings from provider issue observability alert', async () => {
        useStore.setState({ isSettingsOpen: false });

        renderHeader();
        clickMoreAction(/运行统计/);

        await screen.findByText('模型/供应商异常集中');
        expect(screen.getByRole('button', { name: '打开模型设置' })).toBeTruthy();
        expect(screen.getByRole('button', { name: '检测连接' })).toBeTruthy();

        fireEvent.click(screen.getByRole('button', { name: '打开模型设置' }));

        expect(useStore.getState().isSettingsOpen).toBe(true);
        expect(screen.getByText('运行统计详情')).toBeTruthy();
    });

    it('checks model connectivity from observability provider alert', async () => {
        vi.mocked(checkDefaultLlmConfig).mockResolvedValue({
            ok: true,
            message: '模型配置可用',
        });

        renderHeader();
        clickMoreAction(/运行统计/);

        await screen.findByText('模型/供应商异常集中');
        fireEvent.click(screen.getByRole('button', { name: '检测连接' }));

        await waitFor(() => {
            expect(checkDefaultLlmConfig).toHaveBeenCalledTimes(1);
        });
        expect(await screen.findByText('模型配置可用')).toBeTruthy();
    });

    it('shows model connectivity check failure from observability provider alert', async () => {
        vi.mocked(checkDefaultLlmConfig).mockResolvedValue({
            ok: false,
            message: 'API Key 无效',
        });

        renderHeader();
        clickMoreAction(/运行统计/);

        await screen.findByText('模型/供应商异常集中');
        fireEvent.click(screen.getByRole('button', { name: '检测连接' }));

        await waitFor(() => {
            expect(checkDefaultLlmConfig).toHaveBeenCalledTimes(1);
        });
        expect(await screen.findByText('API Key 无效')).toBeTruthy();
    });

    it('filters runtime observability by workflow and stage', async () => {
        renderHeader();
        clickMoreAction(/运行统计/);

        await waitFor(() => {
            expect(fetchObservabilitySummary).toHaveBeenCalledWith({ limit: 20 });
        });

        fireEvent.change(screen.getByLabelText('统计工作流'), {
            target: { value: 'TEST_DESIGN' },
        });
        fireEvent.change(screen.getByLabelText('统计阶段'), {
            target: { value: 'CLARIFY' },
        });
        fireEvent.click(screen.getByRole('button', { name: /应用筛选/ }));

        await waitFor(() => {
            expect(fetchObservabilitySummary).toHaveBeenLastCalledWith({
                limit: 20,
                workflowId: 'TEST_DESIGN',
                stageId: 'CLARIFY',
            });
        });
    });

    it('auto-refreshes runtime observability with active filters until the modal closes', async () => {
        renderHeader();
        clickMoreAction(/运行统计/);

        await waitFor(() => {
            expect(fetchObservabilitySummary).toHaveBeenCalledWith({ limit: 20 });
        });

        fireEvent.change(screen.getByLabelText('统计工作流'), {
            target: { value: 'TEST_DESIGN' },
        });
        fireEvent.change(screen.getByLabelText('统计阶段'), {
            target: { value: 'CLARIFY' },
        });
        const autoRefreshToggle = screen.getByLabelText('自动刷新');

        vi.useFakeTimers();
        fireEvent.click(autoRefreshToggle);

        await act(async () => {
            await vi.advanceTimersByTimeAsync(30000);
        });
        expect(fetchObservabilitySummary).toHaveBeenLastCalledWith({
            limit: 20,
            workflowId: 'TEST_DESIGN',
            stageId: 'CLARIFY',
        });

        const callCountAfterRefresh = vi.mocked(fetchObservabilitySummary).mock.calls.length;
        fireEvent.click(screen.getByRole('button', { name: '关闭' }));
        await act(async () => {
            await vi.advanceTimersByTimeAsync(30000);
        });

        expect(fetchObservabilitySummary).toHaveBeenCalledTimes(callCountAfterRefresh);
        vi.useRealTimers();
    });

    it('shows an error when runtime observability cannot be loaded', async () => {
        vi.mocked(fetchObservabilitySummary).mockRejectedValue(new Error('failed'));

        renderHeader();
        clickMoreAction(/运行统计/);

        expect(await screen.findByText('无法加载运行统计')).toBeTruthy();
    });

    it('imports a Lisa test asset draft into intent-tester', async () => {
        useStore.setState({
            workflow: 'TEST_DESIGN',
            currentRunId: 'run-123',
        });

        renderHeader();
        clickMoreAction(/测试资产/);

        await screen.findByText('用户登录成功');
        fireEvent.click(screen.getByRole('button', { name: /导入 TC-001/ }));

        await waitFor(() => {
            expect(importIntentTesterDraft).toHaveBeenCalledWith(
                TEST_ASSET_COLLECTION.intentTesterDrafts[0]
            );
        });
        expect(await screen.findByText('已导入 intent-tester #42')).toBeTruthy();
        expect(screen.getByRole('link', { name: /去执行 #42/ }).getAttribute('href'))
            .toBe('/intent-tester/execution?testcase_id=42');
    });

    it('shows Lisa test asset quality issues', async () => {
        useStore.setState({
            workflow: 'TEST_DESIGN',
            currentRunId: 'run-123',
        });
        vi.mocked(materializeRunTestAssets).mockResolvedValue(TEST_ASSET_COLLECTION_WITH_ISSUES);

        renderHeader();
        clickMoreAction(/测试资产/);

        expect(await screen.findByText('资产问题')).toBeTruthy();
        expect(screen.getByText('1 个问题 · 1 待处理')).toBeTruthy();
        expect(screen.getByText('覆盖追溯引用了不存在的测试用例 TC-999')).toBeTruthy();
        expect(screen.getByText('TC-999')).toBeTruthy();
        expect(screen.getByText('登录异常链路')).toBeTruthy();
        expect(screen.getByText('质量状态')).toBeTruthy();
        expect(screen.getByText('需修复')).toBeTruthy();
        expect(screen.getByText('1 个资产问题待处理')).toBeTruthy();
        expect(screen.getByText(/先处理阻断项/)).toBeTruthy();
    });

    it('triages Lisa test asset quality issue status locally', async () => {
        useStore.setState({
            workflow: 'TEST_DESIGN',
            currentRunId: 'run-123',
        });
        vi.mocked(materializeRunTestAssets).mockResolvedValue(TEST_ASSET_COLLECTION_WITH_ISSUES);

        renderHeader();
        clickMoreAction(/测试资产/);

        expect(await screen.findByText('资产问题')).toBeTruthy();
        expect(screen.getByText('1 个问题 · 1 待处理')).toBeTruthy();
        expect(screen.getByText('待处理')).toBeTruthy();

        fireEvent.click(screen.getByRole('button', { name: '确认问题' }));

        await waitFor(() => {
            expect(updateTestAssetIssueStatus).toHaveBeenCalledWith(7, 5, 'confirmed');
        });
        expect(screen.getByText('1 个问题 · 0 待处理')).toBeTruthy();
        expect(screen.getByText('已确认')).toBeTruthy();

        vi.mocked(updateTestAssetIssueStatus).mockResolvedValueOnce({
            ...TEST_ASSET_COLLECTION_WITH_ISSUES.assetIssues[0],
            status: 'ignored',
        });
        fireEvent.click(screen.getByRole('button', { name: '忽略问题' }));

        await waitFor(() => {
            expect(updateTestAssetIssueStatus).toHaveBeenLastCalledWith(7, 5, 'ignored');
        });
        expect(screen.getByText('忽略')).toBeTruthy();
        expect(screen.getByText('1 个问题 · 0 待处理')).toBeTruthy();
    });

    it('shows Lisa test asset risk matrix', async () => {
        useStore.setState({
            workflow: 'TEST_DESIGN',
            currentRunId: 'run-123',
        });
        vi.mocked(materializeRunTestAssets).mockResolvedValue(TEST_ASSET_COLLECTION_WITH_RISK_MATRIX);

        renderHeader();
        clickMoreAction(/测试资产/);

        expect(await screen.findByText('风险矩阵')).toBeTruthy();
        expect(screen.getByText('R-LOGIN-001')).toBeTruthy();
        expect(screen.getAllByText('TC-001').length).toBeGreaterThan(0);
        expect(screen.getAllByText('登录主链路').length).toBeGreaterThan(0);
        expect(screen.getAllByText('P0').length).toBeGreaterThan(0);
        expect(screen.getByText('已覆盖')).toBeTruthy();
    });

    it('shows Lisa test point coverage details', async () => {
        useStore.setState({
            workflow: 'TEST_DESIGN',
            currentRunId: 'run-123',
        });
        vi.mocked(materializeRunTestAssets).mockResolvedValue(TEST_ASSET_COLLECTION_WITH_TEST_POINTS);

        renderHeader();
        clickMoreAction(/测试资产/);

        expect(await screen.findByText('测试点覆盖')).toBeTruthy();
        expect(screen.getByText('支付异常链路')).toBeTruthy();
        expect(screen.getByText('未覆盖')).toBeTruthy();
        expect(screen.getAllByText('P1').length).toBeGreaterThan(0);
        expect(screen.getByText('R-PAY-001')).toBeTruthy();
        expect(screen.getByText('无关联用例')).toBeTruthy();
    });

    it('batch imports Lisa test asset drafts into intent-tester', async () => {
        useStore.setState({
            workflow: 'TEST_DESIGN',
            currentRunId: 'run-123',
        });
        vi.mocked(materializeRunTestAssets).mockResolvedValue(TEST_ASSET_COLLECTION_WITH_TWO_DRAFTS);
        vi.mocked(importIntentTesterDraft)
            .mockResolvedValueOnce({ id: 42, name: 'TC-001 用户登录成功' })
            .mockResolvedValueOnce({ id: 43, name: 'TC-002 用户登录失败提示错误' });

        renderHeader();
        clickMoreAction(/测试资产/);

        await screen.findByText('用户登录失败提示错误');
        fireEvent.click(screen.getByRole('button', { name: /批量导入草稿/ }));

        await waitFor(() => {
            expect(importIntentTesterDraft).toHaveBeenCalledTimes(2);
        });
        expect(importIntentTesterDraft).toHaveBeenNthCalledWith(
            1,
            TEST_ASSET_COLLECTION_WITH_TWO_DRAFTS.intentTesterDrafts[0]
        );
        expect(importIntentTesterDraft).toHaveBeenNthCalledWith(
            2,
            TEST_ASSET_COLLECTION_WITH_TWO_DRAFTS.intentTesterDrafts[1]
        );
        expect(await screen.findByText('已批量导入 2 条 intent-tester 用例')).toBeTruthy();
        expect(screen.getByText('已导入 intent-tester #42')).toBeTruthy();
        expect(screen.getByText('已导入 intent-tester #43')).toBeTruthy();
    });

    it('batch updates Lisa test asset case priorities', async () => {
        useStore.setState({
            workflow: 'TEST_DESIGN',
            currentRunId: 'run-123',
        });
        vi.mocked(materializeRunTestAssets).mockResolvedValue(TEST_ASSET_COLLECTION_WITH_TWO_DRAFTS);
        vi.mocked(updateTestAssetCase)
            .mockResolvedValueOnce({
                ...TEST_ASSET_COLLECTION_WITH_TWO_DRAFTS.testCases[0],
                priority: 'P1',
                versionNumber: 2,
            })
            .mockResolvedValueOnce({
                ...TEST_ASSET_COLLECTION_WITH_TWO_DRAFTS.testCases[1],
                priority: 'P1',
                versionNumber: 2,
            });

        renderHeader();
        clickMoreAction(/测试资产/);

        await screen.findByText('用户登录失败提示错误');
        fireEvent.change(screen.getByLabelText('批量优先级'), {
            target: { value: 'P1' },
        });
        fireEvent.click(screen.getByRole('button', { name: /应用优先级/ }));

        await waitFor(() => {
            expect(updateTestAssetCase).toHaveBeenCalledTimes(2);
        });
        expect(updateTestAssetCase).toHaveBeenNthCalledWith(1, 7, 'TC-001', {
            title: '用户登录成功',
            priority: 'P1',
        });
        expect(updateTestAssetCase).toHaveBeenNthCalledWith(2, 7, 'TC-002', {
            title: '用户登录失败提示错误',
            priority: 'P1',
        });
        expect(await screen.findByText('已批量更新 2 条用例优先级')).toBeTruthy();
        expect(screen.getAllByText('版本 2').length).toBeGreaterThanOrEqual(2);
    });

    it('filters recent runs by the current workflow', async () => {
        vi.mocked(fetchRunList)
            .mockResolvedValueOnce({
                limit: 20,
                offset: 0,
                total: 1,
                hasMore: false,
                nextOffset: null,
                query: null,
                runs: [
                    {
                        id: 'alex-run-123',
                        workflowId: 'VALUE_DISCOVERY',
                        agentId: 'alex',
                        currentStageId: 'BLUEPRINT',
                        status: 'active',
                        qualityStatus: 'reusable',
                        model: 'test-model',
                        createdAt: '2026-06-19T09:00:00',
                        updatedAt: '2026-06-19T09:05:00',
                        lastMessage: null,
                        currentArtifact: {
                            stageId: 'BLUEPRINT',
                            versionNumber: 1,
                            summary: '价值发现历史',
                        },
                    },
                ],
            })
            .mockResolvedValueOnce({
                limit: 20,
                offset: 0,
                total: 1,
                hasMore: false,
                nextOffset: null,
                query: null,
                runs: [
                    {
                        id: 'test-run-123',
                        workflowId: 'TEST_DESIGN',
                        agentId: 'lisa',
                        currentStageId: 'STRATEGY',
                        status: 'active',
                        qualityStatus: 'reusable',
                        model: 'test-model',
                        createdAt: '2026-06-19T10:00:00',
                        updatedAt: '2026-06-19T10:05:00',
                        lastMessage: null,
                        currentArtifact: {
                            stageId: 'STRATEGY',
                            versionNumber: 1,
                            summary: '测试设计历史',
                        },
                    },
                ],
            });

        renderHeader();
        fireEvent.click(screen.getByRole('button', { name: /历史会话/ }));

        await screen.findByText('价值发现历史');
        fireEvent.click(screen.getByRole('button', { name: '当前工作流' }));

        await waitFor(() => {
            expect(fetchRunList).toHaveBeenLastCalledWith({
                workflowId: 'TEST_DESIGN',
                limit: 20,
            });
        });
        expect(await screen.findByText('测试设计历史')).toBeTruthy();
        expect(screen.queryByText('价值发现历史')).toBeNull();
    });

    it('searches recent runs and appends the next page', async () => {
        vi.mocked(fetchRunList)
            .mockResolvedValueOnce({
                limit: 20,
                offset: 0,
                total: 0,
                hasMore: false,
                nextOffset: null,
                query: null,
                runs: [],
            })
            .mockResolvedValueOnce({
                limit: 20,
                offset: 0,
                total: 21,
                hasMore: true,
                nextOffset: 20,
                query: '登录',
                runs: [
                    {
                        id: 'run-page-1',
                        workflowId: 'TEST_DESIGN',
                        agentId: 'lisa',
                        currentStageId: 'STRATEGY',
                        status: 'active',
                        qualityStatus: 'reusable',
                        model: 'test-model',
                        createdAt: '2026-06-19T10:00:00',
                        updatedAt: '2026-06-19T10:05:00',
                        lastMessage: null,
                        currentArtifact: {
                            stageId: 'STRATEGY',
                            versionNumber: 1,
                            summary: '登录第一页结果',
                        },
                    },
                ],
            })
            .mockResolvedValueOnce({
                limit: 20,
                offset: 20,
                total: 21,
                hasMore: false,
                nextOffset: null,
                query: '登录',
                runs: [
                    {
                        id: 'run-page-2',
                        workflowId: 'TEST_DESIGN',
                        agentId: 'lisa',
                        currentStageId: 'CASES',
                        status: 'active',
                        qualityStatus: 'reusable',
                        model: 'test-model',
                        createdAt: '2026-06-19T10:10:00',
                        updatedAt: '2026-06-19T10:15:00',
                        lastMessage: null,
                        currentArtifact: {
                            stageId: 'CASES',
                            versionNumber: 1,
                            summary: '登录第二页结果',
                        },
                    },
                ],
            });

        renderHeader();
        fireEvent.click(screen.getByRole('button', { name: /历史会话/ }));
        await screen.findByText('暂无历史会话');

        fireEvent.change(screen.getByLabelText('搜索历史会话'), {
            target: { value: '登录' },
        });
        fireEvent.click(screen.getByRole('button', { name: '搜索' }));

        await waitFor(() => {
            expect(fetchRunList).toHaveBeenLastCalledWith({
                limit: 20,
                query: '登录',
            });
        });
        expect(await screen.findByText('登录第一页结果')).toBeTruthy();

        fireEvent.click(screen.getByRole('button', { name: '加载更多' }));

        await waitFor(() => {
            expect(fetchRunList).toHaveBeenLastCalledWith({
                limit: 20,
                offset: 20,
                query: '登录',
            });
        });
        expect(await screen.findByText('登录第二页结果')).toBeTruthy();
        expect(screen.getByText('登录第一页结果')).toBeTruthy();
    });
});
