import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { WORKFLOWS } from './core/workflows';
import { AgentRunSnapshot, AgentRunSnapshotContextSummary, ArtifactAuditEvent, ArtifactComment, ArtifactSectionLock, ArtifactVisualDiagnosticInput, ChatState as AppState, ArtifactVersion, Message, WorkflowHandoff, WorkflowType } from './core/types';
import { getAgentById } from './core/config/agents';
import { planStageTransitionConfirmation } from './core/agentCore';
import { sanitizeMessageErrorDiagnostic } from './core/messageDiagnostics';
import {
  applyArtifactSectionPatch as applyArtifactSectionPatchToContent,
  buildArtifactSectionChangeIndex,
} from './core/artifactSections';
import {
  isRecord,
  isWorkflowType,
  sanitizeArtifactAuditEvents,
  sanitizeArtifactComments,
  sanitizeArtifactSectionLocks,
  sanitizeAttachments,
  sanitizeCurrentRunId,
  sanitizeOptionalArtifactText,
  sanitizeStageArtifacts,
} from './core/workspaceState';

// Re-export for compatibility
export * from './core/types';
export * from './core/workflows';

const DEFAULT_WORKFLOW: WorkflowType = 'TEST_DESIGN';

export const getWelcomeMessage = (workflow: WorkflowType): string => {
  const wf = WORKFLOWS[workflow];
  if (!wf) return '# 欢迎使用\n\n请在左侧输入您的需求。';

  if (wf.welcomeMessage) {
    return wf.welcomeMessage;
  }

  const agentId = wf.agentId;
  const workflowName = wf.name;
  const agentConfig = getAgentById(agentId);
  const displayTitle = agentConfig?.displayTitle || agentId;

  if (agentConfig?.welcomeTemplate) {
    return agentConfig.welcomeTemplate.replace('{agentName}', displayTitle).replace('{workflowName}', workflowName);
  }

  // Fallback
  return `# 欢迎使用 ${displayTitle}\n\n我们将通过【${workflowName}】流程，共同为您生成相关的产出物文档。`;
};

const sanitizeChatHistory = (chatHistory: unknown): Message[] => {
  if (!Array.isArray(chatHistory)) return [];

  return chatHistory.flatMap((message): Message[] => {
    if (
      !isRecord(message)
      || typeof message.id !== 'string'
      || (message.role !== 'user' && message.role !== 'assistant')
      || typeof message.content !== 'string'
      || typeof message.timestamp !== 'number'
    ) {
      return [];
    }

    const sanitizedMessage: Message = {
      id: message.id,
      role: message.role,
      content: message.content,
      timestamp: message.timestamp,
    };
    const attachments = sanitizeAttachments(message.attachments);
    if (attachments) {
      sanitizedMessage.attachments = attachments;
    }
    if (typeof message.retryable === 'boolean') {
      sanitizedMessage.retryable = message.retryable;
    }
    const errorDiagnostic = sanitizeMessageErrorDiagnostic(message.errorDiagnostic);
    if (errorDiagnostic) {
      sanitizedMessage.errorDiagnostic = errorDiagnostic;
    }
    return [sanitizedMessage];
  });
};

const sanitizeArtifactHistory = (artifactHistory: unknown): ArtifactVersion[] => {
  if (!Array.isArray(artifactHistory)) return [];

  return artifactHistory.flatMap((version): ArtifactVersion[] => {
    if (
      !isRecord(version)
      || typeof version.id !== 'string'
      || typeof version.timestamp !== 'number'
      || typeof version.content !== 'string'
      || typeof version.stageId !== 'string'
    ) {
      return [];
    }
    return [{
      id: version.id,
      timestamp: version.timestamp,
      content: version.content,
      stageId: version.stageId,
    }];
  });
};

const getInitialArtifactForStage = (
  workflow: WorkflowType,
  stageIndex: number
): string => {
  const stage = WORKFLOWS[workflow].stages[stageIndex];
  if (!stage) return getWelcomeMessage(workflow);
  if (stageIndex === 0) return getWelcomeMessage(workflow);
  return stage.template || `# ${stage.name}\n\n暂无产出物。`;
};

