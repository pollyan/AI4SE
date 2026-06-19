import { describe, it, expect, beforeEach, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
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
    const icons = ['Download', 'Code', 'Eye', 'History', 'X', 'AlertTriangle', 'GitCompare', 'Edit3', 'Save', 'MessageSquare', 'Trash2', 'Lock', 'Unlock'];
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
            currentRunId: null,
            isGenerating: false,
        });
    });

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

    it('renders mermaid diagrams', () => {
        useStore.setState({ artifactContent: '```mermaid\ngraph TD\nA-->B\n```' });
        render(<ArtifactPane />);
        expect(screen.getByTestId('mermaid')).toBeTruthy();
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
        fireEvent.click(screen.getByTitle('下载'));
        fireEvent.click(screen.getByRole('button', { name: 'Markdown' }));

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
        fireEvent.click(screen.getByTitle('下载'));
        fireEvent.click(screen.getByRole('button', { name: 'Word' }));

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
        fireEvent.click(screen.getByTitle('下载'));
        fireEvent.click(screen.getByRole('button', { name: 'PDF' }));

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
        fireEvent.click(screen.getByTitle('下载'));
        fireEvent.click(screen.getByRole('button', { name: 'PDF' }));

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
        fireEvent.click(screen.getByTitle('下载'));
        fireEvent.click(screen.getByRole('button', { name: 'PDF' }));

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
        fireEvent.click(screen.getByTitle('下载'));
        fireEvent.click(screen.getByRole('button', { name: 'PDF' }));

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
        fireEvent.click(screen.getByTitle('下载'));
        fireEvent.click(screen.getByRole('button', { name: 'PDF' }));

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
        fireEvent.click(screen.getByTitle('下载'));
        fireEvent.click(screen.getByRole('button', { name: 'PDF' }));

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
        fireEvent.click(screen.getByTitle('下载'));
        fireEvent.click(screen.getByRole('button', { name: 'PDF' }));

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
        fireEvent.click(screen.getByTitle('批注'));
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

        fireEvent.click(screen.getByTitle('批注'));
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
        fireEvent.click(screen.getByTitle('批注'));
        fireEvent.click(screen.getByRole('button', { name: '定位正文' }));

        const highlight = container.querySelector('[data-artifact-anchor-highlight="true"]');
        expect(highlight?.textContent).toBe('请重点确认 SSO 回调失败后的登录边界。');
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
        fireEvent.click(screen.getByTitle('批注'));
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
        fireEvent.click(screen.getByTitle('批注'));
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
        fireEvent.click(screen.getByTitle('章节锁定'));
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
        fireEvent.click(screen.getByTitle('章节锁定'));
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
});
