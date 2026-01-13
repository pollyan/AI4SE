import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MermaidBlock } from '../components/chat/MermaidBlock';
import * as React from 'react';

// Mock mermaid library
vi.mock('mermaid', () => ({
    default: {
        initialize: vi.fn(),
        render: vi.fn(),
    },
}));

describe('MermaidBlock', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('should show loading state initially for valid code', () => {
        render(<MermaidBlock code="flowchart TD\n    A --> B" />);
        expect(screen.getByText(/正在渲染图表/)).toBeInTheDocument();
    });

    it('should show loading state for incomplete code', () => {
        render(<MermaidBlock code="flowchart" />);
        expect(screen.getByText(/正在渲染图表/)).toBeInTheDocument();
    });

    it('should show loading state for code without valid diagram type', () => {
        render(<MermaidBlock code="invalid\n    A --> B" />);
        expect(screen.getByText(/正在渲染图表/)).toBeInTheDocument();
    });

    it('should show loading state for empty code', () => {
        render(<MermaidBlock code="" />);
        expect(screen.getByText(/正在渲染图表/)).toBeInTheDocument();
    });
});
