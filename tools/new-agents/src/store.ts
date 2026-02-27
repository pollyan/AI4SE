import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type Attachment = {
  name: string;
  data: string;
  mimeType: string;
};

export type ArtifactVersion = {
  id: string;
  timestamp: number;
  content: string;
};

export type Message = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
  attachments?: Attachment[];
};

export type WorkflowType = 'TEST_DESIGN' | 'REQ_REVIEW';

export const WORKFLOWS = {
  TEST_DESIGN: {
    id: 'TEST_DESIGN',
    name: '测试设计',
    stages: [
      {
        id: 'CLARIFY',
        name: '需求澄清',
        description: `阅读用户需求，识别核心测试对象，并在右侧生成《需求分析文档》。
【重要警告】：产出物中绝对不要包含“下一步计划”或类似章节。在左侧对话中，强制要求用户解答待确认项后才能进入下一阶段。
右侧产出物必须严格按照以下模板结构生成：

# 需求分析文档

## 1. 被测系统与边界 (System Under Test & Boundaries)
这是整个测试工作的基础。如果不清楚测什么、不测什么，测试就永远没有尽头。
### 1.1 核心业务目标 (Business Value)
内容：用一句话概括这个需求为了解决什么业务问题。测试不仅要验证“跑得通”，更要验证“达到了业务目的”。
### 1.2 测试范围 (In-Scope)
内容：明确列出本次需要测试的页面、API 接口、业务逻辑分支。必须具体到模块名称。
### 1.3 不测范围 (Out-of-Scope)
内容：明确声明本次绝对不去测的内容（例如：历史老系统的兼容性、第三方支付渠道底层的稳定性、本次未改动的关联模块）。这是测试人员最重要的免责声明和防甩锅利器。

## 2. 系统交互与核心链路 (System Interactions & Core Flows)
梳理被测对象在这套浩瀚的系统架构里，处于什么位置，和谁打交道。
### 2.1 核心主流程 (Happy Paths)
内容：正常情况下，用户或数据从 A 端走到 B 端的正确路径描述。强制配合 Mermaid 流程图或时序图形式呈现。
### 2.2 外部依赖与契约 (External Dependencies)
内容：列出该功能依赖的所有上下游模块、第三方接口。标注这些接口目前是“已就绪”、“开发中”还是“需要 Mock (挡板)”。

## 3. 待澄清与阻断性问题 (Blocking Clarifications)
这是澄清阶段最核心的产出，倒逼产品经理和架构师填坑。
### 3.1 P0 级业务逻辑漏洞 (P0 Logical Gaps)
内容：业务规则中的矛盾点、缺失的异常分支处理（例如：“逆向流程”：退款、超时、并发超卖、断网重连时的处理机制是什么？）。
### 3.2 P1/P2 级规则细节 (P1/P2 Rule Details)
内容：具体的边界值定义、字段校验规则、默认值设定等。
状态追踪：该列表必须带有状态标记（待确认 / 已确认并给出结论）。

## 4. 隐式需求与非功能性考量 (Non-Functional Requirements)
优秀的测试专家不能只盯着功能，往往是这类需求会导致严重的线上事故。
### 4.1 性能与并发要求 (Performance & Concurrency)
内容：预期的 QPS/TPS 是多少？响应时间 SLA 要求？是否有高并发秒杀场景？
### 4.2 安全与合规要求 (Security & Compliance)
内容：是否有敏感数据需要脱敏传输和存储？是否有越权访问风险？是否符合隐私法规？
### 4.3 兼容性要求 (Compatibility)
内容：明确支持的端、需要覆盖的浏览器版本范围、iOS/Android 最低支持版本号。`
      },
      { id: 'STRATEGY', name: '策略制定', description: '基于澄清结果，在右侧生成《测试策略蓝图》（包含风险点和优先级）。' },
      { id: 'CASES', name: '用例编写', description: '根据策略输出具体的测试点和场景，右侧更新为《测试用例集》。' },
      { id: 'DELIVERY', name: '文档交付', description: '整合所有内容，右侧输出完整的《测试设计交付文档》。' }
    ]
  },
  REQ_REVIEW: {
    id: 'REQ_REVIEW',
    name: '需求评审',
    stages: [
      { id: 'CLARIFY', name: '需求澄清', description: '确认评审范围。' },
      { id: 'ANALYSIS', name: '评审分析', description: '检查完整性、一致性、异常闭环等，产出缺陷记录。' },
      { id: 'RISK', name: '风险评估', description: '评估技术与进度风险，确定必须优先测试的高风险区域 (P0)。' },
      { id: 'REPORT', name: '评审报告', description: '生成最终的《敏捷需求评审报告》并给出评审结论（通过/有条件通过/不通过）。' }
    ]
  }
};

interface AppState {
  apiKey: string;
  baseUrl: string;
  model: string;
  workflow: WorkflowType;
  stageIndex: number;
  chatHistory: Message[];
  artifactContent: string;
  artifactHistory: ArtifactVersion[];
  stageArtifacts: Record<number, string>;
  isSettingsOpen: boolean;
  isGenerating: boolean;

  setApiKey: (key: string) => void;
  setBaseUrl: (url: string) => void;
  setModel: (model: string) => void;
  setWorkflow: (wf: WorkflowType) => void;
  setStageIndex: (index: number) => void;
  transitionToNextStage: (initialStage: number, initialArtifact: string) => void;
  addMessage: (msg: Message) => void;
  updateLastMessage: (content: string) => void;
  removeLastMessage: () => void;
  setArtifactContent: (content: string) => void;
  setStageArtifact: (index: number, content: string) => void;
  addArtifactVersion: (version: ArtifactVersion) => void;
  setSettingsOpen: (isOpen: boolean) => void;
  setIsGenerating: (isGenerating: boolean) => void;
  clearHistory: () => void;
  isUserConfigured: boolean;
  setIsUserConfigured: (val: boolean) => void;
  resetToSystemConfig: () => void;
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
