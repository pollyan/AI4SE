import { describe, expect, it } from 'vitest';
import {
    isRecord,
    isWorkflowType,
    sanitizeArtifactAuditEvents,
    sanitizeArtifactComments,
    sanitizeArtifactSectionLocks,
    sanitizeCurrentRunId,
    sanitizeStageArtifacts,
} from '../workspaceState';

describe('workspaceState helpers', () => {
    it('should identify plain records without accepting null or primitives', () => {
        expect(isRecord({ workflow: 'TEST_DESIGN' })).toBe(true);
        expect(isRecord(null)).toBe(false);
        expect(isRecord('TEST_DESIGN')).toBe(false);
    });

    it('should validate known runtime workflow ids', () => {
        expect(isWorkflowType('TEST_DESIGN')).toBe(true);
        expect(isWorkflowType('VALUE_DISCOVERY')).toBe(true);
        expect(isWorkflowType('missing')).toBe(false);
    });

    it('should sanitize stage artifacts to the active workflow stages', () => {
        expect(sanitizeStageArtifacts({
            CLARIFY: '# Clarify',
            STRATEGY: '# Strategy',
            BLUEPRINT: '# Cross workflow',
            CASES: 42,
        }, 'TEST_DESIGN')).toEqual({
            CLARIFY: '# Clarify',
            STRATEGY: '# Strategy',
        });
    });

    it('should trim valid run ids and drop blank or malformed values', () => {
        expect(sanitizeCurrentRunId(' run-123 ')).toBe('run-123');
        expect(sanitizeCurrentRunId('   ')).toBeNull();
        expect(sanitizeCurrentRunId(123)).toBeNull();
    });

    it('should sanitize artifact comments to valid workflow stages', () => {
        expect(sanitizeArtifactComments([
            {
                id: 'comment-1',
                stageId: 'CLARIFY',
                content: '需要确认登录边界。',
                artifactExcerpt: '登录边界',
                anchorText: ' 登录边界 ',
                createdAt: 1710000000000,
                status: 'resolved',
                resolvedAt: 1710000000100,
                replies: [
                    {
                        id: 'reply-1',
                        content: '已确认。',
                        createdAt: 1710000000200,
                    },
                    {
                        id: 'bad-reply',
                        content: '   ',
                        createdAt: 1710000000300,
                    },
                ],
            },
            {
                id: 'cross-workflow-comment',
                stageId: 'BLUEPRINT',
                content: '跨 workflow 批注应被过滤。',
                artifactExcerpt: '跨 workflow',
                createdAt: 1710000000400,
            },
        ], 'TEST_DESIGN')).toEqual([
            {
                id: 'comment-1',
                stageId: 'CLARIFY',
                content: '需要确认登录边界。',
                artifactExcerpt: '登录边界',
                anchorText: '登录边界',
                createdAt: 1710000000000,
                status: 'resolved',
                resolvedAt: 1710000000100,
                replies: [
                    {
                        id: 'reply-1',
                        content: '已确认。',
                        createdAt: 1710000000200,
                    },
                ],
            },
        ]);
    });

    it('should sanitize artifact section locks and audit events to valid workflow stages', () => {
        expect(sanitizeArtifactSectionLocks([
            {
                id: 'lock-1',
                stageId: 'STRATEGY',
                heading: '## 风险策略',
                sectionAnchor: ' h2:风险策略:1 ',
                content: '## 风险策略\n\n已锁定。',
                createdAt: 1710000000000,
            },
            {
                id: 'cross-workflow-lock',
                stageId: 'BLUEPRINT',
                heading: '## 蓝图',
                content: '跨 workflow lock',
                createdAt: 1710000000100,
            },
        ], 'TEST_DESIGN')).toEqual([
            {
                id: 'lock-1',
                stageId: 'STRATEGY',
                heading: '## 风险策略',
                sectionAnchor: 'h2:风险策略:1',
                content: '## 风险策略\n\n已锁定。',
                createdAt: 1710000000000,
            },
        ]);

        expect(sanitizeArtifactAuditEvents([
            {
                stageId: 'CASES',
                eventType: 'artifact_saved',
                summary: '保存了 CASES 阶段产出物 v1',
                createdAt: 1710000000200,
            },
            {
                stageId: 'BLUEPRINT',
                eventType: 'artifact_saved',
                summary: '跨 workflow event',
                createdAt: 1710000000300,
            },
        ], 'TEST_DESIGN')).toEqual([
            {
                stageId: 'CASES',
                eventType: 'artifact_saved',
                summary: '保存了 CASES 阶段产出物 v1',
                createdAt: 1710000000200,
            },
        ]);
    });
});
