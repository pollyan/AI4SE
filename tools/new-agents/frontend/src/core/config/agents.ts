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
        description: '专注于做需求评审，并为新需求、新功能设计测试策略与用例的智能体。',
        features: [
            '智能化跟进需求评审',
            '测试策略自动推导与设计',
            '意图级前端测试用例生成'
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
