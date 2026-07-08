export type Attachment = {
    name: string;
    data: string;
    mimeType: string;
};

export type ArtifactVersion = {
    id: string;
    timestamp: number;
    content: string;
    stageId: string;
};

export type ArtifactVersionInput = ArtifactVersion | Omit<ArtifactVersion, 'stageId'>;

export type ArtifactCommentStatus = 'open' | 'resolved';

export type ArtifactCommentReply = {
    id: string;
    content: string;
    createdAt: number;
};

export type ArtifactComment = {
    id: string;
    stageId: string;
    content: string;
    artifactExcerpt: string;
    anchorText: string | null;
    createdAt: number;
    status: ArtifactCommentStatus;
    resolvedAt: number | null;
    replies: ArtifactCommentReply[];
};

export type ArtifactCommentInput = Pick<ArtifactComment, 'content' | 'artifactExcerpt'> & Partial<Pick<ArtifactComment, 'stageId' | 'anchorText'>>;

export type ArtifactSectionLock = {
    id: string;
    stageId: string;
    heading: string;
    sectionAnchor: string | null;
    content: string;
    createdAt: number;
};

export type ArtifactSectionLockInput = Pick<ArtifactSectionLock, 'heading' | 'content'> & Partial<Pick<ArtifactSectionLock, 'stageId' | 'sectionAnchor'>>;

export type ArtifactAuditEvent = {
    stageId: string;
    eventType: string;
    summary: string;
    createdAt: number;
};

export type ArtifactAuditEventInput = Pick<ArtifactAuditEvent, 'eventType' | 'summary'> & Partial<Pick<ArtifactAuditEvent, 'stageId' | 'createdAt'>>;

export type ArtifactVisualDiagnosticKind = 'mermaid' | 'structured-visual';

export type ArtifactVisualDiagnostic = {
    id: string;
    stageId: string;
    kind: ArtifactVisualDiagnosticKind;
    title: string;
    message: string;
    blockIndex?: number;
    createdAt: number;
};

export type ArtifactVisualDiagnosticInput = Omit<ArtifactVisualDiagnostic, 'createdAt'> & Partial<Pick<ArtifactVisualDiagnostic, 'createdAt'>>;

export type ArtifactVisualDiagnosticFocusRequest = {
    id: string;
    seq: number;
};

export type PendingStageTransition = {
    fromStageIndex: number;
    toStageIndex: number;
};

export type MessageErrorDiagnosticKind = 'structured' | 'provider' | 'generic';

export type MessageErrorDiagnostic = {
    kind: MessageErrorDiagnosticKind;
    summary: string;
    rawMessage: string;
    reason?: string;
    action?: string;
    code?: string;
    phase?: string;
    workflowId?: string;
    stageId?: string;
    fieldPath?: string;
    validator?: string;
    retryable?: boolean;
};

export type Message = {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    timestamp: number;
    attachments?: Attachment[];
    retryable?: boolean;
    errorDiagnostic?: MessageErrorDiagnostic;
};

// 已实现的工作流类型（仅包含 online 状态）
export type WorkflowType =
    | 'TEST_DESIGN'
    | 'REQ_REVIEW'
    | 'INCIDENT_REVIEW'
    | 'IDEA_BRAINSTORM'
    | 'VALUE_DISCOVERY'
    | 'STORY_BREAKDOWN'
    | 'PRD_REVIEW';

export type WorkflowHandoff = {
    id: string;
    label: string;
    sourceRunId?: string;
    sourceWorkflowId: WorkflowType;
    sourceStageId: string;
    sourceArtifactVersion: number;
    sourceArtifactDigest?: string;
    sourceArtifactSummary?: string;
    sourceSummary?: string;
    unconfirmedItems: string[];
    targetInputChecklist: string[];
    targetRunId?: string;
    targetWorkflowId: WorkflowType;
    targetStageId: string;
    targetAgentId: string;
    prompt: string;
};

export type StoryHandoffCandidate = {
    storyId: string;
    title: string;
    requirementIds: string[];
    userValue: string;
    readyReason: string;
};

