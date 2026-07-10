import React, { useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import type { Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import { parseArtifactMarkdownSections } from '../core/artifactSections';
import { preprocessMarkdown } from '../core/utils/markdownUtils';

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

type ArtifactMarkdownPreviewProps = {
    content: string;
    createComponents: (chunk: MarkdownPreviewChunk) => Components;
    renderVersionKey: string;
};

const countFencedBlocksByLanguage = (
    content: string,
    language: 'mermaid' | 'ai4se-visual',
): number => {
    const fencePattern = /^```\s*([^\s`]+)/gm;
    let count = 0;
    let match: RegExpExecArray | null;
    while ((match = fencePattern.exec(content)) !== null) {
        if (match[1] === language) count += 1;
    }
    return count;
};

const buildMarkdownPreviewChunks = (content: string): MarkdownPreviewChunk[] => {
    const parsedSections = parseArtifactMarkdownSections(content);
    const baseChunks = parsedSections.length > 0
        ? parsedSections.map(section => ({ sectionKey: section.anchor, content: section.content }))
        : [{ sectionKey: 'full-document', content }];

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
                'ai4se-visual',
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

export const ArtifactMarkdownPreview = ({
    content,
    createComponents,
    renderVersionKey,
}: ArtifactMarkdownPreviewProps) => {
    const displayContent = useMemo(() => preprocessMarkdown(content), [content]);
    const chunks = useMemo(() => buildMarkdownPreviewChunks(displayContent), [displayContent]);

    return (
        <>
            {chunks.map((chunk) => (
                <RenderedMarkdownSection
                    key={chunk.sectionKey}
                    {...chunk}
                    components={createComponents(chunk)}
                    renderVersionKey={renderVersionKey}
                />
            ))}
        </>
    );
};
