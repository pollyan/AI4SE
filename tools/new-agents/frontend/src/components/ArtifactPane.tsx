import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import type { Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import { useStore, ArtifactVersion, WORKFLOWS } from '../store';
import type { AgentRunSnapshotArtifact, ArtifactVisualDiagnostic, ArtifactVisualDiagnosticFocusRequest } from '../core/types';
import { buildLineDiff } from '../core/artifactDiff';
import { preprocessMarkdown, replaceMermaidBlockAtIndex } from '../core/utils/markdownUtils';
import { Download, Code, Eye, History, X, AlertTriangle, GitCompare, Edit3, Save, MessageSquare, Trash2, Lock, Unlock } from 'lucide-react';
import { createMarkdownCodeRenderer } from './markdownCodeRenderer';
import { StructuredVisual } from './StructuredVisual';
import { ArtifactConflictError, updateRunArtifact, updateRunArtifactCollaboration } from '../services/runSnapshotService';
import { buildDocxPackage } from '../core/docxExport';
import { parseStructuredVisual } from '../core/structuredVisuals';

export const ArtifactPane: React.FC = () => {
  const workflow = useStore((state) => state.workflow);
  const stageIndex = useStore((state) => state.stageIndex);
  const artifactContent = useStore((state) => state.artifactContent);
  const artifactHistory = useStore((state) => state.artifactHistory);
  const artifactTruncated = useStore((state) => state.artifactTruncated);
  const isGenerating = useStore((state) => state.isGenerating);
  const currentRunId = useStore((state) => state.currentRunId);
  const setArtifactContent = useStore((state) => state.setArtifactContent);
  const addArtifactVersion = useStore((state) => state.addArtifactVersion);
  const artifactComments = useStore((state) => state.artifactComments);
  const addArtifactComment = useStore((state) => state.addArtifactComment);
  const addArtifactCommentReply = useStore((state) => state.addArtifactCommentReply);
  const setArtifactCommentStatus = useStore((state) => state.setArtifactCommentStatus);
  const removeArtifactComment = useStore((state) => state.removeArtifactComment);
  const artifactSectionLocks = useStore((state) => state.artifactSectionLocks);
  const artifactAuditEvents = useStore((state) => state.artifactAuditEvents);
  const addArtifactSectionLock = useStore((state) => state.addArtifactSectionLock);
  const removeArtifactSectionLock = useStore((state) => state.removeArtifactSectionLock);
  const addArtifactAuditEvent = useStore((state) => state.addArtifactAuditEvent);
  const setArtifactVisualDiagnostic = useStore((state) => state.setArtifactVisualDiagnostic);
  const clearArtifactVisualDiagnostic = useStore((state) => state.clearArtifactVisualDiagnostic);
  const artifactVisualDiagnostics = useStore((state) => state.artifactVisualDiagnostics);
  const artifactVisualDiagnosticFocusRequest = useStore((state) => state.artifactVisualDiagnosticFocusRequest);
  const [viewMode, setViewMode] = useState<'preview' | 'code'>('preview');
  const [showHistory, setShowHistory] = useState(false);
  const [showExportMenu, setShowExportMenu] = useState(false);
  const [showComments, setShowComments] = useState(false);
  const [showSectionLocks, setShowSectionLocks] = useState(false);
  const [commentDraft, setCommentDraft] = useState('');
  const [commentReplyDrafts, setCommentReplyDrafts] = useState<Record<string, string>>({});
  const [selectedVersion, setSelectedVersion] = useState<ArtifactVersion | null>(null);
  const [historyViewMode, setHistoryViewMode] = useState<'preview' | 'diff'>('preview');
  const [isEditing, setIsEditing] = useState(false);
  const [editDraft, setEditDraft] = useState('');
  const [isSavingManualEdit, setIsSavingManualEdit] = useState(false);
  const [manualEditError, setManualEditError] = useState<string | null>(null);
  const [collaborationSyncError, setCollaborationSyncError] = useState<string | null>(null);
  const [conflictVersionNumber, setConflictVersionNumber] = useState<number | null>(null);
  const [conflictArtifact, setConflictArtifact] = useState<AgentRunSnapshotArtifact | null>(null);
  const [showConflictDiff, setShowConflictDiff] = useState(false);
  const [selectedArtifactText, setSelectedArtifactText] = useState<string | null>(null);
  const [activeCommentAnchorText, setActiveCommentAnchorText] = useState<string | null>(null);
  const [activeVisualDiagnosticId, setActiveVisualDiagnosticId] = useState<string | null>(null);
  const artifactPreviewRef = useRef<HTMLDivElement | null>(null);
  const handledVisualDiagnosticFocusSeqRef = useRef<number | null>(null);
  const currentStageId = WORKFLOWS[workflow].stages[stageIndex]?.id;
  const currentStageArtifactHistory = useMemo(
    () => currentStageId
      ? artifactHistory.filter(version => version.stageId === currentStageId)
      : [],
    [artifactHistory, currentStageId]
  );
  const currentStageComments = useMemo(
    () => currentStageId
      ? artifactComments.filter(comment => comment.stageId === currentStageId)
      : [],
    [artifactComments, currentStageId]
  );
  const currentStageSectionLocks = useMemo(
    () => currentStageId
      ? artifactSectionLocks.filter(lock => lock.stageId === currentStageId)
      : [],
    [artifactSectionLocks, currentStageId]
  );
  const currentStageAuditEvents = useMemo(
    () => currentStageId
      ? artifactAuditEvents.filter(event => event.stageId === currentStageId)
      : [],
    [artifactAuditEvents, currentStageId]
  );

  const syncArtifactCollaborationState = useCallback(() => {
    if (!currentRunId) return;
    const state = useStore.getState();
    setCollaborationSyncError(null);
    void updateRunArtifactCollaboration(
      currentRunId,
      state.artifactComments,
      state.artifactSectionLocks,
    ).catch((error: unknown) => {
      const message = error instanceof Error ? error.message : '未知错误';
      setCollaborationSyncError(`协作状态保存失败：${message}`);
    });
  }, [currentRunId]);

  const isFenceStart = (line: string): boolean => /^```/.test(line.trim());
  const isHeading = (line: string): boolean => /^#{1,3}\s+/.test(line);
  const isBulletItem = (line: string): boolean => /^\s*[-*]\s+/.test(line);
  const isNumberedItem = (line: string): boolean => /^\s*\d+[.)]\s+/.test(line);
  const isTableRow = (line: string): boolean => line.trim().includes('|');
  const splitTableRow = (line: string): string[] => {
    const trimmedLine = line.trim().replace(/^\|/, '').replace(/\|$/, '');
    return trimmedLine.split('|').map(cell => cell.trim());
  };
  const isTableSeparator = (line: string): boolean => {
    const cells = splitTableRow(line);
    return cells.length > 1 && cells.every(cell => /^:?-{3,}:?$/.test(cell));
  };
  type ArtifactSection = {
    heading: string;
    title: string;
    content: string;
  };

  const extractMarkdownSections = (content: string): ArtifactSection[] => {
    const lines = content.split(/\r?\n/);
    const sections: ArtifactSection[] = [];
    let currentStart = -1;
    let currentHeading = '';

    lines.forEach((line, index) => {
      if (!/^#{1,3}\s+/.test(line)) return;
      if (currentStart >= 0) {
        sections.push({
          heading: currentHeading,
          title: currentHeading.replace(/^#{1,3}\s+/, ''),
          content: lines.slice(currentStart, index).join('\n').trim(),
        });
      }
      currentStart = index;
      currentHeading = line;
    });

    if (currentStart >= 0) {
      sections.push({
        heading: currentHeading,
        title: currentHeading.replace(/^#{1,3}\s+/, ''),
        content: lines.slice(currentStart).join('\n').trim(),
      });
    }

    return sections;
  };

  const toUtf16BeHex = (content: string): string => {
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
  };

  const stripInlineMarkdown = (content: string): string => (
    content
      .replace(/`([^`]+)`/g, '$1')
      .replace(/\*\*([^*]+)\*\*/g, '$1')
      .replace(/\*([^*]+)\*/g, '$1')
      .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
      .trim()
  );

  const formatPdfTableRows = (rows: string[][]): string[] => {
    const columnWidths = rows.reduce<number[]>((widths, row) => {
      row.forEach((cell, cellIndex) => {
        widths[cellIndex] = Math.max(widths[cellIndex] ?? 0, cell.length);
      });
      return widths;
    }, []);

    return rows.map(row => row.map((cell, cellIndex) => (
      cell.padEnd(columnWidths[cellIndex] ?? cell.length, ' ')
    )).join('    ').trimEnd());
  };

  const getFenceLanguage = (line: string): string => (
    line.trim().replace(/^```/, '').trim().toLowerCase()
  );

  type PdfMermaidFlowchartNode = {
    id: string;
    label: string;
  };

  type PdfMermaidFlowchartEdge = {
    from: string;
    to: string;
  };

  type PdfMermaidFlowchartDiagram = {
    kind: 'flowchart';
    startLineIndex: number;
    diagramType: string;
    nodes: PdfMermaidFlowchartNode[];
    edges: PdfMermaidFlowchartEdge[];
  };

  type PdfMermaidTimelineEvent = {
    section: string;
    time: string;
    description: string;
  };

  type PdfMermaidTimelineDiagram = {
    kind: 'timeline';
    startLineIndex: number;
    diagramType: 'timeline';
    title: string | null;
    sections: string[];
    events: PdfMermaidTimelineEvent[];
  };

  type PdfMermaidMindmapNode = {
    id: string;
    label: string;
    depth: number;
    parentId: string | null;
  };

  type PdfMermaidMindmapDiagram = {
    kind: 'mindmap';
    startLineIndex: number;
    diagramType: 'mindmap';
    nodes: PdfMermaidMindmapNode[];
  };

  type PdfMermaidDiagram =
    | PdfMermaidFlowchartDiagram
    | PdfMermaidTimelineDiagram
    | PdfMermaidMindmapDiagram;

  const parseMermaidEndpoint = (source: string): PdfMermaidFlowchartNode | null => {
    const trimmedSource = source.trim();
    const idMatch = trimmedSource.match(/^([A-Za-z0-9_]+)/);
    if (!idMatch) return null;

    const labelMatch = trimmedSource.match(/\[([^\]]+)\]|\(([^)]+)\)|\{([^}]+)\}/);
    return {
      id: idMatch[1],
      label: stripInlineMarkdown(labelMatch?.[1] || labelMatch?.[2] || labelMatch?.[3] || idMatch[1]),
    };
  };

  const parseMermaidFlowchartForPdf = (
    source: string,
    startLineIndex: number
  ): PdfMermaidFlowchartDiagram | null => {
    const mermaidLines = source.split(/\r?\n/).map(line => line.trim()).filter(Boolean);
    const firstLine = mermaidLines[0] || '';
    const diagramType = firstLine.split(/\s+/)[0] || 'diagram';
    if (!['flowchart', 'graph'].includes(diagramType)) return null;

    const nodes = new Map<string, PdfMermaidFlowchartNode>();
    const edges: PdfMermaidFlowchartEdge[] = [];
    const edgePattern = /\s*(?:-->|---|==>|-.->)\s*/;

    mermaidLines.slice(1).forEach((line) => {
      const endpoints = line.split(edgePattern);
      if (endpoints.length < 2) return;

      const parsedNodes = endpoints
        .map(parseMermaidEndpoint)
        .filter((node): node is PdfMermaidFlowchartNode => node !== null);
      parsedNodes.forEach((node) => {
        const existingNode = nodes.get(node.id);
        if (!existingNode || existingNode.label === existingNode.id) {
          nodes.set(node.id, node);
        }
      });

      for (let index = 0; index < parsedNodes.length - 1; index += 1) {
        edges.push({
          from: parsedNodes[index].id,
          to: parsedNodes[index + 1].id,
        });
      }
    });

    if (nodes.size === 0 || edges.length === 0) return null;

    return {
      kind: 'flowchart',
      startLineIndex,
      diagramType,
      nodes: Array.from(nodes.values()).slice(0, 6),
      edges: edges.filter(edge => nodes.has(edge.from) && nodes.has(edge.to)).slice(0, 8),
    };
  };

  const parseMermaidTimelineForPdf = (
    source: string,
    startLineIndex: number
  ): PdfMermaidTimelineDiagram | null => {
    const mermaidLines = source.split(/\r?\n/).map(line => line.trim()).filter(Boolean);
    const firstLine = mermaidLines[0] || '';
    if (firstLine.split(/\s+/)[0] !== 'timeline') return null;

    let title: string | null = null;
    let currentSection = '事件';
    const sections: string[] = [];
    const events: PdfMermaidTimelineEvent[] = [];

    mermaidLines.slice(1).forEach((line) => {
      if (line.startsWith('title ')) {
        title = stripInlineMarkdown(line.replace(/^title\s+/, ''));
        return;
      }

      if (line.startsWith('section ')) {
        currentSection = stripInlineMarkdown(line.replace(/^section\s+/, ''));
        if (currentSection && !sections.includes(currentSection)) {
          sections.push(currentSection);
        }
        return;
      }

      const eventMatch = line.match(/^(.+?)\s*:\s*(.+)$/);
      if (!eventMatch) return;
      if (currentSection && !sections.includes(currentSection)) {
        sections.push(currentSection);
      }
      events.push({
        section: currentSection,
        time: stripInlineMarkdown(eventMatch[1]),
        description: stripInlineMarkdown(eventMatch[2]),
      });
    });

    if (events.length === 0) return null;

    return {
      kind: 'timeline',
      startLineIndex,
      diagramType: 'timeline',
      title,
      sections: sections.slice(0, 5),
      events: events.slice(0, 8),
    };
  };

  const cleanMermaidMindmapLabel = (source: string): string => {
    let label = source.trim().replace(/^root\s*/i, '').trim();
    for (let index = 0; index < 4; index += 1) {
      const nextLabel = label.trim();
      if (
        (nextLabel.startsWith('((') && nextLabel.endsWith('))'))
        || (nextLabel.startsWith('[[') && nextLabel.endsWith(']]'))
      ) {
        label = nextLabel.slice(2, -2);
        continue;
      }
      if (
        (nextLabel.startsWith('[') && nextLabel.endsWith(']'))
        || (nextLabel.startsWith('(') && nextLabel.endsWith(')'))
        || (nextLabel.startsWith('{') && nextLabel.endsWith('}'))
      ) {
        label = nextLabel.slice(1, -1);
        continue;
      }
      label = nextLabel;
      break;
    }
    label = label.trim().replace(/^["'“”]+|["'“”]+$/g, '').trim();
    return stripInlineMarkdown(label);
  };

  const parseMermaidMindmapForPdf = (
    source: string,
    startLineIndex: number
  ): PdfMermaidMindmapDiagram | null => {
    const lines = source.split(/\r?\n/);
    const firstLineIndex = lines.findIndex(line => line.trim());
    if (firstLineIndex < 0 || lines[firstLineIndex].trim() !== 'mindmap') return null;

    const nodes: PdfMermaidMindmapNode[] = [];
    const stack: Array<{ indent: number; node: PdfMermaidMindmapNode }> = [];

    for (const rawLine of lines.slice(firstLineIndex + 1)) {
      if (!rawLine.trim()) continue;
      if (rawLine.includes('\t')) return null;

      const trimmedLine = rawLine.trim();
      if (/^(class|style|:::)/.test(trimmedLine)) return null;
      const indent = rawLine.match(/^ */)?.[0].length ?? 0;
      const label = cleanMermaidMindmapLabel(trimmedLine);
      if (!label) return null;

      while (stack.length > 0 && indent <= stack[stack.length - 1].indent) {
        stack.pop();
      }

      const parentNode = stack[stack.length - 1]?.node ?? null;
      const node: PdfMermaidMindmapNode = {
        id: `mindmap-${nodes.length}`,
        label,
        depth: parentNode ? Math.min(parentNode.depth + 1, 3) : 0,
        parentId: parentNode?.id ?? null,
      };
      nodes.push(node);
      stack.push({ indent, node });

      if (nodes.length >= 12) break;
    }

    if (nodes.length < 2) return null;

    return {
      kind: 'mindmap',
      startLineIndex,
      diagramType: 'mindmap',
      nodes,
    };
  };

  const parseMermaidDiagramForPdf = (
    source: string,
    startLineIndex: number
  ): PdfMermaidDiagram | null => (
    parseMermaidFlowchartForPdf(source, startLineIndex)
    || parseMermaidTimelineForPdf(source, startLineIndex)
    || parseMermaidMindmapForPdf(source, startLineIndex)
  );

  const projectMermaidToPdfLines = (source: string): string[] => {
    const mermaidLines = source.split(/\r?\n/).map(line => line.trim()).filter(Boolean);
    const firstLine = mermaidLines[0] || 'diagram';
    const diagramType = firstLine.split(/\s+/)[0] || 'diagram';
    const parsedDiagram = parseMermaidDiagramForPdf(source, 0);
    if (parsedDiagram?.kind === 'timeline') {
      return [
        `Mermaid 图表：${diagramType}`,
        ...(parsedDiagram.title ? [parsedDiagram.title] : []),
        ...parsedDiagram.sections,
        ...parsedDiagram.events.map(event => `${event.time}：${event.description}`),
      ];
    }
    if (parsedDiagram?.kind === 'mindmap') {
      return [
        `Mermaid 图表：${diagramType}`,
        ...parsedDiagram.nodes.map(node => node.label),
      ];
    }
    return [
      `Mermaid 图表：${diagramType}`,
      ...(
        parsedDiagram?.kind === 'flowchart'
          ? parsedDiagram.nodes.map(node => node.label)
          : []
      ),
      ...mermaidLines.slice(1),
    ];
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

  const projectMarkdownToPdfDocument = (content: string): PdfProjectedDocument => {
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
          pdfLines.push(...projectMermaidToPdfLines(codeSource));
          const parsedDiagram = parseMermaidDiagramForPdf(codeSource, startLineIndex);
          if (parsedDiagram) {
            mermaidDiagrams.push(parsedDiagram);
          }
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
          pdfLines.push(
            `结构化可视化：${visual.title || visual.type}`,
            ...[
              visual.columns,
              ...visual.rows.map(row => row.cells),
            ].map(row => row.join('    '))
          );
          structuredTables.push({
            startLineIndex,
            columns: visual.columns,
            rows: visual.rows.map(row => row.cells),
          });
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
        while (index < lines.length && isNumberedItem(lines[index])) {
          const itemMatch = lines[index].match(/^\s*(\d+)[.)]\s+(.+)$/);
          if (itemMatch) {
            pdfLines.push(`${itemMatch[1]}. ${stripInlineMarkdown(itemMatch[2])}`);
          }
          index += 1;
        }
        continue;
      }

      pdfLines.push(stripInlineMarkdown(line));
      index += 1;
    }

    return {
      lines: pdfLines.length > 0 ? pdfLines : [' '],
      structuredTables,
      mermaidDiagrams,
    };
  };

  const buildCommentExcerpt = (content: string): string => {
    const lines = content.split(/\r?\n/);
    const firstBodyLine = lines.find((line) => {
      const trimmedLine = line.trim();
      return trimmedLine && !isHeading(trimmedLine) && !isFenceStart(trimmedLine);
    }) || lines.find(line => line.trim()) || '当前产出物';
    const excerpt = stripInlineMarkdown(firstBodyLine.replace(/^\s*[-*]\s+/, ''));
    return excerpt.length > 120 ? `${excerpt.slice(0, 117)}...` : excerpt;
  };

  const normalizeCommentAnchorText = (value: string): string | null => {
    const normalizedValue = value.replace(/\s+/g, ' ').trim();
    if (!normalizedValue) return null;
    return normalizedValue.length > 120
      ? `${normalizedValue.slice(0, 117)}...`
      : normalizedValue;
  };

  const readSelectedArtifactText = (): string | null => {
    const selection = window.getSelection();
    const container = artifactPreviewRef.current;
    if (!selection || selection.rangeCount === 0 || !container) {
      return null;
    }

    const range = selection.getRangeAt(0);
    const anchorNode = range.commonAncestorContainer;
    const selectedNode = anchorNode.nodeType === Node.ELEMENT_NODE
      ? anchorNode
      : anchorNode.parentElement;
    const selectionInsideArtifact = selectedNode !== null
      && container.contains(selectedNode);
    if (!selectionInsideArtifact) {
      return null;
    }

    return normalizeCommentAnchorText(selection.toString());
  };

  const captureSelectedArtifactText = () => {
    const nextSelectedText = readSelectedArtifactText();
    if (nextSelectedText) {
      setSelectedArtifactText(nextSelectedText);
    }
    return nextSelectedText;
  };

  const artifactSections = useMemo(
    () => extractMarkdownSections(artifactContent),
    [artifactContent]
  );

  const findLockedSectionChange = (nextContent: string): string | null => {
    if (currentStageSectionLocks.length === 0) return null;
    const nextSections = extractMarkdownSections(nextContent);
    for (const lock of currentStageSectionLocks) {
      const nextSection = nextSections.find(section => section.heading === lock.heading);
      if (!nextSection || nextSection.content.trim() !== lock.content.trim()) {
        return lock.heading.replace(/^#{1,3}\s+/, '');
      }
    }
    return null;
  };

  const PDF_LINES_PER_PAGE = 42;

  const buildPdfTableDrawingCommands = (
    pageStartLineIndex: number,
    tables: PdfStructuredVisualTable[]
  ): string[] => {
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
      if (visibleStartLineIndex >= visibleEndLineIndex) {
        return;
      }
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
  };

  const buildPdfMermaidDrawingCommands = (
    pageStartLineIndex: number,
    diagrams: PdfMermaidDiagram[]
  ): string[] => {
    const commands: string[] = [];
    const pageEndLineIndex = pageStartLineIndex + PDF_LINES_PER_PAGE;
    const nodeWidth = 150;
    const nodeHeight = 24;
    const nodeGap = 18;
    const nodeLeft = 385;
    const timelineLeft = 64;
    const timelineWidth = 480;
    const timelineEventWidth = 120;
    const timelineEventHeight = 24;
    const mindmapLeft = 56;
    const mindmapNodeWidth = 132;
    const mindmapNodeHeight = 22;
    const mindmapColumnGap = 144;
    const mindmapRowGap = 10;

    diagrams.forEach((diagram) => {
      const diagramLineCount = diagram.kind === 'flowchart'
        ? Math.max(diagram.nodes.length + 1, 2)
        : diagram.kind === 'timeline'
          ? Math.max(diagram.events.length + diagram.sections.length + 2, 3)
          : Math.max(diagram.nodes.length + 1, 2);
      const diagramEndLineIndex = diagram.startLineIndex + diagramLineCount;
      if (diagram.startLineIndex >= pageEndLineIndex || diagramEndLineIndex <= pageStartLineIndex) {
        return;
      }

      const localStartLineIndex = Math.max(diagram.startLineIndex, pageStartLineIndex) - pageStartLineIndex;
      const topY = Math.min(770, 790 - localStartLineIndex * 14 - 2);
      if (diagram.kind === 'timeline') {
        const eventCount = Math.max(diagram.events.length, 1);
        const baselineY = Math.max(130, topY - 44);
        const eventGap = eventCount > 1 ? timelineWidth / (eventCount - 1) : 0;
        commands.push(`${timelineLeft} ${baselineY} m ${timelineLeft + timelineWidth} ${baselineY} l S`);
        diagram.events.forEach((event, eventIndex) => {
          const tickX = Number((timelineLeft + eventGap * eventIndex).toFixed(2));
          const eventY = eventIndex % 2 === 0
            ? baselineY + 28
            : baselineY - 58;
          const eventX = Math.max(
            42,
            Math.min(448, tickX - timelineEventWidth / 2)
          );
          const connectorStartY = eventIndex % 2 === 0
            ? baselineY + 3
            : baselineY - 3;
          const connectorEndY = eventIndex % 2 === 0
            ? eventY
            : eventY + timelineEventHeight;

          commands.push(`${tickX} ${baselineY - 5} m ${tickX} ${baselineY + 5} l S`);
          commands.push(`${tickX} ${connectorStartY} m ${tickX} ${connectorEndY} l S`);
          commands.push(`${Number(eventX.toFixed(2))} ${eventY} ${timelineEventWidth} ${timelineEventHeight} re S`);
        });
        return;
      }

      if (diagram.kind === 'mindmap') {
        const nodePositions = new Map<string, { x: number; y: number }>();
        diagram.nodes.forEach((node, nodeIndex) => {
          const x = Math.min(430, mindmapLeft + node.depth * mindmapColumnGap);
          const y = Math.max(
            82,
            topY - nodeIndex * (mindmapNodeHeight + mindmapRowGap) - mindmapNodeHeight
          );
          nodePositions.set(node.id, { x, y });
          commands.push(`${x} ${y} ${mindmapNodeWidth} ${mindmapNodeHeight} re S`);
        });

        diagram.nodes.forEach((node) => {
          if (!node.parentId) return;
          const parentPosition = nodePositions.get(node.parentId);
          const nodePosition = nodePositions.get(node.id);
          if (!parentPosition || !nodePosition) return;

          const startX = Number((parentPosition.x + mindmapNodeWidth).toFixed(2));
          const startY = Number((parentPosition.y + mindmapNodeHeight / 2).toFixed(2));
          const endX = Number(nodePosition.x.toFixed(2));
          const endY = Number((nodePosition.y + mindmapNodeHeight / 2).toFixed(2));
          commands.push(`${startX} ${startY} m ${endX} ${endY} l S`);
        });
        return;
      }

      const nodePositions = new Map<string, { x: number; y: number }>();

      diagram.nodes.forEach((node, nodeIndex) => {
        const y = Math.max(82, topY - nodeIndex * (nodeHeight + nodeGap) - nodeHeight);
        nodePositions.set(node.id, { x: nodeLeft, y });
        commands.push(`${nodeLeft} ${y} ${nodeWidth} ${nodeHeight} re S`);
      });

      diagram.edges.forEach((edge) => {
        const fromPosition = nodePositions.get(edge.from);
        const toPosition = nodePositions.get(edge.to);
        if (!fromPosition || !toPosition) return;

        const startX = Number((fromPosition.x + nodeWidth / 2).toFixed(2));
        const startY = Number(fromPosition.y.toFixed(2));
        const endX = Number((toPosition.x + nodeWidth / 2).toFixed(2));
        const endY = Number((toPosition.y + nodeHeight).toFixed(2));
        commands.push(`${startX} ${startY} m ${endX} ${endY} l S`);
        commands.push(`${endX - 4} ${endY + 5} m ${endX} ${endY} l ${endX + 4} ${endY + 5} l S`);
      });
    });

    return commands.length > 0
      ? ['q', '0.7 w', '0.18 0.55 0.95 RG', ...commands, 'Q']
      : [];
  };

  const buildPdfContentStream = (
    lines: string[],
    pageStartLineIndex: number,
    tables: PdfStructuredVisualTable[],
    mermaidDiagrams: PdfMermaidDiagram[]
  ): string => {
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
  };

  const buildPlainTextPdf = (content: string): string => {
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
        `${pageObjectId} 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] /Resources << /Font << /F1 ${fontObjectId} 0 R >> >> /Contents ${contentObjectId} 0 R >>\nendobj\n`,
        `${contentObjectId} 0 obj\n<< /Length ${stream.length} >>\nstream\n${stream}\nendstream\nendobj\n`,
      );
    });
    objects.push(`${fontObjectId} 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n`);

    let pdf = '%PDF-1.4\n';
    const offsets = [0];
    objects.forEach((object) => {
      offsets.push(pdf.length);
      pdf += object;
    });
    const xrefOffset = pdf.length;
    pdf += `xref\n0 ${objects.length + 1}\n`;
    pdf += '0000000000 65535 f \n';
    offsets.slice(1).forEach((offset) => {
      pdf += `${offset.toString().padStart(10, '0')} 00000 n \n`;
    });
    pdf += [
      'trailer',
      `<< /Size ${objects.length + 1} /Root 1 0 R >>`,
      'startxref',
      `${xrefOffset}`,
      '%%EOF',
    ].join('\n');
    return pdf;
  };

  const downloadBlob = (blob: Blob, filename: string) => {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleDownload = (format: 'markdown' | 'word' | 'pdf') => {
    setShowExportMenu(false);
    if (format === 'word') {
      downloadBlob(
        buildDocxPackage(artifactContent),
        `${workflow.toLowerCase()}_artifact.docx`
      );
      return;
    }
    if (format === 'pdf') {
      downloadBlob(
        new Blob([buildPlainTextPdf(artifactContent)], { type: 'application/pdf' }),
        `${workflow.toLowerCase()}_artifact.pdf`
      );
      return;
    }

    downloadBlob(
      new Blob([artifactContent], { type: 'text/markdown' }),
      `${workflow.toLowerCase()}_artifact.md`
    );
  };

  const openHistory = () => {
    if (currentStageArtifactHistory.length > 0) {
      setSelectedVersion(currentStageArtifactHistory[currentStageArtifactHistory.length - 1]);
    } else {
      setSelectedVersion(null);
    }
    setHistoryViewMode('preview');
    setShowHistory(true);
  };

  useEffect(() => {
    if (!showHistory) return;
    if (
      selectedVersion
      && currentStageArtifactHistory.some(version => version.id === selectedVersion.id)
    ) {
      return;
    }
    setSelectedVersion(
      currentStageArtifactHistory.length > 0
        ? currentStageArtifactHistory[currentStageArtifactHistory.length - 1]
        : null
    );
  }, [currentStageArtifactHistory, selectedVersion, showHistory]);

  // Content displays using the imported preprocessMarkdown utility

  const displayContent = preprocessMarkdown(artifactContent);
  const truncateAuditLine = (lineContent: string): string => {
    const normalizedLine = lineContent.replace(/\s+/g, ' ').trim();
    return normalizedLine.length > 60
      ? `${normalizedLine.slice(0, 57)}...`
      : normalizedLine;
  };
  const buildConflictMergeBlockLabel = (lineContents: string[]): string => (
    lineContents.map(truncateAuditLine).join(' / ')
  );
  const buildConflictModificationBlockLabel = (removedLines: string[], addedLines: string[]): string => (
    `${buildConflictMergeBlockLabel(removedLines)} → ${buildConflictMergeBlockLabel(addedLines)}`
  );
  const replaceFirstLineSequence = (
    sourceLines: string[],
    targetLines: string[],
    replacementLines: string[]
  ): string[] => {
    const normalizedTargetLines = targetLines.filter(line => line.trim());
    if (normalizedTargetLines.length === 0) return sourceLines;

    const startIndex = sourceLines.findIndex((_, index) => (
      normalizedTargetLines.every((targetLine, offset) => sourceLines[index + offset] === targetLine)
    ));
    if (startIndex < 0) return sourceLines;

    return [
      ...sourceLines.slice(0, startIndex),
      ...replacementLines.filter(line => line.trim()),
      ...sourceLines.slice(startIndex + normalizedTargetLines.length),
    ];
  };
  const collectInsertionSegments = (
    baseLines: string[],
    targetLines: string[]
  ): string[][] | null => {
    const segments = Array.from({ length: baseLines.length + 1 }, () => [] as string[]);
    let targetIndex = 0;

    for (let baseIndex = 0; baseIndex < baseLines.length; baseIndex += 1) {
      while (targetIndex < targetLines.length && targetLines[targetIndex] !== baseLines[baseIndex]) {
        segments[baseIndex].push(targetLines[targetIndex]);
        targetIndex += 1;
      }
      if (targetIndex >= targetLines.length) {
        return null;
      }
      targetIndex += 1;
    }

    segments[baseLines.length].push(...targetLines.slice(targetIndex));
    return segments;
  };
  const collectDraftInsertionSegments = (
    baseLines: string[],
    draftLines: string[]
  ): {
    segments: string[][];
    retainedBaseLineIndexes: Set<number>;
    hasDraftDeletion: boolean;
  } | null => {
    const segments = Array.from({ length: baseLines.length + 1 }, () => [] as string[]);
    const retainedBaseLineIndexes = new Set<number>();
    const pendingInsertions: string[] = [];
    let baseIndex = 0;

    const flushPendingInsertions = (segmentIndex: number) => {
      if (pendingInsertions.length === 0) return;
      segments[segmentIndex].push(...pendingInsertions);
      pendingInsertions.length = 0;
    };

    for (const draftLine of draftLines) {
      if (baseIndex >= baseLines.length) {
        if (baseLines.includes(draftLine)) return null;
        pendingInsertions.push(draftLine);
        continue;
      }

      if (draftLine === baseLines[baseIndex]) {
        flushPendingInsertions(baseIndex);
        retainedBaseLineIndexes.add(baseIndex);
        baseIndex += 1;
        continue;
      }

      const futureMatchIndex = baseLines.findIndex((baseLine, index) => (
        index > baseIndex && baseLine === draftLine
      ));
      if (futureMatchIndex >= 0) {
        flushPendingInsertions(futureMatchIndex);
        retainedBaseLineIndexes.add(futureMatchIndex);
        baseIndex = futureMatchIndex + 1;
        continue;
      }

      if (baseLines.includes(draftLine)) return null;
      pendingInsertions.push(draftLine);
    }

    flushPendingInsertions(baseLines.length);
    return {
      segments,
      retainedBaseLineIndexes,
      hasDraftDeletion: retainedBaseLineIndexes.size < baseLines.length,
    };
  };
  const mergeUniqueInsertions = (primaryLines: string[], secondaryLines: string[]): string[] => {
    const mergedLines = [...primaryLines];
    secondaryLines.forEach((line) => {
      if (!mergedLines.includes(line)) {
        mergedLines.push(line);
      }
    });
    return mergedLines;
  };
  const hasRepeatedNonBlankLines = (lines: string[]): boolean => {
    const seenLines = new Set<string>();
    return lines.some((line) => {
      if (!line.trim()) return false;
      if (seenLines.has(line)) return true;
      seenLines.add(line);
      return false;
    });
  };
  const buildAutoMergedInsertionContent = (
    baseContent: string,
    serverContent: string,
    draftContent: string
  ): string | null => {
    const baseLines = baseContent.replace(/\r\n/g, '\n').split('\n');
    const serverLines = serverContent.replace(/\r\n/g, '\n').split('\n');
    const draftLines = draftContent.replace(/\r\n/g, '\n').split('\n');
    const serverSegments = collectInsertionSegments(baseLines, serverLines);
    const draftMerge = collectDraftInsertionSegments(baseLines, draftLines);
    if (!serverSegments || !draftMerge) return null;
    if (draftMerge.hasDraftDeletion && hasRepeatedNonBlankLines(baseLines)) return null;

    const mergedLines: string[] = [];
    let appliedDraftChange = draftMerge.hasDraftDeletion;
    for (let segmentIndex = 0; segmentIndex < serverSegments.length; segmentIndex += 1) {
      const draftInsertions = draftMerge.segments[segmentIndex];
      const mergedInsertions = mergeUniqueInsertions(serverSegments[segmentIndex], draftInsertions);
      if (draftInsertions.some(line => !serverSegments[segmentIndex].includes(line))) {
        appliedDraftChange = true;
      }
      mergedLines.push(...mergedInsertions);
      if (segmentIndex < baseLines.length && draftMerge.retainedBaseLineIndexes.has(segmentIndex)) {
        mergedLines.push(baseLines[segmentIndex]);
      }
    }

    const mergedContent = mergedLines.join('\n');
    if (!appliedDraftChange || mergedContent === serverContent.replace(/\r\n/g, '\n')) {
      return null;
    }
    return mergedContent;
  };
  const selectedVersionDiff = useMemo(
    () => selectedVersion
      ? buildLineDiff(selectedVersion.content, artifactContent)
      : [],
    [artifactContent, selectedVersion]
  );
  const conflictDraftDiff = useMemo(
    () => conflictArtifact
      ? buildLineDiff(conflictArtifact.content, editDraft)
      : [],
    [conflictArtifact, editDraft]
  );
  const conflictDraftAddedBlocks = useMemo(() => {
    const blocks: Array<{ startIndex: number; lines: string[]; label: string }> = [];
    let blockStartIndex: number | null = null;
    let blockLines: string[] = [];

    const flushBlock = () => {
      if (blockStartIndex !== null && blockLines.length > 1) {
        blocks.push({
          startIndex: blockStartIndex,
          lines: blockLines,
          label: buildConflictMergeBlockLabel(blockLines),
        });
      }
      blockStartIndex = null;
      blockLines = [];
    };

    conflictDraftDiff.forEach((line, index) => {
      if (line.type === 'added' && line.content.trim()) {
        if (blockStartIndex === null) {
          blockStartIndex = index;
        }
        blockLines.push(line.content);
        return;
      }
      flushBlock();
    });
    flushBlock();

    return blocks;
  }, [conflictDraftDiff]);
  const conflictDraftAddedBlockByStartIndex = useMemo(
    () => new Map(conflictDraftAddedBlocks.map(block => [block.startIndex, block])),
    [conflictDraftAddedBlocks]
  );
  const conflictDraftModifiedBlocks = useMemo(() => {
    const blocks: Array<{
      addedStartIndex: number;
      removedLines: string[];
      addedLines: string[];
      label: string;
    }> = [];
    let index = 0;

    while (index < conflictDraftDiff.length) {
      if (conflictDraftDiff[index]?.type !== 'removed') {
        index += 1;
        continue;
      }

      const removedLines: string[] = [];
      while (conflictDraftDiff[index]?.type === 'removed') {
        const content = conflictDraftDiff[index].content;
        if (content.trim()) removedLines.push(content);
        index += 1;
      }

      const addedStartIndex = index;
      const addedLines: string[] = [];
      while (conflictDraftDiff[index]?.type === 'added') {
        const content = conflictDraftDiff[index].content;
        if (content.trim()) addedLines.push(content);
        index += 1;
      }

      if (removedLines.length > 0 && addedLines.length > 0) {
        blocks.push({
          addedStartIndex,
          removedLines,
          addedLines,
          label: buildConflictModificationBlockLabel(removedLines, addedLines),
        });
      }
    }

    return blocks;
  }, [conflictDraftDiff]);
  const conflictDraftModifiedBlockByAddedStartIndex = useMemo(
    () => new Map(conflictDraftModifiedBlocks.map(block => [block.addedStartIndex, block])),
    [conflictDraftModifiedBlocks]
  );
  const autoMergedConflictContent = useMemo(
    () => conflictArtifact
      ? buildAutoMergedInsertionContent(artifactContent, conflictArtifact.content, editDraft)
      : null,
    [artifactContent, conflictArtifact, editDraft]
  );

  const handleMermaidRetry = useCallback(async (brokenCode: string, errorMessage: string, blockIndex: number) => {
    // dynamically import to avoid cyclic or immediate heavy deps
    const { retryMermaidGeneration } = await import('../services/mermaidRetryService');
    const newCode = await retryMermaidGeneration(brokenCode, errorMessage, blockIndex);
    if (!newCode) return false;

    const content = useStore.getState().artifactContent;
    const updatedContent = replaceMermaidBlockAtIndex(content, blockIndex, newCode);
    if (!updatedContent) return false;

    useStore.getState().setArtifactContent(updatedContent);
    return true;
  }, []);

  const handleRestoreSelectedVersion = () => {
    if (!selectedVersion || !currentStageId || selectedVersion.content === artifactContent) {
      setShowHistory(false);
      return;
    }

    addArtifactVersion({
      id: `restore-backup-${Date.now()}`,
      timestamp: Date.now(),
      content: artifactContent,
      stageId: currentStageId,
    });
    setArtifactContent(selectedVersion.content);
    setShowHistory(false);
  };

  const applyHistoryLineReview = (nextContent: string) => {
    if (!currentStageId || nextContent === artifactContent) return;

    const timestamp = Date.now();
    addArtifactVersion({
      id: `history-line-review-backup-${timestamp}`,
      timestamp,
      content: artifactContent,
      stageId: currentStageId,
    });
    setArtifactContent(nextContent);
  };

  const restoreHistoryLine = (lineContent: string) => {
    if (!selectedVersion || !lineContent.trim()) return;

    const currentLines = artifactContent.replace(/\r\n/g, '\n').split('\n');
    if (currentLines.includes(lineContent)) return;

    const historyLines = selectedVersion.content.replace(/\r\n/g, '\n').split('\n');
    const historyLineIndex = historyLines.findIndex(line => line === lineContent);
    if (historyLineIndex < 0) return;

    const insertIndex = Math.min(historyLineIndex, currentLines.length);
    applyHistoryLineReview([
      ...currentLines.slice(0, insertIndex),
      lineContent,
      ...currentLines.slice(insertIndex),
    ].join('\n'));
  };

  const discardCurrentLine = (lineContent: string) => {
    if (!lineContent.trim()) return;

    const currentLines = artifactContent.replace(/\r\n/g, '\n').split('\n');
    const currentLineIndex = currentLines.findIndex(line => line === lineContent);
    if (currentLineIndex < 0) return;

    applyHistoryLineReview([
      ...currentLines.slice(0, currentLineIndex),
      ...currentLines.slice(currentLineIndex + 1),
    ].join('\n'));
  };

  const beginManualEdit = () => {
    setEditDraft(artifactContent);
    setManualEditError(null);
    setConflictVersionNumber(null);
    setConflictArtifact(null);
    setShowConflictDiff(false);
    setIsEditing(true);
    setShowExportMenu(false);
    setShowComments(false);
    setShowSectionLocks(false);
  };

  const cancelManualEdit = () => {
    if (isSavingManualEdit) return;
    setEditDraft('');
    setManualEditError(null);
    setConflictVersionNumber(null);
    setConflictArtifact(null);
    setShowConflictDiff(false);
    setIsEditing(false);
  };

  const inferCurrentServerVersionNumber = (): number | undefined => {
    if (!currentRunId || !currentStageId) return undefined;
    const latestCurrentStageVersion = currentStageArtifactHistory[currentStageArtifactHistory.length - 1];
    if (!latestCurrentStageVersion || latestCurrentStageVersion.content !== artifactContent) {
      return undefined;
    }
    const expectedPrefix = `${currentRunId}-${currentStageId}-v`;
    if (!latestCurrentStageVersion.id.startsWith(expectedPrefix)) {
      return undefined;
    }
    const versionNumber = Number.parseInt(
      latestCurrentStageVersion.id.slice(expectedPrefix.length),
      10
    );
    return Number.isInteger(versionNumber) ? versionNumber : undefined;
  };

  const saveManualEdit = async () => {
    if (!currentStageId) return;

    if (editDraft === artifactContent) {
      setIsEditing(false);
      setEditDraft('');
      setManualEditError(null);
      setConflictVersionNumber(null);
      setConflictArtifact(null);
      setShowConflictDiff(false);
      return;
    }

    setIsSavingManualEdit(true);
    setManualEditError(null);
    setConflictVersionNumber(null);
    setConflictArtifact(null);
    setShowConflictDiff(false);

    const changedLockedSection = findLockedSectionChange(editDraft);
    if (changedLockedSection) {
      setManualEditError(`保存失败：锁定章节“${changedLockedSection}”已被修改，请先解锁后再保存。`);
      setIsSavingManualEdit(false);
      return;
    }

    let savedContent = editDraft;
    let savedVersionId: string | null = null;
    if (currentRunId) {
      try {
        const savedArtifact = await updateRunArtifact(
          currentRunId,
          currentStageId,
          editDraft,
          { expectedVersionNumber: inferCurrentServerVersionNumber() },
        );
        savedContent = savedArtifact.content;
        savedVersionId = `${currentRunId}-${savedArtifact.stageId}-v${savedArtifact.versionNumber}`;
      } catch (error) {
        if (error instanceof ArtifactConflictError) {
          setManualEditError(`保存冲突：${error.message}`);
          setConflictVersionNumber(error.currentArtifact.versionNumber);
          setConflictArtifact(error.currentArtifact);
          setIsSavingManualEdit(false);
          return;
        }
        const message = error instanceof Error ? error.message : '未知错误';
        setManualEditError(`保存失败：${message}`);
        setIsSavingManualEdit(false);
        return;
      }
    }

    const latestCurrentStageVersion = currentStageArtifactHistory[currentStageArtifactHistory.length - 1];
    const timestamp = Date.now();
    if (latestCurrentStageVersion?.content !== artifactContent) {
      addArtifactVersion({
        id: `manual-edit-backup-${timestamp}`,
        timestamp,
        content: artifactContent,
        stageId: currentStageId,
      });
    }
    addArtifactVersion({
      id: savedVersionId ?? `manual-edit-${timestamp}`,
      timestamp: timestamp + 1,
      content: savedContent,
      stageId: currentStageId,
    });
    setArtifactContent(savedContent);
    setEditDraft('');
    setManualEditError(null);
    setConflictVersionNumber(null);
    setConflictArtifact(null);
    setShowConflictDiff(false);
    setIsSavingManualEdit(false);
    setIsEditing(false);
  };

  const refreshToConflictArtifact = () => {
    if (!conflictArtifact || !currentStageId) return;

    const latestCurrentStageVersion = currentStageArtifactHistory[currentStageArtifactHistory.length - 1];
    const timestamp = Date.now();
    if (latestCurrentStageVersion?.content !== artifactContent) {
      addArtifactVersion({
        id: `conflict-local-backup-${timestamp}`,
        timestamp,
        content: artifactContent,
        stageId: currentStageId,
      });
    }
    addArtifactVersion({
      id: `conflict-draft-${timestamp}`,
      timestamp: timestamp + 1,
      content: editDraft,
      stageId: currentStageId,
    });
    addArtifactVersion({
      id: currentRunId
        ? `${currentRunId}-${conflictArtifact.stageId}-v${conflictArtifact.versionNumber}`
        : `conflict-server-${timestamp}`,
      timestamp: timestamp + 2,
      content: conflictArtifact.content,
      stageId: currentStageId,
    });
    setArtifactContent(conflictArtifact.content);
    setEditDraft('');
    setManualEditError(null);
    setConflictVersionNumber(null);
    setConflictArtifact(null);
    setShowConflictDiff(false);
    setIsEditing(false);
  };

  const recordArtifactMergeAuditEvent = (
    eventType: 'artifact_merge_line_accepted' | 'artifact_merge_line_discarded',
    lineContent: string
  ) => {
    if (!currentStageId) return;
    const actionLabel = eventType === 'artifact_merge_line_accepted' ? '采纳草稿行' : '丢弃草稿行';
    addArtifactAuditEvent({
      stageId: currentStageId,
      eventType,
      summary: `合并轨迹：${actionLabel}「${truncateAuditLine(lineContent)}」`,
    });
  };

  const recordArtifactMergeBlockAuditEvent = (
    eventType: 'artifact_merge_block_accepted' | 'artifact_merge_block_discarded',
    lineContents: string[]
  ) => {
    if (!currentStageId) return;
    const actionLabel = eventType === 'artifact_merge_block_accepted' ? '采纳草稿变更块' : '丢弃草稿变更块';
    addArtifactAuditEvent({
      stageId: currentStageId,
      eventType,
      summary: `合并轨迹：${actionLabel}「${buildConflictMergeBlockLabel(lineContents)}」`,
    });
  };

  const recordArtifactModifiedBlockAuditEvent = (
    eventType: 'artifact_merge_block_modified_accepted' | 'artifact_merge_block_modified_kept',
    removedLines: string[],
    addedLines: string[]
  ) => {
    if (!currentStageId) return;
    const actionLabel = eventType === 'artifact_merge_block_modified_accepted'
      ? '采纳草稿修改块'
      : '保留服务端修改块';
    addArtifactAuditEvent({
      stageId: currentStageId,
      eventType,
      summary: `合并轨迹：${actionLabel}「${buildConflictModificationBlockLabel(removedLines, addedLines)}」`,
    });
  };

  const discardConflictDraftLine = (lineContent: string) => {
    if (!lineContent.trim()) return;

    const draftLines = editDraft.replace(/\r\n/g, '\n').split('\n');
    const lineIndex = draftLines.findIndex(line => line === lineContent);
    if (lineIndex < 0) return;

    setEditDraft([
      ...draftLines.slice(0, lineIndex),
      ...draftLines.slice(lineIndex + 1),
    ].join('\n'));
    recordArtifactMergeAuditEvent('artifact_merge_line_discarded', lineContent);
  };

  const discardConflictDraftBlock = (lineContents: string[]) => {
    const blockLines = lineContents.filter(line => line.trim());
    if (blockLines.length === 0) return;

    const nextDraftLines = editDraft.replace(/\r\n/g, '\n').split('\n');
    blockLines.forEach((lineContent) => {
      const lineIndex = nextDraftLines.findIndex(line => line === lineContent);
      if (lineIndex >= 0) {
        nextDraftLines.splice(lineIndex, 1);
      }
    });

    setEditDraft(nextDraftLines.join('\n'));
    recordArtifactMergeBlockAuditEvent('artifact_merge_block_discarded', blockLines);
  };

  const acceptConflictDraftBlock = (lineContents: string[]) => {
    if (!conflictArtifact) return;
    const blockLines = lineContents.filter(line => line.trim());
    if (blockLines.length === 0) return;

    const serverContent = conflictArtifact.content.replace(/\r\n/g, '\n');
    const serverLines = serverContent.split('\n');
    const linesToAppend = blockLines.filter(lineContent => !serverLines.includes(lineContent));
    if (linesToAppend.length === 0) {
      setEditDraft(serverContent);
      return;
    }

    setEditDraft(
      serverContent.endsWith('\n')
        ? `${serverContent}${linesToAppend.join('\n')}`
        : `${serverContent}\n${linesToAppend.join('\n')}`
    );
    recordArtifactMergeBlockAuditEvent('artifact_merge_block_accepted', linesToAppend);
  };

  const acceptConflictDraftModificationBlock = (removedLines: string[], addedLines: string[]) => {
    if (!conflictArtifact) return;
    const serverLines = conflictArtifact.content.replace(/\r\n/g, '\n').split('\n');
    const nextDraftLines = replaceFirstLineSequence(serverLines, removedLines, addedLines);
    if (nextDraftLines === serverLines) return;

    setEditDraft(nextDraftLines.join('\n'));
    recordArtifactModifiedBlockAuditEvent(
      'artifact_merge_block_modified_accepted',
      removedLines.filter(line => line.trim()),
      addedLines.filter(line => line.trim())
    );
  };

  const keepServerModificationBlock = (removedLines: string[], addedLines: string[]) => {
    if (!conflictArtifact) return;

    setEditDraft(conflictArtifact.content.replace(/\r\n/g, '\n'));
    recordArtifactModifiedBlockAuditEvent(
      'artifact_merge_block_modified_kept',
      removedLines.filter(line => line.trim()),
      addedLines.filter(line => line.trim())
    );
  };

  const applyAutoMergedConflictContent = () => {
    if (!autoMergedConflictContent || !currentStageId) return;

    setEditDraft(autoMergedConflictContent);
    addArtifactAuditEvent({
      stageId: currentStageId,
      eventType: 'artifact_auto_merge_applied',
      summary: '合并轨迹：自动合并服务端与草稿的非重叠补充',
    });
  };

  const acceptConflictDraftLine = (lineContent: string) => {
    if (!conflictArtifact || !lineContent.trim()) return;

    const serverContent = conflictArtifact.content.replace(/\r\n/g, '\n');
    const serverLines = serverContent.split('\n');
    if (serverLines.includes(lineContent)) {
      setEditDraft(serverContent);
      return;
    }

    setEditDraft(
      serverContent.endsWith('\n')
        ? `${serverContent}${lineContent}`
        : `${serverContent}\n${lineContent}`
    );
    recordArtifactMergeAuditEvent('artifact_merge_line_accepted', lineContent);
  };

  const addCurrentStageComment = () => {
    if (!currentStageId) return;
    const content = commentDraft.trim();
    if (!content) return;
    const anchorText = captureSelectedArtifactText() ?? selectedArtifactText;
    const artifactExcerpt = anchorText ?? buildCommentExcerpt(artifactContent);
    addArtifactComment({
      stageId: currentStageId,
      content,
      artifactExcerpt,
      anchorText,
    });
    syncArtifactCollaborationState();
    setCommentDraft('');
  };

  const removeCurrentStageComment = (commentId: string) => {
    removeArtifactComment(commentId);
    syncArtifactCollaborationState();
  };

  const addCurrentStageCommentReply = (commentId: string) => {
    const content = commentReplyDrafts[commentId]?.trim() ?? '';
    if (!content) return;
    addArtifactCommentReply(commentId, content);
    syncArtifactCollaborationState();
    setCommentReplyDrafts((drafts) => ({
      ...drafts,
      [commentId]: '',
    }));
  };

  const toggleCurrentStageCommentStatus = (
    commentId: string,
    currentStatus: 'open' | 'resolved'
  ) => {
    setArtifactCommentStatus(commentId, currentStatus === 'resolved' ? 'open' : 'resolved');
    syncArtifactCollaborationState();
  };

  const locateArtifactCommentAnchor = (anchorText: string) => {
    const normalizedAnchorText = normalizeCommentAnchorText(anchorText);
    if (!normalizedAnchorText) return;
    setIsEditing(false);
    setViewMode('preview');
    setActiveCommentAnchorText(normalizedAnchorText);
    window.setTimeout(() => {
      const highlight = artifactPreviewRef.current?.querySelector('[data-artifact-anchor-highlight="true"]');
      if (highlight instanceof HTMLElement && typeof highlight.scrollIntoView === 'function') {
        highlight.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }, 0);
  };

  const locateArtifactVisualDiagnostic = useCallback((
    request: ArtifactVisualDiagnosticFocusRequest | null,
    diagnostics: ArtifactVisualDiagnostic[]
  ) => {
    if (!request || !currentStageId) return;
    if (handledVisualDiagnosticFocusSeqRef.current === request.seq) return;

    const diagnostic = diagnostics.find(
      candidate => candidate.id === request.id && candidate.stageId === currentStageId
    );
    if (!diagnostic) return;

    handledVisualDiagnosticFocusSeqRef.current = request.seq;
    setIsEditing(false);
    setViewMode('preview');
    setActiveVisualDiagnosticId(diagnostic.id);
    window.setTimeout(() => {
      const target = artifactPreviewRef.current?.querySelector(
        `[data-artifact-visual-diagnostic-id="${diagnostic.id}"]`
      );
      if (target instanceof HTMLElement && typeof target.scrollIntoView === 'function') {
        target.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }, 0);
  }, [currentStageId]);

  useEffect(() => {
    locateArtifactVisualDiagnostic(
      artifactVisualDiagnosticFocusRequest,
      artifactVisualDiagnostics
    );
  }, [artifactVisualDiagnosticFocusRequest, artifactVisualDiagnostics, currentStageId]);

  useEffect(() => useStore.subscribe((state) => {
    locateArtifactVisualDiagnostic(
      state.artifactVisualDiagnosticFocusRequest,
      state.artifactVisualDiagnostics
    );
  }), [locateArtifactVisualDiagnostic]);

  const lockSection = (section: ArtifactSection) => {
    if (!currentStageId) return;
    addArtifactSectionLock({
      stageId: currentStageId,
      heading: section.heading,
      content: section.content,
    });
    syncArtifactCollaborationState();
  };

  const unlockSection = (lockId: string) => {
    removeArtifactSectionLock(lockId);
    syncArtifactCollaborationState();
  };

  const getSectionLock = (heading: string) => (
    currentStageSectionLocks.find(lock => lock.heading === heading)
  );

  const buildVisualDiagnosticId = (kind: 'mermaid' | 'structured-visual', blockIndex: number): string => (
    `${kind}:${currentStageId || 'unknown'}:${blockIndex}`
  );

  const getVisualDiagnosticContainerClass = (diagnosticId: string): string => (
    `my-6 rounded-xl transition-shadow ${activeVisualDiagnosticId === diagnosticId
      ? 'ring-2 ring-amber-300/70 shadow-[0_0_0_4px_rgba(252,211,77,0.12)]'
      : 'ring-1 ring-transparent'}`
  );

  const handleMermaidRenderError = useCallback((details: { message: string; blockIndex: number }) => {
    if (!currentStageId) return;
    setArtifactVisualDiagnostic({
      id: buildVisualDiagnosticId('mermaid', details.blockIndex),
      stageId: currentStageId,
      kind: 'mermaid',
      title: 'Mermaid 图表渲染失败',
      message: details.message || '右侧 Mermaid 图表暂时无法渲染。',
      blockIndex: details.blockIndex,
    });
  }, [currentStageId, setArtifactVisualDiagnostic]);

  const handleMermaidRenderSuccess = useCallback((blockIndex: number) => {
    clearArtifactVisualDiagnostic(buildVisualDiagnosticId('mermaid', blockIndex));
  }, [clearArtifactVisualDiagnostic, currentStageId]);

  const handleStructuredVisualValidationError = useCallback((blockIndex: number, message: string) => {
    if (!currentStageId) return;
    setArtifactVisualDiagnostic({
      id: buildVisualDiagnosticId('structured-visual', blockIndex),
      stageId: currentStageId,
      kind: 'structured-visual',
      title: '结构化可视化格式错误',
      message,
      blockIndex,
    });
  }, [currentStageId, setArtifactVisualDiagnostic]);

  const handleStructuredVisualValidationSuccess = useCallback((blockIndex: number) => {
    clearArtifactVisualDiagnostic(buildVisualDiagnosticId('structured-visual', blockIndex));
  }, [clearArtifactVisualDiagnostic, currentStageId]);

  const createArtifactMarkdownComponents = (
    onMermaidRetry?: Parameters<typeof createMarkdownCodeRenderer>[0]['onMermaidRetry'],
    activeAnchorText?: string | null,
    reportVisualDiagnostics = false,
    attachVisualDiagnosticAnchors = false
  ): Components => {
    let mermaidBlockCounter = 0;
    let structuredVisualBlockCounter = 0;
    let anchorHighlighted = false;
    const normalizedActiveAnchorText = activeAnchorText?.trim() || null;
    const highlightAnchorInChildren = (children: React.ReactNode): React.ReactNode => {
      if (!normalizedActiveAnchorText || anchorHighlighted) return children;

      const visitNode = (node: React.ReactNode): React.ReactNode => {
        if (!normalizedActiveAnchorText || anchorHighlighted) return node;
        if (typeof node === 'string') {
          const anchorIndex = node.indexOf(normalizedActiveAnchorText);
          if (anchorIndex < 0) return node;
          anchorHighlighted = true;
          return (
            <>
              {node.slice(0, anchorIndex)}
              <mark
                data-artifact-anchor-highlight="true"
                className="rounded bg-amber-300/25 px-1 py-0.5 font-medium text-amber-100 ring-1 ring-amber-300/40"
              >
                {normalizedActiveAnchorText}
              </mark>
              {node.slice(anchorIndex + normalizedActiveAnchorText.length)}
            </>
          );
        }
        if (Array.isArray(node)) {
          return node.map((child, index) => (
            <React.Fragment key={index}>{visitNode(child)}</React.Fragment>
          ));
        }
        return node;
      };

      return visitNode(children);
    };

    return {
    h1: ({ node, children, ...props }) => <h1 className="text-3xl font-bold text-white mb-6 pb-2 border-b border-[#1e293b]" {...props}>{highlightAnchorInChildren(children)}</h1>,
    h2: ({ node, children, ...props }) => <h2 className="text-2xl font-bold text-white mt-8 mb-4 before:content-['#'] before:text-blue-500 before:opacity-50 before:mr-2" {...props}>{highlightAnchorInChildren(children)}</h2>,
    h3: ({ node, children, ...props }) => <h3 className="text-xl font-semibold text-slate-200 mt-6 mb-3" {...props}>{highlightAnchorInChildren(children)}</h3>,
    p: ({ node, children, ...props }) => <p className="mb-4 leading-relaxed text-slate-400" {...props}>{highlightAnchorInChildren(children)}</p>,
    ul: ({ node, ...props }) => <ul className="list-disc pl-6 mb-4 space-y-2 text-slate-400" {...props} />,
    ol: ({ node, ...props }) => <ol className="list-decimal pl-6 mb-4 space-y-2 text-slate-400" {...props} />,
    li: ({ node, children, ...props }) => <li className="leading-relaxed" {...props}>{highlightAnchorInChildren(children)}</li>,
    strong: ({ node, children, ...props }) => <strong className="font-bold text-white" {...props}>{highlightAnchorInChildren(children)}</strong>,
    blockquote: ({ node, children, ...props }) => <blockquote className="border-l-4 border-blue-500 pl-4 py-2 my-4 bg-blue-500/5 rounded-r text-slate-400 italic" {...props}>{highlightAnchorInChildren(children)}</blockquote>,
    table: ({ node, ...props }) => <div className="overflow-x-auto mb-6"><table className="w-full border-collapse text-sm" {...props} /></div>,
    th: ({ node, children, ...props }) => <th className="bg-[#1e293b] text-slate-200 font-semibold text-left p-3 border-b border-[#334155]" {...props}>{highlightAnchorInChildren(children)}</th>,
    td: ({ node, children, ...props }) => <td className="p-3 border-b border-[#1e293b] text-slate-400 group-hover:bg-white/5" {...props}>{highlightAnchorInChildren(children)}</td>,
    tr: ({ node, ...props }) => <tr className="hover:bg-white/[0.02] transition-colors group" {...props} />,
    mark: ({ node, ...props }) => <mark className="bg-emerald-500/15 text-emerald-400 px-1.5 py-0.5 rounded font-medium shadow-[0_0_8px_rgba(16,185,129,0.1)] box-decoration-clone" {...props} />,
    pre: ({ node, children }) => <>{children}</>,
    code: createMarkdownCodeRenderer({
      nextMermaidBlockIndex: () => mermaidBlockCounter++,
      onMermaidRetry,
      onMermaidRenderError: reportVisualDiagnostics ? handleMermaidRenderError : undefined,
      onMermaidRenderSuccess: reportVisualDiagnostics ? handleMermaidRenderSuccess : undefined,
      renderMermaid: attachVisualDiagnosticAnchors
        ? ({ blockIndex, element }) => {
          const diagnosticId = buildVisualDiagnosticId('mermaid', blockIndex);
          return (
            <div
              data-artifact-visual-diagnostic-id={diagnosticId}
              data-artifact-visual-focused={activeVisualDiagnosticId === diagnosticId ? 'true' : undefined}
              className={getVisualDiagnosticContainerClass(diagnosticId)}
            >
              {element}
            </div>
          );
        }
        : undefined,
      renderStructuredVisual: ({ children }) => (
        (() => {
          const blockIndex = structuredVisualBlockCounter++;
          const diagnosticId = buildVisualDiagnosticId('structured-visual', blockIndex);
          const visual = (
            <StructuredVisual
              source={String(children).replace(/\n$/, '')}
              onValidationError={reportVisualDiagnostics
                ? (message) => handleStructuredVisualValidationError(blockIndex, message)
                : undefined}
              onValidationSuccess={reportVisualDiagnostics
                ? () => handleStructuredVisualValidationSuccess(blockIndex)
                : undefined}
            />
          );
          if (!attachVisualDiagnosticAnchors) {
            return visual;
          }
          return (
            <div
              data-artifact-visual-diagnostic-id={diagnosticId}
              data-artifact-visual-focused={activeVisualDiagnosticId === diagnosticId ? 'true' : undefined}
              className={getVisualDiagnosticContainerClass(diagnosticId)}
            >
              {visual}
            </div>
          );
        })()
      ),
      renderBlockCode: ({ language, className, children, props }) => (
        <div className="relative my-6 rounded-lg overflow-hidden border border-[#1e293b] bg-[#0f172a]">
          {language && (
            <div className="flex items-center px-4 py-2 bg-[#1e293b] text-xs text-slate-400 font-mono border-b border-[#0f172a]">
              {language}
            </div>
          )}
          <pre className="p-4 overflow-x-auto text-sm font-mono text-slate-300">
            <code className={className} {...props}>
              {children}
            </code>
          </pre>
        </div>
      ),
      renderInlineCode: ({ children, props }) => (
        <code className="bg-white/10 text-blue-300 px-1.5 py-0.5 rounded font-mono text-sm" {...props}>
          {children}
        </code>
      ),
    }),
    };
  };

  const editableMarkdownComponents = createArtifactMarkdownComponents(
    handleMermaidRetry,
    activeCommentAnchorText,
    true,
    true
  );
  const readOnlyMarkdownComponents = createArtifactMarkdownComponents();

  return (
    <section className="flex flex-col w-full lg:w-[60%] bg-[#0B0F17] text-gray-300 relative shadow-2xl overflow-hidden bg-grid-pattern h-full">
      <style>{`
        .bg-grid-pattern {
            background-image: linear-gradient(to right, #1f2937 1px, transparent 1px), linear-gradient(to bottom, #1f2937 1px, transparent 1px);
            background-size: 40px 40px;
            background-color: #0d1117;
        }
        .bg-grid-pattern::before {
            content: "";
            position: absolute;
            inset: 0;
            background: radial-gradient(circle at center, transparent 0%, #0d1117 100%);
            pointer-events: none;
        }
      `}</style>

      <div className="flex items-center justify-between px-6 py-3 border-b border-[#1e293b] bg-[#0d1117]/80 backdrop-blur sticky top-0 z-10 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="p-1 rounded bg-purple-500/10 text-purple-400">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
          </div>
          <div className="flex flex-col">
            <h2 className="text-gray-200 font-semibold text-sm tracking-tight">当前产出物.md</h2>
            <span className="text-[10px] text-slate-500">实时渲染</span>
          </div>
          <span className={`ml-2 px-2 py-0.5 rounded-full text-[10px] font-medium border flex items-center gap-1 ${
            isGenerating
              ? 'bg-sky-500/10 text-sky-300 border-sky-500/20'
              : 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20'
          }`}>
            <span className={`w-1.5 h-1.5 rounded-full animate-pulse ${
              isGenerating ? 'bg-sky-300' : 'bg-emerald-500'
            }`}></span>
            {isGenerating ? '正在构建产出物' : '实时同步'}
          </span>
        </div>
        <div className="flex items-center gap-1 bg-[#0f172a] p-1 rounded-lg border border-[#1e293b]">
          <button onClick={() => setViewMode('preview')} className={`p-1.5 rounded transition-colors ${viewMode === 'preview' ? 'bg-white/10 text-white' : 'text-slate-400 hover:text-white hover:bg-white/5'}`} title="预览">
            <Eye className="w-4 h-4" />
          </button>
          <button onClick={() => setViewMode('code')} className={`p-1.5 rounded transition-colors ${viewMode === 'code' ? 'bg-white/10 text-white' : 'text-slate-400 hover:text-white hover:bg-white/5'}`} title="代码">
            <Code className="w-4 h-4" />
          </button>
          <div className="w-px h-4 bg-[#1e293b] mx-1"></div>
          <button onClick={openHistory} className="p-1.5 rounded hover:bg-white/10 text-slate-400 hover:text-white transition-colors" title="历史版本">
            <History className="w-4 h-4" />
          </button>
          <button
            onClick={beginManualEdit}
            disabled={isGenerating}
            className="p-1.5 rounded hover:bg-white/10 text-slate-400 hover:text-white transition-colors disabled:cursor-not-allowed disabled:opacity-40"
            title="编辑产出物"
          >
            <Edit3 className="w-4 h-4" />
          </button>
          <button
            onClick={() => {
              captureSelectedArtifactText();
              setShowComments((current) => !current);
              setShowExportMenu(false);
              setShowSectionLocks(false);
            }}
            className={`p-1.5 rounded transition-colors ${showComments ? 'bg-white/10 text-white' : 'text-slate-400 hover:text-white hover:bg-white/5'}`}
            title="批注"
          >
            <MessageSquare className="w-4 h-4" />
          </button>
          <button
            onClick={() => {
              setShowSectionLocks((current) => !current);
              setShowExportMenu(false);
              setShowComments(false);
            }}
            className={`p-1.5 rounded transition-colors ${showSectionLocks ? 'bg-white/10 text-white' : 'text-slate-400 hover:text-white hover:bg-white/5'}`}
            title="章节锁定"
          >
            <Lock className="w-4 h-4" />
          </button>
          <div className="relative">
            <button
              onClick={() => setShowExportMenu((current) => !current)}
              className="p-1.5 rounded hover:bg-white/10 text-slate-400 hover:text-white transition-colors"
              title="下载"
            >
              <Download className="w-4 h-4" />
            </button>
            {showExportMenu && (
              <div className="absolute right-0 top-full z-20 mt-2 w-36 overflow-hidden rounded-lg border border-[#1e293b] bg-[#0f172a] shadow-xl">
                <button
                  onClick={() => handleDownload('markdown')}
                  className="block w-full px-3 py-2 text-left text-xs font-semibold text-slate-200 hover:bg-white/5"
                >
                  Markdown
                </button>
                <button
                  onClick={() => handleDownload('word')}
                  className="block w-full px-3 py-2 text-left text-xs font-semibold text-slate-200 hover:bg-white/5"
                >
                  Word
                </button>
                <button
                  onClick={() => handleDownload('pdf')}
                  className="block w-full px-3 py-2 text-left text-xs font-semibold text-slate-200 hover:bg-white/5"
                >
                  PDF
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-8 md:px-16 relative z-0 custom-scrollbar">
        {/* P0-9: Truncation warning banner */}
        {artifactTruncated && (
          <div className="max-w-4xl mx-auto mb-4 flex items-center gap-3 px-4 py-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-300 text-sm">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>产出物内容可能因流式响应中断而不完整，请检查文档完整性。</span>
          </div>
        )}
        {isGenerating && (
          <div className="max-w-4xl mx-auto mb-4 overflow-hidden rounded-lg border border-sky-500/20 bg-sky-500/10 px-4 py-3 text-sky-100 shadow-[0_0_24px_rgba(14,165,233,0.08)]">
            <div className="flex items-center justify-between gap-4">
              <div className="min-w-0">
                <div className="text-sm font-medium">正在构建右侧产出物</div>
                <div className="mt-1 text-xs text-sky-200/70">模型正在整理结构、章节和图表内容</div>
              </div>
              <div
                className="flex h-8 shrink-0 items-end gap-1.5"
                data-testid="artifact-generation-animation"
                aria-hidden="true"
              >
                <span className="block h-3 w-1.5 rounded-full bg-sky-300/70 animate-pulse"></span>
                <span className="block h-5 w-1.5 rounded-full bg-cyan-200/80 animate-pulse [animation-delay:120ms]"></span>
                <span className="block h-7 w-1.5 rounded-full bg-blue-200/80 animate-pulse [animation-delay:240ms]"></span>
                <span className="block h-4 w-1.5 rounded-full bg-sky-300/70 animate-pulse [animation-delay:360ms]"></span>
              </div>
            </div>
          </div>
        )}
        <div
          ref={artifactPreviewRef}
          onMouseUp={captureSelectedArtifactText}
          onKeyUp={captureSelectedArtifactText}
          className="max-w-4xl mx-auto pb-20"
        >
          {isEditing ? (
            <div className="rounded-xl border border-blue-500/20 bg-[#0f172a] shadow-xl">
              <div className="flex items-center justify-between gap-3 border-b border-[#1e293b] px-4 py-3">
                <div>
                  <div className="text-sm font-semibold text-slate-100">编辑当前阶段产出物</div>
                  <div className="mt-0.5 text-xs text-slate-500">
                    保存后会写入当前阶段历史版本，可在历史版本中对比和恢复。
                  </div>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <button
                    type="button"
                    onClick={cancelManualEdit}
                    disabled={isSavingManualEdit}
                    className="rounded-lg px-3 py-1.5 text-xs font-semibold text-slate-300 transition-colors hover:bg-white/5 disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    取消编辑
                  </button>
                  <button
                    type="button"
                    onClick={saveManualEdit}
                    aria-label="保存修改"
                    disabled={isSavingManualEdit}
                    className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-bold text-white transition-colors hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    <Save className="h-3.5 w-3.5" />
                    {isSavingManualEdit ? '保存中' : '保存修改'}
                  </button>
                </div>
              </div>
              {manualEditError && (
                <div className="border-b border-red-500/20 bg-red-500/10 px-4 py-2 text-xs font-medium text-red-200">
                  <div className="flex flex-wrap items-center gap-2">
                    <span>{manualEditError}</span>
                    {conflictVersionNumber !== null && (
                      <span className="text-red-100/80">
                        服务端当前版本：v{conflictVersionNumber}
                      </span>
                    )}
                    {conflictArtifact && (
                      <div className="ml-auto flex shrink-0 items-center gap-2">
                        {autoMergedConflictContent && (
                          <button
                            type="button"
                            onClick={applyAutoMergedConflictContent}
                            className="rounded-md border border-emerald-300/20 px-2 py-1 text-[11px] font-semibold text-emerald-50 transition-colors hover:bg-emerald-400/10"
                          >
                            自动合并非重叠变更
                          </button>
                        )}
                        <button
                          type="button"
                          onClick={() => setShowConflictDiff((current) => !current)}
                          className="rounded-md border border-red-300/20 px-2 py-1 text-[11px] font-semibold text-red-50 transition-colors hover:bg-red-400/10"
                        >
                          对比服务端版本
                        </button>
                        <button
                          type="button"
                          onClick={refreshToConflictArtifact}
                          className="rounded-md bg-red-200 px-2 py-1 text-[11px] font-bold text-red-950 transition-colors hover:bg-red-100"
                        >
                          刷新为服务端版本
                        </button>
                      </div>
                    )}
                  </div>
                  {showConflictDiff && conflictArtifact && (
                    <div className="mt-3 rounded-lg border border-red-300/20 bg-[#0B1120] p-3">
                      <div className="mb-2 text-[11px] font-bold uppercase tracking-wide text-red-100">
                        服务端版本 vs 你的草稿
                      </div>
                      <div className="max-h-52 overflow-auto rounded border border-[#1e293b] bg-black/20 font-mono text-[11px] leading-relaxed">
                        {conflictDraftDiff.map((line, index) => (
                          <div
                            key={`${line.type}-${index}-${line.content}`}
                            className={`flex items-center gap-2 px-3 py-0.5 ${
                              line.type === 'added'
                                ? 'bg-emerald-500/10 text-emerald-200'
                                : line.type === 'removed'
                                  ? 'bg-red-500/10 text-red-200'
                                  : 'text-slate-400'
                            }`}
                          >
                            <span className="min-w-0 flex-1 whitespace-pre-wrap">
                              {line.type === 'added' ? '+ ' : line.type === 'removed' ? '- ' : '  '}
                              {line.content || ' '}
                            </span>
                            {line.type === 'added' && line.content.trim() && (
                              <span className="flex shrink-0 items-center gap-1">
                                {conflictDraftModifiedBlockByAddedStartIndex.has(index) && (
                                  <>
                                    <button
                                      type="button"
                                      onClick={() => {
                                        const block = conflictDraftModifiedBlockByAddedStartIndex.get(index);
                                        if (block) acceptConflictDraftModificationBlock(block.removedLines, block.addedLines);
                                      }}
                                      aria-label={`采纳修改块：${conflictDraftModifiedBlockByAddedStartIndex.get(index)?.label ?? line.content}`}
                                      className="rounded border border-blue-300/20 px-1.5 py-0.5 text-[10px] font-semibold text-blue-100 hover:bg-blue-300/10"
                                    >
                                      采纳修改块
                                    </button>
                                    <button
                                      type="button"
                                      onClick={() => {
                                        const block = conflictDraftModifiedBlockByAddedStartIndex.get(index);
                                        if (block) keepServerModificationBlock(block.removedLines, block.addedLines);
                                      }}
                                      aria-label={`保留服务端修改块：${conflictDraftModifiedBlockByAddedStartIndex.get(index)?.label ?? line.content}`}
                                      className="rounded border border-rose-300/20 px-1.5 py-0.5 text-[10px] font-semibold text-rose-100 hover:bg-rose-300/10"
                                    >
                                      保留服务端
                                    </button>
                                  </>
                                )}
                                {conflictDraftAddedBlockByStartIndex.has(index) && (
                                  <>
                                    <button
                                      type="button"
                                      onClick={() => {
                                        const block = conflictDraftAddedBlockByStartIndex.get(index);
                                        if (block) acceptConflictDraftBlock(block.lines);
                                      }}
                                      aria-label={`采纳变更块：${conflictDraftAddedBlockByStartIndex.get(index)?.label ?? line.content}`}
                                      className="rounded border border-cyan-300/20 px-1.5 py-0.5 text-[10px] font-semibold text-cyan-100 hover:bg-cyan-300/10"
                                    >
                                      采纳块
                                    </button>
                                    <button
                                      type="button"
                                      onClick={() => {
                                        const block = conflictDraftAddedBlockByStartIndex.get(index);
                                        if (block) discardConflictDraftBlock(block.lines);
                                      }}
                                      aria-label={`丢弃变更块：${conflictDraftAddedBlockByStartIndex.get(index)?.label ?? line.content}`}
                                      className="rounded border border-amber-300/20 px-1.5 py-0.5 text-[10px] font-semibold text-amber-100 hover:bg-amber-300/10"
                                    >
                                      丢弃块
                                    </button>
                                  </>
                                )}
                                <button
                                  type="button"
                                  onClick={() => acceptConflictDraftLine(line.content)}
                                  aria-label={`采纳到草稿：${line.content}`}
                                  className="rounded border border-emerald-300/20 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-100 hover:bg-emerald-300/10"
                                >
                                  采纳
                                </button>
                                <button
                                  type="button"
                                  onClick={() => discardConflictDraftLine(line.content)}
                                  aria-label={`丢弃此行：${line.content}`}
                                  className="rounded border border-slate-300/20 px-1.5 py-0.5 text-[10px] font-semibold text-slate-200 hover:bg-white/10"
                                >
                                  丢弃
                                </button>
                              </span>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
              <textarea
                aria-label="编辑产出物 Markdown"
                value={editDraft}
                onChange={(event) => setEditDraft(event.target.value)}
                disabled={isSavingManualEdit}
                className="min-h-[58vh] w-full resize-none bg-[#0B1120] p-5 font-mono text-sm leading-relaxed text-slate-200 outline-none placeholder:text-slate-600"
                spellCheck={false}
              />
            </div>
          ) : viewMode === 'preview' ? (
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              rehypePlugins={[rehypeRaw]}
              components={editableMarkdownComponents}
            >
              {displayContent}
            </ReactMarkdown>
          ) : (
            <pre className="text-sm font-mono text-slate-300 whitespace-pre-wrap break-words bg-[#0f172a] p-6 rounded-xl border border-[#1e293b]">
              {displayContent}
            </pre>
          )}
        </div>
      </div>

      {showComments && (
        <aside className="absolute right-6 top-20 z-20 w-[min(360px,calc(100%-3rem))] rounded-xl border border-[#1e293b] bg-[#0f172a] shadow-2xl">
          <div className="flex items-center justify-between border-b border-[#1e293b] px-4 py-3">
            <div>
              <h3 className="text-sm font-semibold text-white">产出物批注</h3>
              <p className="text-xs text-slate-500">当前阶段 {currentStageId}</p>
            </div>
            <button
              onClick={() => setShowComments(false)}
              className="rounded p-1 text-slate-400 hover:bg-white/10 hover:text-white"
              title="关闭批注"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
          <div className="space-y-3 p-4">
            <label className="block text-xs font-semibold text-slate-300" htmlFor="artifact-comment-draft">
              新增批注
            </label>
            <textarea
              id="artifact-comment-draft"
              aria-label="新增批注"
              value={commentDraft}
              onChange={(event) => setCommentDraft(event.target.value)}
              className="min-h-24 w-full resize-y rounded-lg border border-[#334155] bg-[#020617] p-3 text-sm leading-relaxed text-slate-200 outline-none focus:border-blue-500"
              placeholder="记录需要确认、后续跟进或人工校准的点..."
            />
            <button
              onClick={addCurrentStageComment}
              disabled={!commentDraft.trim()}
              className="rounded-lg bg-blue-600 px-3 py-2 text-xs font-semibold text-white transition-colors hover:bg-blue-500 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
            >
              添加批注
            </button>

            <div className="border-t border-[#1e293b] pt-3">
              {currentStageComments.length === 0 ? (
                <p className="text-sm text-slate-500">当前阶段还没有批注。</p>
              ) : (
                <div className="space-y-3">
                  {currentStageComments.map((comment) => (
                    <article key={comment.id} className="rounded-lg border border-[#1e293b] bg-[#020617] p-3">
                      <div className="mb-2 flex items-start justify-between gap-3">
                        <div className="min-w-0 flex-1">
                          <div className="mb-2 flex flex-wrap items-center gap-2">
                            <span className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold ${comment.status === 'resolved'
                              ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300'
                              : 'border-amber-500/30 bg-amber-500/10 text-amber-300'
                              }`}
                            >
                              {comment.status === 'resolved' ? '已解决' : '未解决'}
                            </span>
                            <button
                              type="button"
                              onClick={() => toggleCurrentStageCommentStatus(comment.id, comment.status)}
                              className="rounded border border-[#334155] px-2 py-1 text-[10px] font-semibold text-slate-300 transition-colors hover:border-blue-500/60 hover:text-blue-200"
                            >
                              {comment.status === 'resolved' ? '重新打开' : '标记已解决'}
                            </button>
                          </div>
                          <p className="break-words text-sm leading-relaxed text-slate-200">{comment.content}</p>
                        </div>
                        <button
                          onClick={() => removeCurrentStageComment(comment.id)}
                          className="rounded p-1 text-slate-500 hover:bg-red-500/10 hover:text-red-300"
                          title="删除批注"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                      <blockquote className="border-l-2 border-blue-500/50 pl-3 text-xs leading-relaxed text-slate-500">
                        {comment.artifactExcerpt || '当前产出物'}
                      </blockquote>
                      {comment.anchorText && (
                        <button
                          type="button"
                          onClick={() => locateArtifactCommentAnchor(comment.anchorText ?? '')}
                          className="mt-2 rounded border border-blue-500/30 px-2 py-1 text-[10px] font-semibold text-blue-200 transition-colors hover:bg-blue-500/10"
                        >
                          定位正文
                        </button>
                      )}
                      {comment.replies.length > 0 && (
                        <div className="mt-3 space-y-2 border-t border-[#1e293b] pt-3">
                          {comment.replies.map((reply) => (
                            <div key={reply.id} className="rounded-md bg-white/[0.03] px-3 py-2">
                              <p className="break-words text-xs leading-relaxed text-slate-300">{reply.content}</p>
                              <p className="mt-1 text-[10px] text-slate-600">
                                {new Date(reply.createdAt).toLocaleString()}
                              </p>
                            </div>
                          ))}
                        </div>
                      )}
                      <div className="mt-3 flex items-start gap-2">
                        <label className="sr-only" htmlFor={`artifact-comment-reply-${comment.id}`}>
                          回复批注：{comment.content}
                        </label>
                        <textarea
                          id={`artifact-comment-reply-${comment.id}`}
                          aria-label={`回复批注：${comment.content}`}
                          value={commentReplyDrafts[comment.id] ?? ''}
                          onChange={(event) => setCommentReplyDrafts((drafts) => ({
                            ...drafts,
                            [comment.id]: event.target.value,
                          }))}
                          className="min-h-16 flex-1 resize-y rounded-lg border border-[#1e293b] bg-[#0f172a] p-2 text-xs leading-relaxed text-slate-200 outline-none focus:border-blue-500"
                          placeholder="补充处理结论..."
                        />
                        <button
                          type="button"
                          onClick={() => addCurrentStageCommentReply(comment.id)}
                          disabled={!commentReplyDrafts[comment.id]?.trim()}
                          className="rounded-lg bg-slate-700 px-3 py-2 text-xs font-semibold text-white transition-colors hover:bg-slate-600 disabled:cursor-not-allowed disabled:bg-slate-800 disabled:text-slate-500"
                        >
                          添加回复
                        </button>
                      </div>
                      <p className="mt-2 text-[10px] text-slate-600">
                        {new Date(comment.createdAt).toLocaleString()}
                      </p>
                    </article>
                  ))}
                </div>
              )}
            </div>
            {collaborationSyncError && (
              <p className="px-4 pb-3 text-xs text-red-300">{collaborationSyncError}</p>
            )}
          </div>
        </aside>
      )}

      {showSectionLocks && (
        <aside className="absolute right-6 top-20 z-20 w-[min(380px,calc(100%-3rem))] rounded-xl border border-[#1e293b] bg-[#0f172a] shadow-2xl">
          <div className="flex items-center justify-between border-b border-[#1e293b] px-4 py-3">
            <div>
              <h3 className="text-sm font-semibold text-white">章节锁定</h3>
              <p className="text-xs text-slate-500">保护已确认章节不被手工误改</p>
            </div>
            <button
              onClick={() => setShowSectionLocks(false)}
              className="rounded p-1 text-slate-400 hover:bg-white/10 hover:text-white"
              title="关闭章节锁定"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
          <div className="max-h-[60vh] space-y-3 overflow-auto p-4">
            {artifactSections.length === 0 ? (
              <p className="text-sm text-slate-500">当前产出物还没有可锁定的 Markdown 标题章节。</p>
            ) : (
              artifactSections.map((section) => {
                const lock = getSectionLock(section.heading);
                return (
                  <article key={section.heading} className="rounded-lg border border-[#1e293b] bg-[#020617] p-3">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <h4 className="truncate text-sm font-semibold text-slate-100">{section.title}</h4>
                        <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-slate-500">
                          {section.content.replace(section.heading, '').trim() || '空章节'}
                        </p>
                      </div>
                      {lock ? (
                        <button
                          onClick={() => unlockSection(lock.id)}
                          className="inline-flex shrink-0 items-center gap-1 rounded-md border border-amber-400/20 px-2 py-1 text-xs font-semibold text-amber-200 hover:bg-amber-400/10"
                          aria-label={`解除章节锁定 ${section.title}`}
                          title="解除章节锁定"
                        >
                          <Unlock className="h-3.5 w-3.5" />
                          解锁
                        </button>
                      ) : (
                        <button
                          onClick={() => lockSection(section)}
                          className="inline-flex shrink-0 items-center gap-1 rounded-md bg-blue-600 px-2 py-1 text-xs font-semibold text-white hover:bg-blue-500"
                          aria-label={`锁定 ${section.title}`}
                        >
                          <Lock className="h-3.5 w-3.5" />
                          锁定 {section.title}
                        </button>
                      )}
                    </div>
                  </article>
                );
              })
            )}
            {collaborationSyncError && (
              <p className="text-xs text-red-300">{collaborationSyncError}</p>
            )}
          </div>
        </aside>
      )}

      {showHistory && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
          <div className="flex w-full max-w-6xl h-[85vh] overflow-hidden rounded-xl bg-[#0f172a] shadow-2xl ring-1 ring-white/10">
            {/* Sidebar */}
            <div className="w-64 bg-[#0B1120] border-r border-[#1e293b] flex flex-col shrink-0">
              <div className="p-4 border-b border-[#1e293b] flex justify-between items-center">
                <h3 className="text-white font-bold flex items-center gap-2">
                  <History className="w-4 h-4 text-blue-400" />
                  历史版本
                </h3>
                <button onClick={() => setShowHistory(false)} className="text-slate-400 hover:text-white">
                  <X className="w-4 h-4" />
                </button>
              </div>
              <div className="flex-1 overflow-y-auto p-3 space-y-2 custom-scrollbar">
                {currentStageArtifactHistory.length === 0 ? (
                  <div className="text-slate-500 text-sm text-center mt-10">暂无历史版本</div>
                ) : (
                  [...currentStageArtifactHistory].reverse().map((v, i) => {
                    const titleMatch = v.content.match(/^#\s+(.+)$/m);
                    const title = titleMatch ? titleMatch[1].trim() : '未命名文档';
                    return (
                      <button
                        key={v.id}
                        onClick={() => setSelectedVersion(v)}
                        className={`w-full text-left px-3 py-2.5 rounded-lg text-sm transition-all ${selectedVersion?.id === v.id ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30 shadow-inner' : 'text-slate-300 hover:bg-white/5 border border-transparent'}`}
                      >
                        <div className="font-medium truncate" title={title}>{title}</div>
                        <div className="flex justify-between items-center mt-1.5">
                          <span className={`text-[10px] px-1.5 py-0.5 rounded font-mono ${selectedVersion?.id === v.id ? 'bg-blue-500/20 text-blue-300' : 'bg-white/10 text-slate-400'}`}>v{currentStageArtifactHistory.length - i}</span>
                          <span className="text-[10px] opacity-60 font-mono">{new Date(v.timestamp).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</span>
                        </div>
                      </button>
                    );
                  })
                )}
                <div className="mt-4 border-t border-[#1e293b] pt-4">
                  <div className="mb-2 text-[11px] font-bold uppercase tracking-wide text-slate-500">
                    活动轨迹
                  </div>
                  {currentStageAuditEvents.length === 0 ? (
                    <p className="text-xs text-slate-600">暂无活动记录</p>
                  ) : (
                    <div className="space-y-2">
                      {[...currentStageAuditEvents].reverse().map((event, index) => (
                        <div
                          key={`${event.eventType}-${event.createdAt}-${index}`}
                          className="rounded-lg border border-[#1e293b] bg-[#0f172a] px-3 py-2"
                        >
                          <p className="text-xs leading-relaxed text-slate-300">{event.summary}</p>
                          <p className="mt-1 text-[10px] text-slate-600">
                            {new Date(event.createdAt).toLocaleString()}
                          </p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Main content */}
            <div className="flex-1 flex flex-col bg-[#0B0F17] overflow-hidden relative">
              <div className="px-6 py-3 border-b border-[#1e293b] bg-[#0d1117]/80 backdrop-blur flex items-center justify-between shadow-sm">
                <h2 className="text-gray-200 font-semibold text-sm tracking-tight flex items-center gap-2">
                  {historyViewMode === 'preview' ? (
                    <Eye className="w-4 h-4 text-slate-400" />
                  ) : (
                    <GitCompare className="w-4 h-4 text-slate-400" />
                  )}
                  {historyViewMode === 'preview' ? '版本预览' : '与当前产出物对比'} <span className="text-slate-500 font-normal">（只读）</span>
                </h2>
                <div className="flex items-center gap-1 rounded-lg border border-[#1e293b] bg-[#0f172a] p-1">
                  {selectedVersion && (
                    <>
                      <button
                        onClick={handleRestoreSelectedVersion}
                        className="rounded px-3 py-1.5 text-xs font-semibold text-emerald-200 transition-colors hover:bg-emerald-500/10"
                      >
                        恢复此版本
                      </button>
                      <div className="mx-1 h-4 w-px bg-[#1e293b]"></div>
                    </>
                  )}
                  <button
                    onClick={() => setHistoryViewMode('preview')}
                    className={`rounded px-3 py-1.5 text-xs font-semibold transition-colors ${historyViewMode === 'preview' ? 'bg-white/10 text-white' : 'text-slate-400 hover:bg-white/5 hover:text-white'}`}
                  >
                    预览
                  </button>
                  <button
                    onClick={() => setHistoryViewMode('diff')}
                    className={`rounded px-3 py-1.5 text-xs font-semibold transition-colors ${historyViewMode === 'diff' ? 'bg-white/10 text-white' : 'text-slate-400 hover:bg-white/5 hover:text-white'}`}
                  >
                    差异
                  </button>
                </div>
              </div>
              <div className="flex-1 overflow-y-auto p-8 md:px-16 custom-scrollbar">
                <div className="max-w-4xl mx-auto pb-20">
                  {selectedVersion && historyViewMode === 'preview' ? (
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      rehypePlugins={[rehypeRaw]}
                      components={readOnlyMarkdownComponents}
                    >
                      {preprocessMarkdown(selectedVersion.content)}
                    </ReactMarkdown>
                  ) : selectedVersion ? (
                    <div className="overflow-hidden rounded-lg border border-[#1e293b] bg-[#0f172a] font-mono text-xs">
                      {selectedVersionDiff.map((entry, index) => {
                        const prefix = entry.type === 'added' ? '+ ' : entry.type === 'removed' ? '- ' : '  ';
                        return (
                          <div
                            key={`${entry.type}-${index}`}
                            className={`flex items-center gap-2 whitespace-pre-wrap px-4 py-1.5 ${entry.type === 'added' ? 'bg-emerald-500/10 text-emerald-200' : entry.type === 'removed' ? 'bg-red-500/10 text-red-200' : 'text-slate-400'}`}
                          >
                            <span className="min-w-0 flex-1">{prefix}{entry.content}</span>
                            {entry.type === 'removed' && entry.content.trim() && (
                              <button
                                type="button"
                                onClick={() => restoreHistoryLine(entry.content)}
                                aria-label={`恢复此行：${entry.content}`}
                                className="shrink-0 rounded border border-red-300/20 px-1.5 py-0.5 text-[10px] font-semibold text-red-100 hover:bg-red-300/10"
                              >
                                恢复此行
                              </button>
                            )}
                            {entry.type === 'added' && entry.content.trim() && (
                              <button
                                type="button"
                                onClick={() => discardCurrentLine(entry.content)}
                                aria-label={`丢弃当前行：${entry.content}`}
                                className="shrink-0 rounded border border-emerald-300/20 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-100 hover:bg-emerald-300/10"
                              >
                                丢弃当前行
                              </button>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <div className="flex items-center justify-center h-full text-slate-500">
                      请在左侧选择一个历史版本查看
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </section>
  );
};
