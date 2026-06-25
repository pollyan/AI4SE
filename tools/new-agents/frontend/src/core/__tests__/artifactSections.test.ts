import { describe, expect, it } from 'vitest';
import {
  buildArtifactSectionChangeIndex,
  extractArtifactSections,
} from '../artifactSections';

describe('artifactSections', () => {
  it('reports only the section whose body changed', () => {
    const changes = buildArtifactSectionChangeIndex(
      '# 文档\n\n## 范围\n\n旧范围\n\n## 风险\n\n保持不变',
      '# 文档\n\n## 范围\n\n新范围\n\n## 风险\n\n保持不变',
    );

    expect(changes).toEqual([
      expect.objectContaining({
        kind: 'modified',
        title: '范围',
        anchor: 'h2:范围:1',
        safeForPatch: true,
      }),
    ]);
  });

  it('ignores markdown headings inside fenced code blocks', () => {
    const sections = extractArtifactSections(
      '# 文档\n\n```md\n## 伪标题\n```\n\n## 真实标题\n\n正文',
    );

    expect(sections.map(section => section.title)).toEqual(['文档', '真实标题']);
  });

  it('uses occurrence anchors for duplicate headings', () => {
    const sections = extractArtifactSections(
      '# 文档\n\n## 风险\n\n第一处\n\n## 风险\n\n第二处',
    );

    expect(sections.map(section => section.anchor)).toEqual([
      'h1:文档:1',
      'h2:风险:1',
      'h2:风险:2',
    ]);
    expect(sections.map(section => section.displayTitle)).toEqual([
      '文档',
      '风险 #1',
      '风险 #2',
    ]);
  });

  it('marks structured markdown sections as unsafe for automatic patching', () => {
    const changes = buildArtifactSectionChangeIndex(
      '# 文档\n\n## 表格\n\n| 字段 | 内容 |\n| --- | --- |\n| A | 旧值 |',
      '# 文档\n\n## 表格\n\n| 字段 | 内容 |\n| --- | --- |\n| A | 新值 |',
    );

    expect(changes).toEqual([
      expect.objectContaining({
        kind: 'modified',
        title: '表格',
        safeForPatch: false,
        unsafeReason: 'markdown_table',
      }),
    ]);
  });
});
