import type { ArtifactSectionChange, ArtifactSectionChangeKind } from './types';

export type ArtifactMarkdownSection = {
  level: number;
  heading: string;
  title: string;
  displayTitle: string;
  anchor: string;
  content: string;
};

type UnsafeReason = NonNullable<ArtifactSectionChange['unsafeReason']>;

const normalizeMarkdown = (content: string): string => content.replace(/\r\n/g, '\n');

const isFenceBoundary = (line: string): boolean => /^\s*```/.test(line);

const headingPattern = /^(#{1,6})\s+(.+?)\s*$/;

const detectUnsafeReason = (content: string): UnsafeReason | undefined => {
  const lines = content.split('\n');
  if (lines.some(line => /```\s*ai4se-visual\b/.test(line))) return 'structured_visual';
  if (lines.some(isFenceBoundary)) return 'fenced_block';
  if (lines.some(line => /^\s*\|.*\|\s*$/.test(line))) return 'markdown_table';
  if (lines.some(line => /^[-*+]\s+/.test(line) || /^\d+\.\s+/.test(line))) return 'markdown_list';
  return undefined;
};

export const extractArtifactSections = (content: string): ArtifactMarkdownSection[] => {
  const lines = normalizeMarkdown(content).split('\n');
  const rawSections: Array<Omit<ArtifactMarkdownSection, 'displayTitle' | 'anchor'> & { start: number }> = [];
  let inFence = false;
  let currentStart = -1;
  let currentHeading = '';
  let currentTitle = '';
  let currentLevel = 0;

  lines.forEach((line, index) => {
    if (isFenceBoundary(line)) {
      inFence = !inFence;
      return;
    }
    if (inFence) return;

    const match = line.match(headingPattern);
    if (!match) return;

    if (currentStart >= 0) {
      rawSections.push({
        start: currentStart,
        level: currentLevel,
        heading: currentHeading,
        title: currentTitle,
        content: lines.slice(currentStart, index).join('\n').trim(),
      });
    }

    currentStart = index;
    currentHeading = line.trim();
    currentLevel = match[1].length;
    currentTitle = match[2].trim();
  });

  if (currentStart >= 0) {
    rawSections.push({
      start: currentStart,
      level: currentLevel,
      heading: currentHeading,
      title: currentTitle,
      content: lines.slice(currentStart).join('\n').trim(),
    });
  }

  const duplicateCounts = rawSections.reduce<Record<string, number>>((counts, section) => {
    counts[section.title] = (counts[section.title] ?? 0) + 1;
    return counts;
  }, {});
  const occurrenceCounts: Record<string, number> = {};

  return rawSections.map((section) => {
    const occurrence = (occurrenceCounts[section.title] ?? 0) + 1;
    occurrenceCounts[section.title] = occurrence;
    const isDuplicateTitle = duplicateCounts[section.title] > 1;
    return {
      level: section.level,
      heading: section.heading,
      title: section.title,
      displayTitle: isDuplicateTitle ? `${section.title} #${occurrence}` : section.title,
      anchor: `h${section.level}:${section.title}:${occurrence}`,
      content: section.content,
    };
  });
};

const buildChange = (
  kind: ArtifactSectionChangeKind,
  section: ArtifactMarkdownSection,
): ArtifactSectionChange => {
  const unsafeReason = detectUnsafeReason(section.content);
  return {
    kind,
    anchor: section.anchor,
    title: section.title,
    displayTitle: section.displayTitle,
    safeForPatch: unsafeReason === undefined,
    ...(unsafeReason ? { unsafeReason } : {}),
  };
};

export const buildArtifactSectionChangeIndex = (
  previousContent: string,
  currentContent: string,
): ArtifactSectionChange[] => {
  const previousSections = extractArtifactSections(previousContent);
  const currentSections = extractArtifactSections(currentContent);
  if (previousSections.length === 0 || currentSections.length === 0) return [];

  const previousByAnchor = new Map(previousSections.map(section => [section.anchor, section]));
  const currentByAnchor = new Map(currentSections.map(section => [section.anchor, section]));
  const changes: ArtifactSectionChange[] = [];

  currentSections.forEach((section) => {
    const previous = previousByAnchor.get(section.anchor);
    if (!previous) {
      changes.push(buildChange('added', section));
      return;
    }
    if (previous.content !== section.content) {
      changes.push(buildChange('modified', section));
    }
  });

  previousSections.forEach((section) => {
    if (!currentByAnchor.has(section.anchor)) {
      changes.push(buildChange('removed', section));
    }
  });

  return changes;
};
