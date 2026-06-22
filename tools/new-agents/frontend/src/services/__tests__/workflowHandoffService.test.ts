import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fetchWorkflowHandoffs, startWorkflowHandoff } from '../workflowHandoffService';

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
                        context: {
                            sourceArtifactTitle: 'AI 测试资产管理平台需求蓝图',
                            sourceArtifactSummary: 'AI 测试资产管理平台需求蓝图；Lisa handoff 输入 3 项',
                            targetInputSummary: '交给 TEST_DESIGN/CLARIFY 使用：需求 F-001、验收标准 AC-001、约束 NFR-001',
                            unconfirmedItems: ['约束 NFR-001: 数据权限边界待确认'],
                        },
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
                context: {
                    sourceArtifactTitle: 'AI 测试资产管理平台需求蓝图',
                    sourceArtifactSummary: 'AI 测试资产管理平台需求蓝图；Lisa handoff 输入 3 项',
                    targetInputSummary: '交给 TEST_DESIGN/CLARIFY 使用：需求 F-001、验收标准 AC-001、约束 NFR-001',
                    unconfirmedItems: ['约束 NFR-001: 数据权限边界待确认'],
                },
                prompt: '请基于 Alex 的价值蓝图设计测试策略。',
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

    it('should fail explicitly when handoff context is malformed', async () => {
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
                        context: {
                            sourceArtifactTitle: 42,
                        },
                        prompt: '请基于 Alex 的价值蓝图设计测试策略。',
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
                context: {
                    sourceArtifactTitle: 'AI 测试资产管理平台需求蓝图',
                    sourceArtifactSummary: 'AI 测试资产管理平台需求蓝图；Lisa handoff 输入 3 项',
                    targetInputSummary: '交给 TEST_DESIGN/CLARIFY 使用：需求 F-001、验收标准 AC-001、约束 NFR-001',
                    unconfirmedItems: ['约束 NFR-001: 数据权限边界待确认'],
                },
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
        expect(handoff.context?.unconfirmedItems).toEqual(['约束 NFR-001: 数据权限边界待确认']);
    });
});
