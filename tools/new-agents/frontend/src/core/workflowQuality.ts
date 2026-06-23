import { buildArtifactQualityDiagnostics } from './artifactDiagnostics';
import { WORKFLOWS } from './workflows';
import type { ArtifactVisualDiagnostic, WorkflowType } from './types';

export type WorkflowStageQualityStatus = 'not-started' | 'blocked' | 'attention' | 'ready';
export type WorkflowQualityPendingSeverity = 'blocker' | 'attention' | 'not-started';

export interface WorkflowQualityEvidenceItem {
    id: string;
    status: 'pass' | 'warn' | 'fail';
    title: string;
    detail: string;
    nextAction: string;
}

export interface WorkflowQualityPendingItem {
    id: string;
    stageIndex: number;
    stageId: string;
    stageName: string;
    severity: WorkflowQualityPendingSeverity;
    title: string;
    detail: string;
    nextAction: string;
}

export interface WorkflowStageQualitySummary {
    stageIndex: number;
    stageId: string;
    stageName: string;
    isCurrentStage: boolean;
    score: number;
    status: WorkflowStageQualityStatus;
    label: string;
    evidenceItems: WorkflowQualityEvidenceItem[];
    pendingItems: WorkflowQualityPendingItem[];
    nextAction: string;
}

export interface WorkflowQualitySummary {
    averageScore: number;
    nextFocusStageIndex: number | null;
    pendingQueue: WorkflowQualityPendingItem[];
    totals: {
        stages: number;
        ready: number;
        attention: number;
        blocked: number;
        notStarted: number;
        pendingItems: number;
    };
    stages: WorkflowStageQualitySummary[];
}

export interface BuildWorkflowQualitySummaryInput {
    workflowId: WorkflowType;
    currentStageId: string | null | undefined;
    currentArtifactContent: string;
    stageArtifacts: Record<string, string>;
    visualDiagnostics: ArtifactVisualDiagnostic[];
}

const STATUS_LABELS: Record<WorkflowStageQualityStatus, string> = {
    'not-started': '待生成',
    blocked: '需处理',
    attention: '需关注',
    ready: '可推进',
};

const SEVERITY_WEIGHT: Record<WorkflowQualityPendingSeverity, number> = {
    blocker: 0,
    attention: 1,
    'not-started': 2,
};

const clampScore = (score: number): number => Math.max(0, Math.min(100, score));

const resolveStageContent = (
    stageId: string,
    currentStageId: string | null | undefined,
    currentArtifactContent: string,
    stageArtifacts: Record<string, string>
): string => {
    if (stageId === currentStageId && currentArtifactContent.trim()) {
        return currentArtifactContent;
    }
    return stageArtifacts[stageId] || '';
};

