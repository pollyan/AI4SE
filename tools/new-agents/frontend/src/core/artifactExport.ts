import {
    parseStructuredVisual,
    type NodeEdgeStructuredVisual,
    type TimelineStructuredVisual,
} from './structuredVisuals';
import { stripInlineMarkdownToText } from './markdownPlainText';

const PDF_LINES_PER_PAGE = 42;

type PdfMermaidDiagramKind = 'flowchart' | 'timeline' | 'mindmap' | 'pie' | 'journey';

type PdfMermaidDiagram = {
    kind: PdfMermaidDiagramKind;
    startLineIndex: number;
    lineCount: number;
    rectangleCount: number;
    curveCount?: number;
};

type PdfStructuredVisualTable = {
    startLineIndex: number;
    columns: string[];
    rows: string[][];
};

type PdfProjectedDocument = {
    lines: string[];
    structuredTables: PdfStructuredVisualTable[];
    mermaidDiagrams: PdfMermaidDiagram[];
};

export function toUtf16BeHex(content: string): string {
    const codeUnits = Array.from(content);
    return `FEFF${codeUnits.map((character) => {
        const codePoint = character.codePointAt(0) ?? 0x20;
        if (codePoint > 0xffff) {
            const adjusted = codePoint - 0x10000;
            const high = 0xd800 + (adjusted >> 10);
            const low = 0xdc00 + (adjusted & 0x3ff);
            return `${high.toString(16).padStart(4, '0')}${low.toString(16).padStart(4, '0')}`;
        }
        return codePoint.toString(16).padStart(4, '0');
    }).join('')}`.toUpperCase();
}

function stripInlineMarkdown(content: string): string {
    return stripInlineMarkdownToText(content).trim();
}

function isFenceStart(line: string): boolean {
    return /^```/.test(line.trim());
}

function getFenceLanguage(line: string): string {
    return line.trim().replace(/^```/, '').trim().toLowerCase();
}

function isBulletItem(line: string): boolean {
    return /^\s*[-*]\s+/.test(line);
}

function isNumberedItem(line: string): boolean {
    return /^\s*\d+[.)]\s+/.test(line);
}

function isTableRow(line: string): boolean {
    return line.trim().includes('|');
}

function splitTableRow(line: string): string[] {
    return line.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map(cell => cell.trim());
}

function isTableSeparator(line: string): boolean {
    const cells = splitTableRow(line);
    return cells.length > 0 && cells.every(cell => /^:?-{3,}:?$/.test(cell.trim()));
}

function formatPdfTableRows(rows: string[][]): string[] {
    return rows.map(row => row.join('    ').trimEnd());
}

function formatPdfNodeEdgeVisualLines(visual: NodeEdgeStructuredVisual): string[] {
    const lines: string[] = [`结构化可视化：${visual.title || visual.type}`, '节点：'];
    visual.nodes.forEach((node) => {
        lines.push(`${node.label} ${node.title}${node.description ? `：${node.description}` : ''}`);
        if (node.category) lines.push(`类型：${node.category}`);
        if (node.evidence) lines.push(`证据：${node.evidence}`);
        if (node.confidence) lines.push(`置信度：${node.confidence}`);
        if (node.status) lines.push(`状态：${node.status}`);
    });

    lines.push('连接：');
    if (!visual.edges.length) {
        lines.push('无');
        return lines;
    }
    visual.edges.forEach((edge) => {
        lines.push(`${edge.source} -> ${edge.target}${edge.label ? `：${edge.label}` : ''}`);
    });
    return lines;
}

function formatPdfTimelineVisualLines(visual: TimelineStructuredVisual): string[] {
    const lines: string[] = [`结构化可视化：${visual.title || visual.type}`];
    visual.events.forEach((event) => {
        lines.push(`${event.time}  ${event.title}`);
        lines.push(event.description);
        lines.push(`关联事实：${event.factIds.join('、')}`);
    });
    return lines;
}

