import type { MessageErrorDiagnostic } from './types';
import { isRecord } from './workspaceState';

export const sanitizeMessageErrorDiagnostic = (
    diagnostic: unknown
): MessageErrorDiagnostic | null => {
    if (!isRecord(diagnostic)) return null;
    if (!['structured', 'provider', 'generic'].includes(String(diagnostic.kind))) {
        return null;
    }
    if (typeof diagnostic.summary !== 'string' || !diagnostic.summary.trim()) {
        return null;
    }
    if (typeof diagnostic.rawMessage !== 'string' || !diagnostic.rawMessage.trim()) {
        return null;
    }

    const sanitized: MessageErrorDiagnostic = {
        kind: diagnostic.kind as MessageErrorDiagnostic['kind'],
        summary: diagnostic.summary,
        rawMessage: diagnostic.rawMessage,
    };
    if (typeof diagnostic.reason === 'string' && diagnostic.reason.trim()) {
        sanitized.reason = diagnostic.reason;
    }
    if (typeof diagnostic.action === 'string' && diagnostic.action.trim()) {
        sanitized.action = diagnostic.action;
    }
    if (typeof diagnostic.code === 'string' && diagnostic.code.trim()) {
        sanitized.code = diagnostic.code;
    }
    if (typeof diagnostic.phase === 'string' && diagnostic.phase.trim()) {
        sanitized.phase = diagnostic.phase;
    }
    if (typeof diagnostic.workflowId === 'string' && diagnostic.workflowId.trim()) {
        sanitized.workflowId = diagnostic.workflowId;
    }
    if (typeof diagnostic.stageId === 'string' && diagnostic.stageId.trim()) {
        sanitized.stageId = diagnostic.stageId;
    }
    if (typeof diagnostic.fieldPath === 'string' && diagnostic.fieldPath.trim()) {
        sanitized.fieldPath = diagnostic.fieldPath;
    }
    if (typeof diagnostic.validator === 'string' && diagnostic.validator.trim()) {
        sanitized.validator = diagnostic.validator;
    }
    if (typeof diagnostic.retryable === 'boolean') {
        sanitized.retryable = diagnostic.retryable;
    }
    return sanitized;
};
