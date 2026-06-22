import { describe, it, expect, beforeEach, vi } from 'vitest';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { ArtifactPane } from '../ArtifactPane';
import { useStore } from '../../store';
import { ArtifactConflictError, updateRunArtifact, updateRunArtifactCollaboration } from '../../services/runSnapshotService';

vi.mock('../../services/runSnapshotService', async (importOriginal) => {
    const actual = await importOriginal<typeof import('../../services/runSnapshotService')>();
    return {
        ...actual,
        updateRunArtifact: vi.fn(),
        updateRunArtifactCollaboration: vi.fn(),
    };
});

// Mock Mermaid component
vi.mock('../Mermaid', () => ({
    Mermaid: ({
        chart,
        onRetry,
    }: {
        chart: string;
        onRetry?: () => Promise<boolean>;
    }) => (
        <div data-testid="mermaid">
            {chart}
            {onRetry && <button type="button">重新生成图表</button>}
        </div>
    ),
}));

// Mock mermaidRetryService
vi.mock('../../services/mermaidRetryService', () => ({
    retryMermaidGeneration: vi.fn(),
}));

// Mock lucide-react
vi.mock('lucide-react', () => {
    const icons = ['Download', 'Code', 'Eye', 'History', 'X', 'AlertTriangle', 'GitCompare', 'Edit3', 'Save', 'MessageSquare', 'Trash2', 'Lock', 'Unlock', 'MoreHorizontal'];
    const mod: Record<string, React.FC> = {};
    icons.forEach(name => {
        mod[name] = () => <span>{name}</span>;
    });
    return mod;
});