function cleanMermaidLabel(source: string): string {
    let label = source.trim();
    const labelMatch = label.match(/\[([^\]]+)\]|\(([^)]+)\)|\{([^}]+)\}/);
    label = labelMatch?.[1] || labelMatch?.[2] || labelMatch?.[3] || label;
    label = label
        .replace(/^root\s*/i, '')
        .replace(/^\(\(|\)\)$/g, '')
        .replace(/^\[\[|\]\]$/g, '')
        .replace(/^[[({"'“”]+|[\])}"'“”]+$/g, '')
        .trim();
    return stripInlineMarkdown(label);
}

function cleanMermaidPieLabel(source: string): string {
    return stripInlineMarkdown(source.trim().replace(/^["'“”]+|["'“”]+$/g, '').trim());
}

function parseMermaidFlowchart(source: string, startLineIndex: number): {
    lines: string[];
    diagram: PdfMermaidDiagram;
} {
    const mermaidLines = source.split(/\r?\n/).map(line => line.trim()).filter(Boolean);
    const labels: string[] = [];
    mermaidLines.slice(1).forEach((line) => {
        line.split(/\s*(?:-->|---|==>|-.->)\s*/).forEach((endpoint) => {
            const label = cleanMermaidLabel(endpoint);
            if (label && !labels.includes(label)) {
                labels.push(label);
            }
        });
    });
    const projectedLines = [
        'Mermaid 图表：flowchart',
        ...labels,
        ...mermaidLines.slice(1),
    ];
    return {
        lines: projectedLines,
        diagram: {
            kind: 'flowchart',
            startLineIndex,
            lineCount: Math.max(projectedLines.length, 2),
            rectangleCount: Math.max(labels.length, 3),
        },
    };
}

function parseMermaidTimeline(source: string, startLineIndex: number): {
    lines: string[];
    diagram: PdfMermaidDiagram;
} {
    const projectedLines = ['Mermaid 图表：timeline'];
    let eventCount = 0;
    source.split(/\r?\n/).map(line => line.trim()).filter(Boolean).slice(1).forEach((line) => {
        if (line.startsWith('title ')) {
            projectedLines.push(stripInlineMarkdown(line.replace(/^title\s+/, '')));
            return;
        }
        if (line.startsWith('section ')) {
            projectedLines.push(stripInlineMarkdown(line.replace(/^section\s+/, '')));
            return;
        }
        const eventMatch = line.match(/^(.+?)\s*:\s*(.+)$/);
        if (!eventMatch) return;
        eventCount += 1;
        projectedLines.push(`${stripInlineMarkdown(eventMatch[1])}：${stripInlineMarkdown(eventMatch[2])}`);
    });
    return {
        lines: projectedLines,
        diagram: {
            kind: 'timeline',
            startLineIndex,
            lineCount: Math.max(projectedLines.length, 3),
            rectangleCount: Math.max(eventCount, 3),
        },
    };
}

function parseMermaidMindmap(source: string, startLineIndex: number): {
    lines: string[];
    diagram: PdfMermaidDiagram;
} {
    const labels = source
        .split(/\r?\n/)
        .slice(1)
        .map(cleanMermaidLabel)
        .filter(Boolean)
        .slice(0, 12);
    const projectedLines = ['Mermaid 图表：mindmap', ...labels];
    return {
        lines: projectedLines,
        diagram: {
            kind: 'mindmap',
            startLineIndex,
            lineCount: Math.max(projectedLines.length, 2),
            rectangleCount: Math.max(labels.length, 5),
        },
    };
}

function parseMermaidPie(source: string, startLineIndex: number): {
    lines: string[];
    diagram: PdfMermaidDiagram;
} {
    const mermaidLines = source.split(/\r?\n/).map(line => line.trim()).filter(Boolean);
    const projectedLines = ['Mermaid 图表：pie'];
    const inlineTitleMatch = mermaidLines[0]?.match(/^pie\s+title\s+(.+)$/i);
    if (inlineTitleMatch) {
        projectedLines.push(stripInlineMarkdown(inlineTitleMatch[1]));
    }
    let sliceCount = 0;
    mermaidLines.slice(1).forEach((line) => {
        if (line.startsWith('title ')) {
            projectedLines.push(stripInlineMarkdown(line.replace(/^title\s+/, '')));
            return;
        }
        const sliceMatch = line.match(/^(.+?)\s*:\s*([+-]?\d+(?:\.\d+)?)\s*$/);
        if (!sliceMatch) return;
        sliceCount += 1;
        projectedLines.push(`${cleanMermaidPieLabel(sliceMatch[1])}：${sliceMatch[2]}`);
    });
    return {
        lines: projectedLines,
        diagram: {
            kind: 'pie',
            startLineIndex,
            lineCount: Math.max(projectedLines.length, 2),
            rectangleCount: Math.max(sliceCount, 3),
            curveCount: 4,
        },
    };
}

function parseMermaidJourney(source: string, startLineIndex: number): {
    lines: string[];
    diagram: PdfMermaidDiagram;
} {
    const projectedLines = ['Mermaid 图表：journey'];
    let taskCount = 0;
    source.split(/\r?\n/).map(line => line.trim()).filter(Boolean).slice(1).forEach((line) => {
        if (line.startsWith('title ')) {
            projectedLines.push(stripInlineMarkdown(line.replace(/^title\s+/, '')));
            return;
        }
        if (line.startsWith('section ')) {
            projectedLines.push(stripInlineMarkdown(line.replace(/^section\s+/, '')));
            return;
        }
        const taskMatch = line.match(/^(.+?)\s*:\s*([+-]?\d+(?:\.\d+)?)\s*(?::\s*(.+))?$/);
        if (!taskMatch) return;
        taskCount += 1;
        projectedLines.push(
            `${stripInlineMarkdown(taskMatch[1])}：${stripInlineMarkdown(taskMatch[2])}`
            + `${taskMatch[3] ? `（${stripInlineMarkdown(taskMatch[3])}）` : ''}`
        );
    });
    return {
        lines: projectedLines,
        diagram: {
            kind: 'journey',
            startLineIndex,
            lineCount: Math.max(projectedLines.length, 3),
            rectangleCount: Math.max(taskCount + 1, 4),
        },
    };
}

function projectMermaidToPdf(source: string, startLineIndex: number): {
    lines: string[];
    diagram: PdfMermaidDiagram;
} {
    const firstLine = source.split(/\r?\n/).map(line => line.trim()).find(Boolean) ?? 'diagram';
    const diagramType = firstLine.split(/\s+/)[0] || 'diagram';
    if (diagramType === 'timeline') return parseMermaidTimeline(source, startLineIndex);
    if (diagramType === 'mindmap') return parseMermaidMindmap(source, startLineIndex);
    if (diagramType === 'pie') return parseMermaidPie(source, startLineIndex);
    if (diagramType === 'journey') return parseMermaidJourney(source, startLineIndex);
    return parseMermaidFlowchart(source, startLineIndex);
}

function projectMarkdownToPdfDocument(content: string): PdfProjectedDocument {
    const lines = content.split(/\r?\n/);
    const pdfLines: string[] = [];
    const structuredTables: PdfStructuredVisualTable[] = [];
    const mermaidDiagrams: PdfMermaidDiagram[] = [];
    let index = 0;

    while (index < lines.length) {
        const line = lines[index];
        const trimmedLine = line.trim();
        const nextLine = lines[index + 1];

        if (!trimmedLine) {
            pdfLines.push(' ');
            index += 1;
            continue;
        }

        if (isFenceStart(trimmedLine)) {
            const fenceLanguage = getFenceLanguage(trimmedLine);
            index += 1;
            const codeLines: string[] = [];
            while (index < lines.length && !isFenceStart(lines[index])) {
                codeLines.push(lines[index]);
                index += 1;
            }
            if (index < lines.length) index += 1;
            const codeSource = codeLines.join('\n');
            if (fenceLanguage === 'mermaid') {
                const startLineIndex = pdfLines.length;
                const mermaidProjection = projectMermaidToPdf(codeSource, startLineIndex);
                pdfLines.push(...mermaidProjection.lines);
                mermaidDiagrams.push(mermaidProjection.diagram);
                continue;
            }
            if (fenceLanguage === 'ai4se-visual') {
                const visualResult = parseStructuredVisual(codeSource);
                if (visualResult.valid === false) {
                    pdfLines.push(`结构化可视化错误：${visualResult.message}`);
                    continue;
                }
                const { visual } = visualResult;
                const startLineIndex = pdfLines.length;
                if (visual.kind === 'node-edge' || visual.kind === 'flow') {
                    pdfLines.push(...formatPdfNodeEdgeVisualLines(visual));
                    continue;
                }
                if (visual.kind === 'timeline') {
                    pdfLines.push(...formatPdfTimelineVisualLines(visual));
                    continue;
                }
                if (visual.kind === 'matrix') {
                    const rows = visual.rows.map(row => row.cells);
                    pdfLines.push(
                        `结构化可视化：${visual.title || visual.type}`,
                        ...formatPdfTableRows([visual.columns, ...rows])
                    );
                    structuredTables.push({
                        startLineIndex,
                        columns: visual.columns,
                        rows,
                    });
                }
                continue;
            }
            codeLines.forEach(codeLine => pdfLines.push(`    ${codeLine}`));
            continue;
        }

        const headingMatch = line.match(/^(#{1,3})\s+(.+)$/);
        if (headingMatch) {
            pdfLines.push(stripInlineMarkdown(headingMatch[2]));
            index += 1;
            continue;
        }

        if (isTableRow(line) && nextLine && isTableSeparator(nextLine)) {
            const rows = [splitTableRow(line).map(stripInlineMarkdown)];
            index += 2;
            while (index < lines.length && isTableRow(lines[index]) && !isTableSeparator(lines[index])) {
                rows.push(splitTableRow(lines[index]).map(stripInlineMarkdown));
                index += 1;
            }
            const tableLines = formatPdfTableRows(rows);
            const separatorLength = Math.max(...tableLines.map(tableLine => tableLine.length), 1);
            pdfLines.push(tableLines[0], '-'.repeat(separatorLength), ...tableLines.slice(1));
            continue;
        }

        if (isBulletItem(line)) {
            while (index < lines.length && isBulletItem(lines[index])) {
                pdfLines.push(`• ${stripInlineMarkdown(lines[index].replace(/^\s*[-*]\s+/, ''))}`);
                index += 1;
            }
            continue;
        }

        if (isNumberedItem(line)) {
            pdfLines.push(stripInlineMarkdown(line));
            index += 1;
            continue;
        }

        pdfLines.push(stripInlineMarkdown(line));
        index += 1;
    }

    return { lines: pdfLines, structuredTables, mermaidDiagrams };
}

function buildPdfTableDrawingCommands(pageStartLineIndex: number, tables: PdfStructuredVisualTable[]): string[] {
    const commands: string[] = [];
    const pageEndLineIndex = pageStartLineIndex + PDF_LINES_PER_PAGE;
    const tableLeft = 50;
    const tableWidth = 512;
    const rowHeight = 18;

    tables.forEach((table) => {
        const tableLineStartIndex = table.startLineIndex + 1;
        const tableLineEndIndex = tableLineStartIndex + 1 + table.rows.length;
        const visibleStartLineIndex = Math.max(tableLineStartIndex, pageStartLineIndex);
        const visibleEndLineIndex = Math.min(tableLineEndIndex, pageEndLineIndex);
        if (visibleStartLineIndex >= visibleEndLineIndex) return;

        const localStartLineIndex = visibleStartLineIndex - pageStartLineIndex;
        const columnCount = Math.max(table.columns.length, 1);
        const visibleRowCount = visibleEndLineIndex - visibleStartLineIndex;
        const desiredTableHeight = visibleRowCount * rowHeight;
        const topY = 790 - localStartLineIndex * 14 + 4;
        const bottomY = Math.max(70, topY - desiredTableHeight);
        const tableHeight = topY - bottomY;
        const rightX = tableLeft + tableWidth;
        const columnWidth = tableWidth / columnCount;

        commands.push(`${tableLeft} ${bottomY} ${tableWidth} ${tableHeight} re S`);
        for (let columnIndex = 1; columnIndex < columnCount; columnIndex += 1) {
            const x = Number((tableLeft + columnWidth * columnIndex).toFixed(2));
            commands.push(`${x} ${bottomY} m ${x} ${bottomY + tableHeight} l S`);
        }
        for (let rowIndex = 1; rowIndex < visibleRowCount; rowIndex += 1) {
            const y = Number((bottomY + rowHeight * rowIndex).toFixed(2));
            commands.push(`${tableLeft} ${y} m ${rightX} ${y} l S`);
        }
    });

    return commands.length > 0
        ? ['q', '0.45 w', '0.23 0.38 0.62 RG', ...commands, 'Q']
        : [];
}

function buildPdfMermaidDrawingCommands(pageStartLineIndex: number, diagrams: PdfMermaidDiagram[]): string[] {
    const commands: string[] = [];
    const pageEndLineIndex = pageStartLineIndex + PDF_LINES_PER_PAGE;

    diagrams.forEach((diagram, diagramIndex) => {
        const diagramEndLineIndex = diagram.startLineIndex + diagram.lineCount;
        if (diagram.startLineIndex >= pageEndLineIndex || diagramEndLineIndex <= pageStartLineIndex) return;

        const topY = Math.min(
            770,
            790 - (Math.max(diagram.startLineIndex, pageStartLineIndex) - pageStartLineIndex) * 14 - 2
        );
        const baseX = diagram.kind === 'flowchart' ? 385 : 62;
        const baseY = Math.max(110, topY - 40);
        commands.push(`${baseX} ${baseY} m ${Math.min(baseX + 480, 542)} ${baseY} l S`);
        for (let index = 0; index < diagram.rectangleCount; index += 1) {
            const x = Math.min(460, baseX + (index % 4) * 118);
            const y = Math.max(82, baseY - Math.floor(index / 4) * 32 + (index % 2 === 0 ? 24 : -24));
            commands.push(`${x} ${y} 96 22 re S`);
            commands.push(`${x + 48} ${baseY} m ${x + 48} ${y} l S`);
        }
        for (let curveIndex = 0; curveIndex < (diagram.curveCount ?? 0); curveIndex += 1) {
            const y = baseY - curveIndex * 4;
            commands.push(`${120 + diagramIndex} ${y + 42} m ${144 + diagramIndex} ${y + 64} 168 ${y + 64} 192 ${y + 42} c S`);
        }
    });

    return commands.length > 0
        ? ['q', '0.7 w', '0.18 0.55 0.95 RG', ...commands, 'Q']
        : [];
}

function buildPdfContentStream(
    lines: string[],
    pageStartLineIndex: number,
    tables: PdfStructuredVisualTable[],
    mermaidDiagrams: PdfMermaidDiagram[]
): string {
    const drawingCommands = [
        ...buildPdfMermaidDrawingCommands(pageStartLineIndex, mermaidDiagrams),
        ...buildPdfTableDrawingCommands(pageStartLineIndex, tables),
    ];
    const textCommands = lines.map((line) => `<${toUtf16BeHex(line || ' ')}> Tj T*`);
    return [
        ...drawingCommands,
        'BT',
        '/F1 11 Tf',
        '50 790 Td',
        '14 TL',
        ...textCommands,
        'ET',
    ].join('\n');
}

export function buildPlainTextPdf(content: string): string {
    const projectedDocument = projectMarkdownToPdfDocument(content);
    const sourceLines = projectedDocument.lines;
    const pages = sourceLines.length > 0
        ? Array.from(
            { length: Math.ceil(sourceLines.length / PDF_LINES_PER_PAGE) },
            (_, pageIndex) => sourceLines.slice(
                pageIndex * PDF_LINES_PER_PAGE,
                (pageIndex + 1) * PDF_LINES_PER_PAGE
            )
        )
        : [[' ']];
    const fontObjectId = 3 + pages.length * 2;
    const pageObjectIds = pages.map((_, pageIndex) => 3 + pageIndex * 2);
    const objects = [
        '1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n',
        `2 0 obj\n<< /Type /Pages /Kids [${pageObjectIds.map(id => `${id} 0 R`).join(' ')}] /Count ${pages.length} >>\nendobj\n`,
    ];

    pages.forEach((pageLines, pageIndex) => {
        const pageObjectId = 3 + pageIndex * 2;
        const contentObjectId = pageObjectId + 1;
        const stream = buildPdfContentStream(
            pageLines,
            pageIndex * PDF_LINES_PER_PAGE,
            projectedDocument.structuredTables,
            projectedDocument.mermaidDiagrams
        );
        objects.push(
            `${pageObjectId} 0 obj\n`
            + `<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] /Resources << /Font << /F1 ${fontObjectId} 0 R >> >> /Contents ${contentObjectId} 0 R >>\n`
            + 'endobj\n',
            `${contentObjectId} 0 obj\n<< /Length ${stream.length} >>\nstream\n${stream}\nendstream\nendobj\n`
        );
    });

    objects.push(
        `${fontObjectId} 0 obj\n<< /Type /Font /Subtype /Type0 /BaseFont /HeiseiKakuGo-W5 /Encoding /UniJIS-UCS2-H >>\nendobj\n`
    );

    const header = '%PDF-1.4\n';
    let offset = header.length;
    const offsets = [0];
    const body = objects.map((object) => {
        offsets.push(offset);
        offset += object.length;
        return object;
    }).join('');
    const xrefOffset = offset;
    const xrefEntries = [
        '0000000000 65535 f ',
        ...offsets.slice(1).map(value => `${String(value).padStart(10, '0')} 00000 n `),
    ];
    const objectCount = objects.length + 1;
    return [
        header,
        body,
        `xref\n0 ${objectCount}\n`,
        ...xrefEntries.map(entry => `${entry}\n`),
        `trailer\n<< /Root 1 0 R /Size ${objectCount} >>\nstartxref\n${xrefOffset}\n%%EOF`,
    ].join('');
}
