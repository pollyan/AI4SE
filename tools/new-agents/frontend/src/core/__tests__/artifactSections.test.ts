import { describe, expect, it } from 'vitest';
import {
    ArtifactSectionRegenerationError,
    mergeRegeneratedArtifactSection,
    parseArtifactMarkdownSections,
    preserveLockedArtifactSections,
} from '../artifactSections';
import type { ArtifactSectionLock } from '../types';

const makeLock = (
    overrides: Partial<ArtifactSectionLock> & Pick<ArtifactSectionLock, 'heading' | 'content'>
): ArtifactSectionLock => ({
    id: 'lock-1',
    stageId: 'CLARIFY',
    sectionAnchor: null,
    createdAt: 1,
    ...overrides,
});

describe('artifactSections', () => {
    it('parses H1-H3 sections with stable duplicate anchors', () => {
        const sections = parseArtifactMarkdownSections([
            '# 需求分析',
            '背景',
            '## 验收口径',
            '第一版',
            '## 验收口径',
            '第二版',
            '#### 忽略的深层标题',
            '仍属于第二版',
        ].join('\n'));

        expect(sections.map(section => ({
            heading: section.heading,
            displayTitle: section.displayTitle,
            anchor: section.anchor,
        }))).toEqual([
            { heading: '# 需求分析', displayTitle: '需求分析', anchor: 'h1:需求分析:1' },
            { heading: '## 验收口径', displayTitle: '验收口径 #1', anchor: 'h2:验收口径:1' },
            { heading: '## 验收口径', displayTitle: '验收口径 #2', anchor: 'h2:验收口径:2' },
        ]);
        expect(sections[2].content).toContain('#### 忽略的深层标题');
    });

    it('preserves locked sections by anchor before heading', () => {
        const nextArtifact = [
            '# 当前产物',
            '导语',
            '## 验收口径',
            '模型误改第一段',
            '## 验收口径',
            '模型误改第二段',
        ].join('\n');
        const lock = makeLock({
            heading: '## 验收口径',
            sectionAnchor: 'h2:验收口径:2',
            content: '## 验收口径\n已确认第二段',
        });

        expect(preserveLockedArtifactSections(nextArtifact, [lock])).toBe([
            '# 当前产物',
            '导语',
            '## 验收口径',
            '模型误改第一段',
            '## 验收口径',
            '已确认第二段',
        ].join('\n'));
    });

    it('merges only the regenerated target section and restores locked sections', () => {
        const originalArtifact = [
            '# 当前产物',
            '旧导语',
            '## 目标章节',
            '旧目标内容',
            '## 锁定章节',
            '确认内容',
        ].join('\n');
        const generatedArtifact = [
            '# 当前产物',
            '模型试图改导语',
            '## 目标章节',
            '新目标内容',
            '## 锁定章节',
            '模型误改锁定内容',
        ].join('\n');
        const lock = makeLock({
            heading: '## 锁定章节',
            sectionAnchor: 'h2:锁定章节:1',
            content: '## 锁定章节\n确认内容',
        });

        const merged = mergeRegeneratedArtifactSection({
            originalArtifact,
            generatedArtifact,
            target: {
                heading: '## 目标章节',
                sectionAnchor: 'h2:目标章节:1',
                displayTitle: '目标章节',
            },
            locks: [lock],
        });

        expect(merged.content).toBe([
            '# 当前产物',
            '旧导语',
            '## 目标章节',
            '新目标内容',
            '## 锁定章节',
            '确认内容',
        ].join('\n'));
    });

    it('refuses to regenerate a locked target section', () => {
        const artifact = [
            '# 当前产物',
            '导语',
            '## 目标章节',
            '确认内容',
        ].join('\n');
        const lock = makeLock({
            heading: '## 目标章节',
            sectionAnchor: 'h2:目标章节:1',
            content: '## 目标章节\n确认内容',
        });

        expect(() => mergeRegeneratedArtifactSection({
            originalArtifact: artifact,
            generatedArtifact: artifact,
            target: {
                heading: '## 目标章节',
                sectionAnchor: 'h2:目标章节:1',
                displayTitle: '目标章节',
            },
            locks: [lock],
        })).toThrow(ArtifactSectionRegenerationError);
    });

    it('fails when the generated artifact does not contain the target section', () => {
        const originalArtifact = [
            '# 当前产物',
            '导语',
            '## 目标章节',
            '旧内容',
        ].join('\n');
        const generatedArtifact = [
            '# 当前产物',
            '导语',
            '## 其他章节',
            '新内容',
        ].join('\n');

        expect(() => mergeRegeneratedArtifactSection({
            originalArtifact,
            generatedArtifact,
            target: {
                heading: '## 目标章节',
                sectionAnchor: 'h2:目标章节:1',
                displayTitle: '目标章节',
            },
            locks: [],
        })).toThrow('模型返回中没有找到目标章节“目标章节”');
    });
});
