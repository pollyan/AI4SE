import { parseStructuredVisual, type NodeEdgeStructuredVisual } from './structuredVisuals';

const DOCX_MIME_TYPE = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';

type ZipEntry = {
    fileName: string;
    bytes: Uint8Array;
    crc32: number;
    localHeaderOffset: number;
};

type DocxMediaEntry = {
    fileName: string;
    target: string;
    relationshipId: string;
    content: string;
};

type DocxBuildContext = {
    media: DocxMediaEntry[];
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

const nodeEdgeVisualParagraphs = (visual: NodeEdgeStructuredVisual): string[] => {
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
    } else {
        visual.edges.forEach((edge) => {
            lines.push(`${edge.source} -> ${edge.target}${edge.label ? `：${edge.label}` : ''}`);
        });
    }
    return lines.map(line => paragraph(line));
};

type MermaidDocxNode = {
    id: string;
    label: string;
};

type MermaidDocxEdge = {
    from: string;
    to: string;
};

type MermaidDocxProjection = {
    diagramType: string;
    svg: string;
};

type MermaidTimelineEvent = {
    section: string;
    time: string;
    text: string;
};

type MermaidMindmapNode = {
    id: string;
    label: string;
    depth: number;
    parentId: string | null;
};

type MermaidPieSlice = {
    label: string;
    value: number;
    valueText: string;
};

