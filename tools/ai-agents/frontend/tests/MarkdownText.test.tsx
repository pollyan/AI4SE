import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { MarkdownText, CodeOverride } from '../components/chat/MarkdownText';

// Mocks
vi.mock('react-markdown', () => ({
  default: ({ children }: any) => <div data-testid="markdown-primitive">{children}</div>
}));

// Mock MermaidBlock because it uses Mermaid which might fail in JSDOM or be slow
vi.mock('../components/chat/MermaidBlock', () => ({
  MermaidBlock: ({ code }: any) => <div data-testid="mermaid-block">{code}</div>
}));

describe('MarkdownText', () => {
  it('renders primitive', () => {
    render(<MarkdownText content="foo" />);
    expect(screen.getByTestId('markdown-primitive')).toBeDefined();
    expect(screen.getByTestId('markdown-primitive')).toHaveTextContent('foo');
  });
});

describe('CodeOverride', () => {
  it('renders normal code', () => {
    render(<CodeOverride className="language-js">console.log(1)</CodeOverride>);
    const code = screen.getByText('console.log(1)');
    expect(code.tagName).toBe('CODE');
  });

  it('renders mermaid block', () => {
    render(<CodeOverride className="language-mermaid">{'graph TD; A-->B;'}</CodeOverride>);
    expect(screen.getByTestId('mermaid-block')).toHaveTextContent('graph TD; A-->B;');
  });
});
