import React, { useCallback, useEffect, useState } from 'react';
import { useStore, WORKFLOWS } from '../store';
import { Settings, Bot, Plus, AlertTriangle, ArrowLeft, History, Search, ClipboardList, Save, Activity, Upload, FileText, MoreHorizontal } from 'lucide-react';
import { useNavigate, useParams } from 'react-router-dom';
import { clsx } from 'clsx';
import { WorkflowDropdown } from './WorkflowDropdown';
import { cloneRun, createRunDecisionSummary, fetchRunList, fetchRunSnapshot, updateRunContextSummary } from '../services/runSnapshotService';
import { materializeRunTestAssets, updateTestAssetCase, updateTestAssetIssueStatus } from '../services/testAssetService';
import { fetchObservabilitySummary } from '../services/observabilityService';
import { importIntentTesterDraft } from '../services/intentTesterImportService';
import { checkDefaultLlmConfig } from '../services/configService';
import { buildObservabilityAlerts } from '../core/observabilityAlerts';
import { withTestAssetQualitySummary } from '../core/testAssetQuality';
import type { AgentRunListItem, AgentRunSnapshot, AgentRunSnapshotContextSummary, ObservabilitySummary, RunReuseStatus, TestAssetCase, TestAssetCollection, TestAssetIssueStatus, WorkflowType } from '../store';

const RUN_LIST_PAGE_SIZE = 20;
const TEST_ASSET_ISSUE_STATUS_LABELS: Record<TestAssetIssueStatus, string> = {
  pending: '待处理',
  confirmed: '已确认',
  ignored: '忽略',
};
const TEST_ASSET_QUALITY_STATUS_TONE: Record<TestAssetCollection['qualitySummary']['status'], string> = {
  blocked: 'border-red-500/30 bg-red-500/10 text-red-100',
  attention: 'border-amber-500/30 bg-amber-500/10 text-amber-100',
  ready: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-100',
};
const TEST_ASSET_QUALITY_GATE_TONE: Record<TestAssetCollection['qualitySummary']['gates'][number]['status'], string> = {
  fail: 'bg-red-500/10 text-red-100',
  warn: 'bg-amber-500/10 text-amber-100',
  pass: 'bg-emerald-500/10 text-emerald-100',
};
const CONTEXT_SUMMARY_TYPE_LABELS: Record<string, string> = {
  user_supplement: '用户补充',
  stage_conclusion: '阶段结论',
  decision: '关键决策',
  current_artifact: '产物摘要',
};
const RUN_REUSE_STATUS_LABELS: Record<RunReuseStatus, string> = {
  ready: '可复用',
  needs_artifact: '无产物',
  failed: '失败',
};
const RUN_REUSE_STATUS_TONE: Record<RunReuseStatus, string> = {
  ready: 'bg-emerald-500/10 text-emerald-200',
  needs_artifact: 'bg-amber-500/10 text-amber-200',
  failed: 'bg-red-500/10 text-red-200',
};
const OBSERVABILITY_DIAGNOSTIC_STYLES = {
  info: {
    border: 'border-blue-500/30',
    background: 'bg-blue-500/10',
    label: 'text-blue-100',
  },
  warning: {
    border: 'border-amber-500/30',
    background: 'bg-amber-500/10',
    label: 'text-amber-100',
  },
  critical: {
    border: 'border-red-500/30',
    background: 'bg-red-500/10',
    label: 'text-red-100',
  },
} as const;
type ProviderConfigCheckState = {
  status: 'idle' | 'checking' | 'success' | 'error';
  message: string | null;
};

const getContextSummaryKey = (
  summary: Pick<AgentRunSnapshotContextSummary, 'sourceType' | 'sourceStageId' | 'summaryType'>,
): string => [
  summary.sourceType,
  summary.sourceStageId || '',
  summary.summaryType,
].join('|');

const getContextSummaryLabel = (summaryType: string): string => (
  CONTEXT_SUMMARY_TYPE_LABELS[summaryType] || summaryType
);

