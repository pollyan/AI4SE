import { WORKFLOWS } from '../workflows';
import type { WorkflowPreviewConfig } from '../types';

export interface AgentWorkflowConfig {
    id: string;
    agentId: string;
    status: 'online' | 'dev' | 'plan';
    name: string;
    description: string;
    icon: string;
    link?: string;
    statusLabel?: string;
    preview?: WorkflowPreviewConfig;
}

const ONLINE_AGENT_WORKFLOWS: AgentWorkflowConfig[] = Object.values(WORKFLOWS).map((workflow) => ({
    id: workflow.slug,
    agentId: workflow.agentId,
    status: 'online',
    name: workflow.listing.name,
    description: workflow.listing.description,
    icon: workflow.listing.icon,
    link: `/workspace/${workflow.agentId}/${workflow.slug}`,
    preview: workflow.listing.preview,
}));

const NON_RUNTIME_AGENT_WORKFLOWS: AgentWorkflowConfig[] = [
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
        id: 'competitive-analysis',
        agentId: 'alex',
        status: 'plan',
        name: '竞品分析',
        description: '收集市场与竞品信息，通过多维对比和属性打分自动生成差异化策略洞察报告。',
        icon: 'BarChart2',
        statusLabel: 'Plan'
    }
];

const AGENT_WORKFLOWS: AgentWorkflowConfig[] = [
    ...ONLINE_AGENT_WORKFLOWS,
    ...NON_RUNTIME_AGENT_WORKFLOWS,
];

export const getAgentWorkflows = (agentId: string): AgentWorkflowConfig[] => {
    return AGENT_WORKFLOWS.filter(wf => wf.agentId === agentId);
};
