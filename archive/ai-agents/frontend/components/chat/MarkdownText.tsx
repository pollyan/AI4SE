/**
 * MarkdownText 组件 - 使用 react-markdown
 * 支持 Mermaid 图表渲染和 GFM
 */
import React, { memo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { MermaidBlock } from './MermaidBlock';

// 自定义 Code 组件处理 Mermaid
export const CodeOverride = ({ className, children, ...props }: any) => {
    const match = /language-(\w+)/.exec(className || '');
    const language = match ? match[1] : '';

    if (language === 'mermaid') {
        const code = String(children).replace(/\n$/, '');
        return <MermaidBlock code={code} />;
    }

    return <code className={`${className} bg-gray-100 dark:bg-gray-700 rounded px-1 py-0.5`} {...props}>{children}</code>;
};

const MarkdownTextImpl = ({ content }: { content: string }) => {
    return (
        <div className="prose prose-sm dark:prose-invert max-w-none break-words">
            <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                    code: CodeOverride,
                    // 链接在新窗口打开
                    a: ({ node, ...props }) => <a target="_blank" rel="noopener noreferrer" {...props} />,
                    // 保持段落间距适中
                    p: ({ node, ...props }) => <p className="mb-2 last:mb-0" {...props} />,
                }}
            >
                {content}
            </ReactMarkdown>
        </div>
    );
};

export const MarkdownText = memo(MarkdownTextImpl);

export default MarkdownText;
