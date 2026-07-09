import { describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { StructuredVisual } from '../StructuredVisual';

describe('StructuredVisual', () => {
    it('renders traceability matrix JSON as an accessible table', () => {
        render(
            <StructuredVisual
                source={JSON.stringify({
                    type: 'traceability-matrix',
                    title: '需求-风险-用例追溯矩阵',
                    columns: ['需求', '风险', '用例'],
                    rows: [
                        {
                            需求: 'REQ-1',
                            风险: 'RISK-1',
                            用例: 'TC-1',
                        },
                    ],
                })}
            />
        );

        expect(screen.getByRole('table', { name: '需求-风险-用例追溯矩阵' })).toBeTruthy();
        expect(screen.getByText('REQ-1')).toBeTruthy();
        expect(screen.getByText('RISK-1')).toBeTruthy();
        expect(screen.getByText('TC-1')).toBeTruthy();
    });

    it('renders score matrix JSON through the shared visual table', () => {
        render(
            <StructuredVisual
                source={JSON.stringify({
                    type: 'score-matrix',
                    title: '需求质量评分矩阵',
                    columns: ['维度', '评分', '依据'],
                    rows: [
                        {
                            维度: '可测试性',
                            评分: 3,
                            依据: '验收标准不完整',
                        },
                    ],
                })}
            />
        );

        expect(screen.getByRole('table', { name: '需求质量评分矩阵' })).toBeTruthy();
        expect(screen.getByText('ai4se-visual · score-matrix')).toBeTruthy();
        expect(screen.getByText('可测试性')).toBeTruthy();
        expect(screen.getByText('3')).toBeTruthy();
        expect(screen.getByText('验收标准不完整')).toBeTruthy();
    });

    it('renders action board JSON with a professional default title', () => {
        render(
            <StructuredVisual
                source={JSON.stringify({
                    type: 'action-board',
                    columns: ['行动', '状态', '验证方式'],
                    rows: [
                        {
                            行动: '补充发布门禁',
                            状态: '待开始',
                            验证方式: 'CI 检查通过',
                        },
                    ],
                })}
            />
        );

        expect(screen.getByRole('table', { name: '改进行动看板' })).toBeTruthy();
        expect(screen.getByText('ai4se-visual · action-board')).toBeTruthy();
        expect(screen.getByText('补充发布门禁')).toBeTruthy();
        expect(screen.getByText('CI 检查通过')).toBeTruthy();
    });

    it('renders roadmap JSON with a professional default title', () => {
        render(
            <StructuredVisual
                source={JSON.stringify({
                    type: 'roadmap',
                    columns: ['版本', '核心功能', '目标'],
                    rows: [
                        {
                            版本: 'v1.0 MVP',
                            核心功能: '核心闭环',
                            目标: '验证主价值',
                        },
                    ],
                })}
            />
        );

        expect(screen.getByRole('table', { name: '产品路线图' })).toBeTruthy();
        expect(screen.getByText('ai4se-visual · roadmap')).toBeTruthy();
        expect(screen.getByText('v1.0 MVP')).toBeTruthy();
        expect(screen.getByText('验证主价值')).toBeTruthy();
    });

    it('renders story-map JSON with a professional default title', () => {
        render(
            <StructuredVisual
                source={JSON.stringify({
                    type: 'story-map',
                    columns: ['Epic', 'Story', '优先级', 'Sprint'],
                    rows: [
                        {
                            Epic: 'EPIC-001 账号体系',
                            Story: 'US-001 用户登录',
                            优先级: 'P0',
                            Sprint: 'Sprint 1',
                        },
                    ],
                })}
            />
        );

        expect(screen.getByRole('table', { name: '用户故事地图' })).toBeTruthy();
        expect(screen.getByText('ai4se-visual · story-map')).toBeTruthy();
        expect(screen.getByText('EPIC-001 账号体系')).toBeTruthy();
        expect(screen.getByText('US-001 用户登录')).toBeTruthy();
    });

    it('renders cause-map node-edge JSON as a graph view instead of a table', () => {
        render(
            <StructuredVisual
                source={JSON.stringify({
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
                })}
            />
        );

        expect(screen.queryByRole('table')).toBeNull();
        expect(screen.getByRole('group', { name: '5-Why 根因链路图' })).toBeTruthy();
        expect(screen.getByText('Why-1')).toBeTruthy();
        expect(screen.getByText('发布前缺少关键路径回归门禁')).toBeTruthy();
        expect(screen.getByText('继续追问')).toBeTruthy();
        expect(screen.getByText('Why-1 -> Why-2')).toBeTruthy();
    });

    it('renders an explicit error panel for invalid visual JSON', () => {
        render(<StructuredVisual source="{ broken" />);

        expect(screen.getByText('结构化可视化格式错误')).toBeTruthy();
        expect(screen.getByText('结构化可视化必须是合法 JSON。')).toBeTruthy();
    });

    it('reports invalid visual JSON through the validation error callback', async () => {
        const onValidationError = vi.fn();

        render(<StructuredVisual source="{ broken" onValidationError={onValidationError} />);

        await waitFor(() => {
            expect(onValidationError).toHaveBeenCalledWith('结构化可视化必须是合法 JSON。');
        });
    });

    it('reports valid visual JSON through the validation success callback', async () => {
        const onValidationSuccess = vi.fn();

        render(
            <StructuredVisual
                source={JSON.stringify({
                    type: 'score-matrix',
                    columns: ['维度', '评分'],
                    rows: [{ 维度: '价值', 评分: 4 }],
                })}
                onValidationSuccess={onValidationSuccess}
            />
        );

        await waitFor(() => {
            expect(onValidationSuccess).toHaveBeenCalledOnce();
        });
    });
});
