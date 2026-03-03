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
        description: '提供产品需求或代码变更集，一站式完成智能化的需求评审，并为你自动设计详尽的测试策略与自动化测试用例。',
        icon: 'TestTube2',
        link: '/workspace/lisa/test-design'
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
    }
];

export const getAgentWorkflows = (agentId: string): AgentWorkflowConfig[] => {
    return AGENT_WORKFLOWS.filter(wf => wf.agentId === agentId);
};
