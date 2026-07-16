import { describe, expect, it } from 'vitest';
import { buildPlainTextPdf, toUtf16BeHex } from '../artifactExport';

describe('artifactExport', () => {
    it('decodes safe compact metadata entities into literal PDF text', () => {
        const pdf = buildPlainTextPdf([
            '# 测试报告',
            '',
            '## 文档信息',
            '文档元信息：值：&#95;draft&#95; &#126;&#126;old&#126;&#126; &#96;code&#96; &#92;path &#91;link&#93; &lt;script&gt; &#124; &amp;copy;',
        ].join('\n'));

        expect(pdf).toContain(toUtf16BeHex('文档元信息：值：_draft_ ~~old~~ `code` \\path [link] <script> | &copy;'));
        expect(pdf).not.toContain(toUtf16BeHex('&#95;draft&#95;'));
    });

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
            '',
            '```ai4se-visual',
            JSON.stringify({
                type: 'story-map',
                title: '用户故事地图',
                columns: ['Epic', 'Story', 'Sprint'],
                rows: [
                    { Epic: 'EPIC-001', Story: 'US-001 登录', Sprint: 'Sprint 1' },
                ],
            }, null, 2),
            '```',
        ].join('\n'));

        expect(pdf).toContain(toUtf16BeHex('Mermaid 图表：timeline'));
        expect(pdf).toContain(toUtf16BeHex('登录事故时间线'));
        expect(pdf).toContain(toUtf16BeHex('09点10分：监控触发告警'));
        expect(pdf).toContain(toUtf16BeHex('结构化可视化：核心风险矩阵'));
        expect(pdf).toContain(toUtf16BeHex('登录失败    80'));
        expect(pdf).toContain(toUtf16BeHex('结构化可视化：用户故事地图'));
        expect(pdf).toContain(toUtf16BeHex('EPIC-001    US-001 登录    Sprint 1'));
        expect(pdf).toContain('0.18 0.55 0.95 RG');
        expect(pdf).toContain('0.23 0.38 0.62 RG');
    });

    it('projects cause-map node-edge visuals into readable PDF text', () => {
        const pdf = buildPlainTextPdf([
            '# 根因链路',
            '',
            '```ai4se-visual',
            JSON.stringify({
                type: 'cause-map',
                title: '5-Why 根因链路图',
                nodes: [
                    {
                        id: 'Why-1',
                        label: 'Why-1',
                        title: '直接原因',
                        description: '发布前缺少关键路径回归门禁',
                    },
                    {
                        id: 'Why-2',
                        label: 'Why-2',
                        title: '深层原因',
                        description: '回归策略没有覆盖高风险链路',
                    },
                ],
                edges: [
                    { source: 'Why-1', target: 'Why-2', label: '继续追问' },
                ],
            }, null, 2),
            '```',
        ].join('\n'));

        expect(pdf).toContain(toUtf16BeHex('结构化可视化：5-Why 根因链路图'));
        expect(pdf).toContain(toUtf16BeHex('Why-1 直接原因：发布前缺少关键路径回归门禁'));
        expect(pdf).toContain(toUtf16BeHex('Why-1 -> Why-2：继续追问'));
        expect(pdf).not.toContain(toUtf16BeHex('"nodes"'));
    });

    it('projects flow-map node-edge visuals into readable PDF text', () => {
        const pdf = buildPlainTextPdf([
            '# Epic 流程图',
            '',
            '```ai4se-visual',
            JSON.stringify({
                type: 'flow-map',
                title: 'Epic 流程图',
                nodes: [
                    {
                        id: 'Goal',
                        label: 'Goal',
                        title: '产品目标',
                        description: '提升需求拆分质量',
                    },
                    {
                        id: 'EPIC-001',
                        label: 'EPIC-001',
                        title: '用户故事拆解',
                    },
                ],
                edges: [
                    { source: 'Goal', target: 'EPIC-001', label: '拆解为' },
                ],
            }, null, 2),
            '```',
        ].join('\n'));

        expect(pdf).toContain(toUtf16BeHex('结构化可视化：Epic 流程图'));
        expect(pdf).toContain(toUtf16BeHex('Goal 产品目标：提升需求拆分质量'));
        expect(pdf).toContain(toUtf16BeHex('Goal -> EPIC-001：拆解为'));
        expect(pdf).not.toContain(toUtf16BeHex('"nodes"'));
    });

    it('projects timeline-map visuals into readable PDF text', () => {
        const pdf = buildPlainTextPdf([
            '# 事件时间线',
            '',
            '```ai4se-visual',
            JSON.stringify({
                type: 'timeline-map',
                title: '支付故障事件时间线',
                events: [
                    {
                        id: 'TL-001',
                        time: '14:30',
                        title: '订单状态延迟告警触发',
                        description: '阶段：发现与响应；关联事实：FACT-001',
                        factIds: ['FACT-001'],
                    },
                ],
            }, null, 2),
            '```',
        ].join('\n'));

        expect(pdf).toContain(toUtf16BeHex('结构化可视化：支付故障事件时间线'));
        expect(pdf).toContain(toUtf16BeHex('14:30  订单状态延迟告警触发'));
        expect(pdf).toContain(toUtf16BeHex('阶段：发现与响应；关联事实：FACT-001'));
        expect(pdf).toContain(toUtf16BeHex('关联事实：FACT-001'));
        expect(pdf).not.toContain(toUtf16BeHex('"events"'));
    });
});
