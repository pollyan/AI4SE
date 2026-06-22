import { describe, expect, it } from 'vitest';
import { buildArtifactQualitySummary } from '../artifactQuality';
import type { ArtifactVisualDiagnostic, WorkflowStage } from '../types';

const clarifyStage: WorkflowStage = {
    id: 'CLARIFY',
    name: '需求澄清',
    description: '需求澄清',
    artifactContract: {
        requiredHeadings: [
            '# 需求分析文档',
            '## 8. 阶段门禁',
            '事实 ID',
            '状态',
        ],
    },
    visualContract: {
        requiredMermaidDiagrams: ['flowchart'],
        requiredStructuredVisuals: ['risk-board'],
    },
};

describe('buildArtifactQualitySummary', () => {
    it('reports missing headings, fields, visuals, and stage gate decisions', () => {
        const summary = buildArtifactQualitySummary({
            stage: clarifyStage,
            content: '# 草稿\n\n## 8. 阶段门禁\n\n等待确认',
            visualDiagnostics: [],
        });

        expect(summary.status).toBe('fail');
        expect(summary.failedCount).toBe(5);
        expect(summary.warningCount).toBe(1);
        expect(summary.items).toEqual(expect.arrayContaining([
            expect.objectContaining({
                category: 'heading',
                status: 'fail',
                title: '缺少标题：# 需求分析文档',
            }),
            expect.objectContaining({
                category: 'field',
                status: 'fail',
                title: '缺少专业字段：事实 ID',
            }),
            expect.objectContaining({
                category: 'field',
                status: 'fail',
                title: '缺少专业字段：状态',
            }),
            expect.objectContaining({
                category: 'visual',
                status: 'fail',
                title: '缺少 Mermaid 图：flowchart',
            }),
            expect.objectContaining({
                category: 'visual',
                status: 'fail',
                title: '缺少结构化可视化：risk-board',
            }),
            expect.objectContaining({
                category: 'stage-gate',
                status: 'warning',
                title: '阶段门禁缺少决策项',
            }),
        ]));
    });

    it('passes when required headings, fields, visuals, and stage gate decisions exist', () => {
        const summary = buildArtifactQualitySummary({
            stage: clarifyStage,
            content: [
                '# 需求分析文档',
                '',
                '| 事实 ID | 状态 |',
                '| --- | --- |',
                '| F-1 | 已确认 |',
                '',
                '```mermaid',
                'flowchart TD',
                'A --> B',
                '```',
                '',
                '```ai4se-visual',
                '{"type":"risk-board","title":"风险看板","columns":["风险"],"rows":[{"风险":"R1"}]}',
                '```',
                '',
                '## 8. 阶段门禁',
                '- [x] 关键事实已确认',
            ].join('\n'),
            visualDiagnostics: [],
        });

        expect(summary.status).toBe('pass');
        expect(summary.failedCount).toBe(0);
        expect(summary.warningCount).toBe(0);
    });

    it('includes current-stage visual diagnostics as actionable failures', () => {
        const visualDiagnostic: ArtifactVisualDiagnostic = {
            id: 'structured-visual:CLARIFY:0',
            stageId: 'CLARIFY',
            kind: 'structured-visual',
            title: '结构化可视化格式错误',
            message: '结构化可视化必须是合法 JSON。',
            blockIndex: 0,
            createdAt: 1710000000000,
        };

        const summary = buildArtifactQualitySummary({
            stage: clarifyStage,
            content: '',
            visualDiagnostics: [visualDiagnostic],
        });

        expect(summary.items).toContainEqual(expect.objectContaining({
            category: 'visual-diagnostic',
            status: 'fail',
            actionDiagnosticId: 'structured-visual:CLARIFY:0',
        }));
    });

    it('builds missing information items with blocking state and next actions', () => {
        const summary = buildArtifactQualitySummary({
            stage: clarifyStage,
            content: '# 草稿\n\n## 8. 阶段门禁\n\n等待确认',
            visualDiagnostics: [],
        });

        expect(summary.missingInfoItems).toEqual(expect.arrayContaining([
            expect.objectContaining({
                title: '缺少标题：# 需求分析文档',
                blocking: true,
                nextAction: expect.stringContaining('补充'),
            }),
            expect.objectContaining({
                title: '缺少专业字段：事实 ID',
                blocking: true,
                nextAction: expect.stringContaining('补充'),
            }),
            expect.objectContaining({
                title: '缺少 Mermaid 图：flowchart',
                blocking: true,
                nextAction: expect.stringContaining('重新生成'),
            }),
            expect.objectContaining({
                title: '阶段门禁缺少决策项',
                blocking: false,
                nextAction: expect.stringContaining('确认'),
            }),
        ]));
    });

    it('does not report missing information before the stage has artifact content', () => {
        const summary = buildArtifactQualitySummary({
            stage: clarifyStage,
            content: '',
            visualDiagnostics: [],
        });

        expect(summary.status).toBe('empty');
        expect(summary.missingInfoItems).toEqual([]);
    });
});
