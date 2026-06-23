import { describe, expect, it } from 'vitest';
import {
    buildArtifactQualityDiagnostics,
    buildMissingInfoChecklist,
} from '../artifactQuality';

describe('buildArtifactQualityDiagnostics', () => {
    it('marks a complete TEST_DESIGN CLARIFY artifact as passed', () => {
        const result = buildArtifactQualityDiagnostics({
            workflow: 'TEST_DESIGN',
            stageId: 'CLARIFY',
            artifactContent: [
                '# 需求分析',
                '## 核心业务规则',
                '## 待澄清问题',
                '## 阶段门禁',
                '```mermaid',
                'flowchart TD',
                'A[输入] --> B[澄清]',
                '```',
                '```ai4se-visual',
                '{"type":"requirement-map","title":"需求地图"}',
                '```',
            ].join('\n'),
            visualDiagnostics: [],
        });

        expect(result?.status).toBe('pass');
        expect(result?.summary.failed).toBe(0);
        expect(result?.summary.warning).toBe(0);
        expect(result?.groups.some(group => group.id === 'contract')).toBe(true);
    });

    it('reports failed heading and visual checks for an incomplete artifact', () => {
        const result = buildArtifactQualityDiagnostics({
            workflow: 'TEST_DESIGN',
            stageId: 'CLARIFY',
            artifactContent: '# 需求分析\n\n只有摘要。',
            visualDiagnostics: [],
        });

        expect(result?.status).toBe('fail');
        expect(result?.summary.failed).toBeGreaterThanOrEqual(2);
        expect(result?.groups.flatMap(group => group.items).map(item => item.title)).toContain('必需标题');
        expect(result?.groups.flatMap(group => group.items).map(item => item.title)).toContain('必需可视化');
    });

    it('converts current-stage visual diagnostics into warnings', () => {
        const result = buildArtifactQualityDiagnostics({
            workflow: 'TEST_DESIGN',
            stageId: 'CLARIFY',
            artifactContent: [
                '# 需求分析',
                '## 核心业务规则',
                '## 待澄清问题',
                '## 阶段门禁',
                '```mermaid',
                'flowchart TD',
                'A --> B',
                '```',
                '```ai4se-visual',
                '{"type":"requirement-map","title":"需求地图"}',
                '```',
            ].join('\n'),
            visualDiagnostics: [{
                id: 'structured-visual:CLARIFY:0',
                stageId: 'CLARIFY',
                kind: 'structured-visual',
                title: '结构化可视化渲染失败',
                message: 'JSON 缺少 title 字段。',
                blockIndex: 0,
                createdAt: 1710000000000,
            }],
        });

        expect(result?.status).toBe('warning');
        expect(result?.summary.warning).toBe(1);
        expect(result?.groups.flatMap(group => group.items).some(item => item.message.includes('JSON 缺少 title 字段'))).toBe(true);
    });

    it('returns null for blank artifacts', () => {
        expect(buildArtifactQualityDiagnostics({
            workflow: 'TEST_DESIGN',
            stageId: 'CLARIFY',
            artifactContent: '   ',
            visualDiagnostics: [],
        })).toBeNull();
    });
});

describe('buildMissingInfoChecklist', () => {
    it('extracts blocking missing information from a markdown table section', () => {
        const result = buildMissingInfoChecklist([
            '# 需求分析',
            '',
            '## 待澄清问题',
            '',
            '| ID | 问题 | 阻断性 | 责任方 | 状态 | 下一步 |',
            '| --- | --- | --- | --- | --- | --- |',
            '| Q-001 | 登录失败重试次数未确认 | 阻断 | PM | 待确认 | 补充重试规则 |',
            '| Q-002 | 密码策略文案待确认 | 非阻断 | UX | 跟进中 | 更新提示文案 |',
        ].join('\n'));

        expect(result?.summary.total).toBe(2);
        expect(result?.summary.blocking).toBe(1);
        expect(result?.items[0]).toEqual(expect.objectContaining({
            id: 'missing-info-1',
            question: '登录失败重试次数未确认',
            blocking: true,
            owner: 'PM',
            status: '待确认',
            nextStep: '补充重试规则',
        }));
    });

    it('extracts missing information from a list section', () => {
        const result = buildMissingInfoChecklist([
            '# 测试策略',
            '',
            '## 缺失信息',
            '',
            '- [阻断] 需要确认支付回调超时窗口；责任方：架构师；状态：待确认；下一步：补充超时 SLA。',
        ].join('\n'));

        expect(result?.summary.total).toBe(1);
        expect(result?.summary.blocking).toBe(1);
        expect(result?.items[0].question).toBe('需要确认支付回调超时窗口');
        expect(result?.items[0].nextStep).toBe('补充超时 SLA');
    });

    it('returns null when the artifact has no missing information section', () => {
        expect(buildMissingInfoChecklist('# 需求分析\n\n## 阶段门禁\n\n已满足。')).toBeNull();
    });
});
