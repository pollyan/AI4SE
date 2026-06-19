import { describe, expect, it } from 'vitest';
import { buildDocxPackage } from '../docxExport';

const readStoredZipEntries = async (blob: Blob): Promise<Record<string, string>> => {
    const bytes = new Uint8Array(await blob.arrayBuffer());
    const view = new DataView(bytes.buffer);
    const decoder = new TextDecoder();
    const entries: Record<string, string> = {};
    let offset = 0;

    while (offset + 30 <= bytes.length && view.getUint32(offset, true) === 0x04034b50) {
        const compressionMethod = view.getUint16(offset + 8, true);
        const compressedSize = view.getUint32(offset + 18, true);
        const fileNameLength = view.getUint16(offset + 26, true);
        const extraLength = view.getUint16(offset + 28, true);
        const fileNameStart = offset + 30;
        const fileNameEnd = fileNameStart + fileNameLength;
        const contentStart = fileNameEnd + extraLength;
        const contentEnd = contentStart + compressedSize;
        const fileName = decoder.decode(bytes.slice(fileNameStart, fileNameEnd));

        expect(compressionMethod).toBe(0);
        entries[fileName] = decoder.decode(bytes.slice(contentStart, contentEnd));
        offset = contentEnd;
    }

    return entries;
};

describe('docxExport', () => {
    it('builds a real DOCX package with required OOXML entries and escaped Markdown content', async () => {
        const blob = buildDocxPackage([
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
        ].join('\n'));

        expect(blob.type).toBe('application/vnd.openxmlformats-officedocument.wordprocessingml.document');

        const bytes = new Uint8Array(await blob.arrayBuffer());
        expect(bytes[0]).toBe(0x50);
        expect(bytes[1]).toBe(0x4b);

        const entries = await readStoredZipEntries(blob);
        expect(Object.keys(entries)).toEqual(expect.arrayContaining([
            '[Content_Types].xml',
            '_rels/.rels',
            'word/document.xml',
            'word/styles.xml',
        ]));
        expect(entries['[Content_Types].xml']).toContain('wordprocessingml.document.main+xml');
        expect(entries['[Content_Types].xml']).toContain('styles+xml');
        expect(entries['_rels/.rels']).toContain('officeDocument');

        const documentXml = entries['word/document.xml'];
        expect(documentXml).toContain('<w:document');
        expect(documentXml).toContain('<w:tbl>');
        expect(documentXml).toContain('<w:tr>');
        expect(documentXml).toContain('<w:tc>');
        expect(documentXml).toContain('测试报告');
        expect(documentXml).toContain('重点');
        expect(documentXml).toContain('风险覆盖');
        expect(documentXml).toContain('模块');
        expect(documentXml).toContain('状态');
        expect(documentXml).toContain('登录');
        expect(documentXml).toContain('Given 用户已登录');
        expect(documentXml).toContain('&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;');
        expect(documentXml).not.toContain('<script>alert("x")</script>');
        expect(documentXml).not.toContain('# 测试报告');
        expect(documentXml).not.toContain('模块 | 状态');

        const stylesXml = entries['word/styles.xml'];
        expect(stylesXml).toContain('<w:styles');
        expect(stylesXml).toContain('Heading1');
        expect(stylesXml).toContain('TableGrid');
    });

    it('projects Mermaid and structured visual fences into readable DOCX content', async () => {
        const blob = buildDocxPackage([
            '# 可视化交付物',
            '',
            '```mermaid',
            'flowchart TD',
            'A[用户入口] --> B[认证服务]',
            'B --> C[订单服务]',
            '```',
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
            '',
            '```ai4se-visual',
            '{ broken',
            '```',
        ].join('\n'));

        const entries = await readStoredZipEntries(blob);
        const documentXml = entries['word/document.xml'];

        expect(documentXml).toContain('Mermaid 图表：flowchart');
        expect(documentXml).toContain('用户入口');
        expect(documentXml).toContain('认证服务');
        expect(documentXml).toContain('订单服务');
        expect(documentXml).toContain('结构化可视化：核心风险矩阵');
        expect(documentXml).toContain('<w:tbl>');
        expect(documentXml).toContain('风险');
        expect(documentXml).toContain('RPN');
        expect(documentXml).toContain('登录失败');
        expect(documentXml).toContain('补充异常路径用例');
        expect(documentXml).toContain('结构化可视化错误：结构化可视化必须是合法 JSON。');
        expect(documentXml).not.toContain('```mermaid');
        expect(documentXml).not.toContain('```ai4se-visual');
        expect(documentXml).not.toContain('flowchart TD');
        expect(documentXml).not.toContain('A[用户入口] --&gt; B[认证服务]');
        expect(documentXml).not.toContain('&quot;type&quot;');
        expect(documentXml).not.toContain('&quot;rows&quot;');
        expect(documentXml).not.toContain('Consolas');
    });
});