const buildHandoffMessage = (handoff: WorkflowHandoff): Message => ({
  id: `handoff-${handoff.id}-v${handoff.sourceArtifactVersion}`,
  role: 'user',
  content: handoff.prompt,
  timestamp: Date.now(),
});

const buildSnapshotMessages = (snapshot: AgentRunSnapshot): Message[] => (
  [...snapshot.messages]
    .sort((left, right) => left.sequenceIndex - right.sequenceIndex)
    .map((message) => ({
      id: `${snapshot.run.id}-message-${message.sequenceIndex}`,
      role: message.role,
      content: message.content,
      timestamp: Date.now() + message.sequenceIndex,
      ...(message.errorDiagnostic
        ? { errorDiagnostic: message.errorDiagnostic }
        : {}),
    }))
);

const buildSnapshotArtifactHistory = (
  snapshot: AgentRunSnapshot,
  validStageIds: Set<string>
): ArtifactVersion[] => (
  snapshot.artifacts.flatMap((artifact): ArtifactVersion[] => {
    if (!validStageIds.has(artifact.stageId)) {
      return [];
    }
    return [{
      id: `${snapshot.run.id}-${artifact.stageId}-v${artifact.versionNumber}`,
      timestamp: Date.now() + artifact.versionNumber,
      content: artifact.content,
      stageId: artifact.stageId,
    }];
  })
);

const isSameContextSummary = (
  left: Pick<AgentRunSnapshotContextSummary, 'sourceType' | 'sourceStageId' | 'summaryType'>,
  right: Pick<AgentRunSnapshotContextSummary, 'sourceType' | 'sourceStageId' | 'summaryType'>
): boolean => (
  left.sourceType === right.sourceType
  && left.sourceStageId === right.sourceStageId
  && left.summaryType === right.summaryType
);

const sanitizePersistedWorkspaceState = (
  persistedState: Record<string, unknown>,
  currentState: AppState
): Partial<AppState> => {
  const persistedWorkflow = persistedState.workflow;
  const hasValidPersistedWorkflow = isWorkflowType(persistedWorkflow);
  let workflow: WorkflowType = DEFAULT_WORKFLOW;
  if (hasValidPersistedWorkflow) {
    workflow = persistedWorkflow;
  }
  const hasPersistedServiceRun = sanitizeCurrentRunId(persistedState.currentRunId) !== null;
  const stageCount = WORKFLOWS[workflow].stages.length;
  const hasValidPersistedStageIndex = (
    Number.isInteger(persistedState.stageIndex)
    && (persistedState.stageIndex as number) >= 0
    && (persistedState.stageIndex as number) < stageCount
  );
  const stageIndex = !hasPersistedServiceRun && hasValidPersistedStageIndex
    ? persistedState.stageIndex as number
    : 0;
  const stageArtifacts = hasPersistedServiceRun
    ? {}
    : sanitizeStageArtifacts(
      persistedState.stageArtifacts,
      workflow
    );
  const currentStageId = WORKFLOWS[workflow].stages[stageIndex].id;
  const persistedArtifactContent = !hasPersistedServiceRun
    && hasValidPersistedWorkflow
    && hasValidPersistedStageIndex
    && typeof persistedState.artifactContent === 'string'
    && persistedState.artifactContent.trim()
    ? persistedState.artifactContent
    : null;
  const artifactContent = persistedArtifactContent
    || stageArtifacts[currentStageId]
    || getWelcomeMessage(workflow);
  const artifactTruncated = persistedArtifactContent !== null
    && persistedState.artifactTruncated === true;

  return {
    workflow,
    stageIndex,
    chatHistory: hasPersistedServiceRun ? [] : sanitizeChatHistory(persistedState.chatHistory),
    artifactContent,
    artifactChangeIndex: [],
    artifactHistory: hasPersistedServiceRun ? [] : sanitizeArtifactHistory(persistedState.artifactHistory),
    artifactComments: hasPersistedServiceRun ? [] : sanitizeArtifactComments(persistedState.artifactComments, workflow),
    artifactSectionLocks: hasPersistedServiceRun ? [] : sanitizeArtifactSectionLocks(persistedState.artifactSectionLocks, workflow),
    artifactAuditEvents: hasPersistedServiceRun ? [] : sanitizeArtifactAuditEvents(persistedState.artifactAuditEvents, workflow),
    stageArtifacts: {
      ...stageArtifacts,
      [currentStageId]: artifactContent,
    },
    currentRunId: null,
    isGenerating: currentState.isGenerating,
    pendingStageTransition: currentState.pendingStageTransition,
    artifactTruncated: hasPersistedServiceRun ? false : artifactTruncated,
  };
};

