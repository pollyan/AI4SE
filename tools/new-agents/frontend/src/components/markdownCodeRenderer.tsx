import React, { HTMLAttributes, ReactNode } from 'react';
import { Mermaid, MermaidProps } from './Mermaid';

export interface MarkdownCodeRendererProps extends HTMLAttributes<HTMLElement> {
    node?: unknown;
    inline?: boolean;
    className?: string;
    children?: ReactNode;
}

interface CodeRenderArgs {
    language: string;
    className?: string;
    children: ReactNode;
    props: HTMLAttributes<HTMLElement>;
}

interface MarkdownCodeRendererOptions {
    nextMermaidBlockIndex: () => number;
    onMermaidRetry?: MermaidProps['onRetry'];
    onMermaidRenderError?: MermaidProps['onRenderError'];
    onMermaidRenderSuccess?: MermaidProps['onRenderSuccess'];
    renderStructuredVisual?: (args: CodeRenderArgs) => ReactNode;
    renderBlockCode: (args: CodeRenderArgs) => ReactNode;
    renderInlineCode: (args: CodeRenderArgs) => ReactNode;
}

function getCodeLanguage(className?: string): string {
    const match = /(?:^|\s)language-([^\s]+)/.exec(className || '');
    return match ? match[1] : '';
}

function normalizeMermaidChart(children: ReactNode): string {
    return String(children)
        .replace(/\n$/, '')
        .replace(/\$\{FENCE\}/g, '```');
}

function isInlineCodeNode({
    inline,
    language,
    children,
}: {
    inline?: boolean;
    language: string;
    children: ReactNode;
}): boolean {
    if (inline === true) return true;
    if (inline === false) return false;
    return !language && !String(children).includes('\n');
}

export function createMarkdownCodeRenderer({
    nextMermaidBlockIndex,
    onMermaidRetry,
    onMermaidRenderError,
    onMermaidRenderSuccess,
    renderStructuredVisual,
    renderBlockCode,
    renderInlineCode,
}: MarkdownCodeRendererOptions) {
    return function MarkdownCodeRenderer({
        node,
        inline,
        className,
        children,
        ...props
    }: MarkdownCodeRendererProps) {
        const language = getCodeLanguage(className);
        const isInline = isInlineCodeNode({ inline, language, children });

        if (!isInline && language === 'mermaid') {
            return (
                <Mermaid
                    chart={normalizeMermaidChart(children)}
                    blockIndex={nextMermaidBlockIndex()}
                    onRetry={onMermaidRetry}
                    onRenderError={onMermaidRenderError}
                    onRenderSuccess={onMermaidRenderSuccess}
                />
            );
        }

        const renderArgs = {
            language,
            className,
            children,
            props,
        };

        if (!isInline && language === 'ai4se-visual' && renderStructuredVisual) {
            return renderStructuredVisual(renderArgs);
        }

        return isInline ? renderInlineCode(renderArgs) : renderBlockCode(renderArgs);
    };
}
