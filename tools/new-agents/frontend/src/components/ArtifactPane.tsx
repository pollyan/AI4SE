import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import type { Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import { useStore, ArtifactVersion, WORKFLOWS } from '../store';
import type {
  AgentRunSnapshotArtifact,
  ArtifactVisualDiagnostic,
  ArtifactVisualDiagnosticFocusRequest,
  StoryHandoffCandidate,
  StoryHandoffPacket,
  StoryHandoffPacketListItem,
} from '../core/types';
import { buildLineDiff } from '../core/artifactDiff';
import {
  parseArtifactMarkdownSections,
  type ArtifactMarkdownSection,
} from '../core/artifactSections';
import {
  buildAutoMergedInsertionResult,
  buildConflictMergeBlockLabel,
  buildConflictModificationBlockLabel,
  buildContiguousDiffBlocks,
  replaceFirstLineSequence,
  truncateAuditLine,
} from '../core/artifactMerge';
import type { AutoMergedConflictResult } from '../core/artifactMerge';
import { preprocessMarkdown, replaceMermaidBlockAtIndex } from '../core/utils/markdownUtils';
import { Download, Code, Eye, History, X, AlertTriangle, GitCompare, Edit3, Save, MessageSquare, Trash2, Lock, Unlock, MoreHorizontal, RefreshCw } from 'lucide-react';
import { createMarkdownCodeRenderer } from './markdownCodeRenderer';
import { StructuredVisual } from './StructuredVisual';
import { ArtifactConflictError, updateRunArtifact, updateRunArtifactCollaboration } from '../services/runSnapshotService';
import { useChatService } from '../services/chatService';
import {
  createStoryHandoffPacket,
  fetchStoryHandoffCandidates,
  fetchStoryHandoffPackets,
} from '../services/storyHandoffPacketService';
import { buildDocxPackage } from '../core/docxExport';
import { buildPlainTextPdf as buildArtifactPdf } from '../core/artifactExport';
import { buildArtifactQualitySummary } from '../core/artifactQuality';
import { buildWorkflowQualitySummary } from '../core/workflowQuality';

type MarkdownPreviewChunk = {
  sectionKey: string;
  content: string;
  mermaidBlockStartIndex: number;
  structuredVisualBlockStartIndex: number;
};

type RenderedMarkdownSectionProps = MarkdownPreviewChunk & {
  components: Components;
  renderVersionKey: string;
};

const countFencedBlocksByLanguage = (
  content: string,
  language: 'mermaid' | 'ai4se-visual'
): number => {
  const fencePattern = /^```\s*([^\s`]+)/gm;
  let count = 0;
  let match: RegExpExecArray | null;
  while ((match = fencePattern.exec(content)) !== null) {
    if (match[1] === language) {
      count += 1;
    }
  }
  return count;
};

const buildMarkdownPreviewChunks = (content: string): MarkdownPreviewChunk[] => {
  const parsedSections = parseArtifactMarkdownSections(content);
  const baseChunks = parsedSections.length > 0
    ? parsedSections.map(section => ({
      sectionKey: section.anchor,
      content: section.content,
    }))
    : [{
      sectionKey: 'full-document',
      content,
    }];

  let mermaidBlockStartIndex = 0;
  let structuredVisualBlockStartIndex = 0;
  return baseChunks
    .filter(chunk => chunk.content.trim().length > 0)
    .map((chunk) => {
      const result = {
        ...chunk,
        mermaidBlockStartIndex,
        structuredVisualBlockStartIndex,
      };
      mermaidBlockStartIndex += countFencedBlocksByLanguage(chunk.content, 'mermaid');
      structuredVisualBlockStartIndex += countFencedBlocksByLanguage(
        chunk.content,
        'ai4se-visual'
      );
      return result;
    });
};

