import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { createMarkdownCodeRenderer } from '../markdownCodeRenderer';

vi.mock('../Mermaid', () => ({
    Mermaid: ({
        chart,
        blockIndex,
    }: {
        chart: string;
        blockIndex?: number;
    }) => <div data-testid="mermaid" data-block-index={blockIndex}>{chart}</div>,
}));

describe('createMarkdownCodeRenderer', () => {
    it('renders normalized mermaid blocks with the next block index', () => {
        let nextIndex = 2;
        const CodeRenderer = createMarkdownCodeRenderer({
            nextMermaidBlockIndex: () => nextIndex++,
            onMermaidRetry: vi.fn(),
            renderBlockCode: ({ language, children }) => (
                <pre data-testid="block-code" data-language={language}>{children}</pre>
            ),
            renderInlineCode: ({ children }) => (
                <code data-testid="inline-code">{children}</code>
            ),
        });

        render(
            <CodeRenderer inline={false} className="language-mermaid">
                {'graph TD\nA-->B\n${FENCE}\n'}
            </CodeRenderer>
        );

        expect(screen.getByTestId('mermaid').textContent).toBe('graph TD\nA-->B\n```');
        expect(screen.getByTestId('mermaid').getAttribute('data-block-index')).toBe('2');
        expect(screen.queryByTestId('block-code')).toBeNull();
    });

    it('allows callers to wrap rendered mermaid blocks with the full block index', () => {
        const CodeRenderer = createMarkdownCodeRenderer({
            nextMermaidBlockIndex: () => 0,
            renderMermaid: ({ blockIndex, element }) => (
                <section data-testid="mermaid-wrapper" data-block-index={blockIndex}>
                    {element}
                </section>
            ),
            renderBlockCode: ({ language, children }) => (
                <pre data-testid="block-code" data-language={language}>{children}</pre>
            ),
            renderInlineCode: ({ children }) => (
                <code data-testid="inline-code">{children}</code>
            ),
        });

        render(
            <CodeRenderer inline={false} className="language-mermaid">
                {'graph TD\nA-->B\n'}
            </CodeRenderer>
        );

        expect(screen.getByTestId('mermaid-wrapper').getAttribute('data-block-index')).toBe('0');
        expect(screen.getByTestId('mermaid')).toBeTruthy();
    });

    it('delegates non-mermaid block code rendering to the caller', () => {
        const CodeRenderer = createMarkdownCodeRenderer({
            nextMermaidBlockIndex: () => 0,
            onMermaidRetry: vi.fn(),
            renderBlockCode: ({ language, children }) => (
                <pre data-testid="block-code" data-language={language}>{children}</pre>
            ),
            renderInlineCode: ({ children }) => (
                <code data-testid="inline-code">{children}</code>
            ),
        });

        render(
            <CodeRenderer inline={false} className="language-python">
                {'print("hello")'}
            </CodeRenderer>
        );

        expect(screen.getByTestId('block-code').getAttribute('data-language')).toBe('python');
        expect(screen.getByTestId('block-code').textContent).toBe('print("hello")');
        expect(screen.queryByTestId('mermaid')).toBeNull();
    });

    it('treats language-less single-line code as inline when react-markdown omits inline prop', () => {
        const CodeRenderer = createMarkdownCodeRenderer({
            nextMermaidBlockIndex: () => 0,
            onMermaidRetry: vi.fn(),
            renderBlockCode: ({ children }) => (
                <pre data-testid="block-code">{children}</pre>
            ),
            renderInlineCode: ({ children }) => (
                <code data-testid="inline-code">{children}</code>
            ),
        });

        render(<CodeRenderer>{'token'}</CodeRenderer>);

        expect(screen.getByTestId('inline-code').textContent).toBe('token');
        expect(screen.queryByTestId('block-code')).toBeNull();
    });

    it('does not treat mermaid-like language names as mermaid diagrams', () => {
        const CodeRenderer = createMarkdownCodeRenderer({
            nextMermaidBlockIndex: () => 0,
            onMermaidRetry: vi.fn(),
            renderBlockCode: ({ language, children }) => (
                <pre data-testid="block-code" data-language={language}>{children}</pre>
            ),
            renderInlineCode: ({ children }) => (
                <code data-testid="inline-code">{children}</code>
            ),
        });

        render(
            <CodeRenderer inline={false} className="language-mermaid-js">
                {'graph TD\nA-->B'}
            </CodeRenderer>
        );

        expect(screen.getByTestId('block-code').getAttribute('data-language')).toBe('mermaid-js');
        expect(screen.queryByTestId('mermaid')).toBeNull();
    });
});
