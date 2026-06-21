import { describe, expect, it } from 'vitest';
import {
    isRecord,
    isWorkflowType,
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
});
