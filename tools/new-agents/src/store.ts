import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { WORKFLOWS } from './workflows';
import { ChatState as AppState, ArtifactVersion, Message, WorkflowType } from './types';

// Re-export for compatibility
export * from './types';
export * from './workflows';

export const useStore = create<AppState>()(
  persist(
    (set) => ({
      apiKey: process.env.LLM_API_KEY || '',
      baseUrl: process.env.LLM_BASE_URL || 'https://generativelanguage.googleapis.com/v1beta/openai/',
      model: process.env.LLM_MODEL || 'gemini-3-flash-preview',
      workflow: 'TEST_DESIGN',
      stageIndex: 0,
      chatHistory: [],
      artifactContent: '# 欢迎使用 Lisa 测试专家\n\n请在左侧输入您的需求，我将为您生成测试文档。',
      artifactHistory: [],
      stageArtifacts: {
        0: '# 欢迎使用 Lisa 测试专家\n\n请在左侧输入您的需求，我将为您生成测试文档。'
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
        artifactContent: '# 欢迎使用 Lisa 测试专家\n\n请在左侧输入您的需求，我将为您生成测试文档。',
        stageArtifacts: {
          0: '# 欢迎使用 Lisa 测试专家\n\n请在左侧输入您的需求，我将为您生成测试文档。'
        }
      }),
      setStageIndex: (index) => set((state) => {
        const newStageArtifacts = { ...state.stageArtifacts };
        newStageArtifacts[state.stageIndex] = state.artifactContent;

        return {
          stageIndex: index,
          stageArtifacts: newStageArtifacts,
          artifactContent: newStageArtifacts[index] || `# ${WORKFLOWS[state.workflow].stages[index].name}\n\n暂无产出物。`
        };
      }),
      transitionToNextStage: (initialStage, initialArtifact) => set((state) => {
        const newStageArtifacts = { ...state.stageArtifacts };
        // Restore the old stage's artifact
        newStageArtifacts[initialStage] = initialArtifact;

        const nextStage = state.stageIndex + 1;
        // The current artifactContent is the new stage's artifact
        newStageArtifacts[nextStage] = state.artifactContent;

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
      removeLastMessage: () => set((state) => {
        const newHistory = [...state.chatHistory];
        if (newHistory.length > 0) {
          newHistory.pop();
        }
        return { chatHistory: newHistory };
      }),
      setArtifactContent: (artifactContent) => set((state) => {
        const newStageArtifacts = { ...state.stageArtifacts };
        newStageArtifacts[state.stageIndex] = artifactContent;
        return { artifactContent, stageArtifacts: newStageArtifacts };
      }),
      setStageArtifact: (index, content) => set((state) => {
        const newStageArtifacts = { ...state.stageArtifacts };
        newStageArtifacts[index] = content;
        return { stageArtifacts: newStageArtifacts };
      }),
      addArtifactVersion: (version) => set((state) => ({ artifactHistory: [...state.artifactHistory, version] })),
      setSettingsOpen: (isSettingsOpen) => set({ isSettingsOpen }),
      setIsGenerating: (isGenerating) => set({ isGenerating }),
      clearHistory: () => set({
        chatHistory: [],
        artifactHistory: [],
        artifactContent: '# 欢迎使用 Lisa 测试专家\n\n请在左侧输入您的需求，我将为您生成测试文档。',
        stageArtifacts: {
          0: '# 欢迎使用 Lisa 测试专家\n\n请在左侧输入您的需求，我将为您生成测试文档。'
        },
        stageIndex: 0
      }),
    }),
    {
      name: 'lisa-storage',
      partialize: (state) => ({
        apiKey: state.apiKey,
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
