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

// 已实现的工作流类型（仅包含 online 状态）
export type WorkflowType = 'TEST_DESIGN' | 'REQ_REVIEW' | 'INCIDENT_REVIEW' | 'IDEA_BRAINSTORM' | 'VALUE_DISCOVERY';

// 工作流 ID 到 Slug 的映射（大写 -> 小写连字符）
export const WORKFLOW_SLUGS: Record<WorkflowType, string> = {
    TEST_DESIGN: 'test-design',
    REQ_REVIEW: 'req-review',
    INCIDENT_REVIEW: 'incident-review',
    IDEA_BRAINSTORM: 'idea-brainstorm',
    VALUE_DISCOVERY: 'value-discovery',
} as const;

// Slug 到工作流 ID 的反向映射（按需生成，避免手动维护）
export const SLUG_TO_WORKFLOW: Record<string, WorkflowType> = 
    Object.fromEntries(Object.entries(WORKFLOW_SLUGS).map(([k, v]) => [v, k])) as Record<string, WorkflowType>;

export interface WorkflowStage {
    id: string;
    name: string;
    description: string;
    template?: string;
}

export interface OnboardingConfig {
    welcomeMessage: string;
    starterPrompts: string[];
    inputPlaceholder: string;
}

export interface WorkflowDef {
    id: WorkflowType;
    agentId: string;
    welcomeMessage?: string;
    description: string;
    name: string;
    stages: WorkflowStage[];
    onboarding: OnboardingConfig;
}

export interface ChatState {
    apiKey: string;
    baseUrl: string;
    model: string;
    isUserConfigured: boolean;
    workflow: WorkflowType;
    stageIndex: number;
    chatHistory: Message[];
    artifactContent: string;
    artifactHistory: ArtifactVersion[];
    stageArtifacts: Record<string, string>;
    isSettingsOpen: boolean;
    isGenerating: boolean;

    // Actions
    setApiKey: (key: string) => void;
    setBaseUrl: (url: string) => void;
    setModel: (model: string) => void;
    setIsUserConfigured: (isConfigured: boolean) => void;
    setWorkflow: (workflow: WorkflowType) => void;
    setStageIndex: (index: number) => void;
    transitionToNextStage: (initialStageId: string, initialArtifact: string) => void;
    addMessage: (msg: Message) => void;
    updateLastMessage: (content: string) => void;
    updateMessage: (id: string, content: string) => void;
    removeLastMessage: () => void;
    setArtifactContent: (content: string) => void;
    addArtifactVersion: (version: ArtifactVersion) => void;
    setSettingsOpen: (isOpen: boolean) => void;
    setIsGenerating: (isGenerating: boolean) => void;
    clearHistory: () => void;
    setStageArtifact: (stageId: string, content: string) => void;
    resetToSystemConfig: () => void;
}
