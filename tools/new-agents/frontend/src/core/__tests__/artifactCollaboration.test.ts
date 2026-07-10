import { describe, expect, it, vi } from 'vitest';
import { syncArtifactCollaboration } from '../artifactCollaboration';

describe('syncArtifactCollaboration', () => {
    it('does not persist local-only collaboration state', async () => {
        const updateCollaboration = vi.fn();

        await expect(syncArtifactCollaboration({
            runId: null,
            comments: [],
            sectionLocks: [],
            updateCollaboration,
        })).resolves.toBeNull();

        expect(updateCollaboration).not.toHaveBeenCalled();
    });

    it('returns a display-safe error when collaboration persistence fails', async () => {
        const updateCollaboration = vi.fn().mockRejectedValue(new Error('network unavailable'));

        await expect(syncArtifactCollaboration({
            runId: 'run-123',
            comments: [],
            sectionLocks: [],
            updateCollaboration,
        })).resolves.toBe('协作状态保存失败：network unavailable');
    });
});