type MermaidJourneyTask = {
    section: string;
    label: string;
    scoreText: string;
    actor: string | null;
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

const parseMermaidFlowchartProjection = (source: string): MermaidDocxProjection | null => {
    const mermaidLines = source.split(/\r?\n/).map(line => line.trim()).filter(Boolean);
    const firstLine = mermaidLines[0] || '';
    const diagramType = firstLine.split(/\s+/)[0] || 'diagram';
    if (!/^(flowchart|graph)$/i.test(diagramType)) return null;

    const nodeLabels = new Map<string, string>();
    const edges: MermaidDocxEdge[] = [];
    mermaidLines.slice(1).forEach((line) => {
        const edgeMatch = line.match(/^(.+?)\s*-+>+\s*(.+)$/);
        if (!edgeMatch) return;

        const fromNode = parseMermaidNodeToken(edgeMatch[1]);
        const toNode = parseMermaidNodeToken(edgeMatch[2]);
        if (!fromNode || !toNode) return;

        if (!nodeLabels.has(fromNode.id) || fromNode.label !== fromNode.id) {
            nodeLabels.set(fromNode.id, fromNode.label);
        }
        if (!nodeLabels.has(toNode.id) || toNode.label !== toNode.id) {
            nodeLabels.set(toNode.id, toNode.label);
        }
        edges.push({ from: fromNode.id, to: toNode.id });
    });

    const nodes = Array.from(nodeLabels.entries()).map(([id, label]) => ({ id, label }));
    if (nodes.length === 0 || edges.length === 0) return null;

    const nodeWidth = 150;
    const nodeHeight = 52;
    const horizontalGap = 70;
    const verticalGap = 54;
    const columns = Math.min(3, Math.max(1, nodes.length));
    const rows = Math.ceil(nodes.length / columns);
    const width = columns * nodeWidth + (columns - 1) * horizontalGap + 80;
    const height = rows * nodeHeight + (rows - 1) * verticalGap + 80;
    const positions = new Map<string, { x: number; y: number }>();

    nodes.forEach((node, index) => {
        const row = Math.floor(index / columns);
        const column = index % columns;
        positions.set(node.id, {
            x: 40 + column * (nodeWidth + horizontalGap),
            y: 40 + row * (nodeHeight + verticalGap),
        });
    });

    const edgeSvg = edges.map((edge) => {
        const from = positions.get(edge.from);
        const to = positions.get(edge.to);
        if (!from || !to) return '';
        const x1 = from.x + nodeWidth / 2;
        const y1 = from.y + nodeHeight;
        const x2 = to.x + nodeWidth / 2;
        const y2 = to.y;
        return `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="#2563eb" stroke-width="2" marker-end="url(#arrow)"/>`;
    }).join('');

    const nodeSvg = nodes.map((node) => {
        const position = positions.get(node.id);
        if (!position) return '';
        return [
            `<rect x="${position.x}" y="${position.y}" width="${nodeWidth}" height="${nodeHeight}" rx="8" fill="#eff6ff" stroke="#2563eb" stroke-width="1.5"/>`,
            `<text x="${position.x + nodeWidth / 2}" y="${position.y + 31}" text-anchor="middle" font-size="13" font-family="Arial, sans-serif" fill="#0f172a">${xmlEscape(node.label)}</text>`,
        ].join('');
    }).join('');

    return {
        diagramType,
        svg: [
            '<?xml version="1.0" encoding="UTF-8"?>',
            `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">`,
            '<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L8,4 L0,8 z" fill="#2563eb"/></marker></defs>',
            '<rect x="0" y="0" width="100%" height="100%" fill="#ffffff"/>',
            edgeSvg,
            nodeSvg,
            '</svg>',
        ].join(''),
    };
};

const parseMermaidTimelineProjection = (source: string): MermaidDocxProjection | null => {
    const mermaidLines = source.split(/\r?\n/).map(line => line.trim()).filter(Boolean);
    const firstLine = mermaidLines[0] || '';
    const diagramType = firstLine.split(/\s+/)[0] || 'diagram';
    if (!/^timeline$/i.test(diagramType)) return null;

    let title = 'Timeline';
    let currentSection = '';
    const events: MermaidTimelineEvent[] = [];
    mermaidLines.slice(1).forEach((line) => {
        const titleMatch = line.match(/^title\s+(.+)$/i);
        if (titleMatch) {
            title = titleMatch[1].trim();
            return;
        }

        const sectionMatch = line.match(/^section\s+(.+)$/i);
        if (sectionMatch) {
            currentSection = sectionMatch[1].trim();
            return;
        }

        const eventMatch = line.match(/^(.+?)\s+:\s+(.+)$/);
        if (!eventMatch) return;
        events.push({
            section: currentSection,
            time: eventMatch[1].trim(),
            text: eventMatch[2].trim(),
        });
    });

    if (events.length === 0) return null;

    const cardWidth = 170;
    const cardHeight = 74;
    const eventGap = 26;
    const width = Math.max(720, events.length * cardWidth + (events.length - 1) * eventGap + 80);
    const height = 250;
    const lineY = 112;
    const cardY = 136;

    const eventSvg = events.map((event, index) => {
        const x = 40 + index * (cardWidth + eventGap);
        const centerX = x + cardWidth / 2;
        return [
            `<line x1="${centerX}" y1="${lineY}" x2="${centerX}" y2="${cardY}" stroke="#64748b" stroke-width="1.5"/>`,
            `<circle cx="${centerX}" cy="${lineY}" r="5" fill="#2563eb"/>`,
            event.section ? `<text x="${centerX}" y="88" text-anchor="middle" font-size="12" font-family="Arial, sans-serif" font-weight="700" fill="#1e40af">${xmlEscape(event.section)}</text>` : '',
            `<rect x="${x}" y="${cardY}" width="${cardWidth}" height="${cardHeight}" rx="8" fill="#eff6ff" stroke="#2563eb" stroke-width="1.4"/>`,
            `<text x="${x + 14}" y="${cardY + 24}" font-size="13" font-family="Arial, sans-serif" font-weight="700" fill="#0f172a">${xmlEscape(event.time)}</text>`,
            `<text x="${x + 14}" y="${cardY + 50}" font-size="12" font-family="Arial, sans-serif" fill="#334155">${xmlEscape(event.text)}</text>`,
        ].join('');
    }).join('');

    return {
        diagramType,
        svg: [
            '<?xml version="1.0" encoding="UTF-8"?>',
            `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">`,
            '<rect x="0" y="0" width="100%" height="100%" fill="#ffffff"/>',
            `<text x="40" y="42" font-size="20" font-family="Arial, sans-serif" font-weight="700" fill="#0f172a">${xmlEscape(title)}</text>`,
            `<line x1="40" y1="${lineY}" x2="${width - 40}" y2="${lineY}" stroke="#93c5fd" stroke-width="3"/>`,
            eventSvg,
            '</svg>',
        ].join(''),
    };
};

const unwrapMindmapLabel = (content: string): string => {
    let label = content.trim().replace(/^root\s*/i, '').trim();
    const wrappers: Array<[string, string]> = [
        ['((', '))'],
        ['[', ']'],
        ['(', ')'],
        ['{', '}'],
    ];

    let changed = true;
    while (changed) {
        changed = false;
        wrappers.forEach(([start, end]) => {
            if (label.startsWith(start) && label.endsWith(end) && label.length > start.length + end.length) {
                label = label.slice(start.length, -end.length).trim();
                changed = true;
            }
        });
    }

    return label;
};

const parseMermaidMindmapProjection = (source: string): MermaidDocxProjection | null => {
    const lines = source.split(/\r?\n/);
    const firstLine = (lines.find(line => line.trim()) || '').trim();
    const diagramType = firstLine.split(/\s+/)[0] || 'diagram';
    if (!/^mindmap$/i.test(diagramType)) return null;

    const nodes: MermaidMindmapNode[] = [];
    const stack: Array<{ indent: number; id: string; depth: number }> = [];
    lines.slice(lines.indexOf(lines.find(line => line.trim()) || '') + 1).forEach((line) => {
        if (!line.trim()) return;
        const indent = (line.match(/^\s*/) || [''])[0].replace(/\t/g, '  ').length;
        const label = unwrapMindmapLabel(line.trim());
        if (!label) return;

        while (stack.length > 0 && stack[stack.length - 1].indent >= indent) {
            stack.pop();
        }
        const parent = stack[stack.length - 1] || null;
        const node: MermaidMindmapNode = {
            id: `node-${nodes.length + 1}`,
            label,
            depth: parent ? parent.depth + 1 : 0,
            parentId: parent ? parent.id : null,
        };
        nodes.push(node);
        stack.push({ indent, id: node.id, depth: node.depth });
    });

    if (nodes.length === 0) return null;

    const nodeWidth = 176;
    const nodeHeight = 46;
    const horizontalGap = 70;
    const verticalGap = 24;
    const maxDepth = Math.max(...nodes.map(node => node.depth));
    const width = Math.max(640, (maxDepth + 1) * nodeWidth + maxDepth * horizontalGap + 80);
    const height = Math.max(180, nodes.length * (nodeHeight + verticalGap) + 40);
    const positions = new Map<string, { x: number; y: number }>();

    nodes.forEach((node, index) => {
        positions.set(node.id, {
            x: 40 + node.depth * (nodeWidth + horizontalGap),
            y: 30 + index * (nodeHeight + verticalGap),
        });
    });

    const linkSvg = nodes.map((node) => {
        if (!node.parentId) return '';
        const from = positions.get(node.parentId);
        const to = positions.get(node.id);
        if (!from || !to) return '';
        const x1 = from.x + nodeWidth;
        const y1 = from.y + nodeHeight / 2;
        const x2 = to.x;
        const y2 = to.y + nodeHeight / 2;
        return `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="#64748b" stroke-width="1.5"/>`;
    }).join('');

    const nodeSvg = nodes.map((node) => {
        const position = positions.get(node.id);
        if (!position) return '';
        const isRoot = node.parentId === null;
        return [
            `<rect x="${position.x}" y="${position.y}" width="${nodeWidth}" height="${nodeHeight}" rx="10" fill="${isRoot ? '#dbeafe' : '#f8fafc'}" stroke="${isRoot ? '#2563eb' : '#94a3b8'}" stroke-width="${isRoot ? '1.8' : '1.3'}"/>`,
            `<text x="${position.x + nodeWidth / 2}" y="${position.y + 29}" text-anchor="middle" font-size="${isRoot ? '14' : '13'}" font-family="Arial, sans-serif" font-weight="${isRoot ? '700' : '500'}" fill="#0f172a">${xmlEscape(node.label)}</text>`,
        ].join('');
    }).join('');

    return {
        diagramType,
        svg: [
            '<?xml version="1.0" encoding="UTF-8"?>',
            `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">`,
            '<rect x="0" y="0" width="100%" height="100%" fill="#ffffff"/>',
            linkSvg,
            nodeSvg,
            '</svg>',
        ].join(''),
    };
};

const cleanMermaidPieLabel = (source: string): string => {
    const label = source.trim().replace(/^["'“”]+|["'“”]+$/g, '').trim();
    return stripInlineMarkdown(label);
};

const parseMermaidPieProjection = (source: string): MermaidDocxProjection | null => {
    const mermaidLines = source.split(/\r?\n/).map(line => line.trim()).filter(Boolean);
    const firstLine = mermaidLines[0] || '';
    const diagramType = firstLine.split(/\s+/)[0] || 'diagram';
    if (!/^pie$/i.test(diagramType)) return null;

    const inlineTitleMatch = firstLine.match(/^pie\s+title\s+(.+)$/i);
    let title = inlineTitleMatch ? stripInlineMarkdown(inlineTitleMatch[1].trim()) : 'Pie Chart';
    const slices: MermaidPieSlice[] = [];

    mermaidLines.slice(1).forEach((line) => {
        const titleMatch = line.match(/^title\s+(.+)$/i);
        if (titleMatch) {
            title = stripInlineMarkdown(titleMatch[1].trim());
            return;
        }

        const sliceMatch = line.match(/^(.+?)\s*:\s*([+-]?\d+(?:\.\d+)?)\s*$/);
        if (!sliceMatch) return;
        const label = cleanMermaidPieLabel(sliceMatch[1]);
        const value = Number(sliceMatch[2]);
        if (!label || !Number.isFinite(value) || value <= 0) return;
        slices.push({
            label,
            value,
            valueText: sliceMatch[2],
        });
    });

    const boundedSlices = slices.slice(0, 8);
    if (boundedSlices.length === 0) return null;

    const width = 720;
    const height = 260;
    const centerX = 150;
    const centerY = 145;
    const radius = 64;
    const legendLeft = 260;
    const legendTop = 80;
    const legendGap = 22;
    const total = boundedSlices.reduce((sum, slice) => sum + slice.value, 0);
    let currentAngle = -Math.PI / 2;

    const separatorSvg = boundedSlices.slice(0, -1).map((slice) => {
        currentAngle += (slice.value / total) * Math.PI * 2;
        const x = Number((centerX + Math.cos(currentAngle) * radius).toFixed(2));
        const y = Number((centerY + Math.sin(currentAngle) * radius).toFixed(2));
        return `<line x1="${centerX}" y1="${centerY}" x2="${x}" y2="${y}" stroke="#2563eb" stroke-width="1.4"/>`;
    }).join('');

    const legendSvg = boundedSlices.map((slice, index) => {
        const y = legendTop + index * legendGap;
        return [
            `<rect x="${legendLeft}" y="${y - 10}" width="10" height="10" fill="#eff6ff" stroke="#2563eb" stroke-width="1.2"/>`,
            `<text x="${legendLeft + 18}" y="${y}" font-size="12" font-family="Arial, sans-serif" fill="#0f172a">${xmlEscape(slice.label)}：${xmlEscape(slice.valueText)}</text>`,
        ].join('');
    }).join('');

    return {
        diagramType,
        svg: [
            '<?xml version="1.0" encoding="UTF-8"?>',
            `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">`,
            '<rect x="0" y="0" width="100%" height="100%" fill="#ffffff"/>',
            `<text x="40" y="42" font-size="20" font-family="Arial, sans-serif" font-weight="700" fill="#0f172a">${xmlEscape(title)}</text>`,
            `<circle cx="${centerX}" cy="${centerY}" r="${radius}" fill="#eff6ff" stroke="#2563eb" stroke-width="2"/>`,
            separatorSvg,
            legendSvg,
            '</svg>',
        ].join(''),
    };
};

const parseMermaidJourneyProjection = (source: string): MermaidDocxProjection | null => {
    const mermaidLines = source.split(/\r?\n/).map(line => line.trim()).filter(Boolean);
    const firstLine = mermaidLines[0] || '';
    const diagramType = firstLine.split(/\s+/)[0] || 'diagram';
    if (!/^journey$/i.test(diagramType)) return null;

    let title = 'Journey';
    let currentSection = '旅程';
    const sections: string[] = [];
    const tasks: MermaidJourneyTask[] = [];

    mermaidLines.slice(1).forEach((line) => {
        const titleMatch = line.match(/^title\s+(.+)$/i);
        if (titleMatch) {
            title = stripInlineMarkdown(titleMatch[1].trim());
            return;
        }

        const sectionMatch = line.match(/^section\s+(.+)$/i);
        if (sectionMatch) {
            currentSection = stripInlineMarkdown(sectionMatch[1].trim());
            if (currentSection && !sections.includes(currentSection)) {
                sections.push(currentSection);
            }
            return;
        }

        const taskMatch = line.match(/^(.+?)\s*:\s*([+-]?\d+(?:\.\d+)?)\s*(?::\s*(.+))?$/);
        if (!taskMatch) return;
        if (currentSection && !sections.includes(currentSection)) {
            sections.push(currentSection);
        }
        tasks.push({
            section: currentSection,
            label: stripInlineMarkdown(taskMatch[1].trim()),
            scoreText: stripInlineMarkdown(taskMatch[2].trim()),
            actor: taskMatch[3] ? stripInlineMarkdown(taskMatch[3].trim()) : null,
        });
    });

    const boundedTasks = tasks.slice(0, 8);
    if (boundedTasks.length === 0) return null;

    const cardWidth = 128;
    const cardHeight = 56;
    const cardGap = 26;
    const width = Math.max(760, boundedTasks.length * cardWidth + (boundedTasks.length - 1) * cardGap + 80);
    const height = 300;
    const baselineY = 138;
    const cardTop = 166;

    const taskSvg = boundedTasks.map((task, index) => {
        const x = 40 + index * (cardWidth + cardGap);
        const centerX = x + cardWidth / 2;
        return [
            `<line x1="${centerX}" y1="${baselineY}" x2="${centerX}" y2="${cardTop}" stroke="#64748b" stroke-width="1.4"/>`,
            `<circle cx="${centerX}" cy="${baselineY}" r="4.5" fill="#2563eb"/>`,
            `<text x="${centerX}" y="104" text-anchor="middle" font-size="12" font-family="Arial, sans-serif" font-weight="700" fill="#1e40af">${xmlEscape(task.section)}</text>`,
            `<rect x="${x}" y="${cardTop}" width="${cardWidth}" height="${cardHeight}" rx="8" fill="#f8fafc" stroke="#2563eb" stroke-width="1.3"/>`,
            `<text x="${x + 10}" y="${cardTop + 21}" font-size="12" font-family="Arial, sans-serif" font-weight="700" fill="#0f172a">${xmlEscape(task.label)}</text>`,
            `<text x="${x + 10}" y="${cardTop + 42}" font-size="11" font-family="Arial, sans-serif" fill="#334155">评分 ${xmlEscape(task.scoreText)}${task.actor ? ` · ${xmlEscape(task.actor)}` : ''}</text>`,
        ].join('');
    }).join('');

    return {
        diagramType,
        svg: [
            '<?xml version="1.0" encoding="UTF-8"?>',
            `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">`,
            '<rect x="0" y="0" width="100%" height="100%" fill="#ffffff"/>',
            `<text x="40" y="42" font-size="20" font-family="Arial, sans-serif" font-weight="700" fill="#0f172a">${xmlEscape(title)}</text>`,
            `<line x1="40" y1="${baselineY}" x2="${width - 40}" y2="${baselineY}" stroke="#93c5fd" stroke-width="3"/>`,
            taskSvg,
            '</svg>',
        ].join(''),
    };
};

const parseMermaidDocxProjection = (source: string): MermaidDocxProjection | null => (
    parseMermaidFlowchartProjection(source)
    || parseMermaidTimelineProjection(source)
    || parseMermaidMindmapProjection(source)
    || parseMermaidPieProjection(source)
    || parseMermaidJourneyProjection(source)
);

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

const projectMermaidTimelineLine = (line: string): string | null => {
    const titleMatch = line.match(/^title\s+(.+)$/i);
    if (titleMatch) return titleMatch[1].trim();
    const sectionMatch = line.match(/^section\s+(.+)$/i);
    if (sectionMatch) return sectionMatch[1].trim();
    const eventMatch = line.match(/^(.+?)\s+:\s+(.+)$/);
    if (eventMatch) return `${eventMatch[1].trim()}：${eventMatch[2].trim()}`;
    return stripInlineMarkdown(line);
};

const projectMermaidMindmapLine = (line: string): string | null => {
    const label = unwrapMindmapLabel(line.trim());
    return label ? stripInlineMarkdown(label) : null;
};

const projectMermaidPieLine = (line: string): string | null => {
    const inlineTitleMatch = line.match(/^pie\s+title\s+(.+)$/i);
    if (inlineTitleMatch) return stripInlineMarkdown(inlineTitleMatch[1].trim());
    const titleMatch = line.match(/^title\s+(.+)$/i);
    if (titleMatch) return stripInlineMarkdown(titleMatch[1].trim());
    const sliceMatch = line.match(/^(.+?)\s*:\s*([+-]?\d+(?:\.\d+)?)\s*$/);
    if (sliceMatch) {
        const label = cleanMermaidPieLabel(sliceMatch[1]);
        return label ? `${label}：${sliceMatch[2].trim()}` : null;
    }
    return stripInlineMarkdown(line);
};

const projectMermaidJourneyLine = (line: string): string | null => {
    const titleMatch = line.match(/^title\s+(.+)$/i);
    if (titleMatch) return stripInlineMarkdown(titleMatch[1].trim());
    const sectionMatch = line.match(/^section\s+(.+)$/i);
    if (sectionMatch) return stripInlineMarkdown(sectionMatch[1].trim());
    const taskMatch = line.match(/^(.+?)\s*:\s*([+-]?\d+(?:\.\d+)?)\s*(?::\s*(.+))?$/);
    if (taskMatch) {
        const label = stripInlineMarkdown(taskMatch[1].trim());
        const score = stripInlineMarkdown(taskMatch[2].trim());
        const actor = taskMatch[3] ? stripInlineMarkdown(taskMatch[3].trim()) : null;
        return `${label}：${score}${actor ? `（${actor}）` : ''}`;
    }
    return stripInlineMarkdown(line);
};

const projectMermaidSemanticLine = (
    diagramType: string,
    line: string,
    nodeLabels: Map<string, string>
): string | null => {
    if (/^(flowchart|graph)$/i.test(diagramType)) return projectMermaidFlowLine(line, nodeLabels);
    if (/^timeline$/i.test(diagramType)) return projectMermaidTimelineLine(line);
    if (/^mindmap$/i.test(diagramType)) return projectMermaidMindmapLine(line);
    if (/^pie$/i.test(diagramType)) return projectMermaidPieLine(line);
    if (/^journey$/i.test(diagramType)) return projectMermaidJourneyLine(line);
    return stripInlineMarkdown(line);
};

const mediaDrawing = (media: DocxMediaEntry, description: string): string => (
    '<w:p><w:r><w:drawing>'
    + '<wp:inline distT="0" distB="0" distL="0" distR="0">'
    + '<wp:extent cx="5486400" cy="2743200"/>'
    + `<wp:docPr id="${media.relationshipId.replace(/^rId/, '') || '1'}" name="${xmlEscape(media.fileName)}" descr="${xmlEscape(description)}"/>`
    + '<wp:cNvGraphicFramePr><a:graphicFrameLocks noChangeAspect="1"/></wp:cNvGraphicFramePr>'
    + '<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
    + '<pic:pic><pic:nvPicPr>'
    + `<pic:cNvPr id="0" name="${xmlEscape(media.fileName)}"/>`
    + '<pic:cNvPicPr/>'
    + '</pic:nvPicPr><pic:blipFill>'
    + `<a:blip r:embed="${media.relationshipId}"/>`
    + '<a:stretch><a:fillRect/></a:stretch>'
    + '</pic:blipFill><pic:spPr>'
    + '<a:xfrm><a:off x="0" y="0"/><a:ext cx="5486400" cy="2743200"/></a:xfrm>'
    + '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
    + '</pic:spPr></pic:pic>'
    + '</a:graphicData></a:graphic>'
    + '</wp:inline>'
    + '</w:drawing></w:r></w:p>'
);

const registerMedia = (context: DocxBuildContext, content: string): DocxMediaEntry => {
    const index = context.media.length + 1;
    const media: DocxMediaEntry = {
        fileName: `word/media/mermaid-${index}.svg`,
        target: `media/mermaid-${index}.svg`,
        relationshipId: `rId${index}`,
        content,
    };
    context.media.push(media);
    return media;
};

const projectMermaidToWordParagraphs = (source: string, context: DocxBuildContext): string[] => {
    const mermaidLines = source.split(/\r?\n/).map(line => line.trim()).filter(Boolean);
    const firstLine = mermaidLines[0] || 'diagram';
    const diagramType = firstLine.split(/\s+/)[0] || 'diagram';
    const nodeLabels = new Map<string, string>();
    const semanticSourceLines = /^pie$/i.test(diagramType) && /^pie\s+title\s+.+/i.test(firstLine)
        ? mermaidLines
        : mermaidLines.slice(1);
    const semanticLines = semanticSourceLines
        .map(line => projectMermaidSemanticLine(diagramType, line, nodeLabels))
        .filter((line): line is string => Boolean(line));
    const paragraphs = [
        paragraph(`Mermaid 图表：${diagramType}`),
        ...semanticLines.map(line => paragraph(line)),
    ];
    const projection = parseMermaidDocxProjection(source);
    if (!projection) return paragraphs;

    const media = registerMedia(context, projection.svg);
    return [
        paragraphs[0],
        mediaDrawing(media, `Mermaid 图表：${projection.diagramType}`),
        ...paragraphs.slice(1),
    ];
};

const projectStructuredVisualToWordParagraphs = (source: string): string[] => {
    const result = parseStructuredVisual(source);
    if (result.valid === false) {
        return [paragraph(`结构化可视化错误：${result.message}`)];
    }

    const { visual } = result;
    if (visual.kind === 'node-edge') {
        return nodeEdgeVisualParagraphs(visual);
    }

    return [
        paragraph(`结构化可视化：${visual.title || visual.type}`),
        table([
            visual.columns,
            ...visual.rows.map(row => row.cells),
        ]),
    ];
};

const markdownToWordParagraphs = (content: string, context: DocxBuildContext): string[] => {
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
                paragraphs.push(...projectMermaidToWordParagraphs(codeSource, context));
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

const buildDocumentXml = (content: string, context: DocxBuildContext): string => (
    [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">',
        '<w:body>',
        ...markdownToWordParagraphs(content, context),
        '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/></w:sectPr>',
        '</w:body>',
        '</w:document>',
    ].join('')
);

const buildContentTypesXml = (context: DocxBuildContext): string => (
    [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
        '<Default Extension="xml" ContentType="application/xml"/>',
        ...(context.media.length > 0 ? ['<Default Extension="svg" ContentType="image/svg+xml"/>'] : []),
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

const buildDocumentRelationshipsXml = (context: DocxBuildContext): string => (
    [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">',
        ...context.media.map(media => (
            `<Relationship Id="${media.relationshipId}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="${media.target}"/>`
        )),
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
    const context: DocxBuildContext = { media: [] };
    const documentXml = buildDocumentXml(content, context);
    const packageBytes = buildStoredZip([
        { fileName: '[Content_Types].xml', content: buildContentTypesXml(context) },
        { fileName: '_rels/.rels', content: buildRootRelationshipsXml() },
        ...(context.media.length > 0 ? [{ fileName: 'word/_rels/document.xml.rels', content: buildDocumentRelationshipsXml(context) }] : []),
        { fileName: 'word/document.xml', content: documentXml },
        { fileName: 'word/styles.xml', content: buildStylesXml() },
        ...context.media.map(media => ({ fileName: media.fileName, content: media.content })),
    ]);

    return new Blob([packageBytes], { type: DOCX_MIME_TYPE });
};
