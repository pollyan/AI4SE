import type {
    ArtifactSectionChange,
    ArtifactSectionPatch,
    ArtifactSectionPatchApplyResult,
    ArtifactSectionPatchFallbackReason,
    ArtifactSectionLock,
} from './types';

export type ArtifactMarkdownSection = {
    heading: string;
    title: string;
    displayTitle: string;
    anchor: string;
    content: string;
    level: number;
    startLine: number;
    endLine: number;
};

export type ArtifactSectionTarget = {
    heading: string;
    sectionAnchor?: string | null;
    displayTitle?: string;
};

export type ArtifactSectionRegenerationErrorCode =
    | 'TARGET_LOCKED'
    | 'ORIGINAL_TARGET_MISSING'
    | 'GENERATED_TARGET_MISSING';

export class ArtifactSectionRegenerationError extends Error {
    code: ArtifactSectionRegenerationErrorCode;

    constructor(code: ArtifactSectionRegenerationErrorCode, message: string) {
        super(message);
        this.name = 'ArtifactSectionRegenerationError';
        this.code = code;
    }
}

export function parseArtifactMarkdownSections(markdown: string): ArtifactMarkdownSection[] {
    const lines = markdown.split(/\r?\n/);
    const rawSections: Array<{
        heading: string;
        title: string;
        content: string;
        level: number;
        startLine: number;
        endLine: number;
    }> = [];
    let currentStart = -1;
    let currentHeading = '';

    lines.forEach((line, index) => {
        if (!/^#{1,3}\s+/.test(line)) return;
        if (currentStart >= 0) {
            const level = currentHeading.match(/^(#{1,3})\s+/)?.[1].length ?? 1;
            rawSections.push({
                heading: currentHeading,
                title: currentHeading.replace(/^#{1,3}\s+/, ''),
                content: lines.slice(currentStart, index).join('\n').trim(),
                level,
                startLine: currentStart,
                endLine: index,
            });
        }
        currentStart = index;
        currentHeading = line;
    });

    if (currentStart >= 0) {
        const level = currentHeading.match(/^(#{1,3})\s+/)?.[1].length ?? 1;
        rawSections.push({
            heading: currentHeading,
            title: currentHeading.replace(/^#{1,3}\s+/, ''),
            content: lines.slice(currentStart).join('\n').trim(),
            level,
            startLine: currentStart,
            endLine: lines.length,
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
            ...section,
            displayTitle: isDuplicateTitle ? `${section.title} #${occurrence}` : section.title,
            anchor: `h${section.level}:${section.title}:${occurrence}`,
        };
    });
}

export function findArtifactSection(
    sections: ArtifactMarkdownSection[],
    target: ArtifactSectionTarget
): ArtifactMarkdownSection | undefined {
    return sections.find(section => (
        target.sectionAnchor
            ? section.anchor === target.sectionAnchor
            : section.heading === target.heading
    ));
}

export function findArtifactSectionLock(
    section: ArtifactSectionTarget,
    locks: ArtifactSectionLock[]
): ArtifactSectionLock | undefined {
    return locks.find(lock => (
        lock.sectionAnchor && section.sectionAnchor
            ? lock.sectionAnchor === section.sectionAnchor
            : lock.heading === section.heading
    ));
}

export function replaceArtifactSectionContent(
    markdown: string,
    section: ArtifactMarkdownSection,
    replacementContent: string
): string {
    const lines = markdown.split(/\r?\n/);
    const replacementLines = replacementContent.split(/\r?\n/);
    const shouldPreserveHeadingSeparator = (
        lines[section.endLine - 1] === ''
        && /^#{1,3}\s+/.test(lines[section.endLine] ?? '')
        && replacementLines[replacementLines.length - 1] !== ''
    );
    return [
        ...lines.slice(0, section.startLine),
        ...replacementLines,
        ...(shouldPreserveHeadingSeparator ? [''] : []),
        ...lines.slice(section.endLine),
    ].join('\n');
}

const buildSectionMap = (
    sections: ArtifactMarkdownSection[]
): Map<string, ArtifactMarkdownSection> => (
    new Map(sections.map(section => [section.anchor, section]))
);

const toSectionChange = (
    kind: ArtifactSectionChange['kind'],
    section: ArtifactMarkdownSection
): ArtifactSectionChange => ({
    kind,
    title: section.title,
    anchor: section.anchor,
    heading: section.heading,
});

type ArtifactSectionChangeCandidate = {
    kind: ArtifactSectionChange['kind'];
    section: ArtifactMarkdownSection;
    previousSection?: ArtifactMarkdownSection;
    nextSection?: ArtifactMarkdownSection;
};

const containsNestedSection = (
    container: ArtifactMarkdownSection,
    nested: ArtifactMarkdownSection
): boolean => (
    nested.level > container.level
    && nested.startLine > container.startLine
    && nested.endLine <= container.endLine
);

const getCandidateCoordinateSection = (
    candidate: ArtifactSectionChangeCandidate,
    coordinate: 'previous' | 'next'
): ArtifactMarkdownSection | undefined => (
    coordinate === 'previous'
        ? candidate.previousSection
        : candidate.nextSection
);

const hasMoreSpecificNestedChange = (
    candidate: ArtifactSectionChangeCandidate,
    candidates: ArtifactSectionChangeCandidate[]
): boolean => (
    candidates.some((other) => {
        if (other === candidate) return false;

        const coordinate = other.kind === 'removed' ? 'previous' : 'next';
        const container = getCandidateCoordinateSection(candidate, coordinate);
        const nested = getCandidateCoordinateSection(other, coordinate);
        if (!container || !nested) return false;

        return containsNestedSection(container, nested);
    })
);

export function buildArtifactSectionChangeIndex(
    previousArtifact: string,
    nextArtifact: string
): ArtifactSectionChange[] {
    const previousSections = parseArtifactMarkdownSections(previousArtifact);
    const nextSections = parseArtifactMarkdownSections(nextArtifact);
    const previousByAnchor = buildSectionMap(previousSections);
    const nextByAnchor = buildSectionMap(nextSections);
    const candidates: ArtifactSectionChangeCandidate[] = [];

    nextSections.forEach((section) => {
        const previous = previousByAnchor.get(section.anchor);
        if (!previous) {
            candidates.push({
                kind: 'added',
                section,
                nextSection: section,
            });
            return;
        }
        if (previous.content !== section.content) {
            candidates.push({
                kind: 'modified',
                section,
                previousSection: previous,
                nextSection: section,
            });
        }
    });

    previousSections.forEach((section) => {
        if (!nextByAnchor.has(section.anchor)) {
            candidates.push({
                kind: 'removed',
                section,
                previousSection: section,
            });
        }
    });

    return candidates
        .filter(candidate => !hasMoreSpecificNestedChange(candidate, candidates))
        .map(candidate => toSectionChange(candidate.kind, candidate.section));
}

const patchFallback = (
    content: string,
    reason: ArtifactSectionPatchFallbackReason
): ArtifactSectionPatchApplyResult => ({
    applied: false,
    content,
    changes: [],
    fallbackReason: reason,
});

const insertArtifactSectionAfter = (
    markdown: string,
    afterSection: ArtifactMarkdownSection,
    insertedContent: string
): string => {
    const lines = markdown.split(/\r?\n/);
    const insertedLines = insertedContent.split(/\r?\n/);
    return [
        ...lines.slice(0, afterSection.endLine),
        '',
        ...insertedLines,
        ...lines.slice(afterSection.endLine),
    ].join('\n');
};

export function applyArtifactSectionPatch(
    currentArtifact: string,
    patch: ArtifactSectionPatch
): ArtifactSectionPatchApplyResult {
    if (patch.baseContent !== undefined && patch.baseContent !== currentArtifact) {
        return patchFallback(currentArtifact, 'base_content_mismatch');
    }

    const currentSections = parseArtifactMarkdownSections(currentArtifact);

    if (patch.operation === 'replace') {
        const targetSection = currentSections.find(
            section => section.anchor === patch.sectionAnchor
        );
        if (!targetSection) {
            return patchFallback(currentArtifact, 'section_not_found');
        }

        const replacementSections = parseArtifactMarkdownSections(
            patch.replacementMarkdown
        );
        if (!replacementSections.some(section => section.anchor === patch.sectionAnchor)) {
            return patchFallback(currentArtifact, 'replacement_section_missing');
        }

        const content = replaceArtifactSectionContent(
            currentArtifact,
            targetSection,
            patch.replacementMarkdown,
        );
        return {
            applied: true,
            content,
            changes: buildArtifactSectionChangeIndex(currentArtifact, content),
        };
    }

    const afterSection = currentSections.find(
        section => section.anchor === patch.afterSectionAnchor
    );
    if (!afterSection) {
        return patchFallback(currentArtifact, 'anchor_not_found');
    }

    const content = insertArtifactSectionAfter(
        currentArtifact,
        afterSection,
        patch.replacementMarkdown,
    );
    if (!parseArtifactMarkdownSections(content).some(
        section => section.anchor === patch.sectionAnchor
    )) {
        return patchFallback(currentArtifact, 'replacement_section_missing');
    }

    return {
        applied: true,
        content,
        changes: buildArtifactSectionChangeIndex(currentArtifact, content),
    };
}

export function preserveLockedArtifactSections(
    nextArtifact: string,
    locks: ArtifactSectionLock[]
): string {
    if (locks.length === 0) return nextArtifact;

    let protectedArtifact = nextArtifact;
    locks.forEach((lock) => {
        const sections = parseArtifactMarkdownSections(protectedArtifact);
        const section = findArtifactSection(sections, {
            heading: lock.heading,
            sectionAnchor: lock.sectionAnchor,
        });
        if (!section) {
            protectedArtifact = protectedArtifact.endsWith('\n')
                ? `${protectedArtifact}${lock.content}`
                : `${protectedArtifact}\n\n${lock.content}`;
            return;
        }
        protectedArtifact = replaceArtifactSectionContent(
            protectedArtifact,
            section,
            lock.content,
        );
    });
    return protectedArtifact;
}

export function mergeRegeneratedArtifactSection({
    originalArtifact,
    generatedArtifact,
    target,
    locks,
}: {
    originalArtifact: string;
    generatedArtifact: string;
    target: ArtifactSectionTarget;
    locks: ArtifactSectionLock[];
}): { content: string } {
    const targetTitle = target.displayTitle ?? target.heading.replace(/^#{1,3}\s+/, '');
    if (findArtifactSectionLock(target, locks)) {
        throw new ArtifactSectionRegenerationError(
            'TARGET_LOCKED',
            `目标章节“${targetTitle}”已锁定，请先解锁后再重生成。`
        );
    }

    const originalTarget = findArtifactSection(
        parseArtifactMarkdownSections(originalArtifact),
        target
    );
    if (!originalTarget) {
        throw new ArtifactSectionRegenerationError(
            'ORIGINAL_TARGET_MISSING',
            `当前产出物中没有找到目标章节“${targetTitle}”。`
        );
    }

    const generatedTarget = findArtifactSection(
        parseArtifactMarkdownSections(generatedArtifact),
        target
    );
    if (!generatedTarget) {
        throw new ArtifactSectionRegenerationError(
            'GENERATED_TARGET_MISSING',
            `模型返回中没有找到目标章节“${targetTitle}”。`
        );
    }

    const mergedArtifact = replaceArtifactSectionContent(
        originalArtifact,
        originalTarget,
        generatedTarget.content,
    );

    return {
        content: preserveLockedArtifactSections(mergedArtifact, locks),
    };
}
