import { describe, expect, it } from 'vitest';
import {
    buildConflictRefreshHistory,
    updateArtifactHistoryContent,
} from '../artifactHistorySession';

describe('artifact history session', () => {
    it('restores a removed history block at its original location without duplicating existing lines', () => {
        expect(updateArtifactHistoryContent({
            operation: 'restore',
            currentContent: '# 文档\n\n当前风险',
            historicalContent: '# 文档\n\n历史范围\n\n当前风险',
            lines: ['历史范围', '当前风险'],
        })).toBe('# 文档\n\n历史范围\n当前风险');
    });

    it('builds durable local draft and server versions when refreshing an optimistic-save conflict', () => {
        expect(buildConflictRefreshHistory({
            currentRunId: 'run-123',
            currentStageId: 'STRATEGY',
            artifactContent: '# 当前版本',
            latestVersionContent: '# 当前版本',
            draftContent: '# 用户草稿',
            serverArtifact: {
                stageId: 'STRATEGY',
                content: '# 服务端版本',
                versionNumber: 3,
            },
            timestamp: 100,
        })).toEqual({
            content: '# 服务端版本',
            versions: [
                {
                    id: 'conflict-draft-100',
                    timestamp: 101,
                    content: '# 用户草稿',
                    stageId: 'STRATEGY',
                },
                {
                    id: 'run-123-STRATEGY-v3',
                    timestamp: 102,
                    content: '# 服务端版本',
                    stageId: 'STRATEGY',
                },
            ],
        });
    });
});
