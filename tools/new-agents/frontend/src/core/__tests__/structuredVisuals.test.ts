import { describe, expect, it } from 'vitest';
import {
    extractStructuredVisualBlocks,
    parseStructuredVisual,
    validateStructuredVisualBlocks,
} from '../structuredVisuals';
import { WORKFLOWS } from '../workflows';
import { ROOT_CAUSE_TEMPLATE } from '../prompts/incident_review/root_cause';
import { TIMELINE_TEMPLATE } from '../prompts/incident_review/timeline';

describe('parseStructuredVisual', () => {
    it('extracts fenced ai4se-visual blocks from markdown', () => {
        const blocks = extractStructuredVisualBlocks([
            '# 文档',
            '```ai4se-visual',
            '{"type":"score-matrix","columns":["维度"],"rows":[{"维度":"价值"}]}',
            '```',
            '```json',
            '{"type":"not-visual"}',
            '```',
            '```ai4se-visual',
            '{"type":"roadmap","columns":["版本"],"rows":[{"版本":"MVP"}]}',
            '```',
        ].join('\n'));

        expect(blocks).toHaveLength(2);
        expect(blocks[0]).toContain('"score-matrix"');
        expect(blocks[1]).toContain('"roadmap"');
    });

    it('validates all fenced ai4se-visual blocks in markdown', () => {
        expect(() => validateStructuredVisualBlocks([
            '```ai4se-visual',
            '{"type":"score-matrix","columns":["维度"],"rows":[{"维度":"价值"}]}',
            '```',
            '',
            '```ai4se-visual',
            '{"type":"cause-map","nodes":[{"id":"Why-1","label":"Why-1","title":"直接原因"}],"edges":[]}',
            '```',
        ].join('\n'))).not.toThrow();
    });

    it('rejects malformed ai4se-visual blocks before artifact write', () => {
        expect(() => validateStructuredVisualBlocks([
            '```ai4se-visual',
            '{ broken',
            '```',
        ].join('\n'))).toThrow(
            'Artifact structured visual validation failed: 结构化可视化必须是合法 JSON。'
        );
    });

    it('rejects cause-map blocks with missing edge targets before artifact write', () => {
        expect(() => validateStructuredVisualBlocks([
            '```ai4se-visual',
            '{"type":"cause-map","nodes":[{"id":"Why-1","label":"Why-1","title":"直接原因"}],"edges":[{"source":"Why-1","target":"Why-404"}]}',
            '```',
        ].join('\n'))).toThrow(
            'Artifact structured visual validation failed: cause-map edge 引用了不存在的节点：Why-1 -> Why-404。'
        );
    });

    it('rejects matrix visual rows that are arrays instead of column keyed objects', () => {
        const result = parseStructuredVisual(JSON.stringify({
            type: 'risk-board',
            columns: ['风险', '等级', '策略'],
            rows: [
                ['登录绕过', 'P0', '安全专项'],
            ],
        }));

        expect(result).toEqual({
            valid: false,
            message: 'risk-board 必须包含 rows 对象数组。',
        });
    });

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
        expect(result.visual.kind).toBe('matrix');
        if (result.visual.kind !== 'matrix') throw new Error('expected matrix visual');
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
        expect(result.visual.kind).toBe('matrix');
        if (result.visual.kind !== 'matrix') throw new Error('expected matrix visual');
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
        ['mvp-map', 'MVP 功能地图'],
        ['roadmap', '产品路线图'],
        ['story-map', '用户故事地图'],
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
        expect(result.visual.kind).toBe('matrix');
        if (result.visual.kind !== 'matrix') throw new Error('expected matrix visual');
        expect(result.visual.type).toBe(type);
        expect(result.visual.title).toBe(title);
        expect(result.visual.rows[0].cells).toEqual(['关键项', '已识别', '来自阶段产出物']);
    });

    it('parses timeline-map visual blocks as timeline events', () => {
        const result = parseStructuredVisual(JSON.stringify({
            type: 'timeline-map',
            title: '事件时间线',
            events: [
                {
                    id: 'TL-001',
                    time: '14:30',
                    title: '订单状态延迟告警触发',
                    description: '阶段：发现与响应；关联事实：FACT-001',
                    factIds: ['FACT-001'],
                },
            ],
        }));

        expect(result.valid).toBe(true);
        if (result.valid === false) throw new Error(result.message);
        expect(result.visual.kind).toBe('timeline');
        if (result.visual.kind !== 'timeline') throw new Error('expected timeline visual');
        expect(result.visual.type).toBe('timeline-map');
        expect(result.visual.events[0]).toEqual({
            id: 'TL-001',
            time: '14:30',
            title: '订单状态延迟告警触发',
            description: '阶段：发现与响应；关联事实：FACT-001',
            factIds: ['FACT-001'],
        });
    });

    it('rejects timeline-map duplicate event ids', () => {
        const result = parseStructuredVisual(JSON.stringify({
            type: 'timeline-map',
            events: [
                {
                    id: 'TL-001',
                    time: '14:30',
                    title: '告警触发',
                    description: '阶段：发现',
                    factIds: ['FACT-001'],
                },
                {
                    id: 'TL-001',
                    time: '14:35',
                    title: '值班确认',
                    description: '阶段：响应',
                    factIds: ['FACT-002'],
                },
            ],
        }));

        expect(result).toEqual({
            valid: false,
            message: 'timeline-map 包含重复 event id：TL-001。',
        });
    });

    it('rejects timeline-map events without factIds', () => {
        const result = parseStructuredVisual(JSON.stringify({
            type: 'timeline-map',
            events: [
                {
                    id: 'TL-001',
                    time: '14:30',
                    title: '告警触发',
                    description: '阶段：发现',
                    factIds: [],
                },
            ],
        }));

        expect(result).toEqual({
            valid: false,
            message: 'timeline-map event 必须包含非空 factIds 字符串数组。',
        });
    });

    it('supports every structured visual type required by workflow manifests', () => {
        const requiredTypes = new Set<string>();
        Object.values(WORKFLOWS).forEach((workflow) => {
            workflow.stages.forEach((stage) => {
                (stage.visualContract?.requiredStructuredVisuals ?? []).forEach((type) => {
                    requiredTypes.add(type);
                });
            });
        });

        expect(requiredTypes).toContain('story-map');
        requiredTypes.forEach((type) => {
            const sample = (() => {
                if (type === 'cause-map') {
                    return {
                        type,
                        nodes: [{ id: 'N-1', label: 'N-1', title: '节点' }],
                        edges: [],
                    };
                }
                if (type === 'timeline-map') {
                    return {
                        type,
                        events: [
                            {
                                id: 'TL-001',
                                time: '14:30',
                                title: '告警触发',
                                description: '阶段：发现',
                                factIds: ['FACT-001'],
                            },
                        ],
                    };
                }
                return {
                    type,
                    columns: ['对象', '状态'],
                    rows: [{ 对象: '关键项', 状态: '已识别' }],
                };
            })();
            const result = parseStructuredVisual(JSON.stringify(sample));

            expect(result, `${type} should be supported by frontend structured visual parser`).toMatchObject({
                valid: true,
            });
        });
    });

    it('parses cause-map visual blocks as node-edge graphs', () => {
        const result = parseStructuredVisual(JSON.stringify({
            type: 'cause-map',
            title: '5-Why 根因链路图',
            nodes: [
                {
                    id: 'Why-1',
                    label: 'Why-1',
                    title: '直接原因',
                    description: '发布前缺少关键路径回归门禁',
                    category: '流程',
                    evidence: '发布记录与测试记录',
                    confidence: '高',
                    status: '已确认',
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
        }));

        expect(result.valid).toBe(true);
        if (result.valid === false) throw new Error(result.message);
        expect(result.visual.kind).toBe('node-edge');
        if (result.visual.kind !== 'node-edge') throw new Error('expected node-edge visual');
        expect(result.visual.nodes.map(node => node.id)).toEqual(['Why-1', 'Why-2']);
        expect(result.visual.edges[0]).toEqual({
            source: 'Why-1',
            target: 'Why-2',
            label: '继续追问',
        });
    });

    it('rejects cause-map edges that reference missing nodes', () => {
        const result = parseStructuredVisual(JSON.stringify({
            type: 'cause-map',
            nodes: [
                { id: 'Why-1', label: 'Why-1', title: '直接原因' },
            ],
            edges: [
                { source: 'Why-1', target: 'Why-404', label: '继续追问' },
            ],
        }));

        expect(result).toEqual({
            valid: false,
            message: 'cause-map edge 引用了不存在的节点：Why-1 -> Why-404。',
        });
    });

    it('keeps ROOT_CAUSE cause-map template on the node-edge protocol', () => {
        expect(ROOT_CAUSE_TEMPLATE).toContain('"type": "cause-map"');
        expect(ROOT_CAUSE_TEMPLATE).toContain('"nodes"');
        expect(ROOT_CAUSE_TEMPLATE).toContain('"edges"');
        expect(ROOT_CAUSE_TEMPLATE).not.toContain('"columns": ["层级", "问题", "回答"');
    });

    it('keeps TIMELINE template on the timeline-map protocol', () => {
        expect(TIMELINE_TEMPLATE).toContain('"type": "timeline-map"');
        expect(TIMELINE_TEMPLATE).toContain('"events"');
        expect(TIMELINE_TEMPLATE).toContain('"factIds"');
        expect(TIMELINE_TEMPLATE).not.toContain('```mermaid');
        expect(TIMELINE_TEMPLATE).not.toContain('timeline\n');
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
