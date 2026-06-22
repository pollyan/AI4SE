import { useEffect, useMemo, useState } from 'react';
import type { FormEvent } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { clsx } from 'clsx';
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
} from '../services/testAssetService';
import { importIntentTesterDraft } from '../services/intentTesterImportService';
import {
    createIntentTesterExecution,
    fetchIntentTesterExecutionDetail,
    fetchLatestIntentTesterExecution,
} from '../services/intentTesterExecutionService';
import { deriveTestAssetQualityStatus } from '../core/testAssetQuality';
import type {
    IntentTesterDraft,
    IntentTesterExecutionDetail,
    IntentTesterExecutionRecord,
    TestAssetIntentTesterResultSnapshot,
    TestAssetCase,
    TestAssetCasePatch,
    TestAssetCollection,
    TestAssetIssue,
    TestAssetIssueStatus,
    TestAssetPoint,
    TestAssetPointPatch,
    TestAssetRisk,
    TestAssetRiskCreatePatch,
    TestAssetRiskPatch,
    TestAssetRiskStatus,
} from '../store';

const PRIORITIES = ['P0', 'P1', 'P2'];
const TEST_POINT_STATUSES = ['已覆盖', '部分覆盖', '未覆盖'];
const RISK_STATUSES: TestAssetRiskStatus[] = ['open', 'mitigating', 'accepted', 'closed'];
const SORT_FIELDS = ['id', 'priority', 'title', 'risk'] as const;
const SORT_DIRECTIONS = ['asc', 'desc'] as const;
const PAGE_SIZES = [5, 10, 20];
const DEFAULT_SORT_FIELD = 'id';
const DEFAULT_SORT_DIRECTION = 'asc';
const DEFAULT_PAGE_SIZE = 10;
const ISSUE_STATUS_LABELS: Record<TestAssetIssueStatus, string> = {
    pending: '待处理',
    confirmed: '已确认',
    ignored: '忽略',
};
const RISK_STATUS_LABELS: Record<TestAssetRiskStatus, string> = {
    open: '待处置',
    mitigating: '缓解中',
    accepted: '已接受',
    closed: '已关闭',
};

type SortField = typeof SORT_FIELDS[number];
type SortDirection = typeof SORT_DIRECTIONS[number];

type ListQueryState = {
    query: string;
    priority: string;
    sort: SortField;
    direction: SortDirection;
    page: number;
    pageSize: number;
};

const parseCollectionId = (value: string | undefined): number | null => {
    if (!value) return null;
    const id = Number(value);
    return Number.isInteger(id) && id > 0 ? id : null;
};

const isSortField = (value: string | null): value is SortField => (
    typeof value === 'string' && SORT_FIELDS.includes(value as SortField)
);

const isSortDirection = (value: string | null): value is SortDirection => (
    typeof value === 'string' && SORT_DIRECTIONS.includes(value as SortDirection)
);

const parsePositiveInteger = (value: string | null): number | null => {
    if (value === null) return null;
    const parsed = Number(value);
    return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
};

const buildImportedIntentTesterCaseIds = (
    collection: TestAssetCollection,
): Record<string, number> => (
    Object.fromEntries(collection.intentTesterMappings.map(mapping => [
        mapping.sourceCaseId,
        mapping.intentTesterCaseId,
    ]))
);

const buildIntentTesterExecutions = (
    collection: TestAssetCollection,
): Record<string, IntentTesterExecutionRecord> => (
    Object.fromEntries(collection.intentTesterMappings.flatMap(mapping => (
        mapping.latestExecution
            ? [[mapping.sourceCaseId, mapping.latestExecution] as const]
            : []
    )))
);

const buildIntentTesterResults = (
    collection: TestAssetCollection,
): Record<string, TestAssetIntentTesterResultSnapshot> => (
    Object.fromEntries(collection.intentTesterMappings.flatMap(mapping => (
        mapping.latestResult
            ? [[mapping.sourceCaseId, mapping.latestResult] as const]
            : []
    )))
);

const buildIntentTesterResultSnapshot = (
    detail: IntentTesterExecutionDetail,
): TestAssetIntentTesterResultSnapshot => {
    const failedSteps = detail.steps
        .filter(step => step.status === 'failed')
        .sort((left, right) => left.stepIndex - right.stepIndex);
    const screenshots = Array.from(new Set(
        detail.steps
            .map(step => step.screenshotPath)
            .filter((path): path is string => Boolean(path)),
    ));
    return {
        executionId: detail.executionId,
        status: detail.status,
        stepsTotal: detail.stepsTotal ?? detail.steps.length,
        stepsPassed: detail.stepsPassed ?? detail.steps.filter(step => step.status === 'success').length,
        stepsFailed: detail.stepsFailed ?? failedSteps.length,
        duration: detail.duration,
        errorMessage: detail.errorMessage,
        screenshots,
        failedSteps,
    };
};

const parseSearchParams = (params: URLSearchParams): ListQueryState => {
    const query = params.get('q') || '';
    const priority = params.get('priority') || 'all';
    const sortParam = params.get('sort');
    const directionParam = params.get('direction');
    const pageSizeParam = parsePositiveInteger(params.get('pageSize'));
    const pageParam = parsePositiveInteger(params.get('page'));

    return {
        query,
        priority: priority === 'all' || PRIORITIES.includes(priority) ? priority : 'all',
        sort: isSortField(sortParam) ? sortParam : DEFAULT_SORT_FIELD,
        direction: isSortDirection(directionParam) ? directionParam : DEFAULT_SORT_DIRECTION,
        page: pageParam || 1,
        pageSize: pageSizeParam !== null && PAGE_SIZES.includes(pageSizeParam)
            ? pageSizeParam
            : DEFAULT_PAGE_SIZE,
    };
};

const buildSearchParams = (state: ListQueryState): URLSearchParams => {
    const params = new URLSearchParams();
    if (state.query.trim()) params.set('q', state.query.trim());
    if (state.priority !== 'all') params.set('priority', state.priority);
    if (state.sort !== DEFAULT_SORT_FIELD) params.set('sort', state.sort);
    if (state.direction !== DEFAULT_SORT_DIRECTION) params.set('direction', state.direction);
    if (state.page > 1) params.set('page', String(state.page));
    if (state.pageSize !== DEFAULT_PAGE_SIZE) params.set('pageSize', String(state.pageSize));
    return params;
};

const priorityRank = (priority: string): number => {
    const index = PRIORITIES.indexOf(priority);
    return index >= 0 ? index : PRIORITIES.length;
};

const compareCases = (
    left: TestAssetCase,
    right: TestAssetCase,
    sortField: SortField,
): number => {
    if (sortField === 'priority') {
        const priorityCompare = priorityRank(left.priority) - priorityRank(right.priority);
        if (priorityCompare !== 0) return priorityCompare;
        return left.id.localeCompare(right.id);
    }

    return String(left[sortField]).localeCompare(String(right[sortField]), 'zh-Hans-CN');
};

const clampPage = (page: number, totalPages: number): number => (
    Math.min(Math.max(page, 1), Math.max(totalPages, 1))
);

