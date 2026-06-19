import { describe, it, expect } from 'vitest';
import mermaid from 'mermaid';
import { sanitizeMermaidCode, aggressiveSanitize } from '../utils/mermaidSanitizer';

describe('Mermaid Sanitizer', () => {
    const validateMermaid = async (code: string) => {
        mermaid.initialize({ startOnLoad: false, securityLevel: 'loose' });
        await mermaid.parse(code);
    };

    describe('sanitizeMermaidCode', () => {
        it('should remove HTML line break tags', () => {
            const input = 'A[Hello<br>World] --> B[Test<br/>Cases]';
            const expected = 'A[Hello\\nWorld] --> B[Test\\nCases]';
            expect(sanitizeMermaidCode(input)).toBe(expected);
        });

        it('should remove general HTML tags', () => {
            const input = 'A[<b>Bold</b> text] --> B[<i>Italic</i>]';
            const expected = 'A[Bold text] --> B[Italic]';
            expect(sanitizeMermaidCode(input)).toBe(expected);
        });

        it('should automatically wrap node text with special characters in quotes', () => {
            const input = 'A[Node (with parentheses)] --> B[Node <with brackets>]';
            const expected = 'A["Node (with parentheses)"] --> B["Node <with brackets>"]';
            expect(sanitizeMermaidCode(input)).toBe(expected);
        });

        it('should not wrap already quoted strings', () => {
            const input = 'A["Already (quoted)"] --> B';
            expect(sanitizeMermaidCode(input)).toBe(input);
        });

        it('should remove invisible characters', () => {
            const input = 'A[Hello\u00A0World] --> B[\u200BTest]';
            const expected = 'A[Hello World] --> B[Test]';
            expect(sanitizeMermaidCode(input)).toBe(expected);
        });

        it('should normalize line endings', () => {
            const input = 'graph TD\r\nA --> B\r\nB --> C';
            const expected = 'graph TD\nA --> B\nB --> C';
            expect(sanitizeMermaidCode(input)).toBe(expected);
        });

        it('should split collapsed quadrantChart axis directives into parseable lines', async () => {
            const input = [
                'quadrantChart',
                'title 登录功能风险矩阵 x-axis 低发生概率 --> 高发生概率',
                'y-axis 低严重度 --> 高严重度',
                'quadrant-1 高优先级',
                'quadrant-2 重点关注',
                '登录失败锁定: [0.7, 0.8]',
            ].join('\n');

            await validateMermaid(sanitizeMermaidCode(input));
        });

        it('should normalize LLM block-beta group syntax into parseable block nodes', async () => {
            const input = [
                'block-beta',
                '    columns 1 block["UI 端到端测试 (10%)"] {',
                '      login["登录主链路"]',
                '    }',
            ].join('\n');

            await validateMermaid(sanitizeMermaidCode(input));
        });
    });

    describe('aggressiveSanitize', () => {
        it('should preserve standard Mermaid syntax but strip non-standard characters from nodes', () => {
            // Aggressive sanitize replaces complex inner text with simple alphanumeric text if quote wrapping fails
            const input = 'A["Extremely !@#$% Complex (Node)"] --> B';
            // This test depends on the specific aggressive fallback implementation
            const result = aggressiveSanitize(input);
            // Verify it still parses basic structure
            expect(result).toContain('A[');
            expect(result).toContain('] --> B');
            expect(result).not.toContain('!@#$%');
        });
    });
});
