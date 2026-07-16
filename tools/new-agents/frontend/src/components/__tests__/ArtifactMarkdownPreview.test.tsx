import { render, screen } from '@testing-library/react';
import type { Components } from 'react-markdown';
import { describe, expect, it } from 'vitest';
import { ArtifactMarkdownPreview } from '../ArtifactMarkdownPreview';

const components: Components = {
    h1: ({ children }) => <h1>{children}</h1>,
    h2: ({ children }) => <h2>{children}</h2>,
};

describe('ArtifactMarkdownPreview', () => {
    it('renders parsed sections through the shared markdown component contract', () => {
        render(
            <ArtifactMarkdownPreview
                content={'# 需求文档\n\n## 范围\n\n登录\n\n## 风险\n\n回归'}
                createComponents={() => components}
                renderVersionKey="preview"
            />
        );

        expect(screen.getByRole('heading', { name: '需求文档' })).toBeTruthy();
        expect(screen.getByRole('heading', { name: '范围' })).toBeTruthy();
        expect(screen.getByRole('heading', { name: '风险' })).toBeTruthy();
        expect(screen.getByText('登录')).toBeTruthy();
        expect(screen.getByText('回归')).toBeTruthy();
    });

    it('renders compact metadata entities as literal text instead of Markdown or HTML', () => {
        const { container } = render(
            <ArtifactMarkdownPreview
                content={[
                    '# 文档',
                    '',
                    '## 文档信息',
                    '文档元信息：值：&#95;draft&#95; &#126;&#126;old&#126;&#126; &#96;code&#96; &#92;path &#91;link&#93; &lt;script&gt; &#124; &amp;copy;',
                ].join('\n')}
                createComponents={() => components}
                renderVersionKey="metadata-entities"
            />
        );

        expect(screen.getByText(/_draft_ ~~old~~ `code` \\path \[link\] <script> \| &copy;/)).toBeTruthy();
        expect(container.querySelector('em')).toBeNull();
        expect(container.querySelector('del')).toBeNull();
        expect(container.querySelector('code')).toBeNull();
        expect(container.querySelector('script')).toBeNull();
    });
});