export type StoryHandoffCandidateResponse = {
    runId: string;
    workflowId: WorkflowType;
    stageId: string;
    sourceArtifactVersion: number;
    sourceArtifactDigest: string;
    candidates: StoryHandoffCandidate[];
};

export type StoryHandoffPacket = {
    sourceRunId: string;
    sourceWorkflowId: WorkflowType;
    sourceStageId: string;
    sourceArtifactVersion: number;
    sourceArtifactDigest: string;
    createdAt: number;
    storyId: string;
    requirementIds: string[];
    userStory: string;
    acceptanceCriteria: string[];
    businessRules: string[];
    nonFunctionalNotes: string[];
    outOfScope: string[];
    dependencies: string[];
    openQuestions: string[];
};

export type StoryHandoffPacketListItem = {
    id: string;
    storyId: string;
    createdAt: number;
    isStale: boolean;
    currentSourceArtifactVersion: number;
    currentSourceArtifactDigest: string;
    packet: StoryHandoffPacket;
};

export type StoryHandoffPacketListResponse = {
    runId: string;
    workflowId: WorkflowType;
    stageId: string;
    sourceArtifactVersion: number;
    sourceArtifactDigest: string;
    packets: StoryHandoffPacketListItem[];
};

export type AgentRunSnapshotMessage = {
    role: 'user' | 'assistant';
    content: string;
    sequenceIndex: number;
};

export type AgentRunSnapshotArtifact = {
    stageId: string;
    content: string;
    versionNumber: number;
};

export type AgentRunSnapshotContextSummary = {
    sourceType: string;
    sourceStageId: string | null;
    summaryType: string;
    content: string;
};

export type AgentRunSnapshot = {
    run: {
        id: string;
        workflowId: WorkflowType;
        agentId: string;
        currentStageId: string;
        status: string;
        model: string | null;
    };
    messages: AgentRunSnapshotMessage[];
    artifacts: AgentRunSnapshotArtifact[];
    contextSummaries: AgentRunSnapshotContextSummary[];
    artifactComments: ArtifactComment[];
    artifactSectionLocks: ArtifactSectionLock[];
    artifactAuditEvents: ArtifactAuditEvent[];
};

export type RunReuseStatus = 'ready' | 'needs_artifact' | 'failed';

export type AgentRunListItem = {
    id: string;
    workflowId: WorkflowType;
    agentId: string;
    currentStageId: string;
    status: string;
    reuseStatus: RunReuseStatus;
    model: string | null;
    createdAt: string | null;
    updatedAt: string | null;
    lastMessage: AgentRunSnapshotMessage | null;
    currentArtifact: {
        stageId: string;
        versionNumber: number | null;
        summary: string;
    } | null;
};

export type AgentRunListResponse = {
    limit: number;
    offset: number;
    total: number;
    hasMore: boolean;
    nextOffset: number | null;
    query: string | null;
    runs: AgentRunListItem[];
};

export type TestAssetCoverageSummary = {
    totalTestCases: number;
    totalTestPoints: number;
    coveredTestPoints: number;
    partiallyCoveredTestPoints: number;
    uncoveredTestPoints: number;
    coverageRate: number;
    byPriority: Array<{
        priority: string;
        total: number;
        covered: number;
        partial: number;
        uncovered: number;
        coverageRate: number;
    }>;
};

export type TestAssetQualityStatus = 'blocked' | 'attention' | 'ready';

export type TestAssetQualityGateStatus = 'fail' | 'warn' | 'pass';

export type TestAssetQualityGate = {
    id: string;
    status: TestAssetQualityGateStatus;
    title: string;
    detail: string;
};

export type TestAssetQualitySummary = {
    status: TestAssetQualityStatus;
    label: string;
    pendingIssueCount: number;
    confirmedIssueCount: number;
    ignoredIssueCount: number;
    uncoveredTestPointCount: number;
    partialTestPointCount: number;
    openRiskCount: number;
    mitigatingRiskCount: number;
    acceptedRiskCount: number;
    closedRiskCount: number;
    gates: TestAssetQualityGate[];
};

