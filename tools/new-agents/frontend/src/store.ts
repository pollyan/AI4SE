import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { WORKFLOWS } from './core/workflows';
import { ChatState as AppState, ArtifactVersion, Message, WorkflowType } from './core/types';
import { getAgentById } from './core/config/agents';

// Re-export for compatibility
export * from './core/types';
export * from './core/workflows';

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

const OLD_KEY = 'lisa-storage';
const NEW_KEY = 'agent-workspace-storage';
if (typeof window !== 'undefined') {
  try {
    const oldData = localStorage.getItem(OLD_KEY);
    if (oldData && !localStorage.getItem(NEW_KEY)) {
      localStorage.setItem(NEW_KEY, oldData);
      localStorage.removeItem(OLD_KEY);
    }
  } catch (e) {
    console.error('Storage migration failed:', e);
  }
}

export const useStore = create<AppState>()(
  persist(
    (set) => ({
      apiKey: process.env.LLM_API_KEY || '',
      baseUrl: process.env.LLM_BASE_URL || 'https://generativelanguage.googleapis.com/v1beta/openai/',
      model: process.env.LLM_MODEL || 'gemini-3-flash-preview',
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
      isUserConfigured: false,

      setApiKey: (key) => set({ apiKey: key, isUserConfigured: !!key }),
      setIsUserConfigured: (val) => set({ isUserConfigured: val }),
      resetToSystemConfig: () => set({ apiKey: '', baseUrl: '', model: '', isUserConfigured: false }),
      setBaseUrl: (url) => set({ baseUrl: url }),
      setModel: (model) => set({ model }),
      setWorkflow: (workflow) => set({
        workflow,
        stageIndex: 0,
        chatHistory: [],
        artifactHistory: [],
        artifactContent: getWelcomeMessage(workflow),
        stageArtifacts: {
          [WORKFLOWS[workflow].stages[0].id]: getWelcomeMessage(workflow)
        }
      }),
      setStageIndex: (index) => set((state) => {
        const newStageArtifacts = { ...state.stageArtifacts };
        const currentStageId = WORKFLOWS[state.workflow].stages[state.stageIndex].id;
        newStageArtifacts[currentStageId] = state.artifactContent;

        const targetStageId = WORKFLOWS[state.workflow].stages[index].id;
        return {
          stageIndex: index,
          stageArtifacts: newStageArtifacts,
          artifactContent: newStageArtifacts[targetStageId] || `# ${WORKFLOWS[state.workflow].stages[index].name}\n\n暂无产出物。`
        };
      }),
      transitionToNextStage: (initialStageId, initialArtifact) => set((state) => {
        const newStageArtifacts = { ...state.stageArtifacts };
        // Restore the old stage's artifact
        newStageArtifacts[initialStageId] = initialArtifact;

        const nextStage = state.stageIndex + 1;
        // The current artifactContent is the new stage's artifact
        const nextStageId = WORKFLOWS[state.workflow].stages[nextStage].id;
        newStageArtifacts[nextStageId] = state.artifactContent;

        return {
          stageIndex: nextStage,
          stageArtifacts: newStageArtifacts,
          // artifactContent remains the same (the new stage's artifact)
        };
      }),
      addMessage: (msg) => set((state) => ({ chatHistory: [...state.chatHistory, msg] })),
      updateLastMessage: (content) => set((state) => {
        const newHistory = [...state.chatHistory];
        if (newHistory.length > 0) {
          newHistory[newHistory.length - 1].content = content;
        }
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
        const newStageArtifacts = { ...state.stageArtifacts };
        newStageArtifacts[stageId] = content;
        return { stageArtifacts: newStageArtifacts };
      }),
      addArtifactVersion: (version) => set((state) => ({ artifactHistory: [...state.artifactHistory, version] })),
      setSettingsOpen: (isSettingsOpen) => set({ isSettingsOpen }),
      setIsGenerating: (isGenerating) => set({ isGenerating }),
      clearHistory: () => set((state) => ({
        chatHistory: [],
        artifactHistory: [],
        artifactContent: getWelcomeMessage(state.workflow),
        stageArtifacts: {
          [WORKFLOWS[state.workflow].stages[0].id]: getWelcomeMessage(state.workflow)
        },
        stageIndex: 0
      })),
    }),
    {
      name: NEW_KEY,
      partialize: (state) => ({
        baseUrl: state.baseUrl,
        model: state.model,
        workflow: state.workflow,
        stageIndex: state.stageIndex,
        chatHistory: state.chatHistory,
        artifactContent: state.artifactContent,
        artifactHistory: state.artifactHistory,
        stageArtifacts: state.stageArtifacts,
        isUserConfigured: state.isUserConfigured,
      }),
    }
  )
);
