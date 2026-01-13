/**
 * MarkdownText 组件 - 使用 Assistant-ui 的 Markdown 渲染
 * 支持 Mermaid 图表渲染
 */
import { memo, type ComponentPropsWithoutRef } from 'react';
import { MarkdownTextPrimitive } from '@assistant-ui/react-markdown';
import remarkGfm from 'remark-gfm';
import { MermaidBlock } from './MermaidBlock';

// 自定义 CodeBlock 组件，处理 Mermaid 代码块
const CodeBlock = ({ node, className, children, ...props }: ComponentPropsWithoutRef<'code'> & { node?: unknown }) => {
    // 从 className 中提取语言 (格式: "language-xxx")
    const match = /language-(\w+)/.exec(className || '');
    const language = match ? match[1] : '';

    // 如果是 mermaid 代码块，使用 MermaidBlock 渲染
    if (language === 'mermaid') {
        const code = typeof children === 'string'
            ? children
            : Array.isArray(children)
                ? children.join('')
                : String(children || '');
        return <MermaidBlock code={code} />;
    }

    // 对于其他代码块，使用默认样式
    const isInline = !className;

    if (isInline) {
        return (
            <code
                className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-800 rounded text-sm font-mono text-pink-600 dark:text-pink-400"
                {...props}
            >
                {children}
            </code>
        );
    }

    return (
        <code
            className={`block p-4 bg-gray-100 dark:bg-gray-800 rounded-lg text-sm font-mono overflow-x-auto ${className || ''}`}
            {...props}
        >
            {children}
        </code>
    );
};

// 创建基础 MarkdownText 组件
const MarkdownTextImpl = () => {
    return (
        <MarkdownTextPrimitive
            remarkPlugins={[remarkGfm]}
            className="prose prose-sm dark:prose-invert max-w-none break-words"
            components={{
                code: CodeBlock,
            }}
        />
    );
};

export const MarkdownText = memo(MarkdownTextImpl);

export default MarkdownText;
