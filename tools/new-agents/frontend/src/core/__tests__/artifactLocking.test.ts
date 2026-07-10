import { describe, expect, it } from 'vitest';
import { findLockedSectionChange } from '../artifactLocking';

const lockedSection = {
    id: 'lock-1',
    stageId: 'CLARIFY',
    heading: '## 范围',
    sectionAnchor: 'h2:范围:1',
    content: '## 范围\n\n锁定的需求范围。',
    createdAt: 1,
};

describe('findLockedSectionChange', () => {
    it('allows edits outside a locked section', () => {
        expect(findLockedSectionChange({
            currentContent: '# 文档\n\n## 范围\n\n锁定的需求范围。\n\n## 风险\n\n旧风险。',
            nextContent: '# 文档\n\n## 范围\n\n锁定的需求范围。\n\n## 风险\n\n新风险。',
            locks: [lockedSection],
        })).toBeNull();
    });

    it('reports the display title when an anchored locked section changes', () => {
        expect(findLockedSectionChange({
            currentContent: '# 文档\n\n## 范围\n\n锁定的需求范围。\n\n## 风险\n\n旧风险。',
            nextContent: '# 文档\n\n## 范围\n\n被修改的范围。\n\n## 风险\n\n旧风险。',
            locks: [lockedSection],
        })).toBe('范围');
    });
});
