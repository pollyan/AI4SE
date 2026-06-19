import type {
    ObservabilityProviderSummary,
    ObservabilityStageSummary,
    ObservabilitySummary,
} from './types';

export type ObservabilityAlert = {
    id: string;
    title: string;
    detail: string;
};

const LOW_SUCCESS_RATE_THRESHOLD = 80;

const sortByRisk = <T extends { successRate: number; failedTurns: number }>(items: T[]) => (
    [...items].sort((left, right) => (
        left.successRate - right.successRate || right.failedTurns - left.failedTurns
    ))
);

const buildStageAlert = (stage: ObservabilityStageSummary): ObservabilityAlert => ({
    id: `stage-${stage.workflowId}-${stage.stageId}`,
    title: '阶段成功率偏低',
    detail: `${stage.workflowId} / ${stage.stageId} 成功率 ${stage.successRate}%，失败 ${stage.failedTurns}/${stage.turns} 轮。`,
});

const buildProviderAlert = (provider: ObservabilityProviderSummary): ObservabilityAlert => ({
    id: `provider-${provider.provider}`,
    title: '供应商成功率偏低',
    detail: `${provider.provider} 成功率 ${provider.successRate}%，失败 ${provider.failedTurns}/${provider.turns} 轮。`,
});

const formatTopProviderIssueCode = (issueCodes: Record<string, number>): string => {
    const [code, count] = Object.entries(issueCodes).sort((left, right) => (
        right[1] - left[1] || left[0].localeCompare(right[0])
    ))[0] || ['未知错误', 0];
    return `${code} x${count}`;
};

export const buildObservabilityAlerts = (summary: ObservabilitySummary): ObservabilityAlert[] => {
    const alerts: ObservabilityAlert[] = [];

    if (summary.totals.failedTurns > 0) {
        alerts.push({
            id: 'runtime-failures',
            title: '检测到失败运行',
            detail: `最近 ${summary.totals.turns} 轮中有 ${summary.totals.failedTurns} 轮失败，成功率 ${summary.totals.successRate}%。`,
        });
    }

    if (summary.totals.providerIssueCount > 0) {
        alerts.push({
            id: 'provider-issues',
            title: '模型/供应商异常集中',
            detail: `最近 ${summary.totals.turns} 轮中有 ${summary.totals.providerIssueCount} 轮与模型配置、供应商额度、鉴权或网络有关。最高频错误：${formatTopProviderIssueCode(summary.totals.providerIssueCodes)}。`,
        });
    }

    const lowestSuccessStage = sortByRisk(summary.byStage).find(stage => (
        stage.failedTurns > 0 && stage.successRate < LOW_SUCCESS_RATE_THRESHOLD
    ));
    if (lowestSuccessStage) {
        alerts.push(buildStageAlert(lowestSuccessStage));
    }

    const lowestSuccessProvider = sortByRisk(summary.byProvider).find(provider => (
        provider.failedTurns > 0 && provider.successRate < LOW_SUCCESS_RATE_THRESHOLD
    ));
    if (lowestSuccessProvider) {
        alerts.push(buildProviderAlert(lowestSuccessProvider));
    }

    return alerts;
};
