import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
    fetchTargetWorkflowHandoffCandidates,
    fetchWorkflowHandoffs,
    startWorkflowHandoff,
} from '../workflowHandoffService';

global.fetch = vi.fn();

describe('workflowHandoffService', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('should fetch handoff candidates for a persisted run', async () => {
        vi.mocked(fetch).mockResolvedValue(new Response(
            JSON.stringify({
                runId: 'alex-run-123',
                sourceWorkflowId: 'VALUE_DISCOVERY',
                handoffs: [
                    {
                        id: 'handoff-1',
                        label: '交给 Lisa 做测试设计',
                        sourceWorkflowId: 'VALUE_DISCOVERY',
                        sourceStageId: 'BLUEPRINT',
                        sourceArtifactVersion: 2,
                        targetWorkflowId: 'TEST_DESIGN',
                        targetStageId: 'CLARIFY',
                        targetAgentId: 'lisa',
                        prompt: '请基于 Alex 的价值蓝图设计测试策略。',
                    },
                ],
            }),
            {
                status: 200,
                headers: { 'Content-Type': 'application/json' },
            },
        ));

        const handoffs = await fetchWorkflowHandoffs('alex-run-123');

        expect(fetch).toHaveBeenCalledWith('/new-agents/api/agent/runs/alex-run-123/handoffs');
        expect(handoffs).toEqual([
            expect.objectContaining({
                id: 'handoff-1',
                targetWorkflowId: 'TEST_DESIGN',
                targetStageId: 'CLARIFY',
                prompt: '请基于 Alex 的价值蓝图设计测试策略。',
            }),
        ]);
    });

    it('should fetch target-side handoff candidates for a workflow start', async () => {
        vi.mocked(fetch).mockResolvedValue(new Response(
            JSON.stringify({
                targetWorkflowId: 'VALUE_DISCOVERY',
                targetStageId: 'ELEVATOR',
                handoffs: [
                    {
                        id: 'idea-brainstorm-concept-to-value-discovery',
                        label: '从产品概念简报继续梳理需求蓝图',
                        sourceRunId: 'idea-run-123',
                        sourceWorkflowId: 'IDEA_BRAINSTORM',
                        sourceStageId: 'CONCEPT',
                        sourceArtifactVersion: 1,
                        sourceArtifactDigest: 'sha256:abc123',
                        sourceArtifactSummary: '# 产品概念简报 AI 测试资产管理平台',
                        targetWorkflowId: 'VALUE_DISCOVERY',
                        targetStageId: 'ELEVATOR',
                        targetAgentId: 'alex',
                        prompt: '请基于产品概念简报继续梳理需求蓝图。',
                    },
                ],
            }),
            {
                status: 200,
                headers: { 'Content-Type': 'application/json' },
            },
        ));

        const handoffs = await fetchTargetWorkflowHandoffCandidates('VALUE_DISCOVERY', 'ELEVATOR');

        expect(fetch).toHaveBeenCalledWith(
            '/new-agents/api/agent/workflow-handoff-candidates?targetWorkflowId=VALUE_DISCOVERY&targetStageId=ELEVATOR'
        );
        expect(handoffs).toEqual([
            expect.objectContaining({
                id: 'idea-brainstorm-concept-to-value-discovery',
                sourceRunId: 'idea-run-123',
                sourceArtifactDigest: 'sha256:abc123',
                sourceArtifactSummary: '# 产品概念简报 AI 测试资产管理平台',
                targetWorkflowId: 'VALUE_DISCOVERY',
                targetStageId: 'ELEVATOR',
            }),
        ]);
    });

    it('should fail explicitly when the handoff payload is malformed', async () => {
        vi.mocked(fetch).mockResolvedValue(new Response(
            JSON.stringify({
                runId: 'alex-run-123',
                handoffs: [
                    {
                        id: 'handoff-1',
                        targetWorkflowId: 'TEST_DESIGN',
                    },
                ],
            }),
            {
                status: 200,
                headers: { 'Content-Type': 'application/json' },
            },
        ));

        await expect(fetchWorkflowHandoffs('alex-run-123')).rejects.toThrow(
            'Invalid workflow handoff response'
        );
    });

    it('should fail explicitly when target-side source metadata is malformed', async () => {
        vi.mocked(fetch).mockResolvedValue(new Response(
            JSON.stringify({
                targetWorkflowId: 'VALUE_DISCOVERY',
                targetStageId: 'ELEVATOR',
                handoffs: [
                    {
                        id: 'idea-brainstorm-concept-to-value-discovery',
                        label: '从产品概念简报继续梳理需求蓝图',
                        sourceRunId: 123,
                        sourceWorkflowId: 'IDEA_BRAINSTORM',
                        sourceStageId: 'CONCEPT',
                        sourceArtifactVersion: 1,
                        targetWorkflowId: 'VALUE_DISCOVERY',
                        targetStageId: 'ELEVATOR',
                        targetAgentId: 'alex',
                        prompt: '请基于产品概念简报继续梳理需求蓝图。',
                    },
                ],
            }),
            {
                status: 200,
                headers: { 'Content-Type': 'application/json' },
            },
        ));

        await expect(
            fetchTargetWorkflowHandoffCandidates('VALUE_DISCOVERY', 'ELEVATOR')
        ).rejects.toThrow('Invalid workflow handoff response');
    });

    it('should start a handoff target run', async () => {
        vi.mocked(fetch).mockResolvedValue(new Response(
            JSON.stringify({
                id: 'handoff-1',
                label: '交给 Lisa 做测试设计',
                sourceRunId: 'alex-run-123',
                sourceWorkflowId: 'VALUE_DISCOVERY',
                sourceStageId: 'BLUEPRINT',
                sourceArtifactVersion: 2,
                targetRunId: 'lisa-run-456',
                targetWorkflowId: 'TEST_DESIGN',
                targetStageId: 'CLARIFY',
                targetAgentId: 'lisa',
                prompt: '请基于 Alex 的价值蓝图设计测试策略。',
            }),
            {
                status: 200,
                headers: { 'Content-Type': 'application/json' },
            },
        ));

        const handoff = await startWorkflowHandoff('alex-run-123', 'handoff-1');

        expect(fetch).toHaveBeenCalledWith(
            '/new-agents/api/agent/runs/alex-run-123/handoffs/handoff-1/start',
            { method: 'POST' }
        );
        expect(handoff.targetRunId).toBe('lisa-run-456');
        expect(handoff.targetWorkflowId).toBe('TEST_DESIGN');
    });
});
