import { parseStructuredVisual } from './structuredVisuals';

const DOCX_MIME_TYPE = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';

type ZipEntry = {
    fileName: string;
    bytes: Uint8Array;
    crc32: number;
    localHeaderOffset: number;
};

const textEncoder = new TextEncoder();

const xmlEscape = (content: string): string => (
    content
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&apos;')
);

const stripInlineMarkdown = (content: string): string => (
    content
        .replace(/`([^`]+)`/g, '$1')
        .replace(/\*\*([^*]+)\*\*/g, '$1')
        .replace(/\*([^*]+)\*/g, '$1')
        .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
);

const isFenceStart = (line: string): boolean => /^```/.test(line.trim());
const getFenceLanguage = (line: string): string => (
    line.trim().replace(/^```/, '').trim().split(/\s+/)[0] || ''
);
const isBulletItem = (line: string): boolean => /^\s*[-*]\s+/.test(line);
const isNumberedItem = (line: string): boolean => /^\s*\d+[.)]\s+/.test(line);
const isTableRow = (line: string): boolean => line.trim().includes('|');

const splitTableRow = (line: string): string[] => (
    line
        .trim()
        .replace(/^\|/, '')
        .replace(/\|$/, '')
        .split('|')
        .map(cell => stripInlineMarkdown(cell.trim()))
);

const isTableSeparator = (line: string): boolean => {
    const cells = splitTableRow(line);
    return cells.length > 1 && cells.every(cell => /^:?-{3,}:?$/.test(cell));
};

const paragraph = (content: string, style?: string): string => {
    const styleXml = style ? `<w:pPr><w:pStyle w:val="${style}"/></w:pPr>` : '';
    return `<w:p>${styleXml}<w:r><w:t xml:space="preserve">${xmlEscape(content || ' ')}</w:t></w:r></w:p>`;
};

const codeParagraph = (content: string): string => (
    '<w:p><w:r><w:rPr><w:rFonts w:ascii="Consolas" w:hAnsi="Consolas"/></w:rPr>'
    + `<w:t xml:space="preserve">${xmlEscape(content || ' ')}</w:t></w:r></w:p>`
);

const tableCell = (content: string): string => (
    '<w:tc>'
    + '<w:tcPr><w:tcW w:w="2400" w:type="dxa"/></w:tcPr>'
    + paragraph(content)
    + '</w:tc>'
);

const tableRow = (cells: string[]): string => (
    `<w:tr>${cells.map(tableCell).join('')}</w:tr>`
);

const table = (rows: string[][]): string => (
    '<w:tbl>'
    + '<w:tblPr>'
    + '<w:tblStyle w:val="TableGrid"/>'
    + '<w:tblW w:w="0" w:type="auto"/>'
    + '<w:tblBorders>'
    + '<w:top w:val="single" w:sz="4" w:space="0" w:color="B8C7D9"/>'
    + '<w:left w:val="single" w:sz="4" w:space="0" w:color="B8C7D9"/>'
    + '<w:bottom w:val="single" w:sz="4" w:space="0" w:color="B8C7D9"/>'
    + '<w:right w:val="single" w:sz="4" w:space="0" w:color="B8C7D9"/>'
    + '<w:insideH w:val="single" w:sz="4" w:space="0" w:color="D6E0EA"/>'
    + '<w:insideV w:val="single" w:sz="4" w:space="0" w:color="D6E0EA"/>'
    + '</w:tblBorders>'
    + '</w:tblPr>'
    + rows.map(tableRow).join('')
    + '</w:tbl>'
);

type MermaidDocxNode = {
    id: string;
    label: string;
};

const parseMermaidNodeToken = (token: string): MermaidDocxNode | null => {
    const trimmedToken = token.trim();
    const labelMatch = trimmedToken.match(/^([A-Za-z0-9_]+)(?:\[[^\]]*\]|\([^)]+\)|\{[^}]+\})$/);
    if (labelMatch) {
        const id = labelMatch[1];
        const label = trimmedToken
            .slice(id.length)
            .replace(/^[\[{(]/, '')
            .replace(/[\]})]$/, '')
            .trim();
        return { id, label: label || id };
    }
    if (/^[A-Za-z0-9_]+$/.test(trimmedToken)) {
        return { id: trimmedToken, label: trimmedToken };
    }
    return null;
};

const projectMermaidFlowLine = (
    line: string,
    nodeLabels: Map<string, string>
): string => {
    const edgeMatch = line.match(/^(.+?)\s*-+>+\s*(.+)$/);
    if (!edgeMatch) return stripInlineMarkdown(line);

    const fromNode = parseMermaidNodeToken(edgeMatch[1]);
    const toNode = parseMermaidNodeToken(edgeMatch[2]);
    if (!fromNode || !toNode) return stripInlineMarkdown(line);

    if (fromNode.label !== fromNode.id) nodeLabels.set(fromNode.id, fromNode.label);
    if (toNode.label !== toNode.id) nodeLabels.set(toNode.id, toNode.label);

    const fromLabel = nodeLabels.get(fromNode.id) || fromNode.label;
    const toLabel = nodeLabels.get(toNode.id) || toNode.label;
    return `${fromLabel} -> ${toLabel}`;
};

const projectMermaidToWordParagraphs = (source: string): string[] => {
    const mermaidLines = source.split(/\r?\n/).map(line => line.trim()).filter(Boolean);
    const firstLine = mermaidLines[0] || 'diagram';
    const diagramType = firstLine.split(/\s+/)[0] || 'diagram';
    const nodeLabels = new Map<string, string>();
    return [
        paragraph(`Mermaid 图表：${diagramType}`),
        ...mermaidLines.slice(1).map(line => paragraph(projectMermaidFlowLine(line, nodeLabels))),
    ];
};

const projectStructuredVisualToWordParagraphs = (source: string): string[] => {
    const result = parseStructuredVisual(source);
    if (result.valid === false) {
        return [paragraph(`结构化可视化错误：${result.message}`)];
    }

    const { visual } = result;
    return [
        paragraph(`结构化可视化：${visual.title || visual.type}`),
        table([
            visual.columns,
            ...visual.rows.map(row => row.cells),
        ]),
    ];
};

const markdownToWordParagraphs = (content: string): string[] => {
    const lines = content.split(/\r?\n/);
    const paragraphs: string[] = [];
    let index = 0;

    while (index < lines.length) {
        const line = lines[index];
        const trimmedLine = line.trim();
        const nextLine = lines[index + 1];

        if (!trimmedLine) {
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
                paragraphs.push(...projectMermaidToWordParagraphs(codeSource));
                continue;
            }
            if (fenceLanguage === 'ai4se-visual') {
                paragraphs.push(...projectStructuredVisualToWordParagraphs(codeSource));
                continue;
            }
            codeLines.forEach(codeLine => paragraphs.push(codeParagraph(codeLine)));
            continue;
        }

        const headingMatch = line.match(/^(#{1,3})\s+(.+)$/);
        if (headingMatch) {
            paragraphs.push(paragraph(
                stripInlineMarkdown(headingMatch[2]),
                `Heading${headingMatch[1].length}`
            ));
            index += 1;
            continue;
        }

        if (isTableRow(line) && nextLine && isTableSeparator(nextLine)) {
            const rows = [splitTableRow(line)];
            index += 2;
            while (index < lines.length && isTableRow(lines[index]) && !isTableSeparator(lines[index])) {
                rows.push(splitTableRow(lines[index]));
                index += 1;
            }
            paragraphs.push(table(rows));
            continue;
        }

        if (isBulletItem(line)) {
            while (index < lines.length && isBulletItem(lines[index])) {
                paragraphs.push(paragraph(`• ${stripInlineMarkdown(lines[index].replace(/^\s*[-*]\s+/, ''))}`));
                index += 1;
            }
            continue;
        }

        if (isNumberedItem(line)) {
            while (index < lines.length && isNumberedItem(lines[index])) {
                const itemMatch = lines[index].match(/^\s*(\d+)[.)]\s+(.+)$/);
                if (itemMatch) {
                    paragraphs.push(paragraph(`${itemMatch[1]}. ${stripInlineMarkdown(itemMatch[2])}`));
                }
                index += 1;
            }
            continue;
        }

        paragraphs.push(paragraph(stripInlineMarkdown(line)));
        index += 1;
    }

    return paragraphs.length > 0 ? paragraphs : [paragraph(' ')];
};

const buildDocumentXml = (content: string): string => (
    [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">',
        '<w:body>',
        ...markdownToWordParagraphs(content),
        '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/></w:sectPr>',
        '</w:body>',
        '</w:document>',
    ].join('')
);

const buildContentTypesXml = (): string => (
    [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
        '<Default Extension="xml" ContentType="application/xml"/>',
        '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>',
        '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>',
        '</Types>',
    ].join('')
);

const buildRootRelationshipsXml = (): string => (
    [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">',
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>',
        '</Relationships>',
    ].join('')
);

const buildStylesXml = (): string => (
    [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">',
        '<w:style w:type="paragraph" w:default="1" w:styleId="Normal">',
        '<w:name w:val="Normal"/>',
        '<w:rPr><w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr>',
        '</w:style>',
        '<w:style w:type="paragraph" w:styleId="Heading1">',
        '<w:name w:val="Heading 1"/>',
        '<w:basedOn w:val="Normal"/>',
        '<w:pPr><w:spacing w:before="360" w:after="160"/></w:pPr>',
        '<w:rPr><w:b/><w:sz w:val="34"/></w:rPr>',
        '</w:style>',
        '<w:style w:type="paragraph" w:styleId="Heading2">',
        '<w:name w:val="Heading 2"/>',
        '<w:basedOn w:val="Normal"/>',
        '<w:pPr><w:spacing w:before="280" w:after="120"/></w:pPr>',
        '<w:rPr><w:b/><w:sz w:val="28"/></w:rPr>',
        '</w:style>',
        '<w:style w:type="paragraph" w:styleId="Heading3">',
        '<w:name w:val="Heading 3"/>',
        '<w:basedOn w:val="Normal"/>',
        '<w:pPr><w:spacing w:before="220" w:after="100"/></w:pPr>',
        '<w:rPr><w:b/><w:sz w:val="24"/></w:rPr>',
        '</w:style>',
        '<w:style w:type="table" w:styleId="TableGrid">',
        '<w:name w:val="TableGrid"/>',
        '<w:tblPr><w:tblBorders>',
        '<w:top w:val="single" w:sz="4" w:space="0" w:color="B8C7D9"/>',
        '<w:left w:val="single" w:sz="4" w:space="0" w:color="B8C7D9"/>',
        '<w:bottom w:val="single" w:sz="4" w:space="0" w:color="B8C7D9"/>',
        '<w:right w:val="single" w:sz="4" w:space="0" w:color="B8C7D9"/>',
        '<w:insideH w:val="single" w:sz="4" w:space="0" w:color="D6E0EA"/>',
        '<w:insideV w:val="single" w:sz="4" w:space="0" w:color="D6E0EA"/>',
        '</w:tblBorders></w:tblPr>',
        '</w:style>',
        '</w:styles>',
    ].join('')
);

const makeCrc32Table = (): Uint32Array => {
    const table = new Uint32Array(256);
    for (let index = 0; index < 256; index += 1) {
        let value = index;
        for (let bit = 0; bit < 8; bit += 1) {
            value = (value & 1) ? (0xedb88320 ^ (value >>> 1)) : (value >>> 1);
        }
        table[index] = value >>> 0;
    }
    return table;
};

const crc32Table = makeCrc32Table();

const crc32 = (bytes: Uint8Array): number => {
    let crc = 0xffffffff;
    bytes.forEach((byte) => {
        crc = crc32Table[(crc ^ byte) & 0xff] ^ (crc >>> 8);
    });
    return (crc ^ 0xffffffff) >>> 0;
};

const writeUint16 = (target: Uint8Array, offset: number, value: number) => {
    target[offset] = value & 0xff;
    target[offset + 1] = (value >>> 8) & 0xff;
};

const writeUint32 = (target: Uint8Array, offset: number, value: number) => {
    target[offset] = value & 0xff;
    target[offset + 1] = (value >>> 8) & 0xff;
    target[offset + 2] = (value >>> 16) & 0xff;
    target[offset + 3] = (value >>> 24) & 0xff;
};

const concatBytes = (parts: Uint8Array[]): Uint8Array => {
    const totalLength = parts.reduce((length, part) => length + part.length, 0);
    const combined = new Uint8Array(totalLength);
    let offset = 0;
    parts.forEach((part) => {
        combined.set(part, offset);
        offset += part.length;
    });
    return combined;
};

const localFileHeader = (entry: ZipEntry, fileNameBytes: Uint8Array): Uint8Array => {
    const header = new Uint8Array(30 + fileNameBytes.length);
    writeUint32(header, 0, 0x04034b50);
    writeUint16(header, 4, 20);
    writeUint16(header, 6, 0);
    writeUint16(header, 8, 0);
    writeUint16(header, 10, 0);
    writeUint16(header, 12, 0);
    writeUint32(header, 14, entry.crc32);
    writeUint32(header, 18, entry.bytes.length);
    writeUint32(header, 22, entry.bytes.length);
    writeUint16(header, 26, fileNameBytes.length);
    writeUint16(header, 28, 0);
    header.set(fileNameBytes, 30);
    return header;
};

const centralDirectoryHeader = (entry: ZipEntry, fileNameBytes: Uint8Array): Uint8Array => {
    const header = new Uint8Array(46 + fileNameBytes.length);
    writeUint32(header, 0, 0x02014b50);
    writeUint16(header, 4, 20);
    writeUint16(header, 6, 20);
    writeUint16(header, 8, 0);
    writeUint16(header, 10, 0);
    writeUint16(header, 12, 0);
    writeUint16(header, 14, 0);
    writeUint32(header, 16, entry.crc32);
    writeUint32(header, 20, entry.bytes.length);
    writeUint32(header, 24, entry.bytes.length);
    writeUint16(header, 28, fileNameBytes.length);
    writeUint16(header, 30, 0);
    writeUint16(header, 32, 0);
    writeUint16(header, 34, 0);
    writeUint16(header, 36, 0);
    writeUint32(header, 38, 0);
    writeUint32(header, 42, entry.localHeaderOffset);
    header.set(fileNameBytes, 46);
    return header;
};

const endOfCentralDirectory = (
    entryCount: number,
    centralDirectorySize: number,
    centralDirectoryOffset: number
): Uint8Array => {
    const header = new Uint8Array(22);
    writeUint32(header, 0, 0x06054b50);
    writeUint16(header, 4, 0);
    writeUint16(header, 6, 0);
    writeUint16(header, 8, entryCount);
    writeUint16(header, 10, entryCount);
    writeUint32(header, 12, centralDirectorySize);
    writeUint32(header, 16, centralDirectoryOffset);
    writeUint16(header, 20, 0);
    return header;
};

const buildStoredZip = (files: Array<{ fileName: string; content: string }>): Uint8Array => {
    const localParts: Uint8Array[] = [];
    const centralParts: Uint8Array[] = [];
    const entries: ZipEntry[] = [];
    let offset = 0;

    files.forEach((file) => {
        const bytes = textEncoder.encode(file.content);
        const entry: ZipEntry = {
            fileName: file.fileName,
            bytes,
            crc32: crc32(bytes),
            localHeaderOffset: offset,
        };
        const fileNameBytes = textEncoder.encode(file.fileName);
        const localHeader = localFileHeader(entry, fileNameBytes);
        localParts.push(localHeader, bytes);
        entries.push(entry);
        offset += localHeader.length + bytes.length;
    });

    entries.forEach((entry) => {
        centralParts.push(centralDirectoryHeader(entry, textEncoder.encode(entry.fileName)));
    });

    const centralDirectory = concatBytes(centralParts);
    const localContent = concatBytes(localParts);
    return concatBytes([
        localContent,
        centralDirectory,
        endOfCentralDirectory(entries.length, centralDirectory.length, localContent.length),
    ]);
};

export const buildDocxPackage = (content: string): Blob => {
    const packageBytes = buildStoredZip([
        { fileName: '[Content_Types].xml', content: buildContentTypesXml() },
        { fileName: '_rels/.rels', content: buildRootRelationshipsXml() },
        { fileName: 'word/document.xml', content: buildDocumentXml(content) },
        { fileName: 'word/styles.xml', content: buildStylesXml() },
    ]);

    return new Blob([packageBytes], { type: DOCX_MIME_TYPE });
};
