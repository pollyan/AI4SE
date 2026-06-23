import { describe, expect, it } from 'vitest';
import { buildArtifactQualityDiagnostics } from '../artifactQuality';

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
