/**
 * MarkdownText 组件 - 使用 Assistant-ui 的 Markdown 渲染
 * 支持 Mermaid 图表渲染
 */
import React, { memo, type ComponentPropsWithoutRef } from 'react';
import { MarkdownTextPrimitive } from '@assistant-ui/react-markdown';
import remarkGfm from 'remark-gfm';
import { MermaidBlock } from './MermaidBlock';

// 移除 PreBlock，直接由 CodeBlock 接管渲染逻辑
export const CodeBlock = ({ node, inline, className, children, ...props }: any) => {
    // 1. 如果是行内代码，直接渲染 code
    if (inline) {
        return <code className={className} {...props}>{children}</code>;
    }

    // 2. 提取语言
    const match = /language-(\w+)/.exec(className || '');
    const language = match ? match[1] : '';

    // 3. 如果是 Mermaid，渲染图表 (不包裹 pre)
    if (language === 'mermaid') {
        const code = typeof children === 'string'
            ? children
            : Array.isArray(children)
                ? children.join('')
                : String(children || '');
        return <MermaidBlock code={code.replace(/\n$/, '')} />;
    }

    // 4. 普通代码块，手动包裹 pre 以恢复 prose 样式
    return (
        <pre className={`block p-4 bg-gray-100 dark:bg-gray-800 rounded-lg text-sm font-mono overflow-x-auto my-4`}>
            <code className={className} {...props}>
                {children}
            </code>
        </pre>
    );
};

// 创建基础 MarkdownText 组件

const MarkdownTextImpl = () => {
    return (
        <MarkdownTextPrimitive
            remarkPlugins={[remarkGfm]}
            className="prose prose-sm prose-neutral dark:prose-invert max-w-none break-words prose-p:leading-relaxed prose-pre:p-0"
            components={{
                code: CodeBlock,
                // 将 pre 映射为 Fragment，移除默认 DOM 结构，由 CodeBlock 全权接管
                pre: React.Fragment,
            }}
        />
    );
};

export const MarkdownText = memo(MarkdownTextImpl);

export default MarkdownText;