const OLD_KEY = 'lisa-storage';
const NEW_KEY = 'agent-workspace-storage';
function isStorageAccessError(error: unknown): boolean {
  return typeof DOMException !== 'undefined' && error instanceof DOMException;
}

if (typeof window !== 'undefined') {
  try {
    const oldData = localStorage.getItem(OLD_KEY);
    if (oldData && !localStorage.getItem(NEW_KEY)) {
      localStorage.setItem(NEW_KEY, oldData);
      localStorage.removeItem(OLD_KEY);
    }
  } catch (error) {
    if (!isStorageAccessError(error)) {
      throw error;
    }
  }
}

export const useStore = create<AppState>()(
  persist<AppState, [], [], Partial<AppState>>(
    (set) => ({
      workflow: DEFAULT_WORKFLOW,
      stageIndex: 0,
      chatHistory: [],
      artifactContent: getWelcomeMessage(DEFAULT_WORKFLOW),
      artifactChangeIndex: [],
      artifactHistory: [],
      artifactComments: [],
      artifactSectionLocks: [],
      artifactAuditEvents: [],
      artifactVisualDiagnostics: [],
      artifactVisualDiagnosticFocusRequest: null,
      stageArtifacts: {
        [WORKFLOWS[DEFAULT_WORKFLOW].stages[0].id]: getWelcomeMessage(DEFAULT_WORKFLOW)
      },
      contextSummaries: [],
      currentRunId: null,
      isSettingsOpen: false,
      configRefreshSeq: 0,
      isGenerating: false,
      // P0-4: Stage transition confirmation gate
      pendingStageTransition: null,
      // P0-9: Artifact truncation flag
      artifactTruncated: false,

      setWorkflow: (workflow) => set({
        workflow,
        stageIndex: 0,
        chatHistory: [],
        artifactHistory: [],
        artifactChangeIndex: [],
        artifactComments: [],
        artifactSectionLocks: [],
        artifactAuditEvents: [],
        artifactVisualDiagnostics: [],
        artifactVisualDiagnosticFocusRequest: null,
        artifactContent: getWelcomeMessage(workflow),
        stageArtifacts: {
          [WORKFLOWS[workflow].stages[0].id]: getWelcomeMessage(workflow)
        },
        contextSummaries: [],
        pendingStageTransition: null,
        artifactTruncated: false,
        isGenerating: false,
        currentRunId: null,
      }),
      setStageIndex: (index) => set((state) => {
        const workflowStages = WORKFLOWS[state.workflow].stages;
        const targetStage = workflowStages[index];
        const currentStage = workflowStages[state.stageIndex];
        if (!targetStage || !currentStage) {
          return {};
        }

        const newStageArtifacts = { ...state.stageArtifacts };
        const currentStageId = currentStage.id;
        newStageArtifacts[currentStageId] = state.artifactContent;

        const targetStageId = targetStage.id;
        return {
          stageIndex: index,
          stageArtifacts: newStageArtifacts,
          artifactContent: newStageArtifacts[targetStageId] || `# ${targetStage.name}\n\n暂无产出物。`,
          artifactChangeIndex: [],
          artifactTruncated: false,
          artifactVisualDiagnostics: [],
          artifactVisualDiagnosticFocusRequest: null,
          pendingStageTransition: null,
          isGenerating: false,
        };
      }),
      transitionToNextStage: (initialStageId, initialArtifact) => set((state) => {
        const workflowStages = WORKFLOWS[state.workflow].stages;
        const currentStageConfig = workflowStages[state.stageIndex];
        if (!currentStageConfig || currentStageConfig.id !== initialStageId) {
          return {};
        }

        const nextStage = state.stageIndex + 1;
        const nextStageConfig = workflowStages[nextStage];
        if (!nextStageConfig) {
          return {};
        }

        const newStageArtifacts = { ...state.stageArtifacts };
        newStageArtifacts[initialStageId] = initialArtifact;

        const nextStageId = nextStageConfig.id;
        const nextArtifactContent = newStageArtifacts[nextStageId] || `# ${nextStageConfig.name}\n\n暂无产出物。`;

        return {
          stageIndex: nextStage,
          stageArtifacts: newStageArtifacts,
          artifactContent: nextArtifactContent,
          artifactChangeIndex: [],
          pendingStageTransition: null,
          artifactTruncated: false,
          artifactVisualDiagnostics: [],
          artifactVisualDiagnosticFocusRequest: null,
          isGenerating: false,
        };
      }),
      addMessage: (msg) => set((state) => ({ chatHistory: [...state.chatHistory, msg] })),
      updateLastMessage: (content, errorDiagnostic) => set((state) => {
        const lastMessage = state.chatHistory[state.chatHistory.length - 1];
        if (
          !lastMessage
          || (
            lastMessage.content === content
            && errorDiagnostic === undefined
          )
        ) {
          return state;
        }
        const newHistory = [...state.chatHistory];
        newHistory[newHistory.length - 1] = {
          ...lastMessage,
          content,
          ...(errorDiagnostic ? { errorDiagnostic } : {}),
        };
        return { chatHistory: newHistory };
      }),
      updateMessage: (id, content) => set((state) => {
        const newHistory = state.chatHistory.map(m => m.id === id ? { ...m, content } : m);
        return { chatHistory: newHistory };
      }),
      removeLastMessage: () => set((state) => {
        const newHistory = [...state.chatHistory];
        if (newHistory.length > 0) {
          newHistory.pop();
        }
        return { chatHistory: newHistory };
      }),
      setArtifactContent: (artifactContent) => set((state) => {
        const newStageArtifacts = { ...state.stageArtifacts };
        const currentStageId = WORKFLOWS[state.workflow].stages[state.stageIndex].id;
        newStageArtifacts[currentStageId] = artifactContent;
        return {
          artifactContent,
          artifactChangeIndex: buildArtifactSectionChangeIndex(
            state.artifactContent,
            artifactContent
          ),
          stageArtifacts: newStageArtifacts,
          artifactVisualDiagnostics: [],
          artifactVisualDiagnosticFocusRequest: null,
        };
      }),
      applyArtifactSectionPatch: (patch) => {
        const result = applyArtifactSectionPatchToContent(
          useStore.getState().artifactContent,
          patch
        );
        if (!result.applied) return result;

        set((state) => {
          const currentStageId = WORKFLOWS[state.workflow].stages[state.stageIndex].id;
          return {
            artifactContent: result.content,
            artifactChangeIndex: result.changes,
            stageArtifacts: {
              ...state.stageArtifacts,
              [currentStageId]: result.content,
            },
            artifactVisualDiagnostics: [],
            artifactVisualDiagnosticFocusRequest: null,
          };
        });
        return result;
      },
      setStageArtifact: (stageId, content) => set((state) => {
        const workflowStageIds = new Set(
          WORKFLOWS[state.workflow].stages.map(stage => stage.id)
        );
        if (!workflowStageIds.has(stageId)) {
          return {};
        }

        const newStageArtifacts = { ...state.stageArtifacts };
        newStageArtifacts[stageId] = content;
        return {
          stageArtifacts: newStageArtifacts,
          artifactVisualDiagnostics: state.artifactVisualDiagnostics.filter(
            diagnostic => diagnostic.stageId !== stageId
          ),
          artifactVisualDiagnosticFocusRequest: state.artifactVisualDiagnostics.some(
            diagnostic => diagnostic.stageId === stageId
              && diagnostic.id === state.artifactVisualDiagnosticFocusRequest?.id
          )
            ? null
            : state.artifactVisualDiagnosticFocusRequest,
        };
      }),
      addArtifactVersion: (version) => set((state) => {
        const currentStageId = WORKFLOWS[state.workflow].stages[state.stageIndex].id;
        return {
          artifactHistory: [
            ...state.artifactHistory,
            {
              ...version,
              stageId: 'stageId' in version ? version.stageId : currentStageId,
            },
          ],
        };
      }),
      addArtifactComment: (comment) => set((state) => {
        const currentStageId = WORKFLOWS[state.workflow].stages[state.stageIndex].id;
        const stageId = comment.stageId ?? currentStageId;
        const workflowStageIds = new Set(
          WORKFLOWS[state.workflow].stages.map(stage => stage.id)
        );
        const content = comment.content.trim();
        if (!workflowStageIds.has(stageId) || !content) {
          return {};
        }

        return {
          artifactComments: [
            ...state.artifactComments,
            {
              id: `artifact-comment-${Date.now()}-${state.artifactComments.length + 1}`,
              stageId,
              content,
              artifactExcerpt: comment.artifactExcerpt.trim(),
              anchorText: sanitizeOptionalArtifactText(comment.anchorText),
              createdAt: Date.now(),
              status: 'open',
              resolvedAt: null,
              replies: [],
            },
          ],
        };
      }),
      addArtifactCommentReply: (commentId, content) => set((state) => {
        const replyContent = content.trim();
        if (!replyContent) {
          return {};
        }

        return {
          artifactComments: state.artifactComments.map((comment) => (
            comment.id === commentId
              ? {
                ...comment,
                replies: [
                  ...comment.replies,
                  {
                    id: `artifact-comment-reply-${Date.now()}-${comment.replies.length + 1}`,
                    content: replyContent,
                    createdAt: Date.now(),
                  },
                ],
              }
              : comment
          )),
        };
      }),
      setArtifactCommentStatus: (commentId, status) => set((state) => ({
        artifactComments: state.artifactComments.map((comment) => (
          comment.id === commentId
            ? {
              ...comment,
              status,
              resolvedAt: status === 'resolved' ? Date.now() : null,
            }
            : comment
        )),
      })),
      updateArtifactCommentAnchor: (commentId, anchorText) => set((state) => {
        const normalizedAnchorText = sanitizeOptionalArtifactText(anchorText);
        if (!normalizedAnchorText) {
          return {};
        }

        return {
          artifactComments: state.artifactComments.map((comment) => (
            comment.id === commentId
              ? {
                ...comment,
                artifactExcerpt: normalizedAnchorText,
                anchorText: normalizedAnchorText,
              }
              : comment
          )),
        };
      }),
      removeArtifactComment: (commentId) => set((state) => ({
        artifactComments: state.artifactComments.filter(comment => comment.id !== commentId),
      })),
      getArtifactCommentsForStage: (stageId) => (
        useStore.getState().artifactComments.filter(comment => comment.stageId === stageId)
      ),
      addArtifactSectionLock: (lock) => set((state) => {
        const currentStageId = WORKFLOWS[state.workflow].stages[state.stageIndex].id;
        const stageId = lock.stageId ?? currentStageId;
        const workflowStageIds = new Set(
          WORKFLOWS[state.workflow].stages.map(stage => stage.id)
        );
        const heading = lock.heading.trim();
        const content = lock.content.trim();
        const sectionAnchor = sanitizeOptionalArtifactText(lock.sectionAnchor);
        if (!workflowStageIds.has(stageId) || !heading || !content) {
          return {};
        }

        return {
          artifactSectionLocks: [
            ...state.artifactSectionLocks.filter(existing => !(
              existing.stageId === stageId
              && (
                (sectionAnchor !== null && existing.sectionAnchor === sectionAnchor)
                || (sectionAnchor === null && existing.sectionAnchor === null && existing.heading === heading)
              )
            )),
            {
              id: `artifact-section-lock-${Date.now()}-${state.artifactSectionLocks.length + 1}`,
              stageId,
              heading,
              sectionAnchor,
              content,
              createdAt: Date.now(),
            },
          ],
        };
      }),
      removeArtifactSectionLock: (lockId) => set((state) => ({
        artifactSectionLocks: state.artifactSectionLocks.filter(lock => lock.id !== lockId),
      })),
      getArtifactSectionLocksForStage: (stageId) => (
        useStore.getState().artifactSectionLocks.filter(lock => lock.stageId === stageId)
      ),
      addArtifactAuditEvent: (event) => set((state) => {
        const currentStageId = WORKFLOWS[state.workflow].stages[state.stageIndex].id;
        const stageId = event.stageId ?? currentStageId;
        const workflowStageIds = new Set(
          WORKFLOWS[state.workflow].stages.map(stage => stage.id)
        );
        const eventType = event.eventType.trim();
        const summary = event.summary.trim();
        if (!workflowStageIds.has(stageId) || !eventType || !summary) {
          return {};
        }

        return {
          artifactAuditEvents: [
            ...state.artifactAuditEvents,
            {
              stageId,
              eventType,
              summary,
              createdAt: event.createdAt ?? Date.now(),
            },
          ],
        };
      }),
      getArtifactAuditEventsForStage: (stageId) => (
        useStore.getState().artifactAuditEvents.filter(event => event.stageId === stageId)
      ),
      setArtifactVisualDiagnostic: (diagnostic: ArtifactVisualDiagnosticInput) => set((state) => {
        const message = diagnostic.message.trim();
        if (!diagnostic.id.trim() || !diagnostic.stageId.trim() || !message) {
          return {};
        }
        const existingDiagnostic = state.artifactVisualDiagnostics.find(
          existing => existing.id === diagnostic.id
        );
        if (
          existingDiagnostic
          && existingDiagnostic.stageId === diagnostic.stageId
          && existingDiagnostic.kind === diagnostic.kind
          && existingDiagnostic.title === diagnostic.title
          && existingDiagnostic.message === message
          && existingDiagnostic.blockIndex === diagnostic.blockIndex
        ) {
          return state;
        }
        const nextDiagnostic = {
          ...diagnostic,
          message,
          createdAt: diagnostic.createdAt ?? existingDiagnostic?.createdAt ?? Date.now(),
        };
        return {
          artifactVisualDiagnostics: [
            ...state.artifactVisualDiagnostics.filter(existing => existing.id !== diagnostic.id),
            nextDiagnostic,
          ],
        };
      }),
      clearArtifactVisualDiagnostic: (diagnosticId) => set((state) => {
        if (!state.artifactVisualDiagnostics.some(diagnostic => diagnostic.id === diagnosticId)) {
          return state;
        }
        return {
          artifactVisualDiagnostics: state.artifactVisualDiagnostics.filter(
            diagnostic => diagnostic.id !== diagnosticId
          ),
          artifactVisualDiagnosticFocusRequest: state.artifactVisualDiagnosticFocusRequest?.id === diagnosticId
            ? null
            : state.artifactVisualDiagnosticFocusRequest,
        };
      }),
      clearArtifactVisualDiagnosticsForStage: (stageId) => set((state) => {
        if (!state.artifactVisualDiagnostics.some(diagnostic => diagnostic.stageId === stageId)) {
          return state;
        }
        return {
          artifactVisualDiagnostics: state.artifactVisualDiagnostics.filter(
            diagnostic => diagnostic.stageId !== stageId
          ),
          artifactVisualDiagnosticFocusRequest: state.artifactVisualDiagnostics.some(
            diagnostic => diagnostic.stageId === stageId
              && diagnostic.id === state.artifactVisualDiagnosticFocusRequest?.id
          )
            ? null
            : state.artifactVisualDiagnosticFocusRequest,
        };
      }),
      focusArtifactVisualDiagnostic: (diagnosticId) => set((state) => {
        const id = diagnosticId.trim();
        if (!id || !state.artifactVisualDiagnostics.some(diagnostic => diagnostic.id === id)) {
          return state;
        }

        return {
          artifactVisualDiagnosticFocusRequest: {
            id,
            seq: (state.artifactVisualDiagnosticFocusRequest?.seq ?? 0) + 1,
          },
        };
      }),
      setCurrentRunId: (runId) => set({ currentRunId: sanitizeCurrentRunId(runId) }),
      applyWorkflowHandoff: (handoff) => set(() => {
        const targetWorkflow = handoff.targetWorkflowId;
        if (!isWorkflowType(targetWorkflow)) {
          return {};
        }

        const workflowConfig = WORKFLOWS[targetWorkflow];
        if (workflowConfig.agentId !== handoff.targetAgentId) {
          return {};
        }

        const targetStageIndex = workflowConfig.stages.findIndex(
          stage => stage.id === handoff.targetStageId
        );
        const targetStage = workflowConfig.stages[targetStageIndex];
        if (targetStageIndex < 0 || !targetStage) {
          return {};
        }

        const artifactContent = getInitialArtifactForStage(targetWorkflow, targetStageIndex);

        return {
          workflow: targetWorkflow,
          stageIndex: targetStageIndex,
          chatHistory: [buildHandoffMessage(handoff)],
          artifactContent,
          artifactChangeIndex: [],
          artifactHistory: [],
          artifactComments: [],
          artifactSectionLocks: [],
          artifactAuditEvents: [],
          artifactVisualDiagnostics: [],
          artifactVisualDiagnosticFocusRequest: null,
          stageArtifacts: {
            [targetStage.id]: artifactContent,
          },
          contextSummaries: [],
          currentRunId: sanitizeCurrentRunId(handoff.targetRunId ?? null),
          pendingStageTransition: null,
          artifactTruncated: false,
          isGenerating: false,
        };
      }),
      restoreRunSnapshot: (snapshot) => set(() => {
        const workflow = snapshot.run.workflowId;
        if (!isWorkflowType(workflow)) {
          return {};
        }

        const workflowConfig = WORKFLOWS[workflow];
        if (workflowConfig.agentId !== snapshot.run.agentId) {
          return {};
        }

        const stageIndex = workflowConfig.stages.findIndex(
          stage => stage.id === snapshot.run.currentStageId
        );
        const currentStage = workflowConfig.stages[stageIndex];
        if (stageIndex < 0 || !currentStage) {
          return {};
        }

        const validStageIds = new Set(workflowConfig.stages.map(stage => stage.id));
        const stageArtifacts: Record<string, string> = {};
        snapshot.artifacts.forEach((artifact) => {
          if (validStageIds.has(artifact.stageId)) {
            stageArtifacts[artifact.stageId] = artifact.content;
          }
        });
        const artifactContent = stageArtifacts[currentStage.id]
          || getInitialArtifactForStage(workflow, stageIndex);
        stageArtifacts[currentStage.id] = artifactContent;

        return {
          workflow,
          stageIndex,
          chatHistory: buildSnapshotMessages(snapshot),
          artifactContent,
          artifactChangeIndex: [],
          artifactHistory: buildSnapshotArtifactHistory(snapshot, validStageIds),
          artifactComments: sanitizeArtifactComments(snapshot.artifactComments, workflow),
          artifactSectionLocks: sanitizeArtifactSectionLocks(snapshot.artifactSectionLocks, workflow),
          artifactAuditEvents: sanitizeArtifactAuditEvents(snapshot.artifactAuditEvents, workflow),
          stageArtifacts,
          contextSummaries: snapshot.contextSummaries,
          currentRunId: snapshot.run.id,
          pendingStageTransition: null,
          artifactTruncated: false,
          artifactVisualDiagnostics: [],
          artifactVisualDiagnosticFocusRequest: null,
          isGenerating: false,
        };
      }),
      setSettingsOpen: (isSettingsOpen) => set({ isSettingsOpen }),
      notifyDefaultLlmConfigChanged: () => set((state) => ({
        configRefreshSeq: state.configRefreshSeq + 1,
      })),
      setIsGenerating: (isGenerating) => set({ isGenerating }),
      clearHistory: () => set((state) => ({
        chatHistory: [],
        artifactHistory: [],
        artifactComments: [],
        artifactSectionLocks: [],
        artifactAuditEvents: [],
        artifactVisualDiagnostics: [],
        artifactVisualDiagnosticFocusRequest: null,
        artifactContent: getWelcomeMessage(state.workflow),
        artifactChangeIndex: [],
        stageArtifacts: {
          [WORKFLOWS[state.workflow].stages[0].id]: getWelcomeMessage(state.workflow)
        },
        stageIndex: 0,
        contextSummaries: [],
        currentRunId: null,
        // P0-4: Reset transition state on clear
        pendingStageTransition: null,
        // P0-9: Reset truncation flag on clear
        artifactTruncated: false,
        isGenerating: false,
      })),
      // P0-4: Stage transition confirmation actions
      setPendingStageTransition: (pending) => set({ pendingStageTransition: pending }),
      clearPendingStageTransition: () => set({ pendingStageTransition: null }),
      confirmStageTransition: () => set((state) => {
        const transitionPlan = planStageTransitionConfirmation({
          pendingTransition: state.pendingStageTransition,
          stageIndex: state.stageIndex,
          stages: WORKFLOWS[state.workflow].stages,
          artifactContent: state.artifactContent,
          stageArtifacts: state.stageArtifacts,
        });
        return transitionPlan
          ? {
            ...transitionPlan,
            artifactChangeIndex: [],
          }
          : {};
      }),
      updateContextSummaryContent: (summary, content) => set((state) => ({
        contextSummaries: state.contextSummaries.map((currentSummary) => (
          isSameContextSummary(currentSummary, summary)
            ? { ...currentSummary, content }
            : currentSummary
        )),
      })),
      upsertContextSummary: (summary) => set((state) => {
        const existingSummaryIndex = state.contextSummaries.findIndex(
          currentSummary => isSameContextSummary(currentSummary, summary)
        );
        if (existingSummaryIndex < 0) {
          return {
            contextSummaries: [...state.contextSummaries, summary],
          };
        }

        return {
          contextSummaries: state.contextSummaries.map((currentSummary, index) => (
            index === existingSummaryIndex ? summary : currentSummary
          )),
        };
      }),
      // P0-9: Artifact truncation action
      setArtifactTruncated: (truncated) => set({ artifactTruncated: truncated }),
    }),
    {
      name: NEW_KEY,
      partialize: (state) => state.currentRunId ? {
        workflow: state.workflow,
      } : {
        workflow: state.workflow,
        stageIndex: state.stageIndex,
        chatHistory: sanitizeChatHistory(state.chatHistory),
        artifactContent: state.artifactContent,
        artifactHistory: state.artifactHistory,
        artifactComments: state.artifactComments,
        artifactSectionLocks: state.artifactSectionLocks,
        artifactAuditEvents: state.artifactAuditEvents,
        stageArtifacts: state.stageArtifacts,
        currentRunId: state.currentRunId,
        artifactTruncated: state.artifactTruncated,
      },
      merge: (persistedState, currentState): AppState => {
        const baseState = currentState as AppState;
        if (!isRecord(persistedState)) return baseState;
        return {
          ...baseState,
          ...sanitizePersistedWorkspaceState(persistedState, baseState),
        };
      },
    }
  )
);
