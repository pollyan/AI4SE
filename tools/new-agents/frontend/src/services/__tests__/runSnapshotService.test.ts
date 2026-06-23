import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ArtifactConflictError, cloneRun, createRunDecisionSummary, fetchRunList, fetchRunSnapshot, updateRunArtifact, updateRunArtifactCollaboration, updateRunContextSummary } from '../runSnapshotService';

global.fetch = vi.fn();

describe('runSnapshotService', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('should fetch a persisted run snapshot', async () => {
        vi.mocked(fetch).mockResolvedValue(new Response(
            JSON.stringify({
                run: {
                    id: 'run-123',
                    workflowId: 'TEST_DESIGN',
                    agentId: 'lisa',
                    currentStageId: 'STRATEGY',
                    status: 'active',
                    model: 'test-model',
                },
                messages: [
                    {
                        role: 'user',
                        content: '用户需求: 登录功能',
                        sequenceIndex: 1,
                    },
                ],
                artifacts: [
                    {
                        stageId: 'STRATEGY',
                        content: '# 测试策略蓝图',
                        versionNumber: 2,
                    },
                ],
                contextSummaries: [
                    {
                        sourceType: 'artifact',
                        sourceStageId: 'STRATEGY',
                        summaryType: 'current_artifact',
                        content: '摘要',
                    },
                ],
                artifactComments: [
                    {
                        id: 'comment-1',
                        stageId: 'STRATEGY',
                        content: '这里需要业务确认。',
                        artifactExcerpt: '风险优先级',
                        anchorText: '风险优先级',
                        createdAt: 1710000000000,
                        status: 'resolved',
                        resolvedAt: 1710000000300,
                        replies: [
                            {
                                id: 'reply-1',
                                content: '已补充登录异常边界。',
                                createdAt: 1710000000200,
                            },
                        ],
                    },
                ],
                artifactSectionLocks: [
                    {
                        id: 'lock-1',
                        stageId: 'STRATEGY',
                        heading: '## 风险优先级',
                        content: '## 风险优先级\n\n已确认。',
                        sectionAnchor: 'h2:风险优先级:1',
                        createdAt: 1710000000100,
                    },
                ],
                artifactAuditEvents: [
                    {
                        stageId: 'STRATEGY',
                        eventType: 'artifact_saved',
                        summary: '保存了 STRATEGY 阶段产出物 v2',
                        createdAt: 1710000000400,
                    },
                ],
            }),
            {
                status: 200,
                headers: { 'Content-Type': 'application/json' },
            },
        ));

        const snapshot = await fetchRunSnapshot('run-123');

        expect(fetch).toHaveBeenCalledWith('/new-agents/api/agent/runs/run-123');
        expect(snapshot.run.id).toBe('run-123');
        expect(snapshot.run.workflowId).toBe('TEST_DESIGN');
        expect(snapshot.messages[0].content).toBe('用户需求: 登录功能');
        expect(snapshot.artifacts[0].stageId).toBe('STRATEGY');
        expect(snapshot.contextSummaries[0].content).toBe('摘要');
        expect(snapshot).toMatchObject({
            artifactComments: [
                {
                    id: 'comment-1',
                    stageId: 'STRATEGY',
                    content: '这里需要业务确认。',
                    artifactExcerpt: '风险优先级',
                    anchorText: '风险优先级',
                    createdAt: 1710000000000,
                    status: 'resolved',
                    resolvedAt: 1710000000300,
                    replies: [
                        {
                            id: 'reply-1',
                            content: '已补充登录异常边界。',
                            createdAt: 1710000000200,
                        },
                    ],
                },
            ],
            artifactSectionLocks: [
                {
                    id: 'lock-1',
                    stageId: 'STRATEGY',
                    heading: '## 风险优先级',
                    content: '## 风险优先级\n\n已确认。',
                    sectionAnchor: 'h2:风险优先级:1',
                    createdAt: 1710000000100,
                },
            ],
            artifactAuditEvents: [
                {
                    stageId: 'STRATEGY',
                    eventType: 'artifact_saved',
                    summary: '保存了 STRATEGY 阶段产出物 v2',
                    createdAt: 1710000000400,
                },
            ],
        });
    });

    it('should fail explicitly when the snapshot payload is malformed', async () => {
        vi.mocked(fetch).mockResolvedValue(new Response(
            JSON.stringify({
                run: {
                    id: 'run-123',
                    workflowId: 'TEST_DESIGN',
                    agentId: 'lisa',
                },
                messages: 'broken',
                artifacts: [],
                contextSummaries: [],
            }),
            {
                status: 200,
                headers: { 'Content-Type': 'application/json' },
            },
        ));

        await expect(fetchRunSnapshot('run-123')).rejects.toThrow(
            'Invalid run snapshot response'
        );
    });

    it('should update a persisted run context summary', async () => {
        vi.mocked(fetch).mockResolvedValue(new Response(
            JSON.stringify({
                sourceType: 'artifact',
                sourceStageId: 'STRATEGY',
                summaryType: 'stage_conclusion',
                content: '服务端保存后的阶段结论',
            }),
            {
                status: 200,
                headers: { 'Content-Type': 'application/json' },
            },
        ));

        const updated = await updateRunContextSummary(
            'run-123',
            {
                sourceType: 'artifact',
                sourceStageId: 'STRATEGY',
                summaryType: 'stage_conclusion',
            },
            '人工校准后的阶段结论',
        );

        expect(fetch).toHaveBeenCalledWith(
            '/new-agents/api/agent/runs/run-123/context-summaries',
            {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    sourceType: 'artifact',
                    sourceStageId: 'STRATEGY',
                    summaryType: 'stage_conclusion',
                    content: '人工校准后的阶段结论',
                }),
            },
        );
        expect(updated.content).toBe('服务端保存后的阶段结论');
    });

    it('should create a persisted run decision summary', async () => {
        vi.mocked(fetch).mockResolvedValue(new Response(
            JSON.stringify({
                sourceType: 'artifact',
                sourceStageId: 'STRATEGY',
                summaryType: 'decision',
                content: '决定优先覆盖第三方登录回调失败',
            }),
            {
                status: 200,
                headers: { 'Content-Type': 'application/json' },
            },
        ));

        const created = await createRunDecisionSummary(
            'run-123',
            'STRATEGY',
            '决定优先覆盖第三方登录回调失败',
        );

        expect(fetch).toHaveBeenCalledWith(
            '/new-agents/api/agent/runs/run-123/context-summaries/decisions',
            {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    stageId: 'STRATEGY',
                    content: '决定优先覆盖第三方登录回调失败',
                }),
            },
        );
        expect(created.summaryType).toBe('decision');
        expect(created.content).toBe('决定优先覆盖第三方登录回调失败');
    });

    it('should create a persisted artifact version for manual calibration', async () => {
        vi.mocked(fetch).mockResolvedValue(new Response(
            JSON.stringify({
                stageId: 'STRATEGY',
                content: '# 测试策略蓝图\n\n人工校准后的风险优先级',
                versionNumber: 2,
            }),
            {
                status: 200,
                headers: { 'Content-Type': 'application/json' },
            },
        ));

        const updated = await updateRunArtifact(
            'run-123',
            'STRATEGY',
            '# 测试策略蓝图\n\n人工校准后的风险优先级',
            { expectedVersionNumber: 1 },
        );

        expect(fetch).toHaveBeenCalledWith(
            '/new-agents/api/agent/runs/run-123/artifacts',
            {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    stageId: 'STRATEGY',
                    content: '# 测试策略蓝图\n\n人工校准后的风险优先级',
                    expectedVersionNumber: 1,
                }),
            },
        );
        expect(updated.stageId).toBe('STRATEGY');
        expect(updated.versionNumber).toBe(2);
    });

    it('should fail explicitly when an updated artifact payload is malformed', async () => {
        vi.mocked(fetch).mockResolvedValue(new Response(
            JSON.stringify({
                stageId: 'STRATEGY',
                content: '# 测试策略蓝图',
                versionNumber: '2',
            }),
            {
                status: 200,
                headers: { 'Content-Type': 'application/json' },
            },
        ));

        await expect(updateRunArtifact(
            'run-123',
            'STRATEGY',
            '# 测试策略蓝图',
        )).rejects.toThrow('Invalid run snapshot response');
    });

    it('should raise a typed conflict error when artifact save is stale', async () => {
        vi.mocked(fetch).mockResolvedValue(new Response(
            JSON.stringify({
                error: '产出物已被更新，请刷新后再保存',
                currentArtifact: {
                    stageId: 'STRATEGY',
                    content: '# 测试策略蓝图\n\n服务端较新版本',
                    versionNumber: 3,
                },
            }),
            {
                status: 409,
                headers: { 'Content-Type': 'application/json' },
            },
        ));

        let capturedError: unknown;
        try {
            await updateRunArtifact(
                'run-123',
                'STRATEGY',
                '# 测试策略蓝图\n\n旧版本修改',
                { expectedVersionNumber: 2 },
            );
        } catch (error) {
            capturedError = error;
        }

        expect(capturedError).toBeInstanceOf(ArtifactConflictError);
        expect((capturedError as ArtifactConflictError).currentArtifact).toEqual({
            stageId: 'STRATEGY',
            content: '# 测试策略蓝图\n\n服务端较新版本',
            versionNumber: 3,
        });
    });

    it('should replace persisted artifact collaboration state', async () => {
        vi.mocked(fetch).mockResolvedValue(new Response(
            JSON.stringify({
                artifactComments: [
                    {
                        id: 'comment-1',
                        stageId: 'CLARIFY',
                        content: '这里需要业务确认。',
                        artifactExcerpt: '登录边界',
                        anchorText: '登录边界',
                        createdAt: 1710000000000,
                        status: 'resolved',
                        resolvedAt: 1710000000300,
                        replies: [
                            {
                                id: 'reply-1',
                                content: '已补充登录异常边界。',
                                createdAt: 1710000000200,
                            },
                        ],
                    },
                ],
                artifactSectionLocks: [
                    {
                        id: 'lock-1',
                        stageId: 'CLARIFY',
                        heading: '## 业务规则',
                        content: '## 业务规则\n\n已确认。',
                        createdAt: 1710000000100,
                    },
                ],
            }),
            {
                status: 200,
                headers: { 'Content-Type': 'application/json' },
            },
        ));

        const updated = await updateRunArtifactCollaboration(
            'run-123',
            [
                {
                    id: 'comment-1',
                    stageId: 'CLARIFY',
                    content: '这里需要业务确认。',
                    artifactExcerpt: '登录边界',
                    anchorText: '登录边界',
                    createdAt: 1710000000000,
                    status: 'resolved',
                    resolvedAt: 1710000000300,
                    replies: [
                        {
                            id: 'reply-1',
                            content: '已补充登录异常边界。',
                            createdAt: 1710000000200,
                        },
                    ],
                },
            ],
            [
                {
                    id: 'lock-1',
                    stageId: 'CLARIFY',
                    heading: '## 业务规则',
                    sectionAnchor: 'h2:业务规则:1',
                    content: '## 业务规则\n\n已确认。',
                    createdAt: 1710000000100,
                },
            ],
        );

        expect(fetch).toHaveBeenCalledWith(
            '/new-agents/api/agent/runs/run-123/artifact-collaboration',
            {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    comments: [
                        {
                            id: 'comment-1',
                            stageId: 'CLARIFY',
                            content: '这里需要业务确认。',
                            artifactExcerpt: '登录边界',
                            anchorText: '登录边界',
                            createdAt: 1710000000000,
                            status: 'resolved',
                            resolvedAt: 1710000000300,
                            replies: [
                                {
                                    id: 'reply-1',
                                    content: '已补充登录异常边界。',
                                    createdAt: 1710000000200,
                                },
                            ],
                        },
                    ],
                    sectionLocks: [
                        {
                            id: 'lock-1',
                            stageId: 'CLARIFY',
                            heading: '## 业务规则',
                            sectionAnchor: 'h2:业务规则:1',
                            content: '## 业务规则\n\n已确认。',
                            createdAt: 1710000000100,
                        },
                    ],
                }),
            },
        );
        expect(updated.artifactComments).toHaveLength(1);
        expect(updated.artifactSectionLocks).toHaveLength(1);
    });

    it('should fetch recent run list summaries', async () => {
        vi.mocked(fetch).mockResolvedValue(new Response(
            JSON.stringify({
                limit: 20,
                offset: 0,
                total: 1,
                hasMore: false,
                nextOffset: null,
                query: null,
                qualityStatus: null,
                runs: [
                    {
                        id: 'run-123',
                        workflowId: 'TEST_DESIGN',
                        agentId: 'lisa',
                        currentStageId: 'STRATEGY',
                        status: 'active',
                        model: 'test-model',
                        createdAt: '2026-06-19T09:00:00',
                        updatedAt: '2026-06-19T09:05:00',
                        lastMessage: {
                            role: 'assistant',
                            content: '已更新测试策略。',
                            sequenceIndex: 2,
                        },
                        currentArtifact: {
                            stageId: 'STRATEGY',
                            versionNumber: 1,
                            summary: '# 测试策略蓝图\n\n关键风险: 登录绕过',
                            preview: '# 测试策略蓝图\n\n关键风险: 登录绕过\n\n## 风险优先级',
                        },
                        qualityStatus: 'ready',
                    },
                ],
            }),
            {
                status: 200,
                headers: { 'Content-Type': 'application/json' },
            },
        ));

        const result = await fetchRunList({ workflowId: 'TEST_DESIGN', limit: 10 });

        expect(fetch).toHaveBeenCalledWith('/new-agents/api/agent/runs?workflowId=TEST_DESIGN&limit=10');
        expect(result.limit).toBe(20);
        expect(result.offset).toBe(0);
        expect(result.total).toBe(1);
        expect(result.hasMore).toBe(false);
        expect(result.nextOffset).toBeNull();
        expect(result.query).toBeNull();
        expect(result.qualityStatus).toBeNull();
        expect(result.runs[0].id).toBe('run-123');
        expect(result.runs[0].qualityStatus).toBe('ready');
        expect(result.runs[0].lastMessage?.content).toBe('已更新测试策略。');
        expect(result.runs[0].currentArtifact?.summary).toContain('登录绕过');
        expect(result.runs[0].currentArtifact?.preview).toContain('风险优先级');
    });

    it('should pass pagination and search options to the run list endpoint', async () => {
        vi.mocked(fetch).mockResolvedValue(new Response(
            JSON.stringify({
                limit: 5,
                offset: 10,
                total: 12,
                hasMore: false,
                nextOffset: null,
                query: '登录 链路',
                qualityStatus: 'needs_action',
                runs: [],
            }),
            {
                status: 200,
                headers: { 'Content-Type': 'application/json' },
            },
        ));

        const result = await fetchRunList({
            workflowId: 'TEST_DESIGN',
            limit: 5,
            offset: 10,
            query: '登录 链路',
            qualityStatus: 'needs_action',
        });

        expect(fetch).toHaveBeenCalledWith(
            '/new-agents/api/agent/runs?workflowId=TEST_DESIGN&qualityStatus=needs_action&limit=5&offset=10&query=%E7%99%BB%E5%BD%95+%E9%93%BE%E8%B7%AF'
        );
        expect(result.offset).toBe(10);
        expect(result.total).toBe(12);
        expect(result.query).toBe('登录 链路');
        expect(result.qualityStatus).toBe('needs_action');
    });

    it('should clone a persisted run snapshot', async () => {
        vi.mocked(fetch).mockResolvedValue(new Response(
            JSON.stringify({
                run: {
                    id: 'clone-run-456',
                    workflowId: 'VALUE_DISCOVERY',
                    agentId: 'alex',
                    currentStageId: 'BLUEPRINT',
                    status: 'active',
                    model: 'test-model',
                },
                messages: [
                    {
                        role: 'user',
                        content: '请分析测试资产平台',
                        sequenceIndex: 1,
                    },
                ],
                artifacts: [],
                contextSummaries: [],
                artifactComments: [],
                artifactSectionLocks: [],
                artifactAuditEvents: [],
            }),
            {
                status: 200,
                headers: { 'Content-Type': 'application/json' },
            },
        ));

        const snapshot = await cloneRun('source-run-123');

        expect(fetch).toHaveBeenCalledWith(
            '/new-agents/api/agent/runs/source-run-123/clone',
            { method: 'POST' }
        );
        expect(snapshot.run.id).toBe('clone-run-456');
        expect(snapshot.messages[0].content).toBe('请分析测试资产平台');
    });

    it('should fail explicitly when the run list payload is malformed', async () => {
        vi.mocked(fetch).mockResolvedValue(new Response(
            JSON.stringify({
                limit: 20,
                runs: [
                    {
                        id: 'run-123',
                        workflowId: 'TEST_DESIGN',
                        agentId: 'lisa',
                    },
                ],
            }),
            {
                status: 200,
                headers: { 'Content-Type': 'application/json' },
            },
        ));

        await expect(fetchRunList()).rejects.toThrow('Invalid run list response');
    });
});
