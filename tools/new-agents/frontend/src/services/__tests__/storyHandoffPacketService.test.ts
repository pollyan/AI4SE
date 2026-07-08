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
                workflowId: 'STORY_BREAKDOWN',
                stageId: 'SPRINT_PLAN',
                sourceArtifactVersion: 1,
                sourceArtifactDigest: 'sha256:abc123',
                candidates: [
                    {
                        storyId: 'US-001',
                        title: '需求澄清基线',
                        requirementIds: ['EPIC-001', 'AC-001'],
                        userValue: '作为测试负责人，我想把需求输入转成澄清清单，以便在开发前发现遗漏。',
                        readyReason: '状态：待评审；可测试性：高；Sprint：Sprint 1',
                    },
                ],
            }),
            {
                status: 200,
                headers: { 'Content-Type': 'application/json' },
            },
        ));

        const result = await fetchStoryHandoffCandidates('alex-run-123', 'SPRINT_PLAN');

        expect(fetch).toHaveBeenCalledWith(
            '/new-agents/api/agent/runs/alex-run-123/story-handoff-candidates?stageId=SPRINT_PLAN'
        );
        expect(result.candidates).toEqual([
            expect.objectContaining({
                storyId: 'US-001',
                requirementIds: ['EPIC-001', 'AC-001'],
            }),
        ]);
    });

    it('creates a story handoff packet with stage and story id', async () => {
        vi.mocked(fetch).mockResolvedValue(new Response(
            JSON.stringify({
                sourceRunId: 'alex-run-123',
                sourceWorkflowId: 'STORY_BREAKDOWN',
                sourceStageId: 'SPRINT_PLAN',
                sourceArtifactVersion: 1,
                sourceArtifactDigest: 'sha256:abc123',
                createdAt: 1710000000000,
                storyId: 'US-001',
                requirementIds: ['EPIC-001', 'AC-001'],
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

        const packet = await createStoryHandoffPacket('alex-run-123', 'SPRINT_PLAN', 'US-001');

        expect(fetch).toHaveBeenCalledWith(
            '/new-agents/api/agent/runs/alex-run-123/story-handoff-packets',
            {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ stageId: 'SPRINT_PLAN', storyId: 'US-001' }),
            },
        );
        expect(packet.storyId).toBe('US-001');
        expect(packet.requirementIds).toEqual(['EPIC-001', 'AC-001']);
    });

    it('fetches saved story handoff packets with stale metadata', async () => {
        vi.mocked(fetch).mockResolvedValue(new Response(
            JSON.stringify({
                runId: 'alex-run-123',
                workflowId: 'STORY_BREAKDOWN',
                stageId: 'SPRINT_PLAN',
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
                            sourceWorkflowId: 'STORY_BREAKDOWN',
                            sourceStageId: 'SPRINT_PLAN',
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

        const result = await fetchStoryHandoffPackets('alex-run-123', 'SPRINT_PLAN');

        expect(fetch).toHaveBeenCalledWith(
            '/new-agents/api/agent/runs/alex-run-123/story-handoff-packets?stageId=SPRINT_PLAN'
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
                workflowId: 'STORY_BREAKDOWN',
                stageId: 'SPRINT_PLAN',
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
            fetchStoryHandoffPackets('alex-run-123', 'SPRINT_PLAN')
        ).rejects.toThrow('Invalid story handoff packet response');
    });
});