describe('ArtifactPane Component', () => {
    const originalCreateElement = document.createElement.bind(document);
    const toUtf16BeHex = (value: string): string => (
        `FEFF${Array.from(value).map((character) => {
            const codePoint = character.codePointAt(0) ?? 0x20;
            if (codePoint > 0xffff) {
                const adjusted = codePoint - 0x10000;
                const high = 0xd800 + (adjusted >> 10);
                const low = 0xdc00 + (adjusted & 0x3ff);
                return `${high.toString(16).padStart(4, '0')}${low.toString(16).padStart(4, '0')}`;
            }
            return codePoint.toString(16).padStart(4, '0');
        }).join('')}`.toUpperCase()
    );

    beforeEach(() => {
        vi.restoreAllMocks();
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 0,
            artifactContent: '',
            artifactHistory: [],
            stageArtifacts: {},
            artifactTruncated: false,
            artifactVisualDiagnostics: [],
            currentRunId: null,
            isGenerating: false,
        });
    });

    const openArtifactToolbarMenu = () => {
        fireEvent.click(screen.getByRole('button', { name: '更多产物操作' }));
    };

    const clickArtifactToolbarMenuItem = (name: string) => {
        openArtifactToolbarMenu();
        fireEvent.click(screen.getByRole('menuitem', { name }));
    };

    const downloadArtifactAs = (format: 'Markdown' | 'Word' | 'PDF') => {
        clickArtifactToolbarMenuItem(`下载 ${format}`);
    };

    it('shows placeholder when content is empty', () => {
        render(<ArtifactPane />);
        // Should render the pane with "当前产出物.md" header
        expect(screen.getByText(/当前产出物/)).toBeTruthy();
    });

    it('renders markdown content', () => {
        useStore.setState({ artifactContent: '# Hello World\n\nThis is **bold** text.' });
        const { container } = render(<ArtifactPane />);
        // ReactMarkdown renders the heading and paragraph
        expect(container.textContent).toContain('Hello World');
        expect(container.textContent).toContain('bold');
    });

    it('shows a friendly animated artifact generation state while generating', () => {
        useStore.setState({
            artifactContent: '# 需求分析文档\n\n初始内容',
            isGenerating: true,
        });

        const { container } = render(<ArtifactPane />);

        expect(screen.getByText('正在构建产出物')).toBeTruthy();
        expect(screen.getByText('正在构建右侧产出物')).toBeTruthy();
        expect(screen.getByTestId('artifact-generation-animation')).toBeTruthy();
        expect(container.querySelector('.mt-3.h-1')).toBeNull();
    });

    it('keeps secondary artifact actions behind the artifact toolbar menu', () => {
        useStore.setState({ artifactContent: '# 当前产出物' });
        render(<ArtifactPane />);

        expect(screen.queryByTitle('批注')).toBeNull();
        expect(screen.queryByTitle('章节锁定')).toBeNull();
        expect(screen.queryByTitle('下载')).toBeNull();

        fireEvent.click(screen.getByRole('button', { name: '更多产物操作' }));

        expect(screen.getByRole('menuitem', { name: '批注' })).toBeTruthy();
        expect(screen.getByRole('menuitem', { name: '章节锁定' })).toBeTruthy();
        expect(screen.getByRole('menuitem', { name: '下载 Markdown' })).toBeTruthy();
        expect(screen.getByRole('menuitem', { name: '下载 Word' })).toBeTruthy();
        expect(screen.getByRole('menuitem', { name: '下载 PDF' })).toBeTruthy();
    });

    it('opens comments from the artifact toolbar menu', () => {
        useStore.setState({ artifactContent: '# 当前产物\n\n需要批注的内容' });
        render(<ArtifactPane />);

        fireEvent.click(screen.getByRole('button', { name: '更多产物操作' }));
        fireEvent.click(screen.getByRole('menuitem', { name: '批注' }));

        expect(screen.getByText('产出物批注')).toBeTruthy();
        expect(screen.queryByRole('menuitem', { name: '下载 Markdown' })).toBeNull();
    });

    it('opens an artifact review panel that summarizes unresolved collaboration work', () => {
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 0,
            artifactContent: '# 需求分析\n\n## 登录边界\n\n需要确认',
            artifactComments: [
                {
                    id: 'comment-open',
                    stageId: 'CLARIFY',
                    content: '这里需要业务确认登录边界。',
                    artifactExcerpt: '登录边界',
                    anchorText: '登录边界',
                    createdAt: 1710000000000,
                    status: 'open',
                    resolvedAt: null,
                    replies: [],
                },
                {
                    id: 'comment-resolved',
                    stageId: 'CLARIFY',
                    content: '已确认的旧批注不应进入待办列表。',
                    artifactExcerpt: '旧内容',
                    anchorText: null,
                    createdAt: 1710000001000,
                    status: 'resolved',
                    resolvedAt: 1710000002000,
                    replies: [],
                },
            ],
            artifactSectionLocks: [
                {
                    id: 'lock-login',
                    stageId: 'CLARIFY',
                    heading: '## 登录边界',
                    sectionAnchor: '登录边界::1',
                    content: '## 登录边界\n\n需要确认',
                    createdAt: 1710000003000,
                },
            ],
            artifactAuditEvents: [
                {
                    stageId: 'CLARIFY',
                    eventType: 'artifact_merge_block_server_restored',
                    summary: '合并轨迹：恢复服务端删除块「风险 / 验收」',
                    createdAt: 1710000004000,
                },
            ],
            artifactHistory: [
                {
                    id: 'run-123-CLARIFY-v2',
                    timestamp: 1710000005000,
                    content: '# 需求分析\n\n版本 2',
                    stageId: 'CLARIFY',
                },
            ],
        });
        render(<ArtifactPane />);

        fireEvent.click(screen.getByRole('button', { name: '更多产物操作' }));
        fireEvent.click(screen.getByRole('menuitem', { name: '审阅' }));

        expect(screen.getByText('产物审阅')).toBeTruthy();
        expect(screen.getByText('1 条未解决批注')).toBeTruthy();
        expect(screen.getByText('1 个锁定章节')).toBeTruthy();
        expect(screen.getByText('1 条近期轨迹')).toBeTruthy();
        expect(screen.getByText('这里需要业务确认登录边界。')).toBeTruthy();
        expect(screen.queryByText('已确认的旧批注不应进入待办列表。')).toBeNull();
        expect(screen.getByText('## 登录边界')).toBeTruthy();
        expect(screen.getByText('合并轨迹：恢复服务端删除块「风险 / 验收」')).toBeTruthy();
        expect(screen.getByText('最近版本：run-123-CLARIFY-v2')).toBeTruthy();
    });

    it('resolves unresolved comments directly from the artifact review panel', () => {
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 0,
            artifactContent: '# 需求分析\n\n## 登录边界\n\n需要确认',
            artifactComments: [
                {
                    id: 'comment-open',
                    stageId: 'CLARIFY',
                    content: '这里需要业务确认登录边界。',
                    artifactExcerpt: '登录边界',
                    anchorText: '登录边界',
                    createdAt: 1710000000000,
                    status: 'open',
                    resolvedAt: null,
                    replies: [],
                },
            ],
        });
        render(<ArtifactPane />);

        clickArtifactToolbarMenuItem('审阅');
        fireEvent.click(screen.getByRole('button', {
            name: '标记已解决：这里需要业务确认登录边界。',
        }));

        expect(screen.queryByText('这里需要业务确认登录边界。')).toBeNull();
        expect(screen.getByText('当前阶段没有未解决批注。')).toBeTruthy();
        expect(useStore.getState().artifactComments).toEqual([
            expect.objectContaining({
                id: 'comment-open',
                status: 'resolved',
            }),
        ]);
    });

    it('locates active comment anchors from the artifact review panel', () => {
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 0,
            artifactContent: '# 需求分析文档\n\n默认正文。\n\n请重点确认 SSO 回调失败后的登录边界。',
            artifactComments: [
                {
                    id: 'comment-1',
                    stageId: 'CLARIFY',
                    content: '这里需要业务确认登录边界。',
                    artifactExcerpt: '请重点确认 SSO 回调失败后的登录边界。',
                    anchorText: '请重点确认 SSO 回调失败后的登录边界。',
                    createdAt: 1710000000000,
                    status: 'open',
                    resolvedAt: null,
                    replies: [],
                },
            ],
        });

        const { container } = render(<ArtifactPane />);
        clickArtifactToolbarMenuItem('审阅');
        fireEvent.click(screen.getByRole('button', {
            name: '定位正文：这里需要业务确认登录边界。',
        }));

        const highlight = container.querySelector('[data-artifact-anchor-highlight="true"]');
        expect(highlight?.textContent).toBe('请重点确认 SSO 回调失败后的登录边界。');
    });

    it('opens comment handling for stale anchors from the artifact review panel', () => {
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 0,
            artifactContent: '# 需求分析\n\n新的正文',
            artifactComments: [
                {
                    id: 'comment-stale',
                    stageId: 'CLARIFY',
                    content: '旧位置需要处理。',
                    artifactExcerpt: '旧正文',
                    anchorText: '旧正文',
                    createdAt: 1710000000000,
                    status: 'open',
                    resolvedAt: null,
                    replies: [],
                },
            ],
        });
        render(<ArtifactPane />);

        clickArtifactToolbarMenuItem('审阅');
        fireEvent.click(screen.getByRole('button', {
            name: '处理失效锚点：旧位置需要处理。',
        }));

        expect(screen.getByText('产出物批注')).toBeTruthy();
        expect(screen.getByRole('button', { name: '重新绑定选区' })).toBeTruthy();
        expect(screen.queryByText('产物审阅')).toBeNull();
    });

    it('opens section locks and history from the artifact review panel', () => {
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 0,
            artifactContent: '# 需求分析\n\n## 已确认范围\n\n登录',
            artifactHistory: [
                {
                    id: 'version-1',
                    content: '# 历史版本',
                    timestamp: 1710000000000,
                    stageId: 'CLARIFY',
                },
            ],
            artifactSectionLocks: [
                {
                    id: 'lock-1',
                    stageId: 'CLARIFY',
                    heading: '## 已确认范围',
                    sectionAnchor: '已确认范围::1',
                    content: '## 已确认范围\n\n登录',
                    createdAt: 1710000000000,
                },
            ],
        });
        render(<ArtifactPane />);

        clickArtifactToolbarMenuItem('审阅');
        fireEvent.click(screen.getByRole('button', {
            name: '管理锁定章节：## 已确认范围',
        }));
        expect(screen.getByText('章节锁定')).toBeTruthy();
        expect(screen.queryByText('产物审阅')).toBeNull();

        fireEvent.click(screen.getByTitle('关闭章节锁定'));
        clickArtifactToolbarMenuItem('审阅');
        fireEvent.click(screen.getByRole('button', {
            name: '查看最近版本：version-1',
        }));
        expect(screen.getByText('版本预览')).toBeTruthy();
        expect(screen.queryByText('产物审阅')).toBeNull();
    });

    it('renders mermaid diagrams', () => {
        useStore.setState({ artifactContent: '```mermaid\ngraph TD\nA-->B\n```' });
        render(<ArtifactPane />);
        expect(screen.getByTestId('mermaid')).toBeTruthy();
    });

    it('defers Mermaid rendering while the artifact is still generating', () => {
        useStore.setState({
            artifactContent: '```mermaid\ngraph TD\nA-->B\n```',
            isGenerating: true,
        });

        render(<ArtifactPane />);

        expect(screen.queryByTestId('mermaid')).toBeNull();
        expect(screen.getByText('图表将在产出物稳定后绘制')).toBeTruthy();
    });

    it('renders code blocks', () => {
        useStore.setState({ artifactContent: '```python\nprint("hello")\n```' });
        render(<ArtifactPane />);
        expect(screen.getByText('python')).toBeTruthy();
    });

    it('renders structured visual blocks through the artifact Markdown renderer', () => {
        useStore.setState({
            artifactContent: [
                '```ai4se-visual',
                JSON.stringify({
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
                }),
                '```',
            ].join('\n'),
        });

        render(<ArtifactPane />);

        expect(screen.getByRole('table', { name: '需求-风险-用例追溯矩阵' })).toBeTruthy();
        expect(screen.getByText('REQ-1')).toBeTruthy();
        expect(screen.queryByText('ai4se-visual')).toBeNull();
    });

    it('records a current-stage diagnostic when a structured visual block is invalid', async () => {
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 0,
            artifactContent: [
                '```ai4se-visual',
                '{ broken',
                '```',
            ].join('\n'),
        });

        render(<ArtifactPane />);

        expect(screen.getByText('结构化可视化格式错误')).toBeTruthy();
        await waitFor(() => {
            expect(useStore.getState().artifactVisualDiagnostics).toEqual([
                expect.objectContaining({
                    stageId: 'CLARIFY',
                    kind: 'structured-visual',
                    message: '结构化可视化必须是合法 JSON。',
                }),
            ]);
        });
    });

    it('shows artifact quality diagnostics in the review panel', () => {
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 0,
            artifactContent: '# 草稿\n\n## 8. 阶段门禁\n\n等待确认',
        });

        render(<ArtifactPane />);
        clickArtifactToolbarMenuItem('审阅');

        expect(screen.getByText('质量诊断')).toBeTruthy();
        expect(screen.getByText('缺少标题：# 需求分析文档')).toBeTruthy();
        expect(screen.getByText('缺少专业字段：事实 ID')).toBeTruthy();
        expect(screen.getByText('缺少 Mermaid 图：flowchart')).toBeTruthy();
        expect(screen.getByText('阶段门禁缺少决策项')).toBeTruthy();
    });

    it('focuses a visual diagnostic from the artifact quality panel', async () => {
        const scrollIntoView = vi.fn();
        window.HTMLElement.prototype.scrollIntoView = scrollIntoView;
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 0,
            artifactContent: [
                '```ai4se-visual',
                '{ broken',
                '```',
            ].join('\n'),
            artifactVisualDiagnostics: [],
        });

        const { container } = render(<ArtifactPane />);
        await waitFor(() => {
            expect(screen.getByText('结构化可视化格式错误')).toBeTruthy();
        });

        clickArtifactToolbarMenuItem('审阅');
        fireEvent.click(screen.getByRole('button', { name: '定位质量诊断：结构化可视化格式错误' }));

        await waitFor(() => expect(scrollIntoView).toHaveBeenCalled());
        expect(container.querySelector('[data-artifact-visual-focused="true"]')).toBeTruthy();
    });

    it('scrolls and highlights a focused Mermaid visual diagnostic in the current preview', async () => {
        const scrollIntoView = vi.fn();
        window.HTMLElement.prototype.scrollIntoView = scrollIntoView;
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 0,
            artifactContent: [
                '```mermaid',
                'graph TD',
                'A-->B',
                '```',
            ].join('\n'),
            artifactVisualDiagnostics: [
                {
                    id: 'mermaid:CLARIFY:0',
                    stageId: 'CLARIFY',
                    kind: 'mermaid',
                    title: 'Mermaid 图表渲染失败',
                    message: 'Mermaid syntax error',
                    blockIndex: 0,
                    createdAt: Date.now(),
                },
            ],
            artifactVisualDiagnosticFocusRequest: { id: 'mermaid:CLARIFY:0', seq: 1 },
        });

        const { container } = render(<ArtifactPane />);

        await waitFor(() => expect(scrollIntoView).toHaveBeenCalled());
        const focusedBlock = container.querySelector('[data-artifact-visual-diagnostic-id="mermaid:CLARIFY:0"]');
        expect(focusedBlock).toBeTruthy();
        expect(focusedBlock?.getAttribute('data-artifact-visual-focused')).toBe('true');
    });

    it('switches from code mode to preview and refocuses repeated structured visual diagnostic requests', async () => {
        const scrollIntoView = vi.fn();
        window.HTMLElement.prototype.scrollIntoView = scrollIntoView;
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 0,
            artifactContent: [
                '```ai4se-visual',
                '{ broken',
                '```',
            ].join('\n'),
            artifactVisualDiagnostics: [],
        });

        const { container } = render(<ArtifactPane />);
        await waitFor(() => {
            expect(useStore.getState().artifactVisualDiagnostics).toEqual([
                expect.objectContaining({
                    id: 'structured-visual:CLARIFY:0',
                    stageId: 'CLARIFY',
                    kind: 'structured-visual',
                }),
            ]);
        });

        fireEvent.click(screen.getByTitle('代码'));
        await act(async () => {
            useStore.getState().focusArtifactVisualDiagnostic('structured-visual:CLARIFY:0');
        });

        await waitFor(() => expect(scrollIntoView).toHaveBeenCalledTimes(1));
        expect(screen.getByText('结构化可视化格式错误')).toBeTruthy();
        const focusedBlock = container.querySelector('[data-artifact-visual-diagnostic-id="structured-visual:CLARIFY:0"]');
        expect(focusedBlock?.getAttribute('data-artifact-visual-focused')).toBe('true');

        await act(async () => {
            useStore.getState().focusArtifactVisualDiagnostic('structured-visual:CLARIFY:0');
        });
        await waitFor(() => expect(scrollIntoView).toHaveBeenCalledTimes(2));
    });

    it('does not expose Mermaid retry actions in read-only history preview', () => {
        useStore.setState({
            artifactContent: '# Current artifact',
            artifactHistory: [
                {
                    id: 'v1',
                    timestamp: 123,
                    content: '# Historical artifact\n\n```mermaid\ngraph TD\nA-->B\n```',
                    stageId: 'CLARIFY',
                },
            ],
        });

        render(<ArtifactPane />);
        fireEvent.click(screen.getByTitle('历史版本'));

        expect(screen.getByText(/版本预览/)).toBeTruthy();
        expect(screen.getByTestId('mermaid').textContent).toContain('graph TD');
        expect(screen.queryByRole('button', { name: '重新生成图表' })).toBeNull();
    });

    it('does not record visual diagnostics from read-only history preview', async () => {
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 0,
            artifactContent: '# Current artifact',
            artifactHistory: [
                {
                    id: 'v1',
                    timestamp: 123,
                    content: [
                        '# Historical artifact',
                        '',
                        '```ai4se-visual',
                        '{ broken',
                        '```',
                    ].join('\n'),
                    stageId: 'CLARIFY',
                },
            ],
        });

        render(<ArtifactPane />);
        fireEvent.click(screen.getByTitle('历史版本'));

        expect(screen.getByText('结构化可视化格式错误')).toBeTruthy();
        await waitFor(() => {
            expect(useStore.getState().artifactVisualDiagnostics).toEqual([]);
        });
    });

    it('does not attach visual diagnostic focus anchors to read-only history preview', () => {
        useStore.setState({
            artifactContent: '# Current artifact',
            artifactHistory: [
                {
                    id: 'v1',
                    timestamp: 123,
                    content: '# Historical artifact\n\n```mermaid\ngraph TD\nA-->B\n```',
                    stageId: 'CLARIFY',
                },
            ],
        });

        const { container } = render(<ArtifactPane />);
        fireEvent.click(screen.getByTitle('历史版本'));

        expect(screen.getByText(/版本预览/)).toBeTruthy();
        expect(container.querySelector('[data-artifact-visual-diagnostic-id]')).toBeNull();
    });

    it('only lists history versions for the current workflow stage', () => {
        const artifactHistory = [
            {
                id: 'clarify-version',
                timestamp: 123,
                content: '# CLARIFY version\n\n需求澄清版本',
                stageId: 'CLARIFY',
            },
            {
                id: 'strategy-version',
                timestamp: 456,
                content: '# STRATEGY version\n\n策略制定版本',
                stageId: 'STRATEGY',
            },
        ];
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 1,
            artifactContent: '# Current strategy artifact',
            artifactHistory,
        });

        render(<ArtifactPane />);
        fireEvent.click(screen.getByTitle('历史版本'));

        expect(screen.getAllByText('STRATEGY version').length).toBeGreaterThan(0);
        expect(screen.queryByText('CLARIFY version')).toBeNull();
    });

    it('shows artifact audit trail for the current workflow stage in the history panel', () => {
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 1,
            artifactContent: '# Current strategy artifact',
            artifactHistory: [
                {
                    id: 'strategy-version',
                    timestamp: 456,
                    content: '# STRATEGY version\n\n策略制定版本',
                    stageId: 'STRATEGY',
                },
            ],
            artifactAuditEvents: [
                {
                    stageId: 'STRATEGY',
                    eventType: 'artifact_saved',
                    summary: '保存了 STRATEGY 阶段产出物 v1',
                    createdAt: 1710000000400,
                },
                {
                    stageId: 'CLARIFY',
                    eventType: 'collaboration_updated',
                    summary: '更新了 CLARIFY 阶段协作状态：1 条批注，0 个章节锁',
                    createdAt: 1710000000300,
                },
            ],
        });

        render(<ArtifactPane />);
        fireEvent.click(screen.getByTitle('历史版本'));

        expect(screen.getByText('活动轨迹')).toBeTruthy();
        expect(screen.getByText('保存了 STRATEGY 阶段产出物 v1')).toBeTruthy();
        expect(screen.queryByText('更新了 CLARIFY 阶段协作状态：1 条批注，0 个章节锁')).toBeNull();
    });

    it('downloads artifact markdown with a workflow-specific filename', async () => {
        const createdAnchors: HTMLAnchorElement[] = [];
        const click = vi.fn();
        vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:artifact');
        vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});
        vi.spyOn(document, 'createElement').mockImplementation((tagName, options) => {
            const element = originalCreateElement(tagName, options);
            if (tagName.toLowerCase() === 'a') {
                Object.defineProperty(element, 'click', {
                    configurable: true,
                    value: click,
                });
                createdAnchors.push(element as HTMLAnchorElement);
            }
            return element;
        });
        useStore.setState({
            workflow: 'REQ_REVIEW',
            artifactContent: '# 需求评审报告',
        });

        render(<ArtifactPane />);
        downloadArtifactAs('Markdown');

        expect(createdAnchors).toHaveLength(1);
        expect(createdAnchors[0].download).toBe('req_review_artifact.md');
        expect(createdAnchors[0].download).not.toBe('lisa_artifact.md');
        expect(click).toHaveBeenCalledTimes(1);
    });

    it('downloads artifact as a real DOCX package with escaped content', async () => {
        const createdAnchors: HTMLAnchorElement[] = [];
        const click = vi.fn();
        const createObjectURL = vi
            .spyOn(URL, 'createObjectURL')
            .mockReturnValue('blob:artifact-doc');
        vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});
        vi.spyOn(document, 'createElement').mockImplementation((tagName, options) => {
            const element = originalCreateElement(tagName, options);
            if (tagName.toLowerCase() === 'a') {
                Object.defineProperty(element, 'click', {
                    configurable: true,
                    value: click,
                });
                createdAnchors.push(element as HTMLAnchorElement);
            }
            return element;
        });
        useStore.setState({
            workflow: 'TEST_DESIGN',
            artifactContent: [
                '# 测试报告',
                '',
                '这是 **重点** 结论。',
                '',
                '- 风险覆盖',
                '- 回归范围',
                '',
                '| 模块 | 状态 |',
                '| --- | --- |',
                '| 登录 | 通过 |',
                '',
                '```gherkin',
                'Given 用户已登录',
                'When 打开首页',
                'Then 展示仪表盘',
                '```',
                '',
                '<script>alert("x")</script>',
            ].join('\n'),
        });

        render(<ArtifactPane />);
        downloadArtifactAs('Word');

        expect(createdAnchors).toHaveLength(1);
        expect(createdAnchors[0].download).toBe('test_design_artifact.docx');
        const blob = createObjectURL.mock.calls[0][0] as Blob;
        expect(blob.type).toBe('application/vnd.openxmlformats-officedocument.wordprocessingml.document');
        const bytes = new Uint8Array(await blob.arrayBuffer());
        expect(bytes[0]).toBe(0x50);
        expect(bytes[1]).toBe(0x4b);
        const packageText = new TextDecoder().decode(bytes);
        expect(packageText).toContain('[Content_Types].xml');
        expect(packageText).toContain('_rels/.rels');
        expect(packageText).toContain('word/document.xml');
        expect(packageText).toContain('测试报告');
        expect(packageText).toContain('重点');
        expect(packageText).toContain('风险覆盖');
        expect(packageText).toContain('登录');
        expect(packageText).toContain('Given 用户已登录');
        expect(packageText).toContain('&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;');
        expect(packageText).not.toContain('<script>alert("x")</script>');
        expect(click).toHaveBeenCalledTimes(1);
    });

    it('downloads artifact as a minimal PDF document', async () => {
        const createdAnchors: HTMLAnchorElement[] = [];
        const click = vi.fn();
        const createObjectURL = vi
            .spyOn(URL, 'createObjectURL')
            .mockReturnValue('blob:artifact-pdf');
        vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});
        vi.spyOn(document, 'createElement').mockImplementation((tagName, options) => {
            const element = originalCreateElement(tagName, options);
            if (tagName.toLowerCase() === 'a') {
                Object.defineProperty(element, 'click', {
                    configurable: true,
                    value: click,
                });
                createdAnchors.push(element as HTMLAnchorElement);
            }
            return element;
        });
        useStore.setState({
            workflow: 'TEST_DESIGN',
            artifactContent: '# 测试报告\n\nPDF 导出内容',
        });

        render(<ArtifactPane />);
        downloadArtifactAs('PDF');

        expect(createdAnchors).toHaveLength(1);
        expect(createdAnchors[0].download).toBe('test_design_artifact.pdf');
        const blob = createObjectURL.mock.calls[0][0] as Blob;
        expect(blob.type).toBe('application/pdf');
        const content = await blob.text();
        expect(content.startsWith('%PDF-1.4')).toBe(true);
        expect(content).toContain(toUtf16BeHex('测试报告'));
        expect(content).not.toContain(toUtf16BeHex('# 测试报告'));
        expect(click).toHaveBeenCalledTimes(1);
    });

    it('downloads long artifacts as a paginated PDF without truncating later content', async () => {
        const createdAnchors: HTMLAnchorElement[] = [];
        const click = vi.fn();
        const createObjectURL = vi
            .spyOn(URL, 'createObjectURL')
            .mockReturnValue('blob:artifact-long-pdf');
        vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});
        vi.spyOn(document, 'createElement').mockImplementation((tagName, options) => {
            const element = originalCreateElement(tagName, options);
            if (tagName.toLowerCase() === 'a') {
                Object.defineProperty(element, 'click', {
                    configurable: true,
                    value: click,
                });
                createdAnchors.push(element as HTMLAnchorElement);
            }
            return element;
        });
        const lines = Array.from(
            { length: 70 },
            (_, index) => `第 ${index + 1} 行：PDF 分页验证内容`
        );
        useStore.setState({
            workflow: 'TEST_DESIGN',
            artifactContent: lines.join('\n'),
        });

        render(<ArtifactPane />);
        downloadArtifactAs('PDF');

        const blob = createObjectURL.mock.calls[0][0] as Blob;
        const content = await blob.text();
        expect(createdAnchors[0].download).toBe('test_design_artifact.pdf');
        expect(content).toContain('/Count 2');
        expect(content).toContain(toUtf16BeHex('第 70 行：PDF 分页验证内容'));
        expect(click).toHaveBeenCalledTimes(1);
    });

    it('downloads markdown artifacts as a cleaner PDF document layout', async () => {
        const createdAnchors: HTMLAnchorElement[] = [];
        const click = vi.fn();
        const createObjectURL = vi
            .spyOn(URL, 'createObjectURL')
            .mockReturnValue('blob:artifact-layout-pdf');
        vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});
        vi.spyOn(document, 'createElement').mockImplementation((tagName, options) => {
            const element = originalCreateElement(tagName, options);
            if (tagName.toLowerCase() === 'a') {
                Object.defineProperty(element, 'click', {
                    configurable: true,
                    value: click,
                });
                createdAnchors.push(element as HTMLAnchorElement);
            }
            return element;
        });
        useStore.setState({
            workflow: 'TEST_DESIGN',
            artifactContent: [
                '# 测试报告',
                '',
                '这是 **重点** 结论。',
                '',
                '- 风险覆盖',
                '- 回归范围',
                '',
                '| 模块 | 状态 |',
                '| --- | --- |',
                '| 登录 | 通过 |',
                '',
                '```gherkin',
                'Given 用户已登录',
                'Then 展示仪表盘',
                '```',
            ].join('\n'),
        });

        render(<ArtifactPane />);
        downloadArtifactAs('PDF');

        const blob = createObjectURL.mock.calls[0][0] as Blob;
        const content = await blob.text();
        expect(createdAnchors[0].download).toBe('test_design_artifact.pdf');
        expect(content).toContain(toUtf16BeHex('测试报告'));
        expect(content).toContain(toUtf16BeHex('这是 重点 结论。'));
        expect(content).toContain(toUtf16BeHex('• 风险覆盖'));
        expect(content).toContain(toUtf16BeHex('模块    状态'));
        expect(content).toContain(toUtf16BeHex('登录    通过'));
        expect(content).toContain(toUtf16BeHex('    Given 用户已登录'));
        expect(content).not.toContain(toUtf16BeHex('# 测试报告'));
        expect(content).not.toContain(toUtf16BeHex('| --- | --- |'));
        expect(content).not.toContain(toUtf16BeHex('```gherkin'));
        expect(click).toHaveBeenCalledTimes(1);
    });

    it('projects Mermaid and structured visuals into readable PDF content', async () => {
        const createdAnchors: HTMLAnchorElement[] = [];
        const click = vi.fn();
        const createObjectURL = vi
            .spyOn(URL, 'createObjectURL')
            .mockReturnValue('blob:artifact-visual-pdf');
        vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});
        vi.spyOn(document, 'createElement').mockImplementation((tagName, options) => {
            const element = originalCreateElement(tagName, options);
            if (tagName.toLowerCase() === 'a') {
                Object.defineProperty(element, 'click', {
                    configurable: true,
                    value: click,
                });
                createdAnchors.push(element as HTMLAnchorElement);
            }
            return element;
        });
        useStore.setState({
            workflow: 'TEST_DESIGN',
            artifactContent: [
                '# 测试策略',
                '',
                '```mermaid',
                'flowchart TD',
                'A[登录] --> B[校验]',
                '```',
                '',
                '```ai4se-visual',
                JSON.stringify({
                    type: 'risk-board',
                    title: '风险看板',
                    columns: ['风险', 'RPN'],
                    rows: [
                        { 风险: '登录失败', RPN: '80' },
                    ],
                }, null, 2),
                '```',
            ].join('\n'),
        });

        render(<ArtifactPane />);
        downloadArtifactAs('PDF');

        const blob = createObjectURL.mock.calls[0][0] as Blob;
        const content = await blob.text();
        expect(createdAnchors[0].download).toBe('test_design_artifact.pdf');
        expect(content).toContain(toUtf16BeHex('Mermaid 图表：flowchart'));
        expect(content).toContain(toUtf16BeHex('A[登录] --> B[校验]'));
        expect(content).toContain(toUtf16BeHex('结构化可视化：风险看板'));
        expect(content).toContain(toUtf16BeHex('风险    RPN'));
        expect(content).toContain(toUtf16BeHex('登录失败    80'));
        expect(content).not.toContain(toUtf16BeHex('```mermaid'));
        expect(content).not.toContain(toUtf16BeHex('```ai4se-visual'));
        expect(content).not.toContain(toUtf16BeHex('"type": "risk-board"'));
        expect(click).toHaveBeenCalledTimes(1);
    });

    it('draws Mermaid flowcharts as vector diagram shapes in exported PDF content streams', async () => {
        const createdAnchors: HTMLAnchorElement[] = [];
        const click = vi.fn();
        const createObjectURL = vi
            .spyOn(URL, 'createObjectURL')
            .mockReturnValue('blob:artifact-mermaid-vector-pdf');
        vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});
        vi.spyOn(document, 'createElement').mockImplementation((tagName, options) => {
            const element = originalCreateElement(tagName, options);
            if (tagName.toLowerCase() === 'a') {
                Object.defineProperty(element, 'click', {
                    configurable: true,
                    value: click,
                });
                createdAnchors.push(element as HTMLAnchorElement);
            }
            return element;
        });
        useStore.setState({
            workflow: 'TEST_DESIGN',
            artifactContent: [
                '# 系统边界图',
                '',
                '```mermaid',
                'flowchart TD',
                'A[用户入口] --> B[认证服务]',
                'B --> C[订单服务]',
                '```',
            ].join('\n'),
        });

        render(<ArtifactPane />);
        downloadArtifactAs('PDF');

        const blob = createObjectURL.mock.calls[0][0] as Blob;
        const content = await blob.text();
        const rectangleCount = content.match(/ re S/g)?.length ?? 0;
        expect(createdAnchors[0].download).toBe('test_design_artifact.pdf');
        expect(content).toContain(toUtf16BeHex('Mermaid 图表：flowchart'));
        expect(content).toContain(toUtf16BeHex('用户入口'));
        expect(content).toContain(toUtf16BeHex('认证服务'));
        expect(content).toContain(toUtf16BeHex('订单服务'));
        expect(content).toContain('0.18 0.55 0.95 RG');
        expect(rectangleCount).toBeGreaterThanOrEqual(3);
        expect(content).toContain(' m ');
        expect(content).toContain(' l S');
        expect(click).toHaveBeenCalledTimes(1);
    });

    it('draws Mermaid timelines as vector timeline shapes in exported PDF content streams', async () => {
        const createdAnchors: HTMLAnchorElement[] = [];
        const click = vi.fn();
        const createObjectURL = vi
            .spyOn(URL, 'createObjectURL')
            .mockReturnValue('blob:artifact-mermaid-timeline-pdf');
        vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});
        vi.spyOn(document, 'createElement').mockImplementation((tagName, options) => {
            const element = originalCreateElement(tagName, options);
            if (tagName.toLowerCase() === 'a') {
                Object.defineProperty(element, 'click', {
                    configurable: true,
                    value: click,
                });
                createdAnchors.push(element as HTMLAnchorElement);
            }
            return element;
        });
        useStore.setState({
            workflow: 'INCIDENT_REVIEW',
            artifactContent: [
                '# 事件还原',
                '',
                '```mermaid',
                'timeline',
                '    title 登录事故时间线',
                '    section 发现',
                '      09点10分 : 监控触发告警',
                '      09点18分 : 值班确认影响范围',
                '    section 恢复',
                '      09点42分 : 回滚异常发布',
                '```',
            ].join('\n'),
        });

        render(<ArtifactPane />);
        downloadArtifactAs('PDF');

        const blob = createObjectURL.mock.calls[0][0] as Blob;
        const content = await blob.text();
        const rectangleCount = content.match(/ re S/g)?.length ?? 0;
        expect(createdAnchors[0].download).toBe('incident_review_artifact.pdf');
        expect(content).toContain(toUtf16BeHex('Mermaid 图表：timeline'));
        expect(content).toContain(toUtf16BeHex('登录事故时间线'));
        expect(content).toContain(toUtf16BeHex('发现'));
        expect(content).toContain(toUtf16BeHex('09点10分：监控触发告警'));
        expect(content).not.toContain(toUtf16BeHex('section 发现'));
        expect(content).not.toContain(toUtf16BeHex('title 登录事故时间线'));
        expect(content).toContain('0.18 0.55 0.95 RG');
        expect(rectangleCount).toBeGreaterThanOrEqual(3);
        expect(content).toContain(' m ');
        expect(content).toContain(' l S');
        expect(click).toHaveBeenCalledTimes(1);
    });

    it('draws Mermaid mindmaps as vector hierarchy shapes in exported PDF content streams', async () => {
        const createdAnchors: HTMLAnchorElement[] = [];
        const click = vi.fn();
        const createObjectURL = vi
            .spyOn(URL, 'createObjectURL')
            .mockReturnValue('blob:artifact-mermaid-mindmap-pdf');
        vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});
        vi.spyOn(document, 'createElement').mockImplementation((tagName, options) => {
            const element = originalCreateElement(tagName, options);
            if (tagName.toLowerCase() === 'a') {
                Object.defineProperty(element, 'click', {
                    configurable: true,
                    value: click,
                });
                createdAnchors.push(element as HTMLAnchorElement);
            }
            return element;
        });
        useStore.setState({
            workflow: 'INCIDENT_REVIEW',
            artifactContent: [
                '# 根因分析',
                '',
                '```mermaid',
                'mindmap',
                '  root(("故障根因分析"))',
                '    流程',
                '      [发布前缺少回归门禁]',
                '    技术',
                '      [告警覆盖不足]',
                '```',
            ].join('\n'),
        });

        render(<ArtifactPane />);
        downloadArtifactAs('PDF');

        const blob = createObjectURL.mock.calls[0][0] as Blob;
        const content = await blob.text();
        const rectangleCount = content.match(/ re S/g)?.length ?? 0;
        expect(createdAnchors[0].download).toBe('incident_review_artifact.pdf');
        expect(content).toContain(toUtf16BeHex('Mermaid 图表：mindmap'));
        expect(content).toContain(toUtf16BeHex('故障根因分析'));
        expect(content).toContain(toUtf16BeHex('流程'));
        expect(content).toContain(toUtf16BeHex('发布前缺少回归门禁'));
        expect(content).toContain(toUtf16BeHex('技术'));
        expect(content).toContain(toUtf16BeHex('告警覆盖不足'));
        expect(content).not.toContain(toUtf16BeHex('root(("故障根因分析"))'));
        expect(content).not.toContain(toUtf16BeHex('[发布前缺少回归门禁]'));
        expect(content).toContain('0.18 0.55 0.95 RG');
        expect(rectangleCount).toBeGreaterThanOrEqual(5);
        expect(content).toContain(' m ');
        expect(content).toContain(' l S');
        expect(click).toHaveBeenCalledTimes(1);
    });

    it('draws Mermaid pie charts as vector distribution shapes in exported PDF content streams', async () => {
        const createdAnchors: HTMLAnchorElement[] = [];
        const click = vi.fn();
        const createObjectURL = vi
            .spyOn(URL, 'createObjectURL')
            .mockReturnValue('blob:artifact-mermaid-pie-pdf');
        vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});
        vi.spyOn(document, 'createElement').mockImplementation((tagName, options) => {
            const element = originalCreateElement(tagName, options);
            if (tagName.toLowerCase() === 'a') {
                Object.defineProperty(element, 'click', {
                    configurable: true,
                    value: click,
                });
                createdAnchors.push(element as HTMLAnchorElement);
            }
            return element;
        });
        useStore.setState({
            workflow: 'REQ_REVIEW',
            artifactContent: [
                '# 评审报告',
                '',
                '```mermaid',
                'pie title 评审问题优先级分布',
                '    "P0 (阻塞)" : 2',
                '    "P1 (重要)" : 3',
                '    "P2 (建议)" : 5',
                '```',
            ].join('\n'),
        });

        render(<ArtifactPane />);
        downloadArtifactAs('PDF');

        const blob = createObjectURL.mock.calls[0][0] as Blob;
        const content = await blob.text();
        const rectangleCount = content.match(/ re S/g)?.length ?? 0;
        expect(createdAnchors[0].download).toBe('req_review_artifact.pdf');
        expect(content).toContain(toUtf16BeHex('Mermaid 图表：pie'));
        expect(content).toContain(toUtf16BeHex('评审问题优先级分布'));
        expect(content).toContain(toUtf16BeHex('P0 (阻塞)：2'));
        expect(content).toContain(toUtf16BeHex('P1 (重要)：3'));
        expect(content).toContain(toUtf16BeHex('P2 (建议)：5'));
        expect(content).not.toContain(toUtf16BeHex('pie title 评审问题优先级分布'));
        expect(content).not.toContain(toUtf16BeHex('"P0 (阻塞)" : 2'));
        expect(content).toContain('0.18 0.55 0.95 RG');
        expect(content).toContain(' c ');
        expect(rectangleCount).toBeGreaterThanOrEqual(3);
        expect(content).toContain(' m ');
        expect(content).toContain(' l S');
        expect(click).toHaveBeenCalledTimes(1);
    });

    it('draws Mermaid journeys as vector journey map shapes in exported PDF content streams', async () => {
        const createdAnchors: HTMLAnchorElement[] = [];
        const click = vi.fn();
        const createObjectURL = vi
            .spyOn(URL, 'createObjectURL')
            .mockReturnValue('blob:artifact-mermaid-journey-pdf');
        vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});
        vi.spyOn(document, 'createElement').mockImplementation((tagName, options) => {
            const element = originalCreateElement(tagName, options);
            if (tagName.toLowerCase() === 'a') {
                Object.defineProperty(element, 'click', {
                    configurable: true,
                    value: click,
                });
                createdAnchors.push(element as HTMLAnchorElement);
            }
            return element;
        });
        useStore.setState({
            workflow: 'VALUE_DISCOVERY',
            artifactContent: [
                '# 用户旅程分析',
                '',
                '```mermaid',
                'journey',
                '    title 核心用户旅程',
                '    section 问题认知',
                '        意识到问题存在: 3: 用户',
                '    section 寻找方案',
                '        搜索解决方案: 2: 用户',
                '        对比不同选择: 2: 用户',
                '```',
            ].join('\n'),
        });

        render(<ArtifactPane />);
        downloadArtifactAs('PDF');

        const blob = createObjectURL.mock.calls[0][0] as Blob;
        const content = await blob.text();
        const rectangleCount = content.match(/ re S/g)?.length ?? 0;
        expect(createdAnchors[0].download).toBe('value_discovery_artifact.pdf');
        expect(content).toContain(toUtf16BeHex('Mermaid 图表：journey'));
        expect(content).toContain(toUtf16BeHex('核心用户旅程'));
        expect(content).toContain(toUtf16BeHex('问题认知'));
        expect(content).toContain(toUtf16BeHex('意识到问题存在：3（用户）'));
        expect(content).toContain(toUtf16BeHex('寻找方案'));
        expect(content).toContain(toUtf16BeHex('搜索解决方案：2（用户）'));
        expect(content).not.toContain(toUtf16BeHex('title 核心用户旅程'));
        expect(content).not.toContain(toUtf16BeHex('section 问题认知'));
        expect(content).not.toContain(toUtf16BeHex('意识到问题存在: 3: 用户'));
        expect(content).toContain('0.18 0.55 0.95 RG');
        expect(rectangleCount).toBeGreaterThanOrEqual(4);
        expect(content).toContain(' m ');
        expect(content).toContain(' l S');
        expect(click).toHaveBeenCalledTimes(1);
    });

    it('draws structured visual tables in exported PDF content streams', async () => {
        const createdAnchors: HTMLAnchorElement[] = [];
        const click = vi.fn();
        const createObjectURL = vi
            .spyOn(URL, 'createObjectURL')
            .mockReturnValue('blob:artifact-visual-table-pdf');
        vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});
        vi.spyOn(document, 'createElement').mockImplementation((tagName, options) => {
            const element = originalCreateElement(tagName, options);
            if (tagName.toLowerCase() === 'a') {
                Object.defineProperty(element, 'click', {
                    configurable: true,
                    value: click,
                });
                createdAnchors.push(element as HTMLAnchorElement);
            }
            return element;
        });
        useStore.setState({
            workflow: 'TEST_DESIGN',
            artifactContent: [
                '# 风险评估',
                '',
                '```ai4se-visual',
                JSON.stringify({
                    type: 'risk-board',
                    title: '核心风险矩阵',
                    columns: ['风险', 'RPN', '缓解策略'],
                    rows: [
                        { 风险: '登录失败', RPN: '80', 缓解策略: '补充异常路径用例' },
                        { 风险: '权限绕过', RPN: '96', 缓解策略: '增加角色矩阵覆盖' },
                    ],
                }, null, 2),
                '```',
            ].join('\n'),
        });

        render(<ArtifactPane />);
        downloadArtifactAs('PDF');

        const blob = createObjectURL.mock.calls[0][0] as Blob;
        const content = await blob.text();
        expect(createdAnchors[0].download).toBe('test_design_artifact.pdf');
        expect(content).toContain(toUtf16BeHex('结构化可视化：核心风险矩阵'));
        expect(content).toContain(toUtf16BeHex('登录失败    80    补充异常路径用例'));
        expect(content).toContain(' re S');
        expect(content).toContain(' m ');
        expect(content).toContain(' l S');
        expect(click).toHaveBeenCalledTimes(1);
    });

    it('draws structured visual table borders on every PDF page that contains table rows', async () => {
        const createdAnchors: HTMLAnchorElement[] = [];
        const click = vi.fn();
        const createObjectURL = vi
            .spyOn(URL, 'createObjectURL')
            .mockReturnValue('blob:artifact-visual-table-pages-pdf');
        vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});
        vi.spyOn(document, 'createElement').mockImplementation((tagName, options) => {
            const element = originalCreateElement(tagName, options);
            if (tagName.toLowerCase() === 'a') {
                Object.defineProperty(element, 'click', {
                    configurable: true,
                    value: click,
                });
                createdAnchors.push(element as HTMLAnchorElement);
            }
            return element;
        });
        const rows = Array.from({ length: 55 }, (_, index) => ({
            风险: `风险 ${index + 1}`,
            RPN: String(100 - index),
            缓解策略: `策略 ${index + 1}`,
        }));
        useStore.setState({
            workflow: 'TEST_DESIGN',
            artifactContent: [
                '# 长风险矩阵',
                '',
                '```ai4se-visual',
                JSON.stringify({
                    type: 'risk-board',
                    title: '长风险矩阵',
                    columns: ['风险', 'RPN', '缓解策略'],
                    rows,
                }, null, 2),
                '```',
            ].join('\n'),
        });

        render(<ArtifactPane />);
        downloadArtifactAs('PDF');

        const blob = createObjectURL.mock.calls[0][0] as Blob;
        const content = await blob.text();
        const tableRectangleCount = content.match(/ re S/g)?.length ?? 0;
        expect(createdAnchors[0].download).toBe('test_design_artifact.pdf');
        expect(content).toContain('/Count 2');
        expect(content).toContain(toUtf16BeHex('风险 55    46    策略 55'));
        expect(tableRectangleCount).toBeGreaterThanOrEqual(2);
        expect(click).toHaveBeenCalledTimes(1);
    });

    it('shows a diff between the selected history version and the current artifact', () => {
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 0,
            artifactContent: '# 当前产物\n\n新结论\n保留内容',
            artifactHistory: [
                {
                    id: 'v1',
                    timestamp: 123,
                    content: '# 当前产物\n\n旧结论\n保留内容',
                    stageId: 'CLARIFY',
                },
            ],
        });

        render(<ArtifactPane />);
        fireEvent.click(screen.getByTitle('历史版本'));
        fireEvent.click(screen.getByRole('button', { name: '差异' }));

        expect(screen.getByText('与当前产出物对比')).toBeTruthy();
        expect(screen.getByText('- 旧结论')).toBeTruthy();
        expect(screen.getByText('+ 新结论')).toBeTruthy();
        expect(screen.getByText('保留内容')).toBeTruthy();
    });

    it('restores the selected history version and keeps the previous current artifact in history', () => {
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 0,
            artifactContent: '# 当前产物\n\n新结论',
            artifactHistory: [
                {
                    id: 'v1',
                    timestamp: 123,
                    content: '# 当前产物\n\n旧结论',
                    stageId: 'CLARIFY',
                },
            ],
        });

        render(<ArtifactPane />);
        fireEvent.click(screen.getByTitle('历史版本'));
        fireEvent.click(screen.getByRole('button', { name: '恢复此版本' }));

        const state = useStore.getState();
        expect(state.artifactContent).toBe('# 当前产物\n\n旧结论');
        expect(state.stageArtifacts.CLARIFY).toBe('# 当前产物\n\n旧结论');
        expect(state.artifactHistory).toEqual(
            expect.arrayContaining([
                expect.objectContaining({
                    content: '# 当前产物\n\n新结论',
                    stageId: 'CLARIFY',
                }),
            ])
        );
    });

    it('restores a single removed history line from the history diff', () => {
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 0,
            artifactContent: '# 当前产物\n\n新结论\n保留内容',
            stageArtifacts: {
                CLARIFY: '# 当前产物\n\n新结论\n保留内容',
            },
            artifactHistory: [
                {
                    id: 'v1',
                    timestamp: 123,
                    content: '# 当前产物\n\n旧结论\n保留内容',
                    stageId: 'CLARIFY',
                },
            ],
        });

        render(<ArtifactPane />);
        fireEvent.click(screen.getByTitle('历史版本'));
        fireEvent.click(screen.getByRole('button', { name: '差异' }));
        fireEvent.click(screen.getByRole('button', { name: '恢复此行：旧结论' }));

        const state = useStore.getState();
        expect(state.artifactContent).toBe('# 当前产物\n\n旧结论\n新结论\n保留内容');
        expect(state.stageArtifacts.CLARIFY).toBe('# 当前产物\n\n旧结论\n新结论\n保留内容');
        expect(state.artifactHistory).toEqual(expect.arrayContaining([
            expect.objectContaining({
                content: '# 当前产物\n\n新结论\n保留内容',
                stageId: 'CLARIFY',
            }),
        ]));
    });

    it('discards a single current-only line from the history diff', () => {
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 0,
            artifactContent: '# 当前产物\n\n新结论\n保留内容',
            stageArtifacts: {
                CLARIFY: '# 当前产物\n\n新结论\n保留内容',
            },
            artifactHistory: [
                {
                    id: 'v1',
                    timestamp: 123,
                    content: '# 当前产物\n\n保留内容',
                    stageId: 'CLARIFY',
                },
            ],
        });

        render(<ArtifactPane />);
        fireEvent.click(screen.getByTitle('历史版本'));
        fireEvent.click(screen.getByRole('button', { name: '差异' }));
        fireEvent.click(screen.getByRole('button', { name: '丢弃当前行：新结论' }));

        const state = useStore.getState();
        expect(state.artifactContent).toBe('# 当前产物\n\n保留内容');
        expect(state.stageArtifacts.CLARIFY).toBe('# 当前产物\n\n保留内容');
        expect(state.artifactHistory).toEqual(expect.arrayContaining([
            expect.objectContaining({
                content: '# 当前产物\n\n新结论\n保留内容',
                stageId: 'CLARIFY',
            }),
        ]));
    });

    it('restores a contiguous removed history block from the history diff', () => {
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 0,
            artifactContent: '# 当前产物\n\n新结论\n保留内容',
            stageArtifacts: {
                CLARIFY: '# 当前产物\n\n新结论\n保留内容',
            },
            artifactHistory: [
                {
                    id: 'v1',
                    timestamp: 123,
                    content: '# 当前产物\n\n旧风险\n旧验收口径\n保留内容',
                    stageId: 'CLARIFY',
                },
            ],
        });

        render(<ArtifactPane />);
        fireEvent.click(screen.getByTitle('历史版本'));
        fireEvent.click(screen.getByRole('button', { name: '差异' }));
        fireEvent.click(screen.getByRole('button', { name: '恢复变更块：旧风险 / 旧验收口径' }));

        const state = useStore.getState();
        expect(state.artifactContent).toBe('# 当前产物\n\n旧风险\n旧验收口径\n新结论\n保留内容');
        expect(state.stageArtifacts.CLARIFY).toBe('# 当前产物\n\n旧风险\n旧验收口径\n新结论\n保留内容');
        expect(state.artifactHistory).toEqual(expect.arrayContaining([
            expect.objectContaining({
                content: '# 当前产物\n\n新结论\n保留内容',
                stageId: 'CLARIFY',
            }),
        ]));
    });

    it('discards a contiguous current-only history block from the history diff', () => {
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 0,
            artifactContent: '# 当前产物\n\n新风险\n新验收口径\n保留内容',
            stageArtifacts: {
                CLARIFY: '# 当前产物\n\n新风险\n新验收口径\n保留内容',
            },
            artifactHistory: [
                {
                    id: 'v1',
                    timestamp: 123,
                    content: '# 当前产物\n\n保留内容',
                    stageId: 'CLARIFY',
                },
            ],
        });

        render(<ArtifactPane />);
        fireEvent.click(screen.getByTitle('历史版本'));
        fireEvent.click(screen.getByRole('button', { name: '差异' }));
        fireEvent.click(screen.getByRole('button', { name: '丢弃变更块：新风险 / 新验收口径' }));

        const state = useStore.getState();
        expect(state.artifactContent).toBe('# 当前产物\n\n保留内容');
        expect(state.stageArtifacts.CLARIFY).toBe('# 当前产物\n\n保留内容');
        expect(state.artifactHistory).toEqual(expect.arrayContaining([
            expect.objectContaining({
                content: '# 当前产物\n\n新风险\n新验收口径\n保留内容',
                stageId: 'CLARIFY',
            }),
        ]));
    });

    it('saves a controlled manual edit into the current artifact, stage artifact, and history', () => {
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 1,
            artifactContent: '# 测试策略蓝图\n\n旧优先级：P1',
            stageArtifacts: {
                STRATEGY: '# 测试策略蓝图\n\n旧优先级：P1',
            },
            artifactHistory: [],
        });

        render(<ArtifactPane />);
        fireEvent.click(screen.getByTitle('编辑产出物'));
        fireEvent.change(screen.getByLabelText('编辑产出物 Markdown'), {
            target: { value: '# 测试策略蓝图\n\n新优先级：P0' },
        });
        fireEvent.click(screen.getByRole('button', { name: '保存修改' }));

        const state = useStore.getState();
        expect(state.artifactContent).toBe('# 测试策略蓝图\n\n新优先级：P0');
        expect(state.stageArtifacts.STRATEGY).toBe('# 测试策略蓝图\n\n新优先级：P0');
        expect(state.artifactHistory).toEqual([
            expect.objectContaining({
                content: '# 测试策略蓝图\n\n旧优先级：P1',
                stageId: 'STRATEGY',
            }),
            expect.objectContaining({
                content: '# 测试策略蓝图\n\n新优先级：P0',
                stageId: 'STRATEGY',
            }),
        ]);
        expect(screen.queryByLabelText('编辑产出物 Markdown')).toBeNull();
    });

    it('persists a manual edit to the server when the current run is known', async () => {
        vi.mocked(updateRunArtifact).mockResolvedValue({
            stageId: 'STRATEGY',
            content: '# 测试策略蓝图\n\n服务端保存后的 P0 优先级',
            versionNumber: 3,
        });
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 1,
            currentRunId: 'run-123',
            artifactContent: '# 测试策略蓝图\n\n旧优先级：P1',
            stageArtifacts: {
                STRATEGY: '# 测试策略蓝图\n\n旧优先级：P1',
            },
            artifactHistory: [],
        });

        render(<ArtifactPane />);
        fireEvent.click(screen.getByTitle('编辑产出物'));
        fireEvent.change(screen.getByLabelText('编辑产出物 Markdown'), {
            target: { value: '# 测试策略蓝图\n\n服务端保存后的 P0 优先级' },
        });
        fireEvent.click(screen.getByRole('button', { name: '保存修改' }));

        await waitFor(() => {
            expect(updateRunArtifact).toHaveBeenCalledWith(
                'run-123',
                'STRATEGY',
                '# 测试策略蓝图\n\n服务端保存后的 P0 优先级',
                { expectedVersionNumber: undefined },
            );
        });
        await waitFor(() => {
            expect(screen.queryByLabelText('编辑产出物 Markdown')).toBeNull();
        });

        const state = useStore.getState();
        expect(state.artifactContent).toBe('# 测试策略蓝图\n\n服务端保存后的 P0 优先级');
        expect(state.stageArtifacts.STRATEGY).toBe('# 测试策略蓝图\n\n服务端保存后的 P0 优先级');
        expect(state.artifactHistory).toEqual([
            expect.objectContaining({
                content: '# 测试策略蓝图\n\n旧优先级：P1',
                stageId: 'STRATEGY',
            }),
            expect.objectContaining({
                id: 'run-123-STRATEGY-v3',
                content: '# 测试策略蓝图\n\n服务端保存后的 P0 优先级',
                stageId: 'STRATEGY',
            }),
        ]);
    });

    it('keeps the draft open and does not mutate artifacts when server save fails', async () => {
        vi.mocked(updateRunArtifact).mockRejectedValue(new Error('Failed to update run artifact: 500'));
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 1,
            currentRunId: 'run-123',
            artifactContent: '# 测试策略蓝图\n\n旧优先级：P1',
            stageArtifacts: {
                STRATEGY: '# 测试策略蓝图\n\n旧优先级：P1',
            },
            artifactHistory: [],
        });

        render(<ArtifactPane />);
        fireEvent.click(screen.getByTitle('编辑产出物'));
        fireEvent.change(screen.getByLabelText('编辑产出物 Markdown'), {
            target: { value: '# 测试策略蓝图\n\n新优先级：P0' },
        });
        fireEvent.click(screen.getByRole('button', { name: '保存修改' }));

        await waitFor(() => {
            expect(screen.getByText('保存失败：Failed to update run artifact: 500')).toBeTruthy();
        });

        const state = useStore.getState();
        expect(state.artifactContent).toBe('# 测试策略蓝图\n\n旧优先级：P1');
        expect(state.stageArtifacts.STRATEGY).toBe('# 测试策略蓝图\n\n旧优先级：P1');
        expect(state.artifactHistory).toEqual([]);
        expect(screen.getByLabelText('编辑产出物 Markdown')).toBeTruthy();
    });

    it('shows an artifact conflict without overwriting the current artifact', async () => {
        vi.mocked(updateRunArtifact).mockRejectedValue(new ArtifactConflictError(
            '产出物已被更新，请刷新后再保存',
            {
                stageId: 'STRATEGY',
                content: '# 测试策略蓝图\n\n服务端较新版本',
                versionNumber: 3,
            },
        ));
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 1,
            currentRunId: 'run-123',
            artifactContent: '# 测试策略蓝图\n\n版本 2',
            stageArtifacts: {
                STRATEGY: '# 测试策略蓝图\n\n版本 2',
            },
            artifactHistory: [
                {
                    id: 'run-123-STRATEGY-v2',
                    timestamp: 123,
                    content: '# 测试策略蓝图\n\n版本 2',
                    stageId: 'STRATEGY',
                },
            ],
        });

        render(<ArtifactPane />);
        fireEvent.click(screen.getByTitle('编辑产出物'));
        fireEvent.change(screen.getByLabelText('编辑产出物 Markdown'), {
            target: { value: '# 测试策略蓝图\n\n基于旧版本的修改' },
        });
        fireEvent.click(screen.getByRole('button', { name: '保存修改' }));

        await waitFor(() => {
            expect(updateRunArtifact).toHaveBeenCalledWith(
                'run-123',
                'STRATEGY',
                '# 测试策略蓝图\n\n基于旧版本的修改',
                { expectedVersionNumber: 2 },
            );
        });
        expect(await screen.findByText('保存冲突：产出物已被更新，请刷新后再保存')).toBeTruthy();
        expect(screen.getByText('服务端当前版本：v3')).toBeTruthy();

        const state = useStore.getState();
        expect(state.artifactContent).toBe('# 测试策略蓝图\n\n版本 2');
        expect(state.stageArtifacts.STRATEGY).toBe('# 测试策略蓝图\n\n版本 2');
        expect(state.artifactHistory).toEqual([
            expect.objectContaining({
                id: 'run-123-STRATEGY-v2',
                content: '# 测试策略蓝图\n\n版本 2',
            }),
        ]);
        expect(screen.getByLabelText('编辑产出物 Markdown')).toBeTruthy();
    });

    it('shows a conflict diff between the server version and the draft', async () => {
        vi.mocked(updateRunArtifact).mockRejectedValue(new ArtifactConflictError(
            '产出物已被更新，请刷新后再保存',
            {
                stageId: 'STRATEGY',
                content: '# 测试策略蓝图\n\n服务端较新版本\n共同内容',
                versionNumber: 3,
            },
        ));
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 1,
            currentRunId: 'run-123',
            artifactContent: '# 测试策略蓝图\n\n版本 2\n共同内容',
            stageArtifacts: {
                STRATEGY: '# 测试策略蓝图\n\n版本 2\n共同内容',
            },
            artifactHistory: [
                {
                    id: 'run-123-STRATEGY-v2',
                    timestamp: 123,
                    content: '# 测试策略蓝图\n\n版本 2\n共同内容',
                    stageId: 'STRATEGY',
                },
            ],
            artifactAuditEvents: [],
        });

        render(<ArtifactPane />);
        fireEvent.click(screen.getByTitle('编辑产出物'));
        fireEvent.change(screen.getByLabelText('编辑产出物 Markdown'), {
            target: { value: '# 测试策略蓝图\n\n用户草稿版本\n共同内容' },
        });
        fireEvent.click(screen.getByRole('button', { name: '保存修改' }));
        fireEvent.click(await screen.findByRole('button', { name: '对比服务端版本' }));

        expect(screen.getByText('服务端版本 vs 你的草稿')).toBeTruthy();
        expect(screen.getByText('- 服务端较新版本')).toBeTruthy();
        expect(screen.getByText('+ 用户草稿版本')).toBeTruthy();
        expect(screen.getByText('共同内容')).toBeTruthy();
    });

    it('discards a draft-only line from the artifact conflict diff', async () => {
        vi.mocked(updateRunArtifact).mockRejectedValue(new ArtifactConflictError(
            '产出物已被更新，请刷新后再保存',
            {
                stageId: 'STRATEGY',
                content: '# 测试策略蓝图\n\n服务端较新版本\n共同内容',
                versionNumber: 3,
            },
        ));
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 1,
            currentRunId: 'run-123',
            artifactContent: '# 测试策略蓝图\n\n版本 2\n共同内容',
            stageArtifacts: {
                STRATEGY: '# 测试策略蓝图\n\n版本 2\n共同内容',
            },
            artifactHistory: [
                {
                    id: 'run-123-STRATEGY-v2',
                    timestamp: 123,
                    content: '# 测试策略蓝图\n\n版本 2\n共同内容',
                    stageId: 'STRATEGY',
                },
            ],
        });

        render(<ArtifactPane />);
        fireEvent.click(screen.getByTitle('编辑产出物'));
        fireEvent.change(screen.getByLabelText('编辑产出物 Markdown'), {
            target: { value: '# 测试策略蓝图\n\n用户草稿版本\n共同内容' },
        });
        fireEvent.click(screen.getByRole('button', { name: '保存修改' }));
        fireEvent.click(await screen.findByRole('button', { name: '对比服务端版本' }));
        fireEvent.click(screen.getByRole('button', { name: '丢弃此行：用户草稿版本' }));

        expect((screen.getByLabelText('编辑产出物 Markdown') as HTMLTextAreaElement).value).toBe(
            '# 测试策略蓝图\n\n共同内容'
        );
        expect(screen.queryByText('+ 用户草稿版本')).toBeNull();
        expect(useStore.getState().artifactAuditEvents).toEqual([
            expect.objectContaining({
                stageId: 'STRATEGY',
                eventType: 'artifact_merge_line_discarded',
                summary: '合并轨迹：丢弃草稿行「用户草稿版本」',
            }),
        ]);
    });

    it('discards a contiguous draft-only block from the artifact conflict diff', async () => {
        vi.mocked(updateRunArtifact).mockRejectedValue(new ArtifactConflictError(
            '产出物已被更新，请刷新后再保存',
            {
                stageId: 'STRATEGY',
                content: '# 测试策略蓝图\n\n服务端较新版本\n共同内容',
                versionNumber: 3,
            },
        ));
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 1,
            currentRunId: 'run-123',
            artifactContent: '# 测试策略蓝图\n\n版本 2\n共同内容',
            stageArtifacts: {
                STRATEGY: '# 测试策略蓝图\n\n版本 2\n共同内容',
            },
            artifactHistory: [
                {
                    id: 'run-123-STRATEGY-v2',
                    timestamp: 123,
                    content: '# 测试策略蓝图\n\n版本 2\n共同内容',
                    stageId: 'STRATEGY',
                },
            ],
            artifactAuditEvents: [],
        });

        render(<ArtifactPane />);
        fireEvent.click(screen.getByTitle('编辑产出物'));
        fireEvent.change(screen.getByLabelText('编辑产出物 Markdown'), {
            target: { value: '# 测试策略蓝图\n\n用户新增风险\n用户新增验收口径\n共同内容' },
        });
        fireEvent.click(screen.getByRole('button', { name: '保存修改' }));
        fireEvent.click(await screen.findByRole('button', { name: '对比服务端版本' }));
        fireEvent.click(screen.getByRole('button', { name: '丢弃变更块：用户新增风险 / 用户新增验收口径' }));

        expect((screen.getByLabelText('编辑产出物 Markdown') as HTMLTextAreaElement).value).toBe(
            '# 测试策略蓝图\n\n共同内容'
        );
        expect(screen.queryByText('+ 用户新增风险')).toBeNull();
        expect(screen.queryByText('+ 用户新增验收口径')).toBeNull();
        expect(useStore.getState().artifactAuditEvents).toEqual([
            expect.objectContaining({
                stageId: 'STRATEGY',
                eventType: 'artifact_merge_block_discarded',
                summary: '合并轨迹：丢弃草稿变更块「用户新增风险 / 用户新增验收口径」',
            }),
        ]);
    });

    it('restores a contiguous server-only block into the artifact conflict draft', async () => {
        vi.mocked(updateRunArtifact).mockRejectedValue(new ArtifactConflictError(
            '产出物已被更新，请刷新后再保存',
            {
                stageId: 'STRATEGY',
                content: '# 测试策略蓝图\n\n服务端保留风险\n服务端保留验收口径\n共同内容',
                versionNumber: 3,
            },
        ));
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 1,
            currentRunId: 'run-123',
            artifactContent: '# 测试策略蓝图\n\n服务端保留风险\n服务端保留验收口径\n共同内容',
            stageArtifacts: {
                STRATEGY: '# 测试策略蓝图\n\n服务端保留风险\n服务端保留验收口径\n共同内容',
            },
            artifactHistory: [
                {
                    id: 'run-123-STRATEGY-v2',
                    timestamp: 123,
                    content: '# 测试策略蓝图\n\n服务端保留风险\n服务端保留验收口径\n共同内容',
                    stageId: 'STRATEGY',
                },
            ],
            artifactAuditEvents: [],
        });

        render(<ArtifactPane />);
        fireEvent.click(screen.getByTitle('编辑产出物'));
        fireEvent.change(screen.getByLabelText('编辑产出物 Markdown'), {
            target: { value: '# 测试策略蓝图\n\n共同内容' },
        });
        fireEvent.click(screen.getByRole('button', { name: '保存修改' }));
        fireEvent.click(await screen.findByRole('button', { name: '对比服务端版本' }));
        fireEvent.click(screen.getByRole('button', { name: '恢复服务端变更块：服务端保留风险 / 服务端保留验收口径' }));

        expect((screen.getByLabelText('编辑产出物 Markdown') as HTMLTextAreaElement).value).toBe(
            '# 测试策略蓝图\n\n服务端保留风险\n服务端保留验收口径\n共同内容'
        );
        expect(useStore.getState().artifactAuditEvents).toEqual([
            expect.objectContaining({
                stageId: 'STRATEGY',
                eventType: 'artifact_merge_block_server_restored',
                summary: '合并轨迹：恢复服务端删除块「服务端保留风险 / 服务端保留验收口径」',
            }),
        ]);
    });

    it('accepts a draft-only line into a server-based conflict draft', async () => {
        vi.mocked(updateRunArtifact).mockRejectedValue(new ArtifactConflictError(
            '产出物已被更新，请刷新后再保存',
            {
                stageId: 'STRATEGY',
                content: '# 测试策略蓝图\n\n服务端较新版本\n共同内容',
                versionNumber: 3,
            },
        ));
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 1,
            currentRunId: 'run-123',
            artifactContent: '# 测试策略蓝图\n\n版本 2\n共同内容',
            stageArtifacts: {
                STRATEGY: '# 测试策略蓝图\n\n版本 2\n共同内容',
            },
            artifactHistory: [
                {
                    id: 'run-123-STRATEGY-v2',
                    timestamp: 123,
                    content: '# 测试策略蓝图\n\n版本 2\n共同内容',
                    stageId: 'STRATEGY',
                },
            ],
        });

        render(<ArtifactPane />);
        fireEvent.click(screen.getByTitle('编辑产出物'));
        fireEvent.change(screen.getByLabelText('编辑产出物 Markdown'), {
            target: { value: '# 测试策略蓝图\n\n用户补充风险\n共同内容' },
        });
        fireEvent.click(screen.getByRole('button', { name: '保存修改' }));
        fireEvent.click(await screen.findByRole('button', { name: '对比服务端版本' }));
        fireEvent.click(screen.getByRole('button', { name: '采纳到草稿：用户补充风险' }));

        expect((screen.getByLabelText('编辑产出物 Markdown') as HTMLTextAreaElement).value).toBe(
            '# 测试策略蓝图\n\n服务端较新版本\n共同内容\n用户补充风险'
        );
        expect(screen.getByText('服务端较新版本')).toBeTruthy();
        expect(screen.getByText('+ 用户补充风险')).toBeTruthy();
    });

    it('accepts a contiguous draft-only block into a server-based conflict draft', async () => {
        vi.mocked(updateRunArtifact).mockRejectedValue(new ArtifactConflictError(
            '产出物已被更新，请刷新后再保存',
            {
                stageId: 'STRATEGY',
                content: '# 测试策略蓝图\n\n服务端较新版本\n共同内容',
                versionNumber: 3,
            },
        ));
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 1,
            currentRunId: 'run-123',
            artifactContent: '# 测试策略蓝图\n\n版本 2\n共同内容',
            stageArtifacts: {
                STRATEGY: '# 测试策略蓝图\n\n版本 2\n共同内容',
            },
            artifactHistory: [
                {
                    id: 'run-123-STRATEGY-v2',
                    timestamp: 123,
                    content: '# 测试策略蓝图\n\n版本 2\n共同内容',
                    stageId: 'STRATEGY',
                },
            ],
            artifactAuditEvents: [],
        });

        render(<ArtifactPane />);
        fireEvent.click(screen.getByTitle('编辑产出物'));
        fireEvent.change(screen.getByLabelText('编辑产出物 Markdown'), {
            target: { value: '# 测试策略蓝图\n\n用户新增风险\n用户新增验收口径\n共同内容' },
        });
        fireEvent.click(screen.getByRole('button', { name: '保存修改' }));
        fireEvent.click(await screen.findByRole('button', { name: '对比服务端版本' }));
        fireEvent.click(screen.getByRole('button', { name: '采纳变更块：用户新增风险 / 用户新增验收口径' }));

        expect((screen.getByLabelText('编辑产出物 Markdown') as HTMLTextAreaElement).value).toBe(
            '# 测试策略蓝图\n\n服务端较新版本\n共同内容\n用户新增风险\n用户新增验收口径'
        );
        expect(useStore.getState().artifactAuditEvents).toEqual([
            expect.objectContaining({
                stageId: 'STRATEGY',
                eventType: 'artifact_merge_block_accepted',
                summary: '合并轨迹：采纳草稿变更块「用户新增风险 / 用户新增验收口径」',
            }),
        ]);
    });

    it('accepts a modified conflict block in place while preserving server-only changes', async () => {
        vi.mocked(updateRunArtifact).mockRejectedValue(new ArtifactConflictError(
            '产出物已被更新，请刷新后再保存',
            {
                stageId: 'STRATEGY',
                content: '# 测试策略蓝图\n\n背景\n服务端目标：稳定性\n服务端验收：A\n共同内容\n服务端后置补充',
                versionNumber: 3,
            },
        ));
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 1,
            currentRunId: 'run-123',
            artifactContent: '# 测试策略蓝图\n\n背景\n旧目标\n旧验收\n共同内容',
            stageArtifacts: {
                STRATEGY: '# 测试策略蓝图\n\n背景\n旧目标\n旧验收\n共同内容',
            },
            artifactHistory: [
                {
                    id: 'run-123-STRATEGY-v2',
                    timestamp: 123,
                    content: '# 测试策略蓝图\n\n背景\n旧目标\n旧验收\n共同内容',
                    stageId: 'STRATEGY',
                },
            ],
            artifactAuditEvents: [],
        });

        render(<ArtifactPane />);
        fireEvent.click(screen.getByTitle('编辑产出物'));
        fireEvent.change(screen.getByLabelText('编辑产出物 Markdown'), {
            target: { value: '# 测试策略蓝图\n\n背景\n用户目标：性能\n用户验收：B\n共同内容' },
        });
        fireEvent.click(screen.getByRole('button', { name: '保存修改' }));
        fireEvent.click(await screen.findByRole('button', { name: '对比服务端版本' }));
        fireEvent.click(screen.getByRole('button', {
            name: '采纳修改块：服务端目标：稳定性 / 服务端验收：A → 用户目标：性能 / 用户验收：B',
        }));

        expect((screen.getByLabelText('编辑产出物 Markdown') as HTMLTextAreaElement).value).toBe(
            '# 测试策略蓝图\n\n背景\n用户目标：性能\n用户验收：B\n共同内容\n服务端后置补充'
        );
        expect(useStore.getState().artifactAuditEvents).toEqual([
            expect.objectContaining({
                stageId: 'STRATEGY',
                eventType: 'artifact_merge_block_modified_accepted',
                summary: '合并轨迹：采纳草稿修改块「服务端目标：稳定性 / 服务端验收：A → 用户目标：性能 / 用户验收：B」',
            }),
        ]);
    });

    it('keeps a server modified conflict block and records the merge decision', async () => {
        vi.mocked(updateRunArtifact).mockRejectedValue(new ArtifactConflictError(
            '产出物已被更新，请刷新后再保存',
            {
                stageId: 'STRATEGY',
                content: '# 测试策略蓝图\n\n背景\n服务端目标：稳定性\n服务端验收：A\n共同内容\n服务端后置补充',
                versionNumber: 3,
            },
        ));
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 1,
            currentRunId: 'run-123',
            artifactContent: '# 测试策略蓝图\n\n背景\n旧目标\n旧验收\n共同内容',
            stageArtifacts: {
                STRATEGY: '# 测试策略蓝图\n\n背景\n旧目标\n旧验收\n共同内容',
            },
            artifactHistory: [
                {
                    id: 'run-123-STRATEGY-v2',
                    timestamp: 123,
                    content: '# 测试策略蓝图\n\n背景\n旧目标\n旧验收\n共同内容',
                    stageId: 'STRATEGY',
                },
            ],
            artifactAuditEvents: [],
        });

        render(<ArtifactPane />);
        fireEvent.click(screen.getByTitle('编辑产出物'));
        fireEvent.change(screen.getByLabelText('编辑产出物 Markdown'), {
            target: { value: '# 测试策略蓝图\n\n背景\n用户目标：性能\n用户验收：B\n共同内容' },
        });
        fireEvent.click(screen.getByRole('button', { name: '保存修改' }));
        fireEvent.click(await screen.findByRole('button', { name: '对比服务端版本' }));
        fireEvent.click(screen.getByRole('button', {
            name: '保留服务端修改块：服务端目标：稳定性 / 服务端验收：A → 用户目标：性能 / 用户验收：B',
        }));

        expect((screen.getByLabelText('编辑产出物 Markdown') as HTMLTextAreaElement).value).toBe(
            '# 测试策略蓝图\n\n背景\n服务端目标：稳定性\n服务端验收：A\n共同内容\n服务端后置补充'
        );
        expect(useStore.getState().artifactAuditEvents).toEqual([
            expect.objectContaining({
                stageId: 'STRATEGY',
                eventType: 'artifact_merge_block_modified_kept',
                summary: '合并轨迹：保留服务端修改块「服务端目标：稳定性 / 服务端验收：A → 用户目标：性能 / 用户验收：B」',
            }),
        ]);
    });

    it('auto-merges non-overlapping server and draft insertions during an artifact conflict', async () => {
        vi.mocked(updateRunArtifact).mockRejectedValue(new ArtifactConflictError(
            '产出物已被更新，请刷新后再保存',
            {
                stageId: 'STRATEGY',
                content: '# 测试策略蓝图\n\n背景\n服务端新增风险\n共同内容\n服务端后置补充',
                versionNumber: 3,
            },
        ));
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 1,
            currentRunId: 'run-123',
            artifactContent: '# 测试策略蓝图\n\n背景\n共同内容',
            stageArtifacts: {
                STRATEGY: '# 测试策略蓝图\n\n背景\n共同内容',
            },
            artifactHistory: [
                {
                    id: 'run-123-STRATEGY-v2',
                    timestamp: 123,
                    content: '# 测试策略蓝图\n\n背景\n共同内容',
                    stageId: 'STRATEGY',
                },
            ],
            artifactAuditEvents: [],
        });

        render(<ArtifactPane />);
        fireEvent.click(screen.getByTitle('编辑产出物'));
        fireEvent.change(screen.getByLabelText('编辑产出物 Markdown'), {
            target: { value: '# 测试策略蓝图\n\n背景\n用户新增验收\n共同内容' },
        });
        fireEvent.click(screen.getByRole('button', { name: '保存修改' }));
        fireEvent.click(await screen.findByRole('button', { name: '自动合并非重叠变更' }));

        expect((screen.getByLabelText('编辑产出物 Markdown') as HTMLTextAreaElement).value).toBe(
            '# 测试策略蓝图\n\n背景\n服务端新增风险\n用户新增验收\n共同内容\n服务端后置补充'
        );
        expect(useStore.getState().artifactAuditEvents).toEqual([
            expect.objectContaining({
                stageId: 'STRATEGY',
                eventType: 'artifact_auto_merge_applied',
                summary: '合并轨迹：自动合并服务端与草稿的非重叠补充',
            }),
        ]);
    });

    it('auto-merges server insertions with draft deletions during an artifact conflict', async () => {
        vi.mocked(updateRunArtifact).mockRejectedValue(new ArtifactConflictError(
            '产出物已被更新，请刷新后再保存',
            {
                stageId: 'STRATEGY',
                content: '# 测试策略蓝图\n\n背景\n服务端补充\n旧风险\n共同内容\n服务端后置补充',
                versionNumber: 3,
            },
        ));
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 1,
            currentRunId: 'run-123',
            artifactContent: '# 测试策略蓝图\n\n背景\n旧风险\n共同内容',
            stageArtifacts: {
                STRATEGY: '# 测试策略蓝图\n\n背景\n旧风险\n共同内容',
            },
            artifactHistory: [
                {
                    id: 'run-123-STRATEGY-v2',
                    timestamp: 123,
                    content: '# 测试策略蓝图\n\n背景\n旧风险\n共同内容',
                    stageId: 'STRATEGY',
                },
            ],
            artifactAuditEvents: [],
        });

        render(<ArtifactPane />);
        fireEvent.click(screen.getByTitle('编辑产出物'));
        fireEvent.change(screen.getByLabelText('编辑产出物 Markdown'), {
            target: { value: '# 测试策略蓝图\n\n背景\n用户补充\n共同内容' },
        });
        fireEvent.click(screen.getByRole('button', { name: '保存修改' }));
        fireEvent.click(await screen.findByRole('button', { name: '自动合并非重叠变更' }));

        expect((screen.getByLabelText('编辑产出物 Markdown') as HTMLTextAreaElement).value).toBe(
            '# 测试策略蓝图\n\n背景\n服务端补充\n用户补充\n共同内容\n服务端后置补充'
        );
        expect(useStore.getState().artifactAuditEvents).toEqual([
            expect.objectContaining({
                stageId: 'STRATEGY',
                eventType: 'artifact_auto_merge_applied',
                summary: '合并轨迹：自动合并服务端与草稿的非重叠补充',
            }),
        ]);
    });

    it('auto-merges non-overlapping section rewrites during an artifact conflict', async () => {
        vi.mocked(updateRunArtifact).mockRejectedValue(new ArtifactConflictError(
            '产出物已被更新，请刷新后再保存',
            {
                stageId: 'STRATEGY',
                content: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '服务端风险策略：优先覆盖支付链路',
                    '',
                    '## 验收口径',
                    '旧验收口径',
                ].join('\n'),
                versionNumber: 3,
            },
        ));
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 1,
            currentRunId: 'run-123',
            artifactContent: [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '旧风险策略',
                '',
                '## 验收口径',
                '旧验收口径',
            ].join('\n'),
            stageArtifacts: {
                STRATEGY: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '旧风险策略',
                    '',
                    '## 验收口径',
                    '旧验收口径',
                ].join('\n'),
            },
            artifactHistory: [
                {
                    id: 'run-123-STRATEGY-v2',
                    timestamp: 123,
                    content: [
                        '# 测试策略蓝图',
                        '',
                        '## 风险策略',
                        '旧风险策略',
                        '',
                        '## 验收口径',
                        '旧验收口径',
                    ].join('\n'),
                    stageId: 'STRATEGY',
                },
            ],
            artifactAuditEvents: [],
        });

        render(<ArtifactPane />);
        fireEvent.click(screen.getByTitle('编辑产出物'));
        fireEvent.change(screen.getByLabelText('编辑产出物 Markdown'), {
            target: {
                value: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '旧风险策略',
                    '',
                    '## 验收口径',
                    '用户验收口径：增加异常回滚检查',
                ].join('\n'),
            },
        });
        fireEvent.click(screen.getByRole('button', { name: '保存修改' }));
        fireEvent.click(await screen.findByRole('button', { name: '自动合并非重叠变更' }));

        expect((screen.getByLabelText('编辑产出物 Markdown') as HTMLTextAreaElement).value).toBe([
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            '服务端风险策略：优先覆盖支付链路',
            '',
            '## 验收口径',
            '用户验收口径：增加异常回滚检查',
        ].join('\n'));
        expect(useStore.getState().artifactAuditEvents).toEqual([
            expect.objectContaining({
                stageId: 'STRATEGY',
                eventType: 'artifact_auto_merge_applied',
                summary: '合并轨迹：自动合并服务端与草稿的非重叠章节改写',
            }),
        ]);
    });

    it('does not auto-merge section rewrites when both sides changed the same section', async () => {
        vi.mocked(updateRunArtifact).mockRejectedValue(new ArtifactConflictError(
            '产出物已被更新，请刷新后再保存',
            {
                stageId: 'STRATEGY',
                content: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '服务端风险策略：优先覆盖支付链路',
                    '',
                    '## 验收口径',
                    '旧验收口径',
                ].join('\n'),
                versionNumber: 3,
            },
        ));
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 1,
            currentRunId: 'run-123',
            artifactContent: [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '旧风险策略',
                '',
                '## 验收口径',
                '旧验收口径',
            ].join('\n'),
            stageArtifacts: {
                STRATEGY: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '旧风险策略',
                    '',
                    '## 验收口径',
                    '旧验收口径',
                ].join('\n'),
            },
            artifactHistory: [
                {
                    id: 'run-123-STRATEGY-v2',
                    timestamp: 123,
                    content: [
                        '# 测试策略蓝图',
                        '',
                        '## 风险策略',
                        '旧风险策略',
                        '',
                        '## 验收口径',
                        '旧验收口径',
                    ].join('\n'),
                    stageId: 'STRATEGY',
                },
            ],
            artifactAuditEvents: [],
        });

        render(<ArtifactPane />);
        fireEvent.click(screen.getByTitle('编辑产出物'));
        fireEvent.change(screen.getByLabelText('编辑产出物 Markdown'), {
            target: {
                value: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '用户风险策略：优先覆盖退款链路',
                    '',
                    '## 验收口径',
                    '旧验收口径',
                ].join('\n'),
            },
        });
        fireEvent.click(screen.getByRole('button', { name: '保存修改' }));

        await screen.findByRole('button', { name: '对比服务端版本' });
        expect(screen.queryByRole('button', { name: '自动合并非重叠变更' })).toBeNull();
    });

    it('auto-merges non-overlapping paragraph rewrites inside the same section', async () => {
        vi.mocked(updateRunArtifact).mockRejectedValue(new ArtifactConflictError(
            '产出物已被更新，请刷新后再保存',
            {
                stageId: 'STRATEGY',
                content: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '段落A：服务端补充支付链路观测点。',
                    '',
                    '段落B：覆盖退款逆向链路。',
                    '',
                    '段落C：覆盖风控拦截链路。',
                ].join('\n'),
                versionNumber: 3,
            },
        ));
        const baseContent = [
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            '段落A：覆盖支付主链路。',
            '',
            '段落B：覆盖退款逆向链路。',
            '',
            '段落C：覆盖风控拦截链路。',
        ].join('\n');
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 1,
            currentRunId: 'run-123',
            artifactContent: baseContent,
            stageArtifacts: {
                STRATEGY: baseContent,
            },
            artifactHistory: [
                {
                    id: 'run-123-STRATEGY-v2',
                    timestamp: 123,
                    content: baseContent,
                    stageId: 'STRATEGY',
                },
            ],
            artifactAuditEvents: [],
        });

        render(<ArtifactPane />);
        fireEvent.click(screen.getByTitle('编辑产出物'));
        fireEvent.change(screen.getByLabelText('编辑产出物 Markdown'), {
            target: {
                value: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '段落A：覆盖支付主链路。',
                    '',
                    '段落B：用户补充退款失败后的人工复核。',
                    '',
                    '段落C：覆盖风控拦截链路。',
                ].join('\n'),
            },
        });
        fireEvent.click(screen.getByRole('button', { name: '保存修改' }));
        fireEvent.click(await screen.findByRole('button', { name: '自动合并非重叠变更' }));

        expect((screen.getByLabelText('编辑产出物 Markdown') as HTMLTextAreaElement).value).toBe([
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            '段落A：服务端补充支付链路观测点。',
            '',
            '段落B：用户补充退款失败后的人工复核。',
            '',
            '段落C：覆盖风控拦截链路。',
        ].join('\n'));
        expect(useStore.getState().artifactAuditEvents).toEqual([
            expect.objectContaining({
                stageId: 'STRATEGY',
                eventType: 'artifact_auto_merge_applied',
                summary: '合并轨迹：自动合并服务端与草稿的同章节非重叠段落改写',
            }),
        ]);
    });

    it('does not auto-merge same-section paragraph rewrites when both sides changed the same paragraph', async () => {
        vi.mocked(updateRunArtifact).mockRejectedValue(new ArtifactConflictError(
            '产出物已被更新，请刷新后再保存',
            {
                stageId: 'STRATEGY',
                content: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '段落A：服务端补充支付链路观测点。',
                    '',
                    '段落B：覆盖退款逆向链路。',
                ].join('\n'),
                versionNumber: 3,
            },
        ));
        const baseContent = [
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            '段落A：覆盖支付主链路。',
            '',
            '段落B：覆盖退款逆向链路。',
        ].join('\n');
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 1,
            currentRunId: 'run-123',
            artifactContent: baseContent,
            stageArtifacts: {
                STRATEGY: baseContent,
            },
            artifactHistory: [
                {
                    id: 'run-123-STRATEGY-v2',
                    timestamp: 123,
                    content: baseContent,
                    stageId: 'STRATEGY',
                },
            ],
            artifactAuditEvents: [],
        });

        render(<ArtifactPane />);
        fireEvent.click(screen.getByTitle('编辑产出物'));
        fireEvent.change(screen.getByLabelText('编辑产出物 Markdown'), {
            target: {
                value: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '段落A：用户补充支付链路异常回滚。',
                    '',
                    '段落B：覆盖退款逆向链路。',
                ].join('\n'),
            },
        });
        fireEvent.click(screen.getByRole('button', { name: '保存修改' }));

        await screen.findByRole('button', { name: '对比服务端版本' });
        expect(screen.queryByRole('button', { name: '自动合并非重叠变更' })).toBeNull();
    });

    it('does not auto-merge same-section paragraph rewrites when another base paragraph moved position', async () => {
        vi.mocked(updateRunArtifact).mockRejectedValue(new ArtifactConflictError(
            '产出物已被更新，请刷新后再保存',
            {
                stageId: 'STRATEGY',
                content: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '段落B：覆盖退款逆向链路。',
                    '',
                    '段落A：覆盖支付主链路。',
                    '',
                    '段落C：覆盖风控拦截链路。',
                ].join('\n'),
                versionNumber: 3,
            },
        ));
        const baseContent = [
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            '段落A：覆盖支付主链路。',
            '',
            '段落B：覆盖退款逆向链路。',
            '',
            '段落C：覆盖风控拦截链路。',
        ].join('\n');
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 1,
            currentRunId: 'run-123',
            artifactContent: baseContent,
            stageArtifacts: {
                STRATEGY: baseContent,
            },
            artifactHistory: [
                {
                    id: 'run-123-STRATEGY-v2',
                    timestamp: 123,
                    content: baseContent,
                    stageId: 'STRATEGY',
                },
            ],
            artifactAuditEvents: [],
        });

        render(<ArtifactPane />);
        fireEvent.click(screen.getByTitle('编辑产出物'));
        fireEvent.change(screen.getByLabelText('编辑产出物 Markdown'), {
            target: {
                value: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '段落A：覆盖支付主链路。',
                    '',
                    '段落B：覆盖退款逆向链路。',
                    '',
                    '段落C：用户补充风控拦截后的复核策略。',
                ].join('\n'),
            },
        });
        fireEvent.click(screen.getByRole('button', { name: '保存修改' }));

        await screen.findByRole('button', { name: '对比服务端版本' });
        expect(screen.queryByRole('button', { name: '自动合并非重叠变更' })).toBeNull();
    });

    it('auto-merges same-section paragraph deletion with a non-overlapping paragraph rewrite', async () => {
        vi.mocked(updateRunArtifact).mockRejectedValue(new ArtifactConflictError(
            '产出物已被更新，请刷新后再保存',
            {
                stageId: 'STRATEGY',
                content: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '段落A：覆盖支付主链路。',
                    '',
                    '段落C：覆盖风控拦截链路。',
                ].join('\n'),
                versionNumber: 3,
            },
        ));
        const baseContent = [
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            '段落A：覆盖支付主链路。',
            '',
            '段落B：覆盖退款逆向链路。',
            '',
            '段落C：覆盖风控拦截链路。',
        ].join('\n');
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 1,
            currentRunId: 'run-123',
            artifactContent: baseContent,
            stageArtifacts: {
                STRATEGY: baseContent,
            },
            artifactHistory: [
                {
                    id: 'run-123-STRATEGY-v2',
                    timestamp: 123,
                    content: baseContent,
                    stageId: 'STRATEGY',
                },
            ],
            artifactAuditEvents: [],
        });

        render(<ArtifactPane />);
        fireEvent.click(screen.getByTitle('编辑产出物'));
        fireEvent.change(screen.getByLabelText('编辑产出物 Markdown'), {
            target: {
                value: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '段落A：覆盖支付主链路。',
                    '',
                    '段落B：覆盖退款逆向链路。',
                    '',
                    '段落C：用户补充风控拦截后的复核策略。',
                ].join('\n'),
            },
        });
        fireEvent.click(screen.getByRole('button', { name: '保存修改' }));
        fireEvent.click(await screen.findByRole('button', { name: '自动合并非重叠变更' }));

        expect((screen.getByLabelText('编辑产出物 Markdown') as HTMLTextAreaElement).value).toBe([
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            '段落A：覆盖支付主链路。',
            '',
            '段落C：用户补充风控拦截后的复核策略。',
        ].join('\n'));
        expect(useStore.getState().artifactAuditEvents).toEqual([
            expect.objectContaining({
                stageId: 'STRATEGY',
                eventType: 'artifact_auto_merge_applied',
                summary: '合并轨迹：自动合并服务端与草稿的同章节非重叠段落删除与改写',
            }),
        ]);
    });

    it('auto-merges same-section paragraph insertion with a non-overlapping server paragraph rewrite', async () => {
        vi.mocked(updateRunArtifact).mockRejectedValue(new ArtifactConflictError(
            '产出物已被更新，请刷新后再保存',
            {
                stageId: 'STRATEGY',
                content: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '段落A：覆盖支付主链路。',
                    '',
                    '段落B：服务端补充退款逆向链路观测点。',
                ].join('\n'),
                versionNumber: 3,
            },
        ));
        const baseContent = [
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            '段落A：覆盖支付主链路。',
            '',
            '段落B：覆盖退款逆向链路。',
        ].join('\n');
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 1,
            currentRunId: 'run-123',
            artifactContent: baseContent,
            stageArtifacts: {
                STRATEGY: baseContent,
            },
            artifactHistory: [
                {
                    id: 'run-123-STRATEGY-v2',
                    timestamp: 123,
                    content: baseContent,
                    stageId: 'STRATEGY',
                },
            ],
            artifactAuditEvents: [],
        });

        render(<ArtifactPane />);
        fireEvent.click(screen.getByTitle('编辑产出物'));
        fireEvent.change(screen.getByLabelText('编辑产出物 Markdown'), {
            target: {
                value: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '段落A：覆盖支付主链路。',
                    '',
                    '段落A-补充：用户新增支付失败后的人工复核。',
                    '',
                    '段落B：覆盖退款逆向链路。',
                ].join('\n'),
            },
        });
        fireEvent.click(screen.getByRole('button', { name: '保存修改' }));
        fireEvent.click(await screen.findByRole('button', { name: '自动合并非重叠变更' }));

        expect((screen.getByLabelText('编辑产出物 Markdown') as HTMLTextAreaElement).value).toBe([
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            '段落A：覆盖支付主链路。',
            '',
            '段落A-补充：用户新增支付失败后的人工复核。',
            '',
            '段落B：服务端补充退款逆向链路观测点。',
        ].join('\n'));
        expect(useStore.getState().artifactAuditEvents).toEqual([
            expect.objectContaining({
                stageId: 'STRATEGY',
                eventType: 'artifact_auto_merge_applied',
                summary: '合并轨迹：自动合并服务端与草稿的同章节非重叠段落插入与改写',
            }),
        ]);
    });

    it('auto-merges same-section server paragraph insertion with a draft paragraph rewrite', async () => {
        vi.mocked(updateRunArtifact).mockRejectedValue(new ArtifactConflictError(
            '产出物已被更新，请刷新后再保存',
            {
                stageId: 'STRATEGY',
                content: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '段落A：覆盖支付主链路。',
                    '',
                    '段落A-补充：服务端新增支付失败后的回归策略。',
                    '',
                    '段落B：覆盖退款逆向链路。',
                ].join('\n'),
                versionNumber: 3,
            },
        ));
        const baseContent = [
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            '段落A：覆盖支付主链路。',
            '',
            '段落B：覆盖退款逆向链路。',
        ].join('\n');
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 1,
            currentRunId: 'run-123',
            artifactContent: baseContent,
            stageArtifacts: {
                STRATEGY: baseContent,
            },
            artifactHistory: [
                {
                    id: 'run-123-STRATEGY-v2',
                    timestamp: 123,
                    content: baseContent,
                    stageId: 'STRATEGY',
                },
            ],
            artifactAuditEvents: [],
        });

        render(<ArtifactPane />);
        fireEvent.click(screen.getByTitle('编辑产出物'));
        fireEvent.change(screen.getByLabelText('编辑产出物 Markdown'), {
            target: {
                value: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '段落A：覆盖支付主链路。',
                    '',
                    '段落B：用户补充退款失败后的人工复核。',
                ].join('\n'),
            },
        });
        fireEvent.click(screen.getByRole('button', { name: '保存修改' }));
        fireEvent.click(await screen.findByRole('button', { name: '自动合并非重叠变更' }));

        expect((screen.getByLabelText('编辑产出物 Markdown') as HTMLTextAreaElement).value).toBe([
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            '段落A：覆盖支付主链路。',
            '',
            '段落A-补充：服务端新增支付失败后的回归策略。',
            '',
            '段落B：用户补充退款失败后的人工复核。',
        ].join('\n'));
        expect(useStore.getState().artifactAuditEvents).toEqual([
            expect.objectContaining({
                stageId: 'STRATEGY',
                eventType: 'artifact_auto_merge_applied',
                summary: '合并轨迹：自动合并服务端与草稿的同章节非重叠段落插入与改写',
            }),
        ]);
    });

    it('does not auto-merge same-section paragraph insertion when the rewrite side changes multiple paragraphs', async () => {
        vi.mocked(updateRunArtifact).mockRejectedValue(new ArtifactConflictError(
            '产出物已被更新，请刷新后再保存',
            {
                stageId: 'STRATEGY',
                content: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '段落A：覆盖支付主链路。',
                    '',
                    '段落A-补充：服务端新增支付失败后的回归策略。',
                    '',
                    '段落B：覆盖退款逆向链路。',
                ].join('\n'),
                versionNumber: 3,
            },
        ));
        const baseContent = [
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            '段落A：覆盖支付主链路。',
            '',
            '段落B：覆盖退款逆向链路。',
        ].join('\n');
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 1,
            currentRunId: 'run-123',
            artifactContent: baseContent,
            stageArtifacts: {
                STRATEGY: baseContent,
            },
            artifactHistory: [
                {
                    id: 'run-123-STRATEGY-v2',
                    timestamp: 123,
                    content: baseContent,
                    stageId: 'STRATEGY',
                },
            ],
            artifactAuditEvents: [],
        });

        render(<ArtifactPane />);
        fireEvent.click(screen.getByTitle('编辑产出物'));
        fireEvent.change(screen.getByLabelText('编辑产出物 Markdown'), {
            target: {
                value: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '段落A：用户补充支付失败后的降级策略。',
                    '',
                    '段落B：用户补充退款失败后的人工复核。',
                ].join('\n'),
            },
        });
        fireEvent.click(screen.getByRole('button', { name: '保存修改' }));

        await screen.findByRole('button', { name: '对比服务端版本' });
        expect(screen.queryByRole('button', { name: '自动合并非重叠变更' })).toBeNull();
    });

    it('shows an auto-merge unavailable reason for unsafe paragraph insertion conflicts', async () => {
        vi.mocked(updateRunArtifact).mockRejectedValue(new ArtifactConflictError(
            '产出物已被更新，请刷新后再保存',
            {
                stageId: 'STRATEGY',
                content: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '段落A：覆盖支付主链路。',
                    '',
                    '段落A-补充：服务端新增支付失败后的回归策略。',
                    '',
                    '段落B：覆盖退款逆向链路。',
                ].join('\n'),
                versionNumber: 3,
            },
        ));
        const baseContent = [
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            '段落A：覆盖支付主链路。',
            '',
            '段落B：覆盖退款逆向链路。',
        ].join('\n');
        const draftContent = [
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            '段落A：用户补充支付失败后的降级策略。',
            '',
            '段落B：用户补充退款失败后的人工复核。',
        ].join('\n');
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 1,
            currentRunId: 'run-123',
            artifactContent: baseContent,
            stageArtifacts: {
                STRATEGY: baseContent,
            },
            artifactHistory: [
                {
                    id: 'run-123-STRATEGY-v2',
                    timestamp: 123,
                    content: baseContent,
                    stageId: 'STRATEGY',
                },
            ],
            artifactAuditEvents: [],
        });

        render(<ArtifactPane />);
        fireEvent.click(screen.getByTitle('编辑产出物'));
        fireEvent.change(screen.getByLabelText('编辑产出物 Markdown'), {
            target: {
                value: draftContent,
            },
        });
        fireEvent.click(screen.getByRole('button', { name: '保存修改' }));

        await screen.findByRole('button', { name: '对比服务端版本' });
        expect(screen.queryByRole('button', { name: '自动合并非重叠变更' })).toBeNull();
        expect(screen.getByText('自动合并暂不可用')).not.toBeNull();
        expect(screen.getByText('双方改动涉及同一章节的多处段落，已保留你的草稿，请手工确认后重试保存。')).not.toBeNull();
        expect((screen.getByLabelText('编辑产出物 Markdown') as HTMLTextAreaElement).value).toBe(draftContent);
    });

    it('shows a manual merge reason when overlapping section edits cannot be proven safe', async () => {
        vi.mocked(updateRunArtifact).mockRejectedValue(new ArtifactConflictError(
            '产出物已被更新，请刷新后再保存',
            {
                stageId: 'STRATEGY',
                content: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '段落A：服务端补充支付失败后的回归策略。',
                    '',
                    '段落B：覆盖退款逆向链路。',
                    '',
                    '段落C：服务端新增风控拦截链路。',
                ].join('\n'),
                versionNumber: 3,
            },
        ));
        const baseContent = [
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            '段落A：覆盖支付主链路。',
            '',
            '段落B：覆盖退款逆向链路。',
        ].join('\n');
        const draftContent = [
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            '段落A：用户补充支付失败后的降级策略。',
            '',
            '段落B：用户补充退款失败后的人工复核。',
        ].join('\n');
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 1,
            currentRunId: 'run-123',
            artifactContent: baseContent,
            stageArtifacts: {
                STRATEGY: baseContent,
            },
            artifactHistory: [
                {
                    id: 'run-123-STRATEGY-v2',
                    timestamp: 123,
                    content: baseContent,
                    stageId: 'STRATEGY',
                },
            ],
            artifactAuditEvents: [],
        });

        render(<ArtifactPane />);
        fireEvent.click(screen.getByTitle('编辑产出物'));
        fireEvent.change(screen.getByLabelText('编辑产出物 Markdown'), {
            target: {
                value: draftContent,
            },
        });
        fireEvent.click(screen.getByRole('button', { name: '保存修改' }));

        await screen.findByRole('button', { name: '对比服务端版本' });
        expect(screen.queryByRole('button', { name: '自动合并非重叠变更' })).toBeNull();
        expect(screen.getByText('自动合并暂不可用')).not.toBeNull();
        expect(screen.getByText('双方改动存在重叠或顺序无法证明安全，已保留你的草稿，请打开对比服务端版本后手工确认。')).not.toBeNull();
        expect((screen.getByLabelText('编辑产出物 Markdown') as HTMLTextAreaElement).value).toBe(draftContent);
    });

    it('does not auto-merge same-section paragraph deletion when the deleted paragraph is rewritten', async () => {
        vi.mocked(updateRunArtifact).mockRejectedValue(new ArtifactConflictError(
            '产出物已被更新，请刷新后再保存',
            {
                stageId: 'STRATEGY',
                content: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '段落A：覆盖支付主链路。',
                    '',
                    '段落C：覆盖风控拦截链路。',
                ].join('\n'),
                versionNumber: 3,
            },
        ));
        const baseContent = [
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            '段落A：覆盖支付主链路。',
            '',
            '段落B：覆盖退款逆向链路。',
            '',
            '段落C：覆盖风控拦截链路。',
        ].join('\n');
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 1,
            currentRunId: 'run-123',
            artifactContent: baseContent,
            stageArtifacts: {
                STRATEGY: baseContent,
            },
            artifactHistory: [
                {
                    id: 'run-123-STRATEGY-v2',
                    timestamp: 123,
                    content: baseContent,
                    stageId: 'STRATEGY',
                },
            ],
            artifactAuditEvents: [],
        });

        render(<ArtifactPane />);
        fireEvent.click(screen.getByTitle('编辑产出物'));
        fireEvent.change(screen.getByLabelText('编辑产出物 Markdown'), {
            target: {
                value: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '段落A：覆盖支付主链路。',
                    '',
                    '段落B：用户补充退款失败后的人工复核。',
                    '',
                    '段落C：覆盖风控拦截链路。',
                ].join('\n'),
            },
        });
        fireEvent.click(screen.getByRole('button', { name: '保存修改' }));

        await screen.findByRole('button', { name: '对比服务端版本' });
        expect(screen.queryByRole('button', { name: '自动合并非重叠变更' })).toBeNull();
    });

    it('does not auto-merge same-section paragraph deletion when the rewrite side may have reordered rewritten paragraphs', async () => {
        vi.mocked(updateRunArtifact).mockRejectedValue(new ArtifactConflictError(
            '产出物已被更新，请刷新后再保存',
            {
                stageId: 'STRATEGY',
                content: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '段落A：覆盖支付主链路。',
                    '',
                    '段落B：覆盖退款逆向链路。',
                    '',
                    '段落C：覆盖风控拦截链路。',
                ].join('\n'),
                versionNumber: 3,
            },
        ));
        const baseContent = [
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            '段落A：覆盖支付主链路。',
            '',
            '段落B：覆盖退款逆向链路。',
            '',
            '段落C：覆盖风控拦截链路。',
            '',
            '段落D：覆盖通知补偿链路。',
        ].join('\n');
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 1,
            currentRunId: 'run-123',
            artifactContent: baseContent,
            stageArtifacts: {
                STRATEGY: baseContent,
            },
            artifactHistory: [
                {
                    id: 'run-123-STRATEGY-v2',
                    timestamp: 123,
                    content: baseContent,
                    stageId: 'STRATEGY',
                },
            ],
            artifactAuditEvents: [],
        });

        render(<ArtifactPane />);
        fireEvent.click(screen.getByTitle('编辑产出物'));
        fireEvent.change(screen.getByLabelText('编辑产出物 Markdown'), {
            target: {
                value: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '段落B：用户重写退款逆向链路。',
                    '',
                    '段落C：用户重写风控拦截链路。',
                    '',
                    '段落A：用户重写支付主链路。',
                    '',
                    '段落D：覆盖通知补偿链路。',
                ].join('\n'),
            },
        });
        fireEvent.click(screen.getByRole('button', { name: '保存修改' }));

        await screen.findByRole('button', { name: '对比服务端版本' });
        expect(screen.queryByRole('button', { name: '自动合并非重叠变更' })).toBeNull();
    });

    const baseParagraphMoveContent = [
        '# 测试策略蓝图',
        '',
        '## 风险策略',
        '段落A：覆盖支付主链路。',
        '',
        '段落B：覆盖退款逆向链路。',
        '',
        '段落C：覆盖风控拦截链路。',
        '',
        '## 验收口径',
        '旧验收口径',
    ].join('\n');

    const renderParagraphMoveConflict = (
        serverContent: string,
        draftContent: string,
        baseContent = baseParagraphMoveContent,
    ) => {
        vi.mocked(updateRunArtifact).mockRejectedValue(new ArtifactConflictError(
            '产出物已被更新，请刷新后再保存',
            {
                stageId: 'STRATEGY',
                content: serverContent,
                versionNumber: 3,
            },
        ));
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 1,
            currentRunId: 'run-123',
            artifactContent: baseContent,
            stageArtifacts: {
                STRATEGY: baseContent,
            },
            artifactHistory: [
                {
                    id: 'run-123-STRATEGY-v2',
                    timestamp: 123,
                    content: baseContent,
                    stageId: 'STRATEGY',
                },
            ],
            artifactAuditEvents: [],
        });

        render(<ArtifactPane />);
        fireEvent.click(screen.getByTitle('编辑产出物'));
        fireEvent.change(screen.getByLabelText('编辑产出物 Markdown'), {
            target: {
                value: draftContent,
            },
        });
        fireEvent.click(screen.getByRole('button', { name: '保存修改' }));
    };

    const expectParagraphMovementAutoMerge = async (expectedContent: string) => {
        fireEvent.click(await screen.findByRole('button', { name: '自动合并非重叠变更' }));
        expect((screen.getByLabelText('编辑产出物 Markdown') as HTMLTextAreaElement).value).toBe(expectedContent);
        expect(useStore.getState().artifactAuditEvents).toEqual([
            expect.objectContaining({
                stageId: 'STRATEGY',
                eventType: 'artifact_auto_merge_applied',
                summary: '合并轨迹：自动合并服务端与草稿的非重叠段落移动',
            }),
        ]);
    };

    const expectCrossSectionParagraphMovementAutoMerge = async (expectedContent: string) => {
        fireEvent.click(await screen.findByRole('button', { name: '自动合并非重叠变更' }));
        expect((screen.getByLabelText('编辑产出物 Markdown') as HTMLTextAreaElement).value).toBe(expectedContent);
        expect(useStore.getState().artifactAuditEvents).toEqual([
            expect.objectContaining({
                stageId: 'STRATEGY',
                eventType: 'artifact_auto_merge_applied',
                summary: '合并轨迹：自动合并服务端与草稿的非重叠跨章节段落移动',
            }),
        ]);
    };

    const expectTableRowReorderAutoMerge = async (expectedContent: string) => {
        fireEvent.click(await screen.findByRole('button', { name: '自动合并非重叠变更' }));
        expect((screen.getByLabelText('编辑产出物 Markdown') as HTMLTextAreaElement).value).toBe(expectedContent);
        expect(useStore.getState().artifactAuditEvents).toEqual([
            expect.objectContaining({
                stageId: 'STRATEGY',
                eventType: 'artifact_auto_merge_applied',
                summary: '合并轨迹：自动合并服务端与草稿的非重叠表格行重排',
            }),
        ]);
    };

    const expectListItemReorderAutoMerge = async (expectedContent: string) => {
        fireEvent.click(await screen.findByRole('button', { name: '自动合并非重叠变更' }));
        expect((screen.getByLabelText('编辑产出物 Markdown') as HTMLTextAreaElement).value).toBe(expectedContent);
        expect(useStore.getState().artifactAuditEvents).toEqual([
            expect.objectContaining({
                stageId: 'STRATEGY',
                eventType: 'artifact_auto_merge_applied',
                summary: '合并轨迹：自动合并服务端与草稿的非重叠列表项重排',
            }),
        ]);
    };

    const expectFencedBlockLineReorderAutoMerge = async (expectedContent: string) => {
        fireEvent.click(await screen.findByRole('button', { name: '自动合并非重叠变更' }));
        expect((screen.getByLabelText('编辑产出物 Markdown') as HTMLTextAreaElement).value).toBe(expectedContent);
        expect(useStore.getState().artifactAuditEvents).toEqual([
            expect.objectContaining({
                stageId: 'STRATEGY',
                eventType: 'artifact_auto_merge_applied',
                summary: '合并轨迹：自动合并服务端与草稿的非重叠代码块行重排',
            }),
        ]);
    };

    const expectNoParagraphMovementAutoMerge = async () => {
        await screen.findByRole('button', { name: '对比服务端版本' });
        expect(screen.queryByRole('button', { name: '自动合并非重叠变更' })).toBeNull();
    };

    const expectStructuredBlockReorderReason = async () => {
        await expectNoParagraphMovementAutoMerge();
        expect(screen.getByText('结构化块重排需人工处理')).toBeTruthy();
        expect(screen.getByText(/列表项、表格行或代码块位置调整/)).toBeTruthy();
    };

    const expectNoStructuredBlockReorderReason = async () => {
        await expectNoParagraphMovementAutoMerge();
        expect(screen.queryByText('结构化块重排需人工处理')).toBeNull();
    };

    it('auto-merges paragraph movement when draft moves one paragraph and server rewrites another paragraph in the same section', async () => {
        renderParagraphMoveConflict(
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '段落A：服务端补充支付主链路观测点。',
                '',
                '段落B：覆盖退款逆向链路。',
                '',
                '段落C：覆盖风控拦截链路。',
                '',
                '## 验收口径',
                '旧验收口径',
            ].join('\n'),
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '段落C：覆盖风控拦截链路。',
                '',
                '段落A：覆盖支付主链路。',
                '',
                '段落B：覆盖退款逆向链路。',
                '',
                '## 验收口径',
                '旧验收口径',
            ].join('\n'),
        );

        await expectParagraphMovementAutoMerge([
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            '段落C：覆盖风控拦截链路。',
            '',
            '段落A：服务端补充支付主链路观测点。',
            '',
            '段落B：覆盖退款逆向链路。',
            '',
            '## 验收口径',
            '旧验收口径',
        ].join('\n'));
    });

    it('auto-merges paragraph movement when server moves one paragraph and draft rewrites another paragraph in the same section', async () => {
        renderParagraphMoveConflict(
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '段落C：覆盖风控拦截链路。',
                '',
                '段落A：覆盖支付主链路。',
                '',
                '段落B：覆盖退款逆向链路。',
                '',
                '## 验收口径',
                '旧验收口径',
            ].join('\n'),
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '段落A：用户补充支付主链路异常回滚。',
                '',
                '段落B：覆盖退款逆向链路。',
                '',
                '段落C：覆盖风控拦截链路。',
                '',
                '## 验收口径',
                '旧验收口径',
            ].join('\n'),
        );

        await expectParagraphMovementAutoMerge([
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            '段落C：覆盖风控拦截链路。',
            '',
            '段落A：用户补充支付主链路异常回滚。',
            '',
            '段落B：覆盖退款逆向链路。',
            '',
            '## 验收口径',
            '旧验收口径',
        ].join('\n'));
    });

    it('auto-merges paragraph movement when both sides move the same paragraph to the same position', async () => {
        const movedContent = [
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            '段落C：覆盖风控拦截链路。',
            '',
            '段落A：覆盖支付主链路。',
            '',
            '段落B：覆盖退款逆向链路。',
            '',
            '## 验收口径',
            '旧验收口径',
        ].join('\n');
        renderParagraphMoveConflict(movedContent, movedContent);

        await expectParagraphMovementAutoMerge(movedContent);
    });

    it('does not auto-merge paragraph movement when the moved paragraph is also rewritten', async () => {
        renderParagraphMoveConflict(
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '段落A：覆盖支付主链路。',
                '',
                '段落B：覆盖退款逆向链路。',
                '',
                '段落C：服务端改写风控拦截链路。',
                '',
                '## 验收口径',
                '旧验收口径',
            ].join('\n'),
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '段落C：覆盖风控拦截链路。',
                '',
                '段落A：覆盖支付主链路。',
                '',
                '段落B：覆盖退款逆向链路。',
                '',
                '## 验收口径',
                '旧验收口径',
            ].join('\n'),
        );

        await expectNoStructuredBlockReorderReason();
    });

    it('does not auto-merge paragraph movement when paragraph blocks repeat', async () => {
        const repeatedBaseContent = [
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            '重复段落：覆盖支付主链路。',
            '',
            '段落B：覆盖退款逆向链路。',
            '',
            '重复段落：覆盖支付主链路。',
            '',
            '## 验收口径',
            '旧验收口径',
        ].join('\n');
        renderParagraphMoveConflict(
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '重复段落：服务端补充支付观测点。',
                '',
                '段落B：覆盖退款逆向链路。',
                '',
                '重复段落：覆盖支付主链路。',
                '',
                '## 验收口径',
                '旧验收口径',
            ].join('\n'),
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '段落B：覆盖退款逆向链路。',
                '',
                '重复段落：覆盖支付主链路。',
                '',
                '重复段落：覆盖支付主链路。',
                '',
                '## 验收口径',
                '旧验收口径',
            ].join('\n'),
            repeatedBaseContent,
        );

        await expectNoParagraphMovementAutoMerge();
    });

    it('does not auto-merge paragraph movement when both sides move paragraphs differently', async () => {
        renderParagraphMoveConflict(
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '段落C：覆盖风控拦截链路。',
                '',
                '段落A：覆盖支付主链路。',
                '',
                '段落B：覆盖退款逆向链路。',
                '',
                '## 验收口径',
                '旧验收口径',
            ].join('\n'),
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '段落B：覆盖退款逆向链路。',
                '',
                '段落A：覆盖支付主链路。',
                '',
                '段落C：覆盖风控拦截链路。',
                '',
                '## 验收口径',
                '旧验收口径',
            ].join('\n'),
        );

        await expectNoParagraphMovementAutoMerge();
    });

    it('does not auto-merge paragraph movement across sections when the source section is also rewritten', async () => {
        renderParagraphMoveConflict(
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '段落A：服务端补充支付主链路观测点。',
                '',
                '段落B：覆盖退款逆向链路。',
                '',
                '段落C：覆盖风控拦截链路。',
                '',
                '## 验收口径',
                '旧验收口径',
            ].join('\n'),
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '段落A：覆盖支付主链路。',
                '',
                '段落B：覆盖退款逆向链路。',
                '',
                '## 验收口径',
                '段落C：覆盖风控拦截链路。',
                '',
                '旧验收口径',
            ].join('\n'),
        );

        await expectNoParagraphMovementAutoMerge();
    });

    it('auto-merges paragraph movement across sections when draft moves one paragraph and server rewrites another section', async () => {
        const crossSectionBaseContent = [
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            '段落A：覆盖支付主链路。',
            '',
            '段落B：覆盖退款逆向链路。',
            '',
            '段落C：覆盖风控拦截链路。',
            '',
            '## 验收口径',
            '旧验收口径',
            '',
            '## 观察记录',
            '旧观察记录',
        ].join('\n');
        renderParagraphMoveConflict(
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '段落A：覆盖支付主链路。',
                '',
                '段落B：覆盖退款逆向链路。',
                '',
                '段落C：覆盖风控拦截链路。',
                '',
                '## 验收口径',
                '旧验收口径',
                '',
                '## 观察记录',
                '服务端补充观察记录。',
            ].join('\n'),
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '段落A：覆盖支付主链路。',
                '',
                '段落B：覆盖退款逆向链路。',
                '',
                '## 验收口径',
                '段落C：覆盖风控拦截链路。',
                '',
                '旧验收口径',
                '',
                '## 观察记录',
                '旧观察记录',
            ].join('\n'),
            crossSectionBaseContent,
        );

        await expectCrossSectionParagraphMovementAutoMerge([
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            '段落A：覆盖支付主链路。',
            '',
            '段落B：覆盖退款逆向链路。',
            '',
            '## 验收口径',
            '段落C：覆盖风控拦截链路。',
            '',
            '旧验收口径',
            '',
            '## 观察记录',
            '服务端补充观察记录。',
        ].join('\n'));
    });

    it('auto-merges paragraph movement across sections when server moves one paragraph and draft rewrites another section', async () => {
        const crossSectionBaseContent = [
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            '段落A：覆盖支付主链路。',
            '',
            '段落B：覆盖退款逆向链路。',
            '',
            '段落C：覆盖风控拦截链路。',
            '',
            '## 验收口径',
            '旧验收口径',
            '',
            '## 观察记录',
            '旧观察记录',
        ].join('\n');
        renderParagraphMoveConflict(
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '段落A：覆盖支付主链路。',
                '',
                '段落B：覆盖退款逆向链路。',
                '',
                '## 验收口径',
                '段落C：覆盖风控拦截链路。',
                '',
                '旧验收口径',
                '',
                '## 观察记录',
                '旧观察记录',
            ].join('\n'),
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '段落A：覆盖支付主链路。',
                '',
                '段落B：覆盖退款逆向链路。',
                '',
                '段落C：覆盖风控拦截链路。',
                '',
                '## 验收口径',
                '旧验收口径',
                '',
                '## 观察记录',
                '用户补充观察记录。',
            ].join('\n'),
            crossSectionBaseContent,
        );

        await expectCrossSectionParagraphMovementAutoMerge([
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            '段落A：覆盖支付主链路。',
            '',
            '段落B：覆盖退款逆向链路。',
            '',
            '## 验收口径',
            '段落C：覆盖风控拦截链路。',
            '',
            '旧验收口径',
            '',
            '## 观察记录',
            '用户补充观察记录。',
        ].join('\n'));
    });

    it('auto-merges paragraph movement across sections when both sides move the same paragraph to the same target section position', async () => {
        const crossSectionBaseContent = [
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            '段落A：覆盖支付主链路。',
            '',
            '段落B：覆盖退款逆向链路。',
            '',
            '段落C：覆盖风控拦截链路。',
            '',
            '## 验收口径',
            '旧验收口径',
        ].join('\n');
        const movedContent = [
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            '段落A：覆盖支付主链路。',
            '',
            '段落B：覆盖退款逆向链路。',
            '',
            '## 验收口径',
            '段落C：覆盖风控拦截链路。',
            '',
            '旧验收口径',
        ].join('\n');
        renderParagraphMoveConflict(movedContent, movedContent, crossSectionBaseContent);

        await expectCrossSectionParagraphMovementAutoMerge(movedContent);
    });

    it('does not auto-merge paragraph movement for list items', async () => {
        const listBaseContent = [
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            '- 覆盖支付主链路',
            '- 覆盖退款逆向链路',
            '- 覆盖风控拦截链路',
            '',
            '## 验收口径',
            '旧验收口径',
        ].join('\n');
        renderParagraphMoveConflict(
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '- 覆盖支付主链路并补充观测点',
                '- 覆盖退款逆向链路',
                '- 覆盖风控拦截链路',
                '',
                '## 验收口径',
                '旧验收口径',
            ].join('\n'),
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '- 覆盖风控拦截链路',
                '- 覆盖支付主链路',
                '- 覆盖退款逆向链路',
                '',
                '## 验收口径',
                '旧验收口径',
            ].join('\n'),
            listBaseContent,
        );

        await expectNoParagraphMovementAutoMerge();
    });

    it('does not auto-merge paragraph movement inside fenced blocks', async () => {
        const fencedBaseContent = [
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            '```mermaid',
            'flowchart TD',
            'A[支付] --> B[退款]',
            '```',
            '',
            '段落A：覆盖支付主链路。',
            '',
            '## 验收口径',
            '旧验收口径',
        ].join('\n');
        renderParagraphMoveConflict(
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '```mermaid',
                'flowchart TD',
                'A[支付] --> B[退款]',
                '```',
                '',
                '段落A：服务端补充支付观测点。',
                '',
                '## 验收口径',
                '旧验收口径',
            ].join('\n'),
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '段落A：覆盖支付主链路。',
                '',
                '```mermaid',
                'flowchart TD',
                'A[支付] --> B[退款]',
                '```',
                '',
                '## 验收口径',
                '旧验收口径',
            ].join('\n'),
            fencedBaseContent,
        );

        await expectNoParagraphMovementAutoMerge();
    });

    it('does not auto-merge paragraph movement across sections when the moved paragraph is rewritten', async () => {
        const crossSectionBaseContent = [
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            '段落A：覆盖支付主链路。',
            '',
            '段落B：覆盖退款逆向链路。',
            '',
            '段落C：覆盖风控拦截链路。',
            '',
            '## 验收口径',
            '旧验收口径',
            '',
            '## 观察记录',
            '旧观察记录',
        ].join('\n');
        renderParagraphMoveConflict(
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '段落A：覆盖支付主链路。',
                '',
                '段落B：覆盖退款逆向链路。',
                '',
                '段落C：服务端改写风控拦截链路。',
                '',
                '## 验收口径',
                '旧验收口径',
                '',
                '## 观察记录',
                '旧观察记录',
            ].join('\n'),
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '段落A：覆盖支付主链路。',
                '',
                '段落B：覆盖退款逆向链路。',
                '',
                '## 验收口径',
                '段落C：覆盖风控拦截链路。',
                '',
                '旧验收口径',
                '',
                '## 观察记录',
                '旧观察记录',
            ].join('\n'),
            crossSectionBaseContent,
        );

        await expectNoParagraphMovementAutoMerge();
    });

    it('does not auto-merge paragraph movement across sections when the other side reorders a table in another section', async () => {
        const crossSectionBaseContent = [
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            '段落A：覆盖支付主链路。',
            '',
            '段落B：覆盖退款逆向链路。',
            '',
            '段落C：覆盖风控拦截链路。',
            '',
            '## 验收口径',
            '旧验收口径',
            '',
            '## 观察记录',
            '| 场景 | 风险 |',
            '| --- | --- |',
            '| 支付 | 高 |',
            '| 退款 | 中 |',
            '| 风控 | 高 |',
        ].join('\n');
        renderParagraphMoveConflict(
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '段落A：覆盖支付主链路。',
                '',
                '段落B：覆盖退款逆向链路。',
                '',
                '段落C：覆盖风控拦截链路。',
                '',
                '## 验收口径',
                '旧验收口径',
                '',
                '## 观察记录',
                '| 场景 | 风险 |',
                '| --- | --- |',
                '| 风控 | 高 |',
                '| 支付 | 高 |',
                '| 退款 | 中 |',
            ].join('\n'),
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '段落A：覆盖支付主链路。',
                '',
                '段落B：覆盖退款逆向链路。',
                '',
                '## 验收口径',
                '段落C：覆盖风控拦截链路。',
                '',
                '旧验收口径',
                '',
                '## 观察记录',
                '| 场景 | 风险 |',
                '| --- | --- |',
                '| 支付 | 高 |',
                '| 退款 | 中 |',
                '| 风控 | 高 |',
            ].join('\n'),
            crossSectionBaseContent,
        );

        await expectNoParagraphMovementAutoMerge();
    });

    it('does not auto-merge paragraph movement across sections when the other side moves a different paragraph in another section', async () => {
        const crossSectionBaseContent = [
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            '段落A：覆盖支付主链路。',
            '',
            '段落B：覆盖退款逆向链路。',
            '',
            '段落C：覆盖风控拦截链路。',
            '',
            '## 验收口径',
            '旧验收口径',
            '',
            '## 观察记录',
            '观察A：保留服务端错误线索。',
            '',
            '观察B：保留用户反馈线索。',
            '',
            '观察C：保留发布窗口线索。',
        ].join('\n');
        renderParagraphMoveConflict(
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '段落A：覆盖支付主链路。',
                '',
                '段落B：覆盖退款逆向链路。',
                '',
                '段落C：覆盖风控拦截链路。',
                '',
                '## 验收口径',
                '旧验收口径',
                '',
                '## 观察记录',
                '观察C：保留发布窗口线索。',
                '',
                '观察A：保留服务端错误线索。',
                '',
                '观察B：保留用户反馈线索。',
            ].join('\n'),
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '段落A：覆盖支付主链路。',
                '',
                '段落B：覆盖退款逆向链路。',
                '',
                '## 验收口径',
                '段落C：覆盖风控拦截链路。',
                '',
                '旧验收口径',
                '',
                '## 观察记录',
                '观察A：保留服务端错误线索。',
                '',
                '观察B：保留用户反馈线索。',
                '',
                '观察C：保留发布窗口线索。',
            ].join('\n'),
            crossSectionBaseContent,
        );

        await expectNoParagraphMovementAutoMerge();
    });

    it('does not auto-merge list item reordering when a reordered item is rewritten', async () => {
        const listBaseContent = [
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            '- 覆盖支付主链路',
            '- 覆盖退款逆向链路',
            '- 覆盖风控拦截链路',
            '',
            '## 验收口径',
            '旧验收口径',
        ].join('\n');
        renderParagraphMoveConflict(
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '- 覆盖支付主链路并补充观测点',
                '- 覆盖退款逆向链路',
                '- 覆盖风控拦截链路',
                '',
                '## 验收口径',
                '服务端补充验收口径。',
            ].join('\n'),
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '- 覆盖风控拦截链路',
                '- 覆盖支付主链路',
                '- 覆盖退款逆向链路',
                '',
                '## 验收口径',
                '旧验收口径',
            ].join('\n'),
            listBaseContent,
        );

        await expectNoParagraphMovementAutoMerge();
    });

    it('does not auto-merge list item reordering when another section also rewrites list items', async () => {
        const listBaseContent = [
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            '- 覆盖支付主链路',
            '- 覆盖退款逆向链路',
            '- 覆盖风控拦截链路',
            '',
            '## 观察记录',
            '- 旧观察A',
            '- 旧观察B',
        ].join('\n');
        renderParagraphMoveConflict(
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '- 覆盖支付主链路',
                '- 覆盖退款逆向链路',
                '- 覆盖风控拦截链路',
                '',
                '## 观察记录',
                '- 服务端改写观察A',
                '- 旧观察B',
            ].join('\n'),
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '- 覆盖风控拦截链路',
                '- 覆盖支付主链路',
                '- 覆盖退款逆向链路',
                '',
                '## 观察记录',
                '- 旧观察A',
                '- 旧观察B',
            ].join('\n'),
            listBaseContent,
        );

        await expectNoParagraphMovementAutoMerge();
    });

    it('does not auto-merge section movement when the other side reorders list items', async () => {
        const listBaseContent = [
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            '- 覆盖支付主链路',
            '- 覆盖退款逆向链路',
            '- 覆盖风控拦截链路',
            '',
            '## 验收口径',
            '旧验收口径',
        ].join('\n');
        renderParagraphMoveConflict(
            [
                '# 测试策略蓝图',
                '',
                '## 验收口径',
                '旧验收口径',
                '',
                '## 风险策略',
                '- 覆盖支付主链路',
                '- 覆盖退款逆向链路',
                '- 覆盖风控拦截链路',
            ].join('\n'),
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '- 覆盖风控拦截链路',
                '- 覆盖支付主链路',
                '- 覆盖退款逆向链路',
                '',
                '## 验收口径',
                '旧验收口径',
            ].join('\n'),
            listBaseContent,
        );

        await expectNoParagraphMovementAutoMerge();
    });

    it('does not auto-merge section movement when the other side reorders indented list items', async () => {
        const listBaseContent = [
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            ' - 覆盖支付主链路',
            ' - 覆盖退款逆向链路',
            ' - 覆盖风控拦截链路',
            '',
            '## 验收口径',
            '旧验收口径',
        ].join('\n');
        renderParagraphMoveConflict(
            [
                '# 测试策略蓝图',
                '',
                '## 验收口径',
                '旧验收口径',
                '',
                '## 风险策略',
                ' - 覆盖支付主链路',
                ' - 覆盖退款逆向链路',
                ' - 覆盖风控拦截链路',
            ].join('\n'),
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                ' - 覆盖风控拦截链路',
                ' - 覆盖支付主链路',
                ' - 覆盖退款逆向链路',
                '',
                '## 验收口径',
                '旧验收口径',
            ].join('\n'),
            listBaseContent,
        );

        await expectNoParagraphMovementAutoMerge();
    });

    it('does not auto-merge section rename when the other side reorders indented list items', async () => {
        const listBaseContent = [
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            ' - 覆盖支付主链路',
            ' - 覆盖退款逆向链路',
            ' - 覆盖风控拦截链路',
            '',
            '## 验收口径',
            '旧验收口径',
        ].join('\n');
        renderParagraphMoveConflict(
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                ' - 覆盖支付主链路',
                ' - 覆盖退款逆向链路',
                ' - 覆盖风控拦截链路',
                '',
                '## 验收标准',
                '旧验收口径',
            ].join('\n'),
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                ' - 覆盖风控拦截链路',
                ' - 覆盖支付主链路',
                ' - 覆盖退款逆向链路',
                '',
                '## 验收口径',
                '旧验收口径',
            ].join('\n'),
            listBaseContent,
        );

        await expectNoParagraphMovementAutoMerge();
    });

    it('does not auto-merge nested list item reordering', async () => {
        const listBaseContent = [
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            '- 支付链路',
            '  - 支付成功',
            '- 退款链路',
            '  - 退款成功',
            '',
            '## 验收口径',
            '旧验收口径',
        ].join('\n');
        renderParagraphMoveConflict(
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '- 支付链路',
                '  - 支付成功',
                '- 退款链路',
                '  - 退款成功',
                '',
                '## 验收口径',
                '服务端补充验收口径。',
            ].join('\n'),
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '- 退款链路',
                '  - 退款成功',
                '- 支付链路',
                '  - 支付成功',
                '',
                '## 验收口径',
                '旧验收口径',
            ].join('\n'),
            listBaseContent,
        );

        await expectNoParagraphMovementAutoMerge();
    });

    it('auto-merges list-like line reordering inside fenced blocks as fenced block line reordering', async () => {
        const listBaseContent = [
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            '```text',
            '- 支付脚本步骤',
            '- 退款脚本步骤',
            '```',
            '',
            '## 验收口径',
            '旧验收口径',
        ].join('\n');
        const expectedContent = [
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            '```text',
            '- 退款脚本步骤',
            '- 支付脚本步骤',
            '```',
            '',
            '## 验收口径',
            '服务端补充验收口径。',
        ].join('\n');
        renderParagraphMoveConflict(
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '```text',
                '- 支付脚本步骤',
                '- 退款脚本步骤',
                '```',
                '',
                '## 验收口径',
                '服务端补充验收口径。',
            ].join('\n'),
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '```text',
                '- 退款脚本步骤',
                '- 支付脚本步骤',
                '```',
                '',
                '## 验收口径',
                '旧验收口径',
            ].join('\n'),
            listBaseContent,
        );

        await expectFencedBlockLineReorderAutoMerge(expectedContent);
    });

    it('auto-merges list item reordering when draft reorders list items and server rewrites another section', async () => {
        const listBaseContent = [
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            '- 覆盖支付主链路',
            '- 覆盖退款逆向链路',
            '- 覆盖风控拦截链路',
            '',
            '## 验收口径',
            '旧验收口径',
        ].join('\n');
        const expectedContent = [
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            '- 覆盖风控拦截链路',
            '- 覆盖支付主链路',
            '- 覆盖退款逆向链路',
            '',
            '## 验收口径',
            '服务端补充验收口径。',
        ].join('\n');
        renderParagraphMoveConflict(
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '- 覆盖支付主链路',
                '- 覆盖退款逆向链路',
                '- 覆盖风控拦截链路',
                '',
                '## 验收口径',
                '服务端补充验收口径。',
            ].join('\n'),
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '- 覆盖风控拦截链路',
                '- 覆盖支付主链路',
                '- 覆盖退款逆向链路',
                '',
                '## 验收口径',
                '旧验收口径',
            ].join('\n'),
            listBaseContent,
        );

        await expectListItemReorderAutoMerge(expectedContent);
    });

    it('auto-merges list item reordering when server reorders list items and draft rewrites another section', async () => {
        const listBaseContent = [
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            '- 覆盖支付主链路',
            '- 覆盖退款逆向链路',
            '- 覆盖风控拦截链路',
            '',
            '## 验收口径',
            '旧验收口径',
        ].join('\n');
        const expectedContent = [
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            '- 覆盖风控拦截链路',
            '- 覆盖支付主链路',
            '- 覆盖退款逆向链路',
            '',
            '## 验收口径',
            '用户补充验收口径。',
        ].join('\n');
        renderParagraphMoveConflict(
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '- 覆盖风控拦截链路',
                '- 覆盖支付主链路',
                '- 覆盖退款逆向链路',
                '',
                '## 验收口径',
                '旧验收口径',
            ].join('\n'),
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '- 覆盖支付主链路',
                '- 覆盖退款逆向链路',
                '- 覆盖风控拦截链路',
                '',
                '## 验收口径',
                '用户补充验收口径。',
            ].join('\n'),
            listBaseContent,
        );

        await expectListItemReorderAutoMerge(expectedContent);
    });

    it('does not auto-merge table row reordering when a reordered row is rewritten', async () => {
        const tableBaseContent = [
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            '| 场景 | 风险 |',
            '| --- | --- |',
            '| 支付 | 高 |',
            '| 退款 | 中 |',
            '| 风控 | 高 |',
            '',
            '## 验收口径',
            '旧验收口径',
        ].join('\n');
        renderParagraphMoveConflict(
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '| 场景 | 风险 |',
                '| --- | --- |',
                '| 支付 | 高 |',
                '| 退款 | 中 |',
                '| 风控 | 高 |',
                '',
                '## 验收口径',
                '服务端补充验收口径。',
            ].join('\n'),
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '| 场景 | 风险 |',
                '| --- | --- |',
                '| 风控 | 极高 |',
                '| 支付 | 高 |',
                '| 退款 | 中 |',
                '',
                '## 验收口径',
                '旧验收口径',
            ].join('\n'),
            tableBaseContent,
        );

        await expectNoStructuredBlockReorderReason();
    });

    it('auto-merges table row reordering when draft reorders rows and server rewrites another section', async () => {
        const tableBaseContent = [
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            '| 场景 | 风险 |',
            '| --- | --- |',
            '| 支付 | 高 |',
            '| 退款 | 中 |',
            '| 风控 | 高 |',
            '',
            '## 验收口径',
            '旧验收口径',
        ].join('\n');
        const expectedContent = [
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            '| 场景 | 风险 |',
            '| --- | --- |',
            '| 风控 | 高 |',
            '| 支付 | 高 |',
            '| 退款 | 中 |',
            '',
            '## 验收口径',
            '服务端补充验收口径。',
        ].join('\n');
        renderParagraphMoveConflict(
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '| 场景 | 风险 |',
                '| --- | --- |',
                '| 支付 | 高 |',
                '| 退款 | 中 |',
                '| 风控 | 高 |',
                '',
                '## 验收口径',
                '服务端补充验收口径。',
            ].join('\n'),
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '| 场景 | 风险 |',
                '| --- | --- |',
                '| 风控 | 高 |',
                '| 支付 | 高 |',
                '| 退款 | 中 |',
                '',
                '## 验收口径',
                '旧验收口径',
            ].join('\n'),
            tableBaseContent,
        );

        await expectTableRowReorderAutoMerge(expectedContent);
    });

    it('auto-merges table row reordering when server reorders rows and draft rewrites another section', async () => {
        const tableBaseContent = [
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            '| 场景 | 风险 |',
            '| --- | --- |',
            '| 支付 | 高 |',
            '| 退款 | 中 |',
            '| 风控 | 高 |',
            '',
            '## 验收口径',
            '旧验收口径',
        ].join('\n');
        const expectedContent = [
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            '| 场景 | 风险 |',
            '| --- | --- |',
            '| 风控 | 高 |',
            '| 支付 | 高 |',
            '| 退款 | 中 |',
            '',
            '## 验收口径',
            '用户补充验收口径。',
        ].join('\n');
        renderParagraphMoveConflict(
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '| 场景 | 风险 |',
                '| --- | --- |',
                '| 风控 | 高 |',
                '| 支付 | 高 |',
                '| 退款 | 中 |',
                '',
                '## 验收口径',
                '旧验收口径',
            ].join('\n'),
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '| 场景 | 风险 |',
                '| --- | --- |',
                '| 支付 | 高 |',
                '| 退款 | 中 |',
                '| 风控 | 高 |',
                '',
                '## 验收口径',
                '用户补充验收口径。',
            ].join('\n'),
            tableBaseContent,
        );

        await expectTableRowReorderAutoMerge(expectedContent);
    });

    it('does not auto-merge paragraph movement inside fenced blocks when the server rewrites another section', async () => {
        const fencedBaseContent = [
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            '```mermaid',
            'flowchart TD',
            'A[支付] --> B[退款]',
            '```',
            '',
            '段落A：覆盖支付主链路。',
            '',
            '## 验收口径',
            '旧验收口径',
        ].join('\n');
        renderParagraphMoveConflict(
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '```mermaid',
                'flowchart TD',
                'A[支付] --> B[退款]',
                '```',
                '',
                '段落A：覆盖支付主链路。',
                '',
                '## 验收口径',
                '服务端补充验收口径。',
            ].join('\n'),
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '段落A：覆盖支付主链路。',
                '',
                '```mermaid',
                'flowchart TD',
                'A[支付] --> B[退款]',
                '```',
                '',
                '## 验收口径',
                '旧验收口径',
            ].join('\n'),
            fencedBaseContent,
        );

        await expectStructuredBlockReorderReason();
    });

    it('auto-merges fenced block line reordering when draft reorders lines and server rewrites another section', async () => {
        const fencedBaseContent = [
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            '```mermaid',
            'flowchart TD',
            'A[支付] --> B[退款]',
            'B --> C[风控]',
            'C --> D[验收]',
            '```',
            '',
            '## 验收口径',
            '旧验收口径',
        ].join('\n');
        const expectedContent = [
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            '```mermaid',
            'flowchart TD',
            'C --> D[验收]',
            'A[支付] --> B[退款]',
            'B --> C[风控]',
            '```',
            '',
            '## 验收口径',
            '服务端补充验收口径。',
        ].join('\n');
        renderParagraphMoveConflict(
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '```mermaid',
                'flowchart TD',
                'A[支付] --> B[退款]',
                'B --> C[风控]',
                'C --> D[验收]',
                '```',
                '',
                '## 验收口径',
                '服务端补充验收口径。',
            ].join('\n'),
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '```mermaid',
                'flowchart TD',
                'C --> D[验收]',
                'A[支付] --> B[退款]',
                'B --> C[风控]',
                '```',
                '',
                '## 验收口径',
                '旧验收口径',
            ].join('\n'),
            fencedBaseContent,
        );

        await expectFencedBlockLineReorderAutoMerge(expectedContent);
    });

    it('auto-merges fenced block line reordering when server reorders lines and draft rewrites another section', async () => {
        const fencedBaseContent = [
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            '```mermaid',
            'flowchart TD',
            'A[支付] --> B[退款]',
            'B --> C[风控]',
            'C --> D[验收]',
            '```',
            '',
            '## 验收口径',
            '旧验收口径',
        ].join('\n');
        const expectedContent = [
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            '```mermaid',
            'flowchart TD',
            'C --> D[验收]',
            'A[支付] --> B[退款]',
            'B --> C[风控]',
            '```',
            '',
            '## 验收口径',
            '用户补充验收口径。',
        ].join('\n');
        renderParagraphMoveConflict(
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '```mermaid',
                'flowchart TD',
                'C --> D[验收]',
                'A[支付] --> B[退款]',
                'B --> C[风控]',
                '```',
                '',
                '## 验收口径',
                '旧验收口径',
            ].join('\n'),
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '```mermaid',
                'flowchart TD',
                'A[支付] --> B[退款]',
                'B --> C[风控]',
                'C --> D[验收]',
                '```',
                '',
                '## 验收口径',
                '用户补充验收口径。',
            ].join('\n'),
            fencedBaseContent,
        );

        await expectFencedBlockLineReorderAutoMerge(expectedContent);
    });

    it('does not auto-merge fenced block line reordering when a reordered line is rewritten', async () => {
        const fencedBaseContent = [
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            '```mermaid',
            'flowchart TD',
            'A[支付] --> B[退款]',
            'B --> C[风控]',
            'C --> D[验收]',
            '```',
            '',
            '## 验收口径',
            '旧验收口径',
        ].join('\n');
        renderParagraphMoveConflict(
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '```mermaid',
                'flowchart TD',
                'A[支付] --> B[退款]',
                'B --> C[风控]',
                'C --> D[验收]',
                '```',
                '',
                '## 验收口径',
                '服务端补充验收口径。',
            ].join('\n'),
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '```mermaid',
                'flowchart TD',
                'C --> D[验收增强]',
                'A[支付] --> B[退款]',
                'B --> C[风控]',
                '```',
                '',
                '## 验收口径',
                '旧验收口径',
            ].join('\n'),
            fencedBaseContent,
        );

        await expectNoParagraphMovementAutoMerge();
    });

    it('does not auto-merge fenced block line reordering when lines repeat', async () => {
        const fencedBaseContent = [
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            '```text',
            'step: 登录',
            'step: 登录',
            'step: 支付',
            '```',
            '',
            '## 验收口径',
            '旧验收口径',
        ].join('\n');
        renderParagraphMoveConflict(
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '```text',
                'step: 登录',
                'step: 登录',
                'step: 支付',
                '```',
                '',
                '## 验收口径',
                '服务端补充验收口径。',
            ].join('\n'),
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '```text',
                'step: 支付',
                'step: 登录',
                'step: 登录',
                '```',
                '',
                '## 验收口径',
                '旧验收口径',
            ].join('\n'),
            fencedBaseContent,
        );

        await expectNoParagraphMovementAutoMerge();
    });

    it('does not auto-merge paragraph movement when a paragraph is split while the server rewrites the same section', async () => {
        renderParagraphMoveConflict(
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '段落A：服务端补充支付主链路观测点。',
                '',
                '段落B：覆盖退款逆向链路。',
                '',
                '段落C：覆盖风控拦截链路。',
                '',
                '## 验收口径',
                '旧验收口径',
            ].join('\n'),
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '段落A：覆盖支付主链路。',
                '',
                '补充分句：拆出支付异常路径。',
                '',
                '段落B：覆盖退款逆向链路。',
                '',
                '段落C：覆盖风控拦截链路。',
                '',
                '## 验收口径',
                '旧验收口径',
            ].join('\n'),
        );

        await expectNoParagraphMovementAutoMerge();
    });

    const baseSectionRenameContent = [
        '# 测试策略蓝图',
        '',
        '## 风险策略',
        '旧风险策略',
        '',
        '## 验收口径',
        '旧验收口径',
    ].join('\n');

    const renderSectionRenameConflict = (
        serverContent: string,
        draftContent: string,
        baseContent = baseSectionRenameContent,
    ) => {
        vi.mocked(updateRunArtifact).mockRejectedValue(new ArtifactConflictError(
            '产出物已被更新，请刷新后再保存',
            {
                stageId: 'STRATEGY',
                content: serverContent,
                versionNumber: 3,
            },
        ));
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 1,
            currentRunId: 'run-123',
            artifactContent: baseContent,
            stageArtifacts: {
                STRATEGY: baseContent,
            },
            artifactHistory: [
                {
                    id: 'run-123-STRATEGY-v2',
                    timestamp: 123,
                    content: baseContent,
                    stageId: 'STRATEGY',
                },
            ],
            artifactAuditEvents: [],
        });

        render(<ArtifactPane />);
        fireEvent.click(screen.getByTitle('编辑产出物'));
        fireEvent.change(screen.getByLabelText('编辑产出物 Markdown'), {
            target: {
                value: draftContent,
            },
        });
        fireEvent.click(screen.getByRole('button', { name: '保存修改' }));
    };

    it('auto-merges non-overlapping section rename when draft renames and server rewrites another section', async () => {
        renderSectionRenameConflict(
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '服务端风险策略：优先覆盖支付链路',
                '',
                '## 验收口径',
                '旧验收口径',
            ].join('\n'),
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '旧风险策略',
                '',
                '## 质量口径',
                '旧验收口径',
            ].join('\n'),
        );

        fireEvent.click(await screen.findByRole('button', { name: '自动合并非重叠变更' }));

        expect((screen.getByLabelText('编辑产出物 Markdown') as HTMLTextAreaElement).value).toBe([
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            '服务端风险策略：优先覆盖支付链路',
            '',
            '## 质量口径',
            '旧验收口径',
        ].join('\n'));
        expect(useStore.getState().artifactAuditEvents).toEqual([
            expect.objectContaining({
                stageId: 'STRATEGY',
                eventType: 'artifact_auto_merge_applied',
                summary: '合并轨迹：自动合并服务端与草稿的非重叠章节重命名',
            }),
        ]);
    });

    it('auto-merges non-overlapping section rename when server renames and draft rewrites another section', async () => {
        renderSectionRenameConflict(
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '旧风险策略',
                '',
                '## 质量口径',
                '旧验收口径',
            ].join('\n'),
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '用户风险策略：优先覆盖退款链路',
                '',
                '## 验收口径',
                '旧验收口径',
            ].join('\n'),
        );

        fireEvent.click(await screen.findByRole('button', { name: '自动合并非重叠变更' }));

        expect((screen.getByLabelText('编辑产出物 Markdown') as HTMLTextAreaElement).value).toBe([
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            '用户风险策略：优先覆盖退款链路',
            '',
            '## 质量口径',
            '旧验收口径',
        ].join('\n'));
        expect(useStore.getState().artifactAuditEvents).toEqual([
            expect.objectContaining({
                stageId: 'STRATEGY',
                eventType: 'artifact_auto_merge_applied',
                summary: '合并轨迹：自动合并服务端与草稿的非重叠章节重命名',
            }),
        ]);
    });

    it('auto-merges section rename when both sides rename to the same heading', async () => {
        renderSectionRenameConflict(
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '旧风险策略',
                '',
                '## 质量口径',
                '旧验收口径',
            ].join('\n'),
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '用户风险策略：优先覆盖退款链路',
                '',
                '## 质量口径',
                '旧验收口径',
            ].join('\n'),
        );

        fireEvent.click(await screen.findByRole('button', { name: '自动合并非重叠变更' }));

        expect((screen.getByLabelText('编辑产出物 Markdown') as HTMLTextAreaElement).value).toBe([
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            '用户风险策略：优先覆盖退款链路',
            '',
            '## 质量口径',
            '旧验收口径',
        ].join('\n'));
        expect(useStore.getState().artifactAuditEvents).toEqual([
            expect.objectContaining({
                stageId: 'STRATEGY',
                eventType: 'artifact_auto_merge_applied',
                summary: '合并轨迹：自动合并服务端与草稿的非重叠章节重命名',
            }),
        ]);
    });

    it('does not auto-merge section rename when both sides rename to different headings', async () => {
        renderSectionRenameConflict(
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '旧风险策略',
                '',
                '## 服务验收口径',
                '旧验收口径',
            ].join('\n'),
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '旧风险策略',
                '',
                '## 质量口径',
                '旧验收口径',
            ].join('\n'),
        );

        await screen.findByRole('button', { name: '对比服务端版本' });
        expect(screen.queryByRole('button', { name: '自动合并非重叠变更' })).toBeNull();
    });

    it('does not auto-merge section rename when renamed section body also changes', async () => {
        renderSectionRenameConflict(
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '服务端风险策略：优先覆盖支付链路',
                '',
                '## 验收口径',
                '旧验收口径',
            ].join('\n'),
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '旧风险策略',
                '',
                '## 质量口径',
                '用户质量口径：增加回滚检查',
            ].join('\n'),
        );

        await screen.findByRole('button', { name: '对比服务端版本' });
        expect(screen.queryByRole('button', { name: '自动合并非重叠变更' })).toBeNull();
    });

    it('does not auto-merge section rename when the other side changed the renamed section body', async () => {
        renderSectionRenameConflict(
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '旧风险策略',
                '',
                '## 验收口径',
                '服务端验收口径：增加支付回归',
            ].join('\n'),
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '旧风险策略',
                '',
                '## 质量口径',
                '旧验收口径',
            ].join('\n'),
        );

        await screen.findByRole('button', { name: '对比服务端版本' });
        expect(screen.queryByRole('button', { name: '自动合并非重叠变更' })).toBeNull();
    });

    it('does not auto-merge section rename when the other side also moves and rewrites a section', async () => {
        const baseContentWithTrailingBlank = [
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            '旧风险策略',
            '',
            '## 验收口径',
            '旧验收口径',
            '',
        ].join('\n');

        renderSectionRenameConflict(
            [
                '# 测试策略蓝图',
                '',
                '## 验收口径',
                '旧验收口径',
                '',
                '## 风险策略',
                '服务端风险策略：优先覆盖支付链路',
                '',
            ].join('\n'),
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '旧风险策略',
                '',
                '## 质量口径',
                '旧验收口径',
                '',
            ].join('\n'),
            baseContentWithTrailingBlank,
        );

        await screen.findByRole('button', { name: '对比服务端版本' });
        expect(screen.queryByRole('button', { name: '自动合并非重叠变更' })).toBeNull();
    });

    it('does not auto-merge section rename when heading depth changes', async () => {
        renderSectionRenameConflict(
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '服务端风险策略：优先覆盖支付链路',
                '',
                '## 验收口径',
                '旧验收口径',
            ].join('\n'),
            [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '旧风险策略',
                '',
                '### 质量口径',
                '旧验收口径',
            ].join('\n'),
        );

        await screen.findByRole('button', { name: '对比服务端版本' });
        expect(screen.queryByRole('button', { name: '自动合并非重叠变更' })).toBeNull();
    });

    it('auto-merges non-overlapping section add/delete when draft adds a section', async () => {
        vi.mocked(updateRunArtifact).mockRejectedValue(new ArtifactConflictError(
            '产出物已被更新，请刷新后再保存',
            {
                stageId: 'STRATEGY',
                content: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '服务端风险策略：优先覆盖支付链路',
                    '',
                    '## 验收口径',
                    '旧验收口径',
                ].join('\n'),
                versionNumber: 3,
            },
        ));
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 1,
            currentRunId: 'run-123',
            artifactContent: [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '旧风险策略',
                '',
                '## 验收口径',
                '旧验收口径',
            ].join('\n'),
            stageArtifacts: {
                STRATEGY: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '旧风险策略',
                    '',
                    '## 验收口径',
                    '旧验收口径',
                ].join('\n'),
            },
            artifactHistory: [{
                id: 'run-123-STRATEGY-v2',
                timestamp: 123,
                content: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '旧风险策略',
                    '',
                    '## 验收口径',
                    '旧验收口径',
                ].join('\n'),
                stageId: 'STRATEGY',
            }],
            artifactAuditEvents: [],
        });

        render(<ArtifactPane />);
        fireEvent.click(screen.getByTitle('编辑产出物'));
        fireEvent.change(screen.getByLabelText('编辑产出物 Markdown'), {
            target: {
                value: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '旧风险策略',
                    '',
                    '## 验收口径',
                    '旧验收口径',
                    '',
                    '## 覆盖策略',
                    '用户新增覆盖策略：补充退款链路',
                ].join('\n'),
            },
        });
        fireEvent.click(screen.getByRole('button', { name: '保存修改' }));
        fireEvent.click(await screen.findByRole('button', { name: '自动合并非重叠变更' }));

        expect((screen.getByLabelText('编辑产出物 Markdown') as HTMLTextAreaElement).value).toBe([
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            '服务端风险策略：优先覆盖支付链路',
            '',
            '## 验收口径',
            '旧验收口径',
            '',
            '## 覆盖策略',
            '用户新增覆盖策略：补充退款链路',
        ].join('\n'));
        expect(useStore.getState().artifactAuditEvents).toEqual([
            expect.objectContaining({
                stageId: 'STRATEGY',
                eventType: 'artifact_auto_merge_applied',
                summary: '合并轨迹：自动合并服务端与草稿的非重叠章节增删',
            }),
        ]);
    });

    it('auto-merges non-overlapping section add/delete when draft deletes an unchanged section', async () => {
        vi.mocked(updateRunArtifact).mockRejectedValue(new ArtifactConflictError(
            '产出物已被更新，请刷新后再保存',
            {
                stageId: 'STRATEGY',
                content: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '服务端风险策略：优先覆盖支付链路',
                    '',
                    '## 验收口径',
                    '旧验收口径',
                    '',
                    '## 交付计划',
                    '旧交付计划',
                ].join('\n'),
                versionNumber: 3,
            },
        ));
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 1,
            currentRunId: 'run-123',
            artifactContent: [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '旧风险策略',
                '',
                '## 验收口径',
                '旧验收口径',
                '',
                '## 交付计划',
                '旧交付计划',
            ].join('\n'),
            stageArtifacts: {
                STRATEGY: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '旧风险策略',
                    '',
                    '## 验收口径',
                    '旧验收口径',
                    '',
                    '## 交付计划',
                    '旧交付计划',
                ].join('\n'),
            },
            artifactHistory: [{
                id: 'run-123-STRATEGY-v2',
                timestamp: 123,
                content: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '旧风险策略',
                    '',
                    '## 验收口径',
                    '旧验收口径',
                    '',
                    '## 交付计划',
                    '旧交付计划',
                ].join('\n'),
                stageId: 'STRATEGY',
            }],
            artifactAuditEvents: [],
        });

        render(<ArtifactPane />);
        fireEvent.click(screen.getByTitle('编辑产出物'));
        fireEvent.change(screen.getByLabelText('编辑产出物 Markdown'), {
            target: {
                value: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '旧风险策略',
                    '',
                    '## 验收口径',
                    '旧验收口径',
                ].join('\n'),
            },
        });
        fireEvent.click(screen.getByRole('button', { name: '保存修改' }));
        fireEvent.click(await screen.findByRole('button', { name: '自动合并非重叠变更' }));

        expect((screen.getByLabelText('编辑产出物 Markdown') as HTMLTextAreaElement).value).toBe([
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            '服务端风险策略：优先覆盖支付链路',
            '',
            '## 验收口径',
            '旧验收口径',
        ].join('\n'));
        expect(useStore.getState().artifactAuditEvents).toEqual([
            expect.objectContaining({
                stageId: 'STRATEGY',
                eventType: 'artifact_auto_merge_applied',
                summary: '合并轨迹：自动合并服务端与草稿的非重叠章节增删',
            }),
        ]);
    });

    it('auto-merges non-overlapping section add/delete when server adds a section and draft rewrites another section', async () => {
        vi.mocked(updateRunArtifact).mockRejectedValue(new ArtifactConflictError(
            '产出物已被更新，请刷新后再保存',
            {
                stageId: 'STRATEGY',
                content: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '旧风险策略',
                    '',
                    '## 验收口径',
                    '旧验收口径',
                    '',
                    '## 服务端覆盖策略',
                    '服务端新增覆盖策略：补充支付链路',
                ].join('\n'),
                versionNumber: 3,
            },
        ));
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 1,
            currentRunId: 'run-123',
            artifactContent: [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '旧风险策略',
                '',
                '## 验收口径',
                '旧验收口径',
            ].join('\n'),
            stageArtifacts: {
                STRATEGY: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '旧风险策略',
                    '',
                    '## 验收口径',
                    '旧验收口径',
                ].join('\n'),
            },
            artifactHistory: [{
                id: 'run-123-STRATEGY-v2',
                timestamp: 123,
                content: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '旧风险策略',
                    '',
                    '## 验收口径',
                    '旧验收口径',
                ].join('\n'),
                stageId: 'STRATEGY',
            }],
            artifactAuditEvents: [],
        });

        render(<ArtifactPane />);
        fireEvent.click(screen.getByTitle('编辑产出物'));
        fireEvent.change(screen.getByLabelText('编辑产出物 Markdown'), {
            target: {
                value: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '用户风险策略：优先覆盖退款链路',
                    '',
                    '## 验收口径',
                    '旧验收口径',
                ].join('\n'),
            },
        });
        fireEvent.click(screen.getByRole('button', { name: '保存修改' }));
        fireEvent.click(await screen.findByRole('button', { name: '自动合并非重叠变更' }));

        expect((screen.getByLabelText('编辑产出物 Markdown') as HTMLTextAreaElement).value).toBe([
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            '用户风险策略：优先覆盖退款链路',
            '',
            '## 验收口径',
            '旧验收口径',
            '',
            '## 服务端覆盖策略',
            '服务端新增覆盖策略：补充支付链路',
        ].join('\n'));
        expect(useStore.getState().artifactAuditEvents).toEqual([
            expect.objectContaining({
                stageId: 'STRATEGY',
                eventType: 'artifact_auto_merge_applied',
                summary: '合并轨迹：自动合并服务端与草稿的非重叠章节增删',
            }),
        ]);
    });

    it('auto-merges non-overlapping section add/delete when server deletes an unchanged section and draft rewrites another section', async () => {
        vi.mocked(updateRunArtifact).mockRejectedValue(new ArtifactConflictError(
            '产出物已被更新，请刷新后再保存',
            {
                stageId: 'STRATEGY',
                content: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '旧风险策略',
                    '',
                    '## 验收口径',
                    '旧验收口径',
                ].join('\n'),
                versionNumber: 3,
            },
        ));
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 1,
            currentRunId: 'run-123',
            artifactContent: [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '旧风险策略',
                '',
                '## 验收口径',
                '旧验收口径',
                '',
                '## 交付计划',
                '旧交付计划',
            ].join('\n'),
            stageArtifacts: {
                STRATEGY: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '旧风险策略',
                    '',
                    '## 验收口径',
                    '旧验收口径',
                    '',
                    '## 交付计划',
                    '旧交付计划',
                ].join('\n'),
            },
            artifactHistory: [{
                id: 'run-123-STRATEGY-v2',
                timestamp: 123,
                content: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '旧风险策略',
                    '',
                    '## 验收口径',
                    '旧验收口径',
                    '',
                    '## 交付计划',
                    '旧交付计划',
                ].join('\n'),
                stageId: 'STRATEGY',
            }],
            artifactAuditEvents: [],
        });

        render(<ArtifactPane />);
        fireEvent.click(screen.getByTitle('编辑产出物'));
        fireEvent.change(screen.getByLabelText('编辑产出物 Markdown'), {
            target: {
                value: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '用户风险策略：优先覆盖退款链路',
                    '',
                    '## 验收口径',
                    '旧验收口径',
                    '',
                    '## 交付计划',
                    '旧交付计划',
                ].join('\n'),
            },
        });
        fireEvent.click(screen.getByRole('button', { name: '保存修改' }));
        fireEvent.click(await screen.findByRole('button', { name: '自动合并非重叠变更' }));

        expect((screen.getByLabelText('编辑产出物 Markdown') as HTMLTextAreaElement).value).toBe([
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            '用户风险策略：优先覆盖退款链路',
            '',
            '## 验收口径',
            '旧验收口径',
        ].join('\n'));
        expect(useStore.getState().artifactAuditEvents).toEqual([
            expect.objectContaining({
                stageId: 'STRATEGY',
                eventType: 'artifact_auto_merge_applied',
                summary: '合并轨迹：自动合并服务端与草稿的非重叠章节增删',
            }),
        ]);
    });

    it('auto-merges non-overlapping section add/delete when both sides add different sections', async () => {
        vi.mocked(updateRunArtifact).mockRejectedValue(new ArtifactConflictError(
            '产出物已被更新，请刷新后再保存',
            {
                stageId: 'STRATEGY',
                content: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '旧风险策略',
                    '',
                    '## 验收口径',
                    '旧验收口径',
                    '',
                    '## 服务端覆盖策略',
                    '服务端新增覆盖策略：补充支付链路',
                ].join('\n'),
                versionNumber: 3,
            },
        ));
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 1,
            currentRunId: 'run-123',
            artifactContent: [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '旧风险策略',
                '',
                '## 验收口径',
                '旧验收口径',
            ].join('\n'),
            stageArtifacts: {
                STRATEGY: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '旧风险策略',
                    '',
                    '## 验收口径',
                    '旧验收口径',
                ].join('\n'),
            },
            artifactHistory: [{
                id: 'run-123-STRATEGY-v2',
                timestamp: 123,
                content: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '旧风险策略',
                    '',
                    '## 验收口径',
                    '旧验收口径',
                ].join('\n'),
                stageId: 'STRATEGY',
            }],
            artifactAuditEvents: [],
        });

        render(<ArtifactPane />);
        fireEvent.click(screen.getByTitle('编辑产出物'));
        fireEvent.change(screen.getByLabelText('编辑产出物 Markdown'), {
            target: {
                value: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '旧风险策略',
                    '',
                    '## 验收口径',
                    '旧验收口径',
                    '',
                    '## 用户覆盖策略',
                    '用户新增覆盖策略：补充退款链路',
                ].join('\n'),
            },
        });
        fireEvent.click(screen.getByRole('button', { name: '保存修改' }));
        fireEvent.click(await screen.findByRole('button', { name: '自动合并非重叠变更' }));

        expect((screen.getByLabelText('编辑产出物 Markdown') as HTMLTextAreaElement).value).toBe([
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            '旧风险策略',
            '',
            '## 验收口径',
            '旧验收口径',
            '',
            '## 服务端覆盖策略',
            '服务端新增覆盖策略：补充支付链路',
            '',
            '## 用户覆盖策略',
            '用户新增覆盖策略：补充退款链路',
        ].join('\n'));
    });

    it('does not auto-merge section add/delete when both sides add the same new section with different content', async () => {
        vi.mocked(updateRunArtifact).mockRejectedValue(new ArtifactConflictError(
            '产出物已被更新，请刷新后再保存',
            {
                stageId: 'STRATEGY',
                content: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '旧风险策略',
                    '',
                    '## 验收口径',
                    '旧验收口径',
                    '',
                    '## 覆盖策略',
                    '服务端新增覆盖策略：补充支付链路',
                ].join('\n'),
                versionNumber: 3,
            },
        ));
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 1,
            currentRunId: 'run-123',
            artifactContent: [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '旧风险策略',
                '',
                '## 验收口径',
                '旧验收口径',
            ].join('\n'),
            stageArtifacts: {
                STRATEGY: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '旧风险策略',
                    '',
                    '## 验收口径',
                    '旧验收口径',
                ].join('\n'),
            },
            artifactHistory: [{
                id: 'run-123-STRATEGY-v2',
                timestamp: 123,
                content: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '旧风险策略',
                    '',
                    '## 验收口径',
                    '旧验收口径',
                ].join('\n'),
                stageId: 'STRATEGY',
            }],
            artifactAuditEvents: [],
        });

        render(<ArtifactPane />);
        fireEvent.click(screen.getByTitle('编辑产出物'));
        fireEvent.change(screen.getByLabelText('编辑产出物 Markdown'), {
            target: {
                value: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '旧风险策略',
                    '',
                    '## 验收口径',
                    '旧验收口径',
                    '',
                    '## 覆盖策略',
                    '用户新增覆盖策略：补充退款链路',
                ].join('\n'),
            },
        });
        fireEvent.click(screen.getByRole('button', { name: '保存修改' }));

        await screen.findByRole('button', { name: '对比服务端版本' });
        expect(screen.queryByRole('button', { name: '自动合并非重叠变更' })).toBeNull();
    });

    it('does not auto-merge section add/delete by falling back when both sides add the same compact section differently', async () => {
        vi.mocked(updateRunArtifact).mockRejectedValue(new ArtifactConflictError(
            '产出物已被更新，请刷新后再保存',
            {
                stageId: 'STRATEGY',
                content: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '旧风险策略',
                    '## 覆盖策略',
                    '服务端新增覆盖策略',
                ].join('\n'),
                versionNumber: 3,
            },
        ));
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 1,
            currentRunId: 'run-123',
            artifactContent: [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '旧风险策略',
            ].join('\n'),
            stageArtifacts: {
                STRATEGY: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '旧风险策略',
                ].join('\n'),
            },
            artifactHistory: [{
                id: 'run-123-STRATEGY-v2',
                timestamp: 123,
                content: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '旧风险策略',
                ].join('\n'),
                stageId: 'STRATEGY',
            }],
            artifactAuditEvents: [],
        });

        render(<ArtifactPane />);
        fireEvent.click(screen.getByTitle('编辑产出物'));
        fireEvent.change(screen.getByLabelText('编辑产出物 Markdown'), {
            target: {
                value: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '旧风险策略',
                    '## 覆盖策略',
                    '用户新增覆盖策略',
                ].join('\n'),
            },
        });
        fireEvent.click(screen.getByRole('button', { name: '保存修改' }));

        await screen.findByRole('button', { name: '对比服务端版本' });
        expect(screen.queryByRole('button', { name: '自动合并非重叠变更' })).toBeNull();
    });

    it('does not auto-merge section add/delete when draft deletes a server-changed section', async () => {
        vi.mocked(updateRunArtifact).mockRejectedValue(new ArtifactConflictError(
            '产出物已被更新，请刷新后再保存',
            {
                stageId: 'STRATEGY',
                content: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '旧风险策略',
                    '',
                    '## 验收口径',
                    '旧验收口径',
                    '',
                    '## 交付计划',
                    '服务端交付计划：增加上线回滚窗口',
                ].join('\n'),
                versionNumber: 3,
            },
        ));
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 1,
            currentRunId: 'run-123',
            artifactContent: [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '旧风险策略',
                '',
                '## 验收口径',
                '旧验收口径',
                '',
                '## 交付计划',
                '旧交付计划',
            ].join('\n'),
            stageArtifacts: {
                STRATEGY: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '旧风险策略',
                    '',
                    '## 验收口径',
                    '旧验收口径',
                    '',
                    '## 交付计划',
                    '旧交付计划',
                ].join('\n'),
            },
            artifactHistory: [{
                id: 'run-123-STRATEGY-v2',
                timestamp: 123,
                content: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '旧风险策略',
                    '',
                    '## 验收口径',
                    '旧验收口径',
                    '',
                    '## 交付计划',
                    '旧交付计划',
                ].join('\n'),
                stageId: 'STRATEGY',
            }],
            artifactAuditEvents: [],
        });

        render(<ArtifactPane />);
        fireEvent.click(screen.getByTitle('编辑产出物'));
        fireEvent.change(screen.getByLabelText('编辑产出物 Markdown'), {
            target: {
                value: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '旧风险策略',
                    '',
                    '## 验收口径',
                    '旧验收口径',
                ].join('\n'),
            },
        });
        fireEvent.click(screen.getByRole('button', { name: '保存修改' }));

        await screen.findByRole('button', { name: '对比服务端版本' });
        expect(screen.queryByRole('button', { name: '自动合并非重叠变更' })).toBeNull();
    });

    it('does not auto-merge section add/delete when an unsafe section rename changes the body', async () => {
        vi.mocked(updateRunArtifact).mockRejectedValue(new ArtifactConflictError(
            '产出物已被更新，请刷新后再保存',
            {
                stageId: 'STRATEGY',
                content: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '服务端风险策略：优先覆盖支付链路',
                    '',
                    '## 验收口径',
                    '旧验收口径',
                ].join('\n'),
                versionNumber: 3,
            },
        ));
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 1,
            currentRunId: 'run-123',
            artifactContent: [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '旧风险策略',
                '',
                '## 验收口径',
                '旧验收口径',
            ].join('\n'),
            stageArtifacts: {
                STRATEGY: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '旧风险策略',
                    '',
                    '## 验收口径',
                    '旧验收口径',
                ].join('\n'),
            },
            artifactHistory: [{
                id: 'run-123-STRATEGY-v2',
                timestamp: 123,
                content: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '旧风险策略',
                    '',
                    '## 验收口径',
                    '旧验收口径',
                ].join('\n'),
                stageId: 'STRATEGY',
            }],
            artifactAuditEvents: [],
        });

        render(<ArtifactPane />);
        fireEvent.click(screen.getByTitle('编辑产出物'));
        fireEvent.change(screen.getByLabelText('编辑产出物 Markdown'), {
            target: {
                value: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '旧风险策略',
                    '',
                    '## 质量口径',
                    '用户质量口径：增加回滚检查',
                ].join('\n'),
            },
        });
        fireEvent.click(screen.getByRole('button', { name: '保存修改' }));

        await screen.findByRole('button', { name: '对比服务端版本' });
        expect(screen.queryByRole('button', { name: '自动合并非重叠变更' })).toBeNull();
    });

    it('does not auto-merge section add/delete by falling back when server adds a section and draft renames another section', async () => {
        vi.mocked(updateRunArtifact).mockRejectedValue(new ArtifactConflictError(
            '产出物已被更新，请刷新后再保存',
            {
                stageId: 'STRATEGY',
                content: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '旧风险策略',
                    '',
                    '## 验收口径',
                    '旧验收口径',
                    '',
                    '## 服务端覆盖策略',
                    '服务端新增覆盖策略：补充支付链路',
                ].join('\n'),
                versionNumber: 3,
            },
        ));
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 1,
            currentRunId: 'run-123',
            artifactContent: [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '旧风险策略',
                '',
                '## 验收口径',
                '旧验收口径',
            ].join('\n'),
            stageArtifacts: {
                STRATEGY: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '旧风险策略',
                    '',
                    '## 验收口径',
                    '旧验收口径',
                ].join('\n'),
            },
            artifactHistory: [{
                id: 'run-123-STRATEGY-v2',
                timestamp: 123,
                content: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '旧风险策略',
                    '',
                    '## 验收口径',
                    '旧验收口径',
                ].join('\n'),
                stageId: 'STRATEGY',
            }],
            artifactAuditEvents: [],
        });

        render(<ArtifactPane />);
        fireEvent.click(screen.getByTitle('编辑产出物'));
        fireEvent.change(screen.getByLabelText('编辑产出物 Markdown'), {
            target: {
                value: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '旧风险策略',
                    '',
                    '## 质量口径',
                    '旧验收口径',
                ].join('\n'),
            },
        });
        fireEvent.click(screen.getByRole('button', { name: '保存修改' }));

        await screen.findByRole('button', { name: '对比服务端版本' });
        expect(screen.queryByRole('button', { name: '自动合并非重叠变更' })).toBeNull();
    });

    it('auto-merges non-overlapping section movement during an artifact conflict', async () => {
        vi.mocked(updateRunArtifact).mockRejectedValue(new ArtifactConflictError(
            '产出物已被更新，请刷新后再保存',
            {
                stageId: 'STRATEGY',
                content: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '服务端风险策略：优先覆盖支付链路',
                    '',
                    '## 验收口径',
                    '旧验收口径',
                    '',
                    '## 交付计划',
                    '旧交付计划',
                ].join('\n'),
                versionNumber: 3,
            },
        ));
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 1,
            currentRunId: 'run-123',
            artifactContent: [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '旧风险策略',
                '',
                '## 验收口径',
                '旧验收口径',
                '',
                '## 交付计划',
                '旧交付计划',
            ].join('\n'),
            stageArtifacts: {
                STRATEGY: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '旧风险策略',
                    '',
                    '## 验收口径',
                    '旧验收口径',
                    '',
                    '## 交付计划',
                    '旧交付计划',
                ].join('\n'),
            },
            artifactHistory: [
                {
                    id: 'run-123-STRATEGY-v2',
                    timestamp: 123,
                    content: [
                        '# 测试策略蓝图',
                        '',
                        '## 风险策略',
                        '旧风险策略',
                        '',
                        '## 验收口径',
                        '旧验收口径',
                        '',
                        '## 交付计划',
                        '旧交付计划',
                    ].join('\n'),
                    stageId: 'STRATEGY',
                },
            ],
            artifactAuditEvents: [],
        });

        render(<ArtifactPane />);
        fireEvent.click(screen.getByTitle('编辑产出物'));
        fireEvent.change(screen.getByLabelText('编辑产出物 Markdown'), {
            target: {
                value: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '旧风险策略',
                    '',
                    '## 交付计划',
                    '旧交付计划',
                    '',
                    '## 验收口径',
                    '旧验收口径',
                ].join('\n'),
            },
        });
        fireEvent.click(screen.getByRole('button', { name: '保存修改' }));
        fireEvent.click(await screen.findByRole('button', { name: '自动合并非重叠变更' }));

        expect((screen.getByLabelText('编辑产出物 Markdown') as HTMLTextAreaElement).value).toBe([
            '# 测试策略蓝图',
            '',
            '## 风险策略',
            '服务端风险策略：优先覆盖支付链路',
            '',
            '## 交付计划',
            '旧交付计划',
            '',
            '## 验收口径',
            '旧验收口径',
        ].join('\n'));
        expect(useStore.getState().artifactAuditEvents).toEqual([
            expect.objectContaining({
                stageId: 'STRATEGY',
                eventType: 'artifact_auto_merge_applied',
                summary: '合并轨迹：自动合并服务端与草稿的非重叠章节移动',
            }),
        ]);
    });

    it('does not auto-merge section movement when both sides changed the same section', async () => {
        vi.mocked(updateRunArtifact).mockRejectedValue(new ArtifactConflictError(
            '产出物已被更新，请刷新后再保存',
            {
                stageId: 'STRATEGY',
                content: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '服务端风险策略：优先覆盖支付链路',
                    '',
                    '## 验收口径',
                    '旧验收口径',
                    '',
                    '## 交付计划',
                    '旧交付计划',
                ].join('\n'),
                versionNumber: 3,
            },
        ));
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 1,
            currentRunId: 'run-123',
            artifactContent: [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '旧风险策略',
                '',
                '## 验收口径',
                '旧验收口径',
                '',
                '## 交付计划',
                '旧交付计划',
            ].join('\n'),
            stageArtifacts: {
                STRATEGY: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '旧风险策略',
                    '',
                    '## 验收口径',
                    '旧验收口径',
                    '',
                    '## 交付计划',
                    '旧交付计划',
                ].join('\n'),
            },
            artifactHistory: [
                {
                    id: 'run-123-STRATEGY-v2',
                    timestamp: 123,
                    content: [
                        '# 测试策略蓝图',
                        '',
                        '## 风险策略',
                        '旧风险策略',
                        '',
                        '## 验收口径',
                        '旧验收口径',
                        '',
                        '## 交付计划',
                        '旧交付计划',
                    ].join('\n'),
                    stageId: 'STRATEGY',
                },
            ],
            artifactAuditEvents: [],
        });

        render(<ArtifactPane />);
        fireEvent.click(screen.getByTitle('编辑产出物'));
        fireEvent.change(screen.getByLabelText('编辑产出物 Markdown'), {
            target: {
                value: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '用户风险策略：优先覆盖退款链路',
                    '',
                    '## 交付计划',
                    '旧交付计划',
                    '',
                    '## 验收口径',
                    '旧验收口径',
                ].join('\n'),
            },
        });
        fireEvent.click(screen.getByRole('button', { name: '保存修改' }));

        await screen.findByRole('button', { name: '对比服务端版本' });
        expect(screen.queryByRole('button', { name: '自动合并非重叠变更' })).toBeNull();
    });

    it('does not auto-merge section movement when base headings repeat', async () => {
        vi.mocked(updateRunArtifact).mockRejectedValue(new ArtifactConflictError(
            '产出物已被更新，请刷新后再保存',
            {
                stageId: 'STRATEGY',
                content: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '服务端第一风险策略',
                    '',
                    '## 验收口径',
                    '旧验收口径',
                    '',
                    '## 风险策略',
                    '第二风险策略',
                ].join('\n'),
                versionNumber: 3,
            },
        ));
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 1,
            currentRunId: 'run-123',
            artifactContent: [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '第一风险策略',
                '',
                '## 验收口径',
                '旧验收口径',
                '',
                '## 风险策略',
                '第二风险策略',
            ].join('\n'),
            stageArtifacts: {
                STRATEGY: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '第一风险策略',
                    '',
                    '## 验收口径',
                    '旧验收口径',
                    '',
                    '## 风险策略',
                    '第二风险策略',
                ].join('\n'),
            },
            artifactHistory: [
                {
                    id: 'run-123-STRATEGY-v2',
                    timestamp: 123,
                    content: [
                        '# 测试策略蓝图',
                        '',
                        '## 风险策略',
                        '第一风险策略',
                        '',
                        '## 验收口径',
                        '旧验收口径',
                        '',
                        '## 风险策略',
                        '第二风险策略',
                    ].join('\n'),
                    stageId: 'STRATEGY',
                },
            ],
            artifactAuditEvents: [],
        });

        render(<ArtifactPane />);
        fireEvent.click(screen.getByTitle('编辑产出物'));
        fireEvent.change(screen.getByLabelText('编辑产出物 Markdown'), {
            target: {
                value: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '第一风险策略',
                    '',
                    '## 风险策略',
                    '第二风险策略',
                    '',
                    '## 验收口径',
                    '旧验收口径',
                ].join('\n'),
            },
        });
        fireEvent.click(screen.getByRole('button', { name: '保存修改' }));

        await screen.findByRole('button', { name: '对比服务端版本' });
        expect(screen.queryByRole('button', { name: '自动合并非重叠变更' })).toBeNull();
    });

    it('does not auto-merge section movement when server and draft moved sections differently', async () => {
        vi.mocked(updateRunArtifact).mockRejectedValue(new ArtifactConflictError(
            '产出物已被更新，请刷新后再保存',
            {
                stageId: 'STRATEGY',
                content: [
                    '# 测试策略蓝图',
                    '',
                    '## 验收口径',
                    '旧验收口径',
                    '',
                    '## 风险策略',
                    '旧风险策略',
                    '',
                    '## 交付计划',
                    '旧交付计划',
                ].join('\n'),
                versionNumber: 3,
            },
        ));
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 1,
            currentRunId: 'run-123',
            artifactContent: [
                '# 测试策略蓝图',
                '',
                '## 风险策略',
                '旧风险策略',
                '',
                '## 验收口径',
                '旧验收口径',
                '',
                '## 交付计划',
                '旧交付计划',
            ].join('\n'),
            stageArtifacts: {
                STRATEGY: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '旧风险策略',
                    '',
                    '## 验收口径',
                    '旧验收口径',
                    '',
                    '## 交付计划',
                    '旧交付计划',
                ].join('\n'),
            },
            artifactHistory: [
                {
                    id: 'run-123-STRATEGY-v2',
                    timestamp: 123,
                    content: [
                        '# 测试策略蓝图',
                        '',
                        '## 风险策略',
                        '旧风险策略',
                        '',
                        '## 验收口径',
                        '旧验收口径',
                        '',
                        '## 交付计划',
                        '旧交付计划',
                    ].join('\n'),
                    stageId: 'STRATEGY',
                },
            ],
            artifactAuditEvents: [],
        });

        render(<ArtifactPane />);
        fireEvent.click(screen.getByTitle('编辑产出物'));
        fireEvent.change(screen.getByLabelText('编辑产出物 Markdown'), {
            target: {
                value: [
                    '# 测试策略蓝图',
                    '',
                    '## 风险策略',
                    '旧风险策略',
                    '',
                    '## 交付计划',
                    '旧交付计划',
                    '',
                    '## 验收口径',
                    '旧验收口径',
                ].join('\n'),
            },
        });
        fireEvent.click(screen.getByRole('button', { name: '保存修改' }));

        await screen.findByRole('button', { name: '对比服务端版本' });
        expect(screen.queryByRole('button', { name: '自动合并非重叠变更' })).toBeNull();
    });

    it('does not auto-merge draft deletions when repeated base lines make the anchor ambiguous', async () => {
        vi.mocked(updateRunArtifact).mockRejectedValue(new ArtifactConflictError(
            '产出物已被更新，请刷新后再保存',
            {
                stageId: 'STRATEGY',
                content: '# 测试策略蓝图\n\n背景\n重复风险\n服务端补充\n重复风险\n共同内容',
                versionNumber: 3,
            },
        ));
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 1,
            currentRunId: 'run-123',
            artifactContent: '# 测试策略蓝图\n\n背景\n重复风险\n重复风险\n共同内容',
            stageArtifacts: {
                STRATEGY: '# 测试策略蓝图\n\n背景\n重复风险\n重复风险\n共同内容',
            },
            artifactHistory: [
                {
                    id: 'run-123-STRATEGY-v2',
                    timestamp: 123,
                    content: '# 测试策略蓝图\n\n背景\n重复风险\n重复风险\n共同内容',
                    stageId: 'STRATEGY',
                },
            ],
            artifactAuditEvents: [],
        });

        render(<ArtifactPane />);
        fireEvent.click(screen.getByTitle('编辑产出物'));
        fireEvent.change(screen.getByLabelText('编辑产出物 Markdown'), {
            target: { value: '# 测试策略蓝图\n\n背景\n重复风险\n共同内容' },
        });
        fireEvent.click(screen.getByRole('button', { name: '保存修改' }));

        await screen.findByRole('button', { name: '对比服务端版本' });
        expect(screen.queryByRole('button', { name: '自动合并非重叠变更' })).toBeNull();
    });

    it('records accepted conflict merge lines in the artifact activity trail', async () => {
        vi.mocked(updateRunArtifact).mockRejectedValue(new ArtifactConflictError(
            '产出物已被更新，请刷新后再保存',
            {
                stageId: 'STRATEGY',
                content: '# 测试策略蓝图\n\n服务端较新版本\n共同内容',
                versionNumber: 3,
            },
        ));
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 1,
            currentRunId: 'run-123',
            artifactContent: '# 测试策略蓝图\n\n版本 2\n共同内容',
            stageArtifacts: {
                STRATEGY: '# 测试策略蓝图\n\n版本 2\n共同内容',
            },
            artifactHistory: [
                {
                    id: 'run-123-STRATEGY-v2',
                    timestamp: 123,
                    content: '# 测试策略蓝图\n\n版本 2\n共同内容',
                    stageId: 'STRATEGY',
                },
            ],
            artifactAuditEvents: [],
        });

        render(<ArtifactPane />);
        fireEvent.click(screen.getByTitle('编辑产出物'));
        fireEvent.change(screen.getByLabelText('编辑产出物 Markdown'), {
            target: { value: '# 测试策略蓝图\n\n用户补充风险\n共同内容' },
        });
        fireEvent.click(screen.getByRole('button', { name: '保存修改' }));
        fireEvent.click(await screen.findByRole('button', { name: '对比服务端版本' }));
        fireEvent.click(screen.getByRole('button', { name: '采纳到草稿：用户补充风险' }));
        fireEvent.click(screen.getByTitle('历史版本'));

        expect(screen.getByText('合并轨迹：采纳草稿行「用户补充风险」')).toBeTruthy();
        expect(useStore.getState().artifactAuditEvents).toEqual([
            expect.objectContaining({
                stageId: 'STRATEGY',
                eventType: 'artifact_merge_line_accepted',
                summary: '合并轨迹：采纳草稿行「用户补充风险」',
            }),
        ]);
    });

    it('refreshes to the server artifact after conflict while preserving the draft in history', async () => {
        vi.mocked(updateRunArtifact).mockRejectedValue(new ArtifactConflictError(
            '产出物已被更新，请刷新后再保存',
            {
                stageId: 'STRATEGY',
                content: '# 测试策略蓝图\n\n服务端较新版本',
                versionNumber: 3,
            },
        ));
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 1,
            currentRunId: 'run-123',
            artifactContent: '# 测试策略蓝图\n\n版本 2',
            stageArtifacts: {
                STRATEGY: '# 测试策略蓝图\n\n版本 2',
            },
            artifactHistory: [
                {
                    id: 'run-123-STRATEGY-v2',
                    timestamp: 123,
                    content: '# 测试策略蓝图\n\n版本 2',
                    stageId: 'STRATEGY',
                },
            ],
        });

        render(<ArtifactPane />);
        fireEvent.click(screen.getByTitle('编辑产出物'));
        fireEvent.change(screen.getByLabelText('编辑产出物 Markdown'), {
            target: { value: '# 测试策略蓝图\n\n用户草稿版本' },
        });
        fireEvent.click(screen.getByRole('button', { name: '保存修改' }));
        fireEvent.click(await screen.findByRole('button', { name: '刷新为服务端版本' }));

        const state = useStore.getState();
        expect(state.artifactContent).toBe('# 测试策略蓝图\n\n服务端较新版本');
        expect(state.stageArtifacts.STRATEGY).toBe('# 测试策略蓝图\n\n服务端较新版本');
        expect(state.artifactHistory).toEqual([
            expect.objectContaining({
                id: 'run-123-STRATEGY-v2',
                content: '# 测试策略蓝图\n\n版本 2',
            }),
            expect.objectContaining({
                content: '# 测试策略蓝图\n\n用户草稿版本',
                stageId: 'STRATEGY',
            }),
            expect.objectContaining({
                id: 'run-123-STRATEGY-v3',
                content: '# 测试策略蓝图\n\n服务端较新版本',
                stageId: 'STRATEGY',
            }),
        ]);
        expect(screen.queryByLabelText('编辑产出物 Markdown')).toBeNull();
    });

    it('cancels a manual edit without changing artifact state', () => {
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 0,
            artifactContent: '# 需求分析文档\n\n原始内容',
            stageArtifacts: {
                CLARIFY: '# 需求分析文档\n\n原始内容',
            },
            artifactHistory: [],
        });

        render(<ArtifactPane />);
        fireEvent.click(screen.getByTitle('编辑产出物'));
        fireEvent.change(screen.getByLabelText('编辑产出物 Markdown'), {
            target: { value: '# 需求分析文档\n\n误修改内容' },
        });
        fireEvent.click(screen.getByRole('button', { name: '取消编辑' }));

        const state = useStore.getState();
        expect(state.artifactContent).toBe('# 需求分析文档\n\n原始内容');
        expect(state.stageArtifacts.CLARIFY).toBe('# 需求分析文档\n\n原始内容');
        expect(state.artifactHistory).toEqual([]);
        expect(screen.queryByLabelText('编辑产出物 Markdown')).toBeNull();
    });

    it('adds and removes artifact comments for the current stage from the comments panel', () => {
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 0,
            artifactContent: '# 需求分析文档\n\n登录边界需要确认。',
            artifactComments: [],
        });

        render(<ArtifactPane />);
        clickArtifactToolbarMenuItem('批注');
        fireEvent.change(screen.getByLabelText('新增批注'), {
            target: { value: '这里需要业务确认登录边界。' },
        });
        fireEvent.click(screen.getByRole('button', { name: '添加批注' }));

        expect(screen.getByText('这里需要业务确认登录边界。')).toBeTruthy();
        expect(screen.getAllByText('登录边界需要确认。').length).toBeGreaterThanOrEqual(2);
        expect(useStore.getState().artifactComments).toEqual([
            expect.objectContaining({
                stageId: 'CLARIFY',
                content: '这里需要业务确认登录边界。',
                artifactExcerpt: '登录边界需要确认。',
            }),
        ]);

        fireEvent.click(screen.getByTitle('删除批注'));

        expect(screen.queryByText('这里需要业务确认登录边界。')).toBeNull();
        expect(useStore.getState().artifactComments).toEqual([]);
    });

    it('uses selected artifact text as the comment anchor excerpt', () => {
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 0,
            artifactContent: '# 需求分析文档\n\n默认摘录不应被使用。\n\n请重点确认 SSO 回调失败后的登录边界。',
            artifactComments: [],
        });

        render(<ArtifactPane />);
        const selectedParagraph = screen.getByText('请重点确认 SSO 回调失败后的登录边界。');
        const textNode = selectedParagraph.firstChild;
        expect(textNode).toBeTruthy();
        const range = document.createRange();
        range.setStart(textNode as ChildNode, 0);
        range.setEnd(textNode as ChildNode, '请重点确认 SSO 回调失败后的登录边界。'.length);
        const selection = window.getSelection();
        selection?.removeAllRanges();
        selection?.addRange(range);

        clickArtifactToolbarMenuItem('批注');
        fireEvent.change(screen.getByLabelText('新增批注'), {
            target: { value: '这里需要业务确认登录边界。' },
        });
        fireEvent.click(screen.getByRole('button', { name: '添加批注' }));

        expect(screen.getAllByText('请重点确认 SSO 回调失败后的登录边界。').length).toBeGreaterThanOrEqual(2);
        expect(useStore.getState().artifactComments).toEqual([
            expect.objectContaining({
                content: '这里需要业务确认登录边界。',
                artifactExcerpt: '请重点确认 SSO 回调失败后的登录边界。',
                anchorText: '请重点确认 SSO 回调失败后的登录边界。',
            }),
        ]);
    });

    it('highlights anchored artifact text from an artifact comment', () => {
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 0,
            artifactContent: '# 需求分析文档\n\n默认正文。\n\n请重点确认 SSO 回调失败后的登录边界。',
            artifactComments: [
                {
                    id: 'comment-1',
                    stageId: 'CLARIFY',
                    content: '这里需要业务确认登录边界。',
                    artifactExcerpt: '请重点确认 SSO 回调失败后的登录边界。',
                    anchorText: '请重点确认 SSO 回调失败后的登录边界。',
                    createdAt: 1710000000000,
                    status: 'open',
                    resolvedAt: null,
                    replies: [],
                },
            ],
        });

        const { container } = render(<ArtifactPane />);
        clickArtifactToolbarMenuItem('批注');
        fireEvent.click(screen.getByRole('button', { name: '定位正文' }));

        const highlight = container.querySelector('[data-artifact-anchor-highlight="true"]');
        expect(highlight?.textContent).toBe('请重点确认 SSO 回调失败后的登录边界。');
    });

    it('shows stale anchor status when anchored comment text no longer exists', () => {
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 0,
            artifactContent: '# 需求分析文档\n\n登录边界已经被改写。',
            artifactComments: [
                {
                    id: 'comment-1',
                    stageId: 'CLARIFY',
                    content: '这里需要业务确认登录边界。',
                    artifactExcerpt: '请重点确认 SSO 回调失败后的登录边界。',
                    anchorText: '请重点确认 SSO 回调失败后的登录边界。',
                    createdAt: 1710000000000,
                    status: 'open',
                    resolvedAt: null,
                    replies: [],
                },
            ],
        });

        render(<ArtifactPane />);
        clickArtifactToolbarMenuItem('批注');

        expect(screen.getByText('锚点已失效')).toBeTruthy();
        expect(screen.getByText('正文已变化，请重新确认这条批注的位置。')).toBeTruthy();

        fireEvent.click(screen.getByTitle('关闭批注'));
        fireEvent.click(screen.getByRole('button', { name: '更多产物操作' }));
        fireEvent.click(screen.getByRole('menuitem', { name: '审阅' }));

        expect(screen.getByText('锚点已失效')).toBeTruthy();
    });

    it('rebinds stale comment anchor to selected artifact text and syncs it', async () => {
        vi.mocked(updateRunArtifactCollaboration).mockResolvedValue({
            artifactComments: [],
            artifactSectionLocks: [],
        });
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 0,
            currentRunId: 'run-1',
            artifactContent: '# 需求分析文档\n\n新的登录边界需要覆盖 SSO 回调。',
            artifactSectionLocks: [],
            artifactComments: [
                {
                    id: 'comment-1',
                    stageId: 'CLARIFY',
                    content: '这里需要业务确认登录边界。',
                    artifactExcerpt: '旧登录边界',
                    anchorText: '旧登录边界',
                    createdAt: 1710000000000,
                    status: 'open',
                    resolvedAt: null,
                    replies: [],
                },
            ],
        });

        const { container } = render(<ArtifactPane />);
        const selectedParagraph = screen.getByText('新的登录边界需要覆盖 SSO 回调。');
        const textNode = selectedParagraph.firstChild;
        expect(textNode).toBeTruthy();
        const range = document.createRange();
        range.setStart(textNode as ChildNode, 0);
        range.setEnd(textNode as ChildNode, '新的登录边界'.length);
        const selection = window.getSelection();
        selection?.removeAllRanges();
        selection?.addRange(range);

        clickArtifactToolbarMenuItem('批注');
        fireEvent.click(screen.getByRole('button', { name: '重新绑定选区' }));

        expect(useStore.getState().artifactComments[0]).toEqual(expect.objectContaining({
            artifactExcerpt: '新的登录边界',
            anchorText: '新的登录边界',
        }));
        await waitFor(() => {
            expect(updateRunArtifactCollaboration).toHaveBeenCalledWith(
                'run-1',
                [
                    expect.objectContaining({
                        id: 'comment-1',
                        artifactExcerpt: '新的登录边界',
                        anchorText: '新的登录边界',
                    }),
                ],
                [],
            );
        });

        fireEvent.click(screen.getByRole('button', { name: '定位正文' }));
        const highlight = container.querySelector('[data-artifact-anchor-highlight="true"]');
        expect(highlight?.textContent).toBe('新的登录边界');
    });

    it('does not rebind stale comment anchor without artifact selection', () => {
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 0,
            artifactContent: '# 需求分析文档\n\n新的登录边界需要覆盖 SSO 回调。',
            artifactSectionLocks: [],
            artifactComments: [
                {
                    id: 'comment-1',
                    stageId: 'CLARIFY',
                    content: '这里需要业务确认登录边界。',
                    artifactExcerpt: '旧登录边界',
                    anchorText: '旧登录边界',
                    createdAt: 1710000000000,
                    status: 'open',
                    resolvedAt: null,
                    replies: [],
                },
            ],
        });

        window.getSelection()?.removeAllRanges();

        render(<ArtifactPane />);
        clickArtifactToolbarMenuItem('批注');
        fireEvent.click(screen.getByRole('button', { name: '重新绑定选区' }));

        expect(screen.getByText('请先在右侧正文中选中新的批注位置。')).toBeTruthy();
        expect(useStore.getState().artifactComments[0]).toEqual(expect.objectContaining({
            artifactExcerpt: '旧登录边界',
            anchorText: '旧登录边界',
        }));
    });

    it('syncs artifact comments to the current server run', async () => {
        vi.mocked(updateRunArtifactCollaboration).mockResolvedValue({
            artifactComments: [],
            artifactSectionLocks: [],
        });
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 0,
            currentRunId: 'run-123',
            artifactContent: '# 需求分析文档\n\n登录边界需要确认。',
            artifactComments: [],
            artifactSectionLocks: [],
        });

        render(<ArtifactPane />);
        clickArtifactToolbarMenuItem('批注');
        fireEvent.change(screen.getByLabelText('新增批注'), {
            target: { value: '这里需要业务确认登录边界。' },
        });
        fireEvent.click(screen.getByRole('button', { name: '添加批注' }));

        await waitFor(() => {
            expect(updateRunArtifactCollaboration).toHaveBeenCalledWith(
                'run-123',
                [
                    expect.objectContaining({
                        stageId: 'CLARIFY',
                        content: '这里需要业务确认登录边界。',
                        artifactExcerpt: '登录边界需要确认。',
                    }),
                ],
                [],
            );
        });

        fireEvent.click(screen.getByTitle('删除批注'));

        await waitFor(() => {
            expect(updateRunArtifactCollaboration).toHaveBeenLastCalledWith(
                'run-123',
                [],
                [],
            );
        });
    });

    it('adds replies and toggles resolved state for artifact comments', async () => {
        vi.mocked(updateRunArtifactCollaboration).mockResolvedValue({
            artifactComments: [],
            artifactSectionLocks: [],
        });
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 0,
            currentRunId: 'run-123',
            artifactContent: '# 需求分析文档\n\n登录边界需要确认。',
            artifactComments: [
                {
                    id: 'comment-1',
                    stageId: 'CLARIFY',
                    content: '这里需要业务确认登录边界。',
                    artifactExcerpt: '登录边界需要确认。',
                    createdAt: 1710000000000,
                    status: 'open',
                    resolvedAt: null,
                    replies: [],
                },
            ],
            artifactSectionLocks: [],
        });

        render(<ArtifactPane />);
        clickArtifactToolbarMenuItem('批注');
        fireEvent.change(screen.getByLabelText('回复批注：这里需要业务确认登录边界。'), {
            target: { value: '已确认包含账号密码和 SSO 登录。' },
        });
        fireEvent.click(screen.getByRole('button', { name: '添加回复' }));

        expect(screen.getByText('已确认包含账号密码和 SSO 登录。')).toBeTruthy();
        expect(useStore.getState().artifactComments[0].replies).toEqual([
            expect.objectContaining({
                content: '已确认包含账号密码和 SSO 登录。',
            }),
        ]);

        await waitFor(() => {
            expect(updateRunArtifactCollaboration).toHaveBeenLastCalledWith(
                'run-123',
                [
                    expect.objectContaining({
                        id: 'comment-1',
                        replies: [
                            expect.objectContaining({
                                content: '已确认包含账号密码和 SSO 登录。',
                            }),
                        ],
                    }),
                ],
                [],
            );
        });

        fireEvent.click(screen.getByRole('button', { name: '标记已解决' }));

        expect(screen.getByText('已解决')).toBeTruthy();
        expect(useStore.getState().artifactComments[0]).toEqual(
            expect.objectContaining({
                status: 'resolved',
                resolvedAt: expect.any(Number),
            })
        );

        fireEvent.click(screen.getByRole('button', { name: '重新打开' }));

        expect(screen.getByText('未解决')).toBeTruthy();
        expect(useStore.getState().artifactComments[0]).toEqual(
            expect.objectContaining({
                status: 'open',
                resolvedAt: null,
            })
        );
    });

    it('blocks manual saves that modify a locked artifact section until it is unlocked', () => {
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 0,
            artifactContent: [
                '# 需求分析文档',
                '',
                '## 已确认范围',
                '',
                '登录边界已经确认。',
                '',
                '## 待补充问题',
                '',
                '验证码规则待确认。',
            ].join('\n'),
            stageArtifacts: {
                CLARIFY: [
                    '# 需求分析文档',
                    '',
                    '## 已确认范围',
                    '',
                    '登录边界已经确认。',
                    '',
                    '## 待补充问题',
                    '',
                    '验证码规则待确认。',
                ].join('\n'),
            },
            artifactSectionLocks: [],
            artifactHistory: [],
        });

        render(<ArtifactPane />);
        clickArtifactToolbarMenuItem('章节锁定');
        fireEvent.click(screen.getByRole('button', { name: '锁定 已确认范围' }));

        expect(useStore.getState().artifactSectionLocks).toEqual([
            expect.objectContaining({
                stageId: 'CLARIFY',
                heading: '## 已确认范围',
                content: '## 已确认范围\n\n登录边界已经确认。',
            }),
        ]);

        fireEvent.click(screen.getByTitle('编辑产出物'));
        fireEvent.change(screen.getByLabelText('编辑产出物 Markdown'), {
            target: {
                value: [
                    '# 需求分析文档',
                    '',
                    '## 已确认范围',
                    '',
                    '登录边界被误改。',
                    '',
                    '## 待补充问题',
                    '',
                    '验证码规则已补充。',
                ].join('\n'),
            },
        });
        fireEvent.click(screen.getByRole('button', { name: '保存修改' }));

        expect(screen.getByText('保存失败：锁定章节“已确认范围”已被修改，请先解锁后再保存。')).toBeTruthy();
        expect(useStore.getState().artifactContent).toContain('登录边界已经确认。');

        fireEvent.click(screen.getByRole('button', { name: '取消编辑' }));
        clickArtifactToolbarMenuItem('章节锁定');
        fireEvent.click(screen.getByTitle('解除章节锁定'));
        fireEvent.click(screen.getByTitle('编辑产出物'));
        fireEvent.change(screen.getByLabelText('编辑产出物 Markdown'), {
            target: {
                value: [
                    '# 需求分析文档',
                    '',
                    '## 已确认范围',
                    '',
                    '登录边界被授权修改。',
                    '',
                    '## 待补充问题',
                    '',
                    '验证码规则已补充。',
                ].join('\n'),
            },
        });
        fireEvent.click(screen.getByRole('button', { name: '保存修改' }));

        expect(useStore.getState().artifactContent).toContain('登录边界被授权修改。');
        expect(screen.queryByLabelText('编辑产出物 Markdown')).toBeNull();
    });

    it('locks the second duplicate artifact section without locking the first duplicate heading', () => {
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 0,
            artifactContent: [
                '# 需求分析文档',
                '',
                '## 验收口径',
                '',
                '第一个验收口径保持可调整。',
                '',
                '## 验收口径',
                '',
                '第二个验收口径已经确认。',
            ].join('\n'),
            stageArtifacts: {
                CLARIFY: [
                    '# 需求分析文档',
                    '',
                    '## 验收口径',
                    '',
                    '第一个验收口径保持可调整。',
                    '',
                    '## 验收口径',
                    '',
                    '第二个验收口径已经确认。',
                ].join('\n'),
            },
            artifactSectionLocks: [],
            artifactHistory: [],
        });

        render(<ArtifactPane />);
        clickArtifactToolbarMenuItem('章节锁定');
        fireEvent.click(screen.getByRole('button', { name: '锁定 验收口径 #2' }));

        expect(useStore.getState().artifactSectionLocks).toEqual([
            expect.objectContaining({
                stageId: 'CLARIFY',
                heading: '## 验收口径',
                content: '## 验收口径\n\n第二个验收口径已经确认。',
                sectionAnchor: expect.stringContaining('验收口径:2'),
            }),
        ]);
        expect(screen.getByRole('button', { name: '锁定 验收口径 #1' })).toBeTruthy();
        expect(screen.getByLabelText('解除章节锁定 验收口径 #2')).toBeTruthy();

        fireEvent.click(screen.getByTitle('编辑产出物'));
        fireEvent.change(screen.getByLabelText('编辑产出物 Markdown'), {
            target: {
                value: [
                    '# 需求分析文档',
                    '',
                    '## 验收口径',
                    '',
                    '第一个验收口径已调整。',
                    '',
                    '## 验收口径',
                    '',
                    '第二个验收口径已经确认。',
                ].join('\n'),
            },
        });
        fireEvent.click(screen.getByRole('button', { name: '保存修改' }));

        expect(screen.queryByLabelText('编辑产出物 Markdown')).toBeNull();
        expect(useStore.getState().artifactContent).toContain('第一个验收口径已调整。');

        fireEvent.click(screen.getByTitle('编辑产出物'));
        fireEvent.change(screen.getByLabelText('编辑产出物 Markdown'), {
            target: {
                value: [
                    '# 需求分析文档',
                    '',
                    '## 验收口径',
                    '',
                    '第一个验收口径已调整。',
                    '',
                    '## 验收口径',
                    '',
                    '第二个验收口径被误改。',
                ].join('\n'),
            },
        });
        fireEvent.click(screen.getByRole('button', { name: '保存修改' }));

        expect(screen.getByText('保存失败：锁定章节“验收口径 #2”已被修改，请先解锁后再保存。')).toBeTruthy();
        expect(useStore.getState().artifactContent).toContain('第二个验收口径已经确认。');
    });
});
