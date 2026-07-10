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
});
