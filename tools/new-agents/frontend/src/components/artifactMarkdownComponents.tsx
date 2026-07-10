import React from 'react';
import type { Components } from 'react-markdown';
import {
    buildArtifactVisualDiagnosticId,
    getArtifactVisualDiagnosticContainerClass,
} from '../core/artifactVisualDiagnostics';
import { createMarkdownCodeRenderer } from './markdownCodeRenderer';
import { StructuredVisual } from './StructuredVisual';

type ArtifactMarkdownComponentsOptions = {
    currentStageId?: string;
    activeAnchorText?: string | null;
    activeVisualDiagnosticId?: string | null;
    reportVisualDiagnostics?: boolean;
    attachVisualDiagnosticAnchors?: boolean;
    deferMermaidRender?: boolean;
    mermaidBlockStartIndex?: number;
    structuredVisualBlockStartIndex?: number;
    onMermaidRetry?: Parameters<typeof createMarkdownCodeRenderer>[0]['onMermaidRetry'];
    onMermaidRenderError?: (details: { message: string; blockIndex: number }) => void;
    onMermaidRenderSuccess?: (blockIndex: number) => void;
    onStructuredVisualValidationError?: (blockIndex: number, message: string) => void;
    onStructuredVisualValidationSuccess?: (blockIndex: number) => void;
};

