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

export function createMarkdownCodeRenderer({
    nextMermaidBlockIndex,
    onMermaidRetry,
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

        if (!inline && language === 'mermaid') {
            return (
                <Mermaid
                    chart={normalizeMermaidChart(children)}
                    blockIndex={nextMermaidBlockIndex()}
                    onRetry={onMermaidRetry}
                />
            );
        }

        const renderArgs = {
            language,
            className,
            children,
            props,
        };
        return !inline ? renderBlockCode(renderArgs) : renderInlineCode(renderArgs);
    };
}