export function TestAssetsPage() {
    const { collectionId } = useParams();
    const [searchParams, setSearchParams] = useSearchParams();
    const parsedCollectionId = useMemo(() => parseCollectionId(collectionId), [collectionId]);
    const listQuery = useMemo(() => parseSearchParams(searchParams), [searchParams]);
    const [collection, setCollection] = useState<TestAssetCollection | null>(null);
    const [selectedCaseIds, setSelectedCaseIds] = useState<string[]>([]);
    const [batchPriority, setBatchPriority] = useState('P1');
    const [editingCase, setEditingCase] = useState<TestAssetCase | null>(null);
    const [caseDraft, setCaseDraft] = useState<TestAssetCasePatch>({});
    const [editingPoint, setEditingPoint] = useState<TestAssetPoint | null>(null);
    const [pointDraft, setPointDraft] = useState<TestAssetPointPatch>({});
    const [editingRisk, setEditingRisk] = useState<TestAssetRisk | null>(null);
    const [riskDraft, setRiskDraft] = useState<TestAssetRiskPatch>({});
    const [riskCreateDraft, setRiskCreateDraft] = useState<TestAssetRiskCreatePatch>({
        risk: '',
        status: 'open',
        owner: '',
        note: '',
    });
    const [isLoading, setIsLoading] = useState(true);
    const [isUpdating, setIsUpdating] = useState(false);
    const [isSavingCase, setIsSavingCase] = useState(false);
    const [isSavingPoint, setIsSavingPoint] = useState(false);
    const [isSavingRisk, setIsSavingRisk] = useState(false);
    const [isCreatingRisk, setIsCreatingRisk] = useState(false);
    const [deletingRiskId, setDeletingRiskId] = useState<number | null>(null);
    const [updatingIssueId, setUpdatingIssueId] = useState<number | null>(null);
    const [importedIntentTesterCaseIds, setImportedIntentTesterCaseIds] = useState<Record<string, number>>({});
    const [intentTesterExecutions, setIntentTesterExecutions] = useState<Record<string, IntentTesterExecutionRecord>>({});
    const [intentTesterResults, setIntentTesterResults] = useState<Record<string, TestAssetIntentTesterResultSnapshot>>({});
    const [importingIntentTesterCaseId, setImportingIntentTesterCaseId] = useState<string | null>(null);
    const [creatingExecutionCaseId, setCreatingExecutionCaseId] = useState<string | null>(null);
    const [refreshingExecutionCaseId, setRefreshingExecutionCaseId] = useState<string | null>(null);
    const [recordingResultCaseId, setRecordingResultCaseId] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [successMessage, setSuccessMessage] = useState<string | null>(null);

    useEffect(() => {
        let isMounted = true;

        const loadCollection = async () => {
            setIsLoading(true);
            setError(null);
            setSuccessMessage(null);
            setCollection(null);
            setSelectedCaseIds([]);
            setEditingCase(null);
            setCaseDraft({});
            setEditingPoint(null);
            setPointDraft({});
            setEditingRisk(null);
            setRiskDraft({});
            setRiskCreateDraft({ risk: '', status: 'open', owner: '', note: '' });
            setImportedIntentTesterCaseIds({});
            setIntentTesterExecutions({});
            setIntentTesterResults({});
            setImportingIntentTesterCaseId(null);
            setCreatingExecutionCaseId(null);
            setRefreshingExecutionCaseId(null);
            setRecordingResultCaseId(null);

            if (parsedCollectionId === null) {
                setError('无法加载测试资产集合');
                setIsLoading(false);
                return;
            }

            try {
                const nextCollection = await fetchTestAssetCollection(parsedCollectionId);
                if (!isMounted) return;
                setCollection(nextCollection);
                setImportedIntentTesterCaseIds(buildImportedIntentTesterCaseIds(nextCollection));
                setIntentTesterExecutions(buildIntentTesterExecutions(nextCollection));
                setIntentTesterResults(buildIntentTesterResults(nextCollection));
            } catch {
                if (!isMounted) return;
                setError('无法加载测试资产集合');
            } finally {
                if (isMounted) {
                    setIsLoading(false);
                }
            }
        };

        void loadCollection();

        return () => {
            isMounted = false;
        };
    }, [parsedCollectionId]);

    const selectedCases = useMemo(() => {
        if (!collection) return [];
        const selected = new Set(selectedCaseIds);
        return collection.testCases.filter(testCase => selected.has(testCase.id));
    }, [collection, selectedCaseIds]);

    const sortedFilteredTestCases = useMemo(() => {
        if (!collection) return [];
        const query = listQuery.query.trim().toLowerCase();
        const filtered = collection.testCases.filter(testCase => {
            if (listQuery.priority !== 'all' && testCase.priority !== listQuery.priority) {
                return false;
            }
            if (!query) return true;
            return [
                testCase.id,
                testCase.title,
                testCase.testPoint,
                testCase.risk,
                testCase.expectedResult,
            ].some(value => value.toLowerCase().includes(query));
        });
        const directionMultiplier = listQuery.direction === 'asc' ? 1 : -1;
        return [...filtered].sort((left, right) => (
            compareCases(left, right, listQuery.sort) * directionMultiplier
        ));
    }, [collection, listQuery.direction, listQuery.priority, listQuery.query, listQuery.sort]);

    const totalPages = Math.max(
        1,
        Math.ceil(sortedFilteredTestCases.length / listQuery.pageSize),
    );
    const currentPage = clampPage(listQuery.page, totalPages);
    const pageStartIndex = (currentPage - 1) * listQuery.pageSize;
    const paginatedTestCases = sortedFilteredTestCases.slice(
        pageStartIndex,
        pageStartIndex + listQuery.pageSize,
    );
    const pageStart = sortedFilteredTestCases.length === 0 ? 0 : pageStartIndex + 1;
    const pageEnd = Math.min(pageStartIndex + listQuery.pageSize, sortedFilteredTestCases.length);

    const updateListQuery = (
        patch: Partial<ListQueryState>,
        options: { keepPage?: boolean } = {},
    ) => {
        const nextState = {
            ...listQuery,
            ...patch,
            page: options.keepPage ? (patch.page || listQuery.page) : 1,
        };
        const nextPage = clampPage(nextState.page, totalPages);
        setSelectedCaseIds([]);
        setSearchParams(buildSearchParams({ ...nextState, page: nextPage }), {
            replace: true,
        });
    };

    const toggleCaseSelection = (caseId: string) => {
        setSelectedCaseIds(current => (
            current.includes(caseId)
                ? current.filter(selectedCaseId => selectedCaseId !== caseId)
                : [...current, caseId]
        ));
    };

    const toggleAllCases = () => {
        if (!collection) return;
        setSelectedCaseIds(current => (
            current.length === paginatedTestCases.length
                ? []
                : paginatedTestCases.map(testCase => testCase.id)
        ));
    };

    const replaceUpdatedCases = (updatedCases: TestAssetCase[]) => {
        if (!collection) return;
        const updatedById = new Map(updatedCases.map(testCase => [testCase.id, testCase]));
        setCollection({
            ...collection,
            testCases: collection.testCases.map(testCase => (
                updatedById.get(testCase.id) || testCase
            )),
        });
    };

    const startEditCase = (testCase: TestAssetCase) => {
        setEditingCase(testCase);
        setCaseDraft({
            title: testCase.title,
            priority: testCase.priority,
            dimension: testCase.dimension,
            testPoint: testCase.testPoint,
            risk: testCase.risk,
            precondition: testCase.precondition,
            steps: testCase.steps,
            testData: testCase.testData,
            expectedResult: testCase.expectedResult,
        });
        setError(null);
        setSuccessMessage(null);
    };

    const updateCaseDraft = (field: keyof TestAssetCasePatch, value: string) => {
        setCaseDraft(current => ({
            ...current,
            [field]: value,
        }));
    };

    const startEditPoint = (testPoint: TestAssetPoint) => {
        setEditingPoint(testPoint);
        setPointDraft({
            priority: testPoint.priority,
            risk: testPoint.risk,
            status: testPoint.status,
            testCases: testPoint.testCases,
        });
        setError(null);
        setSuccessMessage(null);
    };

    const updatePointDraft = (field: keyof TestAssetPointPatch, value: string | string[]) => {
        setPointDraft(current => ({
            ...current,
            [field]: value,
        }));
    };

    const startEditRisk = (risk: TestAssetRisk) => {
        setEditingRisk(risk);
        setRiskDraft({
            risk: risk.risk,
            status: risk.status,
            owner: risk.owner,
            note: risk.note,
        });
        setError(null);
        setSuccessMessage(null);
    };

    const updateRiskDraft = (
        field: keyof TestAssetRiskPatch,
        value: string | TestAssetRiskStatus,
    ) => {
        setRiskDraft(current => ({
            ...current,
            [field]: value,
        }));
    };

    const updateRiskCreateDraft = (
        field: keyof TestAssetRiskCreatePatch,
        value: string | TestAssetRiskStatus,
    ) => {
        setRiskCreateDraft(current => ({
            ...current,
            [field]: value,
        }));
    };

    const parseCaseIds = (value: string): string[] => (
        value
            .split(',')
            .map(item => item.trim())
            .filter(Boolean)
    );

    const handleBatchUpdatePriority = async () => {
        if (!collection || selectedCases.length === 0) return;
        setIsUpdating(true);
        setError(null);
        setSuccessMessage(null);

        try {
            const updatedCases: TestAssetCase[] = [];
            for (const testCase of selectedCases) {
                const updatedCase = await updateTestAssetCase(collection.id, testCase.id, {
                    title: testCase.title,
                    priority: batchPriority,
                });
                updatedCases.push(updatedCase);
            }
            replaceUpdatedCases(updatedCases);
            setSuccessMessage(`已更新 ${updatedCases.length} 条测试用例`);
        } catch {
            setError('无法批量更新测试用例');
        } finally {
            setIsUpdating(false);
        }
    };

    const handleSaveCase = async (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        if (!collection || !editingCase) return;
        setIsSavingCase(true);
        setError(null);
        setSuccessMessage(null);

        try {
            const updatedCase = await updateTestAssetCase(collection.id, editingCase.id, caseDraft);
            replaceUpdatedCases([updatedCase]);
            setEditingCase(updatedCase);
            setCaseDraft({
                title: updatedCase.title,
                priority: updatedCase.priority,
                dimension: updatedCase.dimension,
                testPoint: updatedCase.testPoint,
                risk: updatedCase.risk,
                precondition: updatedCase.precondition,
                steps: updatedCase.steps,
                testData: updatedCase.testData,
                expectedResult: updatedCase.expectedResult,
            });
            setSuccessMessage(`已保存 ${updatedCase.id}`);
        } catch {
            setError('无法保存测试用例');
        } finally {
            setIsSavingCase(false);
        }
    };

    const handleSavePoint = async (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        if (!collection || !editingPoint) return;
        setIsSavingPoint(true);
        setError(null);
        setSuccessMessage(null);

        try {
            const updatedPoint = await updateTestAssetPoint(
                collection.id,
                editingPoint.testPoint,
                pointDraft,
            );
            const refreshedCollection = await fetchTestAssetCollection(collection.id);
            setCollection(refreshedCollection);
            const refreshedPoint = refreshedCollection.testPoints.find(
                testPoint => testPoint.testPoint === updatedPoint.testPoint
            );
            setEditingPoint(refreshedPoint || updatedPoint);
            setPointDraft({
                priority: updatedPoint.priority,
                risk: updatedPoint.risk,
                status: updatedPoint.status,
                testCases: updatedPoint.testCases,
            });
            setSuccessMessage(`已保存测试点 ${updatedPoint.testPoint}`);
        } catch {
            setError('无法保存测试点');
        } finally {
            setIsSavingPoint(false);
        }
    };

    const handleSaveRisk = async (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        if (!collection || !editingRisk) return;
        setIsSavingRisk(true);
        setError(null);
        setSuccessMessage(null);

        try {
            const updatedRisk = await updateTestAssetRiskById(
                collection.id,
                editingRisk.id,
                riskDraft,
            );
            const refreshedCollection = await fetchTestAssetCollection(collection.id);
            setCollection(refreshedCollection);
            const refreshedRisk = refreshedCollection.riskMatrix.find(
                risk => risk.id === updatedRisk.id
            ) || updatedRisk;
            setEditingRisk(refreshedRisk);
            setRiskDraft({
                risk: refreshedRisk.risk,
                status: refreshedRisk.status,
                owner: refreshedRisk.owner,
                note: refreshedRisk.note,
            });
            setSuccessMessage(`已保存风险 ${refreshedRisk.risk}`);
        } catch {
            setError('无法保存风险');
        } finally {
            setIsSavingRisk(false);
        }
    };

    const handleCreateRisk = async (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        if (!collection) return;
        setIsCreatingRisk(true);
        setError(null);
        setSuccessMessage(null);

        try {
            const createdRisk = await createTestAssetRisk(collection.id, riskCreateDraft);
            setCollection({
                ...collection,
                riskMatrix: [...collection.riskMatrix, createdRisk],
            });
            setRiskCreateDraft({ risk: '', status: 'open', owner: '', note: '' });
            setSuccessMessage(`已新增风险 ${createdRisk.risk}`);
        } catch {
            setError('无法新增风险');
        } finally {
            setIsCreatingRisk(false);
        }
    };

    const handleDeleteRisk = async (risk: TestAssetRisk) => {
        if (!collection) return;
        setDeletingRiskId(risk.id);
        setError(null);
        setSuccessMessage(null);

        try {
            await deleteTestAssetRisk(collection.id, risk.id);
            setCollection({
                ...collection,
                riskMatrix: collection.riskMatrix.filter(currentRisk => currentRisk.id !== risk.id),
            });
            if (editingRisk?.id === risk.id) {
                setEditingRisk(null);
                setRiskDraft({});
            }
            setSuccessMessage(`已删除风险 ${risk.risk}`);
        } catch {
            setError('无法删除风险');
        } finally {
            setDeletingRiskId(null);
        }
    };

    const handleUpdateIssueStatus = async (
        issue: TestAssetIssue,
        status: TestAssetIssueStatus,
    ) => {
        if (!collection) return;
        setUpdatingIssueId(issue.id);
        setError(null);
        setSuccessMessage(null);

        try {
            const updatedIssue = await updateTestAssetIssueStatus(collection.id, issue.id, status);
            setCollection({
                ...collection,
                assetIssues: collection.assetIssues.map(currentIssue => (
                    currentIssue.id === updatedIssue.id ? updatedIssue : currentIssue
                )),
            });
            setSuccessMessage(`已更新资产问题 ${updatedIssue.id}`);
        } catch {
            setError('无法更新资产问题状态');
        } finally {
            setUpdatingIssueId(null);
        }
    };

    const handleImportIntentTesterDraft = async (
        testCase: TestAssetCase,
        draft: IntentTesterDraft,
    ) => {
        setImportingIntentTesterCaseId(testCase.id);
        setError(null);
        setSuccessMessage(null);

        try {
            const created = await importIntentTesterDraft(draft);
            const mapping = await recordTestAssetIntentTesterCase(collection.id, testCase.id, {
                intentTesterCaseId: created.id,
                intentTesterCaseName: created.name,
            });
            setImportedIntentTesterCaseIds(current => ({
                ...current,
                [testCase.id]: mapping.intentTesterCaseId,
            }));
            if (mapping.latestExecution) {
                setIntentTesterExecutions(current => ({
                    ...current,
                    [testCase.id]: mapping.latestExecution,
                }));
            }
            setSuccessMessage(`已导入 intent-tester #${mapping.intentTesterCaseId}`);
        } catch {
            setError(`无法导入 intent-tester 草稿 ${testCase.id}`);
        } finally {
            setImportingIntentTesterCaseId(null);
        }
    };

    const handleCreateIntentTesterExecution = async (
        testCase: TestAssetCase,
        intentTesterCaseId: number,
    ) => {
        setCreatingExecutionCaseId(testCase.id);
        setError(null);
        setSuccessMessage(null);

        try {
            const createdExecution = await createIntentTesterExecution(intentTesterCaseId);
            const executionRecord: IntentTesterExecutionRecord = {
                executionId: createdExecution.executionId,
                testCaseId: intentTesterCaseId,
                status: createdExecution.status,
                mode: 'headless',
                browser: 'chrome',
                startTime: createdExecution.startTime,
                endTime: null,
                duration: null,
                errorMessage: null,
            };
            const mapping = await recordTestAssetIntentTesterExecution(
                collection.id,
                testCase.id,
                executionRecord,
            );
            setIntentTesterExecutions(current => ({
                ...current,
                ...(mapping.latestExecution ? { [testCase.id]: mapping.latestExecution } : {}),
            }));
            setSuccessMessage(`已创建执行记录 ${createdExecution.executionId}`);
        } catch {
            setError(`无法创建 intent-tester 执行记录 ${intentTesterCaseId}`);
        } finally {
            setCreatingExecutionCaseId(null);
        }
    };

    const handleRefreshIntentTesterExecution = async (
        testCase: TestAssetCase,
        intentTesterCaseId: number,
    ) => {
        setRefreshingExecutionCaseId(testCase.id);
        setError(null);
        setSuccessMessage(null);

        try {
            const latestExecution = await fetchLatestIntentTesterExecution(intentTesterCaseId);
            if (latestExecution) {
                const mapping = await recordTestAssetIntentTesterExecution(
                    collection.id,
                    testCase.id,
                    latestExecution,
                );
                setIntentTesterExecutions(current => ({
                    ...current,
                    ...(mapping.latestExecution ? { [testCase.id]: mapping.latestExecution } : {}),
                }));
                setSuccessMessage(`已刷新执行结果 ${mapping.latestExecution?.executionId || latestExecution.executionId}`);
            } else {
                setIntentTesterExecutions(current => {
                    const nextExecutions = { ...current };
                    delete nextExecutions[testCase.id];
                    return nextExecutions;
                });
                setSuccessMessage(`暂无 intent-tester 执行记录 #${intentTesterCaseId}`);
            }
        } catch {
            setError(`无法刷新 intent-tester 执行结果 ${intentTesterCaseId}`);
        } finally {
            setRefreshingExecutionCaseId(null);
        }
    };

    const handleRecordIntentTesterResult = async (
        testCase: TestAssetCase,
        executionId: string,
    ) => {
        if (!collection) return;
        setRecordingResultCaseId(testCase.id);
        setError(null);
        setSuccessMessage(null);

        try {
            const detail = await fetchIntentTesterExecutionDetail(executionId);
            const snapshot = buildIntentTesterResultSnapshot(detail);
            const mapping = await recordTestAssetIntentTesterResult(
                collection.id,
                testCase.id,
                snapshot,
            );
            if (mapping.latestResult) {
                setIntentTesterResults(current => ({
                    ...current,
                    [testCase.id]: mapping.latestResult,
                }));
            }
            if (mapping.latestExecution) {
                setIntentTesterExecutions(current => ({
                    ...current,
                    [testCase.id]: mapping.latestExecution,
                }));
            }
            setSuccessMessage(`已承接执行结果 ${snapshot.executionId}`);
        } catch {
            setError(`无法承接 intent-tester 执行结果 ${executionId}`);
        } finally {
            setRecordingResultCaseId(null);
        }
    };

    if (isLoading) {
        return (
            <main className="min-h-screen bg-[#0b1020] px-6 py-8 text-slate-200">
                <div className="mx-auto max-w-6xl py-20 text-center text-sm text-slate-400">
                    正在加载测试资产集合...
                </div>
            </main>
        );
    }

    if (error && !collection) {
        return (
            <main className="min-h-screen bg-[#0b1020] px-6 py-8 text-slate-200">
                <div className="mx-auto max-w-4xl rounded-lg border border-red-500/30 bg-red-500/10 px-5 py-4 text-sm text-red-100">
                    {error}
                </div>
            </main>
        );
    }

    if (!collection) {
        return null;
    }

    const assetQuality = deriveTestAssetQualityStatus(collection);
    const allCasesSelected = selectedCaseIds.length === paginatedTestCases.length && paginatedTestCases.length > 0;

    return (
        <main className="min-h-screen bg-[#0b1020] px-6 py-8 text-slate-200">
            <div className="mx-auto max-w-7xl space-y-6">
                <header className="flex flex-wrap items-end justify-between gap-4">
                    <div>
                        <p className="text-xs font-semibold uppercase tracking-wide text-blue-300">
                            Lisa TEST_DESIGN / {collection.sourceStageId}
                        </p>
                        <h1 className="mt-2 text-2xl font-bold text-white">Lisa 测试资产中心</h1>
                        <p className="mt-2 text-sm text-slate-400">
                            Run {collection.runId} · 集合 #{collection.id} · 来源版本 {collection.sourceArtifactVersion}
                        </p>
                    </div>
                </header>

                {error && (
                    <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-100">
                        {error}
                    </div>
                )}
                {successMessage && (
                    <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-100">
                        {successMessage}
                    </div>
                )}

                <section className={clsx(
                    "rounded-lg border px-5 py-4",
                    assetQuality.status === 'blocked'
                        ? "border-amber-500/30 bg-amber-500/10"
                        : assetQuality.status === 'attention'
                            ? "border-blue-500/30 bg-blue-500/10"
                            : "border-emerald-500/30 bg-emerald-500/10"
                )}>
                    <div className="flex flex-wrap items-start justify-between gap-4">
                        <div>
                            <div className="text-xs font-semibold uppercase text-slate-300">质量状态</div>
                            <div className="mt-1 text-2xl font-bold text-white">{assetQuality.label}</div>
                            <p className="mt-2 text-sm text-slate-300">{assetQuality.summary}</p>
                        </div>
                        <div className="max-w-xl text-sm text-slate-200">
                            {assetQuality.nextAction}
                        </div>
                    </div>
                    {(assetQuality.blockingItems.length > 0 || assetQuality.attentionItems.length > 0) && (
                        <div className="mt-4 flex flex-wrap gap-2 text-xs font-semibold">
                            {assetQuality.blockingItems.map(item => (
                                <span key={item} className="rounded bg-amber-500/15 px-2.5 py-1 text-amber-100">
                                    {item}
                                </span>
                            ))}
                            {assetQuality.attentionItems.map(item => (
                                <span key={item} className="rounded bg-blue-500/15 px-2.5 py-1 text-blue-100">
                                    {item}
                                </span>
                            ))}
                        </div>
                    )}
                </section>

                <section className="grid gap-3 md:grid-cols-4">
                    <div className="rounded-lg border border-[#1e293b] bg-[#111827] p-4">
                        <div className="text-xs text-slate-500">覆盖率</div>
                        <div className="mt-2 text-xl font-bold text-white">
                            覆盖率 {Math.round(collection.coverageSummary.coverageRate)}%
                        </div>
                    </div>
                    <div className="rounded-lg border border-[#1e293b] bg-[#111827] p-4">
                        <div className="text-xs text-slate-500">测试用例</div>
                        <div className="mt-2 text-xl font-bold text-white">
                            {collection.coverageSummary.totalTestCases}
                        </div>
                    </div>
                    <div className="rounded-lg border border-[#1e293b] bg-[#111827] p-4">
                        <div className="text-xs text-slate-500">测试点覆盖</div>
                        <div className="mt-2 text-xl font-bold text-white">
                            {collection.coverageSummary.coveredTestPoints}
                            <span className="text-sm font-medium text-slate-500">
                                /{collection.coverageSummary.totalTestPoints}
                            </span>
                        </div>
                    </div>
                    <div className="rounded-lg border border-[#1e293b] bg-[#111827] p-4">
                        <div className="text-xs text-slate-500">资产问题</div>
                        <div className="mt-2 text-xl font-bold text-white">
                            {collection.assetIssues.length}
                        </div>
                    </div>
                </section>

                <section className="rounded-lg border border-[#1e293b] bg-[#111827] p-4">
                    <div className="flex flex-wrap items-end justify-between gap-3">
                        <div>
                            <h2 className="text-base font-semibold text-white">测试用例</h2>
                            <p className="mt-1 text-xs text-slate-400">
                                已选择 {selectedCaseIds.length} / {collection.testCases.length} 条 · {' '}
                                <span>
                                    显示 {pageStart}-{pageEnd} / 过滤后 {sortedFilteredTestCases.length} 条 / 总计 {collection.testCases.length} 条
                                </span>
                            </p>
                        </div>
                        <div className="flex flex-wrap items-end gap-3">
                            <div>
                                <label htmlFor="asset-center-case-search" className="block text-xs font-semibold text-slate-300">
                                    搜索测试用例
                                </label>
                                <input
                                    id="asset-center-case-search"
                                    value={listQuery.query}
                                    onChange={(event) => updateListQuery({ query: event.target.value })}
                                    className="mt-2 w-48 rounded-lg border border-[#334155] bg-[#0f1623] px-3 py-2 text-sm text-white outline-none focus:border-blue-500"
                                />
                            </div>
                            <div>
                                <label htmlFor="asset-center-priority-filter" className="block text-xs font-semibold text-slate-300">
                                    优先级过滤
                                </label>
                                <select
                                    id="asset-center-priority-filter"
                                    value={listQuery.priority}
                                    onChange={(event) => updateListQuery({ priority: event.target.value })}
                                    className="mt-2 rounded-lg border border-[#334155] bg-[#0f1623] px-3 py-2 text-sm text-white outline-none focus:border-blue-500"
                                >
                                    <option value="all">全部</option>
                                    {PRIORITIES.map(priority => (
                                        <option key={priority} value={priority}>{priority}</option>
                                    ))}
                                </select>
                            </div>
                            <div>
                                <label htmlFor="asset-center-sort-field" className="block text-xs font-semibold text-slate-300">
                                    排序字段
                                </label>
                                <select
                                    id="asset-center-sort-field"
                                    value={listQuery.sort}
                                    onChange={(event) => updateListQuery({ sort: event.target.value as SortField })}
                                    className="mt-2 rounded-lg border border-[#334155] bg-[#0f1623] px-3 py-2 text-sm text-white outline-none focus:border-blue-500"
                                >
                                    <option value="id">用例 ID</option>
                                    <option value="priority">优先级</option>
                                    <option value="title">标题</option>
                                    <option value="risk">风险</option>
                                </select>
                            </div>
                            <div>
                                <label htmlFor="asset-center-sort-direction" className="block text-xs font-semibold text-slate-300">
                                    排序方向
                                </label>
                                <select
                                    id="asset-center-sort-direction"
                                    value={listQuery.direction}
                                    onChange={(event) => updateListQuery({ direction: event.target.value as SortDirection })}
                                    className="mt-2 rounded-lg border border-[#334155] bg-[#0f1623] px-3 py-2 text-sm text-white outline-none focus:border-blue-500"
                                >
                                    <option value="asc">升序</option>
                                    <option value="desc">降序</option>
                                </select>
                            </div>
                            <div>
                                <label htmlFor="asset-center-page-size" className="block text-xs font-semibold text-slate-300">
                                    每页数量
                                </label>
                                <select
                                    id="asset-center-page-size"
                                    value={String(listQuery.pageSize)}
                                    onChange={(event) => updateListQuery({ pageSize: Number(event.target.value) })}
                                    className="mt-2 rounded-lg border border-[#334155] bg-[#0f1623] px-3 py-2 text-sm text-white outline-none focus:border-blue-500"
                                >
                                    {PAGE_SIZES.map(pageSize => (
                                        <option key={pageSize} value={pageSize}>{pageSize}</option>
                                    ))}
                                </select>
                            </div>
                            <button
                                onClick={toggleAllCases}
                                className="rounded-lg border border-[#334155] px-3 py-2 text-sm font-semibold text-slate-200 hover:border-blue-500/50 hover:bg-blue-500/10"
                            >
                                {allCasesSelected ? '取消全选' : '选择全部'}
                            </button>
                            <div>
                                <label htmlFor="asset-center-batch-priority" className="block text-xs font-semibold text-slate-300">
                                    批量优先级
                                </label>
                                <select
                                    id="asset-center-batch-priority"
                                    value={batchPriority}
                                    onChange={(event) => setBatchPriority(event.target.value)}
                                    className="mt-2 rounded-lg border border-[#334155] bg-[#0f1623] px-3 py-2 text-sm text-white outline-none focus:border-blue-500"
                                >
                                    {PRIORITIES.map(priority => (
                                        <option key={priority} value={priority}>{priority}</option>
                                    ))}
                                </select>
                            </div>
                            <button
                                onClick={handleBatchUpdatePriority}
                                disabled={isUpdating || selectedCases.length === 0}
                                className="rounded-lg bg-blue-600 px-3 py-2 text-sm font-semibold text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
                            >
                                更新选中用例
                            </button>
                        </div>
                    </div>

                    <div className="mt-4 grid gap-3 lg:grid-cols-2">
                        {sortedFilteredTestCases.length === 0 && (
                            <div className="rounded-lg border border-[#1e293b] bg-[#0f1623] p-4 text-sm text-slate-400 lg:col-span-2">
                                当前筛选条件下暂无测试用例
                            </div>
                        )}
                        {paginatedTestCases.map(testCase => {
                            const isSelected = selectedCaseIds.includes(testCase.id);
                            const intentTesterDraft = collection.intentTesterDrafts.find(
                                draft => draft.sourceCaseId === testCase.id
                            );
                            const importedIntentTesterCaseId = importedIntentTesterCaseIds[testCase.id];
                            const intentTesterExecution = intentTesterExecutions[testCase.id];
                            const intentTesterResult = intentTesterResults[testCase.id];
                            return (
                                <article
                                    key={testCase.id}
                                    data-testid={`test-asset-case-${testCase.id}`}
                                    className={clsx(
                                        "rounded-lg border p-4",
                                        isSelected
                                            ? "border-blue-500/50 bg-blue-500/10"
                                            : "border-[#1e293b] bg-[#0f1623]"
                                    )}
                                >
                                    <div className="flex items-start gap-3">
                                        <input
                                            aria-label={`选择 ${testCase.id}`}
                                            type="checkbox"
                                            checked={isSelected}
                                            onChange={() => toggleCaseSelection(testCase.id)}
                                            className="mt-1 h-4 w-4 rounded border-slate-600 bg-[#111827]"
                                        />
                                        <div className="min-w-0 flex-1">
                                            <div className="flex flex-wrap items-center gap-2">
                                                <span className="rounded bg-blue-500/10 px-2 py-1 text-xs font-semibold text-blue-200">
                                                    {testCase.id}
                                                </span>
                                                <span className="rounded bg-emerald-500/10 px-2 py-1 text-xs font-semibold text-emerald-200">
                                                    {testCase.priority}
                                                </span>
                                                <span className="text-xs text-slate-500">版本 {testCase.versionNumber}</span>
                                            </div>
                                            <h3 className="mt-3 text-sm font-semibold text-white">{testCase.title}</h3>
                                            <div className="mt-2 space-y-1 text-xs leading-relaxed text-slate-400">
                                                <div>{testCase.dimension}</div>
                                                <div>{testCase.testPoint}</div>
                                                <div>{testCase.risk}</div>
                                                <div>{testCase.expectedResult}</div>
                                            </div>
                                            <button
                                                onClick={() => startEditCase(testCase)}
                                                className="mt-3 rounded-lg border border-[#334155] px-3 py-2 text-xs font-semibold text-slate-200 hover:border-blue-500/50 hover:bg-blue-500/10"
                                            >
                                                编辑 {testCase.id}
                                            </button>
                                            {intentTesterDraft && (
                                                <div
                                                    data-testid={`intent-tester-panel-${testCase.id}`}
                                                    className="mt-3 rounded-lg border border-cyan-500/20 bg-cyan-500/5 p-3 text-xs text-cyan-50"
                                                >
                                                    <div className="font-semibold text-cyan-100">
                                                        {intentTesterDraft.draftWarnings.length} 条 intent-tester 草稿
                                                    </div>
                                                    {intentTesterDraft.draftWarnings.length > 0 && (
                                                        <div className="mt-2 space-y-1 text-cyan-200/80">
                                                            {intentTesterDraft.draftWarnings.map(warning => (
                                                                <div key={warning}>{warning}</div>
                                                            ))}
                                                        </div>
                                                    )}
                                                    {!importedIntentTesterCaseId ? (
                                                        <button
                                                            onClick={() => void handleImportIntentTesterDraft(
                                                                testCase,
                                                                intentTesterDraft,
                                                            )}
                                                            disabled={importingIntentTesterCaseId === testCase.id}
                                                            className="mt-3 rounded-lg border border-cyan-400/30 px-3 py-2 text-xs font-semibold text-cyan-100 hover:border-cyan-300 hover:bg-cyan-500/10 disabled:cursor-not-allowed disabled:opacity-60"
                                                        >
                                                            导入 intent-tester {testCase.id}
                                                        </button>
                                                    ) : (
                                                        <div className="mt-3 space-y-3">
                                                            <div className="font-semibold text-cyan-100">
                                                                已导入 intent-tester #{importedIntentTesterCaseId}
                                                            </div>
                                                            {intentTesterExecution && (
                                                                <div>
                                                                    最近执行 {intentTesterExecution.executionId} · {intentTesterExecution.status}
                                                                </div>
                                                            )}
                                                            {intentTesterResult && (
                                                                <div className="space-y-2 rounded-lg border border-cyan-400/20 bg-[#0f1623] p-3">
                                                                    <div className="font-semibold text-cyan-100">
                                                                        执行结果 {intentTesterResult.status} · 通过 {intentTesterResult.stepsPassed} / {intentTesterResult.stepsTotal} · 失败 {intentTesterResult.stepsFailed}
                                                                    </div>
                                                                    <div className="text-cyan-200/80">
                                                                        截图 {intentTesterResult.screenshots.length}
                                                                    </div>
                                                                    {intentTesterResult.failedSteps.map(step => (
                                                                        <div
                                                                            key={`${step.stepIndex}-${step.description}`}
                                                                            className="border-l border-red-400/60 pl-2 text-red-100"
                                                                        >
                                                                            <div>
                                                                                失败步骤 {step.stepIndex} {step.description}
                                                                            </div>
                                                                            {step.errorMessage && (
                                                                                <div className="mt-1 text-red-200/80">
                                                                                    {step.errorMessage}
                                                                                </div>
                                                                            )}
                                                                        </div>
                                                                    ))}
                                                                </div>
                                                            )}
                                                            <div className="flex flex-wrap gap-2">
                                                                <button
                                                                    onClick={() => void handleCreateIntentTesterExecution(
                                                                        testCase,
                                                                        importedIntentTesterCaseId,
                                                                    )}
                                                                    disabled={creatingExecutionCaseId === testCase.id}
                                                                    className="rounded-lg border border-cyan-400/30 px-3 py-2 text-xs font-semibold text-cyan-100 hover:border-cyan-300 hover:bg-cyan-500/10 disabled:cursor-not-allowed disabled:opacity-60"
                                                                >
                                                                    创建执行记录 #{importedIntentTesterCaseId}
                                                                </button>
                                                                <button
                                                                    onClick={() => void handleRefreshIntentTesterExecution(
                                                                        testCase,
                                                                        importedIntentTesterCaseId,
                                                                    )}
                                                                    disabled={refreshingExecutionCaseId === testCase.id}
                                                                    className="rounded-lg border border-cyan-400/30 px-3 py-2 text-xs font-semibold text-cyan-100 hover:border-cyan-300 hover:bg-cyan-500/10 disabled:cursor-not-allowed disabled:opacity-60"
                                                                >
                                                                    刷新执行结果 #{importedIntentTesterCaseId}
                                                                </button>
                                                                {intentTesterExecution && (
                                                                    <button
                                                                        onClick={() => void handleRecordIntentTesterResult(
                                                                            testCase,
                                                                            intentTesterExecution.executionId,
                                                                        )}
                                                                        disabled={recordingResultCaseId === testCase.id}
                                                                        className="rounded-lg border border-cyan-400/30 px-3 py-2 text-xs font-semibold text-cyan-100 hover:border-cyan-300 hover:bg-cyan-500/10 disabled:cursor-not-allowed disabled:opacity-60"
                                                                    >
                                                                        承接执行结果 #{intentTesterExecution.executionId}
                                                                    </button>
                                                                )}
                                                                <a
                                                                    href={`/intent-tester/execution?testcase_id=${importedIntentTesterCaseId}`}
                                                                    className="rounded-lg border border-cyan-400/30 px-3 py-2 text-xs font-semibold text-cyan-100 hover:border-cyan-300 hover:bg-cyan-500/10"
                                                                >
                                                                    去执行 #{importedIntentTesterCaseId}
                                                                </a>
                                                            </div>
                                                        </div>
                                                    )}
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                </article>
                            );
                        })}
                    </div>

                    {sortedFilteredTestCases.length > 0 && (
                        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-[#1e293b] pt-4 text-xs text-slate-400">
                            <div>
                                第 {currentPage} / {totalPages} 页
                            </div>
                            <div className="flex gap-2">
                                <button
                                    type="button"
                                    disabled={currentPage <= 1}
                                    onClick={() => updateListQuery({ page: currentPage - 1 }, { keepPage: true })}
                                    className="rounded-lg border border-[#334155] px-3 py-2 font-semibold text-slate-200 hover:border-blue-500/50 hover:bg-blue-500/10 disabled:cursor-not-allowed disabled:opacity-60"
                                >
                                    上一页
                                </button>
                                <button
                                    type="button"
                                    disabled={currentPage >= totalPages}
                                    onClick={() => updateListQuery({ page: currentPage + 1 }, { keepPage: true })}
                                    className="rounded-lg border border-[#334155] px-3 py-2 font-semibold text-slate-200 hover:border-blue-500/50 hover:bg-blue-500/10 disabled:cursor-not-allowed disabled:opacity-60"
                                >
                                    下一页
                                </button>
                            </div>
                        </div>
                    )}

                    {editingCase && (
                        <form
                            onSubmit={handleSaveCase}
                            className="mt-4 grid gap-3 rounded-lg border border-[#1e293b] bg-[#0f1623] p-4 lg:grid-cols-2"
                        >
                            <div className="lg:col-span-2">
                                <h3 className="text-sm font-semibold text-white">编辑 {editingCase.id}</h3>
                            </div>
                            <div>
                                <label htmlFor="asset-case-title" className="block text-xs font-semibold text-slate-300">用例标题</label>
                                <input id="asset-case-title" value={caseDraft.title || ''} onChange={(event) => updateCaseDraft('title', event.target.value)} className="mt-2 w-full rounded-lg border border-[#334155] bg-[#111827] px-3 py-2 text-sm text-white outline-none focus:border-blue-500" />
                            </div>
                            <div>
                                <label htmlFor="asset-case-priority" className="block text-xs font-semibold text-slate-300">优先级</label>
                                <select id="asset-case-priority" value={caseDraft.priority || 'P1'} onChange={(event) => updateCaseDraft('priority', event.target.value)} className="mt-2 w-full rounded-lg border border-[#334155] bg-[#111827] px-3 py-2 text-sm text-white outline-none focus:border-blue-500">
                                    {PRIORITIES.map(priority => <option key={priority} value={priority}>{priority}</option>)}
                                </select>
                            </div>
                            <div>
                                <label htmlFor="asset-case-dimension" className="block text-xs font-semibold text-slate-300">测试维度</label>
                                <input id="asset-case-dimension" value={caseDraft.dimension || ''} onChange={(event) => updateCaseDraft('dimension', event.target.value)} className="mt-2 w-full rounded-lg border border-[#334155] bg-[#111827] px-3 py-2 text-sm text-white outline-none focus:border-blue-500" />
                            </div>
                            <div>
                                <label htmlFor="asset-case-test-point" className="block text-xs font-semibold text-slate-300">测试点</label>
                                <input id="asset-case-test-point" value={caseDraft.testPoint || ''} onChange={(event) => updateCaseDraft('testPoint', event.target.value)} className="mt-2 w-full rounded-lg border border-[#334155] bg-[#111827] px-3 py-2 text-sm text-white outline-none focus:border-blue-500" />
                            </div>
                            <div>
                                <label htmlFor="asset-case-risk" className="block text-xs font-semibold text-slate-300">关联风险</label>
                                <input id="asset-case-risk" value={caseDraft.risk || ''} onChange={(event) => updateCaseDraft('risk', event.target.value)} className="mt-2 w-full rounded-lg border border-[#334155] bg-[#111827] px-3 py-2 text-sm text-white outline-none focus:border-blue-500" />
                            </div>
                            <div>
                                <label htmlFor="asset-case-precondition" className="block text-xs font-semibold text-slate-300">前置条件</label>
                                <input id="asset-case-precondition" value={caseDraft.precondition || ''} onChange={(event) => updateCaseDraft('precondition', event.target.value)} className="mt-2 w-full rounded-lg border border-[#334155] bg-[#111827] px-3 py-2 text-sm text-white outline-none focus:border-blue-500" />
                            </div>
                            <div>
                                <label htmlFor="asset-case-steps" className="block text-xs font-semibold text-slate-300">操作步骤</label>
                                <textarea id="asset-case-steps" value={caseDraft.steps || ''} onChange={(event) => updateCaseDraft('steps', event.target.value)} className="mt-2 min-h-24 w-full rounded-lg border border-[#334155] bg-[#111827] px-3 py-2 text-sm text-white outline-none focus:border-blue-500" />
                            </div>
                            <div>
                                <label htmlFor="asset-case-test-data" className="block text-xs font-semibold text-slate-300">测试数据</label>
                                <textarea id="asset-case-test-data" value={caseDraft.testData || ''} onChange={(event) => updateCaseDraft('testData', event.target.value)} className="mt-2 min-h-24 w-full rounded-lg border border-[#334155] bg-[#111827] px-3 py-2 text-sm text-white outline-none focus:border-blue-500" />
                            </div>
                            <div className="lg:col-span-2">
                                <label htmlFor="asset-case-expected-result" className="block text-xs font-semibold text-slate-300">预期结果</label>
                                <textarea id="asset-case-expected-result" value={caseDraft.expectedResult || ''} onChange={(event) => updateCaseDraft('expectedResult', event.target.value)} className="mt-2 min-h-24 w-full rounded-lg border border-[#334155] bg-[#111827] px-3 py-2 text-sm text-white outline-none focus:border-blue-500" />
                            </div>
                            <div className="flex gap-2 lg:col-span-2">
                                <button
                                    type="submit"
                                    disabled={isSavingCase}
                                    className="rounded-lg bg-blue-600 px-3 py-2 text-sm font-semibold text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
                                >
                                    保存用例
                                </button>
                                <button
                                    type="button"
                                    onClick={() => setEditingCase(null)}
                                    className="rounded-lg border border-[#334155] px-3 py-2 text-sm font-semibold text-slate-200 hover:border-blue-500/50 hover:bg-blue-500/10"
                                >
                                    取消
                                </button>
                            </div>
                        </form>
                    )}
                </section>

                <div className="grid gap-4 lg:grid-cols-3">
                    <section className="rounded-lg border border-[#1e293b] bg-[#111827] p-4">
                        <h2 className="text-sm font-semibold text-white">资产问题</h2>
                        <div className="mt-3 space-y-3">
                            {collection.assetIssues.length === 0 && (
                                <div className="text-xs text-slate-500">暂无资产问题</div>
                            )}
                            {collection.assetIssues.map(issue => (
                                <div
                                    key={issue.id}
                                    data-testid={`asset-issue-${issue.id}`}
                                    className="border-l border-amber-400/60 pl-3 text-xs text-amber-100"
                                >
                                    <div>{issue.message}</div>
                                    <div className="mt-2 text-slate-400">
                                        {issue.caseId || '-'} · {issue.testPoint || '-'} · {' '}
                                        <span>{ISSUE_STATUS_LABELS[issue.status]}</span>
                                    </div>
                                    <div className="mt-3 flex flex-wrap gap-2">
                                        <button
                                            onClick={() => void handleUpdateIssueStatus(issue, 'confirmed')}
                                            disabled={updatingIssueId === issue.id}
                                            className="rounded border border-emerald-500/30 bg-emerald-500/10 px-2 py-1 text-[11px] font-semibold text-emerald-100 disabled:cursor-not-allowed disabled:opacity-60"
                                        >
                                            确认问题
                                        </button>
                                        <button
                                            onClick={() => void handleUpdateIssueStatus(issue, 'ignored')}
                                            disabled={updatingIssueId === issue.id}
                                            className="rounded border border-slate-500/30 bg-slate-500/10 px-2 py-1 text-[11px] font-semibold text-slate-200 disabled:cursor-not-allowed disabled:opacity-60"
                                        >
                                            忽略问题
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </section>

                    <section className="rounded-lg border border-[#1e293b] bg-[#111827] p-4">
                        <h2 className="text-sm font-semibold text-white">风险矩阵</h2>
                        <div className="mt-3 space-y-3">
                            {collection.riskMatrix.length === 0 && (
                                <div className="text-xs text-slate-500">暂无风险矩阵</div>
                            )}
                            {collection.riskMatrix.map(risk => (
                                <div
                                    key={risk.id}
                                    data-testid={`test-asset-risk-${risk.id}`}
                                    className="rounded-lg border border-rose-500/20 bg-rose-500/5 p-3 text-xs text-slate-300"
                                >
                                    <div className="flex flex-wrap items-center gap-2">
                                        <div className="font-semibold text-rose-100">{risk.risk}</div>
                                        <span className="rounded border border-slate-500/30 bg-slate-500/10 px-2 py-0.5 text-[11px] font-semibold text-slate-200">
                                            #{risk.id}
                                        </span>
                                        <span className="rounded border border-rose-400/30 bg-rose-500/10 px-2 py-0.5 text-[11px] font-semibold text-rose-100">
                                            {risk.isManual ? '手工风险' : '派生风险'}
                                        </span>
                                    </div>
                                    <div className="mt-2">
                                        <span className="rounded border border-rose-400/30 bg-rose-500/10 px-2 py-1 font-semibold text-rose-100">
                                            {RISK_STATUS_LABELS[risk.status]}
                                        </span>
                                    </div>
                                    <div className="mt-2">责任人 {risk.owner || '未分配'}</div>
                                    <div>备注 {risk.note || '暂无备注'}</div>
                                    <div>用例 {risk.testCases.join('、') || '-'}</div>
                                    <div>测试点 {risk.testPoints.join('、') || '-'}</div>
                                    <div>状态 {risk.coverageStatuses.join('、') || '-'}</div>
                                    <button
                                        onClick={() => startEditRisk(risk)}
                                        className="mt-3 rounded-lg border border-rose-400/30 px-3 py-2 text-xs font-semibold text-rose-100 hover:border-rose-300 hover:bg-rose-500/10"
                                    >
                                        编辑风险 {risk.risk}
                                    </button>
                                    {risk.testCases.length === 0 && risk.testPoints.length === 0 && (
                                        <button
                                            onClick={() => void handleDeleteRisk(risk)}
                                            disabled={deletingRiskId === risk.id}
                                            className="ml-2 mt-3 rounded-lg border border-red-400/30 px-3 py-2 text-xs font-semibold text-red-100 hover:border-red-300 hover:bg-red-500/10 disabled:cursor-not-allowed disabled:opacity-60"
                                        >
                                            删除风险 {risk.risk}
                                        </button>
                                    )}
                                </div>
                            ))}
                        </div>
                        <form
                            onSubmit={handleCreateRisk}
                            className="mt-4 space-y-3 rounded-lg border border-rose-500/20 bg-[#0f1623] p-3"
                        >
                            <h3 className="text-xs font-semibold text-rose-100">新增风险</h3>
                            <div className="grid gap-3 md:grid-cols-2">
                                <div>
                                    <label htmlFor="asset-risk-create-name" className="block text-xs font-semibold text-slate-300">
                                        新增风险名称
                                    </label>
                                    <input
                                        id="asset-risk-create-name"
                                        value={riskCreateDraft.risk}
                                        onChange={(event) => updateRiskCreateDraft('risk', event.target.value)}
                                        className="mt-2 w-full rounded-lg border border-[#334155] bg-[#111827] px-3 py-2 text-sm text-white outline-none focus:border-blue-500"
                                    />
                                </div>
                                <div>
                                    <label htmlFor="asset-risk-create-owner" className="block text-xs font-semibold text-slate-300">
                                        新增风险责任人
                                    </label>
                                    <input
                                        id="asset-risk-create-owner"
                                        value={riskCreateDraft.owner || ''}
                                        onChange={(event) => updateRiskCreateDraft('owner', event.target.value)}
                                        className="mt-2 w-full rounded-lg border border-[#334155] bg-[#111827] px-3 py-2 text-sm text-white outline-none focus:border-blue-500"
                                    />
                                </div>
                            </div>
                            <div>
                                <label htmlFor="asset-risk-create-note" className="block text-xs font-semibold text-slate-300">
                                    新增风险备注
                                </label>
                                <textarea
                                    id="asset-risk-create-note"
                                    value={riskCreateDraft.note || ''}
                                    onChange={(event) => updateRiskCreateDraft('note', event.target.value)}
                                    className="mt-2 min-h-20 w-full rounded-lg border border-[#334155] bg-[#111827] px-3 py-2 text-sm text-white outline-none focus:border-blue-500"
                                />
                            </div>
                            <button
                                type="submit"
                                disabled={isCreatingRisk}
                                className="rounded-lg bg-rose-600 px-3 py-2 text-xs font-semibold text-white hover:bg-rose-500 disabled:cursor-not-allowed disabled:opacity-60"
                            >
                                新增风险
                            </button>
                        </form>
                        {editingRisk && (
                            <form
                                onSubmit={handleSaveRisk}
                                className="mt-4 space-y-3 rounded-lg border border-rose-500/20 bg-[#0f1623] p-3"
                            >
                                <h3 className="text-xs font-semibold text-rose-100">
                                    编辑风险 {editingRisk.risk}
                                </h3>
                                <div>
                                    <label htmlFor="asset-risk-name" className="block text-xs font-semibold text-slate-300">
                                        风险名称
                                    </label>
                                    <input
                                        id="asset-risk-name"
                                        value={riskDraft.risk || ''}
                                        onChange={(event) => updateRiskDraft('risk', event.target.value)}
                                        className="mt-2 w-full rounded-lg border border-[#334155] bg-[#111827] px-3 py-2 text-sm text-white outline-none focus:border-blue-500"
                                    />
                                </div>
                                <div>
                                    <label htmlFor="asset-risk-status" className="block text-xs font-semibold text-slate-300">
                                        风险处置状态
                                    </label>
                                    <select
                                        id="asset-risk-status"
                                        value={riskDraft.status || 'open'}
                                        onChange={(event) => updateRiskDraft(
                                            'status',
                                            event.target.value as TestAssetRiskStatus,
                                        )}
                                        className="mt-2 w-full rounded-lg border border-[#334155] bg-[#111827] px-3 py-2 text-sm text-white outline-none focus:border-blue-500"
                                    >
                                        {RISK_STATUSES.map(status => (
                                            <option key={status} value={status}>
                                                {RISK_STATUS_LABELS[status]}
                                            </option>
                                        ))}
                                    </select>
                                </div>
                                <div>
                                    <label htmlFor="asset-risk-owner" className="block text-xs font-semibold text-slate-300">
                                        风险责任人
                                    </label>
                                    <input
                                        id="asset-risk-owner"
                                        value={riskDraft.owner || ''}
                                        onChange={(event) => updateRiskDraft('owner', event.target.value)}
                                        className="mt-2 w-full rounded-lg border border-[#334155] bg-[#111827] px-3 py-2 text-sm text-white outline-none focus:border-blue-500"
                                    />
                                </div>
                                <div>
                                    <label htmlFor="asset-risk-note" className="block text-xs font-semibold text-slate-300">
                                        风险处置备注
                                    </label>
                                    <textarea
                                        id="asset-risk-note"
                                        value={riskDraft.note || ''}
                                        onChange={(event) => updateRiskDraft('note', event.target.value)}
                                        className="mt-2 min-h-24 w-full rounded-lg border border-[#334155] bg-[#111827] px-3 py-2 text-sm text-white outline-none focus:border-blue-500"
                                    />
                                </div>
                                <div className="flex flex-wrap gap-2">
                                    <button
                                        type="submit"
                                        disabled={isSavingRisk}
                                        className="rounded-lg bg-rose-600 px-3 py-2 text-xs font-semibold text-white hover:bg-rose-500 disabled:cursor-not-allowed disabled:opacity-60"
                                    >
                                        保存风险
                                    </button>
                                    <button
                                        type="button"
                                        onClick={() => setEditingRisk(null)}
                                        className="rounded-lg border border-[#334155] px-3 py-2 text-xs font-semibold text-slate-200 hover:border-blue-500/50 hover:bg-blue-500/10"
                                    >
                                        取消
                                    </button>
                                </div>
                            </form>
                        )}
                    </section>

                    <section className="rounded-lg border border-[#1e293b] bg-[#111827] p-4">
                        <h2 className="text-sm font-semibold text-white">测试点覆盖</h2>
                        <div className="mt-3 space-y-3">
                            {collection.testPoints.length === 0 && (
                                <div className="text-xs text-slate-500">暂无测试点</div>
                            )}
                            {collection.testPoints.map(testPoint => (
                                <div
                                    key={testPoint.testPoint}
                                    data-testid={`test-asset-point-${testPoint.testPoint}`}
                                    className="rounded-lg border border-blue-500/20 bg-blue-500/5 p-3 text-xs text-slate-300"
                                >
                                    <div className="font-semibold text-blue-100">{testPoint.testPoint}</div>
                                    <div className="mt-2">{testPoint.priority} · {testPoint.status}</div>
                                    <div>{testPoint.risk || '-'}</div>
                                    <div>用例 {testPoint.testCases.join('、') || '无关联用例'}</div>
                                    <button
                                        onClick={() => startEditPoint(testPoint)}
                                        className="mt-3 rounded-lg border border-blue-400/30 px-3 py-2 text-xs font-semibold text-blue-100 hover:border-blue-300 hover:bg-blue-500/10"
                                    >
                                        编辑测试点 {testPoint.testPoint}
                                    </button>
                                </div>
                            ))}
                        </div>
                        {editingPoint && (
                            <form
                                onSubmit={handleSavePoint}
                                className="mt-4 space-y-3 rounded-lg border border-blue-500/20 bg-[#0f1623] p-3"
                            >
                                <h3 className="text-xs font-semibold text-blue-100">
                                    编辑测试点 {editingPoint.testPoint}
                                </h3>
                                <div>
                                    <label htmlFor="asset-point-priority" className="block text-xs font-semibold text-slate-300">
                                        测试点优先级
                                    </label>
                                    <select
                                        id="asset-point-priority"
                                        value={pointDraft.priority || 'P1'}
                                        onChange={(event) => updatePointDraft('priority', event.target.value)}
                                        className="mt-2 w-full rounded-lg border border-[#334155] bg-[#111827] px-3 py-2 text-sm text-white outline-none focus:border-blue-500"
                                    >
                                        {PRIORITIES.map(priority => (
                                            <option key={priority} value={priority}>{priority}</option>
                                        ))}
                                    </select>
                                </div>
                                <div>
                                    <label htmlFor="asset-point-status" className="block text-xs font-semibold text-slate-300">
                                        测试点覆盖状态
                                    </label>
                                    <select
                                        id="asset-point-status"
                                        value={pointDraft.status || '部分覆盖'}
                                        onChange={(event) => updatePointDraft('status', event.target.value)}
                                        className="mt-2 w-full rounded-lg border border-[#334155] bg-[#111827] px-3 py-2 text-sm text-white outline-none focus:border-blue-500"
                                    >
                                        {TEST_POINT_STATUSES.map(status => (
                                            <option key={status} value={status}>{status}</option>
                                        ))}
                                    </select>
                                </div>
                                <div>
                                    <label htmlFor="asset-point-risk" className="block text-xs font-semibold text-slate-300">
                                        测试点关联风险
                                    </label>
                                    <input
                                        id="asset-point-risk"
                                        value={pointDraft.risk || ''}
                                        onChange={(event) => updatePointDraft('risk', event.target.value)}
                                        className="mt-2 w-full rounded-lg border border-[#334155] bg-[#111827] px-3 py-2 text-sm text-white outline-none focus:border-blue-500"
                                    />
                                </div>
                                <div>
                                    <label htmlFor="asset-point-test-cases" className="block text-xs font-semibold text-slate-300">
                                        测试点覆盖用例
                                    </label>
                                    <input
                                        id="asset-point-test-cases"
                                        value={(pointDraft.testCases || []).join(', ')}
                                        onChange={(event) => updatePointDraft('testCases', parseCaseIds(event.target.value))}
                                        className="mt-2 w-full rounded-lg border border-[#334155] bg-[#111827] px-3 py-2 text-sm text-white outline-none focus:border-blue-500"
                                    />
                                </div>
                                <div className="flex flex-wrap gap-2">
                                    <button
                                        type="submit"
                                        disabled={isSavingPoint}
                                        className="rounded-lg bg-blue-600 px-3 py-2 text-xs font-semibold text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
                                    >
                                        保存测试点
                                    </button>
                                    <button
                                        type="button"
                                        onClick={() => setEditingPoint(null)}
                                        className="rounded-lg border border-[#334155] px-3 py-2 text-xs font-semibold text-slate-200 hover:border-blue-500/50 hover:bg-blue-500/10"
                                    >
                                        取消
                                    </button>
                                </div>
                            </form>
                        )}
                    </section>
                </div>
            </div>
        </main>
    );
}
