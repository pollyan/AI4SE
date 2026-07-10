import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { StoryHandoffPacketPanel } from '../StoryHandoffPacketPanel';

const {
    mockFetchCandidates,
    mockFetchPackets,
    mockCreatePacket,
} = vi.hoisted(() => ({
    mockFetchCandidates: vi.fn(),
    mockFetchPackets: vi.fn(),
    mockCreatePacket: vi.fn(),
}));

vi.mock('../../services/storyHandoffPacketService', () => ({
    fetchStoryHandoffCandidates: mockFetchCandidates,
    fetchStoryHandoffPackets: mockFetchPackets,
    createStoryHandoffPacket: mockCreatePacket,
}));

const packet = {
    sourceRunId: 'run-123',
    sourceWorkflowId: 'STORY_BREAKDOWN' as const,
    sourceStageId: 'SPRINT_PLAN',
    sourceArtifactVersion: 1,
    sourceArtifactDigest: 'sha256:story',
    createdAt: 1710000000000,
    storyId: 'US-001',
    requirementIds: ['REQ-001'],
    userStory: '作为负责人，我想生成需求包。',
    acceptanceCriteria: ['Given ready story When 生成 Then 可复制 JSON'],
    businessRules: [],
    nonFunctionalNotes: [],
    outOfScope: [],
    dependencies: [],
    openQuestions: [],
};

const candidatesResponse = {
    runId: 'run-123',
    workflowId: 'STORY_BREAKDOWN' as const,
    stageId: 'SPRINT_PLAN',
    sourceArtifactVersion: 1,
    sourceArtifactDigest: 'sha256:story',
    candidates: [{
        storyId: 'US-001',
        title: '生成需求包',
        requirementIds: ['REQ-001'],
        userValue: '交给 AI Coding 前保留需求追溯。',
        readyReason: '验收标准已明确',
    }],
};

const emptyPacketsResponse = {
    runId: 'run-123',
    workflowId: 'STORY_BREAKDOWN' as const,
    stageId: 'SPRINT_PLAN',
    sourceArtifactVersion: 1,
    sourceArtifactDigest: 'sha256:story',
    packets: [],
};

describe('StoryHandoffPacketPanel', () => {
    it('generates a packet and refreshes the persisted packet list', async () => {
        mockFetchCandidates.mockResolvedValue(candidatesResponse);
        mockFetchPackets
            .mockResolvedValueOnce(emptyPacketsResponse)
            .mockResolvedValueOnce({
                ...emptyPacketsResponse,
                packets: [{
                    id: 'packet-1',
                    storyId: 'US-001',
                    createdAt: 1710000000000,
                    isStale: false,
                    currentSourceArtifactVersion: 1,
                    currentSourceArtifactDigest: 'sha256:story',
                    packet,
                }],
            });
        mockCreatePacket.mockResolvedValue(packet);

        render(<StoryHandoffPacketPanel runId="run-123" stageId="SPRINT_PLAN" />);

        fireEvent.click(await screen.findByRole('button', { name: '生成 US-001 需求包' }));

        await waitFor(() => {
            expect(mockCreatePacket).toHaveBeenCalledWith('run-123', 'SPRINT_PLAN', 'US-001');
            expect(screen.getByRole('button', { name: '复制 US-001 需求包' })).toBeTruthy();
        });
    });

    it('marks persisted stale packets for explicit regeneration', async () => {
        mockFetchCandidates.mockResolvedValue(candidatesResponse);
        mockFetchPackets.mockResolvedValue({
            ...emptyPacketsResponse,
            packets: [{
                id: 'packet-1',
                storyId: 'US-001',
                createdAt: 1710000000000,
                isStale: true,
                currentSourceArtifactVersion: 2,
                currentSourceArtifactDigest: 'sha256:newer',
                packet,
            }],
        });

        render(<StoryHandoffPacketPanel runId="run-123" stageId="SPRINT_PLAN" />);

        expect(await screen.findByText('该需求包可能基于旧版需求，请重新生成后再交给 AI Coding。')).toBeTruthy();
    });
});
