import { WORKFLOWS } from './workflows';
import type { Message, WorkflowType } from './types';

export const isRecord = (value: unknown): value is Record<string, unknown> => (
  typeof value === 'object' && value !== null
);

export const isWorkflowType = (value: unknown): value is WorkflowType => (
  typeof value === 'string'
  && Object.prototype.hasOwnProperty.call(WORKFLOWS, value)
);

export const sanitizeCurrentRunId = (currentRunId: unknown): string | null => (
  typeof currentRunId === 'string' && currentRunId.trim()
    ? currentRunId.trim()
    : null
);

export const sanitizeStageArtifacts = (
  stageArtifacts: unknown,
  workflow: WorkflowType
): Record<string, string> => {
  if (!isRecord(stageArtifacts)) {
    return {};
  }

  const workflowStageIds = new Set(
    WORKFLOWS[workflow].stages.map(stage => stage.id)
  );
  const sanitizedArtifacts: Record<string, string> = {};
  Object.entries(stageArtifacts).forEach(([stageId, content]) => {
    if (workflowStageIds.has(stageId) && typeof content === 'string') {
      sanitizedArtifacts[stageId] = content;
    }
  });

  return sanitizedArtifacts;
};

export const sanitizeAttachments = (attachments: unknown): Message['attachments'] => {
  if (!Array.isArray(attachments)) return undefined;

  const sanitizedAttachments = attachments.flatMap((attachment): Message['attachments'] => {
    if (
      !isRecord(attachment)
      || typeof attachment.name !== 'string'
      || typeof attachment.data !== 'string'
      || typeof attachment.mimeType !== 'string'
    ) {
      return [];
    }
    return [{
      name: attachment.name,
      data: attachment.data,
      mimeType: attachment.mimeType,
    }];
  });

  return sanitizedAttachments.length > 0
    ? sanitizedAttachments
    : undefined;
};
