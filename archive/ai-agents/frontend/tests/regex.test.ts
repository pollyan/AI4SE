import { describe, it, expect } from 'vitest';

describe('Artifact Regex Logic', () => {
    // Markdown 格式 artifact (旧格式)
    const mdArtifactRegex = /:::artifact\s*([\s\S]*?)(\s*:::|$)/g;
    // XML 格式 artifact (新格式 - 后端输出)
    const xmlArtifactRegex = /<artifact\s+key="[^"]*"\s*>[\s\S]*?(<\/artifact>|$)/g;
    const mask = '\n*(已更新右侧分析成果)*\n';

    describe('Markdown format (:::artifact)', () => {
        it('should correctly replace artifact tags with mask', () => {
            const input = '这是分析结果：\n:::artifact\n{"test": "data"}\n:::\n希望能帮到你。';
            const result = input.replace(mdArtifactRegex, mask);

            expect(result).toContain('这是分析结果：');
            expect(result).toContain('(已更新右侧分析成果)');
            expect(result).toContain('希望能帮到你。');
            expect(result).not.toContain('{"test": "data"}');
        });

        it('should handle unclosed artifacts (streaming case)', () => {
            const input = 'Wait, here it comes: :::artifact\n{"partial": "json"';
            const result = input.replace(mdArtifactRegex, mask);

            expect(result).toContain('Wait, here it comes: ');
            expect(result).toContain('(已更新右侧分析成果)');
            expect(result).not.toContain('"partial"');
        });

        it('should handle multiline content inside artifact', () => {
            const input = 'Start\n:::artifact\nLine 1\nLine 2\n:::\nEnd';
            const result = input.replace(mdArtifactRegex, mask);

            expect(result).toBe('Start\n' + mask + '\nEnd');
        });
    });

    describe('XML format (<artifact key="...">)', () => {
        it('should correctly replace closed XML artifact tags', () => {
            const input = '这是分析结果：\n<artifact key="test_design_requirements">\n# 需求分析文档\n## 1. 需求全景图\n</artifact>\n希望能帮到你。';
            const result = input.replace(xmlArtifactRegex, mask);

            expect(result).toContain('这是分析结果：');
            expect(result).toContain('(已更新右侧分析成果)');
            expect(result).toContain('希望能帮到你。');
            expect(result).not.toContain('需求分析文档');
            expect(result).not.toContain('需求全景图');
        });

        it('should handle unclosed XML artifacts (streaming case)', () => {
            const input = 'Wait, here it comes:\n<artifact key="test_design_requirements">\n# 需求分析文档\n## 1. 需求';
            const result = input.replace(xmlArtifactRegex, mask);

            expect(result).toContain('Wait, here it comes:');
            expect(result).toContain('(已更新右侧分析成果)');
            expect(result).not.toContain('需求分析文档');
        });

        it('should handle multiple XML artifacts in same message', () => {
            const input = '第一个产出物：\n<artifact key="doc1">\n内容1\n</artifact>\n第二个产出物：\n<artifact key="doc2">\n内容2\n</artifact>\n完成。';
            const result = input.replace(xmlArtifactRegex, mask);

            expect(result).toContain('第一个产出物：');
            expect(result).toContain('第二个产出物：');
            expect(result).toContain('完成。');
            expect(result).not.toContain('内容1');
            expect(result).not.toContain('内容2');
            // 应该有两个占位符
            const matchCount = (result.match(/已更新右侧分析成果/g) || []).length;
            expect(matchCount).toBe(2);
        });

        it('should handle artifact with complex markdown content', () => {
            const input = `对话内容
<artifact key="test_design_requirements">
# 需求分析文档

## 1. 需求全景图
\`\`\`mermaid
mindmap
  root((核心需求))
\`\`\`

## 2. 功能详细规格
| ID | 功能名称 |
|----|----------|
| F1 | 登录功能 |
</artifact>
请确认是否准确。`;
            const result = input.replace(xmlArtifactRegex, mask);

            expect(result).toContain('对话内容');
            expect(result).toContain('请确认是否准确。');
            expect(result).not.toContain('需求分析文档');
            expect(result).not.toContain('mermaid');
            expect(result).not.toContain('登录功能');
        });
    });

    describe('Combined formats (both MD and XML)', () => {
        it('should handle both formats in same processing chain', () => {
            const input = '旧格式：\n:::artifact\n旧内容\n:::\n新格式：\n<artifact key="new">\n新内容\n</artifact>\n完成';
            const result = input
                .replace(xmlArtifactRegex, mask)
                .replace(mdArtifactRegex, mask);

            expect(result).toContain('旧格式：');
            expect(result).toContain('新格式：');
            expect(result).toContain('完成');
            expect(result).not.toContain('旧内容');
            expect(result).not.toContain('新内容');
        });
    });
});
