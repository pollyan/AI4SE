import { describe, expect, it } from 'vitest';
import { buildWorkflowQualitySummary } from '../workflowQuality';

const STRATEGY_READY_ARTIFACT = [
    '# 测试策略蓝图',
    '## 1. 策略摘要',
    '## 2. 质量目标',
    '## 3. 风险识别与 FMEA',
    '### 3.1 风险矩阵',
    '### 3.2 风险明细',
    '## 4. 测试技术选型',
    '## 5. 测试分层策略',
    '### 5.1 测试金字塔',
    '### 5.2 分层明细',
    '## 6. 测试点拓扑',
    '## 7. 资源与取舍',
    '## 8. 阶段门禁',
    '风险 ID 测试点 ID 覆盖建议',
    '- checked=true',
    '```mermaid',
    'quadrantChart',
    '```',
    '```mermaid',
    'block-beta',
    '```',
    '```ai4se-visual',
    '{"type":"risk-board","title":"风险板","columns":[]}',
    '```',
].join('\n');

const DELIVERY_READY_ARTIFACT = [
    '# 测试设计文档',
    '## 1. 文档信息',
    '## 2. 执行摘要',
    '## 3. 需求分析摘要',
    '## 4. 测试策略摘要',
    '## 5. 测试用例摘要',
    '## 6. 覆盖地图',
    '## 7. 开放风险',
    '## 8. 交付验收清单',
    '## 9. 签署确认',
    '## 10. 变更记录',
    '## 阶段门禁',
    '- checked=true',
    '```ai4se-visual',
    '{"type":"coverage-map","title":"覆盖地图","items":[]}',
    '```',
].join('\n');

describe('buildWorkflowQualitySummary', () => {
    it('aggregates stage scores, global pending queue, and next focus stage', () => {
        const summary = buildWorkflowQualitySummary({
            workflowId: 'TEST_DESIGN',
            currentStageId: 'STRATEGY',
            currentArtifactContent: STRATEGY_READY_ARTIFACT,
            stageArtifacts: {
                CLARIFY: '# 需求分析文档\n\n## 8. 阶段门禁\n\n- checked=true',
                STRATEGY: STRATEGY_READY_ARTIFACT,
                DELIVERY: DELIVERY_READY_ARTIFACT,
            },
            visualDiagnostics: [
                {
                    id: 'structured:DELIVERY:0',
                    stageId: 'DELIVERY',
                    kind: 'structured-visual',
                    title: '结构化可视化渲染失败',
                    message: 'coverage-map schema mismatch',
                    createdAt: 1,
                },
            ],
        });

        const clarify = summary.stages.find(stage => stage.stageId === 'CLARIFY');
        const strategy = summary.stages.find(stage => stage.stageId === 'STRATEGY');
        const cases = summary.stages.find(stage => stage.stageId === 'CASES');
        const delivery = summary.stages.find(stage => stage.stageId === 'DELIVERY');

        expect(strategy).toMatchObject({
            stageIndex: 1,
            stageName: '策略制定',
            status: 'ready',
            label: '可推进',
            score: 100,
            isCurrentStage: true,
        });
        expect(clarify).toMatchObject({
            stageIndex: 0,
            stageName: '需求澄清',
            status: 'blocked',
            label: '需处理',
        });
        expect(clarify?.pendingItems).toEqual(expect.arrayContaining([
            expect.objectContaining({
                severity: 'blocker',
                title: '缺少必填标题',
            }),
            expect.objectContaining({
                severity: 'blocker',
                title: '缺少 Mermaid 图表',
            }),
        ]));
        expect(cases).toMatchObject({
            stageIndex: 2,
            stageName: '用例编写',
            status: 'not-started',
            label: '待生成',
            score: 0,
        });
        expect(cases?.pendingItems).toEqual([
            expect.objectContaining({
                severity: 'not-started',
                title: '待生成产物',
                nextAction: '先生成该阶段产物。',
            }),
        ]);
        expect(delivery).toMatchObject({
            stageIndex: 3,
            stageName: '文档交付',
            status: 'attention',
            label: '需关注',
        });
        expect(delivery?.pendingItems).toEqual(expect.arrayContaining([
            expect.objectContaining({
                severity: 'attention',
                title: '运行时可视化警告',
                detail: 'coverage-map schema mismatch',
            }),
        ]));

        expect(summary.totals).toEqual({
            stages: 4,
            ready: 1,
            attention: 1,
            blocked: 1,
            notStarted: 1,
            pendingItems: summary.pendingQueue.length,
        });
        expect(summary.pendingQueue.map(item => item.stageId)).toEqual([
            'CLARIFY',
            'CLARIFY',
            'DELIVERY',
            'CASES',
        ]);
        expect(summary.pendingQueue[0]).toMatchObject({
            severity: 'blocker',
            stageName: '需求澄清',
        });
        expect(summary.nextFocusStageIndex).toBe(0);
        expect(summary.averageScore).toBeGreaterThan(0);
        expect(summary.averageScore).toBeLessThan(100);
    });

    it('recomputes quality from restored stage artifacts without persisted quality fields', () => {
        const restoredSummary = buildWorkflowQualitySummary({
            workflowId: 'TEST_DESIGN',
            currentStageId: 'STRATEGY',
            currentArtifactContent: STRATEGY_READY_ARTIFACT,
            stageArtifacts: {
                STRATEGY: STRATEGY_READY_ARTIFACT,
            },
            visualDiagnostics: [],
        });

        expect(restoredSummary.stages.find(stage => stage.stageId === 'STRATEGY')).toMatchObject({
            status: 'ready',
            score: 100,
        });
        expect(restoredSummary.stages.find(stage => stage.stageId === 'CLARIFY')).toMatchObject({
            status: 'not-started',
            score: 0,
        });
        expect(restoredSummary.nextFocusStageIndex).toBe(0);
        expect(restoredSummary.pendingQueue).toEqual(expect.arrayContaining([
            expect.objectContaining({
                stageId: 'CLARIFY',
                severity: 'not-started',
            }),
        ]));
    });
});
