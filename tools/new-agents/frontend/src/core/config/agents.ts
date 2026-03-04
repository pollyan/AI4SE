export interface AgentConfig {
    id: string;
    status: 'online' | 'coming_soon' | 'offline';
    name: string;
    role: string;
    description: string;
    features: string[];
}

const AGENTS: AgentConfig[] = [
    {
        id: 'lisa',
        status: 'online',
        name: 'Lisa',
        role: '测试专家',
        description: '专注于深度需求评审、测试策略与用例辅助设计，并提供结构化线上故障复盘引导的智能体。',
        features: [
            '智能化跟进需求评审',
            '测试策略推导与用例设计',
            '结构化线上故障复盘分析'
        ]
    },
    {
        id: 'alex',
        status: 'coming_soon',
        name: 'Alex',
        role: '业务需求分析师',
        description: '擅长分析业务场景与用户故事，自动化拆解产品逻辑，生成清晰规范的需求文档（PRD）。',
        features: [
            '业务需求深度解析',
            '功能逻辑树构建',
            '敏捷开发故事拆分'
        ]
    }
];

export const getAgents = (): AgentConfig[] => {
    return AGENTS;
};

export const getAgentById = (id: string): AgentConfig | undefined => {
    return AGENTS.find(agent => agent.id === id);
};
