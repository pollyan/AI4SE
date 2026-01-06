import { describe, it, expect } from 'vitest';

describe('Artifact Regex Logic', () => {
    const artifactRegex = /:::artifact\s*([\s\S]*?)(\s*:::|$)/;
    const mask = '\n*(已更新右侧分析成果)*\n';

    it('should correctly replace artifact tags with mask', () => {
        const input = '这是分析结果：\n:::artifact\n{"test": "data"}\n:::\n希望能帮到你。';
        // Note: replace will keep surrounded text. 
        // Our regex matches from :::artifact to :::
        const result = input.replace(artifactRegex, mask);

        expect(result).toContain('这是分析结果：');
        expect(result).toContain('(已更新右侧分析成果)');
        expect(result).toContain('希望能帮到你。');
        expect(result).not.toContain('{"test": "data"}');
    });

    it('should handle unclosed artifacts (streaming case)', () => {
        const input = 'Wait, here it comes: :::artifact\n{"partial": "json"';
        const result = input.replace(artifactRegex, mask);

        expect(result).toContain('Wait, here it comes: ');
        expect(result).toContain('(已更新右侧分析成果)');
        expect(result).not.toContain('"partial"');
    });

    it('should handle multiline content inside artifact', () => {
        const input = 'Start\n:::artifact\nLine 1\nLine 2\n:::\nEnd';
        const result = input.replace(artifactRegex, mask);

        expect(result).toBe('Start\n' + mask + '\nEnd');
    });
});
