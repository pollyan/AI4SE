import { describe, expect, it } from 'vitest';
import {
    buildArtifactCommentInput,
    getArtifactCommentAnchorStatus,
} from '../artifactComments';

describe('artifact comments', () => {
    it('uses the selected anchor instead of a generated excerpt for a new comment', () => {
        expect(buildArtifactCommentInput({
            stageId: 'CLARIFY',
            draft: '  请确认此范围  ',
            artifactContent: '# 需求\n\n## 范围\n\n默认摘要',
            selectedAnchor: '  登录   范围  ',
        })).toEqual({
            stageId: 'CLARIFY',
            content: '请确认此范围',
            artifactExcerpt: '登录 范围',
            anchorText: '登录 范围',
        });
    });

    it('marks a normalized anchor stale when it is no longer in the artifact', () => {
        expect(getArtifactCommentAnchorStatus(
            '已删除 的 锚点',
            '# 需求\n\n当前内容',
        )).toBe('stale');
    });
});
