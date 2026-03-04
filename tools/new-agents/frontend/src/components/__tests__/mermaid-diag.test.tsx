/**
 * 诊断：验证 ReactMarkdown + rehype-raw 传递给 Mermaid 组件的 children 内容
 */
import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';

describe('ReactMarkdown mermaid 代码块传递诊断', () => {
    // 模拟 ArtifactPane 中的 code 组件来捕获传递给 Mermaid 的内容
    it('检查 ReactMarkdown 传递给 code 组件的 children 内容', () => {
        let capturedChildren: string = '';

        const markdownComponents = {
            code({ node, inline, className, children, ...props }: any) {
                const match = /language-(\w+)/.exec(className || '');
                const language = match ? match[1] : '';

                if (!inline && language === 'mermaid') {
                    capturedChildren = String(children).replace(/\n$/, '');
                    return <div data-testid="mermaid-captured">{capturedChildren.substring(0, 100)}</div>;
                }
                return <code>{children}</code>;
            }
        };

        const markdownContent = `# 登录流程

\`\`\`mermaid
sequenceDiagram
    participant U as 用户
    participant FE as 前端
    participant BE as 后端服务
    participant DB as 数据库/认证服务
    participant SMS as 短信服务
    participant OAuth as 第三方平台
    
    U->>FE: 选择登录方式
    alt 账号密码登录
        U->>FE: 输入账号密码
        FE->>BE: 提交登录请求 (HTTPS+ 哈希)
        BE->>DB: 验证凭证
        DB-->>BE: 返回验证结果
        BE-->>FE: 返回 Token/Session
        FE-->>U: 登录成功跳转
    else 手机验证码登录
        U->>FE: 输入手机号
        FE->>BE: 请求发送验证码
        BE->>SMS: 调用短信接口
        SMS-->>BE: 验证码发送成功
        BE-->>FE: 60 秒倒计时
        U->>FE: 输入验证码
        FE->>BE: 提交验证码
        BE->>DB: 验证并自动注册 (如未注册)
        BE-->>FE: 返回 Token
        FE-->>U: 登录成功
    else 第三方登录
        U->>OAuth: 授权登录
        OAuth->>BE: 回调 OpenID/UnionID
        BE->>DB: 查询绑定关系
        DB-->>BE: 返回绑定状态
        BE-->>FE: 登录成功或跳转绑定页
    end
\`\`\`
`;

        render(
            <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                rehypePlugins={[rehypeRaw]}
                components={markdownComponents}
            >
                {markdownContent}
            </ReactMarkdown>
        );

        console.log('=== 捕获到的 children (前200字符) ===');
        console.log(capturedChildren.substring(0, 200));
        console.log('\n=== 完整 children ===');
        console.log(JSON.stringify(capturedChildren));

        // 关键验证：检查 ->> 是否被转义或修改
        console.log('\n=== 关键特征检查 ===');
        console.log('包含 ->>:', capturedChildren.includes('->>'));
        console.log('包含 -->>:', capturedChildren.includes('-->>'));
        console.log('包含 (HTTPS+ 哈希):', capturedChildren.includes('(HTTPS+ 哈希)'));
        console.log('包含 Token/Session:', capturedChildren.includes('Token/Session'));
        console.log('包含 sequenceDiagram:', capturedChildren.includes('sequenceDiagram'));
        console.log('包含 alt:', capturedChildren.includes('alt'));
        console.log('包含 else:', capturedChildren.includes('else'));
        console.log('包含 end:', capturedChildren.includes('end'));

        expect(capturedChildren).toContain('sequenceDiagram');
    });
});