export type TestAssetCase = {
    id: string;
    title: string;
    priority: string;
    dimension: string;
    testPoint: string;
    risk: string;
    precondition: string;
    steps: string;
    testData: string;
    expectedResult: string;
    versionNumber: number;
    versions: Array<Omit<TestAssetCase, 'id' | 'versions'>>;
};

export type TestAssetPoint = {
    testPoint: string;
    priority: string;
    risk: string;
    testCases: string[];
    status: string;
};

export type IntentTesterStep = {
    action: string;
    params: Record<string, unknown>;
};

export type IntentTesterDraft = {
    sourceCaseId: string;
    name: string;
    description: string;
    category: string;
    priority: number;
    tags: string[];
    steps: IntentTesterStep[];
    draftWarnings: string[];
};

export type IntentTesterImportResult = {
    id: number;
    name: string;
};

export type IntentTesterExecutionCreateResult = {
    executionId: string;
    status: string;
    testcaseName: string;
    startTime: string;
};

export type IntentTesterExecutionRecord = {
    executionId: string;
    testCaseId: number;
    status: string;
    mode: string;
    browser: string;
    startTime: string | null;
    endTime: string | null;
    duration: number | null;
    errorMessage: string | null;
};

export type IntentTesterExecutionStep = {
    stepIndex: number;
    description: string;
    status: string;
    errorMessage: string | null;
    screenshotPath: string | null;
    action: string | null;
};

export type IntentTesterExecutionDetail = IntentTesterExecutionRecord & {
    stepsTotal: number | null;
    stepsPassed: number | null;
    stepsFailed: number | null;
    steps: IntentTesterExecutionStep[];
};

export type TestAssetIntentTesterResultSnapshot = {
    executionId: string;
    status: string;
    stepsTotal: number;
    stepsPassed: number;
    stepsFailed: number;
    duration: number | null;
    errorMessage: string | null;
    screenshots: string[];
    failedSteps: IntentTesterExecutionStep[];
};

export type TestAssetIntentTesterMapping = {
    sourceCaseId: string;
    intentTesterCaseId: number;
    intentTesterCaseName: string;
    latestExecution: IntentTesterExecutionRecord | null;
    latestResult: TestAssetIntentTesterResultSnapshot | null;
};

export type TestAssetIssueStatus = 'pending' | 'confirmed' | 'ignored';

export type TestAssetIssue = {
    id: number;
    type: string;
    caseId?: string;
    testPoint?: string;
    message: string;
    status: TestAssetIssueStatus;
};

export type TestAssetRiskStatus = 'open' | 'mitigating' | 'accepted' | 'closed';

export type TestAssetRisk = {
    id: number;
    risk: string;
    isManual: boolean;
    testCases: string[];
    testPoints: string[];
    priorities: string[];
    dimensions: string[];
    coverageStatuses: string[];
    status: TestAssetRiskStatus;
    owner: string;
    note: string;
};

export type TestAssetCollection = {
    id: number;
    runId: string;
    workflowId: WorkflowType;
    sourceStageId: string;
    sourceArtifactVersion: number;
    coverageSummary: TestAssetCoverageSummary;
    qualitySummary: TestAssetQualitySummary;
    testCases: TestAssetCase[];
    testPoints: TestAssetPoint[];
    coverageTrace: TestAssetPoint[];
    assetIssues: TestAssetIssue[];
    riskMatrix: TestAssetRisk[];
    intentTesterDrafts: IntentTesterDraft[];
    intentTesterMappings: TestAssetIntentTesterMapping[];
};

export type TestAssetIntentTesterCasePatch = {
    intentTesterCaseId: number;
    intentTesterCaseName: string;
};

export type TestAssetCasePatch = Partial<Pick<
    TestAssetCase,
    | 'title'
    | 'priority'
    | 'dimension'
    | 'testPoint'
    | 'risk'
    | 'precondition'
    | 'steps'
    | 'testData'
    | 'expectedResult'
>>;

export type TestAssetPointPatch = Partial<Pick<
    TestAssetPoint,
    | 'priority'
    | 'risk'
    | 'testCases'
    | 'status'
>>;

export type TestAssetRiskPatch = Partial<Pick<
    TestAssetRisk,
    | 'risk'
    | 'status'
    | 'owner'
    | 'note'
