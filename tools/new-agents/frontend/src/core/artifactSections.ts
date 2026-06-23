import type { ArtifactSectionLock } from './types';

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
    return [
        ...lines.slice(0, section.startLine),
        ...replacementLines,
        ...lines.slice(section.endLine),
    ].join('\n');
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
