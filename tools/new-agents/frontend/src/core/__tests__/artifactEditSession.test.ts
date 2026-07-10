import { describe, expect, it, vi } from 'vitest';
import { saveArtifactEditSession } from '../artifactEditSession';

const lockedSection = {
    id: 'lock-1',
    stageId: 'CLARIFY',
    heading: '## 范围',
    sectionAnchor: 'h2:范围:1',
    content: '## 范围\n\n锁定的需求范围。',
    createdAt: 1,
};

describe('saveArtifactEditSession', () => {
    it('rejects a locked section before calling the persistence boundary', async () => {
        const updateArtifact = vi.fn();

        expect(saveArtifactEditSession({
            currentRunId: 'run-123',
            currentStageId: 'CLARIFY',
            artifactContent: '# 文档\n\n## 范围\n\n锁定的需求范围。',
            editDraft: '# 文档\n\n## 范围\n\n被修改的范围。',
            locks: [lockedSection],
            latestStageVersion: null,
            updateArtifact,
        })).toEqual({ type: 'locked', sectionTitle: '范围' });

        expect(updateArtifact).not.toHaveBeenCalled();
    });

    it('uses the matching persisted version for an optimistic service save', async () => {
        const updateArtifact = vi.fn().mockResolvedValue({
            stageId: 'CLARIFY',
            content: '# 服务端新产物',
            versionNumber: 8,
        });

        await expect(saveArtifactEditSession({
            currentRunId: 'run-123',
            currentStageId: 'CLARIFY',
            artifactContent: '# 当前产物',
            editDraft: '# 编辑后的产物',
            locks: [],
            latestStageVersion: {
                id: 'run-123-CLARIFY-v7',
                timestamp: 1,
                content: '# 当前产物',
                stageId: 'CLARIFY',
            },
            updateArtifact,
        })).resolves.toEqual({
            type: 'saved',
            content: '# 服务端新产物',
            versionId: 'run-123-CLARIFY-v8',
        });

        expect(updateArtifact).toHaveBeenCalledWith(
            'run-123',
            'CLARIFY',
            '# 编辑后的产物',
            { expectedVersionNumber: 7 },
        );
    });
});