export const buildWorkflowQualitySummary = ({
    workflowId,
    currentStageId,
    currentArtifactContent,
    stageArtifacts,
    visualDiagnostics,
}: BuildWorkflowQualitySummaryInput): WorkflowQualitySummary => {
    const workflow = WORKFLOWS[workflowId];
    const stages = workflow.stages.map((stage, stageIndex): WorkflowStageQualitySummary => {
        const artifactContent = resolveStageContent(
            stage.id,
            currentStageId,
            currentArtifactContent,
            stageArtifacts
        );
        if (!artifactContent.trim()) {
            const pendingItem: WorkflowQualityPendingItem = {
                id: `${stage.id}:not-started`,
                stageIndex,
                stageId: stage.id,
                stageName: stage.name,
                severity: 'not-started',
                title: '待生成产物',
                detail: `${stage.name} 阶段还没有可审阅的 artifact。`,
                nextAction: '先生成该阶段产物。',
            };
            return {
                stageIndex,
                stageId: stage.id,
                stageName: stage.name,
                isCurrentStage: stage.id === currentStageId,
                score: 0,
                status: 'not-started',
                label: STATUS_LABELS['not-started'],
                evidenceItems: [],
                pendingItems: [pendingItem],
                nextAction: pendingItem.nextAction,
            };
        }

        const diagnostics = buildArtifactQualityDiagnostics({
            workflowId,
            stageId: stage.id,
            artifactContent,
            visualDiagnostics,
        });
        const evidenceItems: WorkflowQualityEvidenceItem[] = diagnostics.items.map(item => ({
            id: item.id,
            status: item.status,
            title: item.title,
            detail: item.detail,
            nextAction: item.nextAction,
        }));
        const pendingItems: WorkflowQualityPendingItem[] = [
            ...diagnostics.items
                .filter(item => item.status === 'fail' || item.status === 'warn')
                .map((item): WorkflowQualityPendingItem => ({
                    id: `${stage.id}:${item.id}`,
                    stageIndex,
                    stageId: stage.id,
                    stageName: stage.name,
                    severity: item.status === 'fail' ? 'blocker' : 'attention',
                    title: item.title,
                    detail: item.detail,
                    nextAction: item.nextAction,
                })),
            ...diagnostics.openQuestions.map((question): WorkflowQualityPendingItem => ({
                id: `${stage.id}:${question.id}`,
                stageIndex,
                stageId: stage.id,
                stageName: stage.name,
                severity: question.blocking ? 'blocker' : 'attention',
                title: question.title,
                detail: question.detail,
                nextAction: question.nextAction,
            })),
        ];
        const failCount = diagnostics.items.filter(item => item.status === 'fail').length;
        const warnCount = diagnostics.items.filter(item => item.status === 'warn').length;
        const blockingQuestionCount = diagnostics.openQuestions.filter(question => question.blocking).length;
        const nonBlockingQuestionCount = diagnostics.openQuestions.length - blockingQuestionCount;
        const score = clampScore(
            100
            - (failCount * 20)
            - (warnCount * 8)
            - (blockingQuestionCount * 18)
            - (nonBlockingQuestionCount * 8)
        );
        const hasBlocker = failCount > 0 || blockingQuestionCount > 0;
        const hasAttention = warnCount > 0 || nonBlockingQuestionCount > 0;
        const status: WorkflowStageQualityStatus = hasBlocker
            ? 'blocked'
            : hasAttention
                ? 'attention'
                : 'ready';
        const nextAction = pendingItems[0]?.nextAction || '当前阶段质量证据完整，可继续推进。';

        return {
            stageIndex,
            stageId: stage.id,
            stageName: stage.name,
            isCurrentStage: stage.id === currentStageId,
            score,
            status,
            label: STATUS_LABELS[status],
            evidenceItems,
            pendingItems,
            nextAction,
        };
    });

    const pendingQueue = stages
        .flatMap(stage => stage.pendingItems)
        .sort((left, right) => (
            SEVERITY_WEIGHT[left.severity] - SEVERITY_WEIGHT[right.severity]
            || left.stageIndex - right.stageIndex
        ));
    const totals = stages.reduce<WorkflowQualitySummary['totals']>(
        (accumulator, stage) => ({
            stages: accumulator.stages + 1,
            ready: accumulator.ready + (stage.status === 'ready' ? 1 : 0),
            attention: accumulator.attention + (stage.status === 'attention' ? 1 : 0),
            blocked: accumulator.blocked + (stage.status === 'blocked' ? 1 : 0),
            notStarted: accumulator.notStarted + (stage.status === 'not-started' ? 1 : 0),
            pendingItems: accumulator.pendingItems + stage.pendingItems.length,
        }),
        { stages: 0, ready: 0, attention: 0, blocked: 0, notStarted: 0, pendingItems: 0 }
    );
    const scoreTotal = stages.reduce((total, stage) => total + stage.score, 0);

    return {
        averageScore: stages.length === 0 ? 0 : Math.round(scoreTotal / stages.length),
        nextFocusStageIndex: pendingQueue[0]?.stageIndex ?? null,
        pendingQueue,
        totals,
        stages,
    };
};
