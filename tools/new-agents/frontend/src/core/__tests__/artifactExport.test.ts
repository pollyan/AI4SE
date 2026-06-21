import { describe, expect, it } from 'vitest';
import { buildPlainTextPdf, toUtf16BeHex } from '../artifactExport';

describe('artifactExport', () => {
    it('builds a minimal PDF with cleaned markdown text', () => {
        const pdf = buildPlainTextPdf('# 测试报告\n\n这是 **重点** 结论。');

        expect(pdf.startsWith('%PDF-1.4')).toBe(true);
        expect(pdf).toContain(toUtf16BeHex('测试报告'));
        expect(pdf).toContain(toUtf16BeHex('这是 重点 结论。'));
        expect(pdf).not.toContain(toUtf16BeHex('# 测试报告'));
    });

    it('projects Mermaid and structured visuals into PDF text and drawing commands', () => {
        const pdf = buildPlainTextPdf([
            '# 视觉资产',
            '',
            '```mermaid',
            'timeline',
            '    title 登录事故时间线',
            '    section 发现',
            '      09点10分 : 监控触发告警',
            '```',
            '',
            '```ai4se-visual',
            JSON.stringify({
                type: 'risk-board',
                title: '核心风险矩阵',
                columns: ['风险', 'RPN'],
                rows: [
                    { 风险: '登录失败', RPN: '80' },
                ],
            }, null, 2),
            '```',
        ].join('\n'));

        expect(pdf).toContain(toUtf16BeHex('Mermaid 图表：timeline'));
        expect(pdf).toContain(toUtf16BeHex('登录事故时间线'));
        expect(pdf).toContain(toUtf16BeHex('09点10分：监控触发告警'));
        expect(pdf).toContain(toUtf16BeHex('结构化可视化：核心风险矩阵'));
        expect(pdf).toContain(toUtf16BeHex('登录失败    80'));
        expect(pdf).toContain('0.18 0.55 0.95 RG');
        expect(pdf).toContain('0.23 0.38 0.62 RG');
    });
});