>>;

export type TestAssetRiskCreatePatch = Pick<TestAssetRisk, 'risk'> & Partial<Pick<
    TestAssetRisk,
    | 'status'
    | 'owner'
    | 'note'
>>;

export type TestAssetRiskDeleteResult = {
    id: number;
    deleted: boolean;
};

export type ObservabilityTotals = {
    turns: number;
    failedTurns: number;
    successRate: number;
    avgDurationMs: number;
    estimatedTokens: number;
    providerIssueCount: number;
    providerIssueCodes: Record<string, number>;
};

export type ObservabilityDiagnosticSeverity = 'info' | 'warning' | 'critical';

export type ObservabilityDiagnostic = {
    id: string;
    severity: ObservabilityDiagnosticSeverity;
    title: string;
    detail: string;
    action: string;
};

export type ObservabilityStageSummary = ObservabilityTotals & {
    workflowId: WorkflowType;
    stageId: string;
    errorCodes: Record<string, number>;
};

export type ObservabilityProviderSummary = ObservabilityTotals & {
    provider: string;
    errorCodes: Record<string, number>;
};

export type ObservabilityTurn = {
    id: number;
    runId: string;
    workflowId: WorkflowType;
    stageId: string;
    model: string;
    provider: string;
    status: string;
    errorCode: string | null;
    durationMs: number;
    inputChars: number;
    outputChars: number;
    estimatedTokens: number;
    contractRetryCount: number;
    createdAt: string | null;
};

export type ObservabilitySummary = {
    contractRetryReasons: Record<string, number>;
    diagnostics: ObservabilityDiagnostic[];
    totals: ObservabilityTotals;
    byStage: ObservabilityStageSummary[];
    byProvider: ObservabilityProviderSummary[];
    recentTurns: ObservabilityTurn[];
};

export interface ArtifactContract {
    requiredHeadings: string[];
}

export interface ArtifactDataContract {
    modelOutputRules: string[];
    forbiddenOutputs: string[];
    rendererOutputs: string[];
}

export interface VisualContract {
    requiredMermaidDiagrams?: string[];
    requiredStructuredVisuals?: string[];
}

export type ArtifactContractConfig = ArtifactContract;
export type ArtifactDataContractConfig = ArtifactDataContract;
export type VisualContractConfig = VisualContract;

export type ArtifactSectionChangeKind = 'added' | 'modified' | 'removed';

export type ArtifactSectionChange = {
    kind: ArtifactSectionChangeKind;
    title: string;
    anchor: string;
    heading: string;
};

export type ArtifactSectionPatchOperation = 'replace' | 'add_after';

export type ArtifactSectionPatch = {
    operation: ArtifactSectionPatchOperation;
    sectionAnchor: string;
    replacementMarkdown: string;
    afterSectionAnchor?: string;
    baseContent?: string;
};

export type ArtifactSectionPatchFallbackReason =
    | 'section_not_found'
    | 'anchor_not_found'
    | 'base_content_mismatch'
    | 'replacement_section_missing';

export type ArtifactSectionPatchApplyResult = {
    applied: boolean;
    content: string;
    changes: ArtifactSectionChange[];
    fallbackReason?: ArtifactSectionPatchFallbackReason;
};

export interface WorkflowStage {
    id: string;
    name: string;
    description: string;
    template?: string;
    methodIds?: string[];
    promptTemplateVersion?: string;
    regressionSampleIds?: string[];
    artifactContract?: ArtifactContract;
    artifactDataContract?: ArtifactDataContract;
    visualContract?: VisualContract;
}

export interface OnboardingConfig {
    welcomeMessage: string;
    starterPrompts: string[];
    inputPlaceholder: string;
}

export interface WorkflowPreviewConfig {
    suitableFor: string[];
    notSuitableFor: string[];
    requiredInputs: string[];
    expectedOutputs: string[];
    sampleInput: string;
}

export interface WorkflowListingConfig {
    name: string;
    description: string;
    icon: string;
    preview: WorkflowPreviewConfig;
}

