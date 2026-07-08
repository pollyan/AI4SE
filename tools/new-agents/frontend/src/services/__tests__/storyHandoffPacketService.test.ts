import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
    createStoryHandoffPacket,
    fetchStoryHandoffCandidates,
    fetchStoryHandoffPackets,
} from '../storyHandoffPacketService';

global.fetch = vi.fn();

describe('storyHandoffPacketService', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('fetches ready story handoff candidates for a persisted run', async () => {
        vi.mocked(fetch).mockResolvedValue(new Response(
            JSON.stringify({
                runId: 'alex-run-123',
                workflowId: 'USER_STORY_BREAKDOWN',
                stageId: 'HANDOFF',
                sourceArtifactVersion: 1,
                sourceArtifactDigest: 'sha256:abc123',
                candidates: [
                    {
                        storyId: 'US-001',
                        title: '生成澄清问题',
                        requirementIds: ['REQ-001'],
                        userValue: '测试负责人能在设计前发现缺失业务规则',
                        readyReason: '验收标准和业务规则已明确',
                    },
                ],
            }),
            {
                status: 200,
                headers: { 'Content-Type': 'application/json' },
            },
        ));

        const result = await fetchStoryHandoffCandidates('alex-run-123', 'HANDOFF');

        expect(fetch).toHaveBeenCalledWith(
            '/new-agents/api/agent/runs/alex-run-123/story-handoff-candidates?stageId=HANDOFF'
        );
        expect(result.candidates).toEqual([
            expect.objectContaining({
                storyId: 'US-001',
                requirementIds: ['REQ-001'],
            }),
        ]);
    });

    it('creates a story handoff packet with stage and story id', async () => {
        vi.mocked(fetch).mockResolvedValue(new Response(
            JSON.stringify({
                sourceRunId: 'alex-run-123',
                sourceWorkflowId: 'USER_STORY_BREAKDOWN',
                sourceStageId: 'HANDOFF',
                sourceArtifactVersion: 1,
                sourceArtifactDigest: 'sha256:abc123',
                createdAt: 1710000000000,
                storyId: 'US-001',
                requirementIds: ['REQ-001'],
                userStory: '作为测试负责人，我想看到澄清问题，以便补齐规则。',
                acceptanceCriteria: ['输出需求事实清单'],
                businessRules: ['问题必须标注责任方'],
                nonFunctionalNotes: ['可追溯'],
                outOfScope: ['不直接生成用例'],
                dependencies: ['用户提供需求文本'],
                openQuestions: ['问题分类口径待校准'],
            }),
            {
                status: 200,
                headers: { 'Content-Type': 'application/json' },
            },
        ));

        const packet = await createStoryHandoffPacket('alex-run-123', 'HANDOFF', 'US-001');

        expect(fetch).toHaveBeenCalledWith(
            '/new-agents/api/agent/runs/alex-run-123/story-handoff-packets',
            {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ stageId: 'HANDOFF', storyId: 'US-001' }),
            },
        );
        expect(packet.storyId).toBe('US-001');
        expect(packet.requirementIds).toEqual(['REQ-001']);
    });

    it('fetches saved story handoff packets with stale metadata', async () => {
        vi.mocked(fetch).mockResolvedValue(new Response(
            JSON.stringify({
                runId: 'alex-run-123',
                workflowId: 'USER_STORY_BREAKDOWN',
                stageId: 'HANDOFF',
                sourceArtifactVersion: 2,
                sourceArtifactDigest: 'sha256:new',
                packets: [
                    {
                        id: '1',
                        storyId: 'US-001',
                        createdAt: 1710000000000,
                        isStale: true,
                        currentSourceArtifactVersion: 2,
                        currentSourceArtifactDigest: 'sha256:new',
                        packet: {
                            sourceRunId: 'alex-run-123',
                            sourceWorkflowId: 'USER_STORY_BREAKDOWN',
                            sourceStageId: 'HANDOFF',
                            sourceArtifactVersion: 1,
                            sourceArtifactDigest: 'sha256:old',
                            createdAt: 1710000000000,
                            storyId: 'US-001',
                            requirementIds: ['REQ-001'],
                            userStory: '作为测试负责人，我想看到澄清问题，以便补齐规则。',
                            acceptanceCriteria: ['输出需求事实清单'],
                            businessRules: ['问题必须标注责任方'],
                            nonFunctionalNotes: ['可追溯'],
                            outOfScope: ['不直接生成用例'],
                            dependencies: ['用户提供需求文本'],
                            openQuestions: ['问题分类口径待校准'],
                        },
                    },
                ],
            }),
            {
                status: 200,
                headers: { 'Content-Type': 'application/json' },
            },
        ));

        const result = await fetchStoryHandoffPackets('alex-run-123', 'HANDOFF');

        expect(fetch).toHaveBeenCalledWith(
            '/new-agents/api/agent/runs/alex-run-123/story-handoff-packets?stageId=HANDOFF'
        );
        expect(result.packets[0]).toMatchObject({
            id: '1',
            storyId: 'US-001',
            isStale: true,
            currentSourceArtifactVersion: 2,
        });
    });

    it('fails explicitly when packet response is malformed', async () => {
        vi.mocked(fetch).mockResolvedValue(new Response(
            JSON.stringify({
                runId: 'alex-run-123',
                workflowId: 'USER_STORY_BREAKDOWN',
                stageId: 'HANDOFF',
                sourceArtifactVersion: 1,
                sourceArtifactDigest: 'sha256:abc123',
                packets: [
                    {
                        id: '1',
                        packet: {
                            storyId: 'US-001',
                        },
                    },
                ],
            }),
            {
                status: 200,
                headers: { 'Content-Type': 'application/json' },
            },
        ));

        await expect(
            fetchStoryHandoffPackets('alex-run-123', 'HANDOFF')
        ).rejects.toThrow('Invalid story handoff packet response');
    });
});
