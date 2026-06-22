import type { TestAssetCollection } from './types';

export type TestAssetQualityStatus = 'blocked' | 'attention' | 'ready';

export type TestAssetQualitySummary = {
    status: TestAssetQualityStatus;
    label: string;
    summary: string;
    blockingItems: string[];
    attentionItems: string[];
    nextAction: string;
};

const countLabel = (count: number, label: string): string | null => (
    count > 0 ? `${count} 个${label}` : null
);

const compactItems = (items: Array<string | null>): string[] => (
    items.filter((item): item is string => Boolean(item))
);

export function deriveTestAssetQualityStatus(
    collection: TestAssetCollection,
): TestAssetQualitySummary {
    const pendingIssues = collection.assetIssues.filter(issue => issue.status === 'pending');
    const uncoveredPoints = collection.testPoints.filter(point => point.status === '未覆盖');
    const unownedOpenRisks = collection.riskMatrix.filter(
        risk => risk.status === 'open' && risk.owner.trim() === ''
    );
    const partiallyCoveredPoints = collection.testPoints.filter(
        point => point.status === '部分覆盖'
    );
    const mitigatingRisks = collection.riskMatrix.filter(risk => risk.status === 'mitigating');
    const acceptedRisks = collection.riskMatrix.filter(risk => risk.status === 'accepted');

    const blockingItems = compactItems([
        countLabel(pendingIssues.length, '资产问题待处理'),
        countLabel(uncoveredPoints.length, '测试点未覆盖'),
        countLabel(unownedOpenRisks.length, '开放风险未分配责任人'),
    ]);
    const attentionItems = compactItems([
        countLabel(partiallyCoveredPoints.length, '测试点部分覆盖'),
        countLabel(mitigatingRisks.length, '风险缓解中'),
        countLabel(acceptedRisks.length, '风险已接受'),
    ]);

    if (blockingItems.length > 0) {
        return {
            status: 'blocked',
            label: '需修复',
            summary: `仍有 ${blockingItems.length} 类阻断项影响测试资产交付。`,
            blockingItems,
            attentionItems,
            nextAction: '先处理阻断项：确认或忽略资产问题、补齐未覆盖测试点，并为开放风险分配责任人。',
        };
    }

    if (attentionItems.length > 0) {
        return {
            status: 'attention',
            label: '需关注',
            summary: `阻断项已清空，仍有 ${attentionItems.length} 类关注项需要复核。`,
            blockingItems,
            attentionItems,
            nextAction: '复核关注项：确认部分覆盖测试点、缓解中风险和已接受风险是否满足交付条件。',
        };
    }

    return {
        status: 'ready',
        label: '可交付',
        summary: '资产问题、测试点覆盖和风险处置均满足当前交付条件。',
        blockingItems,
        attentionItems,
        nextAction: '可以进入交付评审或 intent-tester 导入执行。',
    };
}
