import { describe, it, expect } from 'vitest';
import { sanitizeMermaidCode, aggressiveSanitize } from '../utils/mermaidSanitizer';

describe('Mermaid Sanitizer', () => {
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

        it('should normalize quadrantChart axis and quadrant labels emitted on one line', () => {
            const input = [
                'quadrantChart',
                '    title 风险优先级矩阵 x-axis 低影响 --> 高影响 y-axis 低概率 --> 高概率 quadrant-1 重点验证 quadrant-2 监控 quadrant-3 接受 quadrant-4 补充分析',
                '    登录风险: [0.8, 0.6]',
            ].join('\n');

            expect(sanitizeMermaidCode(input)).toBe([
                'quadrantChart',
                '    title 风险优先级矩阵',
                '    x-axis "低影响" --> "高影响"',
                '    y-axis "低概率" --> "高概率"',
                '    quadrant-1 "重点验证"',
                '    quadrant-2 "监控"',
                '    quadrant-3 "接受"',
                '    quadrant-4 "补充分析"',
                '    "登录风险": [0.8, 0.6]',
            ].join('\n'));
        });

        it('should normalize unsupported block-beta grouped block syntax', () => {
            const input = [
                'block-beta',
                '    columns 1 block["测试分层"] {',
                '        e2e["端到端验证"]',
                '    }',
            ].join('\n');

            expect(sanitizeMermaidCode(input)).toBe([
                'block-beta',
                '    columns 1',
                '    block_1["测试分层"]',
                '        e2e["端到端验证"]',
            ].join('\n'));
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
