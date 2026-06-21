import { WORKFLOWS } from './workflows';
import type {
  ArtifactAuditEvent,
  ArtifactComment,
  ArtifactCommentReply,
  ArtifactCommentStatus,
  ArtifactSectionLock,
  Message,
  WorkflowType,
} from './types';

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

const sanitizeArtifactCommentReplies = (replies: unknown): ArtifactCommentReply[] => {
  if (!Array.isArray(replies)) return [];

  return replies.flatMap((reply): ArtifactCommentReply[] => {
    if (
      !isRecord(reply)
      || typeof reply.id !== 'string'
      || typeof reply.content !== 'string'
      || !reply.content.trim()
      || typeof reply.createdAt !== 'number'
    ) {
      return [];
    }

    return [{
      id: reply.id,
      content: reply.content,
      createdAt: reply.createdAt,
    }];
  });
};

const sanitizeArtifactCommentStatus = (
  status: unknown
): ArtifactCommentStatus => (
  status === 'resolved' ? 'resolved' : 'open'
);

const sanitizeArtifactCommentResolvedAt = (
  status: ArtifactCommentStatus,
  resolvedAt: unknown
): number | null => (
  status === 'resolved' && typeof resolvedAt === 'number'
    ? resolvedAt
    : null
);

export const sanitizeOptionalArtifactText = (value: unknown): string | null => {
  if (typeof value !== 'string') return null;
  const normalizedValue = value.replace(/\s+/g, ' ').trim();
  return normalizedValue ? normalizedValue : null;
};

export const sanitizeArtifactComments = (
  artifactComments: unknown,
  workflow: WorkflowType
): ArtifactComment[] => {
  if (!Array.isArray(artifactComments)) return [];

  const workflowStageIds = new Set(
    WORKFLOWS[workflow].stages.map(stage => stage.id)
  );
  return artifactComments.flatMap((comment): ArtifactComment[] => {
    if (
      !isRecord(comment)
      || typeof comment.id !== 'string'
      || typeof comment.stageId !== 'string'
      || !workflowStageIds.has(comment.stageId)
      || typeof comment.content !== 'string'
      || !comment.content.trim()
      || typeof comment.artifactExcerpt !== 'string'
      || typeof comment.createdAt !== 'number'
    ) {
      return [];
    }

    return [{
      id: comment.id,
      stageId: comment.stageId,
      content: comment.content,
      artifactExcerpt: comment.artifactExcerpt,
      anchorText: sanitizeOptionalArtifactText(comment.anchorText),
      createdAt: comment.createdAt,
      status: sanitizeArtifactCommentStatus(comment.status),
      resolvedAt: sanitizeArtifactCommentResolvedAt(
        sanitizeArtifactCommentStatus(comment.status),
        comment.resolvedAt
      ),
      replies: sanitizeArtifactCommentReplies(comment.replies),
    }];
  });
};

export const sanitizeArtifactSectionLocks = (
  artifactSectionLocks: unknown,
  workflow: WorkflowType
): ArtifactSectionLock[] => {
  if (!Array.isArray(artifactSectionLocks)) return [];

  const workflowStageIds = new Set(
    WORKFLOWS[workflow].stages.map(stage => stage.id)
  );
  return artifactSectionLocks.flatMap((lock): ArtifactSectionLock[] => {
    if (
      !isRecord(lock)
      || typeof lock.id !== 'string'
      || typeof lock.stageId !== 'string'
      || !workflowStageIds.has(lock.stageId)
      || typeof lock.heading !== 'string'
      || !lock.heading.trim()
      || typeof lock.content !== 'string'
      || !lock.content.trim()
      || typeof lock.createdAt !== 'number'
    ) {
      return [];
    }

    return [{
      id: lock.id,
      stageId: lock.stageId,
      heading: lock.heading,
      sectionAnchor: sanitizeOptionalArtifactText(lock.sectionAnchor),
      content: lock.content,
      createdAt: lock.createdAt,
    }];
  });
};

export const sanitizeArtifactAuditEvents = (
  artifactAuditEvents: unknown,
  workflow: WorkflowType
): ArtifactAuditEvent[] => {
  if (!Array.isArray(artifactAuditEvents)) return [];

  const workflowStageIds = new Set(
    WORKFLOWS[workflow].stages.map(stage => stage.id)
  );
  return artifactAuditEvents.flatMap((event): ArtifactAuditEvent[] => {
    if (
      !isRecord(event)
      || typeof event.stageId !== 'string'
      || !workflowStageIds.has(event.stageId)
      || typeof event.eventType !== 'string'
      || !event.eventType.trim()
      || typeof event.summary !== 'string'
      || !event.summary.trim()
      || typeof event.createdAt !== 'number'
    ) {
      return [];
    }

    return [{
      stageId: event.stageId,
      eventType: event.eventType,
      summary: event.summary,
      createdAt: event.createdAt,
    }];
  });
};