const RenderedMarkdownSection = React.memo(({
  content,
  components,
}: RenderedMarkdownSectionProps) => (
  <ReactMarkdown
    remarkPlugins={[remarkGfm]}
    rehypePlugins={[rehypeRaw]}
    components={components}
  >
    {content}
  </ReactMarkdown>
), (previous, next) => (
  previous.content === next.content
  && previous.mermaidBlockStartIndex === next.mermaidBlockStartIndex
  && previous.structuredVisualBlockStartIndex === next.structuredVisualBlockStartIndex
  && previous.renderVersionKey === next.renderVersionKey
));

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
  const updateArtifactCommentAnchor = useStore((state) => state.updateArtifactCommentAnchor);
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
  const focusArtifactVisualDiagnostic = useStore((state) => state.focusArtifactVisualDiagnostic);
  const { handleRegenerateArtifactSection } = useChatService();
  const [viewMode, setViewMode] = useState<'preview' | 'code'>('preview');
  const [showHistory, setShowHistory] = useState(false);
  const [showArtifactActionsMenu, setShowArtifactActionsMenu] = useState(false);
  const [showReviewPanel, setShowReviewPanel] = useState(false);
  const [showComments, setShowComments] = useState(false);
  const [showSectionLocks, setShowSectionLocks] = useState(false);
  const [commentDraft, setCommentDraft] = useState('');
  const [commentReplyDrafts, setCommentReplyDrafts] = useState<Record<string, string>>({});
  const [commentAnchorRebindErrors, setCommentAnchorRebindErrors] = useState<Record<string, string>>({});
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
  const [storyHandoffCandidates, setStoryHandoffCandidates] = useState<StoryHandoffCandidate[]>([]);
  const [storyHandoffPackets, setStoryHandoffPackets] = useState<StoryHandoffPacketListItem[]>([]);
  const [isLoadingStoryHandoff, setIsLoadingStoryHandoff] = useState(false);
  const [storyHandoffError, setStoryHandoffError] = useState<string | null>(null);
  const [creatingStoryPacketId, setCreatingStoryPacketId] = useState<string | null>(null);
  const [copiedStoryPacketId, setCopiedStoryPacketId] = useState<string | null>(null);
  const artifactPreviewRef = useRef<HTMLDivElement | null>(null);
  const handledVisualDiagnosticFocusSeqRef = useRef<number | null>(null);
  const currentStage = WORKFLOWS[workflow].stages[stageIndex];
  const currentStageId = currentStage?.id;
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
  const currentStageOpenComments = useMemo(
    () => currentStageComments.filter(comment => comment.status !== 'resolved'),
    [currentStageComments]
  );
  const recentStageAuditEvents = useMemo(
    () => [...currentStageAuditEvents]
      .sort((left, right) => right.createdAt - left.createdAt)
      .slice(0, 5),
    [currentStageAuditEvents]
  );
  const latestStageArtifactVersion = currentStageArtifactHistory[currentStageArtifactHistory.length - 1] ?? null;
  const currentStageVisualDiagnostics = useMemo(
    () => currentStageId
      ? artifactVisualDiagnostics.filter(diagnostic => diagnostic.stageId === currentStageId)
      : [],
    [artifactVisualDiagnostics, currentStageId]
  );
  const artifactQualitySummary = useMemo(
    () => buildArtifactQualitySummary({
      stage: currentStage,
      content: artifactContent,
      visualDiagnostics: currentStageVisualDiagnostics,
    }),
    [artifactContent, currentStage, currentStageVisualDiagnostics]
  );
  const workflowQualitySummary = useMemo(
    () => buildWorkflowQualitySummary({
      workflow: WORKFLOWS[workflow],
      stageId: currentStageId,
      artifactMarkdown: artifactContent,
      visualDiagnostics: artifactVisualDiagnostics,
    }),
    [artifactContent, artifactVisualDiagnostics, currentStageId, workflow]
  );
  const isStoryHandoffPacketStage = (
    workflow === 'STORY_BREAKDOWN'
    && currentStageId === 'SPRINT_PLAN'
    && currentRunId !== null
  );
  const storyHandoffPacketByStoryId = useMemo(
    () => new Map(storyHandoffPackets.map(packet => [packet.storyId, packet])),
    [storyHandoffPackets]
  );

  useEffect(() => {
    let cancelled = false;
    if (!isStoryHandoffPacketStage || !currentRunId || !currentStageId) {
      setStoryHandoffCandidates([]);
      setStoryHandoffPackets([]);
      setStoryHandoffError(null);
      setIsLoadingStoryHandoff(false);
      return undefined;
    }

    setIsLoadingStoryHandoff(true);
    setStoryHandoffError(null);
    Promise.all([
      fetchStoryHandoffCandidates(currentRunId, currentStageId),
      fetchStoryHandoffPackets(currentRunId, currentStageId),
    ])
      .then(([candidateResponse, packetResponse]) => {
        if (cancelled) return;
        setStoryHandoffCandidates(candidateResponse.candidates);
        setStoryHandoffPackets(packetResponse.packets);
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        const message = error instanceof Error ? error.message : '未知错误';
        setStoryHandoffCandidates([]);
        setStoryHandoffPackets([]);
        setStoryHandoffError(`单故事需求包加载失败：${message}`);
      })
      .finally(() => {
        if (!cancelled) setIsLoadingStoryHandoff(false);
      });

    return () => {
      cancelled = true;
    };
  }, [currentRunId, currentStageId, isStoryHandoffPacketStage]);

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
  type ArtifactSection = ArtifactMarkdownSection;

  const stripInlineMarkdown = (content: string): string => (
    content
      .replace(/`([^`]+)`/g, '$1')
      .replace(/\*\*([^*]+)\*\*/g, '$1')
      .replace(/\*([^*]+)\*/g, '$1')
      .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
      .trim()
  );

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

  const displayContent = preprocessMarkdown(artifactContent);
  const artifactSections = useMemo(
    () => parseArtifactMarkdownSections(artifactContent),
    [artifactContent]
  );
  const markdownPreviewChunks = useMemo(
    () => buildMarkdownPreviewChunks(displayContent),
    [displayContent]
  );

  const findLockedSectionChange = (nextContent: string): string | null => {
    if (currentStageSectionLocks.length === 0) return null;
    const nextSections = parseArtifactMarkdownSections(nextContent);
    for (const lock of currentStageSectionLocks) {
      const currentSection = artifactSections.find(section => (
        lock.sectionAnchor
          ? section.anchor === lock.sectionAnchor
          : section.heading === lock.heading
      ));
      const nextSection = nextSections.find(section => (
        lock.sectionAnchor
          ? section.anchor === lock.sectionAnchor
          : section.heading === lock.heading
      ));
      if (!nextSection || nextSection.content.trim() !== lock.content.trim()) {
        return currentSection?.displayTitle ?? lock.heading.replace(/^#{1,3}\s+/, '');
      }
    }
    return null;
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
    setShowArtifactActionsMenu(false);
    if (format === 'word') {
      downloadBlob(
        buildDocxPackage(artifactContent),
        `${workflow.toLowerCase()}_artifact.docx`
      );
      return;
    }
    if (format === 'pdf') {
      downloadBlob(
        new Blob([buildArtifactPdf(artifactContent)], { type: 'application/pdf' }),
        `${workflow.toLowerCase()}_artifact.pdf`
      );
      return;
    }

    downloadBlob(
      new Blob([artifactContent], { type: 'text/markdown' }),
      `${workflow.toLowerCase()}_artifact.md`
    );
  };

  const refreshStoryHandoffPackets = async () => {
    if (!currentRunId || !currentStageId) return;
    const packetResponse = await fetchStoryHandoffPackets(currentRunId, currentStageId);
    setStoryHandoffPackets(packetResponse.packets);
  };

  const handleCreateStoryHandoffPacket = async (storyId: string) => {
    if (!currentRunId || !currentStageId) return;
    setCreatingStoryPacketId(storyId);
    setStoryHandoffError(null);
    try {
      await createStoryHandoffPacket(currentRunId, currentStageId, storyId);
      await refreshStoryHandoffPackets();
    } catch (error) {
      const message = error instanceof Error ? error.message : '未知错误';
      setStoryHandoffError(`单故事需求包生成失败：${message}`);
    } finally {
      setCreatingStoryPacketId(null);
    }
  };

  const handleCopyStoryHandoffPacket = async (
    storyId: string,
    packet: StoryHandoffPacket,
  ) => {
    setStoryHandoffError(null);
    if (!navigator.clipboard?.writeText) {
      setStoryHandoffError('当前浏览器不支持复制单故事需求包。');
      return;
    }
    try {
      await navigator.clipboard.writeText(JSON.stringify(packet, null, 2));
      setCopiedStoryPacketId(storyId);
    } catch (error) {
      const message = error instanceof Error ? error.message : '未知错误';
      setStoryHandoffError(`单故事需求包复制失败：${message}`);
    }
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
  type ParsedMarkdownSection = {
    heading: string;
    lines: string[];
  };
  type ParsedMarkdownSections = {
    preambleLines: string[];
    sections: ParsedMarkdownSection[];
  };
  const parseMarkdownSectionsForAutoMerge = (content: string): ParsedMarkdownSections | null => {
    const lines = content.replace(/\r\n/g, '\n').split('\n');
    const headingIndexes: number[] = [];
    lines.forEach((line, index) => {
      if (/^#{1,6}\s+\S/.test(line)) {
        headingIndexes.push(index);
      }
    });

    if (headingIndexes.length === 0) return null;

    const headings = headingIndexes.map(index => lines[index].trim());
    if (new Set(headings).size !== headings.length) return null;

    const sections = headingIndexes.map((headingIndex, index) => {
      const nextHeadingIndex = headingIndexes[index + 1] ?? lines.length;
      return {
        heading: lines[headingIndex].trim(),
        lines: lines.slice(headingIndex, nextHeadingIndex),
      };
    });

    return {
      preambleLines: lines.slice(0, headingIndexes[0]),
      sections,
    };
  };
  const hasSameSectionShape = (
    baseSections: ParsedMarkdownSections,
    targetSections: ParsedMarkdownSections
  ): boolean => (
    baseSections.preambleLines.join('\n') === targetSections.preambleLines.join('\n')
    && baseSections.sections.length === targetSections.sections.length
    && baseSections.sections.every((section, index) => (
      section.heading === targetSections.sections[index]?.heading
    ))
  );
  const areLineGroupsEqual = (leftLines: string[], rightLines: string[]): boolean => (
    leftLines.join('\n') === rightLines.join('\n')
  );
  const getSectionOrder = (sections: ParsedMarkdownSections): string[] => (
    sections.sections.map(section => section.heading)
  );
  const haveSameSectionSet = (
    baseSections: ParsedMarkdownSections,
    targetSections: ParsedMarkdownSections
  ): boolean => {
    if (baseSections.sections.length !== targetSections.sections.length) return false;
    const targetHeadings = new Set(getSectionOrder(targetSections));
    return baseSections.sections.every(section => targetHeadings.has(section.heading));
  };
  const areSectionOrdersEqual = (leftOrder: string[], rightOrder: string[]): boolean => (
    leftOrder.length === rightOrder.length
    && leftOrder.every((heading, index) => heading === rightOrder[index])
  );
  const buildSectionMap = (sections: ParsedMarkdownSections): Map<string, string[]> => (
    new Map(sections.sections.map(section => [section.heading, section.lines]))
  );
  const getSectionHeadingSet = (sections: ParsedMarkdownSections): Set<string> => (
    new Set(getSectionOrder(sections))
  );
  type ParsedParagraphBlock = {
    baseIndex: number;
    lines: string[];
    key: string;
  };
  type ParagraphMoveChange = {
    heading: string;
    movedBaseIndex: number;
    targetOrder: number[];
  };
  type CrossSectionParagraphMoveChange = {
    movedKey: string;
    sourceHeading: string;
    targetHeading: string;
    sectionOrders: Map<string, string[]>;
  };
  type TableRowReorderChange = {
    heading: string;
    targetLines: string[];
  };
  type ListItemReorderChange = {
    heading: string;
    targetLines: string[];
  };
  type FencedBlockLineReorderChange = {
    heading: string;
    targetLines: string[];
  };
  type SectionMovementUnit = {
    heading: string;
    key: string;
    unsafe: boolean;
  };
  const isUnsafeParagraphMoveBlock = (lines: string[]): boolean => (
    lines.some(line => (
      /^```/.test(line.trim())
      || /^[-*+]\s+/.test(line.trim())
      || /^\d+\.\s+/.test(line.trim())
      || /^\|.*\|$/.test(line.trim())
    ))
  );
  const collectSectionMovementUnits = (heading: string, sectionLines: string[]): SectionMovementUnit[] => {
    const units: SectionMovementUnit[] = [];
    let normalBlockLines: string[] = [];

    const flushNormalBlock = () => {
      if (normalBlockLines.length === 0) return;
      units.push({
        heading,
        key: normalBlockLines.join('\n'),
        unsafe: false,
      });
      normalBlockLines = [];
    };

    for (let index = 1; index < sectionLines.length; index += 1) {
      const line = sectionLines[index];
      const trimmedLine = line.trim();
      if (!trimmedLine) {
        flushNormalBlock();
        continue;
      }

      if (/^```/.test(trimmedLine)) {
        flushNormalBlock();
        const fenceLines = [line];
        index += 1;
        while (index < sectionLines.length) {
          fenceLines.push(sectionLines[index]);
          if (/^```/.test(sectionLines[index].trim())) break;
          index += 1;
        }
        units.push({
          heading,
          key: fenceLines.join('\n'),
          unsafe: true,
        });
        continue;
      }

      if (isUnsafeParagraphMoveBlock([line])) {
        flushNormalBlock();
        units.push({
          heading,
          key: line,
          unsafe: true,
        });
        continue;
      }

      normalBlockLines.push(line);
    }

    flushNormalBlock();
    return units;
  };
  const countUnitKeys = (units: SectionMovementUnit[]): Map<string, number> => (
    units.reduce((counts, unit) => {
      counts.set(unit.key, (counts.get(unit.key) ?? 0) + 1);
      return counts;
    }, new Map<string, number>())
  );
  const hasUnsafeUnitReorder = (
    baseSectionLines: string[],
    targetSectionLines: string[],
    heading: string
  ): boolean => {
    const baseUnits = collectSectionMovementUnits(heading, baseSectionLines);
    const targetUnits = collectSectionMovementUnits(heading, targetSectionLines);
    const baseCounts = countUnitKeys(baseUnits);
    const targetCounts = countUnitKeys(targetUnits);
    const comparableKeys = new Set(
      baseUnits
        .map(unit => unit.key)
        .filter(key => baseCounts.get(key) === 1 && targetCounts.get(key) === 1)
    );
    if (comparableKeys.size < 2) return false;

    const baseOrder = baseUnits.filter(unit => comparableKeys.has(unit.key)).map(unit => unit.key);
    const targetOrder = targetUnits.filter(unit => comparableKeys.has(unit.key)).map(unit => unit.key);
    if (areSectionOrdersEqual(baseOrder, targetOrder)) return false;

    const baseUnitByKey = new Map(baseUnits.map(unit => [unit.key, unit]));
    return Array.from(comparableKeys).some((key) => {
      const unit = baseUnitByKey.get(key);
      return Boolean(unit?.unsafe) && baseOrder.indexOf(key) !== targetOrder.indexOf(key);
    });
  };
  const hasSafeParagraphOrderChange = (
    baseSectionLines: string[],
    targetSectionLines: string[]
  ): boolean => {
    const baseBlocks = parseSafeSectionParagraphBlocks(baseSectionLines);
    const targetBlocks = parseSafeSectionParagraphBlocks(targetSectionLines);
    if (!baseBlocks || !targetBlocks) return false;
    const baseCounts = countParagraphBlockKeys(baseBlocks.map(block => ({ ...block, heading: '' })));
    const targetCounts = countParagraphBlockKeys(targetBlocks.map(block => ({ ...block, heading: '' })));
    const comparableKeys = new Set(
      baseBlocks
        .map(block => block.key)
        .filter(key => baseCounts.get(key) === 1 && targetCounts.get(key) === 1)
    );
    if (comparableKeys.size < 2) return false;
    const baseOrder = baseBlocks.filter(block => comparableKeys.has(block.key)).map(block => block.key);
    const targetOrder = targetBlocks.filter(block => comparableKeys.has(block.key)).map(block => block.key);
    return !areSectionOrdersEqual(baseOrder, targetOrder);
  };
  const hasSectionMovementForAutoMerge = (
    baseSectionLines: string[],
    targetSectionLines: string[],
    heading: string
  ): boolean => (
    hasUnsafeUnitReorder(baseSectionLines, targetSectionLines, heading)
    || hasSafeParagraphOrderChange(baseSectionLines, targetSectionLines)
  );
  const isMarkdownTableLine = (line: string): boolean => /^\|.*\|$/.test(line.trim());
  const isMarkdownTableSeparatorLine = (line: string): boolean => {
    const trimmedLine = line.trim();
    return (
      isMarkdownTableLine(trimmedLine)
      && trimmedLine.includes('---')
      && /^[\s|:-]+$/.test(trimmedLine)
    );
  };
  const hasMarkdownTableLineChangeInSection = (
    baseSectionLines: string[],
    targetSectionLines: string[]
  ): boolean => {
    if (areLineGroupsEqual(baseSectionLines, targetSectionLines)) return false;
    return (
      baseSectionLines.some(isMarkdownTableLine)
      || targetSectionLines.some(isMarkdownTableLine)
    );
  };
  const isMarkdownListItemLine = (line: string): boolean => /^[-*+]\s+/.test(line.trim()) || /^\d+\.\s+/.test(line.trim());
  const isTopLevelMarkdownListItemLine = (line: string): boolean => /^[-*+]\s+/.test(line) || /^\d+\.\s+/.test(line);
  const hasMarkdownListItemLineChangeInSection = (
    baseSectionLines: string[],
    targetSectionLines: string[]
  ): boolean => {
    if (areLineGroupsEqual(baseSectionLines, targetSectionLines)) return false;
    return (
      baseSectionLines.some(isMarkdownListItemLine)
      || targetSectionLines.some(isMarkdownListItemLine)
    );
  };
  const isFencedBlockBoundaryLine = (line: string): boolean => /^```/.test(line.trim());
  const hasFencedBlockLineChangeInSection = (
    baseSectionLines: string[],
    targetSectionLines: string[]
  ): boolean => {
    if (areLineGroupsEqual(baseSectionLines, targetSectionLines)) return false;
    return (
      baseSectionLines.some(isFencedBlockBoundaryLine)
      || targetSectionLines.some(isFencedBlockBoundaryLine)
    );
  };
  const parseTableRowReorderSectionLines = (
    baseSectionLines: string[],
    targetSectionLines: string[]
  ): string[] | null => {
    if (baseSectionLines.length !== targetSectionLines.length) return null;

    const tableStarts = baseSectionLines.reduce<number[]>((starts, line, index) => {
      if (
        index > 0
        && index < baseSectionLines.length - 2
        && isMarkdownTableLine(line)
        && isMarkdownTableSeparatorLine(baseSectionLines[index + 1])
      ) {
        starts.push(index);
      }
      return starts;
    }, []);
    if (tableStarts.length !== 1) return null;

    const tableStart = tableStarts[0];
    let tableEndExclusive = tableStart + 2;
    while (
      tableEndExclusive < baseSectionLines.length
      && isMarkdownTableLine(baseSectionLines[tableEndExclusive])
    ) {
      tableEndExclusive += 1;
    }
    if (tableEndExclusive - tableStart < 4) return null;

    for (let index = 0; index < baseSectionLines.length; index += 1) {
      const isDataRow = index >= tableStart + 2 && index < tableEndExclusive;
      if (isDataRow) continue;
      if (baseSectionLines[index] !== targetSectionLines[index]) return null;
    }

    const baseRows = baseSectionLines.slice(tableStart + 2, tableEndExclusive);
    const targetRows = targetSectionLines.slice(tableStart + 2, tableEndExclusive);
    if (!targetRows.every(isMarkdownTableLine)) return null;
    if (new Set(baseRows).size !== baseRows.length || new Set(targetRows).size !== targetRows.length) {
      return null;
    }
    if (!areSectionOrdersEqual([...baseRows].sort(), [...targetRows].sort())) return null;
    if (areSectionOrdersEqual(baseRows, targetRows)) return null;

    return targetSectionLines;
  };
  const findTableRowReorderChange = (
    baseSections: ParsedMarkdownSections,
    targetSections: ParsedMarkdownSections
  ): TableRowReorderChange | null => {
    if (
      !areLineGroupsEqual(baseSections.preambleLines, targetSections.preambleLines)
      || !hasSameSectionShape(baseSections, targetSections)
    ) {
      return null;
    }

    let change: TableRowReorderChange | null = null;
    for (let index = 0; index < baseSections.sections.length; index += 1) {
      const baseSection = baseSections.sections[index];
      const targetSection = targetSections.sections[index];
      if (areLineGroupsEqual(baseSection.lines, targetSection.lines)) continue;
      const reorderedLines = parseTableRowReorderSectionLines(baseSection.lines, targetSection.lines);
      if (!reorderedLines) return null;
      if (change) return null;
      change = {
        heading: baseSection.heading,
        targetLines: reorderedLines,
      };
    }
    return change;
  };
  const parseListItemReorderSectionLines = (
    baseSectionLines: string[],
    targetSectionLines: string[]
  ): string[] | null => {
    if (baseSectionLines.length !== targetSectionLines.length) return null;
    if (
      baseSectionLines.some(line => /^```/.test(line.trim()))
      || targetSectionLines.some(line => /^```/.test(line.trim()))
    ) {
      return null;
    }

    const listBlocks: Array<{ start: number; endExclusive: number }> = [];
    let index = 1;
    while (index < baseSectionLines.length) {
      if (!isTopLevelMarkdownListItemLine(baseSectionLines[index])) {
        index += 1;
        continue;
      }
      const start = index;
      while (index < baseSectionLines.length && isTopLevelMarkdownListItemLine(baseSectionLines[index])) {
        index += 1;
      }
      listBlocks.push({ start, endExclusive: index });
    }
    if (listBlocks.length !== 1) return null;

    const listBlock = listBlocks[0];
    if (listBlock.endExclusive - listBlock.start < 2) return null;

    for (let lineIndex = 0; lineIndex < baseSectionLines.length; lineIndex += 1) {
      const isListLine = lineIndex >= listBlock.start && lineIndex < listBlock.endExclusive;
      if (isListLine) continue;
      if (baseSectionLines[lineIndex] !== targetSectionLines[lineIndex]) return null;
    }

    const baseItems = baseSectionLines.slice(listBlock.start, listBlock.endExclusive);
    const targetItems = targetSectionLines.slice(listBlock.start, listBlock.endExclusive);
    if (!targetItems.every(isTopLevelMarkdownListItemLine)) return null;
    if (new Set(baseItems).size !== baseItems.length || new Set(targetItems).size !== targetItems.length) {
      return null;
    }
    if (!areSectionOrdersEqual([...baseItems].sort(), [...targetItems].sort())) return null;
    if (areSectionOrdersEqual(baseItems, targetItems)) return null;

    return targetSectionLines;
  };
  const findListItemReorderChange = (
    baseSections: ParsedMarkdownSections,
    targetSections: ParsedMarkdownSections
  ): ListItemReorderChange | null => {
    if (
      !areLineGroupsEqual(baseSections.preambleLines, targetSections.preambleLines)
      || !hasSameSectionShape(baseSections, targetSections)
    ) {
      return null;
    }

    let change: ListItemReorderChange | null = null;
    for (let index = 0; index < baseSections.sections.length; index += 1) {
      const baseSection = baseSections.sections[index];
      const targetSection = targetSections.sections[index];
      if (areLineGroupsEqual(baseSection.lines, targetSection.lines)) continue;
      const reorderedLines = parseListItemReorderSectionLines(baseSection.lines, targetSection.lines);
      if (!reorderedLines) return null;
      if (change) return null;
      change = {
        heading: baseSection.heading,
        targetLines: reorderedLines,
      };
    }
    return change;
  };
  const parseFencedBlockLineReorderSectionLines = (
    baseSectionLines: string[],
    targetSectionLines: string[]
  ): string[] | null => {
    if (baseSectionLines.length !== targetSectionLines.length) return null;

    const fenceStarts: number[] = [];
    for (let index = 1; index < baseSectionLines.length; index += 1) {
      if (isFencedBlockBoundaryLine(baseSectionLines[index])) {
        fenceStarts.push(index);
        index += 1;
        while (index < baseSectionLines.length && !isFencedBlockBoundaryLine(baseSectionLines[index])) {
          index += 1;
        }
        if (index >= baseSectionLines.length) return null;
      }
    }
    if (fenceStarts.length !== 1) return null;

    const fenceStart = fenceStarts[0];
    let fenceEnd = fenceStart + 1;
    while (fenceEnd < baseSectionLines.length && !isFencedBlockBoundaryLine(baseSectionLines[fenceEnd])) {
      fenceEnd += 1;
    }
    if (fenceEnd >= baseSectionLines.length) return null;
    if (fenceEnd - fenceStart < 3) return null;

    if (
      baseSectionLines[fenceStart] !== targetSectionLines[fenceStart]
      || baseSectionLines[fenceEnd] !== targetSectionLines[fenceEnd]
    ) {
      return null;
    }

    for (let index = 0; index < baseSectionLines.length; index += 1) {
      const isFenceBodyLine = index > fenceStart && index < fenceEnd;
      if (isFenceBodyLine) continue;
      if (baseSectionLines[index] !== targetSectionLines[index]) return null;
    }

    const baseBodyLines = baseSectionLines.slice(fenceStart + 1, fenceEnd);
    const targetBodyLines = targetSectionLines.slice(fenceStart + 1, fenceEnd);
    if (
      baseBodyLines.some(isFencedBlockBoundaryLine)
      || targetBodyLines.some(isFencedBlockBoundaryLine)
    ) {
      return null;
    }
    if (new Set(baseBodyLines).size !== baseBodyLines.length || new Set(targetBodyLines).size !== targetBodyLines.length) {
      return null;
    }
    if (!areSectionOrdersEqual([...baseBodyLines].sort(), [...targetBodyLines].sort())) return null;
    if (areSectionOrdersEqual(baseBodyLines, targetBodyLines)) return null;

    return targetSectionLines;
  };
  const findFencedBlockLineReorderChange = (
    baseSections: ParsedMarkdownSections,
    targetSections: ParsedMarkdownSections
  ): FencedBlockLineReorderChange | null => {
    if (
      !areLineGroupsEqual(baseSections.preambleLines, targetSections.preambleLines)
      || !hasSameSectionShape(baseSections, targetSections)
    ) {
      return null;
    }

    let change: FencedBlockLineReorderChange | null = null;
    for (let index = 0; index < baseSections.sections.length; index += 1) {
      const baseSection = baseSections.sections[index];
      const targetSection = targetSections.sections[index];
      if (areLineGroupsEqual(baseSection.lines, targetSection.lines)) continue;
      const reorderedLines = parseFencedBlockLineReorderSectionLines(baseSection.lines, targetSection.lines);
      if (!reorderedLines) return null;
      if (change) return null;
      change = {
        heading: baseSection.heading,
        targetLines: reorderedLines,
      };
    }
    return change;
  };
  const parseSectionParagraphBlocks = (sectionLines: string[]): ParsedParagraphBlock[] | null => {
    const blocks: ParsedParagraphBlock[] = [];
    let currentBlockLines: string[] = [];

    const flushBlock = () => {
      if (currentBlockLines.length === 0) return;
      if (isUnsafeParagraphMoveBlock(currentBlockLines)) {
        currentBlockLines = [];
        blocks.push({
          baseIndex: -1,
          lines: [],
          key: '__unsafe__',
        });
        return;
      }
      blocks.push({
        baseIndex: blocks.length,
        lines: currentBlockLines,
        key: currentBlockLines.join('\n'),
      });
      currentBlockLines = [];
    };

    sectionLines.slice(1).forEach((line) => {
      if (!line.trim()) {
        flushBlock();
        return;
      }
      currentBlockLines.push(line);
    });
    flushBlock();

    if (blocks.some(block => block.key === '__unsafe__')) return null;
    if (blocks.length < 2) return null;
    const blockKeys = blocks.map(block => block.key);
    if (new Set(blockKeys).size !== blockKeys.length) return null;
    return blocks;
  };
  const parseSafeSectionParagraphBlocks = (sectionLines: string[]): ParsedParagraphBlock[] | null => {
    const blocks: ParsedParagraphBlock[] = [];
    let currentBlockLines: string[] = [];

    const flushBlock = () => {
      if (currentBlockLines.length === 0) return;
      if (isUnsafeParagraphMoveBlock(currentBlockLines)) {
        currentBlockLines = [];
        blocks.push({
          baseIndex: -1,
          lines: [],
          key: '__unsafe__',
        });
        return;
      }
      blocks.push({
        baseIndex: blocks.length,
        lines: currentBlockLines,
        key: currentBlockLines.join('\n'),
      });
      currentBlockLines = [];
    };

    sectionLines.slice(1).forEach((line) => {
      if (!line.trim()) {
        flushBlock();
        return;
      }
      currentBlockLines.push(line);
    });
    flushBlock();

    if (blocks.some(block => block.key === '__unsafe__')) return null;
    const blockKeys = blocks.map(block => block.key);
    if (new Set(blockKeys).size !== blockKeys.length) return null;
    return blocks;
  };
  const flattenSectionParagraphBlocks = (
    sections: ParsedMarkdownSections
  ): Array<ParsedParagraphBlock & { heading: string }> | null => {
    const units: Array<ParsedParagraphBlock & { heading: string }> = [];
    for (const section of sections.sections) {
      const blocks = parseSafeSectionParagraphBlocks(section.lines);
      if (!blocks) return null;
      blocks.forEach(block => units.push({ ...block, heading: section.heading }));
    }
    return units;
  };
  const countParagraphBlockKeys = (
    blocks: Array<ParsedParagraphBlock & { heading: string }>
  ): Map<string, number> => (
    blocks.reduce((counts, block) => {
      counts.set(block.key, (counts.get(block.key) ?? 0) + 1);
      return counts;
    }, new Map<string, number>())
  );
  const findCrossSectionParagraphMoveChange = (
    baseSections: ParsedMarkdownSections,
    targetSections: ParsedMarkdownSections
  ): CrossSectionParagraphMoveChange | null => {
    if (!hasSameSectionShape(baseSections, targetSections)) return null;
    const baseBlocks = flattenSectionParagraphBlocks(baseSections);
    const targetBlocks = flattenSectionParagraphBlocks(targetSections);
    if (!baseBlocks || !targetBlocks || baseBlocks.length !== targetBlocks.length) return null;

    const baseCounts = countParagraphBlockKeys(baseBlocks);
    const targetCounts = countParagraphBlockKeys(targetBlocks);
    if (
      Array.from(baseCounts.values()).some(count => count !== 1)
      || Array.from(targetCounts.values()).some(count => count !== 1)
    ) {
      return null;
    }

    const targetBlockByKey = new Map(targetBlocks.map(block => [block.key, block]));
    const baseKeys = new Set(baseBlocks.map(block => block.key));
    if (targetBlocks.some(block => !baseKeys.has(block.key))) return null;

    const movedBlocks = baseBlocks.filter(block => (
      targetBlockByKey.get(block.key)?.heading !== block.heading
    ));
    if (movedBlocks.length !== 1) return null;
    const movedBlock = movedBlocks[0];
    const movedTarget = targetBlockByKey.get(movedBlock.key);
    if (!movedTarget || !areLineGroupsEqual(movedBlock.lines, movedTarget.lines)) return null;

    const sectionOrders = new Map<string, string[]>();
    for (const baseSection of baseSections.sections) {
      const targetSection = targetSections.sections.find(section => section.heading === baseSection.heading);
      if (!targetSection) return null;
      const baseSectionBlocks = parseSafeSectionParagraphBlocks(baseSection.lines);
      const targetSectionBlocks = parseSafeSectionParagraphBlocks(targetSection.lines);
      if (!baseSectionBlocks || !targetSectionBlocks) return null;

      const baseKeysWithoutMoved = baseSectionBlocks
        .map(block => block.key)
        .filter(key => key !== movedBlock.key);
      const targetKeysWithoutMoved = targetSectionBlocks
        .map(block => block.key)
        .filter(key => key !== movedBlock.key);
      if (!areSectionOrdersEqual(baseKeysWithoutMoved, targetKeysWithoutMoved)) {
        return null;
      }
      sectionOrders.set(baseSection.heading, targetSectionBlocks.map(block => block.key));
    }

    return {
      movedKey: movedBlock.key,
      sourceHeading: movedBlock.heading,
      targetHeading: movedTarget.heading,
      sectionOrders,
    };
  };
  const areCrossSectionParagraphMovesEqual = (
    left: CrossSectionParagraphMoveChange,
    right: CrossSectionParagraphMoveChange,
    sectionHeadings: string[]
  ): boolean => (
    left.movedKey === right.movedKey
    && left.sourceHeading === right.sourceHeading
    && left.targetHeading === right.targetHeading
    && sectionHeadings.every(heading => areSectionOrdersEqual(
      left.sectionOrders.get(heading) ?? [],
      right.sectionOrders.get(heading) ?? []
    ))
  );
  const findSingleMovedParagraphIndex = (baseOrder: number[], targetOrder: number[]): number | null => {
    if (
      baseOrder.length !== targetOrder.length
      || baseOrder.every((baseIndex, index) => baseIndex === targetOrder[index])
    ) {
      return null;
    }

    const matchingMovedIndexes = new Set<number>();
    for (let fromIndex = 0; fromIndex < baseOrder.length; fromIndex += 1) {
      for (let toIndex = 0; toIndex < baseOrder.length; toIndex += 1) {
        if (fromIndex === toIndex) continue;
        const reordered = [...baseOrder];
        const [movedBaseIndex] = reordered.splice(fromIndex, 1);
        reordered.splice(toIndex, 0, movedBaseIndex);
        if (reordered.every((baseIndex, index) => baseIndex === targetOrder[index])) {
          matchingMovedIndexes.add(movedBaseIndex);
        }
      }
    }

    return matchingMovedIndexes.size === 1 ? Array.from(matchingMovedIndexes)[0] : null;
  };
  const getTrailingBlankLineCount = (sectionLines: string[]): number => {
    let count = 0;
    for (let index = sectionLines.length - 1; index > 0; index -= 1) {
      if (sectionLines[index].trim()) break;
      count += 1;
    }
    return count;
  };
  const buildParagraphSectionLines = (
    heading: string,
    blocks: ParsedParagraphBlock[],
    trailingBlankLineCount: number
  ): string[] => {
    const lines = [heading];
    blocks.forEach((block, index) => {
      if (index > 0) lines.push('');
      lines.push(...block.lines);
    });
    for (let index = 0; index < trailingBlankLineCount; index += 1) {
      lines.push('');
    }
    return lines;
  };
  type ParagraphRewriteSection = {
    blocks: ParsedParagraphBlock[];
    trailingBlankLineCount: number;
  };
  type ParagraphDeleteChange = {
    deletedIndexes: Set<number>;
  };
  type ParagraphInsertChange = {
    insertedBlocks: Array<{ afterBaseIndex: number; block: ParsedParagraphBlock }>;
  };
  type ParagraphRewriteChange = {
    rewrittenBlocks: Map<number, ParsedParagraphBlock>;
  };
  const parseParagraphRewriteSection = (
    heading: string,
    sectionLines: string[]
  ): ParagraphRewriteSection | null => {
    const blocks = parseSafeSectionParagraphBlocks(sectionLines);
    if (!blocks || blocks.length < 2) return null;
    const trailingBlankLineCount = getTrailingBlankLineCount(sectionLines);
    if (!areLineGroupsEqual(
      sectionLines,
      buildParagraphSectionLines(heading, blocks, trailingBlankLineCount)
    )) {
      return null;
    }

    return {
      blocks,
      trailingBlankLineCount,
    };
  };
  const parseParagraphChangeSection = (
    heading: string,
    sectionLines: string[]
  ): ParagraphRewriteSection | null => {
    const blocks = parseSafeSectionParagraphBlocks(sectionLines);
    if (!blocks || blocks.length === 0) return null;
    const trailingBlankLineCount = getTrailingBlankLineCount(sectionLines);
    if (!areLineGroupsEqual(
      sectionLines,
      buildParagraphSectionLines(heading, blocks, trailingBlankLineCount)
    )) {
      return null;
    }

    return {
      blocks,
      trailingBlankLineCount,
    };
  };
  const parsePureParagraphDeleteChange = (
    baseSection: ParagraphRewriteSection,
    targetSection: ParagraphRewriteSection
  ): ParagraphDeleteChange | null => {
    if (
      targetSection.blocks.length >= baseSection.blocks.length
      || targetSection.trailingBlankLineCount !== baseSection.trailingBlankLineCount
    ) {
      return null;
    }

    const baseBlockIndexByKey = new Map(
      baseSection.blocks.map((block, index) => [block.key, index])
    );
    let previousBaseIndex = -1;
    const retainedIndexes = new Set<number>();
    for (const targetBlock of targetSection.blocks) {
      const baseIndex = baseBlockIndexByKey.get(targetBlock.key);
      if (baseIndex === undefined || baseIndex <= previousBaseIndex) return null;
      retainedIndexes.add(baseIndex);
      previousBaseIndex = baseIndex;
    }

    const deletedIndexes = new Set<number>();
    baseSection.blocks.forEach((_, index) => {
      if (!retainedIndexes.has(index)) {
        deletedIndexes.add(index);
      }
    });
    return deletedIndexes.size > 0 ? { deletedIndexes } : null;
  };
  const parsePureParagraphInsertChange = (
    baseSection: ParagraphRewriteSection,
    targetSection: ParagraphRewriteSection
  ): ParagraphInsertChange | null => {
    if (
      targetSection.blocks.length <= baseSection.blocks.length
      || targetSection.trailingBlankLineCount !== baseSection.trailingBlankLineCount
    ) {
      return null;
    }

    const baseBlockKeySet = new Set(baseSection.blocks.map(block => block.key));
    const insertedBlocks: ParagraphInsertChange['insertedBlocks'] = [];
    let baseIndex = 0;

    for (const targetBlock of targetSection.blocks) {
      const baseBlock = baseSection.blocks[baseIndex];
      if (baseBlock && targetBlock.key === baseBlock.key && areLineGroupsEqual(targetBlock.lines, baseBlock.lines)) {
        baseIndex += 1;
        continue;
      }
      if (baseBlockKeySet.has(targetBlock.key)) {
        return null;
      }
      insertedBlocks.push({
        afterBaseIndex: baseIndex - 1,
        block: targetBlock,
      });
    }

    if (baseIndex !== baseSection.blocks.length || insertedBlocks.length === 0) {
      return null;
    }

    return { insertedBlocks };
  };
  const parsePureParagraphRewriteChange = (
    baseSection: ParagraphRewriteSection,
    targetSection: ParagraphRewriteSection
  ): ParagraphRewriteChange | null => {
    if (
      targetSection.blocks.length !== baseSection.blocks.length
      || targetSection.trailingBlankLineCount !== baseSection.trailingBlankLineCount
    ) {
      return null;
    }

    const baseBlockIndexByKey = new Map(
      baseSection.blocks.map((block, index) => [block.key, index])
    );
    const rewrittenBlocks = new Map<number, ParsedParagraphBlock>();
    for (let blockIndex = 0; blockIndex < baseSection.blocks.length; blockIndex += 1) {
      const baseBlock = baseSection.blocks[blockIndex];
      const targetBlock = targetSection.blocks[blockIndex];
      const matchedBaseIndex = baseBlockIndexByKey.get(targetBlock.key);
      if (matchedBaseIndex !== undefined && matchedBaseIndex !== blockIndex) {
        return null;
      }
      if (!areLineGroupsEqual(baseBlock.lines, targetBlock.lines)) {
        rewrittenBlocks.set(blockIndex, targetBlock);
      }
    }

    return rewrittenBlocks.size === 1 ? { rewrittenBlocks } : null;
  };
  const hasParagraphRewriteShape = (
    baseSection: ParagraphRewriteSection,
    targetSection: ParagraphRewriteSection
  ): boolean => {
    if (
      targetSection.blocks.length !== baseSection.blocks.length
      || targetSection.trailingBlankLineCount !== baseSection.trailingBlankLineCount
    ) {
      return false;
    }
    const baseBlockIndexByKey = new Map(
      baseSection.blocks.map((block, index) => [block.key, index])
    );
    let changedBlocks = 0;
    for (let blockIndex = 0; blockIndex < baseSection.blocks.length; blockIndex += 1) {
      const targetBlock = targetSection.blocks[blockIndex];
      const matchedBaseIndex = baseBlockIndexByKey.get(targetBlock.key);
      if (matchedBaseIndex !== undefined && matchedBaseIndex !== blockIndex) {
        return false;
      }
      if (!areLineGroupsEqual(baseSection.blocks[blockIndex].lines, targetBlock.lines)) {
        changedBlocks += 1;
      }
    }
    return changedBlocks > 0;
  };
  const buildMergedSameSectionParagraphInsertRewriteLines = (
    heading: string,
    baseSectionLines: string[],
    insertSectionLines: string[],
    rewriteSectionLines: string[]
  ): string[] | null => {
    const baseSection = parseParagraphRewriteSection(heading, baseSectionLines);
    const insertSection = parseParagraphChangeSection(heading, insertSectionLines);
    const rewriteSection = parseParagraphRewriteSection(heading, rewriteSectionLines);
    if (!baseSection || !insertSection || !rewriteSection) return null;

    const insertChange = parsePureParagraphInsertChange(baseSection, insertSection);
    const rewriteChange = parsePureParagraphRewriteChange(baseSection, rewriteSection);
    if (!insertChange || !rewriteChange) return null;
    const rewrittenBaseIndexes = new Set(rewriteChange.rewrittenBlocks.keys());
    if (insertChange.insertedBlocks.some(({ afterBaseIndex }) => rewrittenBaseIndexes.has(afterBaseIndex))) {
      return null;
    }

    const insertedBlocksByBaseIndex = new Map<number, ParsedParagraphBlock[]>();
    insertChange.insertedBlocks.forEach(({ afterBaseIndex, block }) => {
      const existingBlocks = insertedBlocksByBaseIndex.get(afterBaseIndex) ?? [];
      existingBlocks.push(block);
      insertedBlocksByBaseIndex.set(afterBaseIndex, existingBlocks);
    });

    const mergedBlocks = [
      ...(insertedBlocksByBaseIndex.get(-1) ?? []),
    ];
    baseSection.blocks.forEach((baseBlock, index) => {
      mergedBlocks.push(rewriteChange.rewrittenBlocks.get(index) ?? baseBlock);
      mergedBlocks.push(...(insertedBlocksByBaseIndex.get(index) ?? []));
    });

    const mergedKeys = mergedBlocks.map(block => block.key);
    if (new Set(mergedKeys).size !== mergedKeys.length) return null;

    return buildParagraphSectionLines(
      heading,
      mergedBlocks,
      baseSection.trailingBlankLineCount
    );
  };
  const buildMergedSameSectionParagraphRewriteLines = (
    heading: string,
    baseSectionLines: string[],
    serverSectionLines: string[],
    draftSectionLines: string[]
  ): string[] | null => {
    const baseSection = parseParagraphRewriteSection(heading, baseSectionLines);
    const serverSection = parseParagraphRewriteSection(heading, serverSectionLines);
    const draftSection = parseParagraphRewriteSection(heading, draftSectionLines);
    if (!baseSection || !serverSection || !draftSection) return null;
    if (
      baseSection.blocks.length !== serverSection.blocks.length
      || baseSection.blocks.length !== draftSection.blocks.length
      || baseSection.trailingBlankLineCount !== serverSection.trailingBlankLineCount
      || baseSection.trailingBlankLineCount !== draftSection.trailingBlankLineCount
    ) {
      return null;
    }

    const baseBlockIndexByKey = new Map(
      baseSection.blocks.map((block, index) => [block.key, index])
    );
    const preservesBaseBlockPositions = (targetSection: ParagraphRewriteSection): boolean => (
      targetSection.blocks.every((block, index) => {
        const baseIndex = baseBlockIndexByKey.get(block.key);
        return baseIndex === undefined || baseIndex === index;
      })
    );
    if (
      !preservesBaseBlockPositions(serverSection)
      || !preservesBaseBlockPositions(draftSection)
    ) {
      return null;
    }

    let hasServerOnlyParagraphChange = false;
    let hasDraftOnlyParagraphChange = false;
    const mergedBlocks: ParsedParagraphBlock[] = [];

    for (let blockIndex = 0; blockIndex < baseSection.blocks.length; blockIndex += 1) {
      const baseBlock = baseSection.blocks[blockIndex];
      const serverBlock = serverSection.blocks[blockIndex];
      const draftBlock = draftSection.blocks[blockIndex];
      const serverChanged = !areLineGroupsEqual(baseBlock.lines, serverBlock.lines);
      const draftChanged = !areLineGroupsEqual(baseBlock.lines, draftBlock.lines);

      if (serverChanged && draftChanged) {
        if (!areLineGroupsEqual(serverBlock.lines, draftBlock.lines)) {
          return null;
        }
        mergedBlocks.push(serverBlock);
        continue;
      }

      if (serverChanged) {
        hasServerOnlyParagraphChange = true;
        mergedBlocks.push(serverBlock);
      } else if (draftChanged) {
        hasDraftOnlyParagraphChange = true;
        mergedBlocks.push(draftBlock);
      } else {
        mergedBlocks.push(baseBlock);
      }
    }

    if (!hasServerOnlyParagraphChange || !hasDraftOnlyParagraphChange) {
      return null;
    }

    return buildParagraphSectionLines(
      heading,
      mergedBlocks,
      baseSection.trailingBlankLineCount
    );
  };
  const buildMergedSameSectionParagraphDeleteRewriteLines = (
    heading: string,
    baseSectionLines: string[],
    deleteSectionLines: string[],
    rewriteSectionLines: string[]
  ): string[] | null => {
    const baseSection = parseParagraphRewriteSection(heading, baseSectionLines);
    const deleteSection = parseParagraphChangeSection(heading, deleteSectionLines);
    const rewriteSection = parseParagraphRewriteSection(heading, rewriteSectionLines);
    if (!baseSection || !deleteSection || !rewriteSection) return null;

    const deleteChange = parsePureParagraphDeleteChange(baseSection, deleteSection);
    const rewriteChange = parsePureParagraphRewriteChange(baseSection, rewriteSection);
    if (!deleteChange || !rewriteChange) return null;
    if (Array.from(deleteChange.deletedIndexes).some(index => rewriteChange.rewrittenBlocks.has(index))) {
      return null;
    }

    const mergedBlocks = baseSection.blocks.reduce<ParsedParagraphBlock[]>((blocks, baseBlock, index) => {
      if (deleteChange.deletedIndexes.has(index)) {
        return blocks;
      }
      blocks.push(rewriteChange.rewrittenBlocks.get(index) ?? baseBlock);
      return blocks;
    }, []);
    if (mergedBlocks.length === baseSection.blocks.length || mergedBlocks.length === 0) return null;

    return buildParagraphSectionLines(
      heading,
      mergedBlocks,
      baseSection.trailingBlankLineCount
    );
  };
  const findParagraphMoveChange = (
    baseSections: ParsedMarkdownSections,
    targetSections: ParsedMarkdownSections
  ): ParagraphMoveChange | null => {
    if (!hasSameSectionShape(baseSections, targetSections)) return null;
    const targetSectionMap = buildSectionMap(targetSections);
    let move: ParagraphMoveChange | null = null;

    for (const baseSection of baseSections.sections) {
      const targetSection = targetSectionMap.get(baseSection.heading);
      if (!targetSection) return null;
      const baseBlocks = parseSectionParagraphBlocks(baseSection.lines);
      const targetBlocks = parseSectionParagraphBlocks(targetSection);
      if (!baseBlocks || !targetBlocks) {
        if (!areLineGroupsEqual(baseSection.lines, targetSection)) return null;
        continue;
      }

      const baseKeys = baseBlocks.map(block => block.key);
      const targetKeys = targetBlocks.map(block => block.key);
      if (
        baseKeys.length !== targetKeys.length
        || targetKeys.some(key => !baseKeys.includes(key))
      ) {
        return null;
      }

      const baseOrder = baseBlocks.map(block => block.baseIndex);
      const targetOrder = targetKeys.map(key => baseKeys.indexOf(key));
      if (areSectionOrdersEqual(baseOrder.map(String), targetOrder.map(String))) {
        if (!areLineGroupsEqual(baseSection.lines, targetSection)) return null;
        continue;
      }
      const movedBaseIndex = findSingleMovedParagraphIndex(baseOrder, targetOrder);
      if (movedBaseIndex === null) return null;
      if (move) return null;
      move = {
        heading: baseSection.heading,
        movedBaseIndex,
        targetOrder,
      };
    }

    return move;
  };
  const hasCrossSectionUnitMovement = (
    baseSections: ParsedMarkdownSections,
    targetSections: ParsedMarkdownSections
  ): boolean => {
    const baseUnits = baseSections.sections.flatMap(section => (
      collectSectionMovementUnits(section.heading, section.lines)
    ));
    const targetUnits = targetSections.sections.flatMap(section => (
      collectSectionMovementUnits(section.heading, section.lines)
    ));
    const baseCounts = countUnitKeys(baseUnits);
    const targetCounts = countUnitKeys(targetUnits);
    const targetUnitByKey = new Map(targetUnits.map(unit => [unit.key, unit]));

    return baseUnits.some((unit) => {
      if (baseCounts.get(unit.key) !== 1 || targetCounts.get(unit.key) !== 1) return false;
      return targetUnitByKey.get(unit.key)?.heading !== unit.heading;
    });
  };
  const hasMovementThatShouldBypassSectionRewrite = (
    baseSections: ParsedMarkdownSections,
    targetSections: ParsedMarkdownSections
  ): boolean => {
    if (findParagraphMoveChange(baseSections, targetSections)) return true;
    if (hasCrossSectionUnitMovement(baseSections, targetSections)) return true;
    return baseSections.sections.some((baseSection, index) => (
      hasUnsafeUnitReorder(
        baseSection.lines,
        targetSections.sections[index]?.lines ?? [],
        baseSection.heading
      )
    ));
  };
  const getSectionBodyLines = (sectionLines: string[]): string[] => sectionLines.slice(1);
  const getMarkdownHeadingDepth = (heading: string): number => heading.match(/^#+/)?.[0].length ?? 0;
  type SectionRenameChange = {
    oldHeading: string;
    newHeading: string;
    newLines: string[];
  };
  const findSectionRenameChange = (
    baseSections: ParsedMarkdownSections,
    targetSections: ParsedMarkdownSections
  ): SectionRenameChange | null => {
    const baseHeadingSet = getSectionHeadingSet(baseSections);
    const targetHeadingSet = getSectionHeadingSet(targetSections);
    const deletedHeadings = getSectionOrder(baseSections).filter(heading => !targetHeadingSet.has(heading));
    const addedHeadings = getSectionOrder(targetSections).filter(heading => !baseHeadingSet.has(heading));
    if (deletedHeadings.length !== 1 || addedHeadings.length !== 1) return null;

    const oldHeading = deletedHeadings[0];
    const newHeading = addedHeadings[0];
    if (getMarkdownHeadingDepth(oldHeading) !== getMarkdownHeadingDepth(newHeading)) {
      return null;
    }
    const expectedTargetOrder = getSectionOrder(baseSections).map(heading => (
      heading === oldHeading ? newHeading : heading
    ));
    if (!areSectionOrdersEqual(expectedTargetOrder, getSectionOrder(targetSections))) {
      return null;
    }

    const baseSection = buildSectionMap(baseSections).get(oldHeading);
    const targetSection = buildSectionMap(targetSections).get(newHeading);
    if (!baseSection || !targetSection) return null;
    if (!areLineGroupsEqual(getSectionBodyLines(baseSection), getSectionBodyLines(targetSection))) {
      return null;
    }
    return {
      oldHeading,
      newHeading,
      newLines: targetSection,
    };
  };
  const buildAutoMergedSectionRewriteResult = (
    baseContent: string,
    serverContent: string,
    draftContent: string
  ): AutoMergedConflictResult | null => {
    const baseSections = parseMarkdownSectionsForAutoMerge(baseContent);
    const serverSections = parseMarkdownSectionsForAutoMerge(serverContent);
    const draftSections = parseMarkdownSectionsForAutoMerge(draftContent);
    if (!baseSections || !serverSections || !draftSections) return null;
    if (
      !hasSameSectionShape(baseSections, serverSections)
      || !hasSameSectionShape(baseSections, draftSections)
    ) {
      return null;
    }
    if (
      hasMovementThatShouldBypassSectionRewrite(baseSections, serverSections)
      || hasMovementThatShouldBypassSectionRewrite(baseSections, draftSections)
    ) {
      return null;
    }
    if (baseSections.sections.some((baseSection, index) => (
      hasMarkdownTableLineChangeInSection(baseSection.lines, serverSections.sections[index].lines)
      || hasMarkdownTableLineChangeInSection(baseSection.lines, draftSections.sections[index].lines)
      || hasMarkdownListItemLineChangeInSection(baseSection.lines, serverSections.sections[index].lines)
      || hasMarkdownListItemLineChangeInSection(baseSection.lines, draftSections.sections[index].lines)
      || hasFencedBlockLineChangeInSection(baseSection.lines, serverSections.sections[index].lines)
      || hasFencedBlockLineChangeInSection(baseSection.lines, draftSections.sections[index].lines)
    ))) {
      return null;
    }

    let hasServerChange = false;
    let hasDraftChange = false;
    const mergedSectionLines: string[][] = [];

    for (let index = 0; index < baseSections.sections.length; index += 1) {
      const baseSectionLines = baseSections.sections[index].lines;
      const serverSectionLines = serverSections.sections[index].lines;
      const draftSectionLines = draftSections.sections[index].lines;
      const serverChanged = !areLineGroupsEqual(baseSectionLines, serverSectionLines);
      const draftChanged = !areLineGroupsEqual(baseSectionLines, draftSectionLines);

      if (
        serverChanged
        && draftChanged
        && !areLineGroupsEqual(serverSectionLines, draftSectionLines)
      ) {
        return null;
      }

      if (draftChanged) {
        hasDraftChange = true;
        mergedSectionLines.push(draftSectionLines);
      } else if (serverChanged) {
        hasServerChange = true;
        mergedSectionLines.push(serverSectionLines);
      } else {
        mergedSectionLines.push(baseSectionLines);
      }
    }

    if (!hasServerChange || !hasDraftChange) return null;

    const mergedContent = [
      ...baseSections.preambleLines,
      ...mergedSectionLines.flat(),
    ].join('\n');
    if (mergedContent === serverContent.replace(/\r\n/g, '\n')) return null;

    return {
      content: mergedContent,
      summary: '合并轨迹：自动合并服务端与草稿的非重叠章节改写',
    };
  };
  const buildAutoMergedSameSectionParagraphRewriteResult = (
    baseContent: string,
    serverContent: string,
    draftContent: string
  ): AutoMergedConflictResult | null => {
    const baseSections = parseMarkdownSectionsForAutoMerge(baseContent);
    const serverSections = parseMarkdownSectionsForAutoMerge(serverContent);
    const draftSections = parseMarkdownSectionsForAutoMerge(draftContent);
    if (!baseSections || !serverSections || !draftSections) return null;
    if (
      !hasSameSectionShape(baseSections, serverSections)
      || !hasSameSectionShape(baseSections, draftSections)
    ) {
      return null;
    }
    if (
      hasMovementThatShouldBypassSectionRewrite(baseSections, serverSections)
      || hasMovementThatShouldBypassSectionRewrite(baseSections, draftSections)
    ) {
      return null;
    }
    if (baseSections.sections.some((baseSection, index) => (
      hasMarkdownTableLineChangeInSection(baseSection.lines, serverSections.sections[index].lines)
      || hasMarkdownTableLineChangeInSection(baseSection.lines, draftSections.sections[index].lines)
      || hasMarkdownListItemLineChangeInSection(baseSection.lines, serverSections.sections[index].lines)
      || hasMarkdownListItemLineChangeInSection(baseSection.lines, draftSections.sections[index].lines)
      || hasFencedBlockLineChangeInSection(baseSection.lines, serverSections.sections[index].lines)
      || hasFencedBlockLineChangeInSection(baseSection.lines, draftSections.sections[index].lines)
    ))) {
      return null;
    }

    let hasSameSectionParagraphMerge = false;
    const mergedSectionLines: string[][] = [];

    for (let index = 0; index < baseSections.sections.length; index += 1) {
      const baseSection = baseSections.sections[index];
      const baseSectionLines = baseSection.lines;
      const serverSectionLines = serverSections.sections[index].lines;
      const draftSectionLines = draftSections.sections[index].lines;
      const serverChanged = !areLineGroupsEqual(baseSectionLines, serverSectionLines);
      const draftChanged = !areLineGroupsEqual(baseSectionLines, draftSectionLines);

      if (serverChanged && draftChanged) {
        if (areLineGroupsEqual(serverSectionLines, draftSectionLines)) {
          mergedSectionLines.push(serverSectionLines);
          continue;
        }
        const mergedSameSectionLines = buildMergedSameSectionParagraphRewriteLines(
          baseSection.heading,
          baseSectionLines,
          serverSectionLines,
          draftSectionLines
        );
        if (!mergedSameSectionLines) return null;
        hasSameSectionParagraphMerge = true;
        mergedSectionLines.push(mergedSameSectionLines);
      } else if (draftChanged) {
        mergedSectionLines.push(draftSectionLines);
      } else if (serverChanged) {
        mergedSectionLines.push(serverSectionLines);
      } else {
        mergedSectionLines.push(baseSectionLines);
      }
    }

    if (!hasSameSectionParagraphMerge) return null;

    const mergedContent = [
      ...baseSections.preambleLines,
      ...mergedSectionLines.flat(),
    ].join('\n');
    if (mergedContent === serverContent.replace(/\r\n/g, '\n')) return null;

    return {
      content: mergedContent,
      summary: '合并轨迹：自动合并服务端与草稿的同章节非重叠段落改写',
    };
  };
  const buildAutoMergedSameSectionParagraphDeleteRewriteResult = (
    baseContent: string,
    serverContent: string,
    draftContent: string
  ): AutoMergedConflictResult | null => {
    const baseSections = parseMarkdownSectionsForAutoMerge(baseContent);
    const serverSections = parseMarkdownSectionsForAutoMerge(serverContent);
    const draftSections = parseMarkdownSectionsForAutoMerge(draftContent);
    if (!baseSections || !serverSections || !draftSections) return null;
    if (
      !hasSameSectionShape(baseSections, serverSections)
      || !hasSameSectionShape(baseSections, draftSections)
    ) {
      return null;
    }
    if (
      hasMovementThatShouldBypassSectionRewrite(baseSections, serverSections)
      || hasMovementThatShouldBypassSectionRewrite(baseSections, draftSections)
    ) {
      return null;
    }
    if (baseSections.sections.some((baseSection, index) => (
      hasMarkdownTableLineChangeInSection(baseSection.lines, serverSections.sections[index].lines)
      || hasMarkdownTableLineChangeInSection(baseSection.lines, draftSections.sections[index].lines)
      || hasMarkdownListItemLineChangeInSection(baseSection.lines, serverSections.sections[index].lines)
      || hasMarkdownListItemLineChangeInSection(baseSection.lines, draftSections.sections[index].lines)
      || hasFencedBlockLineChangeInSection(baseSection.lines, serverSections.sections[index].lines)
      || hasFencedBlockLineChangeInSection(baseSection.lines, draftSections.sections[index].lines)
    ))) {
      return null;
    }

    let hasSameSectionDeleteRewriteMerge = false;
    const mergedSectionLines: string[][] = [];

    for (let index = 0; index < baseSections.sections.length; index += 1) {
      const baseSection = baseSections.sections[index];
      const baseSectionLines = baseSection.lines;
      const serverSectionLines = serverSections.sections[index].lines;
      const draftSectionLines = draftSections.sections[index].lines;
      const serverChanged = !areLineGroupsEqual(baseSectionLines, serverSectionLines);
      const draftChanged = !areLineGroupsEqual(baseSectionLines, draftSectionLines);

      if (serverChanged && draftChanged) {
        if (areLineGroupsEqual(serverSectionLines, draftSectionLines)) {
          mergedSectionLines.push(serverSectionLines);
          continue;
        }

        const serverDeleteMergedLines = buildMergedSameSectionParagraphDeleteRewriteLines(
          baseSection.heading,
          baseSectionLines,
          serverSectionLines,
          draftSectionLines
        );
        const draftDeleteMergedLines = buildMergedSameSectionParagraphDeleteRewriteLines(
          baseSection.heading,
          baseSectionLines,
          draftSectionLines,
          serverSectionLines
        );
        if (serverDeleteMergedLines && draftDeleteMergedLines) return null;
        const mergedSameSectionLines = serverDeleteMergedLines ?? draftDeleteMergedLines;
        if (!mergedSameSectionLines) return null;
        hasSameSectionDeleteRewriteMerge = true;
        mergedSectionLines.push(mergedSameSectionLines);
      } else if (draftChanged) {
        mergedSectionLines.push(draftSectionLines);
      } else if (serverChanged) {
        mergedSectionLines.push(serverSectionLines);
      } else {
        mergedSectionLines.push(baseSectionLines);
      }
    }

    if (!hasSameSectionDeleteRewriteMerge) return null;

    const mergedContent = [
      ...baseSections.preambleLines,
      ...mergedSectionLines.flat(),
    ].join('\n');
    if (mergedContent === serverContent.replace(/\r\n/g, '\n')) return null;

    return {
      content: mergedContent,
      summary: '合并轨迹：自动合并服务端与草稿的同章节非重叠段落删除与改写',
    };
  };
  const buildAutoMergedSameSectionParagraphInsertRewriteResult = (
    baseContent: string,
    serverContent: string,
    draftContent: string
  ): AutoMergedConflictResult | null => {
    const baseSections = parseMarkdownSectionsForAutoMerge(baseContent);
    const serverSections = parseMarkdownSectionsForAutoMerge(serverContent);
    const draftSections = parseMarkdownSectionsForAutoMerge(draftContent);
    if (!baseSections || !serverSections || !draftSections) return null;
    if (
      !hasSameSectionShape(baseSections, serverSections)
      || !hasSameSectionShape(baseSections, draftSections)
    ) {
      return null;
    }
    if (
      hasMovementThatShouldBypassSectionRewrite(baseSections, serverSections)
      || hasMovementThatShouldBypassSectionRewrite(baseSections, draftSections)
    ) {
      return null;
    }
    if (baseSections.sections.some((baseSection, index) => (
      hasMarkdownTableLineChangeInSection(baseSection.lines, serverSections.sections[index].lines)
      || hasMarkdownTableLineChangeInSection(baseSection.lines, draftSections.sections[index].lines)
      || hasMarkdownListItemLineChangeInSection(baseSection.lines, serverSections.sections[index].lines)
      || hasMarkdownListItemLineChangeInSection(baseSection.lines, draftSections.sections[index].lines)
      || hasFencedBlockLineChangeInSection(baseSection.lines, serverSections.sections[index].lines)
      || hasFencedBlockLineChangeInSection(baseSection.lines, draftSections.sections[index].lines)
    ))) {
      return null;
    }

    let hasSameSectionInsertRewriteMerge = false;
    const mergedSectionLines: string[][] = [];

    for (let index = 0; index < baseSections.sections.length; index += 1) {
      const baseSection = baseSections.sections[index];
      const baseSectionLines = baseSection.lines;
      const serverSectionLines = serverSections.sections[index].lines;
      const draftSectionLines = draftSections.sections[index].lines;
      const serverChanged = !areLineGroupsEqual(baseSectionLines, serverSectionLines);
      const draftChanged = !areLineGroupsEqual(baseSectionLines, draftSectionLines);

      if (serverChanged && draftChanged) {
        if (areLineGroupsEqual(serverSectionLines, draftSectionLines)) {
          mergedSectionLines.push(serverSectionLines);
          continue;
        }

        const serverInsertMergedLines = buildMergedSameSectionParagraphInsertRewriteLines(
          baseSection.heading,
          baseSectionLines,
          serverSectionLines,
          draftSectionLines
        );
        const draftInsertMergedLines = buildMergedSameSectionParagraphInsertRewriteLines(
          baseSection.heading,
          baseSectionLines,
          draftSectionLines,
          serverSectionLines
        );
        if (serverInsertMergedLines && draftInsertMergedLines) return null;
        const mergedSameSectionLines = serverInsertMergedLines ?? draftInsertMergedLines;
        if (!mergedSameSectionLines) return null;
        hasSameSectionInsertRewriteMerge = true;
        mergedSectionLines.push(mergedSameSectionLines);
      } else if (draftChanged) {
        mergedSectionLines.push(draftSectionLines);
      } else if (serverChanged) {
        mergedSectionLines.push(serverSectionLines);
      } else {
        mergedSectionLines.push(baseSectionLines);
      }
    }

    if (!hasSameSectionInsertRewriteMerge) return null;

    const mergedContent = [
      ...baseSections.preambleLines,
      ...mergedSectionLines.flat(),
    ].join('\n');
    if (mergedContent === serverContent.replace(/\r\n/g, '\n')) return null;

    return {
      content: mergedContent,
      summary: '合并轨迹：自动合并服务端与草稿的同章节非重叠段落插入与改写',
    };
  };
  const hasUnsafeSameSectionParagraphInsertRewriteForAutoMerge = (
    baseContent: string,
    serverContent: string,
    draftContent: string
  ): boolean => {
    const baseSections = parseMarkdownSectionsForAutoMerge(baseContent);
    const serverSections = parseMarkdownSectionsForAutoMerge(serverContent);
    const draftSections = parseMarkdownSectionsForAutoMerge(draftContent);
    if (!baseSections || !serverSections || !draftSections) return false;
    if (
      !hasSameSectionShape(baseSections, serverSections)
      || !hasSameSectionShape(baseSections, draftSections)
    ) {
      return false;
    }

    return baseSections.sections.some((baseSection, index) => {
      const baseSectionLines = baseSection.lines;
      const serverSectionLines = serverSections.sections[index].lines;
      const draftSectionLines = draftSections.sections[index].lines;
      const serverChanged = !areLineGroupsEqual(baseSectionLines, serverSectionLines);
      const draftChanged = !areLineGroupsEqual(baseSectionLines, draftSectionLines);
      if (!serverChanged || !draftChanged || areLineGroupsEqual(serverSectionLines, draftSectionLines)) {
        return false;
      }

      const baseParsedSection = parseParagraphRewriteSection(baseSection.heading, baseSectionLines);
      const serverParsedSection = parseParagraphChangeSection(baseSection.heading, serverSectionLines);
      const draftParsedSection = parseParagraphChangeSection(baseSection.heading, draftSectionLines);
      if (!baseParsedSection || !serverParsedSection || !draftParsedSection) return false;

      const serverInsertChange = parsePureParagraphInsertChange(baseParsedSection, serverParsedSection);
      const draftInsertChange = parsePureParagraphInsertChange(baseParsedSection, draftParsedSection);
      const serverRewriteShape = hasParagraphRewriteShape(baseParsedSection, serverParsedSection);
      const draftRewriteShape = hasParagraphRewriteShape(baseParsedSection, draftParsedSection);

      return (
        Boolean(serverInsertChange && draftRewriteShape)
        || Boolean(draftInsertChange && serverRewriteShape)
      );
    });
  };
  const buildAutoMergedTableRowReorderResult = (
    baseContent: string,
    serverContent: string,
    draftContent: string
  ): AutoMergedConflictResult | null => {
    const baseSections = parseMarkdownSectionsForAutoMerge(baseContent);
    const serverSections = parseMarkdownSectionsForAutoMerge(serverContent);
    const draftSections = parseMarkdownSectionsForAutoMerge(draftContent);
    if (!baseSections || !serverSections || !draftSections) return null;
    if (
      !areLineGroupsEqual(baseSections.preambleLines, serverSections.preambleLines)
      || !areLineGroupsEqual(baseSections.preambleLines, draftSections.preambleLines)
      || !hasSameSectionShape(baseSections, serverSections)
      || !hasSameSectionShape(baseSections, draftSections)
    ) {
      return null;
    }

    const serverReorder = findTableRowReorderChange(baseSections, serverSections);
    const draftReorder = findTableRowReorderChange(baseSections, draftSections);
    if (!serverReorder && !draftReorder) return null;
    if (
      serverReorder
      && draftReorder
      && (
        serverReorder.heading !== draftReorder.heading
        || !areLineGroupsEqual(serverReorder.targetLines, draftReorder.targetLines)
      )
    ) {
      return null;
    }

    const reorder = draftReorder ?? serverReorder;
    if (!reorder) return null;
    if (draftReorder && !serverReorder && hasMovementThatShouldBypassSectionRewrite(baseSections, serverSections)) {
      return null;
    }
    if (serverReorder && !draftReorder && hasMovementThatShouldBypassSectionRewrite(baseSections, draftSections)) {
      return null;
    }

    const mergedSectionLines: string[][] = [];
    let hasOtherSideChange = false;
    for (let index = 0; index < baseSections.sections.length; index += 1) {
      const baseSection = baseSections.sections[index];
      const serverSection = serverSections.sections[index];
      const draftSection = draftSections.sections[index];
      const serverChanged = !areLineGroupsEqual(baseSection.lines, serverSection.lines);
      const draftChanged = !areLineGroupsEqual(baseSection.lines, draftSection.lines);

      if (baseSection.heading === reorder.heading) {
        const nonReorderSection = draftReorder ? serverSection : draftSection;
        if (
          !serverReorder
          || !draftReorder
        ) {
          if (!areLineGroupsEqual(nonReorderSection.lines, baseSection.lines)) return null;
        }
        mergedSectionLines.push(reorder.targetLines);
        continue;
      }

      if (
        (serverChanged && hasSectionMovementForAutoMerge(baseSection.lines, serverSection.lines, baseSection.heading))
        || (draftChanged && hasSectionMovementForAutoMerge(baseSection.lines, draftSection.lines, baseSection.heading))
        || (serverChanged && hasMarkdownListItemLineChangeInSection(baseSection.lines, serverSection.lines))
        || (draftChanged && hasMarkdownListItemLineChangeInSection(baseSection.lines, draftSection.lines))
        || (serverChanged && hasFencedBlockLineChangeInSection(baseSection.lines, serverSection.lines))
        || (draftChanged && hasFencedBlockLineChangeInSection(baseSection.lines, draftSection.lines))
      ) {
        return null;
      }
      if (
        serverChanged
        && draftChanged
        && !areLineGroupsEqual(serverSection.lines, draftSection.lines)
      ) {
        return null;
      }

      if (draftChanged) {
        hasOtherSideChange = true;
        mergedSectionLines.push(draftSection.lines);
      } else if (serverChanged) {
        hasOtherSideChange = true;
        mergedSectionLines.push(serverSection.lines);
      } else {
        mergedSectionLines.push(baseSection.lines);
      }
    }

    if (!serverReorder || !draftReorder) {
      if (!hasOtherSideChange) return null;
    }

    const mergedContent = [
      ...baseSections.preambleLines,
      ...mergedSectionLines.flat(),
    ].join('\n');
    if (mergedContent === serverContent.replace(/\r\n/g, '\n')) return null;

    return {
      content: mergedContent,
      summary: '合并轨迹：自动合并服务端与草稿的非重叠表格行重排',
    };
  };
  const buildAutoMergedListItemReorderResult = (
    baseContent: string,
    serverContent: string,
    draftContent: string
  ): AutoMergedConflictResult | null => {
    const baseSections = parseMarkdownSectionsForAutoMerge(baseContent);
    const serverSections = parseMarkdownSectionsForAutoMerge(serverContent);
    const draftSections = parseMarkdownSectionsForAutoMerge(draftContent);
    if (!baseSections || !serverSections || !draftSections) return null;
    if (
      !areLineGroupsEqual(baseSections.preambleLines, serverSections.preambleLines)
      || !areLineGroupsEqual(baseSections.preambleLines, draftSections.preambleLines)
      || !hasSameSectionShape(baseSections, serverSections)
      || !hasSameSectionShape(baseSections, draftSections)
    ) {
      return null;
    }

    const serverReorder = findListItemReorderChange(baseSections, serverSections);
    const draftReorder = findListItemReorderChange(baseSections, draftSections);
    if (!serverReorder && !draftReorder) return null;
    if (
      serverReorder
      && draftReorder
      && (
        serverReorder.heading !== draftReorder.heading
        || !areLineGroupsEqual(serverReorder.targetLines, draftReorder.targetLines)
      )
    ) {
      return null;
    }

    const reorder = draftReorder ?? serverReorder;
    if (!reorder) return null;
    if (draftReorder && !serverReorder && hasMovementThatShouldBypassSectionRewrite(baseSections, serverSections)) {
      return null;
    }
    if (serverReorder && !draftReorder && hasMovementThatShouldBypassSectionRewrite(baseSections, draftSections)) {
      return null;
    }

    const mergedSectionLines: string[][] = [];
    let hasOtherSideChange = false;
    for (let index = 0; index < baseSections.sections.length; index += 1) {
      const baseSection = baseSections.sections[index];
      const serverSection = serverSections.sections[index];
      const draftSection = draftSections.sections[index];
      const serverChanged = !areLineGroupsEqual(baseSection.lines, serverSection.lines);
      const draftChanged = !areLineGroupsEqual(baseSection.lines, draftSection.lines);

      if (baseSection.heading === reorder.heading) {
        const nonReorderSection = draftReorder ? serverSection : draftSection;
        if (!serverReorder || !draftReorder) {
          if (!areLineGroupsEqual(nonReorderSection.lines, baseSection.lines)) return null;
        }
        mergedSectionLines.push(reorder.targetLines);
        continue;
      }

      if (
        (serverChanged && hasSectionMovementForAutoMerge(baseSection.lines, serverSection.lines, baseSection.heading))
        || (draftChanged && hasSectionMovementForAutoMerge(baseSection.lines, draftSection.lines, baseSection.heading))
        || (serverChanged && hasMarkdownListItemLineChangeInSection(baseSection.lines, serverSection.lines))
        || (draftChanged && hasMarkdownListItemLineChangeInSection(baseSection.lines, draftSection.lines))
        || (serverChanged && hasFencedBlockLineChangeInSection(baseSection.lines, serverSection.lines))
        || (draftChanged && hasFencedBlockLineChangeInSection(baseSection.lines, draftSection.lines))
      ) {
        return null;
      }
      if (
        serverChanged
        && draftChanged
        && !areLineGroupsEqual(serverSection.lines, draftSection.lines)
      ) {
        return null;
      }

      if (draftChanged) {
        hasOtherSideChange = true;
        mergedSectionLines.push(draftSection.lines);
      } else if (serverChanged) {
        hasOtherSideChange = true;
        mergedSectionLines.push(serverSection.lines);
      } else {
        mergedSectionLines.push(baseSection.lines);
      }
    }

    if (!serverReorder || !draftReorder) {
      if (!hasOtherSideChange) return null;
    }

    const mergedContent = [
      ...baseSections.preambleLines,
      ...mergedSectionLines.flat(),
    ].join('\n');
    if (mergedContent === serverContent.replace(/\r\n/g, '\n')) return null;

    return {
      content: mergedContent,
      summary: '合并轨迹：自动合并服务端与草稿的非重叠列表项重排',
    };
  };
  const buildAutoMergedFencedBlockLineReorderResult = (
    baseContent: string,
    serverContent: string,
    draftContent: string
  ): AutoMergedConflictResult | null => {
    const baseSections = parseMarkdownSectionsForAutoMerge(baseContent);
    const serverSections = parseMarkdownSectionsForAutoMerge(serverContent);
    const draftSections = parseMarkdownSectionsForAutoMerge(draftContent);
    if (!baseSections || !serverSections || !draftSections) return null;
    if (
      !areLineGroupsEqual(baseSections.preambleLines, serverSections.preambleLines)
      || !areLineGroupsEqual(baseSections.preambleLines, draftSections.preambleLines)
      || !hasSameSectionShape(baseSections, serverSections)
      || !hasSameSectionShape(baseSections, draftSections)
    ) {
      return null;
    }

    const serverReorder = findFencedBlockLineReorderChange(baseSections, serverSections);
    const draftReorder = findFencedBlockLineReorderChange(baseSections, draftSections);
    if (!serverReorder && !draftReorder) return null;
    if (
      serverReorder
      && draftReorder
      && (
        serverReorder.heading !== draftReorder.heading
        || !areLineGroupsEqual(serverReorder.targetLines, draftReorder.targetLines)
      )
    ) {
      return null;
    }

    const reorder = draftReorder ?? serverReorder;
    if (!reorder) return null;
    if (draftReorder && !serverReorder && hasMovementThatShouldBypassSectionRewrite(baseSections, serverSections)) {
      return null;
    }
    if (serverReorder && !draftReorder && hasMovementThatShouldBypassSectionRewrite(baseSections, draftSections)) {
      return null;
    }

    const mergedSectionLines: string[][] = [];
    let hasOtherSideChange = false;
    for (let index = 0; index < baseSections.sections.length; index += 1) {
      const baseSection = baseSections.sections[index];
      const serverSection = serverSections.sections[index];
      const draftSection = draftSections.sections[index];
      const serverChanged = !areLineGroupsEqual(baseSection.lines, serverSection.lines);
      const draftChanged = !areLineGroupsEqual(baseSection.lines, draftSection.lines);

      if (baseSection.heading === reorder.heading) {
        const nonReorderSection = draftReorder ? serverSection : draftSection;
        if (!serverReorder || !draftReorder) {
          if (!areLineGroupsEqual(nonReorderSection.lines, baseSection.lines)) return null;
        }
        mergedSectionLines.push(reorder.targetLines);
        continue;
      }

      if (
        (serverChanged && hasSectionMovementForAutoMerge(baseSection.lines, serverSection.lines, baseSection.heading))
        || (draftChanged && hasSectionMovementForAutoMerge(baseSection.lines, draftSection.lines, baseSection.heading))
        || (serverChanged && hasMarkdownTableLineChangeInSection(baseSection.lines, serverSection.lines))
        || (draftChanged && hasMarkdownTableLineChangeInSection(baseSection.lines, draftSection.lines))
        || (serverChanged && hasMarkdownListItemLineChangeInSection(baseSection.lines, serverSection.lines))
        || (draftChanged && hasMarkdownListItemLineChangeInSection(baseSection.lines, draftSection.lines))
        || (serverChanged && hasFencedBlockLineChangeInSection(baseSection.lines, serverSection.lines))
        || (draftChanged && hasFencedBlockLineChangeInSection(baseSection.lines, draftSection.lines))
      ) {
        return null;
      }
      if (
        serverChanged
        && draftChanged
        && !areLineGroupsEqual(serverSection.lines, draftSection.lines)
      ) {
        return null;
      }

      if (draftChanged) {
        hasOtherSideChange = true;
        mergedSectionLines.push(draftSection.lines);
      } else if (serverChanged) {
        hasOtherSideChange = true;
        mergedSectionLines.push(serverSection.lines);
      } else {
        mergedSectionLines.push(baseSection.lines);
      }
    }

    if (!serverReorder || !draftReorder) {
      if (!hasOtherSideChange) return null;
    }

    const mergedContent = [
      ...baseSections.preambleLines,
      ...mergedSectionLines.flat(),
    ].join('\n');
    if (mergedContent === serverContent.replace(/\r\n/g, '\n')) return null;

    return {
      content: mergedContent,
      summary: '合并轨迹：自动合并服务端与草稿的非重叠代码块行重排',
    };
  };
  const buildAutoMergedParagraphMoveResult = (
    baseContent: string,
    serverContent: string,
    draftContent: string
  ): AutoMergedConflictResult | null => {
    const baseSections = parseMarkdownSectionsForAutoMerge(baseContent);
    const serverSections = parseMarkdownSectionsForAutoMerge(serverContent);
    const draftSections = parseMarkdownSectionsForAutoMerge(draftContent);
    if (!baseSections || !serverSections || !draftSections) return null;
    if (
      !areLineGroupsEqual(baseSections.preambleLines, serverSections.preambleLines)
      || !areLineGroupsEqual(baseSections.preambleLines, draftSections.preambleLines)
      || !hasSameSectionShape(baseSections, serverSections)
      || !hasSameSectionShape(baseSections, draftSections)
    ) {
      return null;
    }

    const serverMove = findParagraphMoveChange(baseSections, serverSections);
    const draftMove = findParagraphMoveChange(baseSections, draftSections);
    if (!serverMove && !draftMove) return null;
    if (
      (serverMove && !draftMove && hasCrossSectionUnitMovement(baseSections, draftSections))
      || (draftMove && !serverMove && hasCrossSectionUnitMovement(baseSections, serverSections))
    ) {
      return null;
    }

    const sameMove = Boolean(serverMove && draftMove);
    const move = draftMove ?? serverMove;
    if (!move) return null;
    if (
      serverMove
      && draftMove
      && (
        serverMove.heading !== draftMove.heading
        || serverMove.movedBaseIndex !== draftMove.movedBaseIndex
        || !areSectionOrdersEqual(serverMove.targetOrder.map(String), draftMove.targetOrder.map(String))
      )
    ) {
      return null;
    }

    const serverSectionMap = buildSectionMap(serverSections);
    const draftSectionMap = buildSectionMap(draftSections);
    const mergedSectionLines: string[][] = [];
    let hasNonMoveContentChange = false;

    for (const baseSection of baseSections.sections) {
      const baseSectionLines = baseSection.lines;
      const serverSectionLines = serverSectionMap.get(baseSection.heading);
      const draftSectionLines = draftSectionMap.get(baseSection.heading);
      if (!serverSectionLines || !draftSectionLines) return null;

      if (baseSection.heading === move.heading) {
        const baseBlocks = parseSectionParagraphBlocks(baseSectionLines);
        const serverBlocks = parseSectionParagraphBlocks(serverSectionLines);
        const draftBlocks = parseSectionParagraphBlocks(draftSectionLines);
        if (!baseBlocks || !serverBlocks || !draftBlocks) return null;

        const moveBlocks = draftMove ? draftBlocks : serverBlocks;
        const moveSideOrder = moveBlocks.map(block => baseBlocks.findIndex(baseBlock => baseBlock.key === block.key));
        if (!areSectionOrdersEqual(moveSideOrder.map(String), move.targetOrder.map(String))) {
          return null;
        }
        if (moveSideOrder.some(baseIndex => baseIndex < 0)) return null;
        if (moveBlocks.some((block, index) => (
          !areLineGroupsEqual(block.lines, baseBlocks[move.targetOrder[index]].lines)
        ))) {
          return null;
        }

        const nonMovingBlocks = sameMove ? null : (draftMove ? serverBlocks : draftBlocks);
        if (nonMovingBlocks) {
          if (nonMovingBlocks.length !== baseBlocks.length) return null;
          const baseKeys = baseBlocks.map(block => block.key);
          if (nonMovingBlocks.some((block, index) => (
            block.key !== baseBlocks[index].key && baseKeys.includes(block.key)
          ))) {
            return null;
          }
          if (!areLineGroupsEqual(nonMovingBlocks[move.movedBaseIndex].lines, baseBlocks[move.movedBaseIndex].lines)) {
            return null;
          }
        }

        const orderedBlocks = move.targetOrder.map((baseIndex) => {
          const baseBlock = baseBlocks[baseIndex];
          const nonMovingBlock = nonMovingBlocks?.[baseIndex];
          if (
            nonMovingBlock
            && baseIndex !== move.movedBaseIndex
            && !areLineGroupsEqual(nonMovingBlock.lines, baseBlock.lines)
          ) {
            hasNonMoveContentChange = true;
            return {
              ...nonMovingBlock,
              baseIndex,
            };
          }
          return baseBlock;
        });
        mergedSectionLines.push(buildParagraphSectionLines(
          baseSection.heading,
          orderedBlocks,
          getTrailingBlankLineCount(baseSectionLines)
        ));
        continue;
      }

      const serverChanged = !areLineGroupsEqual(baseSectionLines, serverSectionLines);
      const draftChanged = !areLineGroupsEqual(baseSectionLines, draftSectionLines);
      if (
        (serverChanged && hasSectionMovementForAutoMerge(baseSectionLines, serverSectionLines, baseSection.heading))
        || (draftChanged && hasSectionMovementForAutoMerge(baseSectionLines, draftSectionLines, baseSection.heading))
      ) {
        return null;
      }
      if (
        serverChanged
        && draftChanged
        && !areLineGroupsEqual(serverSectionLines, draftSectionLines)
      ) {
        return null;
      }

      if (draftChanged) {
        hasNonMoveContentChange = true;
        mergedSectionLines.push(draftSectionLines);
      } else if (serverChanged) {
        hasNonMoveContentChange = true;
        mergedSectionLines.push(serverSectionLines);
      } else {
        mergedSectionLines.push(baseSectionLines);
      }
    }

    if (!sameMove && !hasNonMoveContentChange) return null;

    return {
      content: [
        ...baseSections.preambleLines,
        ...mergedSectionLines.flat(),
      ].join('\n'),
      summary: '合并轨迹：自动合并服务端与草稿的非重叠段落移动',
    };
  };
  const buildAutoMergedCrossSectionParagraphMoveResult = (
    baseContent: string,
    serverContent: string,
    draftContent: string
  ): AutoMergedConflictResult | null => {
    const baseSections = parseMarkdownSectionsForAutoMerge(baseContent);
    const serverSections = parseMarkdownSectionsForAutoMerge(serverContent);
    const draftSections = parseMarkdownSectionsForAutoMerge(draftContent);
    if (!baseSections || !serverSections || !draftSections) return null;
    if (
      !areLineGroupsEqual(baseSections.preambleLines, serverSections.preambleLines)
      || !areLineGroupsEqual(baseSections.preambleLines, draftSections.preambleLines)
      || !hasSameSectionShape(baseSections, serverSections)
      || !hasSameSectionShape(baseSections, draftSections)
    ) {
      return null;
    }

    const serverMove = findCrossSectionParagraphMoveChange(baseSections, serverSections);
    const draftMove = findCrossSectionParagraphMoveChange(baseSections, draftSections);
    if (!serverMove && !draftMove) return null;

    const sectionHeadings = getSectionOrder(baseSections);
    const sameMove = Boolean(
      serverMove
      && draftMove
      && areCrossSectionParagraphMovesEqual(serverMove, draftMove, sectionHeadings)
    );
    if (serverMove && draftMove && !sameMove) return null;

    const move = draftMove ?? serverMove;
    if (!move) return null;

    const serverSectionMap = buildSectionMap(serverSections);
    const draftSectionMap = buildSectionMap(draftSections);
    const movedSectionHeadings = new Set([move.sourceHeading, move.targetHeading]);
    const movingSectionMap = buildSectionMap(draftMove ? draftSections : serverSections);
    const nonMovingSectionMap = sameMove
      ? null
      : buildSectionMap(draftMove ? serverSections : draftSections);
    const mergedSectionLines: string[][] = [];
    let hasNonMoveContentChange = false;

    for (const baseSection of baseSections.sections) {
      const baseSectionLines = baseSection.lines;
      const serverSectionLines = serverSectionMap.get(baseSection.heading);
      const draftSectionLines = draftSectionMap.get(baseSection.heading);
      if (!serverSectionLines || !draftSectionLines) return null;

      if (movedSectionHeadings.has(baseSection.heading)) {
        const movingSectionLines = movingSectionMap.get(baseSection.heading);
        const nonMovingSectionLines = nonMovingSectionMap?.get(baseSection.heading);
        if (!movingSectionLines) return null;
        if (
          nonMovingSectionLines
          && !areLineGroupsEqual(baseSectionLines, nonMovingSectionLines)
        ) {
          return null;
        }
        mergedSectionLines.push(movingSectionLines);
        continue;
      }

      const serverChanged = !areLineGroupsEqual(baseSectionLines, serverSectionLines);
      const draftChanged = !areLineGroupsEqual(baseSectionLines, draftSectionLines);
      if (
        (serverChanged && hasSectionMovementForAutoMerge(baseSectionLines, serverSectionLines, baseSection.heading))
        || (draftChanged && hasSectionMovementForAutoMerge(baseSectionLines, draftSectionLines, baseSection.heading))
      ) {
        return null;
      }
      if (
        serverChanged
        && draftChanged
        && !areLineGroupsEqual(serverSectionLines, draftSectionLines)
      ) {
        return null;
      }

      if (draftChanged) {
        hasNonMoveContentChange = true;
        mergedSectionLines.push(draftSectionLines);
      } else if (serverChanged) {
        hasNonMoveContentChange = true;
        mergedSectionLines.push(serverSectionLines);
      } else {
        mergedSectionLines.push(baseSectionLines);
      }
    }

    if (!sameMove && !hasNonMoveContentChange) return null;

    return {
      content: [
        ...baseSections.preambleLines,
        ...mergedSectionLines.flat(),
      ].join('\n'),
      summary: '合并轨迹：自动合并服务端与草稿的非重叠跨章节段落移动',
    };
  };
  const buildAutoMergedSectionMoveResult = (
    baseContent: string,
    serverContent: string,
    draftContent: string
  ): AutoMergedConflictResult | null => {
    const baseSections = parseMarkdownSectionsForAutoMerge(baseContent);
    const serverSections = parseMarkdownSectionsForAutoMerge(serverContent);
    const draftSections = parseMarkdownSectionsForAutoMerge(draftContent);
    if (!baseSections || !serverSections || !draftSections) return null;
    if (
      !areLineGroupsEqual(baseSections.preambleLines, serverSections.preambleLines)
      || !areLineGroupsEqual(baseSections.preambleLines, draftSections.preambleLines)
      || !haveSameSectionSet(baseSections, serverSections)
      || !haveSameSectionSet(baseSections, draftSections)
    ) {
      return null;
    }

    const baseOrder = getSectionOrder(baseSections);
    const serverOrder = getSectionOrder(serverSections);
    const draftOrder = getSectionOrder(draftSections);
    const serverMoved = !areSectionOrdersEqual(baseOrder, serverOrder);
    const draftMoved = !areSectionOrdersEqual(baseOrder, draftOrder);
    if (!serverMoved && !draftMoved) return null;
    if (serverMoved && draftMoved && !areSectionOrdersEqual(serverOrder, draftOrder)) {
      return null;
    }

    const movementOrder = draftMoved ? draftOrder : serverOrder;
    const baseSectionMap = buildSectionMap(baseSections);
    const serverSectionMap = buildSectionMap(serverSections);
    const draftSectionMap = buildSectionMap(draftSections);
    const mergedSectionLines: string[][] = [];
    let hasContentChange = false;

    for (const heading of movementOrder) {
      const baseSectionLines = baseSectionMap.get(heading);
      const serverSectionLines = serverSectionMap.get(heading);
      const draftSectionLines = draftSectionMap.get(heading);
      if (!baseSectionLines || !serverSectionLines || !draftSectionLines) return null;

      const serverChanged = !areLineGroupsEqual(baseSectionLines, serverSectionLines);
      const draftChanged = !areLineGroupsEqual(baseSectionLines, draftSectionLines);
      if (
        serverChanged
        && draftChanged
        && !areLineGroupsEqual(serverSectionLines, draftSectionLines)
      ) {
        return null;
      }

      if (draftChanged) {
        hasContentChange = true;
        mergedSectionLines.push(draftSectionLines);
      } else if (serverChanged) {
        hasContentChange = true;
        mergedSectionLines.push(serverSectionLines);
      } else {
        mergedSectionLines.push(baseSectionLines);
      }
    }

    if (!serverMoved && !draftMoved && !hasContentChange) return null;

    return {
      content: [
        ...baseSections.preambleLines,
        ...mergedSectionLines.flat(),
      ].join('\n'),
      summary: '合并轨迹：自动合并服务端与草稿的非重叠章节移动',
    };
  };
  const buildAutoMergedSectionRenameResult = (
    baseContent: string,
    serverContent: string,
    draftContent: string
  ): AutoMergedConflictResult | null => {
    const baseSections = parseMarkdownSectionsForAutoMerge(baseContent);
    const serverSections = parseMarkdownSectionsForAutoMerge(serverContent);
    const draftSections = parseMarkdownSectionsForAutoMerge(draftContent);
    if (!baseSections || !serverSections || !draftSections) return null;
    if (
      !areLineGroupsEqual(baseSections.preambleLines, serverSections.preambleLines)
      || !areLineGroupsEqual(baseSections.preambleLines, draftSections.preambleLines)
    ) {
      return null;
    }

    const serverRename = findSectionRenameChange(baseSections, serverSections);
    const draftRename = findSectionRenameChange(baseSections, draftSections);
    if (!serverRename && !draftRename) return null;

    const baseSectionMap = buildSectionMap(baseSections);
    const serverSectionMap = buildSectionMap(serverSections);
    const draftSectionMap = buildSectionMap(draftSections);
    let rename: SectionRenameChange;
    let sameRename = false;

    if (serverRename && draftRename) {
      if (
        serverRename.oldHeading !== draftRename.oldHeading
        || serverRename.newHeading !== draftRename.newHeading
        || !areLineGroupsEqual(serverRename.newLines, draftRename.newLines)
      ) {
        return null;
      }
      rename = draftRename;
      sameRename = true;
    } else if (serverRename) {
      if (!haveSameSectionSet(baseSections, draftSections)) return null;
      if (!areSectionOrdersEqual(getSectionOrder(baseSections), getSectionOrder(draftSections))) {
        return null;
      }
      const baseRenamedSection = baseSectionMap.get(serverRename.oldHeading);
      const draftRenamedSection = draftSectionMap.get(serverRename.oldHeading);
      if (
        !baseRenamedSection
        || !draftRenamedSection
        || !areLineGroupsEqual(baseRenamedSection, draftRenamedSection)
      ) {
        return null;
      }
      rename = serverRename;
    } else {
      if (!draftRename || !haveSameSectionSet(baseSections, serverSections)) return null;
      if (!areSectionOrdersEqual(getSectionOrder(baseSections), getSectionOrder(serverSections))) {
        return null;
      }
      const baseRenamedSection = baseSectionMap.get(draftRename.oldHeading);
      const serverRenamedSection = serverSectionMap.get(draftRename.oldHeading);
      if (
        !baseRenamedSection
        || !serverRenamedSection
        || !areLineGroupsEqual(baseRenamedSection, serverRenamedSection)
      ) {
        return null;
      }
      rename = draftRename;
    }

    const mergedSectionLines: string[][] = [];
    let hasServerContentChange = false;
    let hasDraftContentChange = false;

    for (const baseSection of baseSections.sections) {
      if (baseSection.heading === rename.oldHeading) {
        mergedSectionLines.push(rename.newLines);
        continue;
      }

      const baseSectionLines = baseSectionMap.get(baseSection.heading);
      const serverSectionLines = serverSectionMap.get(baseSection.heading);
      const draftSectionLines = draftSectionMap.get(baseSection.heading);
      if (!baseSectionLines || !serverSectionLines || !draftSectionLines) return null;

      const serverChanged = !areLineGroupsEqual(baseSectionLines, serverSectionLines);
      const draftChanged = !areLineGroupsEqual(baseSectionLines, draftSectionLines);
      if (
        serverChanged
        && draftChanged
        && !areLineGroupsEqual(serverSectionLines, draftSectionLines)
      ) {
        return null;
      }

      if (draftChanged) {
        hasDraftContentChange = true;
        mergedSectionLines.push(draftSectionLines);
      } else if (serverChanged) {
        hasServerContentChange = true;
        mergedSectionLines.push(serverSectionLines);
      } else {
        mergedSectionLines.push(baseSectionLines);
      }
    }

    if (
      !sameRename
      && (
        (draftRename && !hasServerContentChange)
        || (serverRename && !hasDraftContentChange)
      )
    ) {
      return null;
    }

    const mergedContent = [
      ...baseSections.preambleLines,
      ...mergedSectionLines.flat(),
    ].join('\n');
    if (!sameRename && mergedContent === serverContent.replace(/\r\n/g, '\n')) return null;

    return {
      content: mergedContent,
      summary: '合并轨迹：自动合并服务端与草稿的非重叠章节重命名',
    };
  };
  const buildAutoMergedSectionAddDeleteResult = (
    baseContent: string,
    serverContent: string,
    draftContent: string
  ): AutoMergedConflictResult | null => {
    const baseSections = parseMarkdownSectionsForAutoMerge(baseContent);
    const serverSections = parseMarkdownSectionsForAutoMerge(serverContent);
    const draftSections = parseMarkdownSectionsForAutoMerge(draftContent);
    if (!baseSections || !serverSections || !draftSections) return null;
    if (
      !areLineGroupsEqual(baseSections.preambleLines, serverSections.preambleLines)
      || !areLineGroupsEqual(baseSections.preambleLines, draftSections.preambleLines)
    ) {
      return null;
    }

    const baseSectionMap = buildSectionMap(baseSections);
    const serverSectionMap = buildSectionMap(serverSections);
    const draftSectionMap = buildSectionMap(draftSections);
    const baseHeadingSet = getSectionHeadingSet(baseSections);
    const serverHeadingSet = getSectionHeadingSet(serverSections);
    const draftHeadingSet = getSectionHeadingSet(draftSections);
    const serverAddedHeadings = getSectionOrder(serverSections).filter(heading => !baseHeadingSet.has(heading));
    const serverDeletedHeadings = getSectionOrder(baseSections).filter(heading => !serverHeadingSet.has(heading));
    const draftAddedHeadings = getSectionOrder(draftSections).filter(heading => !baseHeadingSet.has(heading));
    const draftDeletedHeadings = getSectionOrder(baseSections).filter(heading => !draftHeadingSet.has(heading));

    if (
      (serverAddedHeadings.length > 0 && serverDeletedHeadings.length > 0)
      || (draftAddedHeadings.length > 0 && draftDeletedHeadings.length > 0)
    ) {
      return null;
    }
    if (
      serverAddedHeadings.length === 0
      && serverDeletedHeadings.length === 0
      && draftAddedHeadings.length === 0
      && draftDeletedHeadings.length === 0
    ) {
      return null;
    }

    let hasServerChange = serverAddedHeadings.length > 0 || serverDeletedHeadings.length > 0;
    const mergedSectionLines: string[][] = [];

    for (const section of serverSections.sections) {
      const heading = section.heading;
      const serverSectionLines = serverSectionMap.get(heading);
      const draftSectionLines = draftSectionMap.get(heading);
      if (!serverSectionLines) return null;

      if (!baseHeadingSet.has(heading)) {
        if (
          draftSectionLines
          && !areLineGroupsEqual(serverSectionLines, draftSectionLines)
        ) {
          return null;
        }
        mergedSectionLines.push(serverSectionLines);
        continue;
      }

      const baseSectionLines = baseSectionMap.get(heading);
      if (!baseSectionLines) return null;
      const serverChanged = !areLineGroupsEqual(baseSectionLines, serverSectionLines);
      if (draftDeletedHeadings.includes(heading)) {
        if (serverChanged) return null;
        continue;
      }

      if (!draftSectionLines) return null;
      const draftChanged = !areLineGroupsEqual(baseSectionLines, draftSectionLines);
      if (
        serverChanged
        && draftChanged
        && !areLineGroupsEqual(serverSectionLines, draftSectionLines)
      ) {
        return null;
      }

      if (draftChanged) {
        mergedSectionLines.push(draftSectionLines);
      } else if (serverChanged) {
        hasServerChange = true;
        mergedSectionLines.push(serverSectionLines);
      } else {
        mergedSectionLines.push(baseSectionLines);
      }
    }

    for (const heading of serverDeletedHeadings) {
      const baseSectionLines = baseSectionMap.get(heading);
      const draftSectionLines = draftSectionMap.get(heading);
      if (!baseSectionLines) return null;
      if (
        draftSectionLines
        && !areLineGroupsEqual(baseSectionLines, draftSectionLines)
      ) {
        return null;
      }
    }

    for (const heading of draftAddedHeadings) {
      if (serverHeadingSet.has(heading)) continue;
      const draftSectionLines = draftSectionMap.get(heading);
      if (!draftSectionLines) return null;
      const previousSectionLines = mergedSectionLines[mergedSectionLines.length - 1];
      if (
        previousSectionLines
        && previousSectionLines[previousSectionLines.length - 1]?.trim()
        && draftSectionLines[0]?.trim()
      ) {
        mergedSectionLines.push(['']);
      }
      mergedSectionLines.push(draftSectionLines);
    }

    if (!hasServerChange) return null;

    const mergedContent = [
      ...baseSections.preambleLines,
      ...mergedSectionLines.flat(),
    ].join('\n');
    if (mergedContent === serverContent.replace(/\r\n/g, '\n')) return null;

    return {
      content: mergedContent,
      summary: '合并轨迹：自动合并服务端与草稿的非重叠章节增删',
    };
  };
  const hasMarkdownSectionSetChangeForAutoMerge = (
    baseContent: string,
    serverContent: string,
    draftContent: string
  ): boolean => {
    const baseSections = parseMarkdownSectionsForAutoMerge(baseContent);
    const serverSections = parseMarkdownSectionsForAutoMerge(serverContent);
    const draftSections = parseMarkdownSectionsForAutoMerge(draftContent);
    if (!baseSections || !serverSections || !draftSections) return false;
    return (
      !haveSameSectionSet(baseSections, serverSections)
      || !haveSameSectionSet(baseSections, draftSections)
    );
  };
  const hasMarkdownMovementForAutoMerge = (
    baseContent: string,
    serverContent: string,
    draftContent: string
  ): boolean => {
    const baseSections = parseMarkdownSectionsForAutoMerge(baseContent);
    const serverSections = parseMarkdownSectionsForAutoMerge(serverContent);
    const draftSections = parseMarkdownSectionsForAutoMerge(draftContent);
    if (!baseSections || !serverSections || !draftSections) return false;
    return (
      hasMovementThatShouldBypassSectionRewrite(baseSections, serverSections)
      || hasMovementThatShouldBypassSectionRewrite(baseSections, draftSections)
    );
  };
  const hasMarkdownTableChangeForAutoMerge = (
    baseContent: string,
    serverContent: string,
    draftContent: string
  ): boolean => {
    const baseSections = parseMarkdownSectionsForAutoMerge(baseContent);
    const serverSections = parseMarkdownSectionsForAutoMerge(serverContent);
    const draftSections = parseMarkdownSectionsForAutoMerge(draftContent);
    if (!baseSections || !serverSections || !draftSections) return false;
    if (!hasSameSectionShape(baseSections, serverSections) || !hasSameSectionShape(baseSections, draftSections)) {
      return false;
    }

    const targetHasTableChange = (targetSections: ParsedMarkdownSections): boolean => (
      baseSections.sections.some((baseSection, index) => {
        const targetSection = targetSections.sections[index];
        return hasMarkdownTableLineChangeInSection(baseSection.lines, targetSection.lines);
      })
    );

    return targetHasTableChange(serverSections) || targetHasTableChange(draftSections);
  };
  const hasMarkdownListItemChangeForAutoMerge = (
    baseContent: string,
    serverContent: string,
    draftContent: string
  ): boolean => {
    const baseSections = parseMarkdownSectionsForAutoMerge(baseContent);
    const serverSections = parseMarkdownSectionsForAutoMerge(serverContent);
    const draftSections = parseMarkdownSectionsForAutoMerge(draftContent);
    if (!baseSections || !serverSections || !draftSections) return false;

    const targetHasListItemChange = (targetSections: ParsedMarkdownSections): boolean => (
      baseSections.sections.some((baseSection) => {
        const targetSection = targetSections.sections.find(section => section.heading === baseSection.heading);
        if (!targetSection) return baseSection.lines.some(isMarkdownListItemLine);
        return hasMarkdownListItemLineChangeInSection(baseSection.lines, targetSection.lines);
      })
      || targetSections.sections.some((targetSection) => {
        const baseSection = baseSections.sections.find(section => section.heading === targetSection.heading);
        return !baseSection && targetSection.lines.some(isMarkdownListItemLine);
      })
    );

    return targetHasListItemChange(serverSections) || targetHasListItemChange(draftSections);
  };
  const hasFencedBlockChangeForAutoMerge = (
    baseContent: string,
    serverContent: string,
    draftContent: string
  ): boolean => {
    const baseSections = parseMarkdownSectionsForAutoMerge(baseContent);
    const serverSections = parseMarkdownSectionsForAutoMerge(serverContent);
    const draftSections = parseMarkdownSectionsForAutoMerge(draftContent);
    if (!baseSections || !serverSections || !draftSections) return false;

    const targetHasFencedBlockChange = (targetSections: ParsedMarkdownSections): boolean => (
      baseSections.sections.some((baseSection) => {
        const targetSection = targetSections.sections.find(section => section.heading === baseSection.heading);
        if (!targetSection) return baseSection.lines.some(isFencedBlockBoundaryLine);
        return hasFencedBlockLineChangeInSection(baseSection.lines, targetSection.lines);
      })
      || targetSections.sections.some((targetSection) => {
        const baseSection = baseSections.sections.find(section => section.heading === targetSection.heading);
        return !baseSection && targetSection.lines.some(isFencedBlockBoundaryLine);
      })
    );

    return targetHasFencedBlockChange(serverSections) || targetHasFencedBlockChange(draftSections);
  };
  const hasStructuredBlockReorderForAutoMerge = (
    baseContent: string,
    serverContent: string,
    draftContent: string
  ): boolean => {
    const baseSections = parseMarkdownSectionsForAutoMerge(baseContent);
    const serverSections = parseMarkdownSectionsForAutoMerge(serverContent);
    const draftSections = parseMarkdownSectionsForAutoMerge(draftContent);
    if (!baseSections || !serverSections || !draftSections) return false;

    const hasUnsafeReorder = (targetSections: ParsedMarkdownSections): boolean => {
      const targetSectionMap = buildSectionMap(targetSections);
      return baseSections.sections.some((baseSection) => {
        const targetSectionLines = targetSectionMap.get(baseSection.heading);
        if (!targetSectionLines) return false;
        return hasUnsafeUnitReorder(baseSection.lines, targetSectionLines, baseSection.heading);
      });
    };

    return hasUnsafeReorder(serverSections) || hasUnsafeReorder(draftSections);
  };
  const selectedVersionDiff = useMemo(
    () => selectedVersion
      ? buildLineDiff(selectedVersion.content, artifactContent)
      : [],
    [artifactContent, selectedVersion]
  );
  const selectedVersionRemovedBlocks = useMemo(
    () => buildContiguousDiffBlocks(selectedVersionDiff, 'removed'),
    [selectedVersionDiff]
  );
  const selectedVersionRemovedBlockByStartIndex = useMemo(
    () => new Map(selectedVersionRemovedBlocks.map(block => [block.startIndex, block])),
    [selectedVersionRemovedBlocks]
  );
  const selectedVersionAddedBlocks = useMemo(
    () => buildContiguousDiffBlocks(selectedVersionDiff, 'added'),
    [selectedVersionDiff]
  );
  const selectedVersionAddedBlockByStartIndex = useMemo(
    () => new Map(selectedVersionAddedBlocks.map(block => [block.startIndex, block])),
    [selectedVersionAddedBlocks]
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
  const conflictDraftRemovedBlocks = useMemo(
    () => buildContiguousDiffBlocks(conflictDraftDiff, 'removed'),
    [conflictDraftDiff]
  );
  const conflictDraftRemovedBlockByStartIndex = useMemo(
    () => new Map(conflictDraftRemovedBlocks.map(block => [block.startIndex, block])),
    [conflictDraftRemovedBlocks]
  );
  const conflictDraftModifiedBlocks = useMemo(() => {
    const blocks: Array<{
      removedStartIndex: number;
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

      const removedStartIndex = index;
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
          removedStartIndex,
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
  const conflictDraftModifiedBlockByRemovedStartIndex = useMemo(
    () => new Map(conflictDraftModifiedBlocks.map(block => [block.removedStartIndex, block])),
    [conflictDraftModifiedBlocks]
  );
  const autoMergedConflict = useMemo(
    () => {
      if (!conflictArtifact) return null;
      const sectionRewriteMerge = buildAutoMergedSectionRewriteResult(
        artifactContent,
        conflictArtifact.content,
        editDraft
      );
      if (sectionRewriteMerge) return sectionRewriteMerge;
      const sameSectionParagraphRewriteMerge = buildAutoMergedSameSectionParagraphRewriteResult(
        artifactContent,
        conflictArtifact.content,
        editDraft
      );
      if (sameSectionParagraphRewriteMerge) return sameSectionParagraphRewriteMerge;
      const sameSectionParagraphDeleteRewriteMerge = buildAutoMergedSameSectionParagraphDeleteRewriteResult(
        artifactContent,
        conflictArtifact.content,
        editDraft
      );
      if (sameSectionParagraphDeleteRewriteMerge) return sameSectionParagraphDeleteRewriteMerge;
      const sameSectionParagraphInsertRewriteMerge = buildAutoMergedSameSectionParagraphInsertRewriteResult(
        artifactContent,
        conflictArtifact.content,
        editDraft
      );
      if (sameSectionParagraphInsertRewriteMerge) return sameSectionParagraphInsertRewriteMerge;
      const tableRowReorderMerge = buildAutoMergedTableRowReorderResult(
        artifactContent,
        conflictArtifact.content,
        editDraft
      );
      if (tableRowReorderMerge) return tableRowReorderMerge;
      const listItemReorderMerge = buildAutoMergedListItemReorderResult(
        artifactContent,
        conflictArtifact.content,
        editDraft
      );
      if (listItemReorderMerge) return listItemReorderMerge;
      const fencedBlockLineReorderMerge = buildAutoMergedFencedBlockLineReorderResult(
        artifactContent,
        conflictArtifact.content,
        editDraft
      );
      if (fencedBlockLineReorderMerge) return fencedBlockLineReorderMerge;
      if (hasMarkdownTableChangeForAutoMerge(
        artifactContent,
        conflictArtifact.content,
        editDraft
      ) || hasMarkdownListItemChangeForAutoMerge(
        artifactContent,
        conflictArtifact.content,
        editDraft
      ) || hasFencedBlockChangeForAutoMerge(
        artifactContent,
        conflictArtifact.content,
        editDraft
      )) {
        return null;
      }
      const paragraphMoveMerge = buildAutoMergedParagraphMoveResult(
        artifactContent,
        conflictArtifact.content,
        editDraft
      );
      if (paragraphMoveMerge) return paragraphMoveMerge;
      const crossSectionParagraphMoveMerge = buildAutoMergedCrossSectionParagraphMoveResult(
        artifactContent,
        conflictArtifact.content,
        editDraft
      );
      if (crossSectionParagraphMoveMerge) return crossSectionParagraphMoveMerge;
      const sectionMoveMerge = buildAutoMergedSectionMoveResult(
        artifactContent,
        conflictArtifact.content,
        editDraft
      );
      if (sectionMoveMerge) return sectionMoveMerge;
      const sectionRenameMerge = buildAutoMergedSectionRenameResult(
        artifactContent,
        conflictArtifact.content,
        editDraft
      );
      if (sectionRenameMerge) return sectionRenameMerge;
      const sectionAddDeleteMerge = buildAutoMergedSectionAddDeleteResult(
        artifactContent,
        conflictArtifact.content,
        editDraft
      );
      if (sectionAddDeleteMerge) return sectionAddDeleteMerge;
      if (hasMarkdownSectionSetChangeForAutoMerge(
        artifactContent,
        conflictArtifact.content,
        editDraft
      )) {
        return null;
      }
      if (hasMarkdownMovementForAutoMerge(
        artifactContent,
        conflictArtifact.content,
        editDraft
      )) {
        return null;
      }
      if (hasUnsafeSameSectionParagraphInsertRewriteForAutoMerge(
        artifactContent,
        conflictArtifact.content,
        editDraft
      )) {
        return null;
      }
      return buildAutoMergedInsertionResult(artifactContent, conflictArtifact.content, editDraft);
    },
    [artifactContent, conflictArtifact, editDraft]
  );
  const autoMergeRejectionReason = useMemo(() => {
    if (!conflictArtifact || autoMergedConflict) return null;
    if (hasUnsafeSameSectionParagraphInsertRewriteForAutoMerge(
      artifactContent,
      conflictArtifact.content,
      editDraft
    )) {
      return {
        title: '自动合并暂不可用',
        description: '双方改动涉及同一章节的多处段落，已保留你的草稿，请手工确认后重试保存。',
      };
    }
    if (hasStructuredBlockReorderForAutoMerge(
      artifactContent,
      conflictArtifact.content,
      editDraft
    )) {
      return {
        title: '结构化块重排需人工处理',
        description: '检测到列表项、表格行或代码块位置调整，为避免误合并，请打开对比服务端版本手动确认。',
      };
    }
    return {
      title: '自动合并暂不可用',
      description: '双方改动存在重叠或顺序无法证明安全，已保留你的草稿，请打开对比服务端版本后手工确认。',
    };
  }, [artifactContent, autoMergedConflict, conflictArtifact, editDraft]);

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

  const restoreHistoryBlock = (lineContents: string[]) => {
    if (!selectedVersion) return;

    const blockLines = lineContents.filter(line => line.trim());
    if (blockLines.length === 0) return;

    const currentLines = artifactContent.replace(/\r\n/g, '\n').split('\n');
    const linesToRestore = blockLines.filter(line => !currentLines.includes(line));
    if (linesToRestore.length === 0) return;

    const historyLines = selectedVersion.content.replace(/\r\n/g, '\n').split('\n');
    const historyLineIndex = historyLines.findIndex(line => line === blockLines[0]);
    if (historyLineIndex < 0) return;

    const insertIndex = Math.min(historyLineIndex, currentLines.length);
    applyHistoryLineReview([
      ...currentLines.slice(0, insertIndex),
      ...linesToRestore,
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

  const discardCurrentBlock = (lineContents: string[]) => {
    const blockLines = lineContents.filter(line => line.trim());
    if (blockLines.length === 0) return;

    const nextCurrentLines = artifactContent.replace(/\r\n/g, '\n').split('\n');
    let removedAnyLine = false;
    blockLines.forEach((lineContent) => {
      const currentLineIndex = nextCurrentLines.findIndex(line => line === lineContent);
      if (currentLineIndex < 0) return;
      nextCurrentLines.splice(currentLineIndex, 1);
      removedAnyLine = true;
    });
    if (!removedAnyLine) return;

    applyHistoryLineReview(nextCurrentLines.join('\n'));
  };

  const beginManualEdit = () => {
    setEditDraft(artifactContent);
    setManualEditError(null);
    setConflictVersionNumber(null);
    setConflictArtifact(null);
    setShowConflictDiff(false);
    setIsEditing(true);
    setShowArtifactActionsMenu(false);
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

  const recordArtifactServerBlockRestoredEvent = (lineContents: string[]) => {
    if (!currentStageId) return;
    addArtifactAuditEvent({
      stageId: currentStageId,
      eventType: 'artifact_merge_block_server_restored',
      summary: `合并轨迹：恢复服务端删除块「${buildConflictMergeBlockLabel(lineContents)}」`,
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

  const restoreConflictServerBlock = (lineContents: string[]) => {
    if (!conflictArtifact) return;
    const blockLines = lineContents.filter(line => line.trim());
    if (blockLines.length === 0) return;

    const draftLines = editDraft.replace(/\r\n/g, '\n').split('\n');
    const linesToRestore = blockLines.filter(lineContent => !draftLines.includes(lineContent));
    if (linesToRestore.length === 0) return;

    const serverLines = conflictArtifact.content.replace(/\r\n/g, '\n').split('\n');
    const serverLineIndex = serverLines.findIndex(line => line === blockLines[0]);
    if (serverLineIndex < 0) return;

    const insertIndex = Math.min(serverLineIndex, draftLines.length);
    setEditDraft([
      ...draftLines.slice(0, insertIndex),
      ...linesToRestore,
      ...draftLines.slice(insertIndex),
    ].join('\n'));
    recordArtifactServerBlockRestoredEvent(linesToRestore);
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
    if (!autoMergedConflict || !currentStageId) return;

    setEditDraft(autoMergedConflict.content);
    addArtifactAuditEvent({
      stageId: currentStageId,
      eventType: 'artifact_auto_merge_applied',
      summary: autoMergedConflict.summary,
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

  const resolveCommentFromReview = (commentId: string) => {
    setArtifactCommentStatus(commentId, 'resolved');
    syncArtifactCollaborationState();
  };

  const openCommentsFromReview = () => {
    setShowReviewPanel(false);
    setShowSectionLocks(false);
    setShowComments(true);
  };

  const openSectionLocksFromReview = () => {
    setShowReviewPanel(false);
    setShowComments(false);
    setShowSectionLocks(true);
  };

  const openHistoryFromReview = () => {
    setShowReviewPanel(false);
    openHistory();
  };

  const rebindCurrentStageCommentAnchor = (commentId: string) => {
    const anchorText = captureSelectedArtifactText() ?? selectedArtifactText;
    if (!anchorText) {
      setCommentAnchorRebindErrors((errors) => ({
        ...errors,
        [commentId]: '请先在右侧正文中选中新的批注位置。',
      }));
      return;
    }

    updateArtifactCommentAnchor(commentId, anchorText);
    syncArtifactCollaborationState();
    setCommentAnchorRebindErrors((errors) => {
      const nextErrors = { ...errors };
      delete nextErrors[commentId];
      return nextErrors;
    });
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

  const locateCommentAnchorFromReview = (anchorText: string) => {
    setShowReviewPanel(false);
    locateArtifactCommentAnchor(anchorText);
  };

  const getCommentAnchorStatus = (anchorText: string | null): 'none' | 'active' | 'stale' => {
    const normalizedAnchorText = normalizeCommentAnchorText(anchorText ?? '');
    if (!normalizedAnchorText) return 'none';

    const normalizedArtifactContent = artifactContent.replace(/\s+/g, ' ');
    return normalizedArtifactContent.includes(normalizedAnchorText) ? 'active' : 'stale';
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
      sectionAnchor: section.anchor,
      content: section.content,
    });
    syncArtifactCollaborationState();
  };

  const unlockSection = (lockId: string) => {
    removeArtifactSectionLock(lockId);
    syncArtifactCollaborationState();
  };

  const regenerateSection = (section: ArtifactSection) => {
    void handleRegenerateArtifactSection({
      heading: section.heading,
      sectionAnchor: section.anchor,
      displayTitle: section.displayTitle,
    });
  };

  const getSectionLock = (section: ArtifactSection) => (
    currentStageSectionLocks.find(lock => (
      lock.sectionAnchor
        ? lock.sectionAnchor === section.anchor
        : lock.heading === section.heading
    ))
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
    attachVisualDiagnosticAnchors = false,
    deferMermaidRender = false,
    mermaidBlockStartIndex = 0,
    structuredVisualBlockStartIndex = 0
  ): Components => {
    let mermaidBlockCounter = mermaidBlockStartIndex;
    let structuredVisualBlockCounter = structuredVisualBlockStartIndex;
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
      renderMermaid: attachVisualDiagnosticAnchors || deferMermaidRender
        ? ({ blockIndex, element }) => {
          const mermaidElement = deferMermaidRender
            ? (
              <div className="my-6 flex w-full justify-center overflow-x-auto">
                <div className="flex max-w-xl items-center gap-3 rounded-lg border border-sky-500/30 bg-sky-500/10 px-4 py-3 text-sm text-sky-200">
                  <span className="h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-sky-300 border-t-transparent" aria-hidden="true" />
                  <span>
                    <span className="block font-medium text-sky-100">图表将在产出物稳定后绘制</span>
                    <span className="mt-1 block text-xs text-sky-200/75">模型仍在输出图表内容，已暂停实时绘制以保持页面响应。</span>
                  </span>
                </div>
              </div>
            )
            : element;

          if (!attachVisualDiagnosticAnchors) {
            return mermaidElement;
          }

          const diagnosticId = buildVisualDiagnosticId('mermaid', blockIndex);
          return (
            <div
              data-artifact-visual-diagnostic-id={diagnosticId}
              data-artifact-visual-focused={activeVisualDiagnosticId === diagnosticId ? 'true' : undefined}
              className={getVisualDiagnosticContainerClass(diagnosticId)}
            >
              {mermaidElement}
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

  const markdownPreviewRenderVersionKey = [
    activeCommentAnchorText ?? '',
    activeVisualDiagnosticId ?? '',
    currentStageId ?? '',
    isGenerating ? 'defer-mermaid' : 'render-mermaid',
  ].join('|');
  const readOnlyMarkdownComponents = createArtifactMarkdownComponents();

  return (
    <section className="flex h-full min-h-0 w-full flex-col overflow-hidden bg-[#0B0F17] text-gray-300 relative shadow-2xl bg-grid-pattern lg:w-[60%]">
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
          <div className="relative">
            <button
              type="button"
              onMouseDown={captureSelectedArtifactText}
              onClick={() => {
                captureSelectedArtifactText();
                setShowArtifactActionsMenu((current) => !current);
              }}
              aria-expanded={showArtifactActionsMenu}
              aria-haspopup="menu"
              aria-label="更多产物操作"
              className={`p-1.5 rounded transition-colors ${showArtifactActionsMenu ? 'bg-white/10 text-white' : 'text-slate-400 hover:text-white hover:bg-white/5'}`}
              title="更多产物操作"
            >
              <MoreHorizontal className="w-4 h-4" />
            </button>
            {showArtifactActionsMenu && (
              <div
                className="absolute right-0 top-full z-20 mt-2 w-44 overflow-hidden rounded-lg border border-[#1e293b] bg-[#0f172a] py-1 shadow-xl"
                role="menu"
              >
                <button
                  type="button"
                  onClick={() => {
                    setShowReviewPanel((current) => !current);
                    setShowArtifactActionsMenu(false);
                    setShowComments(false);
                    setShowSectionLocks(false);
                  }}
                  aria-label="审阅"
                  className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs font-semibold text-slate-200 hover:bg-white/5"
                  role="menuitem"
                >
                  <GitCompare className="h-3.5 w-3.5 text-slate-400" />
                  审阅
                </button>
                <button
                  type="button"
                  onClick={() => {
                    captureSelectedArtifactText();
                    setShowComments((current) => !current);
                    setShowArtifactActionsMenu(false);
                    setShowReviewPanel(false);
                    setShowSectionLocks(false);
                  }}
                  aria-label="批注"
                  className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs font-semibold text-slate-200 hover:bg-white/5"
                  role="menuitem"
                >
                  <MessageSquare className="h-3.5 w-3.5 text-slate-400" />
                  批注
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowSectionLocks((current) => !current);
                    setShowArtifactActionsMenu(false);
                    setShowReviewPanel(false);
                    setShowComments(false);
                  }}
                  aria-label="章节锁定"
                  className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs font-semibold text-slate-200 hover:bg-white/5"
                  role="menuitem"
                >
                  <Lock className="h-3.5 w-3.5 text-slate-400" />
                  章节锁定
                </button>
                <div className="my-1 h-px bg-[#1e293b]" />
                <button
                  type="button"
                  onClick={() => handleDownload('markdown')}
                  aria-label="下载 Markdown"
                  className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs font-semibold text-slate-200 hover:bg-white/5"
                  role="menuitem"
                >
                  <Download className="h-3.5 w-3.5 text-slate-400" />
                  下载 Markdown
                </button>
                <button
                  type="button"
                  onClick={() => handleDownload('word')}
                  aria-label="下载 Word"
                  className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs font-semibold text-slate-200 hover:bg-white/5"
                  role="menuitem"
                >
                  <Download className="h-3.5 w-3.5 text-slate-400" />
                  下载 Word
                </button>
                <button
                  onClick={() => handleDownload('pdf')}
                  type="button"
                  aria-label="下载 PDF"
                  className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs font-semibold text-slate-200 hover:bg-white/5"
                  role="menuitem"
                >
                  <Download className="h-3.5 w-3.5 text-slate-400" />
                  下载 PDF
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="relative z-0 min-h-0 flex-1 overflow-y-auto p-8 custom-scrollbar md:px-16">
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
        {isStoryHandoffPacketStage && (
          <section
            className="mx-auto mb-5 max-w-4xl rounded-lg border border-[#1e293b] bg-[#0f172a] p-4 shadow-xl"
            aria-label="单故事需求包"
          >
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold text-slate-100">单故事需求包</h3>
                <p className="mt-1 text-xs leading-relaxed text-slate-500">
                  从当前 ready story 生成可复制的 AI Coding 需求输入。
                </p>
              </div>
              {isLoadingStoryHandoff && (
                <span className="rounded-md border border-sky-400/20 bg-sky-400/10 px-2 py-1 text-[11px] font-semibold text-sky-100">
                  加载中
                </span>
              )}
            </div>
            {storyHandoffError && (
              <div className="mt-3 rounded-md border border-red-400/20 bg-red-500/10 px-3 py-2 text-xs font-medium text-red-100">
                {storyHandoffError}
              </div>
            )}
            {!isLoadingStoryHandoff && !storyHandoffError && storyHandoffCandidates.length === 0 && (
              <p className="mt-3 text-xs text-slate-500">
                当前阶段还没有可生成需求包的 ready story。
              </p>
            )}
            {storyHandoffCandidates.length > 0 && (
              <div className="mt-3 space-y-2">
                {storyHandoffCandidates.map((candidate) => {
                  const packet = storyHandoffPacketByStoryId.get(candidate.storyId);
                  const isCreating = creatingStoryPacketId === candidate.storyId;
                  return (
                    <div
                      key={candidate.storyId}
                      className="rounded-md border border-[#1e293b] bg-[#020617] px-3 py-3"
                    >
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div className="min-w-0 flex-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="text-xs font-bold text-blue-200">{candidate.storyId}</span>
                            {packet && (
                              <span className="rounded-md border border-emerald-400/20 bg-emerald-400/10 px-2 py-0.5 text-[11px] font-semibold text-emerald-100">
                                {candidate.storyId} · v{packet.packet.sourceArtifactVersion}
                              </span>
                            )}
                            <span className="text-sm font-semibold text-slate-100">{candidate.title}</span>
                          </div>
                          <p className="mt-1 text-xs leading-relaxed text-slate-400">
                            {candidate.userValue}
                          </p>
                          <p className="mt-1 text-[11px] text-slate-500">
                            {candidate.readyReason}
                          </p>
                          {packet?.isStale && (
                            <p className="mt-2 text-[11px] font-medium text-amber-200">
                              该需求包可能基于旧版需求，请重新生成后再交给 AI Coding。
                            </p>
                          )}
                          {copiedStoryPacketId === candidate.storyId && (
                            <p className="mt-2 text-[11px] font-semibold text-emerald-200">
                              已复制 {candidate.storyId}
                            </p>
                          )}
                        </div>
                        <div className="flex shrink-0 items-center gap-2">
                          {packet ? (
                            <button
                              type="button"
                              onClick={() => handleCopyStoryHandoffPacket(candidate.storyId, packet.packet)}
                              className="rounded-md border border-emerald-400/20 px-3 py-1.5 text-xs font-semibold text-emerald-100 transition-colors hover:bg-emerald-400/10"
                            >
                              复制 {candidate.storyId} 需求包
                            </button>
                          ) : (
                            <button
                              type="button"
                              onClick={() => handleCreateStoryHandoffPacket(candidate.storyId)}
                              disabled={isCreating}
                              className="rounded-md bg-blue-600 px-3 py-1.5 text-xs font-bold text-white transition-colors hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
                            >
                              {isCreating ? `生成 ${candidate.storyId} 中` : `生成 ${candidate.storyId} 需求包`}
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </section>
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
                    {autoMergeRejectionReason && (
                      <span className="rounded-md border border-amber-300/20 bg-amber-400/10 px-2 py-1 text-[11px] text-amber-100">
                        <span className="font-bold">{autoMergeRejectionReason.title}</span>
                        <span className="ml-1 text-amber-50/80">{autoMergeRejectionReason.description}</span>
                      </span>
                    )}
                    {conflictArtifact && (
                      <div className="ml-auto flex shrink-0 items-center gap-2">
                        {autoMergedConflict && (
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
                            {line.type === 'removed'
                              && line.content.trim()
                              && conflictDraftRemovedBlockByStartIndex.has(index)
                              && !conflictDraftModifiedBlockByRemovedStartIndex.has(index) && (
                                <span className="flex shrink-0 items-center gap-1">
                                  <button
                                    type="button"
                                    onClick={() => {
                                      const block = conflictDraftRemovedBlockByStartIndex.get(index);
                                      if (block) restoreConflictServerBlock(block.lines);
                                    }}
                                    aria-label={`恢复服务端变更块：${conflictDraftRemovedBlockByStartIndex.get(index)?.label ?? line.content}`}
                                    className="rounded border border-rose-300/20 px-1.5 py-0.5 text-[10px] font-semibold text-rose-100 hover:bg-rose-300/10"
                                  >
                                    恢复服务端块
                                  </button>
                                </span>
                              )}
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
            markdownPreviewChunks.map((chunk) => (
              <RenderedMarkdownSection
                key={chunk.sectionKey}
                {...chunk}
                components={createArtifactMarkdownComponents(
                  handleMermaidRetry,
                  activeCommentAnchorText,
                  true,
                  true,
                  isGenerating,
                  chunk.mermaidBlockStartIndex,
                  chunk.structuredVisualBlockStartIndex,
                )}
                renderVersionKey={markdownPreviewRenderVersionKey}
              />
            ))
          ) : (
            <pre className="text-sm font-mono text-slate-300 whitespace-pre-wrap break-words bg-[#0f172a] p-6 rounded-xl border border-[#1e293b]">
              {displayContent}
            </pre>
          )}
        </div>
      </div>

      {showReviewPanel && (
        <aside className="absolute right-6 top-20 z-20 w-[min(400px,calc(100%-3rem))] rounded-xl border border-[#1e293b] bg-[#0f172a] shadow-2xl">
          <div className="flex items-center justify-between border-b border-[#1e293b] px-4 py-3">
            <div>
              <h3 className="text-sm font-semibold text-white">产物审阅</h3>
              <p className="text-xs text-slate-500">当前阶段 {currentStageId}</p>
            </div>
            <button
              onClick={() => setShowReviewPanel(false)}
              className="rounded p-1 text-slate-400 hover:bg-white/10 hover:text-white"
              title="关闭审阅"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
          <div className="max-h-[70vh] space-y-4 overflow-auto p-4">
            <section className="space-y-3 rounded-lg border border-[#1e293b] bg-[#020617] p-3">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h4 className="text-xs font-bold uppercase tracking-wide text-slate-400">质量治理</h4>
                  <p className="mt-1 text-xs leading-relaxed text-slate-500">{workflowQualitySummary.summary}</p>
                </div>
                <div className="shrink-0 text-right">
                  <div className="text-lg font-bold text-slate-100">质量分 {workflowQualitySummary.score}</div>
                  <div className="text-[10px] font-semibold text-slate-500">{workflowQualitySummary.statusLabel}</div>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-2">
                <div className="rounded border border-emerald-400/20 bg-emerald-400/5 p-2 text-center text-xs text-emerald-200">
                  通过 {workflowQualitySummary.passedCount}
                </div>
                <div className="rounded border border-amber-400/20 bg-amber-400/5 p-2 text-center text-xs text-amber-200">
                  警告 {workflowQualitySummary.warningCount}
                </div>
                <div className="rounded border border-red-400/20 bg-red-400/5 p-2 text-center text-xs text-red-200">
                  失败 {workflowQualitySummary.failedCount}
                </div>
              </div>
              <div className="space-y-2">
                {workflowQualitySummary.checks.slice(0, 6).map((check) => (
                  <article key={check.id} className="rounded border border-[#1e293b] bg-black/10 p-2">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs font-semibold text-slate-200">{check.label}</span>
                      <span className="text-[10px] font-bold text-slate-500">{check.statusLabel}</span>
                    </div>
                    <p className="mt-1 text-[11px] leading-relaxed text-slate-500">{check.evidence}</p>
                    <p className="mt-1 text-[11px] leading-relaxed text-slate-400">{check.impact}</p>
                  </article>
                ))}
              </div>
              <div className="rounded border border-[#1e293b] bg-black/10 p-2">
                <div className="text-[11px] font-bold uppercase tracking-wide text-slate-500">待处理项</div>
                {workflowQualitySummary.actionItems.length === 0 ? (
                  <p className="mt-1 text-xs text-slate-500">当前没有阻断项。</p>
                ) : (
                  <ul className="mt-2 space-y-1">
                    {workflowQualitySummary.actionItems.map((item) => (
                      <li key={item} className="text-xs leading-relaxed text-slate-300">- {item}</li>
                    ))}
                  </ul>
                )}
              </div>
              {artifactQualitySummary.missingInfoItems.length > 0 && (
                <div className="space-y-2 border-t border-[#1e293b] pt-3">
                  <div>
                    <h4 className="text-xs font-bold uppercase tracking-wide text-slate-400">缺失信息清单</h4>
                    <p className="mt-1 text-[11px] text-slate-500">按阻断性列出当前阶段需要用户处理的事项</p>
                  </div>
                  {artifactQualitySummary.missingInfoItems.map((item) => (
                    <article
                      key={item.id}
                      className={`rounded-md border p-3 ${
                        item.blocking
                          ? 'border-rose-400/20 bg-rose-400/5'
                          : 'border-amber-400/20 bg-amber-400/5'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <span className={`inline-flex rounded-full border px-2 py-0.5 text-[10px] font-bold ${
                            item.blocking
                              ? 'border-rose-300/30 bg-rose-300/10 text-rose-100'
                              : 'border-amber-300/30 bg-amber-300/10 text-amber-100'
                          }`}>
                            {item.blocking ? '阻断' : '提醒'}
                          </span>
                          <p className="mt-2 text-xs font-semibold text-slate-100">缺失项：{item.title}</p>
                          <p className="mt-1 text-[11px] leading-relaxed text-slate-500">{item.reason}</p>
                          <p className="mt-1 text-[11px] leading-relaxed text-slate-300">
                            <span className="font-semibold text-slate-200">下一步：</span>
                            {item.nextAction}
                          </p>
                        </div>
                        {item.actionDiagnosticId && (
                          <button
                            type="button"
                            onClick={() => focusArtifactVisualDiagnostic(item.actionDiagnosticId ?? '')}
                            className="shrink-0 rounded border border-blue-400/30 px-2 py-1 text-[10px] font-semibold text-blue-200 transition-colors hover:bg-blue-400/10"
                            aria-label={`定位缺失信息：${item.title}`}
                          >
                            定位
                          </button>
                        )}
                      </div>
                    </article>
                  ))}
                </div>
              )}
            </section>

            <div className="grid grid-cols-3 gap-2">
              <div className="rounded-lg border border-[#1e293b] bg-[#020617] p-3">
                <div className="text-lg font-bold text-amber-200">{currentStageOpenComments.length}</div>
                <div className="mt-1 text-[11px] text-slate-500">
                  {currentStageOpenComments.length} 条未解决批注
                </div>
              </div>
              <div className="rounded-lg border border-[#1e293b] bg-[#020617] p-3">
                <div className="text-lg font-bold text-blue-200">{currentStageSectionLocks.length}</div>
                <div className="mt-1 text-[11px] text-slate-500">
                  {currentStageSectionLocks.length} 个锁定章节
                </div>
              </div>
              <div className="rounded-lg border border-[#1e293b] bg-[#020617] p-3">
                <div className="text-lg font-bold text-emerald-200">{recentStageAuditEvents.length}</div>
                <div className="mt-1 text-[11px] text-slate-500">
                  {recentStageAuditEvents.length} 条近期轨迹
                </div>
              </div>
            </div>

            <section className="space-y-2">
              <h4 className="text-xs font-bold uppercase tracking-wide text-slate-400">未解决批注</h4>
              {currentStageOpenComments.length === 0 ? (
                <p className="rounded-lg border border-[#1e293b] bg-[#020617] p-3 text-xs text-slate-500">
                  当前阶段没有未解决批注。
                </p>
              ) : (
                currentStageOpenComments.map((comment) => {
                  const anchorStatus = getCommentAnchorStatus(comment.anchorText);
                  return (
                    <article key={comment.id} className="rounded-lg border border-amber-400/20 bg-amber-400/5 p-3">
                      <p className="break-words text-sm leading-relaxed text-slate-100">{comment.content}</p>
                      <blockquote className="mt-2 border-l-2 border-amber-300/40 pl-3 text-xs leading-relaxed text-slate-500">
                        {comment.artifactExcerpt || '当前产出物'}
                      </blockquote>
                      <div className="mt-3 flex flex-wrap gap-2">
                        <button
                          type="button"
                          onClick={() => resolveCommentFromReview(comment.id)}
                          className="rounded border border-emerald-400/30 px-2 py-1 text-[10px] font-semibold text-emerald-200 transition-colors hover:bg-emerald-400/10"
                          aria-label={`标记已解决：${comment.content}`}
                        >
                          标记已解决
                        </button>
                        {anchorStatus === 'active' && comment.anchorText && (
                          <button
                            type="button"
                            onClick={() => locateCommentAnchorFromReview(comment.anchorText ?? '')}
                            className="rounded border border-blue-400/30 px-2 py-1 text-[10px] font-semibold text-blue-200 transition-colors hover:bg-blue-400/10"
                            aria-label={`定位正文：${comment.content}`}
                          >
                            定位正文
                          </button>
                        )}
                        {anchorStatus === 'stale' && (
                          <button
                            type="button"
                            onClick={openCommentsFromReview}
                            className="rounded border border-amber-300/30 px-2 py-1 text-[10px] font-semibold text-amber-100 transition-colors hover:bg-amber-300/10"
                            aria-label={`处理失效锚点：${comment.content}`}
                          >
                            处理失效锚点
                          </button>
                        )}
                      </div>
                      {anchorStatus === 'stale' && (
                        <div className="mt-2 inline-flex rounded border border-amber-400/20 bg-amber-400/10 px-2 py-1 text-[10px] font-bold text-amber-200">
                          锚点已失效
                        </div>
                      )}
                    </article>
                  );
                })
              )}
            </section>

            <section className="space-y-2">
              <h4 className="text-xs font-bold uppercase tracking-wide text-slate-400">锁定章节</h4>
              {currentStageSectionLocks.length === 0 ? (
                <p className="rounded-lg border border-[#1e293b] bg-[#020617] p-3 text-xs text-slate-500">
                  当前阶段没有锁定章节。
                </p>
              ) : (
                currentStageSectionLocks.map((lock) => (
                  <article key={lock.id} className="rounded-lg border border-blue-400/20 bg-blue-400/5 p-3">
                    <p className="text-sm font-semibold text-blue-100">{lock.heading}</p>
                    <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-slate-500">
                      {lock.content.replace(lock.heading, '').trim() || '空章节'}
                    </p>
                    <button
                      type="button"
                      onClick={openSectionLocksFromReview}
                      className="mt-3 rounded border border-blue-400/30 px-2 py-1 text-[10px] font-semibold text-blue-100 transition-colors hover:bg-blue-400/10"
                      aria-label={`管理锁定章节：${lock.heading}`}
                    >
                      管理锁定章节
                    </button>
                  </article>
                ))
              )}
            </section>

            <section className="space-y-2">
              <h4 className="text-xs font-bold uppercase tracking-wide text-slate-400">最近轨迹</h4>
              {recentStageAuditEvents.length === 0 ? (
                <p className="rounded-lg border border-[#1e293b] bg-[#020617] p-3 text-xs text-slate-500">
                  当前阶段还没有合并或协作轨迹。
                </p>
              ) : (
                recentStageAuditEvents.map((event) => (
                  <article key={`${event.createdAt}-${event.summary}`} className="rounded-lg border border-[#1e293b] bg-[#020617] p-3">
                    <p className="text-xs leading-relaxed text-slate-200">{event.summary}</p>
                    <p className="mt-1 text-[10px] text-slate-600">{new Date(event.createdAt).toLocaleString()}</p>
                  </article>
                ))
              )}
            </section>

            <section className="rounded-lg border border-[#1e293b] bg-[#020617] p-3">
              <h4 className="text-xs font-bold uppercase tracking-wide text-slate-400">最近版本</h4>
              <p className="mt-2 text-xs text-slate-300">
                {latestStageArtifactVersion
                  ? `最近版本：${latestStageArtifactVersion.id}`
                  : '当前阶段还没有历史版本'}
              </p>
              {latestStageArtifactVersion && (
                <button
                  type="button"
                  onClick={openHistoryFromReview}
                  className="mt-3 rounded border border-slate-500/40 px-2 py-1 text-[10px] font-semibold text-slate-200 transition-colors hover:bg-white/10"
                  aria-label={`查看最近版本：${latestStageArtifactVersion.id}`}
                >
                  查看最近版本
                </button>
              )}
            </section>
          </div>
        </aside>
      )}

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
                  {currentStageComments.map((comment) => {
                    const anchorStatus = getCommentAnchorStatus(comment.anchorText);
                    return (
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
                      {anchorStatus === 'active' && comment.anchorText && (
                        <button
                          type="button"
                          onClick={() => locateArtifactCommentAnchor(comment.anchorText ?? '')}
                          className="mt-2 rounded border border-blue-500/30 px-2 py-1 text-[10px] font-semibold text-blue-200 transition-colors hover:bg-blue-500/10"
                        >
                          定位正文
                        </button>
                      )}
                      {anchorStatus === 'stale' && (
                        <div className="mt-2 rounded border border-amber-400/20 bg-amber-400/10 px-2 py-1.5">
                          <div className="text-[10px] font-bold text-amber-200">锚点已失效</div>
                          <div className="mt-0.5 text-[10px] leading-relaxed text-amber-100/80">
                            正文已变化，请重新确认这条批注的位置。
                          </div>
                          <button
                            type="button"
                            onClick={() => rebindCurrentStageCommentAnchor(comment.id)}
                            className="mt-2 rounded border border-amber-300/30 px-2 py-1 text-[10px] font-semibold text-amber-100 transition-colors hover:bg-amber-300/10"
                          >
                            重新绑定选区
                          </button>
                          {commentAnchorRebindErrors[comment.id] && (
                            <div className="mt-1 text-[10px] leading-relaxed text-amber-100">
                              {commentAnchorRebindErrors[comment.id]}
                            </div>
                          )}
                        </div>
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
                    );
                  })}
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
                const lock = getSectionLock(section);
                return (
                  <article key={section.anchor} className="rounded-lg border border-[#1e293b] bg-[#020617] p-3">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <h4 className="truncate text-sm font-semibold text-slate-100">{section.displayTitle}</h4>
                        <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-slate-500">
                          {section.content.replace(section.heading, '').trim() || '空章节'}
                        </p>
                      </div>
                      <div className="flex shrink-0 flex-col items-end gap-2">
                        <button
                          onClick={() => {
                            if (lock || isGenerating) return;
                            regenerateSection(section);
                          }}
                          disabled={Boolean(lock) || isGenerating}
                          className="inline-flex items-center gap-1 rounded-md border border-sky-400/20 px-2 py-1 text-xs font-semibold text-sky-200 hover:bg-sky-400/10 disabled:cursor-not-allowed disabled:opacity-40"
                          aria-label={`重生成章节 ${section.displayTitle}`}
                          title={lock ? '章节已锁定，请先解锁后再重生成' : isGenerating ? '正在生成中' : '重生成章节'}
                        >
                          <RefreshCw className="h-3.5 w-3.5" />
                          重生成
                        </button>
                        {lock ? (
                          <button
                            onClick={() => unlockSection(lock.id)}
                            className="inline-flex items-center gap-1 rounded-md border border-amber-400/20 px-2 py-1 text-xs font-semibold text-amber-200 hover:bg-amber-400/10"
                            aria-label={`解除章节锁定 ${section.displayTitle}`}
                            title="解除章节锁定"
                          >
                            <Unlock className="h-3.5 w-3.5" />
                            解锁
                          </button>
                        ) : (
                          <button
                            onClick={() => lockSection(section)}
                            className="inline-flex items-center gap-1 rounded-md bg-blue-600 px-2 py-1 text-xs font-semibold text-white hover:bg-blue-500"
                            aria-label={`锁定 ${section.displayTitle}`}
                          >
                            <Lock className="h-3.5 w-3.5" />
                            锁定 {section.displayTitle}
                          </button>
                        )}
                      </div>
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
                        const removedBlock = selectedVersionRemovedBlockByStartIndex.get(index);
                        const addedBlock = selectedVersionAddedBlockByStartIndex.get(index);
                        return (
                          <div
                            key={`${entry.type}-${index}`}
                            className={`flex items-center gap-2 whitespace-pre-wrap px-4 py-1.5 ${entry.type === 'added' ? 'bg-emerald-500/10 text-emerald-200' : entry.type === 'removed' ? 'bg-red-500/10 text-red-200' : 'text-slate-400'}`}
                          >
                            <span className="min-w-0 flex-1">{prefix}{entry.content}</span>
                            {removedBlock && (
                              <button
                                type="button"
                                onClick={() => restoreHistoryBlock(removedBlock.lines)}
                                aria-label={`恢复变更块：${removedBlock.label}`}
                                className="shrink-0 rounded border border-red-300/20 px-1.5 py-0.5 text-[10px] font-semibold text-red-100 hover:bg-red-300/10"
                              >
                                恢复块
                              </button>
                            )}
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
                            {addedBlock && (
                              <button
                                type="button"
                                onClick={() => discardCurrentBlock(addedBlock.lines)}
                                aria-label={`丢弃变更块：${addedBlock.label}`}
                                className="shrink-0 rounded border border-emerald-300/20 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-100 hover:bg-emerald-300/10"
                              >
                                丢弃块
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
