/**
 * MarkdownText 组件 - 使用 Assistant-ui 的 Markdown 渲染
 * 支持 Mermaid 图表渲染
 */
import React, { memo } from 'react';
import { Streamdown } from 'streamdown';
import { MermaidBlock } from './MermaidBlock';
import { cn } from '../../lib/utils';

// 自定义 CodeBlock 组件
export const CodeBlock = ({ node, inline, className, children, ...props }: any) => {
    // 1. 如果是行内代码
    if (inline) {
        return <code className={cn("aui-md-inline-code", className)} {...props}>{children}</code>;
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

    // 4. 普通代码块，使用 assistant-ui 标准样式
    return (
        <pre className={cn("aui-md-pre", className)} {...props}>
            <code className={className}>
                {children}
            </code>
        </pre>
    );
};

const MarkdownTextImpl = ({ children, content, ...props }: any) => {
    const textContent = (children || content || '') as string;
    return (
        <Streamdown
            {...props}
            className="aui-md"
            parseIncompleteMarkdown={true}
            components={{
                h1: ({ className, ...props }: any) => <h1 className={cn("aui-md-h1", className)} {...props} />,
                h2: ({ className, ...props }: any) => <h2 className={cn("aui-md-h2", className)} {...props} />,
                h3: ({ className, ...props }: any) => <h3 className={cn("aui-md-h3", className)} {...props} />,
                h4: ({ className, ...props }: any) => <h4 className={cn("aui-md-h4", className)} {...props} />,
                h5: ({ className, ...props }: any) => <h5 className={cn("aui-md-h5", className)} {...props} />,
                h6: ({ className, ...props }: any) => <h6 className={cn("aui-md-h6", className)} {...props} />,
                p: ({ className, ...props }: any) => <p className={cn("aui-md-p", className)} {...props} />,
                a: ({ className, ...props }: any) => <a className={cn("aui-md-a", className)} {...props} target="_blank" rel="noopener noreferrer" />,
                blockquote: ({ className, ...props }: any) => <blockquote className={cn("aui-md-blockquote", className)} {...props} />,
                ul: ({ className, ...props }: any) => <ul className={cn("aui-md-ul", className)} {...props} />,
                ol: ({ className, ...props }: any) => <ol className={cn("aui-md-ol", className)} {...props} />,
                li: ({ className, ...props }: any) => <li className={cn("aui-md-li", className)} {...props} />,
                hr: ({ className, ...props }: any) => <hr className={cn("aui-md-hr", className)} {...props} />,
                table: ({ className, ...props }: any) => (
                    <div className="overflow-x-auto my-4">
                        <table className={cn("aui-md-table", className)} {...props} />
                    </div>
                ),
                th: ({ className, ...props }: any) => <th className={cn("aui-md-th", className)} {...props} />,
                td: ({ className, ...props }: any) => <td className={cn("aui-md-td", className)} {...props} />,
                tr: ({ className, ...props }: any) => <tr className={cn("aui-md-tr", className)} {...props} />,
                
                // Code handling
                code: CodeBlock,
                pre: React.Fragment,
            }}
        >
            {textContent}
        </Streamdown>
    );
};

export const MarkdownText = memo(MarkdownTextImpl);

export default MarkdownText;
