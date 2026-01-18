import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { MarkdownText } from '../components/chat/MarkdownText';

describe('MarkdownText', () => {
  it('renders simple text', () => {
    render(<MarkdownText children="Hello World" />);
    expect(screen.getByText('Hello World')).toBeDefined();
  });

  it('renders markdown', () => {
    render(<MarkdownText children="# Heading" />);
    // Check if it renders as h1 (implementation detail, usually h1)
    const heading = screen.getByRole('heading', { level: 1 });
    expect(heading.textContent).toBe('Heading');
  });
});
