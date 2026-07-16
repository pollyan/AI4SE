const NAMED_HTML_ENTITIES: Record<string, string> = {
    amp: '&',
    apos: "'",
    gt: '>',
    lt: '<',
    quot: '"',
};

const decodeMarkdownHtmlEntities = (content: string): string => (
    content
        .replace(/&#(\d+);/g, (_entity, code: string) => (
            String.fromCodePoint(Number(code))
        ))
        .replace(/&(amp|apos|gt|lt|quot);/g, (_entity, name: string) => (
            NAMED_HTML_ENTITIES[name]
        ))
);

export const stripInlineMarkdownToText = (content: string): string => (
    decodeMarkdownHtmlEntities(
        content
            .replace(/`([^`]+)`/g, '$1')
            .replace(/\*\*([^*]+)\*\*/g, '$1')
            .replace(/\*([^*]+)\*/g, '$1')
            .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1'),
    )
);
