import { describe, it, expect } from 'vitest';
import {
    hashTextForDiagnostics,
    preprocessMarkdown,
    replaceMermaidBlockAtIndex,
} from '../utils/markdownUtils';

describe('hashTextForDiagnostics', () => {
    it('matches the cross-runtime SHA-256 summary format', () => {
        expect(hashTextForDiagnostics('abc')).toBe(
            'sha256-ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'
        );
    });
});

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

describe('replaceMermaidBlockAtIndex', () => {
    it('replaces only the requested mermaid block', () => {
        const input = [
            'Before',
            '```mermaid',
            'graph TD',
            'A-->B',
            '```',
            'Middle',
            '```mermaid',
            'sequenceDiagram',
            'Alice->>Bob: Hi',
            '```',
            'After',
        ].join('\n');

        const result = replaceMermaidBlockAtIndex(input, 1, 'graph LR\nC-->D');

        expect(result).toBe([
            'Before',
            '```mermaid',
            'graph TD',
            'A-->B',
            '```',
            'Middle',
            '```mermaid',
            'graph LR',
            'C-->D',
            '```',
            'After',
        ].join('\n'));
    });

    it('returns null when the target block does not exist', () => {
        const input = '```mermaid\ngraph TD\nA-->B\n```';

        expect(replaceMermaidBlockAtIndex(input, 1, 'graph LR\nC-->D')).toBeNull();
    });

    it('returns null when the replacement block is unchanged', () => {
        const input = '```mermaid\ngraph TD\nA-->B\n```';

        expect(replaceMermaidBlockAtIndex(input, 0, 'graph TD\nA-->B')).toBeNull();
    });

    it('does not count mermaid-like language fences as mermaid blocks', () => {
        const input = [
            'Before',
            '```mermaid-js',
            'graph TD',
            'A-->B',
            '```',
            'Middle',
            '```mermaid',
            'sequenceDiagram',
            'Alice->>Bob: Hi',
            '```',
            'After',
        ].join('\n');

        const result = replaceMermaidBlockAtIndex(input, 0, 'graph LR\nC-->D');

        expect(result).toBe([
            'Before',
            '```mermaid-js',
            'graph TD',
            'A-->B',
            '```',
            'Middle',
            '```mermaid',
            'graph LR',
            'C-->D',
            '```',
            'After',
        ].join('\n'));
    });
});
