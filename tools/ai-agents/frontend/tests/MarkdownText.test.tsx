import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { MarkdownText, CodeOverride } from '../components/chat/MarkdownText';

// Mock dependency to avoid context requirements and potential ESM issues in test
vi.mock('@assistant-ui/react-markdown', () => ({
  MarkdownTextPrimitive: (props: any) => <div data-testid="markdown-primitive">{props.children}</div>
}));

// Mock MermaidBlock because it uses Mermaid which might fail in JSDOM or be slow
vi.mock('../components/chat/MermaidBlock', () => ({
  MermaidBlock: ({ code }: any) => <div data-testid="mermaid-block">{code}</div>
}));

describe('MarkdownText', () => {
  it('renders primitive', () => {
    render(<MarkdownText children="foo" />);
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
