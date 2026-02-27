import { describe, it, expect } from 'vitest';
import { preprocessMarkdown } from '../utils/markdownUtils';

describe('preprocessMarkdown', () => {
    it('should format simple mark tags', () => {
        const input = "Here is <mark>new text</mark>.";
        expect(preprocessMarkdown(input)).toBe("Here is <mark>new text</mark>.");
    });

    it('should split multiple list items within a single mark tag', () => {
        const input = "<mark>* Item 1\n* Item 2</mark>";
        const result = preprocessMarkdown(input);
        expect(result).toBe("* <mark>Item 1</mark>\n* <mark>Item 2</mark>");
    });

    it('should fix block prefixes wrapped in mark tags', () => {
        const input = "<mark>### Header</mark>\n<mark>1. List item</mark>";
        const result = preprocessMarkdown(input);
        expect(result).toBe("### <mark>Header</mark>\n1. <mark>List item</mark>");
    });
});
