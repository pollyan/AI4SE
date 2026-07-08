import type {
    TestAssetCollection,
    TestAssetQualityGate,
    TestAssetQualitySummary,
} from './types';

export const buildTestAssetQualitySummary = (
    collection: Pick<TestAssetCollection, 'assetIssues' | 'testPoints' | 'riskMatrix'>,
): TestAssetQualitySummary => {
    const pendingIssueCount = collection.assetIssues.filter(issue => issue.status === 'pending').length;
    const confirmedIssueCount = collection.assetIssues.filter(issue => issue.status === 'confirmed').length;
    const ignoredIssueCount = collection.assetIssues.filter(issue => issue.status === 'ignored').length;
    const uncoveredTestPointCount = collection.testPoints.filter(testPoint => testPoint.status === '未覆盖').length;
    const partialTestPointCount = collection.testPoints.filter(testPoint => testPoint.status === '部分覆盖').length;
    const openRiskCount = collection.riskMatrix.filter(risk => risk.status === 'open').length;
    const mitigatingRiskCount = collection.riskMatrix.filter(risk => risk.status === 'mitigating').length;
    const acceptedRiskCount = collection.riskMatrix.filter(risk => risk.status === 'accepted').length;
    const closedRiskCount = collection.riskMatrix.filter(risk => risk.status === 'closed').length;

    const gates: TestAssetQualityGate[] = [
        {
            id: 'asset-issues',
            status: pendingIssueCount > 0 ? 'fail' : confirmedIssueCount > 0 ? 'warn' : 'pass',
            title: '资产问题',
            detail: `${pendingIssueCount} 个待处理，${confirmedIssueCount} 个已确认，${ignoredIssueCount} 个已忽略`,
        },
        {
            id: 'test-point-coverage',
            status: uncoveredTestPointCount > 0 ? 'fail' : partialTestPointCount > 0 ? 'warn' : 'pass',
            title: '测试点覆盖',
            detail: `${uncoveredTestPointCount} 个未覆盖，${partialTestPointCount} 个部分覆盖`,
        },
        {
            id: 'risk-lifecycle',
            status: openRiskCount > 0 || mitigatingRiskCount > 0 ? 'warn' : 'pass',
            title: '风险处置',
            detail: `${openRiskCount} 个待处置，${mitigatingRiskCount} 个缓解中，${acceptedRiskCount} 个已接受，${closedRiskCount} 个已关闭`,
        },
    ];
    const hasFailure = gates.some(gate => gate.status === 'fail');
    const hasWarning = gates.some(gate => gate.status === 'warn');
    const status = hasFailure ? 'blocked' : hasWarning ? 'attention' : 'ready';
    const label = status === 'blocked' ? '存在阻断' : status === 'attention' ? '需要关注' : '可交付';

    return {
        status,
        label,
        pendingIssueCount,
        confirmedIssueCount,
        ignoredIssueCount,
        uncoveredTestPointCount,
        partialTestPointCount,
        openRiskCount,
        mitigatingRiskCount,
        acceptedRiskCount,
        closedRiskCount,
        gates,
    };
};

export const withTestAssetQualitySummary = (
    collection: TestAssetCollection,
): TestAssetCollection => ({
    ...collection,
    qualitySummary: buildTestAssetQualitySummary(collection),
});
