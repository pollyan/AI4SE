import { describe, expect, it } from 'vitest';
import { parseStructuredVisual } from '../structuredVisuals';

describe('parseStructuredVisual', () => {
    it('parses a traceability matrix visual block', () => {
        const result = parseStructuredVisual(JSON.stringify({
            type: 'traceability-matrix',
            title: '需求-风险-用例追溯矩阵',
            columns: ['需求', '风险', '用例', '覆盖状态'],
            rows: [
                {
                    需求: 'REQ-1',
                    风险: 'RISK-1',
                    用例: 'TC-1',
                    覆盖状态: '已覆盖',
                },
            ],
        }));

        expect(result.valid).toBe(true);
        if (result.valid === false) throw new Error(result.message);
        expect(result.visual.title).toBe('需求-风险-用例追溯矩阵');
        expect(result.visual.columns).toEqual(['需求', '风险', '用例', '覆盖状态']);
        expect(result.visual.rows[0].cells).toEqual(['REQ-1', 'RISK-1', 'TC-1', '已覆盖']);
    });

    it('parses a score matrix visual block', () => {
        const result = parseStructuredVisual(JSON.stringify({
            type: 'score-matrix',
            title: '价值主张评分矩阵',
            columns: ['维度', '评分', '依据'],
            rows: [
                {
                    维度: '痛点强度',
                    评分: 4,
                    依据: '用户频繁反馈',
                },
            ],
        }));

        expect(result.valid).toBe(true);
        if (result.valid === false) throw new Error(result.message);
        expect(result.visual.type).toBe('score-matrix');
        expect(result.visual.title).toBe('价值主张评分矩阵');
        expect(result.visual.columns).toEqual(['维度', '评分', '依据']);
        expect(result.visual.rows[0].cells).toEqual(['痛点强度', '4', '用户频繁反馈']);
    });

    it.each([
        ['risk-board', '风险处置看板'],
        ['action-board', '改进行动看板'],
        ['journey-map', '用户旅程地图'],
        ['coverage-map', '交付覆盖地图'],
        ['priority-board', '问题优先级看板'],
        ['cause-map', '根因链路图'],
        ['mvp-map', 'MVP 功能地图'],
        ['roadmap', '产品路线图'],
    ])('parses %s visual blocks through the shared table shape', (type, title) => {
        const result = parseStructuredVisual(JSON.stringify({
            type,
            title,
            columns: ['对象', '状态', '依据'],
            rows: [
                {
                    对象: '关键项',
                    状态: '已识别',
                    依据: '来自阶段产出物',
                },
            ],
        }));

        expect(result.valid).toBe(true);
        if (result.valid === false) throw new Error(result.message);
        expect(result.visual.type).toBe(type);
        expect(result.visual.title).toBe(title);
        expect(result.visual.rows[0].cells).toEqual(['关键项', '已识别', '来自阶段产出物']);
    });

    it('returns an invalid result for malformed JSON', () => {
        const result = parseStructuredVisual('{ broken');

        expect(result).toEqual({
            valid: false,
            message: '结构化可视化必须是合法 JSON。',
        });
    });

    it('returns an invalid result for unsupported visual types', () => {
        const result = parseStructuredVisual(JSON.stringify({
            type: 'risk-heatmap',
            columns: ['风险'],
            rows: [{ 风险: 'RISK-1' }],
        }));

        expect(result).toEqual({
            valid: false,
            message: '不支持的结构化可视化类型：risk-heatmap。',
        });
    });
});
