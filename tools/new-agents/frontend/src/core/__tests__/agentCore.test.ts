import { describe, expect, it } from 'vitest';

import {
    planArtifactVersionUpdate,
    planRetryFromHistory,
    planStageTransitionConfirmation,
    reduceAgentStreamChunk,
} from '../agentCore';
import type { Attachment } from '../types';

const testDesignStages = [
    { id: 'CLARIFY', name: '需求澄清', description: '明确测试对象' },
    { id: 'STRATEGY', name: '策略制定', description: '制定测试策略' },
    { id: 'CASES', name: '用例编写', description: '编写测试用例' },
];


describe('reduceAgentStreamChunk', () => {
    it('returns an artifact update for a normal artifact chunk', () => {
        const decision = reduceAgentStreamChunk(
            {
                chatResponse: '已更新文档。',
                newArtifact: '# 需求分析文档\n内容',
                action: '',
                hasArtifactUpdate: true,
            },
            {
                stageIndex: 0,
                stageCount: 4,
                currentStageId: 'CLARIFY',
                hasTransitioned: false,
            }
        );

        expect(decision).toEqual({
            assistantContent: '已更新文档。',
            artifactTruncated: false,
            artifactUpdate: {
                stageId: 'CLARIFY',
                content: '# 需求分析文档\n内容',
            },
            hasTransitioned: false,
            shouldStopStream: false,
        });
    });

    it('requests a pending transition and preserves the completed current-stage artifact', () => {
        const decision = reduceAgentStreamChunk(
            {
                chatResponse: '当前阶段已完成，请确认进入下一阶段。',
                newArtifact: '# 需求分析文档\n最终版',
                action: 'NEXT_STAGE',
                hasArtifactUpdate: true,
            },
            {
                stageIndex: 0,
                stageCount: 4,
                currentStageId: 'CLARIFY',
                hasTransitioned: false,
            }
        );

        expect(decision).toEqual({
            assistantContent: '当前阶段已完成，请确认进入下一阶段。',
            artifactTruncated: false,
            artifactUpdate: {
                stageId: 'CLARIFY',
                content: '# 需求分析文档\n最终版',
            },
            pendingStageTransition: {
                fromStageIndex: 0,
                toStageIndex: 1,
            },
            hasTransitioned: true,
            shouldStopStream: true,
        });
    });

    it('reports artifact truncation without creating an artifact update', () => {
        const decision = reduceAgentStreamChunk(
            {
                chatResponse: '生成被截断。',
                newArtifact: '# 原文档',
                action: '',
                hasArtifactUpdate: false,
                artifactTruncated: true,
            },
            {
                stageIndex: 0,
                stageCount: 4,
                currentStageId: 'CLARIFY',
                hasTransitioned: false,
            }
        );

        expect(decision).toEqual({
            assistantContent: '生成被截断。',
            artifactTruncated: true,
            hasTransitioned: false,
            shouldStopStream: false,
        });
    });

    it('preserves artifact patches on artifact update decisions', () => {
        const patch = {
            operation: 'replace' as const,
            sectionAnchor: 'h2:范围:1',
            replacementMarkdown: '## 范围\n\n新范围',
            baseContent: '# 文档\n\n## 范围\n\n旧范围',
        };

        const decision = reduceAgentStreamChunk(
            {
                chatResponse: '已局部更新。',
                newArtifact: '# 文档\n\n## 范围\n\n新范围',
                action: '',
                hasArtifactUpdate: true,
                artifactPatch: patch,
            },
            {
                stageIndex: 0,
                stageCount: 4,
                currentStageId: 'CLARIFY',
                hasTransitioned: false,
            }
        );

        expect(decision.artifactUpdate).toEqual({
            stageId: 'CLARIFY',
            content: '# 文档\n\n## 范围\n\n新范围',
            patch,
        });
    });
});

describe('planRetryFromHistory', () => {
    it('finds the last user message and returns rollback instructions', () => {
        const decision = planRetryFromHistory([
            {
                id: '1',
                role: 'user',
                content: '第一轮',
                timestamp: 1,
            },
            {
                id: '2',
                role: 'assistant',
                content: '第一轮回复',
                timestamp: 2,
            },
            {
                id: '3',
                role: 'user',
                content: '请重试这一轮',
                timestamp: 3,
                attachments: [
                    {
                        name: 'req.md',
                        data: 'cmVx',
                        mimeType: 'text/markdown',
                    },
                ],
            },
            {
                id: '4',
                role: 'assistant',
                content: '失败回复',
                timestamp: 4,
            },
        ]);

        expect(decision).toEqual({
            retryInput: '请重试这一轮',
            retryAttachments: [
                {
                    name: 'req.md',
                    data: 'cmVx',
                    mimeType: 'text/markdown',
                },
            ],
            messagesToRemove: 2,
        });
    });

    it('returns null when history has no user message', () => {
        const decision = planRetryFromHistory([
            {
                id: '1',
                role: 'assistant',
                content: '欢迎语',
                timestamp: 1,
            },
        ]);

        expect(decision).toBeNull();
    });

    it('returns null when the latest assistant response is not retryable', () => {
        const decision = planRetryFromHistory([
            {
                id: '1',
                role: 'user',
                content: '上一阶段真实用户输入',
                timestamp: 1,
            },
            {
                id: '2',
                role: 'assistant',
                content: '内部续写生成的新阶段内容',
                timestamp: 2,
                retryable: false,
            },
        ]);

        expect(decision).toBeNull();
    });

    it('drops non-array attachments when planning retry from persisted history', () => {
        const decision = planRetryFromHistory([
            {
                id: '1',
                role: 'user',
                content: '请重试脏附件历史',
                timestamp: 1,
                attachments: { length: 1 } as unknown as Attachment[],
            },
            {
                id: '2',
                role: 'assistant',
                content: '失败回复',
                timestamp: 2,
            },
        ]);

        expect(decision).toEqual({
            retryInput: '请重试脏附件历史',
            retryAttachments: [],
            messagesToRemove: 2,
        });
    });
});

