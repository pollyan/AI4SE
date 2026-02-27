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
        description: '专注于意图测试设计、用例自动生成和自动化测试脚本编写的智能体。',
        features: [
            '自动化端到端测试设计',
            'UI / API 自动化用例生成',
            '意图驱动执行支持'
        ]
    },
    {
        id: 'alex',
        status: 'coming_soon',
        name: 'Alex',
        role: '前端框架专家',
        description: '擅长解析 UI 设计稿，自动化编写 React/Vue 组件与框架层代码，提升产研效能。',
        features: [
            'UI 视觉稿精准切图与识别',
            '页面骨架与交互逻辑生成',
            '样式系统无缝接入 (Tailwind)'
        ]
    }
];

export const getAgents = (): AgentConfig[] => {
    return AGENTS;
};

export const getAgentById = (id: string): AgentConfig | undefined => {
    return AGENTS.find(agent => agent.id === id);
};