export const createArtifactMarkdownComponents = ({
    currentStageId,
    activeAnchorText = null,
    activeVisualDiagnosticId = null,
    reportVisualDiagnostics = false,
    attachVisualDiagnosticAnchors = false,
    deferMermaidRender = false,
    mermaidBlockStartIndex = 0,
    structuredVisualBlockStartIndex = 0,
    onMermaidRetry,
    onMermaidRenderError,
    onMermaidRenderSuccess,
    onStructuredVisualValidationError,
    onStructuredVisualValidationSuccess,
}: ArtifactMarkdownComponentsOptions = {}): Components => {
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
        h1: ({ node, children, ...props }) => <h1 className="mb-6 border-b border-[#1e293b] pb-2 text-3xl font-bold text-white" {...props}>{highlightAnchorInChildren(children)}</h1>,
        h2: ({ node, children, ...props }) => <h2 className="mt-8 mb-4 text-2xl font-bold text-white before:mr-2 before:text-blue-500 before:opacity-50 before:content-['#']" {...props}>{highlightAnchorInChildren(children)}</h2>,
        h3: ({ node, children, ...props }) => <h3 className="mt-6 mb-3 text-xl font-semibold text-slate-200" {...props}>{highlightAnchorInChildren(children)}</h3>,
        p: ({ node, children, ...props }) => <p className="mb-4 leading-relaxed text-slate-400" {...props}>{highlightAnchorInChildren(children)}</p>,
        ul: ({ node, ...props }) => <ul className="mb-4 list-disc space-y-2 pl-6 text-slate-400" {...props} />,
        ol: ({ node, ...props }) => <ol className="mb-4 list-decimal space-y-2 pl-6 text-slate-400" {...props} />,
        li: ({ node, children, ...props }) => <li className="leading-relaxed" {...props}>{highlightAnchorInChildren(children)}</li>,
        strong: ({ node, children, ...props }) => <strong className="font-bold text-white" {...props}>{highlightAnchorInChildren(children)}</strong>,
        blockquote: ({ node, children, ...props }) => <blockquote className="my-4 rounded-r border-l-4 border-blue-500 bg-blue-500/5 py-2 pl-4 italic text-slate-400" {...props}>{highlightAnchorInChildren(children)}</blockquote>,
        table: ({ node, ...props }) => <div className="mb-6 overflow-x-auto"><table className="w-full border-collapse text-sm" {...props} /></div>,
        th: ({ node, children, ...props }) => <th className="border-b border-[#334155] bg-[#1e293b] p-3 text-left font-semibold text-slate-200" {...props}>{highlightAnchorInChildren(children)}</th>,
        td: ({ node, children, ...props }) => <td className="group-hover:bg-white/5 border-b border-[#1e293b] p-3 text-slate-400" {...props}>{highlightAnchorInChildren(children)}</td>,
        tr: ({ node, ...props }) => <tr className="group transition-colors hover:bg-white/[0.02]" {...props} />,
        mark: ({ node, ...props }) => <mark className="box-decoration-clone rounded bg-emerald-500/15 px-1.5 py-0.5 font-medium text-emerald-400 shadow-[0_0_8px_rgba(16,185,129,0.1)]" {...props} />,
        pre: ({ node, children }) => <>{children}</>,
        code: createMarkdownCodeRenderer({
            nextMermaidBlockIndex: () => mermaidBlockCounter++,
            onMermaidRetry,
            onMermaidRenderError: reportVisualDiagnostics ? onMermaidRenderError : undefined,
            onMermaidRenderSuccess: reportVisualDiagnostics ? onMermaidRenderSuccess : undefined,
            renderMermaid: attachVisualDiagnosticAnchors || deferMermaidRender
                ? ({ blockIndex, element }) => {
                    const mermaidElement = deferMermaidRender ? (
                        <div className="my-6 flex w-full justify-center overflow-x-auto">
                            <div className="flex max-w-xl items-center gap-3 rounded-lg border border-sky-500/30 bg-sky-500/10 px-4 py-3 text-sm text-sky-200">
                                <span className="h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-sky-300 border-t-transparent" aria-hidden="true" />
                                <span><span className="block font-medium text-sky-100">图表将在产出物稳定后绘制</span><span className="mt-1 block text-xs text-sky-200/75">模型仍在输出图表内容，已暂停实时绘制以保持页面响应。</span></span>
                            </div>
                        </div>
                    ) : element;
                    if (!attachVisualDiagnosticAnchors) return mermaidElement;
                    const diagnosticId = buildArtifactVisualDiagnosticId(currentStageId, 'mermaid', blockIndex);
                    return <div data-artifact-visual-diagnostic-id={diagnosticId} data-artifact-visual-focused={activeVisualDiagnosticId === diagnosticId ? 'true' : undefined} className={getArtifactVisualDiagnosticContainerClass(diagnosticId, activeVisualDiagnosticId)}>{mermaidElement}</div>;
                }
                : undefined,
            renderStructuredVisual: ({ children }) => {
                const blockIndex = structuredVisualBlockCounter++;
                const diagnosticId = buildArtifactVisualDiagnosticId(currentStageId, 'structured-visual', blockIndex);
                const visual = <StructuredVisual source={String(children).replace(/\n$/, '')} onValidationError={reportVisualDiagnostics ? (message) => onStructuredVisualValidationError?.(blockIndex, message) : undefined} onValidationSuccess={reportVisualDiagnostics ? () => onStructuredVisualValidationSuccess?.(blockIndex) : undefined} />;
                if (!attachVisualDiagnosticAnchors) return visual;
                return <div data-artifact-visual-diagnostic-id={diagnosticId} data-artifact-visual-focused={activeVisualDiagnosticId === diagnosticId ? 'true' : undefined} className={getArtifactVisualDiagnosticContainerClass(diagnosticId, activeVisualDiagnosticId)}>{visual}</div>;
            },
            renderBlockCode: ({ language, className, children, props }) => (
                <div className="relative my-6 overflow-hidden rounded-lg border border-[#1e293b] bg-[#0f172a]">
                    {language && <div className="flex items-center border-b border-[#0f172a] bg-[#1e293b] px-4 py-2 font-mono text-xs text-slate-400">{language}</div>}
                    <pre className="overflow-x-auto p-4 font-mono text-sm text-slate-300"><code className={className} {...props}>{children}</code></pre>
                </div>
            ),
            renderInlineCode: ({ children, props }) => <code className="rounded bg-white/10 px-1.5 py-0.5 font-mono text-sm text-blue-300" {...props}>{children}</code>,
        }),
    };
};