export const Header: React.FC = () => {
  const {
    workflow,
    stageIndex,
    contextSummaries,
    currentRunId,
    setStageIndex,
    setSettingsOpen,
    clearHistory,
    restoreRunSnapshot,
    updateContextSummaryContent,
    upsertContextSummary,
  } = useStore();
  const stages = WORKFLOWS[workflow].stages;
  const [showConfirm, setShowConfirm] = useState(false);
  const [showRuns, setShowRuns] = useState(false);
  const [recentRuns, setRecentRuns] = useState<AgentRunListItem[]>([]);
  const [isLoadingRuns, setIsLoadingRuns] = useState(false);
  const [runsError, setRunsError] = useState<string | null>(null);
  const [runListScope, setRunListScope] = useState<'all' | 'workflow'>('all');
  const [runReuseStatusFilter, setRunReuseStatusFilter] = useState<RunReuseStatus | 'all'>('all');
  const [runSearchDraft, setRunSearchDraft] = useState('');
  const [activeRunQuery, setActiveRunQuery] = useState('');
  const [hasMoreRuns, setHasMoreRuns] = useState(false);
  const [nextRunOffset, setNextRunOffset] = useState<number | null>(null);
  const [runTotal, setRunTotal] = useState(0);
  const [selectedRun, setSelectedRun] = useState<AgentRunListItem | null>(null);
  const [selectedRunSnapshot, setSelectedRunSnapshot] = useState<AgentRunSnapshot | null>(null);
  const [isLoadingRunPreview, setIsLoadingRunPreview] = useState(false);
  const [runPreviewError, setRunPreviewError] = useState<string | null>(null);
  const [cloneRunError, setCloneRunError] = useState<string | null>(null);
  const [cloningRunId, setCloningRunId] = useState<string | null>(null);
  const [showContextSummaries, setShowContextSummaries] = useState(false);
  const [contextSummaryDrafts, setContextSummaryDrafts] = useState<Record<string, string>>({});
  const [contextSummariesError, setContextSummariesError] = useState<string | null>(null);
  const [decisionDraft, setDecisionDraft] = useState('');
  const [showTestAssets, setShowTestAssets] = useState(false);
  const [testAssetCollection, setTestAssetCollection] = useState<TestAssetCollection | null>(null);
  const [isLoadingTestAssets, setIsLoadingTestAssets] = useState(false);
  const [isSavingTestCase, setIsSavingTestCase] = useState(false);
  const [testAssetsError, setTestAssetsError] = useState<string | null>(null);
  const [editingCase, setEditingCase] = useState<TestAssetCase | null>(null);
  const [caseDraft, setCaseDraft] = useState({ title: '', priority: '' });
  const [importingCaseId, setImportingCaseId] = useState<string | null>(null);
  const [isBatchImportingDrafts, setIsBatchImportingDrafts] = useState(false);
  const [batchImportSummary, setBatchImportSummary] = useState<string | null>(null);
  const [batchPriorityDraft, setBatchPriorityDraft] = useState('P1');
  const [isBatchUpdatingPriority, setIsBatchUpdatingPriority] = useState(false);
  const [batchPrioritySummary, setBatchPrioritySummary] = useState<string | null>(null);
  const [importedIntentTesterCaseIds, setImportedIntentTesterCaseIds] = useState<Record<string, number>>({});
  const [issueStatuses, setIssueStatuses] = useState<Record<string, TestAssetIssueStatus>>({});
  const [showObservability, setShowObservability] = useState(false);
  const [observabilitySummary, setObservabilitySummary] = useState<ObservabilitySummary | null>(null);
  const [isLoadingObservability, setIsLoadingObservability] = useState(false);
  const [observabilityError, setObservabilityError] = useState<string | null>(null);
  const [observabilityWorkflowFilter, setObservabilityWorkflowFilter] = useState<WorkflowType | ''>('');
  const [observabilityStageFilter, setObservabilityStageFilter] = useState('');
  const [isObservabilityAutoRefreshEnabled, setIsObservabilityAutoRefreshEnabled] = useState(false);
  const [providerConfigCheck, setProviderConfigCheck] = useState<ProviderConfigCheckState>({
    status: 'idle',
    message: null,
  });
  const [showMoreActions, setShowMoreActions] = useState(false);
  const navigate = useNavigate();
  const { agentId } = useParams<{ agentId: string }>();

  const handleNewChat = () => {
    setShowConfirm(true);
  };

  const confirmNewChat = () => {
    clearHistory();
    setShowConfirm(false);
  };

  const loadRuns = async (
    scope: 'all' | 'workflow',
    options?: {
      offset?: number;
      query?: string;
      reuseStatus?: RunReuseStatus | 'all';
      append?: boolean;
    },
  ) => {
    setIsLoadingRuns(true);
    setRunsError(null);
    if (!options?.append) {
      setSelectedRun(null);
      setSelectedRunSnapshot(null);
      setRunPreviewError(null);
      setCloneRunError(null);
    }
    try {
      const reuseStatus = options?.reuseStatus ?? runReuseStatusFilter;
      const result = await fetchRunList({
        ...(scope === 'workflow' ? { workflowId: workflow } : {}),
        ...(reuseStatus !== 'all' ? { reuseStatus } : {}),
        limit: RUN_LIST_PAGE_SIZE,
        ...(options?.offset !== undefined ? { offset: options.offset } : {}),
        ...(options?.query ? { query: options.query } : {}),
      });
      setRecentRuns((currentRuns) => (
        options?.append ? [...currentRuns, ...result.runs] : result.runs
      ));
      setHasMoreRuns(result.hasMore);
      setNextRunOffset(result.nextOffset);
      setRunTotal(result.total);
    } catch {
      if (!options?.append) {
        setRecentRuns([]);
      }
      setRunsError('无法加载历史会话');
      setHasMoreRuns(false);
      setNextRunOffset(null);
      setRunTotal(0);
    } finally {
      setIsLoadingRuns(false);
    }
  };

  const handleOpenRuns = async () => {
    setShowRuns(true);
    setRunListScope('all');
    setRunReuseStatusFilter('all');
    setRunSearchDraft('');
    setActiveRunQuery('');
    setSelectedRun(null);
    setSelectedRunSnapshot(null);
    setRunPreviewError(null);
    setCloneRunError(null);
    await loadRuns('all', { reuseStatus: 'all' });
  };

  const handleRunListScopeChange = async (scope: 'all' | 'workflow') => {
    setRunListScope(scope);
    await loadRuns(scope, { query: activeRunQuery });
  };

  const handleSearchRuns = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const normalizedQuery = runSearchDraft.trim();
    setActiveRunQuery(normalizedQuery);
    await loadRuns(runListScope, { query: normalizedQuery });
  };

  const handleRunReuseStatusFilterChange = async (reuseStatus: RunReuseStatus | 'all') => {
    setRunReuseStatusFilter(reuseStatus);
    await loadRuns(runListScope, {
      query: activeRunQuery,
      reuseStatus,
    });
  };

  const handleLoadMoreRuns = async () => {
    if (nextRunOffset === null) return;
    await loadRuns(runListScope, {
      offset: nextRunOffset,
      query: activeRunQuery,
      append: true,
    });
  };

  const handleContinueRun = (run: AgentRunListItem | null = selectedRun) => {
    if (!run) return;
    const targetWorkflow = WORKFLOWS[run.workflowId];
    navigate(`/workspace/${run.agentId}/${targetWorkflow.slug}?runId=${encodeURIComponent(run.id)}`);
    setShowRuns(false);
  };

  const handleSelectRun = async (run: AgentRunListItem) => {
    setSelectedRun(run);
    setSelectedRunSnapshot(null);
    setRunPreviewError(null);
    setCloneRunError(null);
    setIsLoadingRunPreview(true);
    try {
      setSelectedRunSnapshot(await fetchRunSnapshot(run.id));
    } catch {
      setRunPreviewError('无法加载历史会话预览');
    } finally {
      setIsLoadingRunPreview(false);
    }
  };

  const handleCloneSelectedRun = async () => {
    if (!selectedRun) return;

    setCloneRunError(null);
    setCloningRunId(selectedRun.id);
    try {
      const snapshot = await cloneRun(selectedRun.id);
      restoreRunSnapshot(snapshot);
      const targetWorkflow = WORKFLOWS[snapshot.run.workflowId];
      navigate(`/workspace/${snapshot.run.agentId}/${targetWorkflow.slug}?runId=${encodeURIComponent(snapshot.run.id)}`);
      setShowRuns(false);
    } catch {
      setCloneRunError('无法复制历史会话');
    } finally {
      setCloningRunId(null);
    }
  };

  const handleOpenContextSummaries = () => {
    setContextSummaryDrafts(Object.fromEntries(
      contextSummaries.map(summary => [
        getContextSummaryKey(summary),
        summary.content,
      ])
    ));
    setContextSummariesError(null);
    setDecisionDraft('');
    setShowContextSummaries(true);
  };

  const handleSaveContextSummary = async (summary: AgentRunSnapshotContextSummary) => {
    const key = getContextSummaryKey(summary);
    if (!currentRunId) {
      setContextSummariesError('当前会话尚未持久化，无法保存上下文摘要');
      return;
    }

    setContextSummariesError(null);
    try {
      const updatedSummary = await updateRunContextSummary(
        currentRunId,
        {
          sourceType: summary.sourceType,
          sourceStageId: summary.sourceStageId,
          summaryType: summary.summaryType,
        },
        contextSummaryDrafts[key] ?? summary.content,
      );
      const updatedKey = getContextSummaryKey(updatedSummary);
      updateContextSummaryContent(updatedSummary, updatedSummary.content);
      setContextSummaryDrafts(current => ({
        ...current,
        [updatedKey]: updatedSummary.content,
      }));
    } catch {
      setContextSummariesError('无法保存上下文摘要');
    }
  };

  const handleSaveDecisionSummary = async () => {
    const currentStageId = stages[stageIndex]?.id;
    if (!currentRunId) {
      setContextSummariesError('当前会话尚未持久化，无法保存关键决策');
      return;
    }
    if (!currentStageId) {
      setContextSummariesError('当前阶段无效，无法保存关键决策');
      return;
    }

    setContextSummariesError(null);
    try {
      const decisionSummary = await createRunDecisionSummary(
        currentRunId,
        currentStageId,
        decisionDraft,
      );
      upsertContextSummary(decisionSummary);
      setContextSummaryDrafts(current => ({
        ...current,
        [getContextSummaryKey(decisionSummary)]: decisionSummary.content,
      }));
      setDecisionDraft('');
    } catch {
      setContextSummariesError('无法保存关键决策');
    }
  };

  const getActiveObservabilityFilters = useCallback(() => ({
    ...(observabilityWorkflowFilter ? { workflowId: observabilityWorkflowFilter } : {}),
    ...(observabilityWorkflowFilter && observabilityStageFilter ? { stageId: observabilityStageFilter } : {}),
  }), [observabilityWorkflowFilter, observabilityStageFilter]);

  const loadObservabilitySummary = useCallback(async (filters?: {
    workflowId?: WorkflowType;
    stageId?: string;
  }) => {
    setIsLoadingObservability(true);
    setObservabilityError(null);
    try {
      const summary = await fetchObservabilitySummary({
        limit: RUN_LIST_PAGE_SIZE,
        ...filters,
      });
      setObservabilitySummary(summary);
    } catch {
      setObservabilitySummary(null);
      setObservabilityError('无法加载运行统计');
    } finally {
      setIsLoadingObservability(false);
    }
  }, []);

  const handleOpenObservability = async () => {
    setShowObservability(true);
    setObservabilityWorkflowFilter('');
    setObservabilityStageFilter('');
    setIsObservabilityAutoRefreshEnabled(false);
    setProviderConfigCheck({ status: 'idle', message: null });
    await loadObservabilitySummary();
  };

  const handleApplyObservabilityFilters = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    await loadObservabilitySummary(getActiveObservabilityFilters());
  };

  const handleOpenSettingsFromObservabilityAlert = () => {
    setSettingsOpen(true);
  };

  const handleCheckProviderConfigFromObservabilityAlert = async () => {
    setProviderConfigCheck({ status: 'checking', message: null });
    const result = await checkDefaultLlmConfig();
    setProviderConfigCheck({
      status: result.ok ? 'success' : 'error',
      message: result.message,
    });
  };

  useEffect(() => {
    if (!showObservability || !isObservabilityAutoRefreshEnabled) return undefined;

    const intervalId = window.setInterval(() => {
      void loadObservabilitySummary(getActiveObservabilityFilters());
    }, 30000);

    return () => window.clearInterval(intervalId);
  }, [
    getActiveObservabilityFilters,
    isObservabilityAutoRefreshEnabled,
    loadObservabilitySummary,
    showObservability,
  ]);

  const handleOpenTestAssets = async () => {
    setShowTestAssets(true);
    setTestAssetsError(null);
    setEditingCase(null);
    setBatchImportSummary(null);
    setBatchPrioritySummary(null);
    setBatchPriorityDraft('P1');
    setImportedIntentTesterCaseIds({});
    setIssueStatuses({});
    if (!currentRunId) {
      setTestAssetCollection(null);
      setTestAssetsError('当前会话尚未持久化，暂时无法读取测试资产');
      return;
    }

    setIsLoadingTestAssets(true);
    try {
      const collection = await materializeRunTestAssets(currentRunId);
      setTestAssetCollection(collection);
    } catch {
      setTestAssetCollection(null);
      setTestAssetsError('无法加载测试资产');
    } finally {
      setIsLoadingTestAssets(false);
    }
  };

  const getIssueKey = (
    issue: TestAssetCollection['assetIssues'][number],
    index: number,
  ) => [
    issue.type,
    issue.caseId || '',
    issue.testPoint || '',
    issue.message,
    String(index),
  ].join('|');

  const setIssueStatus = async (
    issue: TestAssetCollection['assetIssues'][number],
    index: number,
    status: TestAssetIssueStatus,
  ) => {
    if (!testAssetCollection) return;

    setTestAssetsError(null);
    try {
      const updatedIssue = await updateTestAssetIssueStatus(
        testAssetCollection.id,
        issue.id,
        status,
      );
      setTestAssetCollection(withTestAssetQualitySummary({
        ...testAssetCollection,
        assetIssues: testAssetCollection.assetIssues.map(currentIssue => (
          currentIssue.id === updatedIssue.id ? updatedIssue : currentIssue
        )),
      }));
      setIssueStatuses(current => ({
        ...current,
        [getIssueKey(updatedIssue, index)]: updatedIssue.status,
      }));
    } catch {
      setTestAssetsError('无法更新资产问题状态');
    }
  };

  const startEditCase = (testCase: TestAssetCase) => {
    setEditingCase(testCase);
    setCaseDraft({
      title: testCase.title,
      priority: testCase.priority,
    });
    setTestAssetsError(null);
  };

  const handleImportIntentTesterDraft = async (testCase: TestAssetCase) => {
    const draft = testAssetCollection?.intentTesterDrafts.find(
      intentTesterDraft => intentTesterDraft.sourceCaseId === testCase.id
    );
    if (!draft) {
      setTestAssetsError('缺少 intent-tester 草稿');
      return;
    }

    setImportingCaseId(testCase.id);
    setTestAssetsError(null);
    try {
      const created = await importIntentTesterDraft(draft);
      setImportedIntentTesterCaseIds(current => ({
        ...current,
        [testCase.id]: created.id,
      }));
    } catch {
      setTestAssetsError('无法导入 intent-tester');
    } finally {
      setImportingCaseId(null);
    }
  };

  const handleBatchImportIntentTesterDrafts = async () => {
    if (!testAssetCollection) return;

    const draftsToImport = testAssetCollection.intentTesterDrafts.filter(
      draft => importedIntentTesterCaseIds[draft.sourceCaseId] === undefined
    );
    if (draftsToImport.length === 0) {
      setBatchImportSummary('没有待导入的 intent-tester 草稿');
      return;
    }

    setIsBatchImportingDrafts(true);
    setTestAssetsError(null);
    setBatchImportSummary(null);
    try {
      for (const draft of draftsToImport) {
        const created = await importIntentTesterDraft(draft);
        setImportedIntentTesterCaseIds(current => ({
          ...current,
          [draft.sourceCaseId]: created.id,
        }));
      }
      setBatchImportSummary(`已批量导入 ${draftsToImport.length} 条 intent-tester 用例`);
    } catch {
      setTestAssetsError('批量导入 intent-tester 失败');
    } finally {
      setIsBatchImportingDrafts(false);
    }
  };

  const handleBatchUpdatePriority = async () => {
    if (!testAssetCollection) return;

    setIsBatchUpdatingPriority(true);
    setTestAssetsError(null);
    setBatchPrioritySummary(null);
    try {
      const updatedCases: TestAssetCase[] = [];
      for (const testCase of testAssetCollection.testCases) {
        const updatedCase = await updateTestAssetCase(
          testAssetCollection.id,
          testCase.id,
          {
            title: testCase.title,
            priority: batchPriorityDraft,
          },
        );
        updatedCases.push(updatedCase);
      }
      setTestAssetCollection({
        ...testAssetCollection,
        testCases: testAssetCollection.testCases.map(testCase => (
          updatedCases.find(updatedCase => updatedCase.id === testCase.id) || testCase
        )),
      });
      setBatchPrioritySummary(`已批量更新 ${updatedCases.length} 条用例优先级`);
    } catch {
      setTestAssetsError('批量更新测试用例失败');
    } finally {
      setIsBatchUpdatingPriority(false);
    }
  };

  const handleSaveTestCase = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!testAssetCollection || !editingCase) return;

    setIsSavingTestCase(true);
    setTestAssetsError(null);
    try {
      const updatedCase = await updateTestAssetCase(
        testAssetCollection.id,
        editingCase.id,
        {
          title: caseDraft.title.trim(),
          priority: caseDraft.priority.trim(),
        },
      );
      setTestAssetCollection({
        ...testAssetCollection,
        testCases: testAssetCollection.testCases.map(testCase => (
          testCase.id === updatedCase.id ? updatedCase : testCase
        )),
      });
      setEditingCase(null);
    } catch {
      setTestAssetsError('无法保存测试用例');
    } finally {
      setIsSavingTestCase(false);
    }
  };

  const agentIdForUrl = agentId || WORKFLOWS[workflow].agentId;
  const observabilityWorkflowStages = observabilityWorkflowFilter
    ? WORKFLOWS[observabilityWorkflowFilter].stages
    : [];
  const observabilityAlerts = observabilitySummary
    ? buildObservabilityAlerts(observabilitySummary)
    : [];
  const observabilityContractRetryReasons = observabilitySummary
    ? Object.entries(observabilitySummary.contractRetryReasons)
    : [];
  const pendingIssueCount = testAssetCollection
    ? testAssetCollection.assetIssues.filter((issue, index) => (
      (issueStatuses[getIssueKey(issue, index)] || issue.status) === 'pending'
    )).length
    : 0;
  const selectedRunArtifact = selectedRunSnapshot?.artifacts.find(artifact => (
    artifact.stageId === selectedRun?.currentArtifact?.stageId
  )) || selectedRunSnapshot?.artifacts[0] || null;
  const selectedRunPreview = selectedRunArtifact?.content
    || selectedRun?.currentArtifact?.summary
    || selectedRun?.lastMessage?.content
    || '';

  return (
    <>
      <header className="flex items-center justify-between border-b border-[#1e293b] bg-[#0B1120]/80 backdrop-blur-md px-6 py-3 shrink-0 z-30">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate(`/workflows/${agentIdForUrl}`)}
            className="group flex items-center justify-center p-2 rounded-lg hover:bg-[#1e293b] text-slate-400 hover:text-white transition-all mr-2"
          >
            <ArrowLeft className="w-5 h-5 group-hover:-translate-x-1 transition-transform" />
          </button>

          <div className="w-9 h-9 flex items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500/20 to-indigo-600/10 text-indigo-400 border border-indigo-500/30 shadow-[0_0_10px_rgba(99,102,241,0.1)]">
            <Bot className="w-5 h-5" />
          </div>
          <WorkflowDropdown />
        </div>

        <div className="hidden md:flex flex-1 max-w-2xl mx-8">
          <div className="flex h-12 w-full items-center justify-center rounded-xl bg-[#0f1623] p-1.5 border border-[#1e293b]/50">
            {stages.map((stage, idx) => {
              const isActive = idx === stageIndex;
              return (
                <div
                  key={stage.id}
                  onClick={() => setStageIndex(idx)}
                  className={clsx(
                    "relative flex cursor-pointer h-full grow items-center justify-center rounded-lg px-4 text-sm font-medium transition-all group",
                    isActive ? "bg-blue-600 text-white shadow-md shadow-blue-500/10 font-semibold" : "text-slate-400 hover:text-white hover:bg-white/5"
                  )}
                >
                  <span className={clsx(
                    "mr-2 text-[10px] font-mono px-1.5 py-0.5 rounded transition-opacity",
                    isActive ? "bg-white/20 opacity-80" : "bg-white/5 opacity-40 group-hover:opacity-60"
                  )}>
                    0{idx + 1}
                  </span>
                  <span className="truncate">{stage.name}</span>
                </div>
              );
            })}
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleNewChat}
            className="flex items-center justify-center gap-2 rounded-lg h-9 px-4 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium transition-all shadow-md shadow-blue-500/20"
          >
            <Plus className="w-4 h-4" />
            <span className="truncate hidden lg:inline">新会话</span>
          </button>
          <button
            onClick={handleOpenRuns}
            className="flex items-center justify-center gap-2 rounded-lg h-9 px-4 bg-[#151e32] border border-[#1e293b] hover:border-blue-500/50 text-slate-400 hover:text-white text-sm font-medium transition-all"
          >
            <History className="w-4 h-4" />
            <span className="truncate hidden lg:inline">历史会话</span>
          </button>
          <div className="relative">
            <button
              type="button"
              aria-label="更多操作"
              aria-haspopup="menu"
              aria-expanded={showMoreActions}
              onClick={() => setShowMoreActions(current => !current)}
              className="flex items-center justify-center gap-2 rounded-lg h-9 px-3 bg-[#151e32] border border-[#1e293b] hover:border-blue-500/50 text-slate-400 hover:text-white text-sm font-medium transition-all"
            >
              <MoreHorizontal className="w-4 h-4" />
              <span className="truncate hidden lg:inline">更多</span>
            </button>
            {showMoreActions && (
              <div
                role="menu"
                className="absolute right-0 top-full z-40 mt-2 w-44 overflow-hidden rounded-lg border border-[#1e293b] bg-[#0f172a] py-1 shadow-xl"
              >
                <button
                  type="button"
                  onClick={() => {
                    setShowMoreActions(false);
                    handleOpenContextSummaries();
                  }}
                  className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm font-medium text-slate-200 hover:bg-white/5"
                >
                  <FileText className="h-4 w-4 text-slate-400" />
                  上下文摘要
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowMoreActions(false);
                    void handleOpenObservability();
                  }}
                  className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm font-medium text-slate-200 hover:bg-white/5"
                >
                  <Activity className="h-4 w-4 text-slate-400" />
                  运行统计
                </button>
                {workflow === 'TEST_DESIGN' && (
                  <button
                    type="button"
                    onClick={() => {
                      setShowMoreActions(false);
                      void handleOpenTestAssets();
                    }}
                    className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm font-medium text-slate-200 hover:bg-white/5"
                  >
                    <ClipboardList className="h-4 w-4 text-slate-400" />
                    测试资产
                  </button>
                )}
                <div className="my-1 h-px bg-[#1e293b]"></div>
                <button
                  type="button"
                  onClick={() => {
                    setShowMoreActions(false);
                    setSettingsOpen(true);
                  }}
                  className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm font-medium text-slate-200 hover:bg-white/5"
                >
                  <Settings className="h-4 w-4 text-slate-400" />
                  设置
                </button>
              </div>
            )}
          </div>
          <div className="bg-center bg-no-repeat bg-cover rounded-full w-9 h-9 ml-2 ring-2 ring-[#151e32]" style={{ backgroundImage: `url("https://picsum.photos/seed/${agentIdForUrl}/100/100")` }}></div>
        </div>
      </header>

      {showConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
          <div className="flex w-full max-w-sm flex-col overflow-hidden rounded-xl bg-[#151f2b] shadow-2xl ring-1 ring-white/10 p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-red-500/10 text-red-500">
                <AlertTriangle className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-bold text-white">开启新会话</h3>
            </div>
            <p className="text-sm text-slate-300 mb-6">
              确定要开启新会话吗？这将清空当前的对话历史和产出物文档，且无法恢复。
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowConfirm(false)}
                className="rounded-lg px-4 py-2 text-sm font-medium text-slate-300 hover:bg-white/5 transition-colors"
              >
                取消
              </button>
              <button
                onClick={confirmNewChat}
                className="rounded-lg bg-red-600 px-4 py-2 text-sm font-bold text-white hover:bg-red-500 transition-colors shadow-md shadow-red-500/20"
              >
                确定清空
              </button>
            </div>
          </div>
        </div>
      )}

      {showContextSummaries && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
          <div className="flex w-full max-w-3xl flex-col overflow-hidden rounded-xl bg-[#151f2b] shadow-2xl ring-1 ring-white/10">
            <div className="flex items-center justify-between border-b border-white/10 px-5 py-4">
              <div>
                <h3 className="text-base font-bold text-white">上下文摘要详情</h3>
                <p className="mt-1 text-xs text-slate-400">保存后会更新当前 run 的服务端摘要</p>
              </div>
              <button
                onClick={() => setShowContextSummaries(false)}
                className="rounded-lg px-3 py-1.5 text-sm text-slate-300 hover:bg-white/5"
              >
                关闭
              </button>
            </div>
            <div className="max-h-[620px] overflow-y-auto p-5">
              {contextSummariesError && (
                <div className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
                  {contextSummariesError}
                </div>
              )}
              <section className="mb-4 rounded-lg border border-[#1e293b] bg-[#0f1623] p-4">
                <h4 className="text-sm font-semibold text-white">关键决策录入</h4>
                <label className="mt-3 block text-xs font-semibold text-slate-300">
                  关键决策内容
                  <textarea
                    value={decisionDraft}
                    onChange={(event) => setDecisionDraft(event.target.value)}
                    className="mt-2 min-h-24 w-full resize-y rounded-lg border border-[#1e293b] bg-[#111827] px-3 py-2 text-sm leading-relaxed text-white outline-none focus:border-blue-500"
                  />
                </label>
                <div className="mt-3 flex justify-end">
                  <button
                    onClick={() => void handleSaveDecisionSummary()}
                    className="flex items-center justify-center gap-2 rounded-lg bg-emerald-600 px-3 py-2 text-sm font-semibold text-white hover:bg-emerald-500"
                  >
                    <Save className="h-4 w-4" />
                    保存关键决策
                  </button>
                </div>
              </section>
              {contextSummaries.length === 0 && (
                <div className="rounded-lg border border-[#1e293b] bg-[#0f1623] px-4 py-8 text-center text-sm text-slate-400">
                  暂无上下文摘要
                </div>
              )}
              {contextSummaries.length > 0 && (
                <div className="space-y-4">
                  {contextSummaries.map((summary) => {
                    const key = getContextSummaryKey(summary);
                    const summaryLabel = getContextSummaryLabel(summary.summaryType);
                    return (
                      <section key={key} className="rounded-lg border border-[#1e293b] bg-[#0f1623] p-4">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="rounded bg-blue-500/10 px-2 py-1 text-xs font-semibold text-blue-200">
                            {summaryLabel}
                          </span>
                          <span className="rounded bg-slate-700/70 px-2 py-1 text-xs font-semibold text-slate-100">
                            {summary.sourceStageId || '全局'}
                          </span>
                          <span className="text-xs text-slate-500">{summary.sourceType}</span>
                        </div>
                        <label className="mt-4 block text-xs font-semibold text-slate-300">
                          摘要内容
                          <textarea
                            value={contextSummaryDrafts[key] ?? summary.content}
                            onChange={(event) => setContextSummaryDrafts(current => ({
                              ...current,
                              [key]: event.target.value,
                            }))}
                            className="mt-2 min-h-28 w-full resize-y rounded-lg border border-[#1e293b] bg-[#111827] px-3 py-2 text-sm leading-relaxed text-white outline-none focus:border-blue-500"
                          />
                        </label>
                        <div className="mt-3 flex justify-end">
                          <button
                            onClick={() => void handleSaveContextSummary(summary)}
                            className="flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-3 py-2 text-sm font-semibold text-white hover:bg-blue-500"
                          >
                            <Save className="h-4 w-4" />
                            保存摘要
                          </button>
                        </div>
                      </section>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {showObservability && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
          <div className="flex w-full max-w-4xl flex-col overflow-hidden rounded-xl bg-[#151f2b] shadow-2xl ring-1 ring-white/10">
            <div className="flex items-center justify-between border-b border-white/10 px-5 py-4">
              <div>
                <h3 className="text-base font-bold text-white">运行统计详情</h3>
                <p className="mt-1 text-xs text-slate-400">最近 {RUN_LIST_PAGE_SIZE} 轮 Agent Runtime 运行</p>
              </div>
              <button
                onClick={() => {
                  setShowObservability(false);
                  setIsObservabilityAutoRefreshEnabled(false);
                }}
                className="rounded-lg px-3 py-1.5 text-sm text-slate-300 hover:bg-white/5"
              >
                关闭
              </button>
            </div>
            <div className="max-h-[620px] overflow-y-auto p-5">
              {isLoadingObservability && (
                <div className="py-12 text-center text-sm text-slate-400">正在加载运行统计...</div>
              )}
              {!isLoadingObservability && observabilityError && (
                <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
                  {observabilityError}
                </div>
              )}
              {!isLoadingObservability && !observabilityError && observabilitySummary && (
                <div className="space-y-5">
                  <form
                    onSubmit={handleApplyObservabilityFilters}
                    className="grid gap-3 rounded-lg border border-[#1e293b] bg-[#0f1623] p-4 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto_auto]"
                  >
                    <div>
                      <label htmlFor="observability-workflow-filter" className="block text-xs font-semibold text-slate-300">
                        统计工作流
                      </label>
                      <select
                        id="observability-workflow-filter"
                        value={observabilityWorkflowFilter}
                        onChange={(event) => {
                          setObservabilityWorkflowFilter(event.target.value as WorkflowType | '');
                          setObservabilityStageFilter('');
                        }}
                        className="mt-2 w-full rounded-lg border border-[#1e293b] bg-[#111827] px-3 py-2 text-sm text-white outline-none focus:border-blue-500"
                      >
                        <option value="">全部工作流</option>
                        {Object.entries(WORKFLOWS).map(([workflowId, workflowConfig]) => (
                          <option key={workflowId} value={workflowId}>
                            {workflowConfig.name}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label htmlFor="observability-stage-filter" className="block text-xs font-semibold text-slate-300">
                        统计阶段
                      </label>
                      <select
                        id="observability-stage-filter"
                        value={observabilityStageFilter}
                        disabled={!observabilityWorkflowFilter}
                        onChange={(event) => setObservabilityStageFilter(event.target.value)}
                        className="mt-2 w-full rounded-lg border border-[#1e293b] bg-[#111827] px-3 py-2 text-sm text-white outline-none focus:border-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        <option value="">全部阶段</option>
                        {observabilityWorkflowStages.map((stage) => (
                          <option key={stage.id} value={stage.id}>
                            {stage.name}
                          </option>
                        ))}
                      </select>
                    </div>
                    <button
                      type="submit"
                      disabled={isLoadingObservability}
                      className="self-end rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      应用筛选
                    </button>
                    <label className="flex self-end items-center gap-2 rounded-lg border border-[#1e293b] bg-[#111827] px-3 py-2 text-sm font-semibold text-slate-200">
                      <input
                        type="checkbox"
                        checked={isObservabilityAutoRefreshEnabled}
                        onChange={(event) => setIsObservabilityAutoRefreshEnabled(event.target.checked)}
                        className="h-4 w-4 accent-blue-500"
                      />
                      自动刷新
                    </label>
                  </form>

                  {observabilityAlerts.length > 0 && (
                    <section className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-4">
                      <h4 className="text-sm font-semibold text-amber-100">运行告警</h4>
                      <div className="mt-3 grid gap-3 lg:grid-cols-3">
                        {observabilityAlerts.map((alert) => (
                          <div key={alert.id} className="rounded-lg border border-amber-500/20 bg-[#111827] p-3">
                            <div className="text-sm font-semibold text-white">{alert.title}</div>
                            <div className="mt-2 text-xs leading-relaxed text-amber-100">
                              {alert.detail}
                            </div>
                            {alert.id === 'provider-issues' && (
                              <div className="mt-3 space-y-2">
                                <div className="flex flex-wrap gap-2">
                                  <button
                                    type="button"
                                    onClick={handleOpenSettingsFromObservabilityAlert}
                                    className="rounded-lg border border-amber-400/30 px-3 py-1.5 text-xs font-semibold text-amber-100 hover:bg-amber-400/10"
                                  >
                                    打开模型设置
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() => void handleCheckProviderConfigFromObservabilityAlert()}
                                    disabled={providerConfigCheck.status === 'checking'}
                                    className="rounded-lg bg-amber-500 px-3 py-1.5 text-xs font-semibold text-slate-950 hover:bg-amber-400 disabled:cursor-not-allowed disabled:opacity-60"
                                  >
                                    {providerConfigCheck.status === 'checking' ? '正在检测...' : '检测连接'}
                                  </button>
                                </div>
                                {providerConfigCheck.message && (
                                  <div className={clsx(
                                    "rounded-lg border px-3 py-2 text-xs leading-relaxed",
                                    providerConfigCheck.status === 'success'
                                      ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-100"
                                      : "border-red-500/30 bg-red-500/10 text-red-100"
                                  )}>
                                    {providerConfigCheck.message}
                                  </div>
                                )}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </section>
                  )}

                  {observabilitySummary.diagnostics.length > 0 && (
                    <section className="rounded-lg border border-[#1e293b] bg-[#0f1623] p-4">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <h4 className="text-sm font-semibold text-white">诊断建议</h4>
                        {observabilityContractRetryReasons.length > 0 && (
                          <div className="flex flex-wrap gap-2">
                            {observabilityContractRetryReasons.map(([reason, count]) => (
                              <span
                                key={reason}
                                className="rounded-full border border-amber-500/30 bg-amber-500/10 px-2.5 py-1 text-xs font-semibold text-amber-100"
                              >
                                {reason} x{count}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                      <div className="mt-3 grid gap-3 lg:grid-cols-2">
                        {observabilitySummary.diagnostics.map((diagnostic) => {
                          const style = OBSERVABILITY_DIAGNOSTIC_STYLES[diagnostic.severity];
                          return (
                            <article
                              key={diagnostic.id}
                              className={clsx(
                                'rounded-lg border p-3',
                                style.border,
                                style.background,
                              )}
                            >
                              <div className={clsx('text-sm font-semibold', style.label)}>
                                {diagnostic.title}
                              </div>
                              <div className="mt-2 text-xs leading-relaxed text-slate-200">
                                {diagnostic.detail}
                              </div>
                              <div className="mt-3 rounded-lg border border-white/10 bg-[#111827] px-3 py-2 text-xs leading-relaxed text-slate-100">
                                {diagnostic.action}
                              </div>
                            </article>
                          );
                        })}
                      </div>
                    </section>
                  )}

                  <div className="grid gap-3 sm:grid-cols-5">
                    <div className="rounded-lg border border-[#1e293b] bg-[#0f1623] p-4">
                      <div className="text-xs text-slate-500">总轮次</div>
                      <div className="mt-2 text-xl font-bold text-white">{observabilitySummary.totals.turns}</div>
                    </div>
                    <div className="rounded-lg border border-[#1e293b] bg-[#0f1623] p-4">
                      <div className="text-xs text-slate-500">成功率</div>
                      <div className="mt-2 text-xl font-bold text-white">
                        成功率 {observabilitySummary.totals.successRate}%
                      </div>
                    </div>
                    <div className="rounded-lg border border-[#1e293b] bg-[#0f1623] p-4">
                      <div className="text-xs text-slate-500">失败轮次</div>
                      <div className="mt-2 text-xl font-bold text-white">{observabilitySummary.totals.failedTurns}</div>
                    </div>
                    <div className="rounded-lg border border-[#1e293b] bg-[#0f1623] p-4">
                      <div className="text-xs text-slate-500">估算 Token</div>
                      <div className="mt-2 text-xl font-bold text-white">{observabilitySummary.totals.estimatedTokens}</div>
                    </div>
                    <div className="rounded-lg border border-[#1e293b] bg-[#0f1623] p-4">
                      <div className="text-xs text-slate-500">模型/供应商问题</div>
                      <div className={clsx(
                        "mt-2 text-xl font-bold",
                        observabilitySummary.totals.providerIssueCount > 0 ? "text-amber-200" : "text-white"
                      )}>
                        {observabilitySummary.totals.providerIssueCount}
                      </div>
                    </div>
                  </div>

                  <div className="grid gap-4 lg:grid-cols-2">
                    <section className="rounded-lg border border-[#1e293b] bg-[#0f1623] p-4">
                      <h4 className="text-sm font-semibold text-white">按阶段</h4>
                      <div className="mt-3 space-y-3">
                        {observabilitySummary.byStage.length === 0 && (
                          <div className="text-sm text-slate-500">暂无阶段统计</div>
                        )}
                        {observabilitySummary.byStage.map((stage) => (
                          <div key={`${stage.workflowId}-${stage.stageId}`} className="rounded-lg bg-[#111827] p-3">
                            <div className="flex items-center justify-between gap-3">
                              <span className="text-sm font-semibold text-white">{stage.workflowId} / {stage.stageId}</span>
                              <span className="text-xs text-slate-400">成功率 {stage.successRate}%</span>
                            </div>
                            <div className="mt-2 text-xs text-slate-500">
                              {stage.turns} 轮 · 失败 {stage.failedTurns} · 平均 {stage.avgDurationMs}ms
                            </div>
                            {Object.keys(stage.errorCodes).length > 0 && (
                              <div className="mt-2 flex flex-wrap gap-2">
                                {stage.providerIssueCount > 0 && (
                                  <span className="rounded bg-amber-500/10 px-2 py-1 text-xs font-semibold text-amber-200">
                                    模型/供应商问题 x{stage.providerIssueCount}
                                  </span>
                                )}
                                {Object.entries(stage.errorCodes).map(([code, count]) => (
                                  <span key={code} className="rounded bg-red-500/10 px-2 py-1 text-xs text-red-200">
                                    {code} x{count}
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </section>

                    <section className="rounded-lg border border-[#1e293b] bg-[#0f1623] p-4">
                      <h4 className="text-sm font-semibold text-white">按供应商</h4>
                      <div className="mt-3 space-y-3">
                        {observabilitySummary.byProvider.length === 0 && (
                          <div className="text-sm text-slate-500">暂无供应商统计</div>
                        )}
                        {observabilitySummary.byProvider.map((provider) => (
                          <div key={provider.provider} className="rounded-lg bg-[#111827] p-3">
                            <div className="flex items-center justify-between gap-3">
                              <span className="text-sm font-semibold text-white">{provider.provider}</span>
                              <span className="text-xs text-slate-400">成功率 {provider.successRate}%</span>
                            </div>
                            <div className="mt-2 text-xs text-slate-500">
                              {provider.turns} 轮 · 失败 {provider.failedTurns} · 平均 {provider.avgDurationMs}ms
                            </div>
                            {Object.keys(provider.errorCodes).length > 0 && (
                              <div className="mt-2 flex flex-wrap gap-2">
                                {provider.providerIssueCount > 0 && (
                                  <span className="rounded bg-amber-500/10 px-2 py-1 text-xs font-semibold text-amber-200">
                                    模型/供应商问题 x{provider.providerIssueCount}
                                  </span>
                                )}
                                {Object.entries(provider.errorCodes).map(([code, count]) => (
                                  <span key={code} className="rounded bg-red-500/10 px-2 py-1 text-xs text-red-200">
                                    {code} x{count}
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </section>
                  </div>

                  <section className="rounded-lg border border-[#1e293b] bg-[#0f1623] p-4">
                    <h4 className="text-sm font-semibold text-white">最近运行</h4>
                    <div className="mt-3 space-y-2">
                      {observabilitySummary.recentTurns.length === 0 && (
                        <div className="text-sm text-slate-500">暂无运行统计</div>
                      )}
                      {observabilitySummary.recentTurns.map((turn) => (
                        <div key={turn.id} className="rounded-lg bg-[#111827] p-3">
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <span className="text-sm font-semibold text-white">
                              {turn.runId} · {turn.workflowId}/{turn.stageId}
                            </span>
                            <span className={clsx(
                              "rounded px-2 py-1 text-xs font-semibold",
                              turn.status === 'success'
                                ? "bg-emerald-500/10 text-emerald-200"
                                : "bg-red-500/10 text-red-200"
                            )}>
                              {turn.status}
                            </span>
                          </div>
                          <div className="mt-2 flex flex-wrap gap-3 text-xs text-slate-500">
                            <span>{turn.provider}</span>
                            <span>{turn.model}</span>
                            <span>{turn.durationMs}ms</span>
                            <span>{turn.estimatedTokens} tokens</span>
                            {turn.errorCode && <span className="text-red-200">{turn.errorCode}</span>}
                          </div>
                          {turn.diagnostic && (
                            <div className="mt-2 rounded-md border border-amber-400/20 bg-amber-400/10 px-2 py-1.5 text-xs leading-relaxed text-amber-100">
                              <div>{turn.diagnostic.publicReason}</div>
                              <div className="mt-1 flex flex-wrap gap-2 text-amber-100/75">
                                <span>{turn.diagnostic.phase}</span>
                                <span>{turn.diagnostic.fieldPath}</span>
                                <span>{turn.diagnostic.validator}</span>
                                <span>{turn.diagnostic.retryable ? '可重试' : '需处理后重试'}</span>
                              </div>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </section>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {showTestAssets && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
          <div className="flex w-full max-w-4xl flex-col overflow-hidden rounded-xl bg-[#151f2b] shadow-2xl ring-1 ring-white/10">
            <div className="flex items-center justify-between border-b border-white/10 px-5 py-4">
              <div>
                <h3 className="text-base font-bold text-white">Lisa 测试资产</h3>
                {testAssetCollection && (
                  <p className="mt-1 text-xs text-slate-400">
                    来源版本 {testAssetCollection.sourceArtifactVersion}
                  </p>
                )}
              </div>
              <div className="flex items-center gap-2">
                {testAssetCollection && (
                  <button
                    onClick={() => navigate(`/test-assets/${testAssetCollection.id}`)}
                    className="rounded-lg bg-blue-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-blue-500"
                  >
                    打开资产中心
                  </button>
                )}
                <button
                  onClick={() => setShowTestAssets(false)}
                  className="rounded-lg px-3 py-1.5 text-sm text-slate-300 hover:bg-white/5"
                >
                  关闭
                </button>
              </div>
            </div>
            <div className="max-h-[620px] overflow-y-auto p-5">
              {isLoadingTestAssets && (
                <div className="py-12 text-center text-sm text-slate-400">正在加载测试资产...</div>
              )}
              {!isLoadingTestAssets && testAssetsError && (
                <div className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
                  {testAssetsError}
                </div>
              )}
              {!isLoadingTestAssets && testAssetCollection && (
                <div className="space-y-5">
                  <div className={clsx(
                    "rounded-lg border p-4",
                    TEST_ASSET_QUALITY_STATUS_TONE[testAssetCollection.qualitySummary.status],
                  )}>
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <div className="text-xs font-semibold text-slate-300">质量状态</div>
                        <div className="mt-2 text-xl font-bold text-white">
                          {testAssetCollection.qualitySummary.label}
                        </div>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {testAssetCollection.qualitySummary.gates.map(gate => (
                          <div
                            key={gate.id}
                            className={clsx(
                              "rounded px-3 py-2 text-xs font-semibold",
                              TEST_ASSET_QUALITY_GATE_TONE[gate.status],
                            )}
                          >
                            <div>{gate.title}</div>
                            <div className="mt-1 font-medium text-slate-200">
                              {gate.detail}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                  <div className="grid gap-3 sm:grid-cols-3">
                    <div className="rounded-lg border border-[#1e293b] bg-[#0f1623] p-4">
                      <div className="text-xs text-slate-500">覆盖率</div>
                      <div className="mt-2 text-xl font-bold text-white">
                        覆盖率 {Math.round(testAssetCollection.coverageSummary.coverageRate)}%
                      </div>
                    </div>
                    <div className="rounded-lg border border-[#1e293b] bg-[#0f1623] p-4">
                      <div className="text-xs text-slate-500">测试用例</div>
                      <div className="mt-2 text-xl font-bold text-white">
                        {testAssetCollection.coverageSummary.totalTestCases}
                      </div>
                    </div>
                    <div className="rounded-lg border border-[#1e293b] bg-[#0f1623] p-4">
                      <div className="text-xs text-slate-500">测试点</div>
                      <div className="mt-2 text-xl font-bold text-white">
                        {testAssetCollection.coverageSummary.coveredTestPoints}
                        <span className="text-sm font-medium text-slate-500">
                          /{testAssetCollection.coverageSummary.totalTestPoints}
                        </span>
                      </div>
                    </div>
                  </div>

                  {testAssetCollection.intentTesterDrafts.length > 0 && (
                    <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-[#1e293b] bg-[#0f1623] px-4 py-3">
                      <div>
                        <div className="text-sm font-semibold text-white">intent-tester 草稿</div>
                        <div className="mt-1 text-xs text-slate-400">
                          {testAssetCollection.intentTesterDrafts.length} 条草稿可手动导入
                        </div>
                      </div>
                      <button
                        onClick={handleBatchImportIntentTesterDrafts}
                        disabled={isBatchImportingDrafts}
                        className="flex items-center justify-center gap-2 rounded-lg bg-emerald-600 px-3 py-2 text-sm font-semibold text-white hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        <Upload className="h-4 w-4" />
                        批量导入草稿
                      </button>
                    </div>
                  )}

                  <div className="flex flex-wrap items-end justify-between gap-3 rounded-lg border border-[#1e293b] bg-[#0f1623] px-4 py-3">
                    <div>
                      <label htmlFor="batch-priority" className="block text-xs font-semibold text-slate-300">
                        批量优先级
                      </label>
                      <select
                        id="batch-priority"
                        value={batchPriorityDraft}
                        onChange={(event) => setBatchPriorityDraft(event.target.value)}
                        className="mt-2 rounded-lg border border-[#1e293b] bg-[#111827] px-3 py-2 text-sm text-white outline-none focus:border-blue-500"
                      >
                        <option value="P0">P0</option>
                        <option value="P1">P1</option>
                        <option value="P2">P2</option>
                      </select>
                    </div>
                    <button
                      onClick={handleBatchUpdatePriority}
                      disabled={isBatchUpdatingPriority || testAssetCollection.testCases.length === 0}
                      className="rounded-lg bg-blue-600 px-3 py-2 text-sm font-semibold text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      应用优先级
                    </button>
                  </div>

                  {batchImportSummary && (
                    <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-200">
                      {batchImportSummary}
                    </div>
                  )}
                  {batchPrioritySummary && (
                    <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-200">
                      {batchPrioritySummary}
                    </div>
                  )}

                  <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
                    <div className="space-y-3">
                      {testAssetCollection.testCases.map((testCase) => {
                        const draft = testAssetCollection.intentTesterDrafts.find(
                          intentTesterDraft => intentTesterDraft.sourceCaseId === testCase.id
                        );
                        const importedCaseId = importedIntentTesterCaseIds[testCase.id];
                        return (
                          <div
                            key={testCase.id}
                            className="rounded-lg border border-[#1e293b] bg-[#0f1623] p-4"
                          >
                            <div className="flex items-start justify-between gap-4">
                              <div className="min-w-0">
                                <div className="flex flex-wrap items-center gap-2">
                                  <span className="rounded bg-blue-500/10 px-2 py-1 text-xs font-semibold text-blue-200">
                                    {testCase.id}
                                  </span>
                                  <span className="rounded bg-emerald-500/10 px-2 py-1 text-xs font-semibold text-emerald-200">
                                    {testCase.priority}
                                  </span>
                                  <span className="text-xs text-slate-500">版本 {testCase.versionNumber}</span>
                                </div>
                                <div className="mt-3 text-sm font-semibold text-white">{testCase.title}</div>
                                <div className="mt-2 line-clamp-2 text-xs leading-relaxed text-slate-400">
                                  {testCase.testPoint} · {testCase.expectedResult}
                                </div>
                                {importedCaseId !== undefined && (
                                  <div className="mt-3 flex flex-wrap items-center gap-3 text-xs font-semibold">
                                    <span className="text-emerald-300">
                                      已导入 intent-tester #{importedCaseId}
                                    </span>
                                    <a
                                      href={`/intent-tester/execution?testcase_id=${importedCaseId}`}
                                      target="_blank"
                                      rel="noreferrer"
                                      className="text-blue-300 hover:text-blue-200"
                                    >
                                      去执行 #{importedCaseId}
                                    </a>
                                  </div>
                                )}
                              </div>
                              <div className="flex shrink-0 flex-col gap-2">
                                <button
                                  onClick={() => startEditCase(testCase)}
                                  className="rounded-lg border border-[#1e293b] px-3 py-2 text-xs font-semibold text-slate-200 hover:border-blue-500/40 hover:bg-[#172033]"
                                >
                                  编辑 {testCase.id}
                                </button>
                                {draft && (
                                  <button
                                    onClick={() => handleImportIntentTesterDraft(testCase)}
                                    disabled={isBatchImportingDrafts || importingCaseId === testCase.id}
                                    className="flex items-center justify-center gap-1 rounded-lg border border-[#1e293b] px-3 py-2 text-xs font-semibold text-slate-200 hover:border-emerald-500/40 hover:bg-[#172033] disabled:cursor-not-allowed disabled:opacity-60"
                                  >
                                    <Upload className="h-3.5 w-3.5" />
                                    导入 {testCase.id}
                                  </button>
                                )}
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>

                    <div className="space-y-5 rounded-lg border border-[#1e293b] bg-[#0f1623] p-4">
                      {testAssetCollection.assetIssues.length > 0 && (
                        <section>
                          <div className="flex items-center justify-between gap-3">
                            <h4 className="text-sm font-semibold text-white">资产问题</h4>
                            <span className="rounded-full bg-amber-500/10 px-2 py-1 text-xs font-semibold text-amber-200">
                              {testAssetCollection.assetIssues.length} 个问题 · {pendingIssueCount} 待处理
                            </span>
                          </div>
                          <div className="mt-3 space-y-3">
                            {testAssetCollection.assetIssues.map((issue, index) => {
                              const issueStatus = issueStatuses[getIssueKey(issue, index)] || issue.status;
                              return (
                                <div
                                  key={`${issue.type}-${issue.caseId ?? issue.testPoint ?? index}`}
                                  className="border-l border-amber-400/50 pl-3"
                                >
                                  <div className="flex items-start justify-between gap-3">
                                    <div className="text-xs leading-relaxed text-amber-100">
                                      {issue.message}
                                    </div>
                                    <span className="shrink-0 rounded bg-slate-700/70 px-2 py-1 text-[11px] font-semibold text-slate-100">
                                      {TEST_ASSET_ISSUE_STATUS_LABELS[issueStatus]}
                                    </span>
                                  </div>
                                  <div className="mt-2 flex flex-wrap gap-2 text-[11px] font-semibold text-slate-400">
                                    {issue.caseId && <span>{issue.caseId}</span>}
                                    {issue.testPoint && <span>{issue.testPoint}</span>}
                                  </div>
                                  <div className="mt-3 flex flex-wrap gap-2">
                                    <button
                                      onClick={() => void setIssueStatus(issue, index, 'confirmed')}
                                      className="rounded border border-emerald-500/20 bg-emerald-500/10 px-2 py-1 text-[11px] font-semibold text-emerald-200 hover:border-emerald-400/40"
                                    >
                                      确认问题
                                    </button>
                                    <button
                                      onClick={() => void setIssueStatus(issue, index, 'ignored')}
                                      className="rounded border border-slate-500/20 bg-slate-500/10 px-2 py-1 text-[11px] font-semibold text-slate-200 hover:border-slate-400/40"
                                    >
                                      忽略问题
                                    </button>
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        </section>
                      )}
                      {testAssetCollection.riskMatrix.length > 0 && (
                        <section>
                          <div className="flex items-center justify-between gap-3">
                            <h4 className="text-sm font-semibold text-white">风险矩阵</h4>
                            <span className="rounded-full bg-rose-500/10 px-2 py-1 text-xs font-semibold text-rose-200">
                              {testAssetCollection.riskMatrix.length} 项风险
                            </span>
                          </div>
                          <div className="mt-3 space-y-3">
                            {testAssetCollection.riskMatrix.map((risk) => (
                              <div
                                key={risk.risk}
                                className="rounded-lg border border-rose-500/20 bg-rose-500/5 p-3"
                              >
                                <div className="text-xs font-semibold text-rose-100">
                                  {risk.risk}
                                </div>
                                <div className="mt-2 space-y-2 text-[11px] text-slate-400">
                                  <div>
                                    <span className="text-slate-500">用例 </span>
                                    {risk.testCases.join('、') || '-'}
                                  </div>
                                  <div>
                                    <span className="text-slate-500">测试点 </span>
                                    {risk.testPoints.join('、') || '-'}
                                  </div>
                                  <div className="flex flex-wrap gap-2">
                                    {risk.priorities.map((priority) => (
                                      <span
                                        key={priority}
                                        className="rounded bg-emerald-500/10 px-2 py-1 font-semibold text-emerald-200"
                                      >
                                        {priority}
                                      </span>
                                    ))}
                                    {risk.coverageStatuses.map((status) => (
                                      <span
                                        key={status}
                                        className="rounded bg-blue-500/10 px-2 py-1 font-semibold text-blue-200"
                                      >
                                        {status}
                                      </span>
                                    ))}
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        </section>
                      )}
                      {testAssetCollection.testPoints.length > 0 && (
                        <section>
                          <div className="flex items-center justify-between gap-3">
                            <h4 className="text-sm font-semibold text-white">测试点覆盖</h4>
                            <span className="rounded-full bg-blue-500/10 px-2 py-1 text-xs font-semibold text-blue-200">
                              {testAssetCollection.testPoints.length} 个测试点
                            </span>
                          </div>
                          <div className="mt-3 space-y-3">
                            {testAssetCollection.testPoints.map((testPoint) => (
                              <div
                                key={testPoint.testPoint}
                                className="rounded-lg border border-blue-500/20 bg-blue-500/5 p-3"
                              >
                                <div className="flex flex-wrap items-center gap-2">
                                  <span className="text-xs font-semibold text-blue-100">
                                    {testPoint.testPoint}
                                  </span>
                                  <span className="rounded bg-slate-700/70 px-2 py-1 text-[11px] font-semibold text-slate-200">
                                    {testPoint.status}
                                  </span>
                                  <span className="rounded bg-emerald-500/10 px-2 py-1 text-[11px] font-semibold text-emerald-200">
                                    {testPoint.priority}
                                  </span>
                                </div>
                                <div className="mt-2 space-y-1 text-[11px] text-slate-400">
                                  <div>
                                    <span className="text-slate-500">风险 </span>
                                    {testPoint.risk || '-'}
                                  </div>
                                  <div>
                                    <span className="text-slate-500">用例 </span>
                                    {testPoint.testCases.length > 0
                                      ? testPoint.testCases.join('、')
                                      : '无关联用例'}
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        </section>
                      )}
                      {editingCase ? (
                        <form onSubmit={handleSaveTestCase} className="space-y-4">
                          <div>
                            <label htmlFor="test-case-title" className="block text-xs font-semibold text-slate-300">
                              用例标题
                            </label>
                            <input
                              id="test-case-title"
                              value={caseDraft.title}
                              onChange={(event) => setCaseDraft({
                                ...caseDraft,
                                title: event.target.value,
                              })}
                              className="mt-2 w-full rounded-lg border border-[#1e293b] bg-[#111827] px-3 py-2 text-sm text-white outline-none focus:border-blue-500"
                            />
                          </div>
                          <div>
                            <label htmlFor="test-case-priority" className="block text-xs font-semibold text-slate-300">
                              优先级
                            </label>
                            <input
                              id="test-case-priority"
                              value={caseDraft.priority}
                              onChange={(event) => setCaseDraft({
                                ...caseDraft,
                                priority: event.target.value,
                              })}
                              className="mt-2 w-full rounded-lg border border-[#1e293b] bg-[#111827] px-3 py-2 text-sm text-white outline-none focus:border-blue-500"
                            />
                          </div>
                          <button
                            type="submit"
                            disabled={isSavingTestCase}
                            className="flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-3 py-2 text-sm font-semibold text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
                          >
                            <Save className="h-4 w-4" />
                            保存用例
                          </button>
                        </form>
                      ) : (
                        <div className="py-12 text-center text-sm text-slate-500">
                          选择一个测试用例进行编辑
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {showRuns && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
          <div className="flex w-full max-w-5xl flex-col overflow-hidden rounded-xl bg-[#151f2b] shadow-2xl ring-1 ring-white/10">
            <div className="flex items-center justify-between border-b border-white/10 px-5 py-4">
              <div>
                <h3 className="text-base font-bold text-white">历史会话</h3>
                <p className="mt-1 text-xs text-slate-500">筛选、预览并复用已有 run</p>
              </div>
              <button
                onClick={() => setShowRuns(false)}
                className="rounded-lg px-3 py-1.5 text-sm text-slate-300 hover:bg-white/5"
              >
                关闭
              </button>
            </div>
            <div className="flex gap-2 border-b border-white/10 px-5 py-3">
              <button
                onClick={() => handleRunListScopeChange('all')}
                className={clsx(
                  "rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors",
                  runListScope === 'all'
                    ? "bg-blue-600 text-white"
                    : "bg-[#0f1623] text-slate-300 hover:bg-white/5"
                )}
              >
                全部
              </button>
              <button
                onClick={() => handleRunListScopeChange('workflow')}
                className={clsx(
                  "rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors",
                  runListScope === 'workflow'
                    ? "bg-blue-600 text-white"
                    : "bg-[#0f1623] text-slate-300 hover:bg-white/5"
                )}
              >
                当前工作流
              </button>
            </div>
            <div className="flex flex-wrap gap-2 border-b border-white/10 px-5 py-3">
              {[
                ['all', '全部状态'],
                ['ready', '可复用'],
                ['needs_artifact', '无产物'],
                ['failed', '失败'],
              ].map(([status, label]) => (
                <button
                  key={status}
                  type="button"
                  onClick={() => handleRunReuseStatusFilterChange(status as RunReuseStatus | 'all')}
                  className={clsx(
                    "rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors",
                    runReuseStatusFilter === status
                      ? "bg-blue-600 text-white"
                      : "bg-[#0f1623] text-slate-300 hover:bg-white/5"
                  )}
                >
                  {label}
                </button>
              ))}
            </div>
            <form
              onSubmit={handleSearchRuns}
              className="flex items-center gap-2 border-b border-white/10 px-5 py-3"
            >
              <label htmlFor="run-history-search" className="sr-only">搜索历史会话</label>
              <div className="flex min-w-0 flex-1 items-center gap-2 rounded-lg border border-[#1e293b] bg-[#0f1623] px-3 py-2 text-slate-300">
                <Search className="h-4 w-4 shrink-0 text-slate-500" />
                <input
                  id="run-history-search"
                  value={runSearchDraft}
                  onChange={(event) => setRunSearchDraft(event.target.value)}
                  className="min-w-0 flex-1 bg-transparent text-sm text-white outline-none placeholder:text-slate-500"
                  placeholder="搜索消息、摘要或阶段"
                />
              </div>
              <button
                type="submit"
                className="rounded-lg bg-blue-600 px-3 py-2 text-sm font-semibold text-white hover:bg-blue-500"
              >
                搜索
              </button>
            </form>
            <div className="grid max-h-[560px] overflow-hidden lg:grid-cols-[minmax(0,1fr)_360px]">
              <div className="overflow-y-auto p-3">
                {isLoadingRuns && (
                  <div className="px-3 py-8 text-center text-sm text-slate-400">正在加载历史会话...</div>
                )}
                {!isLoadingRuns && runsError && (
                  <div className="px-3 py-8 text-center text-sm text-red-300">{runsError}</div>
                )}
                {!isLoadingRuns && !runsError && recentRuns.length === 0 && (
                  <div className="px-3 py-8 text-center text-sm text-slate-400">暂无历史会话</div>
                )}
                {!isLoadingRuns && !runsError && recentRuns.length > 0 && (
                  <div className="space-y-3">
                    <div className="px-1 text-xs text-slate-500">
                      共 {runTotal} 条历史会话
                    </div>
                    <div className="space-y-2">
                      {recentRuns.map((run) => {
                        const workflowConfig = WORKFLOWS[run.workflowId];
                        const stageName = workflowConfig.stages.find(stage => stage.id === run.currentStageId)?.name || run.currentStageId;
                        const summary = run.currentArtifact?.summary || run.lastMessage?.content || '暂无摘要';
                        return (
                          <button
                            key={run.id}
                            type="button"
                            onClick={() => void handleSelectRun(run)}
                            className={clsx(
                              "w-full rounded-lg border bg-[#0f1623] p-3 text-left transition-colors hover:border-blue-500/40 hover:bg-[#172033]",
                              selectedRun?.id === run.id
                                ? "border-blue-500/60 bg-[#172033]"
                                : "border-[#1e293b]"
                            )}
                          >
                            <div className="flex items-start justify-between gap-3">
                              <div className="min-w-0">
                                <div className="truncate text-sm font-semibold text-white">
                                  {workflowConfig.name} / {stageName}
                                </div>
                                <div className="mt-1 line-clamp-2 text-xs leading-relaxed text-slate-400">
                                  {summary}
                                </div>
                              </div>
                              <div className="flex shrink-0 flex-col items-end gap-2">
                                <span className={clsx(
                                  "rounded px-2 py-1 text-[10px] font-semibold",
                                  RUN_REUSE_STATUS_TONE[run.reuseStatus],
                                )}>
                                  {RUN_REUSE_STATUS_LABELS[run.reuseStatus]}
                                </span>
                                <span className="text-[10px] uppercase tracking-wide text-slate-500">
                                  {run.status}
                                </span>
                              </div>
                            </div>
                          </button>
                        );
                      })}
                    </div>
                    {hasMoreRuns && (
                      <button
                        type="button"
                        onClick={handleLoadMoreRuns}
                        className="w-full rounded-lg border border-[#1e293b] bg-[#101827] px-3 py-2 text-sm font-semibold text-slate-200 hover:border-blue-500/40 hover:bg-[#172033]"
                      >
                        加载更多
                      </button>
                    )}
                  </div>
                )}
              </div>

              <aside className="border-t border-white/10 bg-[#0f1623] p-4 lg:border-l lg:border-t-0">
                {!selectedRun && (
                  <div className="flex h-full min-h-[260px] items-center justify-center rounded-lg border border-dashed border-[#1e293b] px-4 text-center text-sm text-slate-500">
                    选择一条历史会话查看预览
                  </div>
                )}
                {selectedRun && (
                  <div className="space-y-4">
                    <div>
                      <div className="flex items-center justify-between gap-3">
                        <h4 className="text-sm font-semibold text-white">
                          {WORKFLOWS[selectedRun.workflowId].name}
                        </h4>
                        <span className={clsx(
                          "rounded px-2 py-1 text-[10px] font-semibold",
                          RUN_REUSE_STATUS_TONE[selectedRun.reuseStatus],
                        )}>
                          {RUN_REUSE_STATUS_LABELS[selectedRun.reuseStatus]}
                        </span>
                      </div>
                      <div className="mt-1 text-xs text-slate-500">
                        {selectedRun.currentStageId} · {selectedRun.id}
                      </div>
                    </div>

                    {isLoadingRunPreview && (
                      <div className="rounded-lg border border-[#1e293b] bg-[#111827] px-4 py-8 text-center text-sm text-slate-400">
                        正在加载历史会话预览...
                      </div>
                    )}
                    {!isLoadingRunPreview && runPreviewError && (
                      <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
                        {runPreviewError}
                      </div>
                    )}
                    {!isLoadingRunPreview && !runPreviewError && (
                      <div className="rounded-lg border border-[#1e293b] bg-[#111827] p-4">
                        <div className="text-xs font-semibold text-slate-300">当前产物预览</div>
                        <div className="mt-3 max-h-52 overflow-y-auto whitespace-pre-wrap text-xs leading-relaxed text-slate-300">
                          {selectedRunPreview || '暂无可预览内容'}
                        </div>
                      </div>
                    )}

                    {cloneRunError && (
                      <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
                        {cloneRunError}
                      </div>
                    )}

                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={() => handleContinueRun()}
                        className="rounded-lg border border-[#1e293b] px-3 py-2 text-sm font-semibold text-slate-200 hover:border-blue-500/40 hover:bg-[#172033]"
                      >
                        继续此 run
                      </button>
                      <button
                        type="button"
                        onClick={() => void handleCloneSelectedRun()}
                        disabled={cloningRunId === selectedRun.id}
                        className="rounded-lg bg-blue-600 px-3 py-2 text-sm font-semibold text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        复制为新 run
                      </button>
                    </div>
                  </div>
                )}
              </aside>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