export interface WorkflowDef {
    id: WorkflowType;
    agentId: string;
    slug: string;
    welcomeMessage?: string;
    description: string;
    name: string;
    listing: WorkflowListingConfig;
    stages: WorkflowStage[];
    onboarding: OnboardingConfig;
}

export interface ChatState {
    workflow: WorkflowType;
    stageIndex: number;
    chatHistory: Message[];
    artifactContent: string;
    artifactHistory: ArtifactVersion[];
    artifactComments: ArtifactComment[];
    artifactSectionLocks: ArtifactSectionLock[];
    artifactAuditEvents: ArtifactAuditEvent[];
    artifactVisualDiagnostics: ArtifactVisualDiagnostic[];
    artifactVisualDiagnosticFocusRequest: ArtifactVisualDiagnosticFocusRequest | null;
    artifactChangeIndex: ArtifactSectionChange[];
    stageArtifacts: Record<string, string>;
    contextSummaries: AgentRunSnapshotContextSummary[];
    currentRunId: string | null;
    isSettingsOpen: boolean;
    configRefreshSeq: number;
    isGenerating: boolean;
    // P0-4: Stage transition confirmation gate
    pendingStageTransition: PendingStageTransition | null;
    // P0-9: Artifact truncation flag
    artifactTruncated: boolean;

    // Actions
    setWorkflow: (workflow: WorkflowType) => void;
    setStageIndex: (index: number) => void;
    transitionToNextStage: (initialStageId: string, initialArtifact: string) => void;
    addMessage: (msg: Message) => void;
    updateLastMessage: (content: string, errorDiagnostic?: MessageErrorDiagnostic) => void;
    updateMessage: (id: string, content: string) => void;
    removeLastMessage: () => void;
    setArtifactContent: (content: string) => void;
    applyArtifactSectionPatch: (patch: ArtifactSectionPatch) => ArtifactSectionPatchApplyResult;
    addArtifactVersion: (version: ArtifactVersionInput) => void;
    addArtifactComment: (comment: ArtifactCommentInput) => void;
    addArtifactCommentReply: (commentId: string, content: string) => void;
    setArtifactCommentStatus: (commentId: string, status: ArtifactCommentStatus) => void;
    updateArtifactCommentAnchor: (commentId: string, anchorText: string) => void;
    removeArtifactComment: (commentId: string) => void;
    getArtifactCommentsForStage: (stageId: string) => ArtifactComment[];
    addArtifactSectionLock: (lock: ArtifactSectionLockInput) => void;
    removeArtifactSectionLock: (lockId: string) => void;
    getArtifactSectionLocksForStage: (stageId: string) => ArtifactSectionLock[];
    addArtifactAuditEvent: (event: ArtifactAuditEventInput) => void;
    getArtifactAuditEventsForStage: (stageId: string) => ArtifactAuditEvent[];
    setArtifactVisualDiagnostic: (diagnostic: ArtifactVisualDiagnosticInput) => void;
    clearArtifactVisualDiagnostic: (diagnosticId: string) => void;
    clearArtifactVisualDiagnosticsForStage: (stageId: string) => void;
    focusArtifactVisualDiagnostic: (diagnosticId: string) => void;
    setCurrentRunId: (runId: string | null) => void;
    applyWorkflowHandoff: (handoff: WorkflowHandoff) => void;
    restoreRunSnapshot: (snapshot: AgentRunSnapshot) => void;
    updateContextSummaryContent: (
        summary: Pick<AgentRunSnapshotContextSummary, 'sourceType' | 'sourceStageId' | 'summaryType'>,
        content: string
    ) => void;
    upsertContextSummary: (summary: AgentRunSnapshotContextSummary) => void;
    setSettingsOpen: (isOpen: boolean) => void;
    notifyDefaultLlmConfigChanged: () => void;
    setIsGenerating: (isGenerating: boolean) => void;
    clearHistory: () => void;
    setStageArtifact: (stageId: string, content: string) => void;
    // P0-4: Stage transition actions
    setPendingStageTransition: (pending: PendingStageTransition | null) => void;
    clearPendingStageTransition: () => void;
    confirmStageTransition: () => void;
    // P0-9: Artifact truncation action
    setArtifactTruncated: (truncated: boolean) => void;
}
