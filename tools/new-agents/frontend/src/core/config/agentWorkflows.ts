export interface AgentWorkflowConfig {
    id: string;
    agentId: string;
    status: 'online' | 'dev' | 'plan';
    name: string;
    description: string;
    icon: string;
    link?: string;
    statusLabel?: string;
}

const AGENT_WORKFLOWS: AgentWorkflowConfig[] = [
    {
        id: 'test-design',
        agentId: 'lisa',
        status: 'online',
        name: '测试策略与用例设计',
        description: '提供产品需求或代码变更集，为你自动设计详尽的测试策略与测试用例。',
        icon: 'TestTube2',
        link: '/workspace/lisa/test-design'
    },
    {
        id: 'req-review',
        agentId: 'lisa',
        status: 'online',
        name: '需求评审',
        description: '从测试人员视角深度评审需求文档，自动扫描可测试性、完整性、边界定义等维度，输出结构化的评审问题清单。',
        icon: 'FileCode2',
        link: '/workspace/lisa/req-review'
    },
    {
        id: 'incident-review',
        agentId: 'lisa',
        status: 'online',
        name: '线上故障复盘',
        description: '引导你用结构化方法完成线上故障复盘，自动生成包含时间线、根因分析（5-Why + 鱼骨图）和改进措施的专业复盘报告。',
        icon: 'ShieldAlert',
        link: '/workspace/lisa/incident-review'
    },
    {
        id: 'log-diagnostics',
        agentId: 'lisa',
        status: 'dev',
        name: '执行日志诊断',
        description: '导入 MidScene 录制的运行日志、截图及错误报告，智能定位元素变更和代码故障点。',
        icon: 'ActivitySquare',
        statusLabel: 'Dev'
    },
    {
        id: 'auto-assert',
        agentId: 'lisa',
        status: 'plan',
        name: '智能断言生成',
        description: '结合上下文语境与页面 DOM 结构，自动预测并生成可执行的 AI 意图校验断言语句。',
        icon: 'FileCode2',
        statusLabel: 'Plan'
    },
    {
        id: 'idea-brainstorm',
        agentId: 'alex',
        status: 'online',
        name: '创意头脑风暴',
        description: '引导你完成创意探索和产品概念沉淀，生成清晰可沟通的产品概念简报（One-Pager）。',
        icon: 'Lightbulb',
        link: '/workspace/alex/idea-brainstorm'
    }
];

export const getAgentWorkflows = (agentId: string): AgentWorkflowConfig[] => {
    return AGENT_WORKFLOWS.filter(wf => wf.agentId === agentId);
};
