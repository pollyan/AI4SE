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

export type WorkflowType = 'TEST_DESIGN' | 'REQ_REVIEW' | 'INCIDENT_REVIEW' | 'IDEA_BRAINSTORM' | 'VALUE_DISCOVERY';

export const WORKFLOW_SLUGS: Record<WorkflowType, string> = {
    TEST_DESIGN: 'test-design',
    REQ_REVIEW: 'req-review',
    INCIDENT_REVIEW: 'incident-review',
    IDEA_BRAINSTORM: 'idea-brainstorm',
    VALUE_DISCOVERY: 'value-discovery',
};

export const SLUG_TO_WORKFLOW: Record<string, WorkflowType> = Object.fromEntries(
    Object.entries(WORKFLOW_SLUGS).map(([k, v]) => [v, k as WorkflowType])
) as Record<string, WorkflowType>;

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
    removeLastMessage: () => void;
    setArtifactContent: (content: string) => void;
    addArtifactVersion: (version: ArtifactVersion) => void;
    setSettingsOpen: (isOpen: boolean) => void;
    setIsGenerating: (isGenerating: boolean) => void;
    clearHistory: () => void;
    setStageArtifact: (stageId: string, content: string) => void;
    resetToSystemConfig: () => void;
}