describe('planArtifactVersionUpdate', () => {
    it('returns null for empty artifact content', () => {
        expect(planArtifactVersionUpdate('', [])).toBeNull();
    });

    it('returns null for welcome artifact content', () => {
        expect(
            planArtifactVersionUpdate(
                '# 欢迎使用 Lisa 测试专家\n\n请在左侧输入您的需求。',
                []
            )
        ).toBeNull();
    });

    it('returns a content-only write plan when history is empty', () => {
        expect(
            planArtifactVersionUpdate('# 需求分析文档\n内容', [])
        ).toEqual({
            content: '# 需求分析文档\n内容',
        });
    });

    it('returns null when the latest artifact version already has the same content', () => {
        expect(
            planArtifactVersionUpdate('# 需求分析文档\n内容', [
                {
                    id: 'v1',
                    timestamp: 1,
                    content: '# 需求分析文档\n内容',
                    stageId: 'CLARIFY',
                },
            ])
        ).toBeNull();
    });

    it('returns a content-only write plan when the latest artifact version differs', () => {
        expect(
            planArtifactVersionUpdate('# 需求分析文档\n新内容', [
                {
                    id: 'v1',
                    timestamp: 1,
                    content: '# 需求分析文档\n旧内容',
                    stageId: 'CLARIFY',
                },
            ])
        ).toEqual({
            content: '# 需求分析文档\n新内容',
        });
    });
});

describe('planStageTransitionConfirmation', () => {
    it('returns null when there is no pending transition', () => {
        const decision = planStageTransitionConfirmation({
            pendingTransition: null,
            stageIndex: 0,
            stages: testDesignStages,
            artifactContent: 'stage-0-content',
            stageArtifacts: {
                CLARIFY: 'stage-0-content',
            },
        });

        expect(decision).toBeNull();
    });

    it('clears pending transition without advancing when target stage is invalid', () => {
        const decision = planStageTransitionConfirmation({
            pendingTransition: { fromStageIndex: 2, toStageIndex: 3 },
            stageIndex: 2,
            stages: testDesignStages,
            artifactContent: 'stage-2-content',
            stageArtifacts: {
                CASES: 'stage-2-content',
            },
        });

        expect(decision).toEqual({
            pendingStageTransition: null,
        });
    });

    it('clears pending transition without advancing when target is not the immediate next stage', () => {
        expect(planStageTransitionConfirmation({
            pendingTransition: { fromStageIndex: 0, toStageIndex: 2 },
            stageIndex: 0,
            stages: testDesignStages,
            artifactContent: 'updated clarify artifact',
            stageArtifacts: {
                CLARIFY: 'old clarify artifact',
            },
        })).toEqual({
            pendingStageTransition: null,
        });

        expect(planStageTransitionConfirmation({
            pendingTransition: { fromStageIndex: 1, toStageIndex: 0 },
            stageIndex: 1,
            stages: testDesignStages,
            artifactContent: 'updated strategy artifact',
            stageArtifacts: {
                STRATEGY: 'old strategy artifact',
            },
        })).toEqual({
            pendingStageTransition: null,
        });
    });

    it('confirms transition and saves the current stage artifact', () => {
        const decision = planStageTransitionConfirmation({
            pendingTransition: { fromStageIndex: 0, toStageIndex: 1 },
            stageIndex: 0,
            stages: testDesignStages,
            artifactContent: 'updated clarify artifact',
            stageArtifacts: {
                CLARIFY: 'old clarify artifact',
            },
        });

        expect(decision).toEqual({
            pendingStageTransition: null,
            stageIndex: 1,
            artifactContent: '# 策略制定\n\n暂无产出物。',
            artifactTruncated: false,
            stageArtifacts: {
                CLARIFY: 'updated clarify artifact',
            },
        });
    });

    it('uses the existing target stage artifact when confirming transition', () => {
        const decision = planStageTransitionConfirmation({
            pendingTransition: { fromStageIndex: 0, toStageIndex: 1 },
            stageIndex: 0,
            stages: testDesignStages,
            artifactContent: 'updated clarify artifact',
            stageArtifacts: {
                CLARIFY: 'old clarify artifact',
                STRATEGY: '# 测试策略蓝图\n已有内容',
            },
        });

        expect(decision).toEqual({
            pendingStageTransition: null,
            stageIndex: 1,
            artifactContent: '# 测试策略蓝图\n已有内容',
            artifactTruncated: false,
            stageArtifacts: {
                CLARIFY: 'updated clarify artifact',
                STRATEGY: '# 测试策略蓝图\n已有内容',
            },
        });
    });

    it('clears stale pending transition without changing stage when current stage no longer matches the pending source', () => {
        const decision = planStageTransitionConfirmation({
            pendingTransition: { fromStageIndex: 0, toStageIndex: 1 },
            stageIndex: 2,
            stages: testDesignStages,
            artifactContent: 'current cases artifact',
            stageArtifacts: {
                CLARIFY: 'old clarify artifact',
            },
        });

        expect(decision).toEqual({
            pendingStageTransition: null,
        });
    });
});
