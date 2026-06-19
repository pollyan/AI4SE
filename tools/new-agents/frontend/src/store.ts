import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { WORKFLOWS } from './core/workflows';
import { ChatState as AppState, ArtifactVersion, Message, WorkflowType } from './core/types';
import { getAgentById } from './core/config/agents';
import { planStageTransitionConfirmation } from './core/agentCore';

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

const isRecord = (value: unknown): value is Record<string, unknown> => (
  typeof value === 'object' && value !== null
);

const isWorkflowType = (value: unknown): value is WorkflowType => (
  typeof value === 'string'
  && Object.prototype.hasOwnProperty.call(WORKFLOWS, value)
);

const sanitizeAttachments = (attachments: unknown): Message['attachments'] => {
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
    return [sanitizedMessage];
  });
};

const sanitizeStageArtifacts = (
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
  const stageCount = WORKFLOWS[workflow].stages.length;
  const hasValidPersistedStageIndex = (
    Number.isInteger(persistedState.stageIndex)
    && (persistedState.stageIndex as number) >= 0
    && (persistedState.stageIndex as number) < stageCount
  );
  const stageIndex = hasValidPersistedStageIndex
    ? persistedState.stageIndex as number
    : 0;
  const stageArtifacts = sanitizeStageArtifacts(
    persistedState.stageArtifacts,
    workflow
  );
  const currentStageId = WORKFLOWS[workflow].stages[stageIndex].id;
  const persistedArtifactContent = hasValidPersistedWorkflow
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
    chatHistory: sanitizeChatHistory(persistedState.chatHistory),
    artifactContent,
    artifactHistory: sanitizeArtifactHistory(persistedState.artifactHistory),
    stageArtifacts: {
      ...stageArtifacts,
      [currentStageId]: artifactContent,
    },
    isGenerating: currentState.isGenerating,
    pendingStageTransition: currentState.pendingStageTransition,
    artifactTruncated,
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
  persist(
    (set) => ({
      workflow: 'TEST_DESIGN',
      stageIndex: 0,
      chatHistory: [],
      artifactContent: getWelcomeMessage('TEST_DESIGN'),
      artifactHistory: [],
      stageArtifacts: {
        [WORKFLOWS['TEST_DESIGN'].stages[0].id]: getWelcomeMessage('TEST_DESIGN')
      },
      isSettingsOpen: false,
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
        artifactContent: getWelcomeMessage(workflow),
        stageArtifacts: {
          [WORKFLOWS[workflow].stages[0].id]: getWelcomeMessage(workflow)
        },
        pendingStageTransition: null,
        artifactTruncated: false,
        isGenerating: false,
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
          artifactTruncated: false,
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
          pendingStageTransition: null,
          artifactTruncated: false,
          isGenerating: false,
        };
      }),
      addMessage: (msg) => set((state) => ({ chatHistory: [...state.chatHistory, msg] })),
      updateLastMessage: (content) => set((state) => {
        const lastMessage = state.chatHistory[state.chatHistory.length - 1];
        if (!lastMessage || lastMessage.content === content) {
          return state;
        }
        const newHistory = [...state.chatHistory];
        newHistory[newHistory.length - 1] = { ...lastMessage, content };
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
        return { artifactContent, stageArtifacts: newStageArtifacts };
      }),
      setStageArtifact: (stageId, content) => set((state) => {
        const workflowStageIds = new Set(
          WORKFLOWS[state.workflow].stages.map(stage => stage.id)
        );
        if (!workflowStageIds.has(stageId)) {
          return {};
        }

        const newStageArtifacts = { ...state.stageArtifacts };
        newStageArtifacts[stageId] = content;
        return { stageArtifacts: newStageArtifacts };
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
      setSettingsOpen: (isSettingsOpen) => set({ isSettingsOpen }),
      setIsGenerating: (isGenerating) => set({ isGenerating }),
      clearHistory: () => set((state) => ({
        chatHistory: [],
        artifactHistory: [],
        artifactContent: getWelcomeMessage(state.workflow),
        stageArtifacts: {
          [WORKFLOWS[state.workflow].stages[0].id]: getWelcomeMessage(state.workflow)
        },
        stageIndex: 0,
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
        return planStageTransitionConfirmation({
          pendingTransition: state.pendingStageTransition,
          stageIndex: state.stageIndex,
          stages: WORKFLOWS[state.workflow].stages,
          artifactContent: state.artifactContent,
          stageArtifacts: state.stageArtifacts,
        }) || {};
      }),
      // P0-9: Artifact truncation action
      setArtifactTruncated: (truncated) => set({ artifactTruncated: truncated }),
    }),
    {
      name: NEW_KEY,
      partialize: (state) => ({
        workflow: state.workflow,
        stageIndex: state.stageIndex,
        chatHistory: sanitizeChatHistory(state.chatHistory),
        artifactContent: state.artifactContent,
        artifactHistory: state.artifactHistory,
        stageArtifacts: state.stageArtifacts,
        artifactTruncated: state.artifactTruncated,
      }),
      merge: (persistedState, currentState) => {
        if (!isRecord(persistedState)) return currentState;
        return {
          ...currentState,
          ...sanitizePersistedWorkspaceState(persistedState, currentState),
        };
      },
    }
  )
);
