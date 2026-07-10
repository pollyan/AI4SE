import type { ArtifactSectionLock } from './types';
import { parseArtifactMarkdownSections } from './artifactSections';

type FindLockedSectionChangeInput = {
    currentContent: string;
    nextContent: string;
    locks: ArtifactSectionLock[];
};

export const findLockedSectionChange = ({
    currentContent,
    nextContent,
    locks,
}: FindLockedSectionChangeInput): string | null => {
    if (locks.length === 0) return null;

    const currentSections = parseArtifactMarkdownSections(currentContent);
    const nextSections = parseArtifactMarkdownSections(nextContent);
    for (const lock of locks) {
        const currentSection = currentSections.find((section) => (
            lock.sectionAnchor
                ? section.anchor === lock.sectionAnchor
                : section.heading === lock.heading
        ));
        const nextSection = nextSections.find((section) => (
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
