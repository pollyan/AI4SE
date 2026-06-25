import { describe, expect, it } from 'vitest';
import {
  applyArtifactSectionPatch,
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

  it('applies a same-base section replace patch and reports the changed section', () => {
    const base = '# 文档\n\n## 范围\n\n旧范围\n\n## 风险\n\n保持不变';
    const result = applyArtifactSectionPatch(base, {
      operation: 'replace',
      sectionAnchor: 'h2:范围:1',
      replacementMarkdown: '## 范围\n\n新范围',
      baseContent: base,
    });

    expect(result).toEqual(expect.objectContaining({
      applied: true,
      content: '# 文档\n\n## 范围\n\n新范围\n\n## 风险\n\n保持不变',
    }));
    expect(result.changes).toEqual([
      expect.objectContaining({
        kind: 'modified',
        anchor: 'h2:范围:1',
      }),
    ]);
  });

  it('applies an add_after patch after an existing section', () => {
    const base = '# 文档\n\n## 范围\n\n旧范围';
    const result = applyArtifactSectionPatch(base, {
      operation: 'add_after',
      sectionAnchor: 'h2:风险:1',
      afterSectionAnchor: 'h2:范围:1',
      replacementMarkdown: '## 风险\n\n| 风险 | 状态 |\n| --- | --- |\n| R1 | 待处理 |',
      baseContent: base,
    });

    expect(result).toEqual(expect.objectContaining({
      applied: true,
      content: '# 文档\n\n## 范围\n\n旧范围\n\n## 风险\n\n| 风险 | 状态 |\n| --- | --- |\n| R1 | 待处理 |',
    }));
    expect(result.changes).toEqual([
      expect.objectContaining({
        kind: 'added',
        anchor: 'h2:风险:1',
      }),
    ]);
  });

  it('rejects add_after patches without an insertion anchor', () => {
    const base = '# 文档\n\n## 范围\n\n旧范围';

    const result = applyArtifactSectionPatch(base, {
      operation: 'add_after',
      sectionAnchor: 'h2:风险:1',
      replacementMarkdown: '## 风险\n\n新风险',
      baseContent: base,
    });

    expect(result).toEqual({
      applied: false,
      content: base,
      changes: [],
      fallbackReason: 'invalid_patch',
    });
  });

  it('rejects section patches when the current content no longer matches the base', () => {
    const base = '# 文档\n\n## 范围\n\n旧范围';
    const current = '# 文档\n\n## 范围\n\n用户已手动修改';

    const result = applyArtifactSectionPatch(current, {
      operation: 'replace',
      sectionAnchor: 'h2:范围:1',
      replacementMarkdown: '## 范围\n\n新范围',
      baseContent: base,
    });

    expect(result).toEqual({
      applied: false,
      content: current,
      changes: [],
      fallbackReason: 'base_mismatch',
    });
  });

  it('rejects section patches when the anchor cannot be found', () => {
    const current = '# 文档\n\n## 范围\n\n旧范围';

    const result = applyArtifactSectionPatch(current, {
      operation: 'replace',
      sectionAnchor: 'h2:不存在:1',
      replacementMarkdown: '## 不存在\n\n新范围',
      baseContent: current,
    });

    expect(result.fallbackReason).toBe('section_not_found');
    expect(result.content).toBe(current);
  });

  it('rejects section patches for unsafe structured markdown sections', () => {
    const current = '# 文档\n\n## 表格\n\n| 字段 | 内容 |\n| --- | --- |\n| A | 旧值 |';

    const result = applyArtifactSectionPatch(current, {
      operation: 'replace',
      sectionAnchor: 'h2:表格:1',
      replacementMarkdown: '## 表格\n\n| 字段 | 内容 |\n| --- | --- |\n| A | 新值 |',
      baseContent: current,
    });

    expect(result).toEqual({
      applied: false,
      content: current,
      changes: [],
      fallbackReason: 'unsafe_section',
    });
  });
});
