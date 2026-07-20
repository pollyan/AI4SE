import { beforeEach, describe, it, expect } from 'vitest';
import { getWelcomeMessage, useStore } from '../store';

describe('Zustand Store', () => {
    beforeEach(() => {
        localStorage.removeItem('agent-workspace-storage');
        useStore.getState().clearHistory();
    });

    it('should clear history to defaults', () => {
        const state = useStore.getState();
        state.addMessage({ id: '1', role: 'user', content: 'hello', timestamp: 123 });
        state.setStageIndex(2);
        state.setIsGenerating(true);
        state.setCurrentRunId('run-123');

        useStore.getState().clearHistory();
        const newState = useStore.getState();

        expect(newState.chatHistory).toHaveLength(0);
        expect(newState.stageIndex).toBe(0);
        expect(newState.isGenerating).toBe(false);
        expect(newState.currentRunId).toBeNull();
    });

    it('should focus existing artifact visual diagnostics with repeatable requests', () => {
        useStore.getState().setArtifactVisualDiagnostic({
            id: 'structured-visual:CLARIFY:0',
            stageId: 'CLARIFY',
            kind: 'structured-visual',
            title: '结构化可视化格式错误',
            message: '结构化可视化必须是合法 JSON。',
        });

        useStore.getState().focusArtifactVisualDiagnostic('structured-visual:CLARIFY:0');
        const firstRequest = useStore.getState().artifactVisualDiagnosticFocusRequest;
        useStore.getState().focusArtifactVisualDiagnostic('structured-visual:CLARIFY:0');
        const secondRequest = useStore.getState().artifactVisualDiagnosticFocusRequest;

        expect(firstRequest).toEqual({ id: 'structured-visual:CLARIFY:0', seq: expect.any(Number) });
        expect(secondRequest?.id).toBe('structured-visual:CLARIFY:0');
        expect(secondRequest?.seq).toBeGreaterThan(firstRequest?.seq ?? 0);
    });

    it('should ignore focus requests for missing artifact visual diagnostics', () => {
        useStore.getState().focusArtifactVisualDiagnostic('structured-visual:CLARIFY:404');

        expect(useStore.getState().artifactVisualDiagnosticFocusRequest).toBeNull();
    });

    it('should not notify subscribers when clearing a missing artifact visual diagnostic', () => {
        let notificationCount = 0;
        const unsubscribe = useStore.subscribe(() => {
            notificationCount += 1;
        });

        useStore.getState().clearArtifactVisualDiagnostic('mermaid:CLARIFY:404');
        unsubscribe();

        expect(notificationCount).toBe(0);
    });

    it('should store the current server run id', () => {
        useStore.getState().setCurrentRunId('run-123');

        expect(useStore.getState().currentRunId).toBe('run-123');
    });

    it('should keep chat history reference when updating the last message with identical content', () => {
        useStore.getState().addMessage({
            id: 'assistant-1',
            role: 'assistant',
            content: '我正在整理右侧产出物，请先关注当前确认点。',
            timestamp: 123,
        });
        const beforeHistory = useStore.getState().chatHistory;

        useStore.getState().updateLastMessage('我正在整理右侧产出物，请先关注当前确认点。');

        expect(useStore.getState().chatHistory).toBe(beforeHistory);
    });

    it('should transition to next stage and preserve artifacts', () => {
        useStore.getState().transitionToNextStage('CLARIFY', 'Stage 0 Data');
        const state = useStore.getState();

        expect(state.stageIndex).toBe(1);
        expect(state.stageArtifacts['CLARIFY']).toBe('Stage 0 Data');
    });

    it('should not reuse the source artifact as the next stage artifact during legacy transitions', () => {
        const clarifyArtifact = '# Clarify-only artifact\n\nThis content belongs to CLARIFY.';
        useStore.getState().setArtifactContent(clarifyArtifact);

        useStore.getState().transitionToNextStage('CLARIFY', clarifyArtifact);

        const state = useStore.getState();
        expect(state.stageIndex).toBe(1);
        expect(state.artifactContent).toBe('# 策略制定\n\n暂无产出物。');
        expect(state.artifactContent).not.toBe(clarifyArtifact);
        expect(state.stageArtifacts.STRATEGY).not.toBe(clarifyArtifact);
    });

    it('should clear derived workflow state when legacy next-stage transition advances', () => {
        useStore.getState().setPendingStageTransition({ fromStageIndex: 0, toStageIndex: 1 });
        useStore.getState().setArtifactTruncated(true);
        useStore.getState().setIsGenerating(true);

        useStore.getState().transitionToNextStage('CLARIFY', '# Clarify artifact');

        const state = useStore.getState();
        expect(state.stageIndex).toBe(1);
        expect(state.pendingStageTransition).toBeNull();
        expect(state.artifactTruncated).toBe(false);
        expect(state.isGenerating).toBe(false);
    });

    it('should ignore out-of-range manual stage switches', () => {
        useStore.getState().setStageIndex(1);
        useStore.getState().setArtifactContent('# Strategy artifact');
        const before = useStore.getState();

        expect(() => useStore.getState().setStageIndex(999)).not.toThrow();

        const after = useStore.getState();
        expect(after.stageIndex).toBe(before.stageIndex);
        expect(after.artifactContent).toBe(before.artifactContent);
        expect(after.stageArtifacts).toEqual(before.stageArtifacts);
    });

    it('should ignore next-stage transitions when already on the final stage', () => {
        const finalStageIndex = 3;
        useStore.getState().setStageIndex(finalStageIndex);
        useStore.getState().setArtifactContent('# Delivery artifact');
        const before = useStore.getState();

        expect(() => {
            useStore.getState().transitionToNextStage('DELIVERY', '# Delivery artifact');
        }).not.toThrow();

        const after = useStore.getState();
        expect(after.stageIndex).toBe(before.stageIndex);
        expect(after.artifactContent).toBe(before.artifactContent);
        expect(after.stageArtifacts).toEqual(before.stageArtifacts);
    });

    it('should ignore next-stage transitions with a source stage outside the active workflow', () => {
        useStore.getState().setArtifactContent('# Clarify artifact');
        const before = useStore.getState();

        useStore.getState().transitionToNextStage('REPORT', '# Cross-workflow source artifact');

        const after = useStore.getState();
        expect(after.stageIndex).toBe(before.stageIndex);
        expect(after.artifactContent).toBe(before.artifactContent);
        expect(after.stageArtifacts).toEqual(before.stageArtifacts);
    });

    it('should clear artifact truncation state when confirming a stage transition', () => {
        useStore.getState().setArtifactTruncated(true);
        useStore.getState().setPendingStageTransition({ fromStageIndex: 0, toStageIndex: 1 });

        useStore.getState().confirmStageTransition();

        const state = useStore.getState();
        expect(state.stageIndex).toBe(1);
        expect(state.pendingStageTransition).toBeNull();
        expect(state.artifactTruncated).toBe(false);
    });

    it('should clear artifact truncation state when manually switching stages', () => {
        useStore.getState().setArtifactTruncated(true);
        useStore.getState().setIsGenerating(true);
        useStore.getState().setStageIndex(1);

        const state = useStore.getState();
        expect(state.stageIndex).toBe(1);
        expect(state.artifactTruncated).toBe(false);
        expect(state.isGenerating).toBe(false);
    });

    it('should clear pending stage transition when manually switching stages', () => {
        useStore.getState().setPendingStageTransition({ fromStageIndex: 0, toStageIndex: 1 });
        useStore.getState().setStageIndex(2);

        const state = useStore.getState();
        expect(state.stageIndex).toBe(2);
        expect(state.pendingStageTransition).toBeNull();
    });

    it('should stamp artifact versions with the current stage id', () => {
        useStore.getState().setStageIndex(1);

        useStore.getState().addArtifactVersion({
            id: 'v1',
            timestamp: 123,
            content: '# Strategy artifact',
        });

        expect(useStore.getState().artifactHistory[0]).toEqual(
            expect.objectContaining({
                stageId: 'STRATEGY',
            })
        );
    });

    it('should keep artifact comments scoped to the current workflow stage and clear them with workspace resets', () => {
        useStore.getState().setArtifactContent('# Clarify artifact\n\n需要确认登录边界。');

        useStore.getState().addArtifactComment({
            content: '这里需要业务确认。',
            artifactExcerpt: '需要确认登录边界。',
            anchorText: '需要确认登录边界。',
        });

        expect(useStore.getState().getArtifactCommentsForStage('CLARIFY')).toEqual([
            expect.objectContaining({
                stageId: 'CLARIFY',
                content: '这里需要业务确认。',
                artifactExcerpt: '需要确认登录边界。',
                anchorText: '需要确认登录边界。',
                status: 'open',
                resolvedAt: null,
                replies: [],
            }),
        ]);

        useStore.getState().setStageIndex(1);
        expect(useStore.getState().getArtifactCommentsForStage('STRATEGY')).toEqual([]);

        useStore.getState().addArtifactComment({
            content: '策略阶段单独批注。',
            artifactExcerpt: '暂无产出物。',
        });
        const strategyComment = useStore.getState().getArtifactCommentsForStage('STRATEGY')[0];
        useStore.getState().removeArtifactComment(strategyComment.id);

        expect(useStore.getState().getArtifactCommentsForStage('STRATEGY')).toEqual([]);
        expect(useStore.getState().getArtifactCommentsForStage('CLARIFY')).toHaveLength(1);

        useStore.getState().clearHistory();

        expect(useStore.getState().artifactComments).toEqual([]);
    });

    it('should support replies and resolved state for artifact comments', () => {
        useStore.getState().addArtifactComment({
            content: '这里需要确认优先级。',
            artifactExcerpt: '优先级 P1',
            anchorText: '优先级 P1',
        });
        const comment = useStore.getState().getArtifactCommentsForStage('CLARIFY')[0];

        useStore.getState().addArtifactCommentReply(comment.id, '已确认按 P1 处理。');
        useStore.getState().setArtifactCommentStatus(comment.id, 'resolved');

        const resolvedComment = useStore.getState().getArtifactCommentsForStage('CLARIFY')[0];
        expect(resolvedComment.status).toBe('resolved');
        expect(resolvedComment.resolvedAt).toEqual(expect.any(Number));
        expect(resolvedComment.replies).toEqual([
            expect.objectContaining({
                content: '已确认按 P1 处理。',
                createdAt: expect.any(Number),
            }),
        ]);

        useStore.getState().setArtifactCommentStatus(comment.id, 'open');

        expect(useStore.getState().getArtifactCommentsForStage('CLARIFY')[0]).toEqual(
            expect.objectContaining({
                status: 'open',
                resolvedAt: null,
            })
        );
    });

    it('should update artifact comment anchor and excerpt', () => {
        useStore.setState({
            workflow: 'TEST_DESIGN',
            stageIndex: 0,
            artifactComments: [
                {
                    id: 'comment-1',
                    stageId: 'CLARIFY',
                    content: '确认登录边界。',
                    artifactExcerpt: '旧登录边界',
                    anchorText: '旧登录边界',
                    createdAt: 1710000000000,
                    status: 'open',
                    resolvedAt: null,
                    replies: [],
                },
            ],
        });

        useStore.getState().updateArtifactCommentAnchor('comment-1', '新的登录边界');

        expect(useStore.getState().artifactComments).toEqual([
            expect.objectContaining({
                id: 'comment-1',
                artifactExcerpt: '新的登录边界',
                anchorText: '新的登录边界',
            }),
        ]);
    });

    it('should keep artifact section locks scoped to the current workflow stage and clear them with workspace resets', () => {
        useStore.getState().addArtifactSectionLock({
            heading: '## 业务规则',
            content: '## 业务规则\n\n已确认的登录规则。',
        });

        expect(useStore.getState().getArtifactSectionLocksForStage('CLARIFY')).toEqual([
            expect.objectContaining({
                stageId: 'CLARIFY',
                heading: '## 业务规则',
                content: '## 业务规则\n\n已确认的登录规则。',
            }),
        ]);

        useStore.getState().setStageIndex(1);
        expect(useStore.getState().getArtifactSectionLocksForStage('STRATEGY')).toEqual([]);

        useStore.getState().addArtifactSectionLock({
            heading: '## 策略章节',
            content: '## 策略章节\n\n已确认的策略。',
        });
        const strategyLock = useStore.getState().getArtifactSectionLocksForStage('STRATEGY')[0];
        useStore.getState().removeArtifactSectionLock(strategyLock.id);

        expect(useStore.getState().getArtifactSectionLocksForStage('STRATEGY')).toEqual([]);
        expect(useStore.getState().getArtifactSectionLocksForStage('CLARIFY')).toHaveLength(1);

        useStore.getState().clearHistory();

        expect(useStore.getState().artifactSectionLocks).toEqual([]);
    });

    it('should preserve section anchors and keep duplicate heading locks distinct', () => {
        useStore.getState().addArtifactSectionLock({
            heading: '## 验收口径',
            content: '## 验收口径\n\n第一个验收口径。',
            sectionAnchor: 'h2:验收口径:1',
        });
        useStore.getState().addArtifactSectionLock({
            heading: '## 验收口径',
            content: '## 验收口径\n\n第二个验收口径。',
            sectionAnchor: 'h2:验收口径:2',
        });

        expect(useStore.getState().getArtifactSectionLocksForStage('CLARIFY')).toEqual([
            expect.objectContaining({
                heading: '## 验收口径',
                content: '## 验收口径\n\n第一个验收口径。',
                sectionAnchor: 'h2:验收口径:1',
            }),
            expect.objectContaining({
                heading: '## 验收口径',
                content: '## 验收口径\n\n第二个验收口径。',
                sectionAnchor: 'h2:验收口径:2',
            }),
        ]);
    });

    it('should restore artifact comments and section locks from a run snapshot', () => {
        useStore.getState().restoreRunSnapshot({
            run: {
                id: 'run-123',
                workflowId: 'TEST_DESIGN',
                agentId: 'lisa',
                currentStageId: 'CLARIFY',
                status: 'active',
                model: 'test-model',
            },
            messages: [],
            artifacts: [
                {
                    stageId: 'CLARIFY',
                    content: '# 需求分析文档\n\n## 业务规则\n\n已确认的登录规则。',
                    versionNumber: 1,
                },
            ],
            contextSummaries: [],
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
                {
                    id: 'comment-outside-workflow',
                    stageId: 'REPORT',
                    content: '跨工作流批注应被过滤。',
                    artifactExcerpt: '报告',
                    createdAt: 1710000000001,
                },
            ],
            artifactSectionLocks: [
                {
                    id: 'lock-1',
                    stageId: 'CLARIFY',
                    heading: '## 业务规则',
                    content: '## 业务规则\n\n已确认的登录规则。',
                    sectionAnchor: 'h2:业务规则:1',
                    createdAt: 1710000000100,
                },
                {
                    id: 'lock-outside-workflow',
                    stageId: 'REPORT',
                    heading: '## 报告章节',
                    content: '## 报告章节\n\n跨工作流锁应被过滤。',
                    createdAt: 1710000000101,
                },
            ],
            artifactAuditEvents: [
                {
                    stageId: 'CLARIFY',
                    eventType: 'artifact_saved',
                    summary: '保存了 CLARIFY 阶段产出物 v1',
                    createdAt: 1710000000200,
                },
                {
                    stageId: 'REPORT',
                    eventType: 'artifact_saved',
                    summary: '跨工作流活动应被过滤。',
                    createdAt: 1710000000201,
                },
            ],
        });

        expect(useStore.getState().getArtifactCommentsForStage('CLARIFY')).toEqual([
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
        ]);
        expect(useStore.getState().getArtifactSectionLocksForStage('CLARIFY')).toEqual([
            {
                id: 'lock-1',
                stageId: 'CLARIFY',
                heading: '## 业务规则',
                content: '## 业务规则\n\n已确认的登录规则。',
                sectionAnchor: 'h2:业务规则:1',
                createdAt: 1710000000100,
            },
        ]);
        expect(useStore.getState().getArtifactAuditEventsForStage('CLARIFY')).toEqual([
            {
                stageId: 'CLARIFY',
                eventType: 'artifact_saved',
                summary: '保存了 CLARIFY 阶段产出物 v1',
                createdAt: 1710000000200,
            },
        ]);
    });

    it('should add local artifact audit events for the current workflow stage', () => {
        useStore.getState().setWorkflow('TEST_DESIGN');
        useStore.getState().setStageIndex(1);

        useStore.getState().addArtifactAuditEvent({
            eventType: ' artifact_merge_line_accepted ',
            summary: ' 合并轨迹：采纳草稿行「用户补充风险」 ',
            createdAt: 1710000000300,
        });
        useStore.getState().addArtifactAuditEvent({
            stageId: 'UNKNOWN_STAGE',
            eventType: 'artifact_merge_line_discarded',
            summary: '不应写入',
            createdAt: 1710000000400,
        });

        expect(useStore.getState().getArtifactAuditEventsForStage('STRATEGY')).toEqual([
            {
                stageId: 'STRATEGY',
                eventType: 'artifact_merge_line_accepted',
                summary: '合并轨迹：采纳草稿行「用户补充风险」',
                createdAt: 1710000000300,
            },
        ]);
        expect(useStore.getState().artifactAuditEvents).toHaveLength(1);
    });

    it('should switch workflows and clear state', () => {
        useStore.getState().setStageIndex(2);
        useStore.getState().setArtifactTruncated(true);
        useStore.getState().setIsGenerating(true);
        useStore.getState().setCurrentRunId('run-123');
        useStore.getState().setWorkflow('REQ_REVIEW');
        const state = useStore.getState();

        expect(state.workflow).toBe('REQ_REVIEW');
        expect(state.stageIndex).toBe(0);
        expect(state.artifactTruncated).toBe(false);
        expect(state.isGenerating).toBe(false);
        expect(state.currentRunId).toBeNull();
    });

    it('should apply a workflow handoff as a fresh target workflow context', () => {
        useStore.getState().setWorkflow('VALUE_DISCOVERY');
        useStore.getState().setStageIndex(3);
        useStore.getState().addMessage({
            id: 'source-user-message',
            role: 'user',
            content: '这是 Alex 的旧对话',
            timestamp: 123,
        });
        useStore.getState().setArtifactTruncated(true);
        useStore.getState().setIsGenerating(true);
        useStore.getState().setCurrentRunId('alex-run-123');

        useStore.getState().applyWorkflowHandoff({
            id: 'handoff-1',
            label: '交给 Lisa 做测试设计',
            sourceWorkflowId: 'VALUE_DISCOVERY',
            sourceStageId: 'BLUEPRINT',
            sourceArtifactVersion: 2,
            sourceSummary: 'AI 测试资产管理平台需求蓝图: AI 测试资产管理平台。',
            unconfirmedItems: ['需求 F-001: 自动生成测试策略和用例'],
            targetInputChecklist: ['复核来源版本 VALUE_DISCOVERY/BLUEPRINT v2'],
            targetWorkflowId: 'TEST_DESIGN',
            targetStageId: 'CLARIFY',
            targetAgentId: 'lisa',
            prompt: '来源版本: VALUE_DISCOVERY/BLUEPRINT v2\n\n关键摘要:\n- AI 测试资产管理平台需求蓝图',
        });

        const state = useStore.getState();
        expect(state.workflow).toBe('TEST_DESIGN');
        expect(state.stageIndex).toBe(0);
        expect(state.currentRunId).toBeNull();
        expect(state.isGenerating).toBe(false);
        expect(state.artifactTruncated).toBe(false);
        expect(state.pendingStageTransition).toBeNull();
        expect(state.artifactContent).toBe(getWelcomeMessage('TEST_DESIGN'));
        expect(state.stageArtifacts).toEqual({
            CLARIFY: getWelcomeMessage('TEST_DESIGN'),
        });
        expect(state.artifactHistory).toEqual([]);
        expect(state.chatHistory).toEqual([
            expect.objectContaining({
                id: 'handoff-handoff-1-v2',
                role: 'user',
                content: '来源版本: VALUE_DISCOVERY/BLUEPRINT v2\n\n关键摘要:\n- AI 测试资产管理平台需求蓝图',
            }),
        ]);
    });

    it('should ignore workflow handoffs that do not match the configured target agent or stage', () => {
        useStore.getState().setWorkflow('TEST_DESIGN');
        useStore.getState().setArtifactContent('# Stable artifact');
        const before = useStore.getState();

        useStore.getState().applyWorkflowHandoff({
            id: 'handoff-bad-agent',
            label: '错误接力',
            sourceWorkflowId: 'VALUE_DISCOVERY',
            sourceStageId: 'BLUEPRINT',
            sourceArtifactVersion: 1,
            sourceSummary: 'AI 测试资产管理平台需求蓝图',
            unconfirmedItems: [],
            targetInputChecklist: ['复核来源版本 VALUE_DISCOVERY/BLUEPRINT v1'],
            targetWorkflowId: 'TEST_DESIGN',
            targetStageId: 'CLARIFY',
            targetAgentId: 'alex',
            prompt: '不应应用',
        });

        useStore.getState().applyWorkflowHandoff({
            id: 'handoff-bad-stage',
            label: '错误阶段',
            sourceWorkflowId: 'VALUE_DISCOVERY',
            sourceStageId: 'BLUEPRINT',
            sourceArtifactVersion: 1,
            sourceSummary: 'AI 测试资产管理平台需求蓝图',
            unconfirmedItems: [],
            targetInputChecklist: ['复核来源版本 VALUE_DISCOVERY/BLUEPRINT v1'],
            targetWorkflowId: 'TEST_DESIGN',
            targetStageId: 'UNKNOWN_STAGE',
            targetAgentId: 'lisa',
            prompt: '不应应用',
        });

        const after = useStore.getState();
        expect(after.workflow).toBe(before.workflow);
        expect(after.stageIndex).toBe(before.stageIndex);
        expect(after.artifactContent).toBe(before.artifactContent);
        expect(after.chatHistory).toEqual(before.chatHistory);
        expect(after.currentRunId).toBe(before.currentRunId);
    });

    it('should restore workspace state from a server run snapshot', () => {
        useStore.getState().setWorkflow('REQ_REVIEW');
        useStore.getState().setCurrentRunId('old-run');
        useStore.getState().addMessage({
            id: 'old-message',
            role: 'user',
            content: '旧对话',
            timestamp: 1,
        });

        useStore.getState().restoreRunSnapshot({
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
                {
                    role: 'assistant',
                    content: '⚠️ **模型调用未完成**\n\n模型供应商返回错误。',
                    sequenceIndex: 2,
                    errorDiagnostic: {
                        kind: 'provider',
                        summary: '模型调用未完成',
                        rawMessage: '模型供应商返回错误。',
                        code: 'LLM_ERROR',
                        phase: 'provider',
                        workflowId: 'TEST_DESIGN',
                        stageId: 'CLARIFY',
                        fieldPath: 'provider',
                        validator: 'provider_error',
                        retryable: true,
                    },
                },
            ],
            artifacts: [
                {
                    stageId: 'CLARIFY',
                    content: '# 需求分析文档',
                    versionNumber: 1,
                },
                {
                    stageId: 'STRATEGY',
                    content: '# 测试策略蓝图',
                    versionNumber: 3,
                },
            ],
            contextSummaries: [],
        });

        const state = useStore.getState();
        expect(state.workflow).toBe('TEST_DESIGN');
        expect(state.stageIndex).toBe(1);
        expect(state.currentRunId).toBe('run-123');
        expect(state.artifactContent).toBe('# 测试策略蓝图');
        expect(state.stageArtifacts).toEqual({
            CLARIFY: '# 需求分析文档',
            STRATEGY: '# 测试策略蓝图',
        });
        expect(state.artifactHistory).toEqual([
            expect.objectContaining({
                id: 'run-123-CLARIFY-v1',
                stageId: 'CLARIFY',
                content: '# 需求分析文档',
            }),
            expect.objectContaining({
                id: 'run-123-STRATEGY-v3',
                stageId: 'STRATEGY',
                content: '# 测试策略蓝图',
            }),
        ]);
        expect(state.chatHistory).toEqual([
            expect.objectContaining({
                id: 'run-123-message-1',
                role: 'user',
                content: '用户需求: 登录功能',
            }),
            expect.objectContaining({
                id: 'run-123-message-2',
                role: 'assistant',
                content: '⚠️ **模型调用未完成**\n\n模型供应商返回错误。',
                errorDiagnostic: {
                    kind: 'provider',
                    summary: '模型调用未完成',
                    rawMessage: '模型供应商返回错误。',
                    code: 'LLM_ERROR',
                    phase: 'provider',
                    workflowId: 'TEST_DESIGN',
                    stageId: 'CLARIFY',
                    fieldPath: 'provider',
                    validator: 'provider_error',
                    retryable: true,
                },
            }),
        ]);
        expect(state.pendingStageTransition).toBeNull();
        expect(state.artifactTruncated).toBe(false);
        expect(state.isGenerating).toBe(false);
    });

    it('should restore and locally calibrate context summaries from a server run snapshot', () => {
        useStore.getState().restoreRunSnapshot({
            run: {
                id: 'run-123',
                workflowId: 'TEST_DESIGN',
                agentId: 'lisa',
                currentStageId: 'STRATEGY',
                status: 'active',
                model: null,
            },
            messages: [],
            artifacts: [],
            contextSummaries: [
                {
                    sourceType: 'stage',
                    sourceStageId: 'CLARIFY',
                    summaryType: 'user_supplement',
                    content: '用户补充了登录异常场景。',
                },
            ],
        });

        expect(useStore.getState().contextSummaries).toEqual([
            {
                sourceType: 'stage',
                sourceStageId: 'CLARIFY',
                summaryType: 'user_supplement',
                content: '用户补充了登录异常场景。',
            },
        ]);

        useStore.getState().updateContextSummaryContent(
            {
                sourceType: 'stage',
                sourceStageId: 'CLARIFY',
                summaryType: 'user_supplement',
            },
            '用户补充了登录异常和锁定场景。'
        );

        expect(useStore.getState().contextSummaries[0].content).toBe(
            '用户补充了登录异常和锁定场景。'
        );
    });

    it('should upsert context summaries by source and summary identity', () => {
        useStore.getState().upsertContextSummary({
            sourceType: 'artifact',
            sourceStageId: 'STRATEGY',
            summaryType: 'decision',
            content: '旧决策',
        });
        useStore.getState().upsertContextSummary({
            sourceType: 'artifact',
            sourceStageId: 'STRATEGY',
            summaryType: 'decision',
            content: '新决策',
        });

        expect(useStore.getState().contextSummaries).toEqual([
            {
                sourceType: 'artifact',
                sourceStageId: 'STRATEGY',
                summaryType: 'decision',
                content: '新决策',
            },
        ]);
    });

    it('should clear context summaries when leaving the current workspace boundary', () => {
        useStore.getState().restoreRunSnapshot({
            run: {
                id: 'run-123',
                workflowId: 'TEST_DESIGN',
                agentId: 'lisa',
                currentStageId: 'CLARIFY',
                status: 'active',
                model: null,
            },
            messages: [],
            artifacts: [],
            contextSummaries: [
                {
                    sourceType: 'stage',
                    sourceStageId: 'CLARIFY',
                    summaryType: 'decision',
                    content: '优先覆盖 P0 登录主链路。',
                },
            ],
        });

        expect(useStore.getState().contextSummaries).toHaveLength(1);

        useStore.getState().clearHistory();
        expect(useStore.getState().contextSummaries).toEqual([]);

        useStore.getState().restoreRunSnapshot({
            run: {
                id: 'run-456',
                workflowId: 'TEST_DESIGN',
                agentId: 'lisa',
                currentStageId: 'CLARIFY',
                status: 'active',
                model: null,
            },
            messages: [],
            artifacts: [],
            contextSummaries: [
                {
                    sourceType: 'stage',
                    sourceStageId: 'CLARIFY',
                    summaryType: 'decision',
                    content: '第二个 run 的决策摘要。',
                },
            ],
        });

        useStore.getState().setWorkflow('VALUE_DISCOVERY');

        expect(useStore.getState().contextSummaries).toEqual([]);
    });

    it('should ignore server run snapshots with mismatched target agent or stage', () => {
        useStore.getState().setWorkflow('TEST_DESIGN');
        useStore.getState().setArtifactContent('# Stable artifact');
        const before = useStore.getState();

        useStore.getState().restoreRunSnapshot({
            run: {
                id: 'run-bad-agent',
                workflowId: 'TEST_DESIGN',
                agentId: 'alex',
                currentStageId: 'CLARIFY',
                status: 'active',
                model: null,
            },
            messages: [],
            artifacts: [],
            contextSummaries: [],
        });

        useStore.getState().restoreRunSnapshot({
            run: {
                id: 'run-bad-stage',
                workflowId: 'TEST_DESIGN',
                agentId: 'lisa',
                currentStageId: 'REPORT',
                status: 'active',
                model: null,
            },
            messages: [],
            artifacts: [],
            contextSummaries: [],
        });

        const after = useStore.getState();
        expect(after.workflow).toBe(before.workflow);
        expect(after.stageIndex).toBe(before.stageIndex);
        expect(after.artifactContent).toBe(before.artifactContent);
        expect(after.chatHistory).toEqual(before.chatHistory);
        expect(after.currentRunId).toBe(before.currentRunId);
    });

    it('should ignore stage artifact updates for stages outside the active workflow', () => {
        useStore.getState().setWorkflow('TEST_DESIGN');
        useStore.getState().setStageArtifact('REPORT', '# Cross-workflow artifact');
        useStore.getState().setStageArtifact('UNKNOWN_STAGE', '# Unknown artifact');

        const state = useStore.getState();
        expect(state.workflow).toBe('TEST_DESIGN');
        expect(state.stageArtifacts.REPORT).toBeUndefined();
        expect(state.stageArtifacts.UNKNOWN_STAGE).toBeUndefined();
        expect(Object.keys(state.stageArtifacts)).toEqual(['CLARIFY']);
    });

    it('should drop non-array attachments when hydrating persisted chat history', async () => {
        localStorage.setItem(
            'agent-workspace-storage',
            JSON.stringify({
                state: {
                    workflow: 'TEST_DESIGN',
                    stageIndex: 0,
                    chatHistory: [
                        {
                            id: '1',
                            role: 'user',
                            content: '历史消息',
                            timestamp: 123,
                            attachments: { length: 1 },
                        },
                    ],
                    artifactContent: '# Persisted',
                    artifactHistory: [],
                    stageArtifacts: {
                        CLARIFY: '# Persisted',
                    },
                },
                version: 0,
            })
        );

        await useStore.persist.rehydrate();

        const [message] = useStore.getState().chatHistory;
        expect(message.content).toBe('历史消息');
        expect(message.attachments).toBeUndefined();
    });

    it('should discard service-backed conversation data during local storage hydration', async () => {
        localStorage.setItem(
            'agent-workspace-storage',
            JSON.stringify({
                state: {
                    workflow: 'TEST_DESIGN',
                    stageIndex: 1,
                    chatHistory: [{
                        id: 'persisted-user',
                        role: 'user',
                        content: '陈旧的本地会话',
                        timestamp: 123,
                    }],
                    artifactContent: '# 陈旧产物',
                    artifactHistory: [{
                        id: 'persisted-v1',
                        timestamp: 123,
                        content: '# 陈旧产物',
                        stageId: 'STRATEGY',
                    }],
                    stageArtifacts: {
                        STRATEGY: '# 陈旧产物',
                    },
                    currentRunId: 'run-123',
                },
                version: 0,
            })
        );

        await useStore.persist.rehydrate();

        const state = useStore.getState();
        expect(state.currentRunId).toBeNull();
        expect(state.chatHistory).toEqual([]);
        expect(state.artifactHistory).toEqual([]);
        expect(state.stageIndex).toBe(0);
        expect(state.artifactContent).toBe(getWelcomeMessage('TEST_DESIGN'));
    });

    it('should drop a blank persisted current run id', async () => {
        localStorage.setItem(
            'agent-workspace-storage',
            JSON.stringify({
                state: {
                    workflow: 'TEST_DESIGN',
                    stageIndex: 0,
                    chatHistory: [],
                    artifactContent: '# Persisted',
                    artifactHistory: [],
                    stageArtifacts: {
                        CLARIFY: '# Persisted',
                    },
                    currentRunId: '   ',
                },
                version: 0,
            })
        );

        await useStore.persist.rehydrate();

        expect(useStore.getState().currentRunId).toBeNull();
    });

    it('should drop malformed attachment entries when hydrating persisted chat history', async () => {
        localStorage.setItem(
            'agent-workspace-storage',
            JSON.stringify({
                state: {
                    workflow: 'TEST_DESIGN',
                    stageIndex: 0,
                    chatHistory: [
                        {
                            id: '1',
                            role: 'user',
                            content: '历史消息',
                            timestamp: 123,
                            attachments: [
                                null,
                                {
                                    name: 'valid.md',
                                    data: 'IyB2YWxpZA==',
                                    mimeType: 'text/markdown',
                                },
                                {
                                    name: 'missing-data.md',
                                    mimeType: 'text/markdown',
                                },
                                {
                                    name: 123,
                                    data: 'abc',
                                    mimeType: 'text/plain',
                                },
                            ],
                        },
                    ],
                    artifactContent: '# Persisted',
                    artifactHistory: [],
                    stageArtifacts: {
                        CLARIFY: '# Persisted',
                    },
                },
                version: 0,
            })
        );

        await useStore.persist.rehydrate();

        const [message] = useStore.getState().chatHistory;
        expect(message.attachments).toEqual([
            {
                name: 'valid.md',
                data: 'IyB2YWxpZA==',
                mimeType: 'text/markdown',
            },
        ]);
    });

    it('should preserve non-retryable assistant metadata when hydrating persisted chat history', async () => {
        localStorage.setItem(
            'agent-workspace-storage',
            JSON.stringify({
                state: {
                    workflow: 'TEST_DESIGN',
                    stageIndex: 1,
                    chatHistory: [
                        {
                            id: '1',
                            role: 'assistant',
                            content: '内部续写生成的新阶段内容',
                            timestamp: 123,
                            retryable: false,
                        },
                    ],
                    artifactContent: '# Persisted',
                    artifactHistory: [],
                    stageArtifacts: {
                        CLARIFY: '# Clarify',
                        STRATEGY: '# Persisted',
                    },
                },
                version: 0,
            })
        );

        await useStore.persist.rehydrate();

        const [message] = useStore.getState().chatHistory;
        expect(message.retryable).toBe(false);
    });

    it('should preserve valid assistant error diagnostics when hydrating persisted chat history', async () => {
        localStorage.setItem(
            'agent-workspace-storage',
            JSON.stringify({
                state: {
                    workflow: 'TEST_DESIGN',
                    stageIndex: 1,
                    chatHistory: [
                        {
                            id: '1',
                            role: 'assistant',
                            content: '⚠️ 本轮生成失败：请查看错误详情后重试。',
                            timestamp: 123,
                            errorDiagnostic: {
                                kind: 'generic',
                                summary: '本轮生成失败：请查看错误详情后重试。',
                                rawMessage: 'LLM_ERROR: raw detail',
                            },
                        },
                    ],
                    artifactContent: '# Persisted',
                    artifactHistory: [],
                    stageArtifacts: {
                        CLARIFY: '# Clarify',
                        STRATEGY: '# Persisted',
                    },
                },
                version: 0,
            })
        );

        await useStore.persist.rehydrate();

        const [message] = useStore.getState().chatHistory;
        expect(message).toMatchObject({
            errorDiagnostic: {
                kind: 'generic',
                summary: '本轮生成失败：请查看错误详情后重试。',
                rawMessage: 'LLM_ERROR: raw detail',
            },
        });
    });

    it('should fall back to default workflow when hydrating an unknown workflow', async () => {
        localStorage.setItem(
            'agent-workspace-storage',
            JSON.stringify({
                state: {
                    workflow: 'UNKNOWN_WORKFLOW',
                    stageIndex: 999,
                    chatHistory: [],
                    artifactContent: '# Broken',
                    artifactHistory: [],
                    stageArtifacts: 'broken',
                },
                version: 0,
            })
        );

        await useStore.persist.rehydrate();

        const state = useStore.getState();
        expect(state.workflow).toBe('TEST_DESIGN');
        expect(state.stageIndex).toBe(0);
        expect(state.artifactContent).toContain('欢迎使用');
        expect(state.stageArtifacts.CLARIFY).toBe(state.artifactContent);
    });

    it('should clamp an out-of-range persisted stage index for a valid workflow', async () => {
        localStorage.setItem(
            'agent-workspace-storage',
            JSON.stringify({
                state: {
                    workflow: 'REQ_REVIEW',
                    stageIndex: 999,
                    chatHistory: [],
                    artifactContent: '# Broken',
                    artifactHistory: [],
                    stageArtifacts: {},
                },
                version: 0,
            })
        );

        await useStore.persist.rehydrate();

        const state = useStore.getState();
        expect(state.workflow).toBe('REQ_REVIEW');
        expect(state.stageIndex).toBe(0);
        expect(state.artifactContent).toContain('欢迎使用');
        expect(state.stageArtifacts.REVIEW).toBe(state.artifactContent);
    });

    it('should restore current artifact content when persisted stage artifacts are missing', async () => {
        localStorage.setItem(
            'agent-workspace-storage',
            JSON.stringify({
                state: {
                    workflow: 'TEST_DESIGN',
                    stageIndex: 0,
                    chatHistory: [],
                    artifactContent: '# Persisted artifact\n\n用户已经生成的需求分析内容',
                    artifactHistory: [],
                    stageArtifacts: {},
                },
                version: 0,
            })
        );

        await useStore.persist.rehydrate();

        const state = useStore.getState();
        expect(state.workflow).toBe('TEST_DESIGN');
        expect(state.stageIndex).toBe(0);
        expect(state.artifactContent).toBe('# Persisted artifact\n\n用户已经生成的需求分析内容');
        expect(state.stageArtifacts.CLARIFY).toBe(state.artifactContent);
    });

    it('should prefer persisted current artifact content over stale current-stage artifact', async () => {
        localStorage.setItem(
            'agent-workspace-storage',
            JSON.stringify({
                state: {
                    workflow: 'TEST_DESIGN',
                    stageIndex: 0,
                    chatHistory: [],
                    artifactContent: '# 最新需求分析\n\n用户刚生成的内容',
                    artifactHistory: [],
                    stageArtifacts: {
                        CLARIFY: '# 旧需求分析',
                    },
                },
                version: 0,
            })
        );

        await useStore.persist.rehydrate();

        const state = useStore.getState();
        expect(state.artifactContent).toBe('# 最新需求分析\n\n用户刚生成的内容');
        expect(state.stageArtifacts.CLARIFY).toBe(state.artifactContent);
    });

    it('should persist and restore artifact truncation state for the current artifact', async () => {
        localStorage.setItem(
            'agent-workspace-storage',
            JSON.stringify({
                state: {
                    workflow: 'TEST_DESIGN',
                    stageIndex: 0,
                    chatHistory: [],
                    artifactContent: '# 截断产物\n\n内容因为模型输出限制被截断',
                    artifactHistory: [],
                    stageArtifacts: {},
                    artifactTruncated: true,
                },
                version: 0,
            })
        );

        await useStore.persist.rehydrate();

        const state = useStore.getState();
        expect(state.artifactContent).toBe('# 截断产物\n\n内容因为模型输出限制被截断');
        expect(state.artifactTruncated).toBe(true);
    });

    it('records artifact section changes when current artifact content is replaced', () => {
        useStore.getState().setArtifactContent('# 文档\n\n## 范围\n\n旧范围\n\n## 风险\n\n保持不变');

        useStore.getState().setArtifactContent('# 文档\n\n## 范围\n\n新范围\n\n## 风险\n\n保持不变');

        expect(useStore.getState().artifactChangeIndex).toEqual([
            expect.objectContaining({
                kind: 'modified',
                title: '范围',
                anchor: 'h2:范围:1',
            }),
        ]);
    });

    it('clears artifact section changes when switching stage and clearing history', () => {
        useStore.getState().setArtifactContent('# 文档\n\n## 范围\n\n旧范围');
        useStore.getState().setArtifactContent('# 文档\n\n## 范围\n\n新范围');
        expect(useStore.getState().artifactChangeIndex).toHaveLength(1);

        useStore.getState().setStageIndex(1);
        expect(useStore.getState().artifactChangeIndex).toEqual([]);

        useStore.getState().setArtifactContent('# 策略\n\n## 方向\n\n旧方向');
        useStore.getState().setArtifactContent('# 策略\n\n## 方向\n\n新方向');
        expect(useStore.getState().artifactChangeIndex).toHaveLength(1);

        useStore.getState().clearHistory();
        expect(useStore.getState().artifactChangeIndex).toEqual([]);
    });

    it('applies artifact section patches to the active stage artifact', () => {
        const base = '# 文档\n\n## 范围\n\n旧范围\n\n## 风险\n\n保持不变';
        useStore.getState().setArtifactContent(base);

        const result = useStore.getState().applyArtifactSectionPatch({
            operation: 'replace',
            sectionAnchor: 'h2:范围:1',
            replacementMarkdown: '## 范围\n\n新范围',
            baseContent: base,
        });

        expect(result.applied).toBe(true);
        expect(useStore.getState().artifactContent).toBe('# 文档\n\n## 范围\n\n新范围\n\n## 风险\n\n保持不变');
        expect(useStore.getState().stageArtifacts.CLARIFY).toBe(useStore.getState().artifactContent);
        expect(useStore.getState().artifactChangeIndex).toEqual([
            expect.objectContaining({
                kind: 'modified',
                anchor: 'h2:范围:1',
            }),
        ]);
    });

    it('does not mutate artifact state when section patch application falls back', () => {
        const base = '# 文档\n\n## 范围\n\n旧范围';
        useStore.getState().setArtifactContent(base);

        const result = useStore.getState().applyArtifactSectionPatch({
            operation: 'replace',
            sectionAnchor: 'h2:不存在:1',
            replacementMarkdown: '## 不存在\n\n新范围',
            baseContent: base,
        });

        expect(result).toEqual({
            applied: false,
            content: base,
            changes: [],
            fallbackReason: 'section_not_found',
        });
        expect(useStore.getState().artifactContent).toBe(base);
        expect(useStore.getState().stageArtifacts.CLARIFY).toBe(base);
    });
});
