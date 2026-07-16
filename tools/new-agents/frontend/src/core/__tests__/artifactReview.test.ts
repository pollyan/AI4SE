import { describe, expect, it } from 'vitest';
import { buildArtifactQualityDiagnostics } from '../artifactDiagnostics';

describe('buildArtifactQualityDiagnostics', () => {
    it('reports missing required headings and required visuals for the current stage', () => {
        const result = buildArtifactQualityDiagnostics({
            workflowId: 'TEST_DESIGN',
            stageId: 'STRATEGY',
            artifactContent: '# 测试策略蓝图\n\n## 1. 策略摘要\n\n## 8. 阶段门禁\n\n- checked=true',
            visualDiagnostics: [],
        });

        expect(result.status).toBe('fail');
        expect(result.summary.fail).toBeGreaterThan(0);
        expect(result.items).toEqual(expect.arrayContaining([
            expect.objectContaining({
                category: 'heading',
                status: 'fail',
                title: '缺少必填标题',
            }),
            expect.objectContaining({
                category: 'mermaid',
                status: 'fail',
                title: '缺少 Mermaid 图表',
            }),
            expect.objectContaining({
                category: 'structured-visual',
                status: 'fail',
                title: '缺少结构化可视化',
            }),
        ]));
    });

    it('passes when the artifact satisfies the stage contract', () => {
        const result = buildArtifactQualityDiagnostics({
            workflowId: 'TEST_DESIGN',
            stageId: 'STRATEGY',
            artifactContent: [
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
                '## 文档信息',
                '风险 ID 测试点 ID 覆盖建议',
                '```mermaid',
                'quadrantChart',
                '```',
                '```mermaid',
                'block-beta',
                '```',
                '```ai4se-visual',
                '{"type":"risk-board","title":"风险板","columns":[]}',
                '```',
            ].join('\n'),
            visualDiagnostics: [],
        });

        expect(result.status).toBe('pass');
        expect(result.summary.fail).toBe(0);
        expect(result.summary.openQuestions).toBe(0);
    });

    it('adds current-stage runtime visual diagnostics as warnings', () => {
        const result = buildArtifactQualityDiagnostics({
            workflowId: 'TEST_DESIGN',
            stageId: 'CLARIFY',
            artifactContent: '# 需求分析文档\n\n## 8. 阶段门禁\n\n```mermaid\nflowchart TD\n```',
            visualDiagnostics: [{
                id: 'mermaid:CLARIFY:0',
                stageId: 'CLARIFY',
                kind: 'mermaid',
                title: 'Mermaid 图表渲染失败',
                message: 'syntax error',
                createdAt: 1,
            }],
        });

        expect(result.items).toEqual(expect.arrayContaining([
            expect.objectContaining({
                category: 'runtime-visual',
                status: 'warn',
                detail: 'syntax error',
            }),
        ]));
    });

    it('extracts blocking missing information from artifact sections', () => {
        const result = buildArtifactQualityDiagnostics({
            workflowId: 'TEST_DESIGN',
            stageId: 'CLARIFY',
            artifactContent: [
                '# 需求分析文档',
                '## 5. 待澄清问题',
                '- 阻断：支付失败重试次数缺失，必须由 PM 确认。',
                '- 待确认：优惠券叠加规则需要补充样例。',
                '## 8. 阶段门禁',
                '- checked=false：核心异常链路未确认，无法进入策略制定。',
            ].join('\n'),
            visualDiagnostics: [],
        });

        expect(result.summary.openQuestions).toBe(3);
        expect(result.openQuestions).toEqual(expect.arrayContaining([
            expect.objectContaining({
                blocking: true,
                title: '支付失败重试次数缺失',
                nextAction: '补充输入或手工修订后重新生成当前阶段产物。',
            }),
            expect.objectContaining({
                blocking: false,
                title: '优惠券叠加规则需要补充样例',
            }),
        ]));
    });
});
