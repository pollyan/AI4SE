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

export interface WorkflowStage {
    id: string;
    name: string;
    description: string;
}

export interface WorkflowDef {
    id: WorkflowType;
    name: string;
    stages: WorkflowStage[];
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
    stageArtifacts: { [stageIndex: number]: string };
    isSettingsOpen: boolean;
    isGenerating: boolean;

    // Actions
    setApiKey: (key: string) => void;
    setBaseUrl: (url: string) => void;
    setModel: (model: string) => void;
    setIsUserConfigured: (isConfigured: boolean) => void;
    setWorkflow: (workflow: WorkflowType) => void;
    setStageIndex: (index: number) => void;
    transitionToNextStage: (currentIndex: number, currentArtifact: string) => void;
    addMessage: (msg: Message) => void;
    updateLastMessage: (content: string) => void;
    removeLastMessage: () => void;
    setArtifactContent: (content: string) => void;
    addArtifactVersion: (version: ArtifactVersion) => void;
    setSettingsOpen: (isOpen: boolean) => void;
    setIsGenerating: (isGenerating: boolean) => void;
    clearHistory: () => void;
    setStageArtifact: (index: number, content: string) => void;
    resetToSystemConfig: () => void;
}
