import { render } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
// @ts-expect-error - Component not created yet
import { TypingIndicator } from '../components/chat/TypingIndicator';

describe('TypingIndicator', () => {
    it('renders three bouncing dots', () => {
        const { container } = render(<TypingIndicator />);
        const dots = container.querySelectorAll('.animate-bounce');
        expect(dots.length).toBe(3);
    });
});
